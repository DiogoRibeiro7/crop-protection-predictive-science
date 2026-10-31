"""Regression tests for experimental-unit structure in original source tables."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crop_protection_ps.aphid_dryad_units import (
    _aphid_controlled,
    _aphid_field,
    _dryad_field,
    _dryad_greenhouse,
    _dryad_lab,
    audit_aphid_dryad,
    main,
)

_ROOT = Path(__file__).resolve().parents[1]


def _field_row(sampling: str, interval: str = "0", population: str = "5") -> dict[str, str]:
    """Construct synthetic field follow-ups with an unambiguous ratio."""
    return {
        "Site": "TEST",
        "Treat": "C",
        "Replicate": "C_1",
        "Date": "45082",
        "Interval": interval,
        "SamplingDay": sampling,
        "PopSize": population,
        "Base_number": "10",
        "Mortality": str(1 - float(population) / 10),
        "DH_above26": "8",
        "Order": "Heat_first",
        "Type": "Hot",
        "CONC": "2.5",
    }


def test_report_matches_verified_source_data() -> None:
    actual = audit_aphid_dryad(_ROOT / "data")
    saved = json.loads((_ROOT / "results/external_aphid_dryad_units.json").read_text())
    assert actual == saved
    assert actual["schema_version"] == 1


def test_aphid_cohorts_are_not_individual_replicate_identifiers() -> None:
    results = audit_aphid_dryad(_ROOT / "data")["aphid"]
    controlled = results["controlled"]
    assert {name: study["rows"] for name, study in controlled.items()} == {
        "Experiment1": 36,
        "Experiment2": 24,
        "Experiment3": 180,
        "Experiment4": 36,
    }
    assert sum(study["counted_aphids"] for study in controlled.values()) == 8111
    assert controlled["Experiment3"]["condition_cells"] == 48
    assert controlled["Experiment3"]["records_per_condition"] == {"3": 40, "6": 4, "9": 4}
    assert all(not study["explicit_replicate_id"] for study in controlled.values())


def test_aphid_field_pairs_days_but_does_not_collapse_distinct_intervals() -> None:
    field = audit_aphid_dryad(_ROOT / "data")["aphid"]["field"]
    assert field["rows"] == 54
    assert field["provisional_series_count"] == 27
    assert field["complete_day3_day7_series"] == 27
    assert field["observations_per_series"] == {"2": 27}
    assert field["repeated_sampling_keys"] == 0
    assert field["fractional_base_number_rows"] == 44

    synthetic = [
        _field_row("Day3_postpesticide"),
        _field_row("Day7_postpesticide", population="2"),
        _field_row("Day3_postpesticide", interval="5"),
        _field_row("Day7_postpesticide", interval="5", population="2"),
    ]
    report = _aphid_field(synthetic)
    assert report["provisional_series_count"] == 2
    assert report["complete_day3_day7_series"] == 2
    assert report["observations_per_series"] == {"2": 2}

    repeated = _aphid_field([synthetic[0], synthetic[0]])
    assert repeated["provisional_series_count"] == 1
    assert repeated["repeated_sampling_keys"] == 1
    assert repeated["complete_day3_day7_series"] == 0


def test_aphid_validation_rejects_invalid_counts_and_derived_mortality() -> None:
    fields = ("Temperature", "CONC")
    with pytest.raises(ValueError, match="invalid DEAD/TOTAL cohort"):
        _aphid_controlled(
            "Experiment1", [{"Temperature": "22", "CONC": "0", "TOTAL": "2", "DEAD": "3"}],
            fields,
        )
    bad_mortality = {**_field_row("Day3_postpesticide"), "Mortality": "0.7"}
    with pytest.raises(ValueError, match="field mortality disagrees"):
        _aphid_field([bad_mortality])


def test_dryad_lab_counts_preserve_batch_nesting_and_picture_id_collisions() -> None:
    lab = audit_aphid_dryad(_ROOT / "data")["dryad"]["laboratory"]
    germination = lab["Germination_data.xlsx"]
    assert germination["rows"] == 84
    assert germination["temperatures"] == 14
    assert germination["temperature_run_groups"] == 28
    assert germination["records_per_temperature_run"] == {"3": 28}
    assert germination["duplicate_nested_record_keys"] == 0

    growth = lab["Growth_data_strain_2.xlsx"]
    assert growth["rows"] == 168
    assert growth["distinct_picture_ids"] == 84
    assert growth["repeated_picture_id_rows"] == 84
    assert growth["unique_nested_record_keys"] == 168
    assert lab["Growth_data_strain_3.xlsx"]["temperature_run_groups"] == 30

    with pytest.raises(ValueError, match="published assay proportion"):
        _dryad_lab(
            [{
                "Temperature": "20", "Temp.Rep": "1", "Run.Num": "2",
                "Rep": "1", "Sum.Germ": "1", "Sum.Total": "2", "Sum.Prop": "0.9",
            }],
            "germination",
            "test.xlsx",
        )


def test_dryad_greenhouse_preserves_identical_plant_records() -> None:
    greenhouse = audit_aphid_dryad(_ROOT / "data")["dryad"]["greenhouse"]
    assert greenhouse["infection_rows"] == 1112
    assert greenhouse["infection_exact_repeated_rows"] == 141
    assert greenhouse["death_case_rows"] == 173
    assert greenhouse["death_exact_repeated_rows"] == 58
    assert greenhouse["unique_plant_identifier_present"] is False
    assert greenhouse["disease_status_codes"] == {
        "D": 171,
        "HF": 507,
        "HM": 325,
        "LD": 109,
    }
    infection_row = {
        "year": "22", "Date": "45318", "Temperature": "24",
        "Smut Exposure": "with", "Time": "NA", "Rep": "1", "Family": "7",
        "Disease Status": "D",
    }
    death_row = {
        "year": "22", "date": "45318", "temperature": "24",
        "smut exposure": "with", "time": "NA", "replicate": "1",
        "family": "7", "dead": "1",
    }
    report = _dryad_greenhouse([infection_row, infection_row], [death_row, death_row])
    assert report["infection_rows"] == 2
    assert report["infection_exact_repeated_rows"] == 1
    assert report["death_case_rows"] == 2
    assert report["death_exact_repeated_rows"] == 1


def test_dryad_field_rows_are_plants_not_date_measurements() -> None:
    field = audit_aphid_dryad(_ROOT / "data")["dryad"]["field"]
    assert field["plant_rows"] == field["unique_row_position_pairs"] == 178
    assert field["raw_status_date_columns"] == 27
    assert field["infection_status_date_columns"] == 27
    assert field["field_is_longitudinal"] is True
    with pytest.raises(ValueError, match="empty Dryad field"):
        _dryad_field([], [{"Date": "44123"}])


def test_dryad_weather_anomalies_remain_visible() -> None:
    weather = audit_aphid_dryad(_ROOT / "data")["dryad"]["weather"]
    assert weather == {
        "weather_rows": 214,
        "rows_with_missing_temperature": 1,
        "rows_with_low_above_high": 1,
    }


def test_cli_freshness_check_fails_on_stale_report(tmp_path: Path) -> None:
    destination = tmp_path / "units.json"
    arguments = ["--data-dir", str(_ROOT / "data"), "--output", str(destination)]
    assert main(arguments) == 0
    baseline = destination.read_bytes()
    assert main([*arguments, "--check"]) == 0
    assert destination.read_bytes() == baseline
    destination.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main([*arguments, "--check"])
    assert error.value.code == 1
