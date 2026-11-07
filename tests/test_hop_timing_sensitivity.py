"""Checks for design-preserving hop fungicide timing sensitivity estimates."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from crop_protection_ps.hop_timing_sensitivity import (
    analyse_hop_timing_sensitivity,
    run_hop_timing_sensitivity,
)
from crop_protection_ps.hop_trial import (
    load_hop_trial,
    paired_timing_differences,
    prepare_primary_analysis,
    prepare_timing_analysis,
)

_ROOT = Path(__file__).resolve().parents[1]
_RAW = _ROOT / "data/raw/richardson_gent_hop_downy_mildew.csv"


def _real_pairs() -> pd.DataFrame:
    """Use the source-defined treatment pairing and 2019 exclusion."""
    return paired_timing_differences(
        prepare_timing_analysis(prepare_primary_analysis(load_hop_trial(_RAW)))
    )


def _toy_pairs() -> pd.DataFrame:
    """Create labelled synthetic pairs with unequal product coverage by year."""
    records: list[dict[str, object]] = []
    for year, product_count, offset in [(2020, 1, 0.0), (2021, 2, 10.0)]:
        for block, block_effect in [("I", 1.0), ("II", 3.0)]:
            for product in ("A", "B")[:product_count]:
                raw_delta = offset + block_effect
                records.append(
                    {
                        "year": year,
                        "block": block,
                        "treatment": product,
                        "delta_audpc_late_minus_early": raw_delta,
                        "delta_sqrt_audpc_late_minus_early": raw_delta / 2,
                    }
                )
    return pd.DataFrame.from_records(records)


def test_public_trial_year_and_field_block_coverage() -> None:
    result = analyse_hop_timing_sensitivity(_real_pairs(), n_bootstrap=250)
    assert result.summary["n_trial_years"] == 4
    assert result.summary["n_year_blocks"] == 20
    assert result.summary["n_complete_product_pairs"] == 92
    assert set(result.by_year["year"]) == {2017, 2018, 2020, 2021}
    assert result.by_year["n_blocks"].tolist() == [5, 5, 5, 5]
    assert result.without_year["n_pairs"].min() > 0
    assert len(result.without_year_block) == 20
    assert result.summary["estimands"]["pair_weighted_audpc"] == pytest.approx(
        40.93152173913044
    )


def test_estimands_distinguish_pair_and_year_weighting() -> None:
    result = analyse_hop_timing_sensitivity(_toy_pairs(), n_bootstrap=150, seed=3)
    estimates = result.summary["estimands"]
    assert estimates["pair_weighted_audpc"] == pytest.approx(26 / 3)
    assert estimates["equal_year_audpc"] == pytest.approx(7)
    assert estimates["pair_weighted_sqrt_audpc"] == pytest.approx(13 / 3)
    by_year = result.by_year.set_index("year")
    assert by_year.loc[2020, "n_pairs"] == 2
    assert by_year.loc[2021, "n_pairs"] == 4
    without = result.without_year.set_index("omitted_year")
    assert without.loc[2020, "pair_weighted_audpc"] == pytest.approx(12)
    assert without.loc[2021, "pair_weighted_audpc"] == pytest.approx(2)
    assert all(result.without_year_block["n_pairs"] < 6)


def test_results_are_reproducible_when_rows_are_reordered() -> None:
    pairs = _toy_pairs()
    first = analyse_hop_timing_sensitivity(pairs, n_bootstrap=200, seed=44)
    second = analyse_hop_timing_sensitivity(
        pairs.sample(frac=1, random_state=19), n_bootstrap=200, seed=44
    )
    assert first.summary == second.summary
    pd.testing.assert_frame_equal(first.by_year, second.by_year)
    pd.testing.assert_frame_equal(first.without_year, second.without_year)
    pd.testing.assert_frame_equal(first.without_year_block, second.without_year_block)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("2019", "source-excluded 2019"),
        ("duplicate", "duplicate year-block-product"),
        ("null_id", "identifiers must be present"),
        ("infinite", "must be finite"),
        ("single_year", "two independent trial years"),
        ("single_block", "two field blocks"),
        ("fractional_year", "integer identifier"),
    ],
)
def test_invalid_experimental_units_are_rejected(mutation: str, message: str) -> None:
    pairs = _toy_pairs()
    if mutation == "2019":
        pairs.loc[0, "year"] = 2019
    elif mutation == "duplicate":
        pairs = pd.concat([pairs, pairs.iloc[[0]]], ignore_index=True)
    elif mutation == "null_id":
        pairs.loc[0, "block"] = None
    elif mutation == "infinite":
        pairs.loc[0, "delta_audpc_late_minus_early"] = np.inf
    elif mutation == "single_year":
        pairs = pairs.loc[pairs["year"] == 2020]
    elif mutation == "single_block":
        pairs = pairs.loc[~((pairs["year"] == 2021) & (pairs["block"] == "II"))]
    elif mutation == "fractional_year":
        pairs["year"] = pairs["year"].astype(float)
    with pytest.raises(ValueError, match=message):
        analyse_hop_timing_sensitivity(pairs, n_bootstrap=100)


@pytest.mark.parametrize("count", [0, 99, True, 250.0])
def test_bootstrap_count_is_validated(count: object) -> None:
    with pytest.raises(ValueError, match="n_bootstrap"):
        analyse_hop_timing_sensitivity(_toy_pairs(), n_bootstrap=count)  # type: ignore[arg-type]


def test_generated_tables_and_source_checksum_match_committed_receipt(tmp_path: Path) -> None:
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/raw/richardson_gent_hop_downy_mildew.csv").write_bytes(_RAW.read_bytes())
    computed = run_hop_timing_sensitivity(tmp_path)
    stored = json.loads(
        (_ROOT / "results/real_hop_trial/timing_sensitivity/summary.json").read_text()
    )
    assert computed == stored
    for table in ("by_year", "leave_one_year_out", "leave_one_year_block_out"):
        relative = f"results/real_hop_trial/timing_sensitivity/{table}.csv"
        assert (tmp_path / relative).read_bytes() == (_ROOT / relative).read_bytes()
