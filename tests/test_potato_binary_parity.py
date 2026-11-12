"""Offline scientific contract for potato RData/TSV source-format parity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from crop_protection_ps.potato_binary_parity import (
    BINARY_SHA256,
    BINARY_ZENODO_MD5,
    _check_original_binary,
    compare_potato_observation_frames,
)
from crop_protection_ps.potato_source_audit import SOURCE_COLUMNS, SOURCE_SHA256

_SAVED = Path(__file__).resolve().parents[1] / "results/real_potato_late_blight/binary_parity.json"


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Make two synthetically identical source representations with unused R levels."""
    binary = pd.DataFrame(
        {
            "Country": pd.Categorical(["UNITED KINGDOM", "IRELAND"]),
            "Latitude": [52.9, 53.1],
            "Longitude": [-1.5, -7.5],
            "Date": [0.0, 1.0],
            "CropStage": pd.Categorical(["65-71", "75"], categories=["65-71", "75", "BBCH"]),
            "Trial": pd.Categorical(["1", "1"], categories=["0", "1"]),
            "Plot": pd.Categorical(["103", "104"]),
            "Treatment": pd.Categorical(["2", "3"]),
            "Untreated": pd.Categorical(["0", "1"]),
            "Value": [0.0, 62.5],
        },
        index=[1, 2],
    )
    tsv = pd.DataFrame(
        {
            "Country": ["UNITED KINGDOM", "IRELAND"],
            "Latitude": ["52.9", "53.1"],
            "Longitude": ["-1.5", "-7.5"],
            "Date": ["1970-01-01", "1970-01-02"],
            "CropStage": ["65-71", "75"],
            "Trial": ["1", "1"],
            "Plot": ["103", "104"],
            "Treatment": ["2", "3"],
            "Untreated": ["0", "1"],
            "Value": ["0", "62.5"],
        }
    )
    return binary, tsv


def test_exact_row_column_date_and_factor_parity() -> None:
    """Compare numeric doubles exactly and retain unused R vocabulary."""
    binary, tsv = _frames()
    report = compare_potato_observation_frames(binary, tsv)
    assert report["rows_compared"] == 2
    assert report["columns_compared"] == len(SOURCE_COLUMNS)
    assert report["cells_compared"] == 20
    assert report["unexplained_mismatches"] == 0
    assert report["exact_numeric_parity"] is True
    assert report["row_order_preserved"] is True
    stages = next(item for item in report["factor_vocabulary"] if item["column"] == "CropStage")
    assert stages["declared_factor_levels"] == 3
    assert stages["observed_factor_levels"] == 2
    assert stages["unused_factor_labels"] == ["BBCH"]


@pytest.mark.parametrize(
    "change",
    [
        "row_reorder",
        "column_reorder",
        "extra_column",
        "removed_row",
        "factor_label",
        "numeric",
        "sub_ulp_numeric",
        "date",
        "empty_field",
        "factor_type",
        "fractional_date",
    ],
)
def test_source_format_mismatches_fail_closed(change: str) -> None:
    """Source export transformations cannot silently change any observed cell."""
    binary, tsv = _frames()
    if change == "row_reorder":
        tsv = tsv.iloc[::-1]
    elif change == "column_reorder":
        tsv = tsv[list(reversed(SOURCE_COLUMNS))]
    elif change == "extra_column":
        tsv["Endpoint"] = "yield"
    elif change == "removed_row":
        tsv = tsv.iloc[:1]
    elif change == "factor_label":
        tsv.loc[0, "Treatment"] = "4"
    elif change == "numeric":
        tsv.loc[0, "Value"] = "1.5"
    elif change == "sub_ulp_numeric":
        binary.loc[2, "Value"] = np.nextafter(62.5, np.inf)
    elif change == "date":
        tsv.loc[0, "Date"] = "1970-01-03"
    elif change == "empty_field":
        tsv.loc[0, "Country"] = ""
    elif change == "factor_type":
        binary["Trial"] = binary["Trial"].astype(str)
    elif change == "fractional_date":
        binary.loc[1, "Date"] = 1.5
    with pytest.raises(ValueError):
        compare_potato_observation_frames(binary, tsv)


def test_unrecognized_original_binary_is_rejected_before_deserialization(tmp_path: Path) -> None:
    """Fail checksum identity before handing bytes to the RData deserializer."""
    candidate = tmp_path / "tampered.Rdata"
    candidate.write_bytes(b"not the Zenodo original")
    with pytest.raises(ValueError, match="checksum"):
        _check_original_binary(candidate)


def test_pinned_binary_parity_artifact_does_not_promote_a_model() -> None:
    """Validate the offline audit without downloading or redistributing source rows."""
    report = json.loads(_SAVED.read_text(encoding="utf-8"))
    assert report["binary_original_md5"] == BINARY_ZENODO_MD5
    assert report["binary_sha256"] == BINARY_SHA256
    assert report["binary_size_bytes"] == 310_853
    assert report["text_sha256"] == SOURCE_SHA256
    assert report["r_objects"] == ["obs"]
    assert report["comparison"]["rows_compared"] == 127_034
    assert report["comparison"]["columns_compared"] == 10
    assert report["comparison"]["cells_compared"] == 1_270_340
    assert report["comparison"]["unexplained_mismatches"] == 0
    assert report["comparison"]["row_order_preserved"] is True
    assert report["comparison"]["exact_numeric_parity"] is True
    assert [item["column"] for item in report["comparison"]["column_results"]] == list(
        SOURCE_COLUMNS
    )
    assert all(item["mismatches"] == 0 for item in report["comparison"]["column_results"])
    factors = {item["column"]: item for item in report["comparison"]["factor_vocabulary"]}
    assert len(factors) == 6
    assert factors["Trial"]["unused_factor_labels"] == ["0"]
    assert factors["Plot"]["unused_factor_labels"] == ["44", "55", "56"]
    assert factors["CropStage"]["declared_factor_levels"] == 89
    assert factors["CropStage"]["observed_factor_levels"] == 79
    assert "BBCH" in factors["CropStage"]["unused_factor_labels"]
    assert report["source_duplicate_excess_rows_reproduced_in_both_formats"] == 118_021
    assert report["source_signatures_repeated_100x_reproduced_in_both_formats"] == 1_192
    assert report["unrepresented_endpoint_columns_found"] is False
    assert report["experiment_identifiers_reconciled"] is False
    assert report["model_permission"] == "requires_protocol"
