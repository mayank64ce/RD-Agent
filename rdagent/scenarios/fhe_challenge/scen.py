"""
FHE Challenge Scenario for RD-Agent.

Supports BLACK_BOX and WHITE_BOX_OPENFHE challenge types from the fhe_challenge/ directory.
"""

from __future__ import annotations

import re
from pathlib import Path

from rdagent.core.scenario import Scenario


class FHEScenario(Scenario):
    """
    Scenario for FHE challenges from the fhe_challenge/ directory.

    Reads challenge.md, detects challenge type, loads template files, and extracts
    C++ variable names for use in LLM prompts.
    """

    def __init__(self, challenge_dir: str) -> None:
        self.challenge_dir = Path(challenge_dir).resolve()
        if not self.challenge_dir.exists():
            raise ValueError(f"Challenge directory does not exist: {self.challenge_dir}")

        challenge_md_path = self.challenge_dir / "challenge.md"
        if not challenge_md_path.exists():
            raise ValueError(f"challenge.md not found in {self.challenge_dir}")

        self.challenge_md: str = challenge_md_path.read_text()
        self.challenge_name: str = self.challenge_dir.name
        self.challenge_type: str = self._detect_type()
        self.template_files: dict[str, str] = self._load_templates()
        self.variable_names: dict[str, str] = self._extract_variable_names()

    def _detect_type(self) -> str:
        """Detect challenge type from challenge.md: 'Black Box' → black_box, else white_box."""
        if re.search(r"Challenge type:\s*Black Box", self.challenge_md, re.IGNORECASE):
            return "black_box"
        return "white_box"

    def _load_templates(self) -> dict[str, str]:
        """Load all files from templates/openfhe/ as {filename: content}."""
        template_dir = self.challenge_dir / "templates" / "openfhe"
        result: dict[str, str] = {}
        if template_dir.exists():
            for f in sorted(template_dir.iterdir()):
                if f.is_file():
                    result[f.name] = f.read_text()
        return result

    def _extract_variable_names(self) -> dict[str, str]:
        """
        Regex on yourSolution.h to extract C++ member variable names.
        Returns dict with keys: cc, pk, input, output (where found).
        """
        header = self.template_files.get("yourSolution.h", "")
        names: dict[str, str] = {}

        cc_match = re.search(r"CryptoContext<DCRTPoly>\s+(\w+)", header)
        if cc_match:
            names["cc"] = cc_match.group(1)

        pk_match = re.search(r"PublicKey<DCRTPoly>\s+(\w+)", header)
        if pk_match:
            names["pk"] = pk_match.group(1)

        ct_matches = re.findall(r"Ciphertext<DCRTPoly>\s+(\w+)", header)
        if ct_matches:
            names["input"] = ct_matches[0]
            if len(ct_matches) > 1:
                names["output"] = ct_matches[-1]

        return names

    @property
    def background(self) -> str:
        return self.challenge_md

    def get_scenario_all_desc(
        self,
        task=None,
        filtered_tag: str | None = None,
        simple_background: bool | None = None,
    ) -> str:
        """Return challenge_md + formatted template files content."""
        desc = f"# FHE Challenge: {self.challenge_name}\n\n{self.challenge_md}\n\n"
        if self.template_files:
            desc += "## Template Files\n\n"
            for fname, content in self.template_files.items():
                desc += f"### {fname}\n```cpp\n{content}\n```\n\n"
        return desc

    def get_runtime_environment(self) -> str:
        return "OpenFHE C++ library, Docker container (fherma-validator or challenge Dockerfile)"

    @property
    def rich_style_description(self) -> str:
        return f"FHE Challenge: {self.challenge_name} ({self.challenge_type})"
