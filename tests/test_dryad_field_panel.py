"""Source-backed and synthetic checks for Dryad field-panel descriptions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crop_protection_ps.dryad_field_panel import (
    _excel_date,
    audit_dryad_field_panel,
    audit_field_panel,
    main,
)

_ROOT = Path(__file__).resolve().parents[1]


def _example() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """Return two longitudinal plants, two visits, and two weather records."""
    plants = [
        {
            "Row": "1",
            "Position": "1",
            "Ever.dis": "",
            "Status.May.17": "V",
            "Infect.status.may.17": "",
            "Status.May.25": "D/H",
            "Infect.status.may.25": "PD",
        },
        {
            "Row": "1",
            "Position": "2",
            "Ever.dis": "0",
            "Status.May.17": "",
            "Infect.status.may.17": "",
            "Status.May.25": "H",
            "Infect.status.may.25": "H",
        },
    ]
    flower = [
        {"Date": "44333", "days": "0"},
        {"Date": "44341", "days": "8"},
    ]
    weather = [
        {"Date": "5/17/21", "High": "", "Low": "45"},
        {"Date": "5/25/21", "High": "60", "Low": "61"},
    ]
    return plants, flower, weather


def test_saved_report_matches_original_verified_dryad_files() -> None:
    actual = audit_dryad_field_panel(_ROOT / "data")
    saved = json.loads((_ROOT / "results/external_dryad_field_panel.json").read_text())
    assert actual == saved
    assert actual["schema_version"] == 1
    panel = actual["field_panel"]
    assert panel["plant_rows"] == panel["unique_row_position_pairs"] == 178
    assert panel["field_visits"] == 27
    assert panel["raw_status_cells"] == 178 * 27
    assert panel["raw_status_codes"][""] == 11
    assert panel["raw_status_codes"]["D"] == 1756
    assert panel["raw_status_codes"]["H"] == 975
    assert panel["infection_status_codes"][""] == 1862
    assert panel["infection_unlisted_readme_codes"] == {"F": 1}
    assert panel["ever_disease_field_codes"] == {"": 172, "0": 6}


def test_original_timeline_matches_summary_and_weather_without_imputation() -> None:
    panel = audit_dryad_field_panel(_ROOT / "data")["field_panel"]
    assert panel["summary_dates_matched_to_raw_status"] == 27
    assert panel["summary_dates_matched_to_infection_status"] == 27
    assert panel["visits_with_matching_weather_date"] == 27
    assert panel["source_header_aliases"] == [
        {"source_header": "Status.Spet.24", "parsed_date": "2021-09-24"}
    ]
    assert panel["weather_missing_temperature_dates"] == ["2021-08-30"]
    assert panel["weather_low_above_high_dates"] == ["2021-08-31"]
    assert [visit["date"] for visit in panel["visits"]][:2] == ["2021-05-17", "2021-05-25"]
    assert panel["visits"][15]["weather_low_above_high"] is True
    assert sum(visit["raw_blank"] for visit in panel["visits"]) == 11


def test_synthetic_codes_and_weather_are_descriptive_not_recoded() -> None:
    panel = audit_field_panel(*_example())
    assert panel["plant_rows"] == 2
    assert panel["raw_status_codes"] == {"": 1, "D/H": 1, "H": 1, "V": 1}
    assert panel["raw_unlisted_readme_codes"] == {"D/H": 1, "H": 1}
    assert panel["infection_status_codes"] == {"": 2, "H": 1, "PD": 1}
    assert panel["weather_missing_temperature_dates"] == ["2021-05-17"]
    assert panel["weather_low_above_high_dates"] == ["2021-05-25"]
    assert panel["visits"][0]["weather_missing_temperature"] is True
    assert panel["visits"][1]["weather_low_above_high"] is True


def test_unlisted_header_typo_is_explicit_alias_only() -> None:
    plants, flower, weather = _example()
    for plant in plants:
        plant["Status.Spet.24"] = plant.pop("Status.May.25")
        plant["Infect.status.sept.24"] = plant.pop("Infect.status.may.25")
    flower[1] = {"Date": "44463", "days": "130"}
    weather[1]["Date"] = "9/24/21"
    panel = audit_field_panel(plants, flower, weather)
    assert panel["source_header_aliases"] == [
        {"source_header": "Status.Spet.24", "parsed_date": "2021-09-24"}
    ]


@pytest.mark.parametrize("bad", ["NaN", "-1", "44333.5", "oops", "60"])
def test_invalid_excel_serials_are_rejected(bad: str) -> None:
    with pytest.raises(ValueError, match="Excel date serial"):
        _excel_date(bad)


def test_missing_or_conflicting_field_dates_are_rejected() -> None:
    plants, flower, weather = _example()
    plants[0]["Status.May.24"] = plants[0].pop("Status.May.25")
    plants[1]["Status.May.24"] = plants[1].pop("Status.May.25")
    with pytest.raises(ValueError, match="field/flower date mismatch"):
        audit_field_panel(plants, flower, weather)

    plants, flower, weather = _example()
    for plant in plants:
        plant["Status.May.025"] = "V"
    with pytest.raises(ValueError, match="duplicate field date columns"):
        audit_field_panel(plants, flower, weather)


def test_summary_elapsed_days_must_match_dates() -> None:
    plants, flower, weather = _example()
    flower[1]["days"] = "7"
    with pytest.raises(ValueError, match="elapsed days"):
        audit_field_panel(plants, flower, weather)

    plants, flower, weather = _example()
    with pytest.raises(ValueError, match="duplicated or unordered"):
        audit_field_panel(plants, flower[::-1], weather)


def test_weather_duplicates_and_bad_values_fail_closed() -> None:
    plants, flower, weather = _example()
    with pytest.raises(ValueError, match="duplicate Dryad weather date"):
        audit_field_panel(plants, flower, [*weather, weather[0]])

    plants, flower, weather = _example()
    weather[0]["High"] = "NaN"
    with pytest.raises(ValueError, match="nonfinite"):
        audit_field_panel(plants, flower, weather)

    plants, flower, weather = _example()
    weather[0].pop("Low")
    with pytest.raises(ValueError, match="unexpected Dryad weather columns"):
        audit_field_panel(plants, flower, weather)


def test_missing_plant_identity_and_malformed_columns_fail_closed() -> None:
    plants, flower, weather = _example()
    plants[0]["Position"] = ""
    with pytest.raises(ValueError, match="missing Dryad field plant position"):
        audit_field_panel(plants, flower, weather)

    plants, flower, weather = _example()
    plants[1].pop("Status.May.25")
    with pytest.raises(ValueError, match="inconsistent Dryad field plant columns"):
        audit_field_panel(plants, flower, weather)


def test_cli_check_is_read_only_and_rejects_stale_report(tmp_path: Path) -> None:
    output = tmp_path / "field.json"
    arguments = ["--data-dir", str(_ROOT / "data"), "--output", str(output)]
    assert main(arguments) == 0
    content = output.read_bytes()
    assert main([*arguments, "--check"]) == 0
    assert output.read_bytes() == content
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main([*arguments, "--check"])
    assert error.value.code == 1
