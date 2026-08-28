"""Tests for applicability-domain and model-risk controls."""

from __future__ import annotations

import numpy as np

from crop_protection_ps.model_risk import (
    ModelRiskConfig,
    applicability_distance,
    build_risk_strata,
    conformal_quantile,
    fit_quadratic_ridge,
    simulate_model_risk_audit,
    summarise_model_risk,
)
from crop_protection_ps.multiobjective_bo import BOConfig, build_candidate_grid


def test_risk_strata_partition_candidate_grid() -> None:
    """Historical, near-shift and far-shift regions must form an exhaustive partition."""
    grid = build_candidate_grid(BOConfig(n_rollouts=1))
    strata = build_risk_strata(grid)
    combined = np.concatenate([strata.in_domain, strata.near_shift, strata.far_shift])
    assert combined.size == grid.n_candidates
    assert np.unique(combined).size == grid.n_candidates
    assert min(strata.in_domain.size, strata.near_shift.size, strata.far_shift.size) > 0


def test_quadratic_ridge_and_distance_are_finite() -> None:
    """Deployment model and applicability score must be deterministic and finite."""
    rng = np.random.default_rng(13)
    x = rng.uniform(0.1, 0.8, size=(40, 3))
    y = 0.2 + 0.5 * x[:, 0] - 0.1 * x[:, 1] ** 2
    model = fit_quadratic_ridge(x, y, alpha=3.0)
    prediction = model.predict(x[:7])
    distance = applicability_distance(x, x[:7], n_neighbors=5)
    assert prediction.shape == (7,)
    assert distance.shape == (7,)
    assert np.isfinite(prediction).all()
    assert np.isfinite(distance).all()
    assert (distance >= 0.0).all()


def test_conformal_quantile_is_monotone_in_coverage() -> None:
    """Higher requested coverage cannot produce a smaller conformal half-width."""
    scores = np.asarray([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float64)
    assert conformal_quantile(scores, 0.90) >= conformal_quantile(scores, 0.70)


def test_model_risk_audit_is_reproducible() -> None:
    """Fixed seeds must reproduce the paired model-risk simulation exactly."""
    config = ModelRiskConfig(n_rollouts=4)
    first, first_example = simulate_model_risk_audit(config)
    second, second_example = simulate_model_risk_audit(config)
    assert first.equals(second)
    assert first_example.equals(second_example)


def test_locked_model_risk_controls_earn_promotion() -> None:
    """Distance scaling and abstention must pass the locked controlled-DGP risk gate."""
    config = ModelRiskConfig(n_rollouts=12)
    metrics, _ = simulate_model_risk_audit(config)
    summary = summarise_model_risk(metrics)
    gate = summary["promotion_gate"]
    assert gate["promoted"] is True
    assert gate["observed_distance_scaled_coverage"] >= 0.90
    assert gate["observed_ood_rejection_rate"] >= 0.95
    assert gate["observed_selective_mae_reduction_percent"] >= 60.0
