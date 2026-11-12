"""Regression contracts for the non-inferential potato late-blight intake."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from crop_protection_ps.potato_source_audit import (
    SOURCE_COLUMNS,
    SOURCE_SHA256,
    SOURCE_ZENODO_MD5,
    audit_potato_source,
    write_potato_audit,
)

RESULTS = Path(__file__).resolve().parents[1] / "results/real_potato_late_blight/source_audit"


def _record(**changes: str) -> dict[str, str]:
    """Construct one toy assessment with explicit literal source identifiers."""
    record = {
        "Country": "United Kingdom",
        "Latitude": "52.0",
        "Longitude": "-1.0",
        "Date": "2016-07-10",
        "CropStage": "65-71",
        "Trial": "1",
        "Plot": "2",
        "Treatment": "1",
        "Untreated": "0",
        "Value": "25.0",
    }
    record.update(changes)
    return record


def _write_source(path: Path, records: list[dict[str, str]]) -> None:
    """Write an unvendored stand-in for the upstream TSV in a temporary directory."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SOURCE_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(records)


def test_multiplicity_is_not_interpreted_as_independent_plot_replication(
    tmp_path: Path,
) -> None:
    """Repeated source lines inflate row counts but not provisional plots."""
    source = tmp_path / "sample.tsv"
    treated = _record()
    untreated = _record(Plot="3", Untreated="1", Treatment="1", Value="45")
    second_site = _record(
        Country="Ireland", Latitude="53.2", Longitude="-7.1", Trial="1", Plot="2"
    )
    _write_source(source, [*([treated] * 100), untreated, second_site])

    audit = audit_potato_source(source, verify_source=False)
    assert audit.summary["original_source_rows"] == 102
    assert audit.summary["distinct_complete_row_signatures"] == 3
    assert audit.summary["exact_repeat_excess_rows"] == 99
    assert audit.summary["signatures_repeated_100_times"] == 1
    assert audit.summary["site_year_geocode_cells"] == 2
    assert audit.summary["site_year_trial_code_cells"] == 2
    assert audit.summary["distinct_trial_code_labels"] == 1
    assert audit.summary["candidate_plot_keys"] == 3
    assert audit.summary["distinct_assessment_event_keys"] == 3
    assert audit.summary["event_keys_with_different_recorded_values"] == 0
    assert sum(item["untreated_plot_ids"] for item in audit.sites) == 1


def test_conflicting_observations_are_reported_and_never_averaged(tmp_path: Path) -> None:
    """An apparent event collision must remain an unresolved ambiguity."""
    source = tmp_path / "collision.tsv"
    _write_source(source, [_record(Value="10"), _record(Value="15"), _record(Value="15")])

    audit = audit_potato_source(source, verify_source=False)
    assert audit.summary["exact_repeat_excess_rows"] == 1
    assert audit.summary["distinct_assessment_event_keys"] == 1
    assert audit.summary["event_keys_with_different_recorded_values"] == 1
    assert audit.conflicting_events[0]["distinct_recorded_values"] == 2
    assert audit.years[0]["event_keys_with_different_values"] == 1

    first = tmp_path / "first"
    second = tmp_path / "second"
    write_potato_audit(audit, first)
    write_potato_audit(audit, second)
    assert (first / "summary.json").read_bytes() == (second / "summary.json").read_bytes()
    assert (first / "conflicting_events.csv").read_bytes() == (
        second / "conflicting_events.csv"
    ).read_bytes()
    # The export contains candidate event identifiers and counts, never source responses.
    with (first / "conflicting_events.csv").open(encoding="utf-8", newline="") as handle:
        assert "Value" not in csv.DictReader(handle).fieldnames


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"Date": "not-a-date"}, "invalid Date"),
        ({"Latitude": "Infinity"}, "outside finite range"),
        ({"Longitude": "181"}, "outside finite range"),
        ({"Value": "NaN"}, "outside finite range"),
        ({"Value": "101"}, "outside finite range"),
        ({"Trial": "1.5"}, "positive integer"),
        ({"Plot": "0"}, "positive integer"),
        ({"Treatment": "0"}, "positive integer"),
        ({"Untreated": "2"}, "invalid Untreated"),
        ({"Country": ""}, "missing or malformed"),
        ({"CropStage": ""}, "missing or malformed"),
    ],
)
def test_invalid_records_fail_closed(
    tmp_path: Path, changes: dict[str, str], match: str
) -> None:
    """Invalid field contracts must not silently become missing observations."""
    source = tmp_path / "invalid.tsv"
    _write_source(source, [_record(**changes)])
    with pytest.raises(ValueError, match=match):
        audit_potato_source(source, verify_source=False)


def test_inconsistent_assignment_fails_closed(tmp_path: Path) -> None:
    """Candidate plot identity is unsafe if treatment assignments change."""
    source = tmp_path / "changed_assignment.tsv"
    _write_source(
        source,
        [_record(), _record(Date="2016-07-12", Treatment="2", Value="30")],
    )
    with pytest.raises(ValueError, match="plot changes treatment"):
        audit_potato_source(source, verify_source=False)


def test_source_identity_is_pinned_by_default(tmp_path: Path) -> None:
    """The toy dataset cannot masquerade as the official byte-identical release."""
    source = tmp_path / "toy.tsv"
    _write_source(source, [_record()])
    with pytest.raises(ValueError, match="checksum mismatch"):
        audit_potato_source(source)


def test_invalid_schema_and_empty_source_fail_closed(tmp_path: Path) -> None:
    """Missing columns and header-only sources cannot be treated as evidence."""
    source = tmp_path / "empty.tsv"
    source.write_text("\t".join(SOURCE_COLUMNS) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="contains no records"):
        audit_potato_source(source, verify_source=False)
    source.write_text("Country\tPlot\nUnited Kingdom\t2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="column contract changed"):
        audit_potato_source(source, verify_source=False)


def test_persisted_zenodo_intake_scientific_contract() -> None:
    """CI validates the pinned derived ledger without downloading unlicensed data."""
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    assert summary["source_sha256"] == SOURCE_SHA256
    assert summary["source_md5"] == SOURCE_ZENODO_MD5
    assert summary["source_md5_matches_zenodo"] is True
    assert summary["original_source_rows"] == 127_034
    assert summary["distinct_complete_row_signatures"] == 9_013
    assert summary["exact_repeat_excess_rows"] == 118_021
    assert summary["exact_repeat_multiplicity_distribution"] == {
        "1": 7808, "2": 13, "100": 1192
    }
    assert summary["site_year_geocode_cells"] == 18
    assert summary["distinct_trial_code_labels"] == 8
    assert summary["site_year_trial_code_cells"] == 34
    assert summary["candidate_plot_keys"] == 602
    assert summary["distinct_assessment_event_keys"] == 8_990
    assert summary["event_keys_with_different_recorded_values"] == 23
    assert summary["permitted_actions"] == ["source_integrity_audit", "design_identity_inventory"]

    with (RESULTS / "years.csv").open(encoding="utf-8", newline="") as handle:
        years = list(csv.DictReader(handle))
    with (RESULTS / "site_years.csv").open(encoding="utf-8", newline="") as handle:
        sites = list(csv.DictReader(handle))
    with (RESULTS / "trial_aliases.csv").open(encoding="utf-8", newline="") as handle:
        aliases = list(csv.DictReader(handle))
    with (RESULTS / "conflicting_events.csv").open(encoding="utf-8", newline="") as handle:
        conflicts = list(csv.DictReader(handle))

    assert len(years) == 5
    assert len(sites) == 18
    assert len(aliases) == 34
    assert len(conflicts) == 23
    for field in ("source_rows", "distinct_full_records", "exact_repeat_excess"):
        for table in (years, sites, aliases):
            assert sum(int(item[field]) for item in table) == {
                "source_rows": 127_034,
                "distinct_full_records": 9_013,
                "exact_repeat_excess": 118_021,
            }[field]
    assert sum(int(item["candidate_plot_ids"]) for item in sites) == 602
    assert sum(int(item["candidate_plot_ids"]) for item in aliases) == 602
    assert sum(int(item["event_keys_with_different_values"]) for item in years) == 23
    assert {item["year"] for item in years} == {"2013", "2014", "2015", "2016", "2017"}
    year_2016 = next(item for item in years if item["year"] == "2016")
    assert year_2016["source_rows"] == "119772"
    assert year_2016["distinct_full_records"] == "1764"
    assert year_2016["exact_repeat_excess"] == "118008"
    assert year_2016["repeated_100x_signatures"] == "1192"
