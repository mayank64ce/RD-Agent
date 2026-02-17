"""
FHE Research Agent (ExpGen).

FHEHypothesis - wraps proposed algorithm plan
FHEExpGen     - calls LLM to propose algorithm, returns FHEExperiment
"""

from __future__ import annotations

from pathlib import Path

from rdagent.core.proposal import ExpGen, ExperimentFeedback, Hypothesis, Trace
from rdagent.log import rdagent_logger as logger
from rdagent.oai.llm_utils import APIBackend
from rdagent.scenarios.fhe_challenge.experiment import FHEExperiment, FHETask


class FHEHypothesis(Hypothesis):
    """A proposed algorithm plan for implementing eval()."""

    def __init__(self, algorithm: str, reasoning: str) -> None:
        super().__init__(
            hypothesis=algorithm,
            reason=reasoning,
            concise_reason=reasoning[:200],
            concise_observation="",
            concise_justification="",
            concise_knowledge="",
        )
        self.algorithm: str = algorithm

    def __str__(self) -> str:
        return f"Algorithm Plan:\n{self.algorithm}"


class FHEExpGen(ExpGen):
    """
    Research Agent: reads challenge description + history, proposes an algorithm plan.

    Uses prompts/propose.md template.
    """

    def __init__(self, scen) -> None:
        super().__init__(scen)
        prompt_path = Path(__file__).parent / "prompts" / "propose.md"
        self.prompt_template: str = prompt_path.read_text()

    def gen(self, trace: Trace, plan=None) -> FHEExperiment:
        history_text = self._build_history(trace)
        var_text = self._format_variable_names()
        template_summary = self._format_template_summary()

        user_prompt = self.prompt_template.format(
            challenge_md=self.scen.challenge_md,
            template_summary=template_summary,
            variable_names=var_text,
            history=history_text,
        )

        logger.info(f"[FHEExpGen] Calling LLM to propose algorithm for {self.scen.challenge_name}")
        response = APIBackend().build_messages_and_create_chat_completion(
            user_prompt=user_prompt,
            system_prompt="You are an FHE expert specializing in the OpenFHE C++ library.",
        )

        algorithm = response.strip()
        reasoning = algorithm[:500]

        hyp = FHEHypothesis(algorithm=algorithm, reasoning=reasoning)
        logger.log_object(hyp, tag="hypothesis")
        return FHEExperiment(tasks=[FHETask(algorithm_plan=algorithm)], hypothesis=hyp)

    def _build_history(self, trace: Trace) -> str:
        """Build a summary of the last 3 attempts from trace.hist."""
        if not trace.hist:
            return "No previous attempts."

        lines = []
        recent = trace.hist[-3:]
        for i, (exp, fb) in enumerate(recent):
            lines.append(f"\n### Attempt {len(trace.hist) - len(recent) + i + 1}")
            if exp.hypothesis and hasattr(exp.hypothesis, "algorithm"):
                # Show first 300 chars of algorithm plan
                plan_preview = exp.hypothesis.algorithm[:300]
                lines.append(f"Algorithm (preview): {plan_preview}...")
            result_str = "SUCCESS" if fb.decision else "FAILED"
            lines.append(f"Result: {result_str}")
            lines.append(f"Feedback: {str(fb.reason)[:600]}")

        return "\n".join(lines)

    def _format_variable_names(self) -> str:
        var_names = self.scen.variable_names
        lines = []
        if "cc" in var_names:
            lines.append(f"  {var_names['cc']}  → CryptoContext<DCRTPoly>")
        if "input" in var_names:
            lines.append(f"  {var_names['input']}  → Input Ciphertext<DCRTPoly>")
        if "output" in var_names:
            lines.append(f"  {var_names['output']}  → Output Ciphertext (assign here, eval() is void)")
        if "pk" in var_names:
            lines.append(f"  {var_names['pk']}  → PublicKey<DCRTPoly>")
        return "\n".join(lines) if lines else "  (variable names not extracted)"

    def _format_template_summary(self) -> str:
        lines = []
        for fname, content in self.scen.template_files.items():
            lines.append(f"- {fname}: {len(content)} chars")
        return "\n".join(lines) if lines else "  (no template files found)"
