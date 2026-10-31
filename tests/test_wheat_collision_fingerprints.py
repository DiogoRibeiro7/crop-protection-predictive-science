"""Regression tests for cross-TrialId overlaps at shared, rounded geocodes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crop_protection_ps.wheat_collision_fingerprints import (
    audit_wheat_collision_data,
    main,
    summarize_wheat_collisions,
)

_ROOT = Path(__file__).resolve().parents[1]


def _record(
    trial_id: str,
    *,
    date: str = "2019-05-12",
    latitude: str = "48.0",
    organism: str = "SEPTTR",
    treatment: str = "Untreated",
    sprays: str = "1",
    value: str = "0",
) -> dict[str, str]:
    """Construct a complete synthetic source row with a known assessment key."""
    return {
        "TrialId": trial_id,
        "Country": "TEST",
        "Latitude": latitude,
        "Longitude": "1.8",
        "Date": date,
        "Daft": "15",
        "GsFrom": "50",
        "GsTo": "55",
        "NumSprays": sprays,
        "Treatment": treatment,
        "Organism": organism,
        "Parameter": "INFECT",
        "Clarifier": "INFECT % NR",
        "Method": "P%INF",
        "SampleUnit": "TPLOT",
        "PlantPart": "LEAF, 1ST",
        "Value": value,
    }


def test_source_report_is_reproducible_and_finds_exact_record_overlap() -> None:
    actual = audit_wheat_collision_data(_ROOT / "data")
    saved = json.loads((_ROOT / "results/external_wheat_collision_fingerprints.json").read_text())
    assert actual == saved
    assert actual["source_rows"] == 2276
    assert actual["trial_id_count"] == 76
    assert actual["geocode_count"] == 56
    assert actual["geocode_year_count"] == 65
    assert actual["shared_geocode_year_count"] == 9
    assert actual["trial_ids_in_shared_geocode_years"] == 20
    assert actual["pairwise_comparison_count"] == 14
    assert actual["pairs_with_common_date"] == 10
    assert actual["pairs_with_common_assessment_signature"] == 3
    assert actual["pairs_with_identical_records_except_trial_id"] == 3
    assert actual["pairwise_identical_record_matches"] == 22


def test_identical_records_excluding_trial_id_are_counted_without_collapsing() -> None:
    rows = [_record("1"), _record("2")]
    summary = summarize_wheat_collisions(rows)
    pair = summary["shared_geocode_years"][0]["pairwise_comparisons"][0]
    assert pair["trial_ids"] == ["1", "2"]
    assert pair["shared_dates"] == ["2019-05-12"]
    assert pair["shared_assessment_signatures"] == 1
    assert pair["shared_arm_assessment_signatures"] == 1
    assert pair["identical_records_except_trial_id"] == 1
    assert summary == summarize_wheat_collisions(list(reversed(rows)))


@pytest.mark.parametrize(
    "changed",
    [
        {"value": "1"},
        {"sprays": "2"},
        {"treatment": "TreatmentA"},
    ],
)
def test_same_endpoint_is_not_necessarily_identical_record(changed: dict[str, str]) -> None:
    pair = summarize_wheat_collisions(
        [
            _record("1"),
            _record("2", **changed),
        ]
    )["shared_geocode_years"][0]["pairwise_comparisons"][0]
    assert pair["shared_assessment_signatures"] == 1
    assert pair["identical_records_except_trial_id"] == 0


def test_only_common_date_does_not_imply_common_endpoint() -> None:
    pair = summarize_wheat_collisions(
        [
            _record("1"),
            _record("2", organism="PUCCRT"),
        ]
    )["shared_geocode_years"][0]["pairwise_comparisons"][0]
    assert pair["shared_dates"] == ["2019-05-12"]
    assert pair["shared_assessment_signatures"] == 0
    assert pair["identical_records_except_trial_id"] == 0


def test_exact_record_overlap_uses_multiset_counts() -> None:
    summary = summarize_wheat_collisions([_record("1"), _record("1"), _record("2")])
    pair = summary["shared_geocode_years"][0]["pairwise_comparisons"][0]
    assert pair["identical_records_except_trial_id"] == 1


def test_separate_geocodes_or_years_are_not_compared_as_same_trial() -> None:
    report = summarize_wheat_collisions(
        [
            _record("1"),
            _record("2", latitude="48.1"),
            _record("3", date="2020-05-12"),
        ]
    )
    assert report["trial_id_count"] == 3
    assert report["shared_geocode_year_count"] == 0
    assert report["pairwise_comparison_count"] == 0


def test_incomplete_row_or_reused_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing endpoint metadata"):
        summarize_wheat_collisions([{k: v for k, v in _record("1").items() if k != "Value"}])
    with pytest.raises(ValueError, match="reused across geocodes or years"):
        summarize_wheat_collisions([_record("1"), _record("1", latitude="48.1")])


def test_cli_preserves_original_data_and_rejects_stale_reports(tmp_path: Path) -> None:
    report_path = tmp_path / "collision.json"
    args = ["--data-dir", str(_ROOT / "data"), "--output", str(report_path)]
    assert main(args) == 0
    original = report_path.read_bytes()
    assert main([*args, "--check"]) == 0
    assert report_path.read_bytes() == original
    report_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main([*args, "--check"])
    assert error.value.code == 1
