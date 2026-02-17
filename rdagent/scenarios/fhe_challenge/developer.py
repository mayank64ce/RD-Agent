"""
FHE Developer Agent (FHECoder).

Generates the eval() function body and injects it into the template yourSolution.cpp.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from rdagent.core.developer import Developer
from rdagent.core.exception import CoderError
from rdagent.log import rdagent_logger as logger
from rdagent.oai.llm_utils import APIBackend
from rdagent.scenarios.fhe_challenge.experiment import FHEExperiment


class FHECoder(Developer):
    """
    Developer Agent: given an FHEExperiment with a hypothesis (algorithm plan),
    generates C++ code for the eval() body and injects it into yourSolution.cpp.

    For white_box challenges, optionally also extracts a JSON config block.
    """

    def __init__(self, scen) -> None:
        super().__init__(scen)
        prompt_path = Path(__file__).parent / "prompts" / "code.md"
        self.prompt_template: str = prompt_path.read_text()

    def develop(self, exp: FHEExperiment) -> FHEExperiment:
        if not exp.sub_tasks:
            raise CoderError("FHEExperiment has no sub_tasks")

        task = exp.sub_tasks[0]
        algorithm_plan = task.algorithm_plan

        # Get template yourSolution.cpp
        template_cpp = self.scen.template_files.get("yourSolution.cpp", "")
        if not template_cpp:
            raise CoderError("No yourSolution.cpp template found in challenge")

        # Build last feedback context
        feedback_text = self._get_feedback_context(exp)

        user_prompt = self.prompt_template.format(
            algorithm_plan=algorithm_plan,
            challenge_summary=self.scen.challenge_md[:1200],
            variable_names=self._format_variable_names(),
            feedback=feedback_text,
            challenge_type=self.scen.challenge_type,
        )

        logger.info(f"[FHECoder] Calling LLM to generate eval() body for {self.scen.challenge_name}")
        response = APIBackend().build_messages_and_create_chat_completion(
            user_prompt=user_prompt,
            system_prompt="You are an OpenFHE C++ expert. Generate only the eval() function body.",
        )

        # Extract eval() body from ```cpp ... ``` block
        eval_body = self._extract_cpp_code(response)
        if not eval_body:
            raise CoderError("LLM did not produce a ```cpp ... ``` code block in response")

        # Strip any void eval() { ... } wrapper if LLM included it
        eval_body = self._strip_eval_wrapper(eval_body)

        # Inject eval body into template
        try:
            modified_cpp = self._inject_eval_body(template_cpp, eval_body)
        except ValueError as e:
            raise CoderError(f"Code injection failed: {e}") from e

        # Write modified cpp to workspace using relative path (for runner to use)
        exp.experiment_workspace.inject_files(**{"yourSolution.cpp": modified_cpp})

        # For white_box: also extract optional config.json block
        if self.scen.challenge_type == "white_box":
            config = self._extract_config(response)
            if config is not None:
                exp.experiment_workspace.inject_files(**{"config.json": json.dumps(config, indent=2)})
                logger.info("[FHECoder] Extracted and stored modified config.json")

        logger.log_object({"eval_body_lines": eval_body.count("\n") + 1}, tag="code_stats")
        return exp

    def _get_feedback_context(self, exp: FHEExperiment) -> str:
        """Build feedback string from previous run results stored in exp."""
        if exp.error_message:
            return f"Previous attempt failed:\n{exp.error_message[:800]}"
        if exp.docker_output:
            return f"Previous output (last 500 chars):\n{exp.docker_output[-500:]}"
        return "No previous feedback (first attempt)."

    def _format_variable_names(self) -> str:
        var_names = self.scen.variable_names
        lines = []
        if "cc" in var_names:
            lines.append(f"- {var_names['cc']}  → CryptoContext<DCRTPoly> (NOT 'cc')")
        if "input" in var_names:
            lines.append(f"- {var_names['input']}  → Input Ciphertext<DCRTPoly> (read from this)")
        if "output" in var_names:
            lines.append(
                f"- {var_names['output']}  → Output Ciphertext"
                " (ASSIGN to this, eval() is void - no return!)"
            )
        if "pk" in var_names:
            lines.append(f"- {var_names['pk']}  → PublicKey<DCRTPoly>")
        return "\n".join(lines) if lines else "  (variable names not extracted from header)"

    def _extract_cpp_code(self, response: str) -> str:
        """Extract C++ code from ```cpp ... ``` block in LLM response."""
        match = re.search(r"```cpp\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback: try generic code block
        match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            code = match.group(1).strip()
            # Only use if it looks like C++ (has common FHE keywords)
            if any(kw in code for kw in ["EvalMult", "EvalAdd", "m_cc", "m_InputC", "Ciphertext"]):
                return code
        return ""

    def _extract_config(self, response: str) -> dict | None:
        """Extract JSON config from ```json ... ``` block (white box only)."""
        match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                logger.warning("[FHECoder] Found ```json block but failed to parse it")
        return None

    def _strip_eval_wrapper(self, code: str) -> str:
        """
        If LLM included the function signature void ClassName::eval() { ... },
        strip it and return only the body.
        """
        match = re.search(r"void\s+\w+::eval\s*\(\s*\)\s*\{(.*)", code, re.DOTALL)
        if match:
            body = match.group(1)
            # Remove trailing closing brace of the function
            depth = 1
            pos = 0
            while pos < len(body) and depth > 0:
                if body[pos] == "{":
                    depth += 1
                elif body[pos] == "}":
                    depth -= 1
                pos += 1
            return body[: pos - 1].strip()
        return code

    def _inject_eval_body(self, template_cpp: str, eval_body: str) -> str:
        """
        Replace the body of void ClassName::eval() { <body> } with eval_body.

        Uses regex to find the function start, then brace-matching to find the end.
        """
        pattern = r"(void\s+\w+::eval\s*\(\s*\)\s*\{)"
        match = re.search(pattern, template_cpp)
        if not match:
            raise ValueError("Cannot find 'void ClassName::eval() {' in template")

        start = match.end()
        depth = 1
        pos = start
        while pos < len(template_cpp) and depth > 0:
            if template_cpp[pos] == "{":
                depth += 1
            elif template_cpp[pos] == "}":
                depth -= 1
            pos += 1

        # pos-1 points to the closing '}' of eval()
        return template_cpp[:start] + f"\n{eval_body}\n" + template_cpp[pos - 1 :]
