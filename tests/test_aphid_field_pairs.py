"""Regression tests for the source-verifiable aphid field-pair export."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

import crop_protection_ps.aphid_field_pairs as module
from crop_protection_ps.aphid_field_pairs import (
    audit_aphid_field_pairs,
    main,
    pair_source_field_rows,
    render_reports,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_aphid_field"


def _row(
    day: str,
    population: float,
    *,
    replicate: str = "A_1",
    date: str = "45082",
    interval: str = "4",
    baseline: float = 10.0,
) -> dict[str, str]:
    """Make one internally consistent source-style row for pairing tests."""
    return {
        "Site": "Langfang",
        "Treat": "A",
        "Replicate": replicate,
        "SamplingDay": day,
        "Date": date,
        "PopSize": str(population),
        "Base_number": str(baseline),
        "Order": "Pesticide_first",
        "Interval": interval,
        "Type": "Hot",
        "DH_above26": "56.6",
        "Mortality": str(1 - population / baseline),
        "CONC": "2.5",
    }


def _pair(
    *,
    early_population: float = 5,
    late_population: float = 2,
) -> list[dict[str, str]]:
    """Create one descriptive day-3/day-7 series, without a plot identifier."""
    return [
        _row("Day3_postpesticide", early_population),
        _row("Day7_postpesticide", late_population),
    ]


def test_export_exactly_matches_checked_in_source_derived_files() -> None:
    report = audit_aphid_field_pairs(_ROOT / "data")
    rendered = render_reports(report)
    assert set(rendered) == {"summary.json", "paired_series.csv"}
    for name, content in rendered.items():
        assert (_OUTPUT / name).read_text(encoding="utf-8") == content
    assert report == json.loads((_OUTPUT / "summary.json").read_text(encoding="utf-8"))
    assert report["analysis"] == "within_series_mortality_description"
    assert report["source_sheet"] == "Experiment5"
    assert report["provisional_series_fields"] == ["Site", "Treat", "Replicate", "Date", "Interval"]


def test_field_pairs_and_raw_date_serials_reconcile_with_original_source() -> None:
    report = audit_aphid_field_pairs(_ROOT / "data")
    summary = report["summary"]
    assert summary["source_record_count"] == 54
    assert summary["provisional_series_count"] == 27
    assert summary["pairs_with_same_source_date_serial"] == 27
    assert summary["series_by_site"] == {"Langfang": 18, "Xinxiang": 9}
    assert summary["series_by_treatment_label"] == {"A": 6, "B": 9, "C": 12}
    assert summary["fractional_baseline_series"] == 22
    assert summary["recorded_day7_minus_day3_signs"] == {"negative": 0, "zero": 2, "positive": 25}
    assert summary["source_date_serials_by_site"] == {
        "Langfang": ["45082", "45083"],
        "Xinxiang": ["41414"],
    }
    assert report["source_date_interpretation"].endswith("unverified_as_sampling_date")


def test_csv_preserves_source_rate_and_population_strings_without_integer_counts() -> None:
    report = audit_aphid_field_pairs(_ROOT / "data")
    csv_records = list(csv.DictReader(io.StringIO(render_reports(report)["paired_series.csv"])))
    assert len(csv_records) == 27
    assert all("TOTAL" not in row and "DEAD" not in row for row in csv_records)
    assert sum(not float(row["Base_number"]).is_integer() for row in csv_records) == 22
    assert {row["Date"] for row in csv_records} == {"45082", "45083", "41414"}
    assert all(
        float(row["Day7_minus_Day3_Mortality"])
        == pytest.approx(float(row["Day7_Mortality"]) - float(row["Day3_Mortality"]), abs=1e-10)
        for row in csv_records
    )
    assert csv_records == report["series"]


@pytest.mark.parametrize(
    "early,late,sign,delta",
    [(5, 2, "positive", 0.3), (2, 5, "negative", -0.3), (2, 2, "zero", 0.0)],
)
def test_synthetic_changes_are_descriptive_not_treatment_contrasts(
    early: float, late: float, sign: str, delta: float
) -> None:
    report = pair_source_field_rows(_pair(early_population=early, late_population=late))
    assert report["source_record_count"] == 2
    assert report["provisional_series_count"] == 1
    assert report["recorded_day7_minus_day3_signs"][sign] == 1
    assert float(report["series"][0]["Day7_minus_Day3_Mortality"]) == pytest.approx(delta)


def test_same_replicate_label_can_recur_in_distinct_source_series() -> None:
    first = _pair()
    second = [
        _row("Day3_postpesticide", 5, date="45083", interval="5"),
        _row("Day7_postpesticide", 2, date="45083", interval="5"),
    ]
    report = pair_source_field_rows(first + second)
    assert report["provisional_series_count"] == 2
    assert [record["Date"] for record in report["series"]] == ["45082", "45083"]


@pytest.mark.parametrize(
    "rows,reason",
    [
        ([], "empty aphid field"),
        ([_pair()[0]], "incomplete source field series"),
        ([_pair()[0], _pair()[0], _pair()[1]], "repeated sampling-day"),
        ([_row("Day4", 5), _pair()[1]], "invalid or repeated sampling-day"),
        ([_pair()[0], {**_pair()[1], "Base_number": "20"}], "mortality disagrees"),
        ([_pair()[0], {**_pair()[1], "CONC": "1"}], "changing baseline or exposure"),
        ([_pair()[0], {**_pair()[1], "Mortality": "0.4"}], "mortality disagrees"),
        ([_pair()[0], {**_pair()[1], "Mortality": "NaN"}], "invalid Mortality"),
    ],
)
def test_invalid_or_unverified_pairs_fail_closed(rows: list[dict[str, str]], reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        pair_source_field_rows(rows)


def test_eligibility_denial_stops_source_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "analysis_decision", lambda *args: {"status": "requires_protocol"})
    with pytest.raises(ValueError, match="not permitted"):
        audit_aphid_field_pairs(_ROOT / "data")


def test_cli_check_is_read_only_and_detects_stale_outputs(tmp_path: Path) -> None:
    target = tmp_path / "aphid-field"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(target)]
    with pytest.raises(SystemExit) as absent:
        main([*args, "--check"])
    assert absent.value.code == 1
    assert not target.exists()

    assert main(args) == 0
    original = {path.name: path.read_bytes() for path in target.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {path.name: path.read_bytes() for path in target.iterdir()} == original

    (target / "paired_series.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stale:
        main([*args, "--check"])
    assert stale.value.code == 1
