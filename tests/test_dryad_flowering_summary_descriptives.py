"""Tests for literal Dryad visit-level flowering summary exports."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

import crop_protection_ps.dryad_flowering_summary_descriptives as module
from crop_protection_ps.dryad_flowering_summary_descriptives import (
    _SOURCE_FIELDS,
    audit_dryad_flowering_summary,
    describe_flowering_visits,
    main,
    render_reports,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_dryad_flowering_summary"


def _row(
    *,
    serial: str,
    elapsed: str,
    flag: str,
    flowering: str,
    fully: str,
    partial: str,
    any_disease: str,
    prop_any: str,
    prop_flowering: str,
    diseased_flower: str = "",
    healthy_flower: str = "",
    total: str = "",
    fraction: str = "",
) -> dict[str, str]:
    """Build one source-shaped row with untouched weather placeholders."""
    row = dict.fromkeys(_SOURCE_FIELDS, "")
    row.update(
        {
            "Date": serial,
            "days": elapsed,
            "Flwer.data": flag,
            "Flwr.plants": flowering,
            "Fully.Smutty.plants": fully,
            "Partial.dis": partial,
            "any.disease": any_disease,
            "Prop.any.dis": prop_any,
            "prop.flwr": prop_flowering,
            "total.D.flwr": diseased_flower,
            "total.H.flwr": healthy_flower,
            "total": total,
            "proportion": fraction,
        }
    )
    return row


def _example() -> list[dict[str, str]]:
    """A measured flower count followed by unmeasured flowers, not plants."""
    return [
        _row(
            serial="44333",
            elapsed="0",
            flag="1",
            flowering="1",
            fully="1",
            partial="0",
            any_disease="1",
            prop_any="1.0",
            prop_flowering="0.5",
            diseased_flower="2",
            healthy_flower="1",
            total="3",
            fraction="0.67",
        ),
        _row(
            serial="44341",
            elapsed="8",
            flag="0",
            flowering="2",
            fully="0",
            partial="1",
            any_disease="1",
            prop_any="0.5",
            prop_flowering="1.0",
            total="0",
        ),
    ]


def _csv_rows(text: str) -> list[dict[str, str]]:
    """Read CSV as strings to avoid introducing numeric model endpoints."""
    return list(csv.DictReader(io.StringIO(text)))


def test_original_source_reproduces_committed_outputs() -> None:
    report = audit_dryad_flowering_summary(_ROOT / "data")
    outputs = render_reports(report)
    assert set(outputs) == {
        "summary.json",
        "source_flowering_visits.csv",
        "source_arithmetic_checks.csv",
    }
    for filename, content in outputs.items():
        assert (_OUTPUT / filename).read_text(encoding="utf-8") == content
    metadata = json.loads(outputs["summary.json"])
    assert metadata["analysis"] == "aggregate_flowering_description"
    assert metadata["observational_unit"] == "aggregate_visit_row_not_individual_plant"
    assert metadata["source_visit_rows"] == 27
    assert metadata["source_plant_rows_used_only_for_arithmetic_check"] == 178
    assert (metadata["first_visit_date"], metadata["last_visit_date"]) == (
        "2021-05-17",
        "2021-11-18",
    )
    assert metadata["recorded_flower_data_flag_counts"] == {"0": 8, "1": 19}
    assert metadata["flower_count_availability"] == {"complete": 19, "not_collected": 8}
    assert metadata["nonblank_cells_by_count_or_fraction_field"]["total.D.flwr"] == 19
    assert metadata["nonblank_cells_by_count_or_fraction_field"]["Flwr.plants"] == 27
    assert metadata["arithmetic_check_counts"]["source_flower_total_sum"] == {
        "agrees": 19,
        "not_recorded": 8,
    }
    assert metadata["arithmetic_check_counts"]["source_any_disease_count_sum"] == {"agrees": 27}
    assert metadata["arithmetic_check_counts"]["source_flowering_fraction_vs_plant_rows"] == {
        "agrees": 27
    }
    assert "source_visits" not in metadata
    assert "arithmetic_checks" not in metadata


def test_original_visit_values_preserve_all_literal_fields_and_missingness() -> None:
    report = audit_dryad_flowering_summary(_ROOT / "data")
    output = render_reports(report)
    visits = _csv_rows(output["source_flowering_visits.csv"])
    checks = _csv_rows(output["source_arithmetic_checks.csv"])
    assert len(visits) == len(checks) == 27
    assert list(visits[0]) == ["visit_order", "calendar_date", *_SOURCE_FIELDS]
    assert visits[0]["Date"] == "44333" and visits[0]["days"] == "0"
    assert visits[0]["total"] == "" and visits[0]["Flwr.plants"] == "39"
    assert visits[0]["Prop.any.dis"] == "0.82099999999999995"
    assert visits[1]["total.D.flwr"] == "63"
    assert visits[1]["total.H.flwr"] == "1"
    assert visits[1]["total"] == "64"
    assert visits[1]["proportion"] == "0.98"
    assert visits[-1]["calendar_date"] == "2021-11-18"
    assert visits[-1]["total"] == "0" and visits[-1]["proportion"] == ""
    assert checks[0]["flower_count_availability"] == "not_collected"
    assert checks[0]["source_flower_fraction"] == "not_recorded"
    assert checks[-1]["source_any_disease_fraction"] == "agrees"
    assert "estimated_temperature_effect" not in visits[0]


def test_synthetic_aggregate_count_checks_preserve_missing_flower_measurements() -> None:
    report = describe_flowering_visits(_example(), 2)
    assert report["source_visit_rows"] == 2
    assert report["flower_count_availability"] == {"complete": 1, "not_collected": 1}
    assert report["arithmetic_check_counts"]["source_flower_total_sum"] == {
        "agrees": 1,
        "not_recorded": 1,
    }
    assert report["arithmetic_check_counts"]["source_flower_fraction"] == {
        "agrees": 1,
        "not_recorded": 1,
    }
    checks = _csv_rows(render_reports(report)["source_arithmetic_checks.csv"])
    assert checks[0]["source_any_disease_count_sum"] == "agrees"
    assert checks[1]["source_any_disease_count_sum"] == "agrees"
    assert checks[1]["source_flowering_fraction_vs_plant_rows"] == "agrees"


def test_numeric_arithmetic_disagreements_are_reported_not_silently_repaired() -> None:
    rows = _example()
    rows[0]["total"] = "5"
    rows[0]["proportion"] = "0.95"
    rows[0]["Prop.any.dis"] = "0.25"
    report = describe_flowering_visits(rows, 2)
    checks = report["arithmetic_checks"][0]
    assert checks["source_flower_total_sum"] == "disagrees"
    assert checks["source_flower_fraction"] == "disagrees"
    assert checks["source_any_disease_fraction"] == "disagrees"
    assert report["source_visits"][0]["total"] == "5"
    assert report["source_visits"][0]["proportion"] == "0.95"


def test_collection_flag_conflicts_with_observed_details_are_visible() -> None:
    rows = _example()
    rows[1]["total.D.flwr"] = "2"
    report = describe_flowering_visits(rows, 2)
    assert report["flower_count_availability"] == {
        "complete": 1,
        "flag_off_with_detail_values": 1,
    }
    assert report["source_visits"][1]["total.D.flwr"] == "2"
    assert report["arithmetic_checks"][1]["flower_count_availability"] == (
        "flag_off_with_detail_values"
    )


@pytest.mark.parametrize(
    "problem",
    ["flag", "negative", "noninteger", "nonfinite", "more_than_plants", "date", "columns", "type"],
)
def test_invalid_source_structure_or_numeric_values_fail_closed(problem: str) -> None:
    rows = _example()
    if problem == "flag":
        rows[0]["Flwer.data"] = "yes"
    elif problem == "negative":
        rows[0]["Flwr.plants"] = "-1"
    elif problem == "noninteger":
        rows[0]["total"] = "3.1"
    elif problem == "nonfinite":
        rows[0]["proportion"] = "NaN"
    elif problem == "more_than_plants":
        rows[0]["Flwr.plants"] = "3"
    elif problem == "date":
        rows[1]["days"] = "9"
    elif problem == "columns":
        rows[0].pop("Flwr.plants")
    else:
        rows[0]["Flwr.plants"] = None  # type: ignore[assignment]
    with pytest.raises(ValueError):
        describe_flowering_visits(rows, 2)


def test_invalid_source_plant_denominator_fails_closed() -> None:
    for bad in (0, -1, True):
        with pytest.raises(ValueError, match="invalid independently audited"):
            describe_flowering_visits(_example(), bad)


def test_denied_permission_prevents_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "analysis_decision", lambda *args: {"status": "requires_protocol"})
    with pytest.raises(ValueError, match="not permitted"):
        audit_dryad_flowering_summary(_ROOT / "data")


def test_check_mode_is_read_only_and_catches_missing_or_stale_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "flower"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(output_dir)]
    with pytest.raises(SystemExit) as missing:
        main([*args, "--check"])
    assert missing.value.code == 1
    assert not output_dir.exists()
    assert main(args) == 0
    before = {path.name: path.read_bytes() for path in output_dir.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {path.name: path.read_bytes() for path in output_dir.iterdir()} == before
    (output_dir / "source_flowering_visits.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stale:
        main([*args, "--check"])
    assert stale.value.code == 1
