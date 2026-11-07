"""Check that wheat validation partitions do not invent experimental units."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crop_protection_ps.wheat_pairability import _FIELDS
from crop_protection_ps.wheat_split_contamination import (
    _fold_assignment,
    _recorded_keys,
    audit_wheat_split_data,
    audit_wheat_split_rows,
    main,
)

_ROOT = Path(__file__).resolve().parents[1]


def _row(
    trial: str,
    *,
    country: str = "TEST",
    latitude: str = "48.0",
    longitude: str = "1.8",
    observation_date: str = "2019-06-01",
    value: str = "1.0",
) -> dict[str, str]:
    """Build a complete synthetic source row; all response fields are opaque."""
    result = dict.fromkeys(_FIELDS, "NA")
    result.update(
        {
            "TrialId": trial,
            "Country": country,
            "Latitude": latitude,
            "Longitude": longitude,
            "Date": observation_date,
            "Treatment": "Untreated",
            "Value": value,
        }
    )
    return result


def _synthetic_rows() -> list[dict[str, str]]:
    """Include two trial IDs at one geocode and a reused geocode/year."""
    return [
        _row("1"),
        _row("2"),
        _row("3", longitude="2.0"),
        _row("4", longitude="2.1"),
        _row("5", longitude="2.2"),
        _row("6", longitude="2.3"),
        _row("7", longitude="2.3", observation_date="2020-06-01"),
    ]


def _scheme(report: dict[str, object], name: str) -> dict[str, object]:
    """Select one deterministic report scheme with a structural assertion."""
    schemes = report["schemes"]
    assert isinstance(schemes, list)
    return next(item for item in schemes if item["scheme"] == name)


def test_source_report_is_exactly_reproducible() -> None:
    computed = audit_wheat_split_data(_ROOT / "data")
    saved = json.loads((_ROOT / "results/external_wheat_split_contamination.json").read_text())
    assert computed == saved
    assert computed["source_rows"] == 2276
    assert computed["grouping_counts"] == {
        "trial_id": 76,
        "geocode_year": 65,
        "geocode": 56,
    }
    assert computed["fold_count"] == 5
    assert computed["cross_id_exact_record_signatures"] == 22
    assert computed["physical_trial_identity_verified"] is False
    assert computed["trial_level_treatment_effect_permitted"] is False


def test_rowwise_folds_overlap_every_recorded_source_group() -> None:
    report = audit_wheat_split_data(_ROOT / "data")
    row = _scheme(report, "row")
    assert row["fold_row_counts"] == [456, 455, 455, 455, 455]
    overlap = row["recorded_group_overlap"]
    assert all(
        counts["groups_spanning_folds"] == counts["distinct_recorded_groups"]
        and counts["rows_in_groups_spanning_folds"] == 2276
        for counts in overlap.values()
    )
    assert row["cross_id_exact_record_signatures_spanning_folds"] == 19


def test_trial_only_folds_leave_recorded_locations_across_folds() -> None:
    report = audit_wheat_split_data(_ROOT / "data")
    trial = _scheme(report, "trial_id")
    overlap = trial["recorded_group_overlap"]
    assert overlap["trial_id"]["groups_spanning_folds"] == 0
    assert overlap["geocode_year"]["groups_spanning_folds"] == 9
    assert overlap["geocode_year"]["rows_in_groups_spanning_folds"] == 522
    assert overlap["geocode"]["groups_spanning_folds"] == 10
    assert trial["cross_id_exact_record_signatures_spanning_folds"] == 22
    assert trial["rows_in_cross_id_exact_signatures_spanning_folds"] == 44


@pytest.mark.parametrize(
    ("scheme", "zero_overlap"),
    [
        ("geocode_year", ("trial_id", "geocode_year")),
        ("geocode", ("trial_id", "geocode_year", "geocode")),
    ],
)
def test_stronger_grouping_preserves_recorded_units(
    scheme: str, zero_overlap: tuple[str, ...]
) -> None:
    report = audit_wheat_split_data(_ROOT / "data")
    candidate = _scheme(report, scheme)
    assert sum(candidate["fold_row_counts"]) == 2276
    assert len(candidate["fold_row_counts"]) == 5
    assert all(count > 0 for count in candidate["fold_row_counts"])
    for level in zero_overlap:
        assert candidate["recorded_group_overlap"][level]["groups_spanning_folds"] == 0
    assert candidate["cross_id_exact_record_signatures_spanning_folds"] == 0


def test_grouped_assignment_is_deterministic_and_row_order_invariant() -> None:
    rows = _synthetic_rows()
    keys = _recorded_keys(rows)["geocode_year"]
    first = _fold_assignment(keys, fold_count=5, seed=72, group_aware=True)
    repeated = _fold_assignment(keys, fold_count=5, seed=72, group_aware=True)
    reverse = _fold_assignment(list(reversed(keys)), fold_count=5, seed=72, group_aware=True)
    assert first == repeated
    assert first == list(reversed(reverse))
    assert first[0] == first[1]  # Two trial IDs share the same rounded geocode/year.
    assert all(fold >= 0 for fold in first)


def test_raw_coordinate_spellings_are_canonicalized_without_extra_rounding() -> None:
    keys = _recorded_keys(_synthetic_rows())
    assert keys["geocode"][0] == keys["geocode"][1]
    assert keys["geocode_year"][0] == keys["geocode_year"][1]
    assert keys["geocode"][5] == keys["geocode"][6]
    assert keys["geocode_year"][5] != keys["geocode_year"][6]
    spellings = _recorded_keys([_row("1", latitude="48"), _row("2")])
    assert spellings["geocode"][0] == spellings["geocode"][1]


def test_exact_cross_id_matches_are_not_labeled_duplicate_plots() -> None:
    report = audit_wheat_split_rows(_synthetic_rows(), fold_count=5, seed=18)
    assert report["cross_id_exact_record_signatures"] == 1
    assert report["scientific_scope"] == "descriptive_validation_partition_structure_only"
    assert report["physical_trial_identity_verified"] is False
    assert _scheme(report, "geocode_year")["cross_id_exact_record_signatures_spanning_folds"] == 0


@pytest.mark.parametrize("fold_count", [0, 1, 8, True, "5"])
def test_invalid_fold_counts_fail_closed(fold_count: object) -> None:
    with pytest.raises(ValueError, match="fold_count"):
        audit_wheat_split_rows(_synthetic_rows(), fold_count=fold_count)


def test_group_shortage_and_invalid_seed_fail_closed() -> None:
    keys = _recorded_keys(_synthetic_rows())
    with pytest.raises(ValueError, match="fewer distinct"):
        _fold_assignment(keys["geocode"], fold_count=7, seed=0, group_aware=True)
    with pytest.raises(ValueError, match="seed"):
        _fold_assignment(keys["geocode"], fold_count=5, seed=True, group_aware=True)


@pytest.mark.parametrize(
    "bad_row",
    [
        {"TrialId": "1"},
        _row("1", latitude="48.03"),
        _row("1", observation_date="2019-14-01"),
    ],
)
def test_invalid_source_rows_are_rejected(bad_row: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        audit_wheat_split_rows([bad_row], fold_count=2)


def test_report_generation_and_read_only_check(tmp_path: Path) -> None:
    output = tmp_path / "wheat_split.json"
    args = ["--data-dir", str(_ROOT / "data"), "--output", str(output)]
    assert main(args) == 0
    baseline = output.read_bytes()
    assert main([*args, "--check"]) == 0
    assert output.read_bytes() == baseline
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main([*args, "--check"])
    assert exc.value.code == 1
