"""Tests for multi-fidelity candidate progression."""

from __future__ import annotations

import numpy as np

from crop_protection_ps.multifidelity import (
    MultiFidelityConfig,
    evaluate_calibration,
    fit_calibration_models,
    policy_cost_table,
    simulate_candidate_cohort,
    simulate_screening_policies,
    summarise_screening_policies,
)


def test_equal_budget_is_exact() -> None:
    """Every screening policy must consume exactly the same experimental budget."""
    config = MultiFidelityConfig(n_rollouts=500)
    table = policy_cost_table(config)
    assert table["total_cost_units"].nunique() == 1
    assert int(table["total_cost_units"].iloc[0]) == 1040


def test_glasshouse_improves_held_out_calibration() -> None:
    """The controlled DGP must contain useful but imperfect glasshouse-to-field information."""
    rng = np.random.default_rng(1234)
    train = simulate_candidate_cohort(400, rng=rng)
    test = simulate_candidate_cohort(200, rng=rng)
    models = fit_calibration_models(train, ridge_alpha=5.0)
    metrics = evaluate_calibration(models, test).set_index("calibration_model")
    assert metrics.loc["lab_plus_glasshouse", "rmse_field_efficacy"] < metrics.loc[
        "lab_only", "rmse_field_efficacy"
    ]
    assert 0.0 < metrics.loc["lab_plus_glasshouse", "r2_field_efficacy"] < 1.0


def test_multifidelity_policy_is_reproducible() -> None:
    """Fixed seeds must reproduce rollout summaries exactly."""
    config = MultiFidelityConfig(n_rollouts=500, seed=77)
    rng = np.random.default_rng(99)
    calibration = simulate_candidate_cohort(400, rng=rng)
    models = fit_calibration_models(calibration, ridge_alpha=config.ridge_alpha)
    first = summarise_screening_policies(simulate_screening_policies(models, config=config))
    second = summarise_screening_policies(simulate_screening_policies(models, config=config))
    assert first.equals(second)


def test_multifidelity_reduces_controlled_selection_regret() -> None:
    """In the locked DGP the added glasshouse stage should earn its promotion under equal spend."""
    config = MultiFidelityConfig(n_rollouts=800, seed=20260828)
    rng = np.random.default_rng(config.seed)
    calibration = simulate_candidate_cohort(500, rng=rng)
    models = fit_calibration_models(calibration, ridge_alpha=config.ridge_alpha)
    summary = summarise_screening_policies(
        simulate_screening_policies(models, config=config)
    ).set_index("policy")
    assert summary.loc["multifidelity", "mean_simple_regret_field_efficacy"] < summary.loc[
        "lab_field", "mean_simple_regret_field_efficacy"
    ]
    assert summary.loc["multifidelity", "mean_oracle_top_k_recall"] > summary.loc[
        "lab_field", "mean_oracle_top_k_recall"
    ]
