"""
Configuration for the FHE challenge RD-Agent loop.

All settings can be overridden via environment variables with FHE_ prefix.
Example: FHE_CHALLENGE_DIR=/path/to/challenge FHE_MAX_LOOPS=10
"""

from __future__ import annotations

from pydantic_settings import SettingsConfigDict

from rdagent.components.workflow.conf import BasePropSetting


class FHEPropSetting(BasePropSetting):
    """
    Settings for the FHE challenge agent loop.

    Environment variable prefix: FHE_
    """

    model_config = SettingsConfigDict(env_prefix="FHE_", protected_namespaces=())

    # Challenge to run
    challenge_dir: str = ""
    """Path to the FHE challenge directory (must contain challenge.md and templates/)"""

    # Docker timeouts
    build_timeout: int = 600
    """Docker build timeout in seconds (default: 10 minutes)"""

    run_timeout: int = 600
    """Docker run timeout in seconds (default: 10 minutes)"""

    # Loop control
    max_loops: int = 20
    """Maximum number of RD loops to run"""

    # Accuracy threshold
    accuracy_threshold: float = 0.8
    """Minimum accuracy (0.0–1.0) for experiment to be considered successful"""


FHE_SETTING = FHEPropSetting()
