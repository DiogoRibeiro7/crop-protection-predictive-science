"""Tests for case-only Dryad greenhouse death tally exports."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

import crop_protection_ps.dryad_greenhouse_death_descriptives as module
from crop_protection_ps.dryad_greenhouse_death_descriptives import (
    audit_dryad_greenhouse_deaths,
    main,
    render_reports,
    summarise_death_cases,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_dryad_greenhouse_deaths"


def _row(
    *,
    dead: str = "1",
    year: str = "21",
    date: str = "45641",
    temperature: str = "24",
    exposure: str = "with",
    time: str = "NA",
    replicate: str = "1",
    family: str = "25",
) -> dict[str, str]:
    """Create one record using the source's lowercase death-case columns."""
    return {
        "date": date,
        "temperature": temperature,
        "smut exposure": exposure,
        "time": time,
        "replicate": replicate,
        "family": family,
        "dead": dead,
        "year": year,
    }


def test_original_case_tally_reproduces_all_committed_artifacts() -> None:
    report = audit_dryad_greenhouse_deaths(_ROOT / "data")
    artifacts = render_reports(report)
    assert set(artifacts) == {"summary.json", "cases_by_recorded_cell.csv", "cases_by_stratum.csv"}
    for filename, content in artifacts.items():
        assert (_OUTPUT / filename).read_text(encoding="utf-8") == content
    metadata = json.loads((_OUTPUT / "summary.json").read_text(encoding="utf-8"))
    assert metadata == {
        key: value for key, value in report.items() if key not in {"case_cells", "strata"}
    }
    assert report["analysis"] == "death_case_tally"
    assert report["source_workbook"] == "seedling_inoculation-_death_data.xlsx"
    assert report["source_case_value"] == "1"


def test_original_case_only_counts_are_not_treated_as_mortality_rates() -> None:
    report = audit_dryad_greenhouse_deaths(_ROOT / "data")
    assert report["source_death_case_rows"] == 173
    assert report["recorded_case_cells"] == 115
    assert report["source_exact_repeated_row_excess"] == 58
    assert report["source_year_code_counts"] == {"21": 62, "22": 111}
    assert len(report["source_date_serial_counts"]) == 7
    assert report["source_temperature_code_counts"] == {"24": 35, "26": 84, "30": 54}
    assert report["source_records_per_case_cell"] == {
        "1": 81,
        "2": 22,
        "3": 8,
        "4": 1,
        "5": 1,
        "6": 1,
        "9": 1,
    }
    assert len(report["strata"]) == 19
    assert report["observational_unit"] == "recorded_death_case_row_not_verified_unique_plant"
    assert "at_risk_plant_count" not in report
    assert "mortality_fraction" not in report
    assert "infection_records" not in report
    assert "case_cells" not in json.loads((_OUTPUT / "summary.json").read_text())


def test_both_csvs_reconcile_cases_without_inventing_denominators() -> None:
    report = audit_dryad_greenhouse_deaths(_ROOT / "data")
    artifacts = render_reports(report)
    for name, count in (("cases_by_recorded_cell.csv", 115), ("cases_by_stratum.csv", 19)):
        rows = list(csv.DictReader(io.StringIO(artifacts[name])))
        assert len(rows) == count
        assert sum(int(row["source_death_case_rows"]) for row in rows) == 173
        assert all(int(row["source_death_case_rows"]) >= 1 for row in rows)
        assert not any("rate" in field or "denominator" in field for field in rows[0])
    cell_rows = list(csv.DictReader(io.StringIO(artifacts["cases_by_recorded_cell.csv"])))
    assert all(row["date"].isascii() and row["date"].isdigit() for row in cell_rows)
    assert {row["year"] for row in cell_rows} == {"21", "22"}
    stratum_rows = list(csv.DictReader(io.StringIO(artifacts["cases_by_stratum.csv"])))
    assert sum(int(row["recorded_case_cells"]) for row in stratum_rows) == 115


def test_identical_case_rows_are_retained_without_deduplicating_plants() -> None:
    rows = [_row(), _row(), _row(family="72"), _row(date="45642")]
    report = summarise_death_cases(rows)
    assert report["source_death_case_rows"] == 4
    assert report["recorded_case_cells"] == 3
    assert report["source_exact_repeated_row_excess"] == 1
    assert [x["source_death_case_rows"] for x in report["case_cells"]] == [2, 1, 1]
    assert len(report["strata"]) == 1
    assert report["strata"][0]["recorded_case_cells"] == 3
    assert report["strata"][0]["source_death_case_rows"] == 4


def test_different_dates_and_years_remain_separate_source_cells() -> None:
    rows = [_row(), _row(date="45313"), _row(year="22")]
    report = summarise_death_cases(rows)
    assert report["recorded_case_cells"] == 3
    assert len(report["strata"]) == 2
    assert report["source_date_serial_counts"] == {"45313": 1, "45641": 2}


@pytest.mark.parametrize(
    "rows,reason",
    [
        ([], "empty Dryad greenhouse death"),
        ([_row(dead="0")], "literal dead=1"),
        ([_row(dead="2")], "literal dead=1"),
        ([_row(dead="1.0")], "literal dead=1"),
        ([_row(dead="NA")], "literal dead=1"),
        ([_row(date="NA")], "invalid greenhouse death date"),
        ([_row(year="2.1")], "invalid greenhouse death year"),
        ([_row(replicate="1.5")], "invalid greenhouse death replicate"),
        ([_row(temperature="nan")], "invalid greenhouse death temperature"),
        ([_row(temperature="inf")], "invalid greenhouse death temperature"),
        ([_row(family="")], "blank greenhouse death source field: family"),
        ([_row() | {"extra": "test"}], "unexpected greenhouse death source columns"),
        ([_row() | {"dead": None}], "blank greenhouse death source field: dead"),
    ],
)
def test_unsafe_source_case_rows_fail_closed(rows: list[dict[str, str]], reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        summarise_death_cases(rows)


def test_denied_case_tally_permission_prevents_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "analysis_decision", lambda *args: {"status": "requires_protocol"})
    with pytest.raises(ValueError, match="not permitted"):
        audit_dryad_greenhouse_deaths(_ROOT / "data")


def test_check_mode_is_read_only_and_catches_missing_and_stale_files(tmp_path: Path) -> None:
    destination = tmp_path / "greenhouse-death"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(destination)]
    with pytest.raises(SystemExit) as absent:
        main([*args, "--check"])
    assert absent.value.code == 1
    assert not destination.exists()

    assert main(args) == 0
    before = {p.name: p.read_bytes() for p in destination.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == before

    (destination / "cases_by_stratum.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stale:
        main([*args, "--check"])
    assert stale.value.code == 1
