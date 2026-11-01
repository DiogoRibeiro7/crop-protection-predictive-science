"""Tests for permitted, non-inferential aphid condition summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import crop_protection_ps.aphid_controlled_descriptives as module
from crop_protection_ps.aphid_controlled_descriptives import (
    audit_aphid_conditions,
    main,
    render_reports,
    summarise_experiment,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_aphid_controlled"


def _source_rows() -> list[dict[str, str]]:
    """Create two different cohorts in one literal source condition."""
    return [
        {"Temperature": "30", "CONC": "2.5", "TOTAL": "25", "DEAD": "5"},
        {"Temperature": "30", "CONC": "2.5", "TOTAL": "35", "DEAD": "14"},
    ]


def test_real_report_matches_verified_original_and_all_checked_in_csv_files() -> None:
    report = audit_aphid_conditions(_ROOT / "data")
    rendered = render_reports(report)
    assert set(rendered) == {
        "summary.json",
        "experiment1_conditions.csv",
        "experiment2_conditions.csv",
        "experiment3_conditions.csv",
        "experiment4_conditions.csv",
    }
    for name, content in rendered.items():
        assert (_OUTPUT / name).read_text(encoding="utf-8") == content
    assert report == json.loads((_OUTPUT / "summary.json").read_text())
    assert report["schema_version"] == 1
    assert report["analysis"] == "condition_mortality_description"
    assert report["excluded_source_sheet"] == "Experiment5"


def test_each_source_experiment_is_kept_separate_and_preserves_uneven_cells() -> None:
    reports = audit_aphid_conditions(_ROOT / "data")["experiments"]
    assert {name: study["source_records"] for name, study in reports.items()} == {
        "Experiment1": 36,
        "Experiment2": 24,
        "Experiment3": 180,
        "Experiment4": 36,
    }
    assert {name: study["condition_cells"] for name, study in reports.items()} == {
        "Experiment1": 12,
        "Experiment2": 8,
        "Experiment3": 48,
        "Experiment4": 12,
    }
    assert sum(study["counted_aphids"] for study in reports.values()) == 8111
    assert sum(study["recorded_deaths"] for study in reports.values()) == 2485
    assert reports["Experiment3"]["source_records_per_condition"] == {"3": 40, "6": 4, "9": 4}
    assert reports["Experiment3"]["exact_source_row_match_excess"] == 20
    assert reports["Experiment2"]["factor_levels_as_recorded"]["Treatment_Time"] == ["12h", "90"]
    time_by_temperature: dict[str, set[str]] = {}
    for condition in reports["Experiment2"]["conditions"]:
        factors = condition["factors"]
        time_by_temperature.setdefault(factors["Temperature"], set()).add(factors["Treatment_Time"])
    assert time_by_temperature == {"22": {"12h"}, "30": {"90"}, "33": {"90"}, "36": {"90"}}


def test_csv_has_only_applicable_factors_and_counts_reconcile() -> None:
    experiments = audit_aphid_conditions(_ROOT / "data")["experiments"]
    for name, study in experiments.items():
        with (_OUTPUT / f"{name.lower()}_conditions.csv").open(newline="") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames is not None
            assert reader.fieldnames[: len(study["factor_fields"])] == study["factor_fields"]
            assert "source_records" in reader.fieldnames
            rows = list(reader)
        assert len(rows) == study["condition_cells"]
        assert sum(int(row["source_records"]) for row in rows) == study["source_records"]
        assert sum(int(row["counted_aphids"]) for row in rows) == study["counted_aphids"]
        assert sum(int(row["recorded_deaths"]) for row in rows) == study["recorded_deaths"]
        for row in rows:
            assert float(row["pooled_recorded_mortality"]) == pytest.approx(
                int(row["recorded_deaths"]) / int(row["counted_aphids"]), abs=1e-10
            )


def test_synthetic_condition_aggregation_is_count_weighted_not_row_mean() -> None:
    report = summarise_experiment(_source_rows(), ("Temperature", "CONC"), "example")
    assert report["source_records"] == 2
    assert report["condition_cells"] == 1
    value = report["conditions"][0]
    assert value["source_records"] == 2
    assert value["counted_aphids"] == 60
    assert value["recorded_deaths"] == 19
    assert value["pooled_recorded_mortality"] == round(19 / 60, 10)
    assert value["min_source_cohort_fraction"] == 0.2
    assert value["max_source_cohort_fraction"] == 0.4


def test_exact_identical_source_rows_are_kept_as_recorded_cohorts() -> None:
    rows = [_source_rows()[0]] * 2
    report = summarise_experiment(rows, ("Temperature", "CONC"), "example")
    assert report["exact_source_row_match_excess"] == 1
    assert report["conditions"][0]["source_records"] == 2
    assert report["conditions"][0]["counted_aphids"] == 50
    assert report["conditions"][0]["recorded_deaths"] == 10


def test_literal_treatment_times_are_never_normalized_across_units() -> None:
    rows = [
        {**_source_rows()[0], "Treatment_Time": "12h"},
        {**_source_rows()[1], "Treatment_Time": "90"},
    ]
    report = summarise_experiment(rows, ("Temperature", "CONC", "Treatment_Time"), "example")
    assert report["condition_cells"] == 2
    assert {condition["factors"]["Treatment_Time"] for condition in report["conditions"]} == {
        "12h",
        "90",
    }


@pytest.mark.parametrize(
    "value,expected",
    [
        ({"TOTAL": "0"}, "invalid DEAD/TOTAL"),
        ({"TOTAL": "-5"}, "invalid TOTAL source count"),
        ({"TOTAL": "5.5"}, "invalid TOTAL source count"),
        ({"TOTAL": "NaN"}, "invalid TOTAL source count"),
        ({"DEAD": "26"}, "invalid DEAD/TOTAL"),
        ({"DEAD": ""}, "invalid DEAD source count"),
        ({"Temperature": ""}, "blank factor value"),
    ],
)
def test_invalid_counts_or_factor_labels_fail_closed(value: dict[str, str], expected: str) -> None:
    row = {**_source_rows()[0], **value}
    with pytest.raises(ValueError, match=expected):
        summarise_experiment([row], ("Temperature", "CONC"), "example")


def test_missing_or_extra_source_columns_and_empty_experiments_fail_closed() -> None:
    with pytest.raises(ValueError, match="empty controlled"):
        summarise_experiment([], ("Temperature", "CONC"), "example")
    row = {**_source_rows()[0], "Replicate": "1"}
    with pytest.raises(ValueError, match="unexpected source columns"):
        summarise_experiment([row], ("Temperature", "CONC"), "example")
    with pytest.raises(ValueError, match="invalid factor fields"):
        summarise_experiment(_source_rows(), ("CONC", "CONC"), "example")


def test_explicit_eligibility_denial_rejects_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "analysis_decision", lambda *args: {"status": "requires_protocol"})
    with pytest.raises(ValueError, match="not permitted"):
        audit_aphid_conditions(_ROOT / "data")


def test_cli_check_is_read_only_and_detects_stale_or_missing_files(tmp_path: Path) -> None:
    destination = tmp_path / "controlled"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(destination)]
    assert main(args) == 0
    before = {path.name: path.read_bytes() for path in destination.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {path.name: path.read_bytes() for path in destination.iterdir()} == before
    (destination / "experiment2_conditions.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as failure:
        main([*args, "--check"])
    assert failure.value.code == 1
