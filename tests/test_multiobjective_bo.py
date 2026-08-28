"""Tests for constrained multi-objective Bayesian optimisation."""

from __future__ import annotations

import numpy as np

from crop_protection_ps.multiobjective_bo import (
    BOConfig,
    acquisition_values,
    build_candidate_grid,
    hypervolume_2d,
    oracle_frontier,
    pareto_mask,
    response_features,
    simulate_observations,
    simulate_policies,
    summarise_policies,
)


def test_pareto_mask_and_hypervolume_known_case() -> None:
    """Two-dimensional frontier and hypervolume calculations must match a hand calculation."""
    points = np.asarray([[0.5, 0.9], [0.8, 0.5], [0.4, 0.4]], dtype=np.float64)
    mask = pareto_mask(points)
    assert np.array_equal(mask, np.asarray([True, True, False]))
    assert np.isclose(hypervolume_2d(points), 0.60)


def test_candidate_grid_has_feasible_pareto_frontier() -> None:
    """Controlled DGP must contain feasible and infeasible regions plus a trade-off frontier."""
    config = BOConfig(n_rollouts=10)
    grid = build_candidate_grid(config)
    frontier, hypervolume = oracle_frontier(grid, config)
    feasible = grid.crop_injury <= config.injury_limit
    assert feasible.any()
    assert (~feasible).any()
    assert frontier.size >= 4
    assert hypervolume > 0.0


def test_response_features_are_finite() -> None:
    """Bayesian nonlinear basis must be deterministic and finite."""
    grid = build_candidate_grid(BOConfig(n_rollouts=10))
    features = response_features(grid.x)
    assert features.shape[0] == grid.n_candidates
    assert features.shape[1] >= 12
    assert np.isfinite(features).all()


def test_constrained_acquisition_is_finite_for_unevaluated_candidates() -> None:
    """Posterior constrained-EI acquisition must be well-defined after the initial screen."""
    config = BOConfig(n_rollouts=10)
    grid = build_candidate_grid(config)
    observations = simulate_observations(grid, config, rng=np.random.default_rng(9))
    features = response_features(grid.x)
    evaluated = np.arange(config.n_initial, dtype=np.int64)
    table = acquisition_values(
        grid,
        features,
        evaluated,
        observations,
        config,
        policy="constrained_pareto",
        scalar_weight=0.5,
    )
    remaining = table.loc[~table.index.isin(evaluated), "acquisition"]
    assert np.isfinite(remaining).all()
    assert (remaining >= 0.0).all()
    assert table.loc[evaluated, "acquisition"].eq(-np.inf).all()


def test_policy_simulation_is_reproducible() -> None:
    """Fixed seeds must reproduce paired multi-objective policy summaries exactly."""
    config = BOConfig(n_rollouts=12, n_sequential=8, seed=44)
    first = summarise_policies(simulate_policies(config))
    second = summarise_policies(simulate_policies(config))
    assert first.equals(second)


def test_constrained_pareto_earns_locked_promotion() -> None:
    """Multi-objective policy must outperform efficacy-only search in the locked controlled DGP."""
    config = BOConfig(n_rollouts=18, n_sequential=10, seed=20260828)
    summary = summarise_policies(simulate_policies(config)).set_index("policy")
    assert summary.loc["constrained_pareto", "mean_hypervolume_ratio"] > summary.loc[
        "efficacy_only", "mean_hypervolume_ratio"
    ]
    assert summary.loc["constrained_pareto", "mean_unsafe_evaluation_rate"] < summary.loc[
        "random", "mean_unsafe_evaluation_rate"
    ]
