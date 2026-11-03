"""Regression tests for permission-gated Dryad greenhouse status frequencies."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

import crop_protection_ps.dryad_greenhouse_status_descriptives as module
from crop_protection_ps.dryad_greenhouse_status_descriptives import (
    audit_dryad_greenhouse_status,
    main,
    render_reports,
    summarise_infection_status,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_dryad_greenhouse_status"


def _row(
    status: str = "D",
    *,
    date: str = "45318",
    year: str = "22",
    temperature: str = "24",
    exposure: str = "with",
    time: str = "NA",
    rep: str = "1",
    family: str = "37",
    observer: str = "DC",
    comments: str = "",
) -> dict[str, str]:
    """Construct one source-shaped scored greenhouse record."""
    return {
        "Date": date,
        "Temperature": temperature,
        "Smut Exposure": exposure,
        "Time": time,
        "Rep": rep,
        "Family": family,
        "Disease Status": status,
        "Observer": observer,
        "year": year,
        "Comments": comments,
    }


def test_original_greenhouse_report_matches_all_committed_artifacts() -> None:
    report = audit_dryad_greenhouse_status(_ROOT / "data")
    outputs = render_reports(report)
    assert set(outputs) == {
        "summary.json",
        "status_by_visit_cell.csv",
        "status_by_stratum.csv",
    }
    for filename, contents in outputs.items():
        assert (_OUTPUT / filename).read_text(encoding="utf-8") == contents
    summary = json.loads((_OUTPUT / "summary.json").read_text(encoding="utf-8"))
    assert summary == {
        key: value for key, value in report.items() if key not in {"visit_cells", "strata"}
    }
    assert report["analysis"] == "disease_status_frequencies"
    assert report["source_workbook"] == "seedling_inoculation-_infection_data.xlsx"
    assert report["visit_fields"] == [
        "year",
        "Date",
        "Temperature",
        "Smut Exposure",
        "Time",
        "Rep",
        "Family",
    ]


def test_original_status_codes_and_repeated_rows_are_preserved() -> None:
    report = audit_dryad_greenhouse_status(_ROOT / "data")
    assert report["source_scored_rows"] == 1112
    assert report["recorded_visit_cells"] == 852
    assert report["source_exact_repeated_row_excess"] == 141
    assert report["source_status_code_counts"] == {"D": 171, "HF": 507, "HM": 325, "LD": 109}
    assert report["source_year_code_counts"] == {"22": 1033, "23": 79}
    assert report["source_observer_code_counts"] == {"DC": 1107, "SPS": 5}
    assert report["source_nonblank_comment_rows"] == 0
    assert report["source_records_per_visit_cell"] == {
        "1": 667,
        "2": 137,
        "3": 32,
        "4": 9,
        "5": 4,
        "6": 2,
        "7": 1,
    }
    assert len(report["strata"]) == 21
    assert report["observational_unit"] == "recorded_plant_score_row_not_verified_unique_plant"
    assert "death_case_rows" not in report
    assert "infection_rate" not in report


def test_csv_reconciles_every_record_without_status_recoding() -> None:
    report = audit_dryad_greenhouse_status(_ROOT / "data")
    outputs = render_reports(report)
    for filename, expected_count in (
        ("status_by_visit_cell.csv", 852),
        ("status_by_stratum.csv", 21),
    ):
        rows = list(csv.DictReader(io.StringIO(outputs[filename])))
        assert len(rows) == expected_count
        assert sum(int(row["source_scored_rows"]) for row in rows) == 1112
        for code, n in report["source_status_code_counts"].items():
            assert sum(int(row[f"status_{code}"]) for row in rows) == n
        assert all(
            sum(int(row[f"status_{code}"]) for code in ("D", "HF", "HM", "LD"))
            == int(row["source_scored_rows"])
            for row in rows
        )
    visits = list(csv.DictReader(io.StringIO(outputs["status_by_visit_cell.csv"])))
    assert all(row["Date"].isascii() and row["Date"].isdigit() for row in visits)
    assert all(isinstance(json.loads(row["observer_labels"]), list) for row in visits)
    assert all(row["nonblank_comment_rows"] == "0" for row in visits)
    strata = list(csv.DictReader(io.StringIO(outputs["status_by_stratum.csv"])))
    assert sum(int(row["recorded_visit_cells"]) for row in strata) == 852


def test_synthetic_duplicate_rows_are_not_dropped_or_used_as_plant_ids() -> None:
    rows = [
        _row("D"),
        _row("D"),  # Could be a different plant with all the same recorded fields.
        _row("HF", observer="SPS", comments="source note"),
        _row("HM", date="45319"),
        _row("LD", family="NA"),
    ]
    report = summarise_infection_status(rows)
    assert report["source_scored_rows"] == 5
    assert report["recorded_visit_cells"] == 3
    assert report["source_exact_repeated_row_excess"] == 1
    assert report["source_status_code_counts"] == {"D": 2, "HF": 1, "HM": 1, "LD": 1}
    assert report["source_nonblank_comment_rows"] == 1
    group = next(
        row for row in report["visit_cells"] if row["Family"] == "37" and row["Date"] == "45318"
    )
    assert group["source_scored_rows"] == 3
    assert [group[f"status_{code}"] for code in ("D", "HF", "HM", "LD")] == [2, 1, 0, 0]
    assert group["observer_labels"] == ["DC", "SPS"]
    assert group["nonblank_comment_rows"] == 1
    assert report["visit_cells"][0]["Date"] == "45318"


def test_same_design_labels_at_different_dates_remain_separate_visits() -> None:
    rows = [_row("D", date="45318"), _row("HF", date="45319")]
    report = summarise_infection_status(rows)
    assert report["recorded_visit_cells"] == 2
    assert len(report["strata"]) == 1
    assert report["strata"][0]["recorded_visit_cells"] == 2


@pytest.mark.parametrize(
    "rows,reason",
    [
        ([], "empty Dryad greenhouse"),
        ([_row("X")], "unmapped greenhouse Disease Status"),
        ([_row("")], "blank greenhouse source field: Disease Status"),
        ([_row(date="missing")], "invalid greenhouse Date code"),
        ([_row(year="2.2")], "invalid greenhouse year code"),
        ([_row(rep="1.5")], "invalid greenhouse Rep code"),
        ([_row(temperature="NaN")], "invalid greenhouse Temperature"),
        ([_row(temperature="inf")], "invalid greenhouse Temperature"),
        ([_row(family="")], "blank greenhouse source field: Family"),
        ([_row(observer="")], "blank greenhouse source field: Observer"),
        ([_row() | {"extra": "value"}], "unexpected greenhouse infection source columns"),
        ([_row() | {"Comments": None}], "non-string greenhouse Comments"),
    ],
)
def test_unsafe_or_unexpected_source_rows_fail_closed(
    rows: list[dict[str, str]], reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        summarise_infection_status(rows)


def test_denied_permission_blocks_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "analysis_decision", lambda *args: {"status": "requires_protocol"})
    with pytest.raises(ValueError, match="not permitted"):
        audit_dryad_greenhouse_status(_ROOT / "data")


def test_check_mode_is_read_only_and_catches_missing_and_stale_outputs(tmp_path: Path) -> None:
    destination = tmp_path / "dryad-greenhouse"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(destination)]
    with pytest.raises(SystemExit) as absent:
        main([*args, "--check"])
    assert absent.value.code == 1
    assert not destination.exists()

    assert main(args) == 0
    before = {p.name: p.read_bytes() for p in destination.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == before

    (destination / "status_by_stratum.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stale:
        main([*args, "--check"])
    assert stale.value.code == 1
