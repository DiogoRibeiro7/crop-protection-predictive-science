"""Source-backed and synthetic tests for Dryad longitudinal field exports."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

import crop_protection_ps.dryad_field_status_descriptives as module
from crop_protection_ps.dryad_field_status_descriptives import (
    audit_dryad_field_statuses,
    describe_field_statuses,
    main,
    render_reports,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_dryad_field_statuses"


def _example() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Provide two tracked plants, two dates, blanks and ambiguous codes."""
    plants = [
        {
            "Row": "2",
            "Position": "1",
            "Ever.dis": "",
            "Status.May.17": "V",
            "Infect.status.may.17": "",
            "Status.May.25": "D/H",
            "Infect.status.may.25": "F",
        },
        {
            "Row": "2",
            "Position": "2",
            "Ever.dis": "0",
            "Status.May.17": "",
            "Infect.status.may.17": "",
            "Status.May.25": "H",
            "Infect.status.may.25": "H",
        },
    ]
    flower = [{"Date": "44333", "days": "0"}, {"Date": "44341", "days": "8"}]
    return plants, flower


def _csv_rows(content: str) -> list[dict[str, str]]:
    """Read a generated CSV without imposing numeric endpoint semantics."""
    return list(csv.DictReader(io.StringIO(content)))


def test_committed_outputs_match_verified_unmodified_source() -> None:
    report = audit_dryad_field_statuses(_ROOT / "data")
    outputs = render_reports(report)
    assert set(outputs) == {
        "summary.json",
        "plant_visit_status.csv",
        "status_labels_by_visit.csv",
    }
    for filename, content in outputs.items():
        assert (_OUTPUT / filename).read_text(encoding="utf-8") == content

    metadata = json.loads(outputs["summary.json"])
    assert metadata["analysis"] == "within_plant_status_description"
    assert metadata["observational_unit"] == "source_plant_with_repeated_dated_visits"
    assert metadata["plant_rows"] == metadata["unique_plant_keys"] == 178
    assert metadata["field_visits"] == 27
    assert metadata["plant_visit_rows"] == 4806
    assert metadata["raw_status_populated"] == 4795
    assert metadata["raw_status_blank"] == 11
    assert metadata["infection_status_populated"] == 2944
    assert metadata["infection_status_blank"] == 1862
    assert metadata["raw_status_distinct_nonblank_labels"] == 31
    assert metadata["infection_status_counts"]["F"] == 1
    assert metadata["source_header_aliases"] == [
        {"source_header": "Status.Spet.24", "parsed_date": "2021-09-24"}
    ]
    assert "plant_visits" not in metadata
    assert "visit_label_counts" not in metadata
    assert "transition_probability" not in metadata


def test_repeated_source_plant_rows_are_preserved_and_reconciled() -> None:
    report = audit_dryad_field_statuses(_ROOT / "data")
    csvs = render_reports(report)
    plant_visits = _csv_rows(csvs["plant_visit_status.csv"])
    frequencies = _csv_rows(csvs["status_labels_by_visit.csv"])
    assert len(plant_visits) == 178 * 27
    assert len({(r["Row"], r["Position"]) for r in plant_visits}) == 178
    assert {
        len([r for r in plant_visits if r["source_plant_row"] == str(i)]) for i in (1, 178)
    } == {27}
    assert [r["date"] for r in plant_visits[:3]] == [
        "2021-05-17",
        "2021-05-25",
        "2021-06-01",
    ]
    assert [r["source_plant_row"] for r in plant_visits[:27]] == ["1"] * 27
    assert [r["source_plant_row"] for r in plant_visits[27:54]] == ["2"] * 27
    assert sum(int(r["plant_rows_with_label"]) for r in frequencies) == 2 * 4806
    assert all(r["plant_rows_observed"] == "178" for r in frequencies)
    assert {(r["date"], r["status_field"]) for r in frequencies} == {
        (r["date"], kind) for r in plant_visits for kind in ("raw_status", "infection_status")
    }
    assert any(
        r["raw_status_header"] == "Status.Spet.24" and r["date"] == "2021-09-24"
        for r in plant_visits
    )


def test_compound_unlisted_and_blank_labels_are_retained_without_recoding() -> None:
    plants, flower = _example()
    report = describe_field_statuses(plants, flower)
    assert report["plant_rows"] == report["unique_plant_keys"] == 2
    assert report["field_visits"] == 2
    assert report["plant_visit_rows"] == 4
    assert report["raw_status_counts"] == {"": 1, "D/H": 1, "H": 1, "V": 1}
    assert report["infection_status_counts"] == {"": 2, "F": 1, "H": 1}
    outputs = render_reports(report)
    plant_visits = _csv_rows(outputs["plant_visit_status.csv"])
    assert [
        (r["source_plant_row"], r["raw_status"], r["infection_status"]) for r in plant_visits
    ] == [
        ("1", "V", ""),
        ("1", "D/H", "F"),
        ("2", "", ""),
        ("2", "H", "H"),
    ]
    assert "Ever.dis" not in plant_visits[0]
    assert "disease" not in plant_visits[0]
    frequencies = _csv_rows(outputs["status_labels_by_visit.csv"])
    assert any(
        row["date"] == "2021-05-17"
        and row["status_field"] == "raw_status"
        and row["literal_label"] == ""
        and row["plant_rows_with_label"] == "1"
        for row in frequencies
    )


@pytest.mark.parametrize("problem", ["duplicate", "missing", "inconsistent", "date", "status_type"])
def test_unsafe_plant_or_visit_source_fails_closed(problem: str) -> None:
    plants, flower = _example()
    if problem == "duplicate":
        plants[1]["Position"] = "1"
    elif problem == "missing":
        plants[1]["Row"] = ""
    elif problem == "inconsistent":
        plants[1].pop("Status.May.25")
    elif problem == "date":
        flower[1]["days"] = "7"
    elif problem == "status_type":
        plants[1]["Status.May.25"] = None  # type: ignore[assignment]
    with pytest.raises(ValueError):
        describe_field_statuses(plants, flower)


def test_header_alias_keeps_source_name_and_correct_calendar_date() -> None:
    plants, flower = _example()
    for plant in plants:
        plant["Status.Spet.24"] = plant.pop("Status.May.25")
        plant["Infect.status.sept.24"] = plant.pop("Infect.status.may.25")
    flower[1] = {"Date": "44463", "days": "130"}
    report = describe_field_statuses(plants, flower)
    assert report["source_header_aliases"] == [
        {"source_header": "Status.Spet.24", "parsed_date": "2021-09-24"}
    ]
    assert report["plant_visits"][1]["raw_status_header"] == "Status.Spet.24"
    assert report["plant_visits"][1]["date"] == "2021-09-24"


def test_denied_contract_action_prevents_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "analysis_decision", lambda *args: {"status": "requires_protocol"})
    with pytest.raises(ValueError, match="not permitted"):
        audit_dryad_field_statuses(_ROOT / "data")


def test_check_mode_never_creates_or_changes_outputs(tmp_path: Path) -> None:
    destination = tmp_path / "field-status"
    arguments = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(destination)]
    with pytest.raises(SystemExit) as absent:
        main([*arguments, "--check"])
    assert absent.value.code == 1
    assert not destination.exists()

    assert main(arguments) == 0
    original = {path.name: path.read_bytes() for path in destination.iterdir()}
    assert main([*arguments, "--check"]) == 0
    assert {path.name: path.read_bytes() for path in destination.iterdir()} == original
    (destination / "plant_visit_status.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stale:
        main([*arguments, "--check"])
    assert stale.value.code == 1
