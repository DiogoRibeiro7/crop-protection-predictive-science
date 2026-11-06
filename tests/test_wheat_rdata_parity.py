"""Regression coverage for original RData/TSV parity and fail-closed identity."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from crop_protection_ps.wheat_rdata_parity import (
    _original_rdata_md5,
    audit_wheat_rdata_parity,
    compare_wheat_observation_frames,
    main,
)

_ROOT = Path(__file__).resolve().parents[1]
_BINARY = _ROOT / "data/external/zenodo_wheat_fungicide_6521175/basf-wheat-diseases.Rdata"


def _small_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construct ordered source-like rows with a single one-ULP conversion."""
    binary = pd.DataFrame(
        {
            "TrialId": pd.Categorical(["1", "2"]),
            "Date": [1.0, 2.0],
            "Value": [np.nextafter(86.090916, -np.inf), np.nan],
            "Treatment": pd.Categorical(["Untreated", "TreatmentA"]),
            "GsTo": [np.nan, 37.0],
        }
    )
    tsv = pd.DataFrame(
        {
            "TrialId": ["1", "2"],
            "Date": ["1970-01-02", "1970-01-03"],
            "Value": ["86.090916", "NA"],
            "Treatment": ["Untreated", "TreatmentA"],
            "GsTo": ["NA", "37"],
        }
    )
    return binary, tsv


def test_complete_published_binary_agrees_with_ordered_tsv() -> None:
    report = audit_wheat_rdata_parity(_ROOT / "data")
    saved = json.loads((_ROOT / "results/external_wheat_rdata_parity.json").read_text())
    assert report == saved
    assert _BINARY.stat().st_size == 23452
    assert report["binary_original_md5"] == _original_rdata_md5(_ROOT / "data")
    assert hashlib.md5(_BINARY.read_bytes()).hexdigest() == report["binary_original_md5"]
    assert report["original_r_objects"] == ["obs"]
    assert report["published_trial_count"] == 56
    assert report["source_trial_id_codes"] == 76
    assert report["comparison"]["rows_compared"] == 2276
    assert report["comparison"]["columns_compared"] == 17
    assert report["comparison"]["cells_compared"] == 38692
    assert report["comparison"]["rounding_only_difference_count"] == 1
    assert report["comparison"]["rounding_only_differences"][0]["source_line"] == 1161
    assert report["comparison"]["unexplained_mismatches"] == 0
    assert report["comparison"]["row_order_preserved"] is True
    assert report["additional_plot_or_trial_keys_found"] is False
    assert report["trial_identity_established"] is False
    assert report["model_permission"] == "requires_protocol"


def test_one_ulp_export_difference_and_missingness_are_explained() -> None:
    binary, tsv = _small_frames()
    result = compare_wheat_observation_frames(binary, tsv)
    assert result["cells_compared"] == 10
    assert result["rounding_only_difference_count"] == 1
    assert result["rounding_only_differences"][0]["column"] == "Value"
    assert result["rounding_only_differences"][0]["source_line"] == 2
    assert result["column_results"][2]["missing_in_both"] == 1
    assert result["column_results"][4]["missing_in_both"] == 1


def test_two_ulp_difference_must_fail() -> None:
    binary, tsv = _small_frames()
    binary.loc[0, "Value"] = np.nextafter(binary.loc[0, "Value"], -np.inf)
    with pytest.raises(ValueError, match="binary/TSV disagreement in Value"):
        compare_wheat_observation_frames(binary, tsv)


@pytest.mark.parametrize("change", ["reorder", "extra", "missing", "category", "date", "rows"])
def test_schema_and_exact_metadata_disagreement_fails(change: str) -> None:
    binary, tsv = _small_frames()
    if change == "reorder":
        tsv = tsv.iloc[::-1].reset_index(drop=True)
    elif change == "extra":
        tsv["extra_column"] = "extra"
    elif change == "missing":
        tsv.loc[0, "GsTo"] = "40"
    elif change == "category":
        tsv.loc[0, "Treatment"] = "Unknown"
    elif change == "date":
        tsv.loc[0, "Date"] = "1970-01-04"
    elif change == "rows":
        tsv = tsv.iloc[0:1].copy()
    with pytest.raises(ValueError):
        compare_wheat_observation_frames(binary, tsv)


def test_cli_writes_then_checks_hash_stable_artifact(tmp_path: Path) -> None:
    output = tmp_path / "wheat_rdata.json"
    args = ["--data-dir", str(_ROOT / "data"), "--output", str(output)]
    assert main(args) == 0
    expected = output.read_bytes()
    assert main([*args, "--check"]) == 0
    assert output.read_bytes() == expected
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as err:
        main([*args, "--check"])
    assert err.value.code == 1
