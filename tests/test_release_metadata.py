from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib

import crop_protection_ps


ROOT = Path(__file__).parents[1]
ORCID = "0009-0001-2022-7072"
ORCID_URI = f"https://orcid.org/{ORCID}"


def test_release_metadata_versions_agree() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    version = pyproject["project"]["version"]

    assert crop_protection_ps.__version__ == version

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert re.search(rf"^version:\s*{re.escape(version)}\s*$", citation, re.MULTILINE)
    assert f'orcid: "{ORCID_URI}"' in citation

    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    assert zenodo["version"] == version
    assert zenodo["upload_type"] == "software"
    assert zenodo["creators"][0]["orcid"] == ORCID

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^##\s+{re.escape(version)}(?:\s|$)", changelog, re.MULTILINE)
