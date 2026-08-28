"""Tests for the environment-aware transportability extension."""

from pathlib import Path

import numpy as np

from crop_protection_ps.environment_transport import (
    attach_environment_state,
    derive_environment_features,
    gxe_promotion_gate,
    leave_one_year_out_environment_models,
    load_corvallis_weather,
)
from crop_protection_ps.hop_trial import (
    load_hop_trial,
    prepare_primary_analysis,
    prepare_timing_analysis,
)

ROOT = Path(__file__).resolve().parents[1]


def _modelling_frame():
    trial = load_hop_trial(ROOT / "data/raw/richardson_gent_hop_downy_mildew.csv")
    primary = prepare_primary_analysis(trial)
    timing = prepare_timing_analysis(primary)
    weather = load_corvallis_weather(ROOT / "data/raw/corvallis_monthly_weather_2009_2025.csv")
    environment = derive_environment_features(weather)
    return attach_environment_state(timing, primary, environment)


def test_weather_contract_and_external_climatology() -> None:
    weather = load_corvallis_weather(ROOT / "data/raw/corvallis_monthly_weather_2009_2025.csv")
    assert len(weather) == 17 * 4
    assert set(weather["month"]) == {"February", "March", "April", "May"}
    features = derive_environment_features(weather)
    assert set([2017, 2018, 2020, 2021]).issubset(set(features["year"]))
    assert np.isfinite(features["preseason_wetness_z"]).all()
    assert np.isfinite(features["application_wetness_z"]).all()


def test_environment_join_uses_only_nt_as_sentinel() -> None:
    frame = _modelling_frame()
    assert len(frame) == 187
    assert set(frame["year"].unique()) == {2017, 2018, 2020, 2021}
    assert (frame["sentinel_n"] == 5).all()
    expected_2021 = np.sqrt(941.734)
    observed_2021 = float(frame.loc[frame["year"] == 2021, "sentinel_sqrt_audpc"].iloc[0])
    assert np.isclose(observed_2021, expected_2021, atol=1e-9)


def test_loyo_environment_predictions_cover_each_row_once_per_model() -> None:
    frame = _modelling_frame()
    metrics, predictions = leave_one_year_out_environment_models(frame, alpha=10.0)
    assert set(metrics["model"]) == {"baseline", "coarse_weather", "sentinel", "sentinel_gxe"}
    for model in metrics["model"].unique():
        assert len(predictions.loc[predictions["model"] == model]) == len(frame)
    assert (metrics.groupby("model")["held_out_year"].size() == 5).all()


def test_sentinel_improves_locked_unseen_year_benchmark() -> None:
    frame = _modelling_frame()
    metrics, _ = leave_one_year_out_environment_models(frame, alpha=10.0)
    aggregate = metrics.loc[metrics["held_out_year"] == "ALL"].set_index("model")
    assert float(aggregate.loc["sentinel", "rmse"]) < float(aggregate.loc["baseline", "rmse"])
    assert float(aggregate.loc["sentinel", "r2"]) > 0.0


def test_gxe_complexity_fails_promotion_gate_on_locked_data() -> None:
    frame = _modelling_frame()
    metrics, _ = leave_one_year_out_environment_models(frame, alpha=10.0)
    gate = gxe_promotion_gate(metrics)
    assert gate.n_folds == 4
    assert gate.fold_wins == 0
    assert not gate.promoted
    assert gate.aggregate_rmse_candidate > gate.aggregate_rmse_reference
