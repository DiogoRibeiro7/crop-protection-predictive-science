"""Reproducibility and experimental-unit checks for late-season hop trials."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from crop_protection_ps.hop_cone_quality import (
    CASCADE_COLUMNS,
    CASCADE_SHA256,
    ConeQualityAnalysis,
    METRICS,
    MILDEW_COLUMNS,
    MILDEW_SHA256,
    run_late_season_cones,
)

_ROOT = Path(__file__).resolve().parents[1]
_RESULTS = _ROOT / "results/real_hop_powdery_mildew/late_season"


def _quality_fixture() -> list[dict[str, str]]:
    """Construct paired plot records with quality in a source-only year."""
    result: list[dict[str, str]] = []
    for year in (2020, 2021):
        for block in ("I", "II"):
            for treatment in (1, 2, 3, 4):
                result.append(
                    {
                        "Year": str(year),
                        "Date": f"8/25/{year}",
                        "Field": "Farm3",
                        "Block": block,
                        "Treatment": str(treatment),
                        "Dry_Matter": str(20 + treatment),
                        "A_acid": str(5 + treatment),
                        "B_acid": str(8 + treatment / 10),
                        "_HSI": str(0.2 + treatment / 100),
                        "Color": str(5 + treatment),
                    }
                )
    return result


def _mildew_fixture() -> list[dict[str, str]]:
    """Create disease records for only 2020, with ten cone slots per plant."""
    result: list[dict[str, str]] = []
    for block in ("I", "II"):
        for treatment, infected in ((1, 1), (2, 0), (3, 2), (4, 0)):
            for plant in range(1, 11):
                result.append(
                    {
                        "YEAR": "2020",
                        "DATE": "8/26/2020",
                        "SU": "Cone",
                        "REP": block,
                        "TRT": str(treatment),
                        "PLANT": str(plant),
                        "PM": str(infected),
                    }
                )
    return result


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _run(
    tmp_path: Path,
    mildew: list[dict[str, str]] | None = None,
    quality: list[dict[str, str]] | None = None,
    *,
    verify_source: bool = False,
) -> ConeQualityAnalysis:
    mildew_path = _write(
        tmp_path / "source/Mildew.csv", MILDEW_COLUMNS,
        mildew if mildew is not None else _mildew_fixture(),
    )
    quality_path = _write(
        tmp_path / "source/Cascade.csv", CASCADE_COLUMNS,
        quality if quality is not None else _quality_fixture(),
    )
    return run_late_season_cones(
        mildew_path, quality_path, tmp_path / "output", verify_source=verify_source
    )


def test_quality_plots_and_mildew_subsamples_remain_distinct(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.summary["mildew_plant_rows"] == 80
    assert result.summary["quality_plot_rows"] == 16
    assert result.summary["mildew_complete_plots"] == 8
    assert result.summary["quality_only_years"] == [2021]
    assert result.summary["quality_only_plots"] == 8
    assert result.summary["paired_quality_block_comparisons"] == 12
    assert result.summary["paired_complete_mildew_block_comparisons"] == 6
    assert len(result.block_influence) == 2 * 3 * len(METRICS) * 2
    assert {row["mildew_vs_quality_date_offset_days"] for row in result.linked_plots} == {
        1, None,
    }
    comparison = next(
        row for row in result.year_comparisons
        if row["year"] == 2020 and row["additional_after_bloom"] == 1
    )
    assert comparison["mean_mildew_delta_percentage_points"] == pytest.approx(-10)
    assert comparison["mean_delta_alpha_acids_percent"] == pytest.approx(1)
    assert next(
        row for row in result.year_comparisons
        if row["year"] == 2021 and row["additional_after_bloom"] == 1
    )["mean_mildew_delta_percentage_points"] is None


def test_missing_plant_outcomes_remove_only_affected_mildew_pair(tmp_path: Path) -> None:
    mildew = _mildew_fixture()
    for row in mildew:
        if row["REP"] == "II" and row["TRT"] == "2":
            row["PM"] = "."
    result = _run(tmp_path, mildew=mildew)
    assert result.summary["mildew_missing_plant_rows"] == 10
    assert result.summary["mildew_incomplete_plots"] == 1
    assert result.summary["paired_complete_mildew_block_comparisons"] == 5
    assert result.summary["paired_quality_block_comparisons"] == 12
    absent = next(
        row for row in result.linked_plots
        if row["year"] == 2020 and row["block"] == "II" and row["treatment"] == 2
    )
    assert absent["mildew_status"] == "incomplete"
    assert absent["mildew_incidence_percent"] is None
    assert absent["mildew_plants_observed"] == 0


def test_join_refuses_ambiguous_farm_attribution(tmp_path: Path) -> None:
    quality = _quality_fixture()
    quality[0]["Field"] = "FarmZ"
    with pytest.raises(ValueError, match="multiple farms make the join ambiguous"):
        _run(tmp_path, quality=quality)


def test_duplicate_plant_or_missing_quality_plot_fails_closed(tmp_path: Path) -> None:
    mildew = _mildew_fixture()
    mildew.append(dict(mildew[0]))
    with pytest.raises(ValueError, match="duplicate year-block-treatment-plant"):
        _run(tmp_path / "duplicate", mildew=mildew)
    quality = _quality_fixture()
    quality.pop()
    with pytest.raises(ValueError, match="all four treatments"):
        _run(tmp_path / "missing", quality=quality)


@pytest.mark.parametrize(
    ("file", "field", "value", "error"),
    [
        ("mildew", "PM", "11", "PM outside"),
        ("mildew", "SU", "Leaf", "SU must be Cone"),
        ("mildew", "DATE", "8/26/2021", "DATE year"),
        ("quality", "Color", "11", "Color outside"),
        ("quality", "A_acid", "NaN", "finite in-range"),
        ("quality", "_HSI", "1.5", "finite in-range"),
        ("quality", "Date", "8/25/2019", "Date year"),
    ],
)
def test_invalid_source_values_fail_closed(
    tmp_path: Path, file: str, field: str, value: str, error: str
) -> None:
    mildew = _mildew_fixture()
    quality = _quality_fixture()
    target = mildew if file == "mildew" else quality
    target[0][field] = value
    with pytest.raises(ValueError, match=error):
        _run(tmp_path, mildew=mildew, quality=quality)


def test_source_hash_contract_protects_against_changed_data(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source checksum mismatch"):
        _run(tmp_path, verify_source=True)


def test_source_derived_tables_remain_arithmetically_consistent() -> None:
    def read_csv(name: str) -> list[dict[str, str]]:
        with (_RESULTS / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    result = json.loads((_RESULTS / "summary.json").read_text(encoding="utf-8"))
    assert result["mildew_canonical_sha256"] == MILDEW_SHA256
    assert result["cascade_canonical_sha256"] == CASCADE_SHA256
    assert result["mildew_plant_rows"] == 1_120
    assert result["mildew_missing_plant_rows"] == 203
    assert result["mildew_complete_plots"] == 89
    assert result["mildew_incomplete_plots"] == 23
    assert result["quality_only_plots"] == 28
    assert result["quality_only_years"] == [2021]
    assert result["paired_quality_block_comparisons"] == 105
    assert result["paired_complete_mildew_block_comparisons"] == 65
    assert result["alpha_acid_largest_original_value"]["value_percent"] == 13.5

    linked = read_csv("linked_plots.csv")
    pairs = read_csv("paired_blocks.csv")
    years = read_csv("year_comparisons.csv")
    influence = read_csv("block_influence.csv")
    assert len(linked) == 140
    assert len(pairs) == 105
    assert len(years) == 15
    assert len(influence) == 525
    lookup = {
        (row["year"], row["block"], row["treatment"]): row for row in linked
    }
    assert len(lookup) == len(linked)
    for pair in pairs:
        y, block, trt = pair["year"], pair["block"], pair["additional_after_bloom"]
        baseline = lookup[(y, block, "1")]
        treatment = lookup[(y, block, str(int(trt) + 1))]
        for metric in METRICS:
            assert float(pair[f"delta_{metric}"]) == pytest.approx(
                float(treatment[metric]) - float(baseline[metric])
            )
        if pair["mildew_pair_status"] == "complete":
            assert float(pair["mildew_delta_percentage_points"]) == pytest.approx(
                float(treatment["mildew_incidence_percent"])
                - float(baseline["mildew_incidence_percent"])
            )
        else:
            assert pair["mildew_delta_percentage_points"] == ""

    check = next(
        row for row in influence
        if (
            row["year"], row["additional_after_bloom"],
            row["metric"], row["omitted_block"]
        ) == ("2022", "1", "alpha_acids_percent", "VII")
    )
    assert float(check["all_block_mean_delta"]) == pytest.approx(1.2142857143)
    assert float(check["without_block_mean_delta"]) == pytest.approx(-0.0833333333)
