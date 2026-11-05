"""Source-literal regression tests for the permitted Dryad weather review."""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from pathlib import Path

import pytest

import crop_protection_ps.dryad_weather_quality_descriptives as module
from crop_protection_ps.dryad_weather_quality_descriptives import (
    audit_dryad_weather_quality,
    describe_weather_records,
    main,
    render_reports,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_dryad_weather_quality"


def _rows(text: str) -> list[dict[str, str]]:
    """Keep CSV values as strings to detect accidental source rewriting."""
    return list(csv.DictReader(io.StringIO(text)))


def _example() -> list[dict[str, str]]:
    """Include intact, missing, reversed and discontinuous station dates."""
    return [
        {"Date": "5/1/21", "High": "89.00", "Low": "41.0"},
        {"Date": "5/2/21", "High": "92.00", "Low": ""},
        {"Date": "5/4/21", "High": "85.00", "Low": "90.00"},
    ]


def test_original_source_reproduces_committed_outputs_and_all_units() -> None:
    report = audit_dryad_weather_quality(_ROOT / "data")
    outputs = render_reports(report)
    assert set(outputs) == {"summary.json", "source_daily_weather.csv", "quality_events.csv"}
    for name, content in outputs.items():
        assert (_OUTPUT / name).read_text(encoding="utf-8") == content
    metadata = json.loads(outputs["summary.json"])
    assert metadata["analysis"] == "source_weather_quality_review"
    assert metadata["observational_unit"] == "weather_station_calendar_day_not_individual_plant"
    assert metadata["source_weather_rows"] == metadata["distinct_dates"] == 214
    assert (metadata["first_weather_date"], metadata["last_weather_date"]) == (
        "2021-05-01",
        "2021-11-30",
    )
    assert metadata["out_of_order_source_rows"] == 0
    assert metadata["missing_calendar_days_between_records"] == 0
    assert metadata["calendar_gaps"] == []
    assert metadata["quality_flag_counts"] == {
        "low_above_high": 1,
        "missing_low": 1,
        "ok": 212,
    }
    assert metadata["records_missing_high"] == 0
    assert metadata["records_missing_low"] == 1
    assert metadata["records_low_above_high"] == 1
    assert metadata["source_anomaly_dates"] == ["2021-08-30", "2021-08-31"]
    assert metadata["field_visit_date_count"] == 27
    assert metadata["weather_dates_matching_field_visits"] == 27
    assert metadata["field_visits_without_weather"] == []
    assert metadata["field_visits_on_source_anomaly_dates"] == ["2021-08-31"]
    assert "source_records" not in metadata
    assert "quality_events" not in metadata


def test_all_original_strings_and_quality_event_rows_are_unchanged() -> None:
    report = audit_dryad_weather_quality(_ROOT / "data")
    output = render_reports(report)
    rows = _rows(output["source_daily_weather.csv"])
    issues = _rows(output["quality_events.csv"])
    assert len(rows) == 214
    assert len(issues) == 2
    assert list(rows[0]) == [
        "record_order",
        "calendar_date",
        "Date",
        "High",
        "Low",
        "quality_flag",
        "high_missing",
        "low_missing",
        "low_above_high",
        "aligned_field_visit",
    ]
    assert rows[0]["Date"] == "5/1/21"
    assert rows[0]["High"] == "67.0" and rows[0]["Low"] == "45.0"
    assert rows[31]["High"] == "78.00" and rows[31]["Low"] == "48.00"
    missing, reversed_pair = issues
    assert (missing["calendar_date"], missing["issue"]) == ("2021-08-30", "missing_low")
    assert missing["High"] == "91.00" and missing["Low"] == ""
    assert missing["aligned_field_visit"] == "False"
    assert (reversed_pair["calendar_date"], reversed_pair["issue"]) == (
        "2021-08-31",
        "low_above_high",
    )
    assert reversed_pair["High"] == "85.00" and reversed_pair["Low"] == "90.00"
    assert reversed_pair["aligned_field_visit"] == "True"
    assert rows[-1]["calendar_date"] == "2021-11-30"
    assert rows[-1]["High"] == "50" and rows[-1]["Low"] == "27"
    assert "estimated_exposure" not in rows[0]
    source_path = _ROOT / "data/external/dryad_pathogen_temperature_4mw6m90jv/daily_high_temps.txt"
    with source_path.open(encoding="utf-8-sig", newline="") as handle:
        originals = list(csv.DictReader(handle, delimiter="\t"))
    assert [{field: item[field] for field in ("Date", "High", "Low")} for item in rows] == (
        originals
    )


def test_synthetic_dates_gaps_and_anomalies_are_reported_not_repaired() -> None:
    report = describe_weather_records(_example(), [date(2021, 5, 1), date(2021, 5, 4)])
    assert report["source_weather_rows"] == 3
    assert report["distinct_dates"] == 3
    assert report["missing_calendar_days_between_records"] == 1
    assert report["calendar_gaps"] == [
        {"before": "2021-05-02", "after": "2021-05-04", "missing_calendar_days": 1}
    ]
    assert report["quality_flag_counts"] == {"low_above_high": 1, "missing_low": 1, "ok": 1}
    assert report["field_visits_on_source_anomaly_dates"] == ["2021-05-04"]
    assert report["weather_dates_matching_field_visits"] == 2
    rows = _rows(render_reports(report)["source_daily_weather.csv"])
    assert rows[0]["High"] == "89.00"
    assert rows[1]["Low"] == "" and rows[1]["quality_flag"] == "missing_low"
    assert rows[2]["High"] == "85.00" and rows[2]["Low"] == "90.00"


def test_missing_high_is_distinct_and_present_low_must_be_numeric() -> None:
    rows = _example()
    rows[1] = {"Date": "5/2/21", "High": "", "Low": "42.00"}
    report = describe_weather_records(rows, [date(2021, 5, 2)])
    assert report["records_missing_high"] == 1
    assert report["records_missing_low"] == 0
    assert report["quality_events"][0]["issue"] == "missing_high"
    assert report["quality_events"][0]["Low"] == "42.00"

    rows[1]["Low"] = "n/a"
    with pytest.raises(ValueError, match="invalid Dryad Low"):
        describe_weather_records(rows, [date(2021, 5, 2)])


@pytest.mark.parametrize(
    "problem",
    ["duplicate_date", "bad_date", "bad_header", "null_low", "infinite", "invalid_high"],
)
def test_invalid_weather_source_fails_closed(problem: str) -> None:
    rows = _example()
    if problem == "duplicate_date":
        rows[1]["Date"] = "5/1/21"
    elif problem == "bad_date":
        rows[1]["Date"] = "2/30/21"
    elif problem == "bad_header":
        rows[1]["Rain"] = rows[1].pop("Low")
    elif problem == "null_low":
        rows[1]["Low"] = None  # type: ignore[assignment]
    elif problem == "infinite":
        rows[1]["High"] = "Inf"
    else:
        rows[0]["High"] = "not-a-number"
    with pytest.raises(ValueError):
        describe_weather_records(rows, [date(2021, 5, 1)])


def test_visit_dates_without_source_record_are_explicit_not_imputed() -> None:
    report = describe_weather_records(_example(), [date(2021, 5, 3), date(2021, 5, 4)])
    assert report["field_visits_without_weather"] == ["2021-05-03"]
    assert report["weather_dates_matching_field_visits"] == 1


def test_out_of_order_daily_rows_are_reported_without_sorting_source() -> None:
    rows = _example()
    rows[0], rows[1] = rows[1], rows[0]
    report = describe_weather_records(rows, [date(2021, 5, 1)])
    assert report["out_of_order_source_rows"] == 1
    original = _rows(render_reports(report)["source_daily_weather.csv"])
    assert [item["Date"] for item in original] == ["5/2/21", "5/1/21", "5/4/21"]


def test_both_missing_temperature_components_remain_distinguishable() -> None:
    rows = _example()
    rows[1]["High"] = ""
    report = describe_weather_records(rows, [date(2021, 5, 2)])
    assert report["quality_flag_counts"]["missing_high+missing_low"] == 1
    assert report["records_missing_high"] == report["records_missing_low"] == 1
    assert [event["issue"] for event in report["quality_events"]] == [
        "missing_high",
        "missing_low",
        "low_above_high",
    ]


def test_invalid_visit_date_axis_fails_closed() -> None:
    for visits in ([], [date(2021, 5, 1), date(2021, 5, 1)], [date(2021, 5, 4), date(2021, 5, 1)]):
        with pytest.raises(ValueError):
            describe_weather_records(_example(), visits)


def test_denied_permission_prevents_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "analysis_decision", lambda *_args: {"status": "requires_protocol"})
    with pytest.raises(ValueError, match="not permitted"):
        audit_dryad_weather_quality(_ROOT / "data")


def test_cli_check_is_read_only_and_detects_stale_files(tmp_path: Path) -> None:
    target = tmp_path / "weather"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(target)]
    with pytest.raises(SystemExit) as missing:
        main([*args, "--check"])
    assert missing.value.code == 1
    assert not target.exists()
    assert main(args) == 0
    original = {path.name: path.read_bytes() for path in target.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {path.name: path.read_bytes() for path in target.iterdir()} == original
    (target / "quality_events.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stale:
        main([*args, "--check"])
    assert stale.value.code == 1
