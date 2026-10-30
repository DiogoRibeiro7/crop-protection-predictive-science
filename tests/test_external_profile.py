"""Regression checks for deterministic profiles of untouched public source data."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from crop_protection_ps.external_profile import main, profile_external_data

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_PROFILE_PATH = _DATA_DIR / "external" / "profile.json"


def _tables(profile: dict[str, Any], source_id: str) -> dict[str, dict[str, Any]]:
    """Return the observation and documentation sheets indexed by sheet name."""
    source = next(item for item in profile["sources"] if item["id"] == source_id)
    return {
        table["name"]: table
        for file in source["files"]
        for table in file["tables"]
    }


def _field(table: dict[str, Any], name: str) -> dict[str, Any]:
    return next(field for field in table["fields"] if field["name"] == name)


def test_committed_profile_matches_all_original_sources() -> None:
    actual = profile_external_data(_DATA_DIR)
    expected = json.loads(_PROFILE_PATH.read_text(encoding="utf-8"))
    assert actual == expected
    manifest_bytes = (_DATA_DIR / "external" / "manifest.json").read_bytes()
    assert actual["manifest_sha256"] == hashlib.sha256(manifest_bytes).hexdigest()


def test_wheat_profile_distinguishes_rows_from_trial_identifiers() -> None:
    table = _tables(profile_external_data(_DATA_DIR), "zenodo_wheat_fungicide_6521175")
    wheat = table["basf-wheat-diseases.txt"]
    assert (wheat["rows"], wheat["columns"]) == (2276, 17)
    assert _field(wheat, "TrialId")["distinct_nonblank"] == 76
    assert sum(field["literal_na_cells"] for field in wheat["fields"]) == 1101
    assert sum(field["missing_cells"] for field in wheat["fields"]) == 0


def test_aphid_profile_preserves_five_distinct_experiments() -> None:
    tables = _tables(profile_external_data(_DATA_DIR), "zenodo_aphid_pesticide_19805135")
    assert {name: table["rows"] for name, table in tables.items()} == {
        "Experiment1": 36,
        "Experiment2": 24,
        "Experiment3": 180,
        "Experiment4": 36,
        "Experiment5": 54,
    }
    assert all(table["role"] == "observations" for table in tables.values())


def test_dryad_readme_sheets_are_documentation_not_observations() -> None:
    source = next(
        item for item in profile_external_data(_DATA_DIR)["sources"]
        if item["id"] == "dryad_pathogen_temperature_4mw6m90jv"
    )
    tables = [table for file in source["files"] for table in file["tables"]]
    assert sum(table["role"] == "observations" for table in tables) == 12
    assert sum(table["role"] == "documentation" for table in tables) == 10
    field = next(table for table in tables if table["name"] == "Sheet1")
    assert (field["rows"], field["columns"]) == (178, 124)
    assert sum(col["missing_cells"] for col in field["fields"]) == 5326


def test_profile_rejects_corrupted_external_source(tmp_path: Path) -> None:
    copy = tmp_path / "external"
    shutil.copytree(_DATA_DIR / "external", copy)
    wheat = copy / "zenodo_wheat_fungicide_6521175" / "basf-wheat-diseases.txt"
    with wheat.open("ab") as handle:
        handle.write(b"changed\n")
    with pytest.raises(ValueError, match="external source integrity failed"):
        profile_external_data(tmp_path)


def test_cli_check_is_read_only_and_detects_stale_profile(tmp_path: Path) -> None:
    output = tmp_path / "profile.json"
    arguments = ["--data-dir", str(_DATA_DIR), "--output", str(output)]
    assert main(arguments) == 0
    original = output.read_bytes()
    assert main([*arguments, "--check"]) == 0
    assert output.read_bytes() == original
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main([*arguments, "--check"])
    assert error.value.code == 1
