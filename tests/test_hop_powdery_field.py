"""Source-integrity and experimental-unit tests for Gent (2025) field data."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from crop_protection_ps.hop_powdery_field import (
    SOURCE_CANONICAL_SHA256,
    SOURCE_COLUMNS,
    analyse_field_intervals,
    load_gent_interval_csv,
    write_field_interval_analysis,
)

_ROOT = Path(__file__).resolve().parents[1]
_SUMMARY = _ROOT / "results/real_hop_powdery_mildew/field_interval/summary.json"


def _rows() -> list[dict[str, str]]:
    """Make two observed dates, two blocks and four randomised field arms."""
    result: list[dict[str, str]] = []
    for assessment in ("5/1/2020", "7/8/2020"):
        for block in ("I", "II"):
            for treatment in (1, 2, 3, 4):
                for plant in range(1, 11):
                    result.append(
                        {
                            "YEAR": "2020",
                            "Site": "Toppenish",
                            "DATE": assessment,
                            "SU": "Leaf",
                            "REP": block,
                            "TRT": str(treatment),
                            "PLANT": str(plant),
                            # Early disease cannot leak into the final endpoint.
                            "PM": "10" if assessment == "5/1/2020" else str(treatment),
                        }
                    )
    return result


def _source(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    """Write only constructed test cases; never download upstream in CI."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "Interval.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SOURCE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_end_of_season_plot_and_block_unit_are_preserved(tmp_path: Path) -> None:
    source = load_gent_interval_csv(_source(tmp_path, _rows()), verify_source=False)
    result = analyse_field_intervals(source)
    assert result.summary["plant_assessment_rows"] == 160
    assert result.summary["plot_visit_units"] == 16
    assert result.summary["end_season_plot_units"] == 8
    assert result.summary["within_block_risk_vs_fixed_pairs"] == 6
    assert result.summary["site_year_environments"] == 1
    assert result.environments[0]["end_season_mean_incidence_percent"] == pytest.approx(25)
    assert len(result.paired_comparisons) == 6
    # Each pair uses two plots, NOT the ten plants per plot as replicates.
    comparison = result.environment_contrasts
    assert [row["paired_blocks"] for row in comparison] == [2, 2, 2]
    assert [row["mean_risk_minus_fixed_percentage_points"] for row in comparison] == [
        30,
        20,
        10,
    ]
    assert all(plot["date"] == "2020-07-08" for plot in result.end_season_plots)
    assert all(plot["plants_observed"] == 10 for plot in result.end_season_plots)


def test_missing_pm_is_not_zero_and_invalid_plots_cannot_form_pairs(tmp_path: Path) -> None:
    rows = _rows()
    for row in rows:
        if row["DATE"] == "7/8/2020" and row["REP"] == "II" and row["TRT"] == "2":
            row["PM"] = "."
    result = analyse_field_intervals(
        load_gent_interval_csv(_source(tmp_path, rows), verify_source=False)
    )
    assert result.summary["missing_pm_plant_rows"] == 10
    assert result.summary["complete_end_season_plots"] == 7
    assert result.summary["excluded_incomplete_end_season_plots"] == 1
    assert result.summary["within_block_risk_vs_fixed_pairs"] == 5
    invalid = next(
        row
        for row in result.end_season_plots
        if row["block"] == "II" and row["treatment"] == 2
    )
    assert invalid["incidence_percent"] is None
    assert invalid["missing_plants"] == 10
    assert next(
        row for row in result.environment_contrasts if row["fixed_treatment"] == 2
    )["paired_blocks"] == 1


def test_duplicate_original_plant_id_is_recorded_and_visit_rejected(tmp_path: Path) -> None:
    rows = _rows()
    # Original public source has one such collision in an early visit.
    duplicate = next(
        row
        for row in rows
        if row["DATE"] == "5/1/2020"
        and row["REP"] == "I"
        and row["TRT"] == "3"
        and row["PLANT"] == "1"
    )
    duplicate["PLANT"] = "2"
    source = load_gent_interval_csv(_source(tmp_path, rows), verify_source=False)
    result = analyse_field_intervals(source)
    assert source.duplicated_plant_identifiers == 1
    assert result.summary["plot_visits_with_invalid_plant_ids"] == 1
    visit = next(
        row
        for row in result.plot_visits
        if row["date"] == "2020-05-01"
        and row["block"] == "I"
        and row["treatment"] == 3
    )
    assert visit["plot_integrity"] == "invalid_plant_ids"
    assert visit["incidence_percent"] is None
    assert result.summary["within_block_risk_vs_fixed_pairs"] == 6


def test_an_invalid_final_visit_drops_only_its_matched_contrast(tmp_path: Path) -> None:
    rows = _rows()
    duplicate = next(
        row
        for row in rows
        if row["DATE"] == "7/8/2020"
        and row["REP"] == "I"
        and row["TRT"] == "1"
        and row["PLANT"] == "1"
    )
    duplicate["PLANT"] = "2"
    result = analyse_field_intervals(
        load_gent_interval_csv(_source(tmp_path, rows), verify_source=False)
    )
    assert result.summary["within_block_risk_vs_fixed_pairs"] == 5
    assert result.summary["complete_end_season_plots"] == 7


def test_order_independence_and_deterministic_csv_exports(tmp_path: Path) -> None:
    rows = _rows()
    first = analyse_field_intervals(
        load_gent_interval_csv(_source(tmp_path / "first", rows), verify_source=False)
    )
    reverse_source = _source(tmp_path / "second", list(reversed(rows)))
    second = analyse_field_intervals(load_gent_interval_csv(reverse_source, verify_source=False))
    assert first.end_season_plots == second.end_season_plots
    assert first.paired_comparisons == second.paired_comparisons
    write_field_interval_analysis(first, tmp_path / "output")
    written = json.loads((tmp_path / "output/summary.json").read_text(encoding="utf-8"))
    assert written["experimental_unit"].startswith("site-year")
    assert (tmp_path / "output/plot_visits.csv").read_text().count("\n") == 17


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("YEAR", "2021", "DATE and YEAR"),
        ("Site", "unknown", "unexpected trial site"),
        ("SU", "Cone", "only the original Leaf"),
        ("REP", "VIII", "unexpected field replicate"),
        ("TRT", "0", "TRT outside"),
        ("PLANT", "11", "PLANT outside"),
        ("PM", "11", "PM outside"),
        ("PM", "", "partially empty"),
    ],
)
def test_malformed_source_data_fails_closed(
    tmp_path: Path, field: str, value: str, error: str
) -> None:
    rows = _rows()
    rows[0][field] = value
    with pytest.raises(ValueError, match=error):
        load_gent_interval_csv(_source(tmp_path, rows), verify_source=False)


def test_source_hash_must_match_pinned_original(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source checksum mismatch"):
        load_gent_interval_csv(_source(tmp_path, _rows()))


def test_persisted_real_audit_is_separate_from_synthetic_test_data() -> None:
    summary = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    assert summary["source_canonical_sha256"] == SOURCE_CANONICAL_SHA256
    assert summary["plant_assessment_rows"] == 12_880
    assert summary["original_all_empty_csv_rows"] == 1
    assert summary["duplicate_plant_identifier_rows"] == 1
    assert summary["plot_visits_with_invalid_plant_ids"] == 1
    assert summary["site_year_environments"] == 8
    assert summary["complete_end_season_plots"] == 221
    assert summary["within_block_risk_vs_fixed_pairs"] == 165


def test_persisted_real_plot_and_pair_tables_obey_experimental_unit_contract() -> None:
    """Check source-derived outputs without downloading third-party data in CI."""
    result_dir = _SUMMARY.parent

    def read_table(name: str) -> list[dict[str, str]]:
        with (result_dir / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    visits = read_table("plot_visits.csv")
    finals = read_table("end_season_plots.csv")
    paired = read_table("paired_risk_vs_fixed.csv")
    environments = read_table("environment_quality.csv")
    contrasts = read_table("environment_contrasts.csv")
    assert len(visits) == 1_288
    assert len(finals) == 224
    assert len(paired) == 165
    assert len(environments) == 8
    assert len(contrasts) == 24
    assert sum(row["plot_integrity"] != "ok" for row in visits) == 1
    assert sum(int(row["missing_plants"]) for row in visits) == 100
    assert sum(row["incidence_percent"] == "" for row in finals) == 3

    plot_by_unit = {
        (r["year"], r["site"], r["block"], r["treatment"]): r for r in finals
    }
    assert len(plot_by_unit) == len(finals)
    comparison_keys: set[tuple[str, str, str, str]] = set()
    for pair in paired:
        year, site, block, fixed = (
            pair["year"],
            pair["site"],
            pair["block"],
            pair["fixed_treatment"],
        )
        key = year, site, block, fixed
        assert key not in comparison_keys
        comparison_keys.add(key)
        risk = plot_by_unit[(year, site, block, "4")]
        control = plot_by_unit[(year, site, block, fixed)]
        assert risk["plants_observed"] == control["plants_observed"] == "10"
        assert risk["plot_integrity"] == control["plot_integrity"] == "ok"
        assert float(pair["risk_minus_fixed_percentage_points"]) == pytest.approx(
            float(risk["incidence_percent"]) - float(control["incidence_percent"])
        )

    top_2022 = next(
        c
        for c in contrasts
        if (c["year"], c["site"], c["fixed_treatment"]) == ("2022", "Toppenish", "3")
    )
    assert top_2022["paired_blocks"] == "7"
    assert float(top_2022["mean_risk_minus_fixed_percentage_points"]) == pytest.approx(-17)
