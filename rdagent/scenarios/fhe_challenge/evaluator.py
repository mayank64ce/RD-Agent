"""
FHE Evaluator - generates ExperimentFeedback from Docker run results.
"""

from __future__ import annotations

from rdagent.core.proposal import Experiment2Feedback, ExperimentFeedback, Trace
from rdagent.log import rdagent_logger as logger
from rdagent.scenarios.fhe_challenge.experiment import FHEExperiment

# Default accuracy threshold (80% slots within error tolerance = pass)
DEFAULT_ACCURACY_THRESHOLD = 0.8


class FHEEvaluator(Experiment2Feedback):
    """
    Generates ExperimentFeedback from an executed FHEExperiment.

    decision=True  → accuracy >= accuracy_threshold (challenge solved!)
    decision=False → build/run failure or accuracy too low
    """

    def __init__(self, scen, accuracy_threshold: float = DEFAULT_ACCURACY_THRESHOLD) -> None:
        super().__init__(scen)
        self.accuracy_threshold = accuracy_threshold

    def generate_feedback(self, exp: FHEExperiment, trace: Trace) -> ExperimentFeedback:
        # Build failure
        if not exp.build_success:
            reason = (
                f"Build failed.\n\n"
                f"Error:\n{exp.error_message[:2000]}\n\n"
                f"Docker output (last 1000 chars):\n{exp.docker_output[-1000:]}"
            )
            logger.info(f"[FHEEvaluator] Build failed: {exp.error_message[:100]}")
            return ExperimentFeedback(reason=reason, decision=False)

        # Runtime failure
        if not exp.run_success:
            reason = (
                f"Runtime error.\n\n"
                f"Error:\n{exp.error_message[:2000]}\n\n"
                f"Docker output (last 1000 chars):\n{exp.docker_output[-1000:]}"
            )
            logger.info(f"[FHEEvaluator] Run failed: {exp.error_message[:100]}")
            return ExperimentFeedback(reason=reason, decision=False)

        # Accuracy check
        accuracy = exp.accuracy
        if accuracy is None:
            reason = (
                f"Run succeeded but accuracy could not be parsed.\n\n"
                f"Docker output (last 1000 chars):\n{exp.docker_output[-1000:]}"
            )
            logger.warning("[FHEEvaluator] Accuracy not parsed from output")
            return ExperimentFeedback(reason=reason, decision=False)

        passed = accuracy >= self.accuracy_threshold
        status = "PASSED" if passed else "FAILED"

        reason = (
            f"Accuracy: {accuracy:.4f} ({accuracy * 100:.1f}%)\n"
            f"Threshold: {self.accuracy_threshold:.2f} ({self.accuracy_threshold * 100:.0f}%)\n"
            f"Status: {status}\n\n"
            f"Docker output (last 2000 chars):\n{exp.docker_output[-2000:]}"
        )

        # Add comparison with previous best
        sota_hyp, sota_exp = trace.get_sota_hypothesis_and_experiment()
        if sota_exp is not None and hasattr(sota_exp, "accuracy") and sota_exp.accuracy is not None:
            reason += f"\n\nPrevious best accuracy: {sota_exp.accuracy:.4f}"

        logger.info(f"[FHEEvaluator] {status}: accuracy={accuracy:.4f} (threshold={self.accuracy_threshold:.2f})")
        return ExperimentFeedback(reason=reason, decision=passed)
