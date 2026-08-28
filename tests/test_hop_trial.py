from pathlib import Path

import numpy as np

from crop_protection_ps.hop_trial import (
    EXCLUDED_YEAR,
    bootstrap_timing_effects,
    compare_year_transportability,
    load_hop_trial,
    paired_timing_differences,
    prepare_primary_analysis,
    prepare_timing_analysis,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "richardson_gent_hop_downy_mildew.csv"


def test_public_hop_trial_schema_and_counts() -> None:
    frame = load_hop_trial(RAW)
    assert len(frame) == 290
    assert frame["audpc"].isna().sum() == 3
    assert set(frame["year"].unique()) == {2017, 2018, 2019, 2020, 2021}


def test_source_defined_2019_exclusion_is_explicit() -> None:
    raw = load_hop_trial(RAW)
    primary = prepare_primary_analysis(raw)
    assert EXCLUDED_YEAR in set(raw["year"])
    assert EXCLUDED_YEAR not in set(primary["year"])
    assert set(primary["year"]) == {2017, 2018, 2020, 2021}


def test_control_normalisation_is_well_defined() -> None:
    primary = prepare_primary_analysis(load_hop_trial(RAW))
    untreated = primary.loc[primary["treatment"] == "NT"]
    assert np.allclose(
        untreated.groupby("year")["relative_disease"].mean().to_numpy(),
        1.0,
    )


def test_paired_timing_contrasts_match_experimental_units() -> None:
    timing = prepare_timing_analysis(prepare_primary_analysis(load_hop_trial(RAW)))
    paired = paired_timing_differences(timing)
    assert len(timing) == 187
    assert len(paired) == 92
    assert paired[["year", "block", "treatment"]].duplicated().sum() == 0


def test_bootstrap_timing_effect_is_deterministic() -> None:
    timing = prepare_timing_analysis(prepare_primary_analysis(load_hop_trial(RAW)))
    paired = paired_timing_differences(timing)
    first = bootstrap_timing_effects(paired, n_bootstrap=250, seed=17)
    second = bootstrap_timing_effects(paired, n_bootstrap=250, seed=17)
    assert first.equals(second)
    overall = first.loc[first["scope"] == "all_products"].iloc[0]
    assert overall["mean_delta_audpc_late_minus_early"] > 0


def test_leave_one_year_out_is_harder_for_raw_trial_year_proxy() -> None:
    timing = prepare_timing_analysis(prepare_primary_analysis(load_hop_trial(RAW)))
    validation = compare_year_transportability(timing)
    raw = validation.loc[validation["target"] == "sqrt_audpc"].set_index("strategy")
    assert raw.loc["leave_one_year_out", "rmse"] > raw.loc["random_5fold", "rmse"]
    assert raw.loc["leave_one_year_out", "n_folds"] == 4
