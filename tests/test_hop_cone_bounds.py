"""Partial-identification checks for missing hop cone assessments."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from crop_protection_ps.hop_cone_bounds import run_late_season_cone_bounds
from crop_protection_ps.hop_cone_quality import (
    CASCADE_COLUMNS,
    CASCADE_SHA256,
    MILDEW_COLUMNS,
    MILDEW_SHA256,
)

_ROOT = Path(__file__).resolve().parents[1]
_RESULTS = _ROOT / "results/real_hop_powdery_mildew/late_season/bounds"


def _quality() -> list[dict[str, str]]:
    """Provide all four treatment plots in two blocks over two years."""
    rows: list[dict[str, str]] = []
    for year in (2020, 2021):
        for block in ("I", "II"):
            for treatment in (1, 2, 3, 4):
                rows.append(
                    {
                        "Year": str(year),
                        "Date": f"8/25/{year}",
                        "Field": "Farm3",
                        "Block": block,
                        "Treatment": str(treatment),
                        "Dry_Matter": "21",
                        "A_acid": "7",
                        "B_acid": "8",
                        "_HSI": "0.2",
                        "Color": "5",
                    }
                )
    return rows


def _mildew() -> list[dict[str, str]]:
    """Create asymmetric missingness within one source year."""
    rows: list[dict[str, str]] = []
    for block in ("I", "II"):
        for treatment in (1, 2, 3, 4):
            for plant in range(1, 11):
                # Two infected cones in the I/1 baseline; one in II/1.
                infected = 2 if block == "I" and treatment == plant == 1 else 0
                if block == "II" and treatment == plant == 1:
                    infected = 1
                missing = block == "I" and (
                    (treatment == 1 and plant in (9, 10))
                    or (treatment == 2 and plant == 10)
                )
                rows.append(
                    {
                        "YEAR": "2020",
                        "DATE": "8/26/2020",
                        "SU": "Cone",
                        "REP": block,
                        "TRT": str(treatment),
                        "PLANT": str(plant),
                        "PM": "." if missing else str(infected),
                    }
                )
    return rows


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _run(
    tmp_path: Path, mildew: list[dict[str, str]] | None = None, *, verify: bool = False
) -> tuple[dict[str, object], list[dict[str, str]], list[dict[str, str]]]:
    """Run the public CLI-equivalent contract on synthetic source records."""
    source = tmp_path / "input"
    mildew_path = _write(
        source / "Mildew.csv", MILDEW_COLUMNS,
        _mildew() if mildew is None else mildew,
    )
    cascade_path = _write(source / "Cascade.csv", CASCADE_COLUMNS, _quality())
    result = run_late_season_cone_bounds(
        mildew_path, cascade_path, tmp_path / "output", verify_source=verify
    )

    def read(name: str) -> list[dict[str, str]]:
        with (tmp_path / "output" / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    return result.summary, read("plot_bounds.csv"), read("paired_bounds.csv")


def test_missing_plants_are_bounded_not_imputed(tmp_path: Path) -> None:
    summary, plots, pairs = _run(tmp_path)
    assert summary["missing_plant_assessments"] == 3
    assert summary["source_plots"] == 8
    assert summary["point_identified_plots"] == 6
    assert summary["partially_identified_plots"] == 2
    assert summary["plots_without_disease_source"] == 8
    assert summary["bounded_disease_pairs"] == 6
    assert summary["partially_identified_disease_pairs"] == 3
    assert summary["disease_pairs_without_source"] == 6

    baseline = next(
        row for row in plots
        if (row["year"], row["block"], row["treatment"]) == ("2020", "I", "1")
    )
    assert baseline["observed_plants"] == "8"
    assert baseline["missing_plants"] == "2"
    assert baseline["infected_observed_cones"] == "2"
    assert float(baseline["incidence_lower_percent"]) == 2
    assert float(baseline["incidence_upper_percent"]) == 22

    pair = next(
        row for row in pairs
        if (row["year"], row["block"], row["additional_after_bloom"])
        == ("2020", "I", "1")
    )
    assert pair["identification_status"] == "partially_identified"
    assert float(pair["delta_lower_percentage_points"]) == -22
    assert float(pair["delta_upper_percentage_points"]) == 8
    assert pair["identified_direction"] == "not_sign_identified"

    complete = next(
        row for row in plots
        if (row["year"], row["block"], row["treatment"]) == ("2020", "II", "2")
    )
    absent = next(
        row for row in plots
        if (row["year"], row["block"], row["treatment"]) == ("2021", "II", "2")
    )
    assert (complete["incidence_lower_percent"], complete["incidence_upper_percent"]) == (
        "0.0", "0.0",
    )
    assert absent["observed_plants"] == ""
    assert absent["incidence_lower_percent"] == ""
    assert absent["mildew_source_status"] == "not_in_source"


def test_missingness_can_preserve_or_destroy_a_contrast_sign(tmp_path: Path) -> None:
    _, _, pairs = _run(tmp_path)
    pair = next(
        row for row in pairs
        if (row["year"], row["block"], row["additional_after_bloom"])
        == ("2020", "I", "2")
    )
    assert float(pair["delta_lower_percentage_points"]) == -22
    assert float(pair["delta_upper_percentage_points"]) == -2
    assert pair["identified_direction"] == "negative"

    with (tmp_path / "output/year_bounds.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        year_bounds = list(csv.DictReader(handle))
    one_more = next(
        row for row in year_bounds
        if (row["year"], row["additional_after_bloom"]) == ("2020", "1")
    )
    two_more = next(
        row for row in year_bounds
        if (row["year"], row["additional_after_bloom"]) == ("2020", "2")
    )
    assert float(one_more["mean_lower_percentage_points"]) == -11.5
    assert float(one_more["mean_upper_percentage_points"]) == 3.5
    assert one_more["identified_direction"] == "not_sign_identified"
    assert float(two_more["mean_lower_percentage_points"]) == -11.5
    assert float(two_more["mean_upper_percentage_points"]) == -1.5
    assert two_more["identified_direction"] == "negative"
    assert all(
        row["mean_lower_percentage_points"] == ""
        for row in year_bounds if row["year"] == "2021"
    )


def test_fully_unobserved_plot_has_honest_0_to_100_bounds(tmp_path: Path) -> None:
    mildew = _mildew()
    for row in mildew:
        if row["REP"] == "I" and row["TRT"] == "3":
            row["PM"] = "."
    _, plots, _ = _run(tmp_path, mildew)
    source = next(
        row for row in plots
        if (row["year"], row["block"], row["treatment"]) == ("2020", "I", "3")
    )
    assert source["observed_plants"] == "0"
    assert source["missing_plants"] == "10"
    assert source["incidence_lower_percent"] == "0.0"
    assert source["incidence_upper_percent"] == "100.0"


def test_pinned_source_identity_is_not_optional_by_default(tmp_path: Path) -> None:
    source = tmp_path / "input"
    mildew = _write(source / "Mildew.csv", MILDEW_COLUMNS, _mildew())
    quality = _write(source / "Cascade.csv", CASCADE_COLUMNS, _quality())
    with pytest.raises(ValueError, match="source checksum mismatch"):
        run_late_season_cone_bounds(mildew, quality, tmp_path / "output")


def test_persisted_bounds_obey_original_plot_arithmetic() -> None:
    """Check derived evidence without network or original raw CSV files."""
    with (_RESULTS / "plot_bounds.csv").open(encoding="utf-8", newline="") as handle:
        plots = list(csv.DictReader(handle))
    with (_RESULTS / "paired_bounds.csv").open(encoding="utf-8", newline="") as handle:
        pairs = list(csv.DictReader(handle))
    with (_RESULTS / "year_bounds.csv").open(encoding="utf-8", newline="") as handle:
        years = list(csv.DictReader(handle))
    summary = json.loads((_RESULTS / "summary.json").read_text(encoding="utf-8"))
    assert summary["source_mildew_canonical_sha256"] == MILDEW_SHA256
    assert summary["source_cascade_canonical_sha256"] == CASCADE_SHA256
    assert summary["missing_plant_assessments"] == 203
    assert summary["source_plots"] == 112
    assert summary["point_identified_plots"] == 89
    assert summary["partially_identified_plots"] == 23
    assert summary["plots_without_disease_source"] == 28
    assert (len(plots), len(pairs), len(years)) == (140, 105, 15)
    assert summary["point_identified_disease_pairs"] == 65
    assert summary["partially_identified_disease_pairs"] == 19
    assert summary["disease_pairs_without_source"] == 21

    plot_lookup = {
        (row["year"], row["block"], row["treatment"]): row for row in plots
    }
    for plot in plots:
        if plot["mildew_source_status"] == "not_in_source":
            assert plot["incidence_lower_percent"] == ""
            continue
        lower = float(plot["incidence_lower_percent"])
        upper = float(plot["incidence_upper_percent"])
        missing = int(plot["missing_plants"])
        assert 0 <= lower <= upper <= 100
        assert upper - lower == pytest.approx(10 * missing)
        assert lower == int(plot["infected_observed_cones"])

    for pair in pairs:
        baseline = plot_lookup[(pair["year"], pair["block"], "1")]
        treated = plot_lookup[
            (pair["year"], pair["block"], str(int(pair["additional_after_bloom"]) + 1))
        ]
        if pair["identification_status"] == "not_in_source":
            assert pair["delta_lower_percentage_points"] == ""
            assert pair["delta_upper_percentage_points"] == ""
            continue
        assert float(pair["delta_lower_percentage_points"]) == pytest.approx(
            float(treated["incidence_lower_percent"])
            - float(baseline["incidence_upper_percent"])
        )
        assert float(pair["delta_upper_percentage_points"]) == pytest.approx(
            float(treated["incidence_upper_percent"])
            - float(baseline["incidence_lower_percent"])
        )

    for annual in years:
        matching = [
            row for row in pairs
            if row["year"] == annual["year"]
            and row["additional_after_bloom"] == annual["additional_after_bloom"]
        ]
        assert len(matching) == 7
        sourced = [row for row in matching if row["identification_status"] != "not_in_source"]
        assert int(annual["source_pairs"]) == len(sourced)
        if not sourced:
            assert annual["mean_lower_percentage_points"] == ""
            assert annual["mean_upper_percentage_points"] == ""
            continue
        assert len(sourced) == len(matching)
        for bound in ("lower", "upper"):
            key = f"delta_{bound}_percentage_points"
            expected = sum(float(row[key]) for row in sourced) / len(sourced)
            assert float(annual[f"mean_{bound}_percentage_points"]) == pytest.approx(
                expected
            )

    assert all(
        row["identified_direction"] == "not_sign_identified"
        for row in years if row["year"] in ("2018", "2019")
    )
    assert all(
        row["identified_direction"] == "negative"
        for row in years if row["year"] in ("2020", "2022")
    )
    assert all(
        row["identified_direction"] == "not_in_source"
        for row in years if row["year"] == "2021"
    )
