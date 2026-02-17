"""
FHE Experiment, Task, and Workspace abstractions.

FHETask       - a single eval() implementation task
FHEWorkspace  - file-based workspace for template + generated code
FHEExperiment - holds task, workspace, and Docker run results
"""

from __future__ import annotations

from rdagent.core.experiment import Experiment, FBWorkspace, Task


class FHETask(Task):
    """A single FHE eval() implementation task."""

    def __init__(self, algorithm_plan: str) -> None:
        super().__init__(name="eval_implementation", description=algorithm_plan)
        self.algorithm_plan: str = algorithm_plan

    def get_task_information(self) -> str:
        return f"FHE eval() implementation\nAlgorithm Plan:\n{self.algorithm_plan}"


class FHEWorkspace(FBWorkspace):
    """File-based workspace holding template files + generated eval() body."""

    pass


class FHEExperiment(Experiment):
    """
    Holds one FHETask and results from Docker execution.

    Attributes
    ----------
    docker_output : str
        Combined stdout+stderr from the Docker build/run.
    build_success : bool
        True if Docker build succeeded.
    run_success : bool
        True if Docker run succeeded (solution ran without error).
    accuracy : float | None
        Parsed accuracy score (0.0–1.0), or None if not available.
    error_message : str
        Error text for build/run failures.
    """

    def __init__(self, tasks: list[FHETask], hypothesis=None) -> None:
        super().__init__(sub_tasks=tasks, hypothesis=hypothesis)
        self.experiment_workspace: FHEWorkspace = FHEWorkspace()
        self.docker_output: str = ""
        self.build_success: bool = False
        self.run_success: bool = False
        self.accuracy: float | None = None
        self.error_message: str = ""
