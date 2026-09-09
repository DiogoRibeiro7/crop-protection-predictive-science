from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import crop_protection_ps


ROOT = Path(__file__).parents[1]


def test_release_metadata_versions_agree() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    version = pyproject["project"]["version"]

    assert crop_protection_ps.__version__ == version

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert re.search(rf"^version:\s*{re.escape(version)}\s*$", citation, re.MULTILINE)

    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    assert zenodo["version"] == version
    assert zenodo["upload_type"] == "software"

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^##\s+{re.escape(version)}(?:\s|$)", changelog, re.MULTILINE)
