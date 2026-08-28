"""Applicability-domain and selective-prediction controls for scientific model risk.

The audit reuses the controlled formulation/application response surface from the multi-objective
case study. A deliberately compact quadratic efficacy model is trained only inside a historical
support region. Separate in-domain and near-shift calibration sets are then used to define:

1. an in-domain split-conformal interval;
2. a stress-calibrated global interval;
3. a distance-inflated interval whose width grows outside the calibrated applicability domain;
4. an abstention rule based on k-nearest-neighbour distance from historical experimental support.

The final stress test is held out from all threshold and interval calibration. Latent truth is used
only for controlled evaluation; it is never exposed to the fitted deployment model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from crop_protection_ps.multiobjective_bo import BOConfig, CandidateGrid, build_candidate_grid

_DEFAULT_SEED: Final[int] = 20260828


@dataclass(frozen=True)
class ModelRiskConfig:
    """Locked design for the applicability-domain stress audit."""

    n_train: int = 160
    n_calibration_id: int = 100
    n_calibration_shift: int = 120
    n_test_id: int = 120
    n_test_near: int = 180
    n_test_far: int = 220
    n_rollouts: int = 50
    noise_sd: float = 0.035
    ridge_alpha: float = 8.0
    n_neighbors: int = 7
    nominal_coverage: float = 0.90
    acceptance_quantile: float = 0.85
    distance_scale_power: float = 2.0
    seed: int = _DEFAULT_SEED

    def __post_init__(self) -> None:
        counts = (
            self.n_train,
            self.n_calibration_id,
            self.n_calibration_shift,
            self.n_test_id,
            self.n_test_near,
            self.n_test_far,
            self.n_rollouts,
        )
        if min(counts) <= 0:
            raise ValueError("All sample and rollout counts must be positive.")
        if self.noise_sd <= 0.0 or self.ridge_alpha <= 0.0:
            raise ValueError("Noise and ridge scales must be positive.")
        if self.n_neighbors < 1:
            raise ValueError("n_neighbors must be positive.")
        if not 0.5 < self.nominal_coverage < 1.0:
            raise ValueError("nominal_coverage must lie between 0.5 and 1.0.")
        if not 0.0 < self.acceptance_quantile < 1.0:
            raise ValueError("acceptance_quantile must lie strictly between zero and one.")
        if self.distance_scale_power <= 0.0:
            raise ValueError("distance_scale_power must be positive.")


@dataclass(frozen=True)
class RiskStrata:
    """Candidate indices defining historical support and two distribution-shift regimes."""

    in_domain: NDArray[np.int64]
    near_shift: NDArray[np.int64]
    far_shift: NDArray[np.int64]


@dataclass(frozen=True)
class RiskSplit:
    """One fully separated fit/calibration/stress-test split."""

    train: NDArray[np.int64]
    calibration_id: NDArray[np.int64]
    calibration_shift: NDArray[np.int64]
    test_id: NDArray[np.int64]
    test_near: NDArray[np.int64]
    test_far: NDArray[np.int64]


@dataclass(frozen=True)
class QuadraticRidgeModel:
    """Auditable quadratic ridge response surface with explicit standardisation."""

    feature_mean: NDArray[np.float64]
    feature_sd: NDArray[np.float64]
    coefficients: NDArray[np.float64]

    def predict(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """Predict efficacy without clipping extrapolative values."""
        features = quadratic_features(x)
        standardised = (features - self.feature_mean) / self.feature_sd
        design = np.column_stack([np.ones(x.shape[0]), standardised])
        return (design @ self.coefficients).astype(np.float64)


def build_risk_strata(grid: CandidateGrid) -> RiskStrata:
    """Partition the controlled grid into historical support, near shift and far shift.

    The historical region resembles a programme whose experiments have covered moderate doses,
    formulation settings and adjuvant levels but not the search-space extremes. ``far_shift`` is
    reserved for clearly extrapolative edges. The remainder is a ``near_shift`` challenge region.
    """
    x = grid.x
    historical = (
        (x[:, 0] >= 0.12)
        & (x[:, 0] <= 0.72)
        & (x[:, 1] >= 0.12)
        & (x[:, 1] <= 0.86)
        & (x[:, 2] >= 0.08)
        & (x[:, 2] <= 0.78)
    )
    far = (
        (x[:, 0] >= 0.90)
        | (x[:, 1] <= 0.05)
        | (x[:, 1] >= 0.95)
        | (x[:, 2] >= 0.90)
    ) & ~historical
    near = ~historical & ~far
    return RiskStrata(
        in_domain=np.flatnonzero(historical).astype(np.int64),
        near_shift=np.flatnonzero(near).astype(np.int64),
        far_shift=np.flatnonzero(far).astype(np.int64),
    )


def sample_risk_split(
    strata: RiskStrata,
    config: ModelRiskConfig,
    *,
    rng: np.random.Generator,
) -> RiskSplit:
    """Sample non-overlapping fit, calibration and final stress-test candidate sets."""
    required_id = config.n_train + config.n_calibration_id + config.n_test_id
    required_near = config.n_calibration_shift + config.n_test_near
    if strata.in_domain.size < required_id:
        raise ValueError(
            "Historical support does not contain enough candidates for the locked split."
        )
    if strata.near_shift.size < required_near or strata.far_shift.size < config.n_test_far:
        raise ValueError("Shift strata do not contain enough candidates for the locked split.")

    in_domain = rng.permutation(strata.in_domain)
    near = rng.permutation(strata.near_shift)
    far = rng.permutation(strata.far_shift)
    train_end = config.n_train
    cal_end = train_end + config.n_calibration_id
    test_end = cal_end + config.n_test_id
    return RiskSplit(
        train=in_domain[:train_end],
        calibration_id=in_domain[train_end:cal_end],
        calibration_shift=near[: config.n_calibration_shift],
        test_id=in_domain[cal_end:test_end],
        test_near=near[
            config.n_calibration_shift : config.n_calibration_shift + config.n_test_near
        ],
        test_far=far[: config.n_test_far],
    )


def quadratic_features(x: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return a deliberately compact quadratic basis for the deployable efficacy model."""
    if x.ndim != 2 or x.shape[1] != 3:
        raise ValueError("x must have shape (n, 3).")
    d, f, a = x.T
    return np.column_stack(
        [d, f, a, d**2, f**2, a**2, d * f, d * a, f * a]
    ).astype(np.float64)


def fit_quadratic_ridge(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    *,
    alpha: float,
) -> QuadraticRidgeModel:
    """Fit quadratic ridge regression with an unpenalised intercept."""
    if x.shape[0] != y.shape[0] or y.ndim != 1:
        raise ValueError("x and y must contain the same number of rows.")
    if alpha <= 0.0:
        raise ValueError("alpha must be positive.")
    features = quadratic_features(x)
    mean = features.mean(axis=0)
    sd = features.std(axis=0, ddof=0)
    if np.any(sd <= 0.0):
        raise ValueError("Training design contains a constant quadratic feature.")
    standardised = (features - mean) / sd
    design = np.column_stack([np.ones(x.shape[0]), standardised])
    penalty = np.eye(design.shape[1], dtype=np.float64) * alpha
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return QuadraticRidgeModel(
        feature_mean=mean.astype(np.float64),
        feature_sd=sd.astype(np.float64),
        coefficients=coefficients.astype(np.float64),
    )


def applicability_distance(
    train_x: NDArray[np.float64],
    query_x: NDArray[np.float64],
    *,
    n_neighbors: int,
) -> NDArray[np.float64]:
    """Mean k-nearest-neighbour distance after scaling by historical experimental spread."""
    if train_x.ndim != 2 or query_x.ndim != 2 or train_x.shape[1] != query_x.shape[1]:
        raise ValueError(
            "Training and query designs must be two-dimensional with matching columns."
        )
    if not 1 <= n_neighbors <= train_x.shape[0]:
        raise ValueError("n_neighbors must not exceed the historical training size.")
    mean = train_x.mean(axis=0)
    sd = train_x.std(axis=0, ddof=0)
    if np.any(sd <= 0.0):
        raise ValueError("Historical design contains a constant applicability-domain variable.")
    train_scaled = (train_x - mean) / sd
    query_scaled = (query_x - mean) / sd
    difference = query_scaled[:, None, :] - train_scaled[None, :, :]
    distances = np.sqrt(np.sum(difference**2, axis=2))
    nearest = np.partition(distances, n_neighbors - 1, axis=1)[:, :n_neighbors]
    return nearest.mean(axis=1).astype(np.float64)


def conformal_quantile(scores: NDArray[np.float64], coverage: float) -> float:
    """Finite-sample split-conformal order statistic for absolute residual scores."""
    if scores.ndim != 1 or scores.size == 0 or not np.isfinite(scores).all():
        raise ValueError("Conformal scores must be a finite, non-empty one-dimensional array.")
    if not 0.0 < coverage < 1.0:
        raise ValueError("coverage must lie strictly between zero and one.")
    rank = int(np.ceil((scores.size + 1) * coverage))
    index = min(max(rank - 1, 0), scores.size - 1)
    return float(np.sort(scores)[index])


def _mc_interval(values: NDArray[np.float64]) -> dict[str, float]:
    """Return a mean and normal-approximation Monte Carlo 95% interval."""
    mean = float(np.mean(values))
    if values.size < 2:
        return {"mean": mean, "mc95_low": mean, "mc95_high": mean}
    se = float(np.std(values, ddof=1) / np.sqrt(values.size))
    return {
        "mean": mean,
        "mc95_low": mean - 1.96 * se,
        "mc95_high": mean + 1.96 * se,
    }


def _test_arrays(split: RiskSplit) -> tuple[NDArray[np.int64], NDArray[np.str_]]:
    """Return final stress-test indices and human-readable domain labels."""
    indices = np.concatenate([split.test_id, split.test_near, split.test_far]).astype(np.int64)
    labels = np.asarray(
        ["in_domain"] * split.test_id.size
        + ["near_shift"] * split.test_near.size
        + ["far_shift"] * split.test_far.size,
        dtype=str,
    )
    return indices, labels


def evaluate_model_risk_rollout(
    grid: CandidateGrid,
    strata: RiskStrata,
    config: ModelRiskConfig,
    *,
    rollout: int,
) -> tuple[dict[str, float | int], pd.DataFrame]:
    """Run one fully held-out applicability-domain and uncertainty-calibration audit."""
    rng = np.random.default_rng(config.seed + 17 * rollout)
    split = sample_risk_split(strata, config, rng=rng)

    train_observed = grid.efficacy[split.train] + rng.normal(
        0.0, config.noise_sd, split.train.size
    )
    model = fit_quadratic_ridge(
        grid.x[split.train],
        train_observed,
        alpha=config.ridge_alpha,
    )

    distance_id = applicability_distance(
        grid.x[split.train],
        grid.x[split.calibration_id],
        n_neighbors=config.n_neighbors,
    )
    acceptance_threshold = float(np.quantile(distance_id, config.acceptance_quantile))

    calibration_id_observed = grid.efficacy[split.calibration_id] + rng.normal(
        0.0, config.noise_sd, split.calibration_id.size
    )
    calibration_id_pred = model.predict(grid.x[split.calibration_id])
    id_scores = np.abs(calibration_id_observed - calibration_id_pred)
    id_half_width = conformal_quantile(id_scores, config.nominal_coverage)

    calibration = np.concatenate([split.calibration_id, split.calibration_shift])
    calibration_distance = applicability_distance(
        grid.x[split.train],
        grid.x[calibration],
        n_neighbors=config.n_neighbors,
    )
    calibration_observed = grid.efficacy[calibration] + rng.normal(
        0.0, config.noise_sd, calibration.size
    )
    calibration_pred = model.predict(grid.x[calibration])
    calibration_abs_error = np.abs(calibration_observed - calibration_pred)
    global_half_width = conformal_quantile(
        calibration_abs_error,
        config.nominal_coverage,
    )
    calibration_ratio = calibration_distance / acceptance_threshold
    calibration_scale = np.maximum(1.0, calibration_ratio) ** config.distance_scale_power
    scaled_score = calibration_abs_error / calibration_scale
    scaled_base_half_width = conformal_quantile(scaled_score, config.nominal_coverage)

    test_indices, labels = _test_arrays(split)
    test_distance = applicability_distance(
        grid.x[split.train],
        grid.x[test_indices],
        n_neighbors=config.n_neighbors,
    )
    test_ratio = test_distance / acceptance_threshold
    test_scale = np.maximum(1.0, test_ratio) ** config.distance_scale_power
    prediction = model.predict(grid.x[test_indices])
    observed = grid.efficacy[test_indices] + rng.normal(
        0.0, config.noise_sd, test_indices.size
    )
    residual = np.abs(observed - prediction)
    latent_error = np.abs(grid.efficacy[test_indices] - prediction)
    accepted = test_distance <= acceptance_threshold
    out_of_domain = labels != "in_domain"
    scaled_half_width = scaled_base_half_width * test_scale

    if not accepted.any():
        raise RuntimeError("The locked applicability-domain rule accepted no stress-test rows.")

    metrics: dict[str, float | int] = {
        "rollout": rollout,
        "naive_id_interval_coverage": float(np.mean(residual <= id_half_width)),
        "stress_global_interval_coverage": float(np.mean(residual <= global_half_width)),
        "distance_scaled_interval_coverage": float(np.mean(residual <= scaled_half_width)),
        "selective_interval_coverage": float(np.mean(residual[accepted] <= id_half_width)),
        "always_predict_mae": float(np.mean(latent_error)),
        "selective_mae": float(np.mean(latent_error[accepted])),
        "acceptance_rate": float(np.mean(accepted)),
        "ood_rejection_rate": float(np.mean(~accepted[out_of_domain])),
        "in_domain_acceptance_rate": float(np.mean(accepted[~out_of_domain])),
        "far_shift_global_coverage": float(
            np.mean(residual[labels == "far_shift"] <= global_half_width)
        ),
        "far_shift_scaled_coverage": float(
            np.mean(residual[labels == "far_shift"] <= scaled_half_width[labels == "far_shift"])
        ),
        "mean_global_interval_width": float(2.0 * global_half_width),
        "mean_scaled_interval_width": float(np.mean(2.0 * scaled_half_width)),
        "acceptance_threshold": acceptance_threshold,
        "id_half_width": id_half_width,
        "global_half_width": global_half_width,
        "scaled_base_half_width": scaled_base_half_width,
    }

    details = pd.DataFrame(
        {
            "candidate": test_indices,
            "domain": labels,
            "dose": grid.x[test_indices, 0],
            "formulation": grid.x[test_indices, 1],
            "adjuvant": grid.x[test_indices, 2],
            "true_efficacy": grid.efficacy[test_indices],
            "observed_efficacy": observed,
            "prediction": prediction,
            "absolute_latent_error": latent_error,
            "applicability_distance": test_distance,
            "distance_ratio": test_ratio,
            "accepted": accepted,
            "id_interval_half_width": id_half_width,
            "global_interval_half_width": global_half_width,
            "scaled_interval_half_width": scaled_half_width,
        }
    )
    return metrics, details


def simulate_model_risk_audit(
    config: ModelRiskConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run paired model-risk rollouts and retain an auditable example stress set."""
    grid = build_candidate_grid(BOConfig(n_rollouts=1, seed=config.seed))
    strata = build_risk_strata(grid)
    metrics: list[dict[str, float | int]] = []
    example = pd.DataFrame()
    for rollout in range(config.n_rollouts):
        result, details = evaluate_model_risk_rollout(
            grid,
            strata,
            config,
            rollout=rollout,
        )
        metrics.append(result)
        if rollout == 0:
            example = details
    return pd.DataFrame(metrics), example


def summarise_model_risk(metrics: pd.DataFrame) -> dict[str, object]:
    """Summarise model-risk controls and apply the pre-specified promotion gate."""
    required = {
        "naive_id_interval_coverage",
        "stress_global_interval_coverage",
        "distance_scaled_interval_coverage",
        "selective_interval_coverage",
        "always_predict_mae",
        "selective_mae",
        "acceptance_rate",
        "ood_rejection_rate",
        "mean_global_interval_width",
        "mean_scaled_interval_width",
    }
    missing = sorted(required.difference(metrics.columns))
    if missing:
        raise ValueError(f"Missing model-risk metrics: {missing}")

    scaled_minus_global = (
        metrics["distance_scaled_interval_coverage"]
        - metrics["stress_global_interval_coverage"]
    ).to_numpy(dtype=np.float64)
    selective_minus_always = (
        metrics["selective_mae"] - metrics["always_predict_mae"]
    ).to_numpy(dtype=np.float64)
    mean_selective = float(metrics["selective_mae"].mean())
    mean_always = float(metrics["always_predict_mae"].mean())
    mae_reduction = 100.0 * (mean_always - mean_selective) / mean_always

    gate = {
        "minimum_distance_scaled_coverage": 0.90,
        "minimum_selective_coverage": 0.87,
        "minimum_ood_rejection_rate": 0.95,
        "minimum_selective_mae_reduction_percent": 60.0,
        "observed_distance_scaled_coverage": float(
            metrics["distance_scaled_interval_coverage"].mean()
        ),
        "observed_selective_coverage": float(metrics["selective_interval_coverage"].mean()),
        "observed_ood_rejection_rate": float(metrics["ood_rejection_rate"].mean()),
        "observed_selective_mae_reduction_percent": mae_reduction,
        "paired_coverage_gain_scaled_minus_global": _mc_interval(scaled_minus_global),
        "paired_mae_difference_selective_minus_always": _mc_interval(selective_minus_always),
    }
    gate["promoted"] = bool(
        gate["observed_distance_scaled_coverage"] >= gate["minimum_distance_scaled_coverage"]
        and gate["observed_selective_coverage"] >= gate["minimum_selective_coverage"]
        and gate["observed_ood_rejection_rate"] >= gate["minimum_ood_rejection_rate"]
        and gate["observed_selective_mae_reduction_percent"]
        >= gate["minimum_selective_mae_reduction_percent"]
        and gate["paired_coverage_gain_scaled_minus_global"]["mc95_low"] > 0.0
        and gate["paired_mae_difference_selective_minus_always"]["mc95_high"] < 0.0
    )

    metric_names = sorted(required)
    summary_metrics = {
        name: _mc_interval(metrics[name].to_numpy(dtype=np.float64)) for name in metric_names
    }
    return {
        "metrics": summary_metrics,
        "selective_mae_reduction_percent": mae_reduction,
        "promotion_gate": gate,
    }
