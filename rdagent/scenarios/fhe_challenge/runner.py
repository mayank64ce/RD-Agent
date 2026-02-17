"""
FHE Runner - Docker-based execution for FHE challenges.

FHERunner handles both black_box (challenge Dockerfile) and white_box
(yashalabinc/fherma-validator) challenge types.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from rdagent.core.developer import Developer
from rdagent.log import rdagent_logger as logger
from rdagent.scenarios.fhe_challenge.experiment import FHEExperiment


class FHERunner(Developer):
    """
    Runs FHE challenge experiments via Docker.

    Black Box:
        Copies challenge files to workspace, builds challenge's own Dockerfile,
        runs against each testcase, parses verifier output for accuracy.

    White Box:
        Copies template files to workspace/app_build/, runs fherma-validator
        Docker image, parses result.json for accuracy.
    """

    def __init__(self, scen, setting) -> None:
        super().__init__(scen)
        self.build_timeout: int = setting.build_timeout
        self.run_timeout: int = setting.run_timeout

    def develop(self, exp: FHEExperiment) -> FHEExperiment:
        ws = exp.experiment_workspace
        ws.prepare()

        if self.scen.challenge_type == "black_box":
            self._run_black_box(exp)
        else:
            self._run_white_box(exp)

        return exp

    # ------------------------------------------------------------------ #
    # Black Box                                                            #
    # ------------------------------------------------------------------ #

    def _run_black_box(self, exp: FHEExperiment) -> None:
        """
        Black box execution:
        1. Mirror challenge_dir layout in workspace (Dockerfile, CMakeLists, verifier + templates/)
        2. docker build
        3. docker run -v testcase:/data for each testcase
        4. Parse verifier output for accuracy
        """
        ws = exp.experiment_workspace
        workspace_path = ws.workspace_path
        challenge_dir = self.scen.challenge_dir

        # Copy root challenge files (Dockerfile, CMakeLists.txt, verifier.cpp, etc.)
        for item in challenge_dir.iterdir():
            if item.is_file():
                dest = workspace_path / item.name
                if not dest.exists():
                    shutil.copy2(item, dest)

        # Create templates/openfhe/ directory in workspace
        template_dir = workspace_path / "templates" / "openfhe"
        template_dir.mkdir(parents=True, exist_ok=True)

        # First copy all original template files
        src_template_dir = challenge_dir / "templates" / "openfhe"
        if src_template_dir.exists():
            for f in src_template_dir.iterdir():
                if f.is_file():
                    dest = template_dir / f.name
                    if not dest.exists():
                        shutil.copy2(f, dest)

        # Overwrite with generated files from workspace file_dict (yourSolution.cpp, config.json)
        for fname, content in ws.file_dict.items():
            (template_dir / fname).write_text(content)

        # Build Docker image
        image_tag = f"fhe-{self.scen.challenge_name}-{uuid.uuid4().hex[:8]}"
        logger.info(f"[FHERunner] Building Docker image: {image_tag}")
        build_cmd = ["docker", "build", "-t", image_tag, str(workspace_path)]
        build_output, build_rc = self._docker_run(build_cmd, self.build_timeout)

        if build_rc != 0:
            exp.build_success = False
            exp.error_message = f"Docker build failed (exit {build_rc}):\n{build_output[-3000:]}"
            exp.docker_output = build_output
            logger.warning(f"[FHERunner] Build failed for {image_tag}")
            return

        exp.build_success = True
        logger.info(f"[FHERunner] Build succeeded for {image_tag}")

        # Run against each testcase
        test_dir = challenge_dir / "tests"
        testcases = sorted([d for d in test_dir.iterdir() if d.is_dir()]) if test_dir.exists() else []

        if not testcases:
            exp.run_success = False
            exp.error_message = f"No testcase directories found in {test_dir}"
            exp.docker_output = build_output
            self._cleanup_image(image_tag)
            return

        total_accuracy = 0.0
        run_outputs: list[str] = []
        all_success = True

        for testcase in testcases:
            logger.info(f"[FHERunner] Running testcase: {testcase.name}")
            run_cmd = [
                "docker", "run", "--rm",
                "-v", f"{testcase.resolve()}:/data",
                image_tag,
            ]
            run_output, run_rc = self._docker_run(run_cmd, self.run_timeout)
            run_outputs.append(f"=== {testcase.name} ===\n{run_output}")

            if run_rc != 0:
                all_success = False
                exp.error_message += f"\nTestcase {testcase.name} failed (exit {run_rc}):\n{run_output[-800:]}"
            else:
                acc = self._parse_accuracy_black_box(run_output)
                if acc is not None:
                    total_accuracy += acc

        exp.run_success = all_success
        exp.docker_output = "\n\n".join(run_outputs)

        if testcases:
            exp.accuracy = total_accuracy / len(testcases)

        logger.info(f"[FHERunner] Accuracy: {exp.accuracy:.3f}" if exp.accuracy is not None else "[FHERunner] Accuracy: N/A")
        self._cleanup_image(image_tag)

    # ------------------------------------------------------------------ #
    # White Box                                                            #
    # ------------------------------------------------------------------ #

    def _run_white_box(self, exp: FHEExperiment) -> None:
        """
        White box execution:
        1. Copy template files to workspace/app_build/
        2. Overwrite with generated yourSolution.cpp (and optionally config.json)
        3. Symlink workspace/tests/ → challenge_dir/tests/
        4. docker run yashalabinc/fherma-validator
        5. Parse workspace/app_build/result.json for accuracy
        """
        ws = exp.experiment_workspace
        workspace_path = ws.workspace_path
        challenge_dir = self.scen.challenge_dir

        # Create app_build/ directory
        app_build = workspace_path / "app_build"
        app_build.mkdir(parents=True, exist_ok=True)

        # Copy original template files to app_build/
        src_template_dir = challenge_dir / "templates" / "openfhe"
        if src_template_dir.exists():
            for f in src_template_dir.iterdir():
                if f.is_file():
                    shutil.copy2(f, app_build / f.name)

        # Overwrite with generated files (yourSolution.cpp, optionally config.json)
        for fname, content in ws.file_dict.items():
            (app_build / fname).write_text(content)

        # Symlink tests/ → challenge_dir/tests/
        tests_link = workspace_path / "tests"
        if tests_link.exists() or tests_link.is_symlink():
            tests_link.unlink()
        tests_link.symlink_to((challenge_dir / "tests").resolve())

        # Run fherma-validator
        logger.info("[FHERunner] Running fherma-validator Docker image")
        run_cmd = [
            "docker", "run", "-t", "--rm",
            "-v", f"{workspace_path.resolve()}:/fherma",
            "yashalabinc/fherma-validator",
            "--project-folder=/fherma/app_build",
            "--testcase=/fherma/tests/test_case.json",
        ]
        run_output, run_rc = self._docker_run(run_cmd, self.run_timeout)
        exp.docker_output = run_output

        if run_rc != 0:
            # Determine if build or runtime failure
            lower_out = run_output.lower()
            if any(kw in lower_out for kw in ["cmake error", "compilation", "error:", "make[", "undefined reference"]):
                exp.build_success = False
                exp.run_success = False
                exp.error_message = f"Compilation/build error:\n{run_output[-3000:]}"
            else:
                exp.build_success = True
                exp.run_success = False
                exp.error_message = f"Runtime error (exit {run_rc}):\n{run_output[-3000:]}"
            logger.warning(f"[FHERunner] fherma-validator failed: {exp.error_message[:200]}")
            return

        exp.build_success = True
        exp.run_success = True

        # Parse result.json
        result_json = app_build / "result.json"
        if result_json.exists():
            exp.accuracy = self._parse_accuracy_white_box(result_json)
        else:
            # Fallback: parse from output
            exp.accuracy = self._parse_accuracy_from_output(run_output)

        logger.info(f"[FHERunner] Accuracy: {exp.accuracy:.3f}" if exp.accuracy is not None else "[FHERunner] Accuracy: N/A")

    # ------------------------------------------------------------------ #
    # Accuracy parsers                                                     #
    # ------------------------------------------------------------------ #

    def _parse_accuracy_black_box(self, output: str) -> float | None:
        """Parse verifier stdout for 'Accuracy: 0.NN' or 'Slots passed: X/Y'."""
        match = re.search(r"Accuracy:\s*([0-9.]+)", output)
        if match:
            return float(match.group(1))
        match = re.search(r"Slots passed:\s*(\d+)/(\d+)", output)
        if match:
            total = int(match.group(2))
            if total > 0:
                return int(match.group(1)) / total
        return None

    def _parse_accuracy_white_box(self, result_json_path: Path) -> float | None:
        """
        Parse fherma-validator result.json.
        Computes accuracy as (slots within error threshold) / (total slots).
        """
        try:
            data = json.loads(result_json_path.read_text())
            total_slots = 0
            correct_slots = 0
            for testcase in data.get("testcases", []):
                error_threshold = testcase.get("error_threshold", 0.01)
                for run in testcase.get("runs", []):
                    result = run.get("result", [])
                    expected = run.get("expected_output", [])
                    # Use run-level threshold if available
                    thresh = run.get("error_threshold", error_threshold)
                    for r, e in zip(result, expected):
                        total_slots += 1
                        if abs(float(r) - float(e)) <= thresh:
                            correct_slots += 1
            if total_slots > 0:
                return correct_slots / total_slots
        except Exception as exc:
            logger.warning(f"[FHERunner] Failed to parse result.json: {exc}")
        return None

    def _parse_accuracy_from_output(self, output: str) -> float | None:
        """Fallback: scan Docker output for accuracy pattern."""
        match = re.search(r"[Aa]ccuracy:\s*([0-9.]+)", output)
        if match:
            return float(match.group(1))
        return None

    # ------------------------------------------------------------------ #
    # Docker helpers                                                       #
    # ------------------------------------------------------------------ #

    def _docker_run(self, cmd: list[str], timeout: int) -> tuple[str, int]:
        """Run a Docker command and return (stdout+stderr, exit_code)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout + result.stderr
            return output, result.returncode
        except subprocess.TimeoutExpired:
            logger.warning(f"[FHERunner] Docker command timed out after {timeout}s: {' '.join(cmd[:3])}")
            return f"Docker command timed out after {timeout}s", 1
        except Exception as exc:
            logger.warning(f"[FHERunner] Docker command error: {exc}")
            return str(exc), 1

    def _cleanup_image(self, image_tag: str) -> None:
        """Remove a Docker image silently."""
        subprocess.run(["docker", "rmi", "-f", image_tag], capture_output=True)
