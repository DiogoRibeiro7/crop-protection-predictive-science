"""Tests for the budget-constrained R&D portfolio decision layer."""

from __future__ import annotations

import numpy as np

from crop_protection_ps.portfolio_decision import (
    PortfolioConfig,
    acquisition_scores,
    expected_development_value,
    initial_posterior,
    run_followup_policy,
    simulate_portfolio_cohort,
    simulate_portfolio_policies,
    solve_budgeted_portfolio,
    summarise_portfolio_policies,
)


def test_knapsack_respects_budget_and_count_constraints() -> None:
    """Terminal selection must be the exact constrained advancement problem."""
    values = np.asarray([12.0, 11.0, 8.0, 7.0], dtype=np.float64)
    costs = np.asarray([7, 6, 4, 3], dtype=np.int64)
    selected, value = solve_budgeted_portfolio(values, costs, budget_units=10, max_advanced=2)
    assert int(costs[selected].sum()) <= 10
    assert selected.size <= 2
    assert np.isclose(value, 19.0)


def test_acquisition_scores_are_finite_and_nonnegative() -> None:
    """Deterministic quadrature acquisition values must be well-defined."""
    config = PortfolioConfig(n_rollouts=20)
    cohort = simulate_portfolio_cohort(config, rng=np.random.default_rng(7))
    state = initial_posterior(cohort, config)
    scores = acquisition_scores(state, cohort, config, config.safety_followup)
    assert np.isfinite(scores["entropy_gain_per_cost"]).all()
    assert np.isfinite(scores["decision_evsi_per_cost"]).all()
    assert (scores["entropy_gain_per_cost"] >= 0.0).all()
    assert (scores["decision_evsi_per_cost"] >= 0.0).all()


def test_equal_budget_policies_spend_the_full_followup_budget() -> None:
    """Uniform, uncertainty and portfolio-VOI policies must spend the same locked budget."""
    config = PortfolioConfig(n_rollouts=20, followup_budget_units=24)
    cohort = simulate_portfolio_cohort(config, rng=np.random.default_rng(11))
    for index, policy in enumerate(("uniform", "uncertainty", "portfolio_voi")):
        result = run_followup_policy(
            cohort,
            config,
            policy=policy,  # type: ignore[arg-type]
            uniform_rng=np.random.default_rng(100 + index),
        )
        assert result["followup_cost_units"] == 24
        assert result["downstream_cost_units"] <= config.downstream_budget_units
        assert result["n_advanced"] <= config.max_advanced


def test_expected_value_is_not_efficacy_ranking() -> None:
    """Reward, cost and safety uncertainty must materially enter the terminal portfolio score."""
    config = PortfolioConfig(n_rollouts=20)
    cohort = simulate_portfolio_cohort(config, rng=np.random.default_rng(17))
    state = initial_posterior(cohort, config)
    value = expected_development_value(state, cohort, config)
    assert not np.array_equal(np.argsort(value), np.argsort(state.efficacy_mean))


def test_portfolio_policy_simulation_is_reproducible() -> None:
    """Fixed seeds must reproduce paired policy summaries exactly."""
    config = PortfolioConfig(n_rollouts=40, seed=77)
    first = summarise_portfolio_policies(simulate_portfolio_policies(config))
    second = summarise_portfolio_policies(simulate_portfolio_policies(config))
    assert first.equals(second)


def test_portfolio_voi_reduces_regret_in_locked_dgp() -> None:
    """Decision-aware follow-up must earn promotion in the controlled portfolio DGP."""
    config = PortfolioConfig(n_rollouts=180, seed=20260828)
    summary = summarise_portfolio_policies(simulate_portfolio_policies(config)).set_index("policy")
    assert summary.loc["portfolio_voi", "mean_oracle_regret"] < summary.loc[
        "uncertainty", "mean_oracle_regret"
    ]
    assert summary.loc["portfolio_voi", "mean_realised_portfolio_value"] > summary.loc[
        "uniform", "mean_realised_portfolio_value"
    ]
