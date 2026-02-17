"""
FHE Challenge RD-Agent Loop.

FHERDLoop orchestrates the Research Agent → Developer Agent → Docker Runner → Evaluator cycle
for FHE challenges. Each loop iteration:
  1. direct_exp_gen: Research Agent proposes an algorithm plan
  2. coding:         Developer Agent generates eval() C++ code
  3. running:        Docker Runner executes the solution
  4. feedback:       Evaluator assesses accuracy
  5. record:         Appends (experiment, feedback) to trace history

Usage:
    rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_max
    rdagent fhe_challenge --challenge-dir ../fhe_challenge/black_box/challenge_relu --loop-n 5
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

import fire
import typer
from typing_extensions import Annotated

from rdagent.app.fhe_challenge.conf import FHE_SETTING, FHEPropSetting
from rdagent.core.exception import CoderError
from rdagent.core.proposal import ExperimentFeedback, Trace
from rdagent.log import rdagent_logger as logger
from rdagent.scenarios.fhe_challenge.developer import FHECoder
from rdagent.scenarios.fhe_challenge.evaluator import FHEEvaluator
from rdagent.scenarios.fhe_challenge.experiment import FHEExperiment
from rdagent.scenarios.fhe_challenge.proposal import FHEExpGen
from rdagent.scenarios.fhe_challenge.runner import FHERunner
from rdagent.scenarios.fhe_challenge.scen import FHEScenario
from rdagent.utils.workflow import LoopBase, LoopMeta


class FHERDLoop(LoopBase, metaclass=LoopMeta):
    """
    RD loop for FHE challenges.

    Steps (in order): direct_exp_gen → coding → running → feedback → record

    skip_loop_error: CoderError → skips to record() with exception feedback
    """

    skip_loop_error = (CoderError,)

    def __init__(self, setting: FHEPropSetting) -> None:
        if not setting.challenge_dir:
            raise ValueError("FHEPropSetting.challenge_dir must be set before creating FHERDLoop")

        self.scen = FHEScenario(setting.challenge_dir)
        logger.log_object(self.scen, tag="scenario")
        logger.log_object(setting.model_dump(), tag="FHE_SETTINGS")

        self.exp_gen = FHEExpGen(self.scen)
        self.coder = FHECoder(self.scen)
        self.runner = FHERunner(self.scen, setting)
        self.evaluator = FHEEvaluator(self.scen, accuracy_threshold=setting.accuracy_threshold)
        self.trace = Trace(scen=self.scen)

        super().__init__()

    # ------------------------------------------------------------------ #
    # Loop steps                                                           #
    # ------------------------------------------------------------------ #

    async def direct_exp_gen(self, prev_out: dict[str, Any]) -> FHEExperiment:
        """Step 1: Research Agent proposes algorithm, generates FHEExperiment."""
        # Wait for any parallel loops to finish before generating (sequential mode)
        from rdagent.core.conf import RD_AGENT_SETTINGS

        while True:
            if self.get_unfinished_loop_cnt(self.loop_idx) < RD_AGENT_SETTINGS.get_max_parallel():
                exp = self.exp_gen.gen(self.trace)
                logger.log_object(exp, tag="experiment")
                return exp
            await asyncio.sleep(1)

    def coding(self, prev_out: dict[str, Any]) -> FHEExperiment:
        """Step 2: Developer Agent generates eval() C++ code."""
        exp: FHEExperiment = prev_out["direct_exp_gen"]
        exp = self.coder.develop(exp)
        logger.log_object(exp, tag="coded_experiment")
        return exp

    def running(self, prev_out: dict[str, Any]) -> FHEExperiment:
        """Step 3: Docker Runner executes the solution."""
        exp: FHEExperiment = prev_out["coding"]
        exp = self.runner.develop(exp)
        logger.log_object(exp, tag="run_experiment")
        return exp

    def feedback(self, prev_out: dict[str, Any]) -> ExperimentFeedback:
        """Step 4: Evaluator generates feedback from Docker results."""
        e = prev_out.get(self.EXCEPTION_KEY)
        if e is not None:
            fb = ExperimentFeedback.from_exception(e)
        else:
            exp: FHEExperiment = prev_out["running"]
            fb = self.evaluator.generate_feedback(exp, self.trace)
        logger.log_object(fb, tag="feedback")
        return fb

    def record(self, prev_out: dict[str, Any]) -> None:
        """Step 5: Append (experiment, feedback) to trace history."""
        e = prev_out.get(self.EXCEPTION_KEY)

        # Get the best available experiment object
        if e is not None:
            # When CoderError skips to record, running/coding may be None
            exp = (
                prev_out.get("running")
                or prev_out.get("coding")
                or prev_out.get("direct_exp_gen")
            )
        else:
            exp = prev_out.get("running") or prev_out.get("coding")

        fb: ExperimentFeedback = prev_out["feedback"]

        if exp is not None:
            self.trace.hist.append((exp, fb))
            # Maintain simple dag_parent (all as root nodes for simplicity)
            self.trace.dag_parent.append(())

        logger.log_object(self.trace, tag="trace")

        # Log best accuracy so far
        sota_hyp, sota_exp = self.trace.get_sota_hypothesis_and_experiment()
        if sota_exp is not None and hasattr(sota_exp, "accuracy"):
            logger.info(f"[FHERDLoop] Best accuracy so far: {sota_exp.accuracy:.4f}")


# --------------------------------------------------------------------------- #
# CLI entry point                                                              #
# --------------------------------------------------------------------------- #


def main(
    challenge_dir: str = "",
    path: Optional[str] = None,
    checkout: Annotated[bool, typer.Option("--checkout/--no-checkout", "-c/-C")] = True,
    step_n: Optional[int] = None,
    loop_n: Optional[int] = None,
    build_timeout: int = 600,
    run_timeout: int = 600,
    accuracy_threshold: float = 0.8,
) -> None:
    """
    Run FHE challenge agent.

    Parameters
    ----------
    challenge_dir :
        Path to the FHE challenge directory (must contain challenge.md).
    path :
        Resume from checkpoint, e.g. ``$LOG_PATH/__session__/1/0_direct_exp_gen``.
    checkout :
        If resuming, whether to clear logs after the checkpoint.
    step_n :
        Maximum number of steps to run.
    loop_n :
        Maximum number of loops (iterations) to run.
    build_timeout :
        Docker build timeout in seconds.
    run_timeout :
        Docker run timeout in seconds.
    accuracy_threshold :
        Accuracy threshold (0.0–1.0) for considering a solution successful.

    Examples
    --------
    .. code-block:: bash

        # White box challenge
        rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_max

        # Black box challenge with loop limit
        rdagent fhe_challenge --challenge-dir ../fhe_challenge/black_box/challenge_relu --loop-n 5

        # Resume from checkpoint
        rdagent fhe_challenge --challenge-dir ... --path log/__session__/2/1_coding
    """
    if challenge_dir:
        FHE_SETTING.challenge_dir = challenge_dir
    if build_timeout != 600:
        FHE_SETTING.build_timeout = build_timeout
    if run_timeout != 600:
        FHE_SETTING.run_timeout = run_timeout
    if accuracy_threshold != 0.8:
        FHE_SETTING.accuracy_threshold = accuracy_threshold

    if not FHE_SETTING.challenge_dir:
        raise ValueError(
            "Please specify --challenge-dir or set FHE_CHALLENGE_DIR environment variable.\n"
            "Example: rdagent fhe_challenge --challenge-dir ../fhe_challenge/white_box/openfhe/challenge_max"
        )

    if path is None:
        loop = FHERDLoop(FHE_SETTING)
    else:
        loop = FHERDLoop.load(path, checkout=checkout)

    asyncio.run(loop.run(step_n=step_n, loop_n=loop_n))


if __name__ == "__main__":
    fire.Fire(main)
