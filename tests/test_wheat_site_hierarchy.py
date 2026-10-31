"""Regression tests for the physical-site versus TrialId ambiguity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crop_protection_ps.wheat_pairability import audit_wheat_data
from crop_protection_ps.wheat_site_hierarchy import (
    audit_wheat_site_data,
    audit_wheat_site_rows,
    main,
)

_ROOT = Path(__file__).resolve().parents[1]


def _row(
    trial_id: str,
    *,
    country: str = "TEST",
    latitude: str = "48",
    longitude: str = "1.8",
    date: str = "2019-06-01",
) -> dict[str, str]:
    """Provide only metadata required to test geocode nesting."""
    return {
        "TrialId": trial_id,
        "Country": country,
        "Latitude": latitude,
        "Longitude": longitude,
        "Date": date,
    }


def test_report_reconstructs_original_76_65_56_counts() -> None:
    audit = audit_wheat_site_data(_ROOT / "data")
    saved = json.loads((_ROOT / "results/external_wheat_site_hierarchy.json").read_text())
    assert audit == saved
    assert audit["source_rows"] == 2276
    assert audit["trial_id_count"] == 76
    assert audit["geocode_year_count"] == 65
    assert audit["geocode_count"] == 56
    assert audit["geocode_precision_degrees"] == "0.1"
    assert audit["geocode_year_trial_multiplicity"] == {"1": 56, "2": 8, "4": 1}
    assert audit["geocode_years_per_geocode"] == {"1": 48, "2": 7, "3": 1}
    assert audit["geocode_years_with_multiple_trial_ids"] == 9
    assert audit["trial_ids_at_shared_geocode_years"] == 20
    assert audit["geocodes_reused_across_years"] == 8
    assert len(audit["shared_geocode_years"]) == 9
    assert len(audit["all_geocodes"]) == 56


def test_reconstruction_agrees_with_existing_endpoint_audit() -> None:
    hierarchy = audit_wheat_site_data(_ROOT / "data")
    endpoints = audit_wheat_data(_ROOT / "data")
    assert hierarchy["source_sha256"] == endpoints["source_sha256"]
    assert hierarchy["source_rows"] == endpoints["source_rows"]
    assert hierarchy["trial_id_count"] == endpoints["trial_id_count"]


def test_same_geocode_across_rows_and_years_is_not_a_unique_trial() -> None:
    rows = [
        _row("2", latitude="48.0"),
        _row("1"),
        _row("3", date="2020-07-10"),
        _row("1", date="2019-07-10"),
    ]
    report = audit_wheat_site_rows(rows)
    assert report["trial_id_count"] == 3
    assert report["geocode_count"] == 1
    assert report["geocode_year_count"] == 2
    assert report["geocode_year_trial_multiplicity"] == {"1": 1, "2": 1}
    assert report["shared_geocode_years"][0]["trial_ids"] == ["1", "2"]
    assert report["geocodes_reused_across_years"] == 1
    assert report == audit_wheat_site_rows(list(reversed(rows)))


def test_country_and_one_tenth_degree_are_distinct_grouping_keys() -> None:
    rows = [
        _row("1"),
        _row("2", country="ANOTHER"),
        _row("3", longitude="1.9"),
    ]
    report = audit_wheat_site_rows(rows)
    assert report["trial_id_count"] == report["geocode_count"] == 3
    assert report["geocode_years_with_multiple_trial_ids"] == 0


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("TrialId", "invalid"),
        ("Country", ""),
        ("Latitude", "91"),
        ("Latitude", "NaN"),
        ("Latitude", "48.05"),
        ("Longitude", "181"),
        ("Longitude", "abc"),
        ("Date", "2019-13-01"),
    ],
)
def test_invalid_site_metadata_fails_closed(field: str, invalid: str) -> None:
    with pytest.raises(ValueError):
        audit_wheat_site_rows([{**_row("1"), field: invalid}])


def test_reused_trial_id_must_keep_one_geocode_and_year() -> None:
    for second in (
        _row("1", longitude="1.9"),
        _row("1", date="2020-06-01"),
        _row("1", country="ANOTHER"),
    ):
        with pytest.raises(ValueError, match="reused across geocodes or years"):
            audit_wheat_site_rows([_row("1"), second])


def test_empty_or_incomplete_rows_are_rejected() -> None:
    with pytest.raises(ValueError, match="no wheat field observations"):
        audit_wheat_site_rows([])
    with pytest.raises(ValueError, match="missing site metadata"):
        audit_wheat_site_rows([{"TrialId": "1"}])


def test_cli_detects_stale_or_missing_derived_report(tmp_path: Path) -> None:
    output = tmp_path / "wheat_hierarchy.json"
    args = ["--data-dir", str(_ROOT / "data"), "--output", str(output)]
    assert main(args) == 0
    baseline = output.read_bytes()
    assert main([*args, "--check"]) == 0
    assert output.read_bytes() == baseline
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main([*args, "--check"])
    assert error.value.code == 1
