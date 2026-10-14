"""Known-truth inverse calibration for the verified transport-reaction model.

This module is a controlled scientific-computing demonstration built on the
verified forward solver in :mod:`crop_protection_ps.transport_reaction`.

It does not use empirical crop-protection field data and does not alter any
model-selection decision elsewhere in the repository.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares

from .transport_reaction import (
    TransportReactionConfig,
    solve_transport_reaction,
)


@dataclass(frozen=True)
class TransportObservationSet:
    """Synthetic noisy observations sampled from the forward model."""

    time_index: NDArray[np.int64]
    cell_index: NDArray[np.int64]
    observed: NDArray[np.float64]
    noise_sigma: float

    def __post_init__(self) -> None:
        n = self.observed.size
        if self.time_index.shape != (n,):
            raise ValueError("time_index must match observed shape.")
        if self.cell_index.shape != (n,):
            raise ValueError("cell_index must match observed shape.")
        if not np.isfinite(self.observed).all():
            raise ValueError("observed values must be finite.")
        if self.noise_sigma <= 0.0 or not np.isfinite(self.noise_sigma):
            raise ValueError("noise_sigma must be positive and finite.")
        if n < 3:
            raise ValueError("at least three observations are required.")


@dataclass(frozen=True)
class InverseCalibrationConfig:
    """Bounds, starting point and identifiability threshold for calibration."""

    initial_diffusion: float = 0.02
    initial_decay_rate: float = 0.1
    diffusion_bounds: tuple[float, float] = (1e-6, 0.2)
    decay_rate_bounds: tuple[float, float] = (1e-6, 1.0)
    max_nfev: int = 200
    identifiability_condition_limit: float = 1e8

    def __post_init__(self) -> None:
        d_low, d_high = self.diffusion_bounds
        k_low, k_high = self.decay_rate_bounds
        if not (0.0 <= d_low < d_high):
            raise ValueError("diffusion_bounds must satisfy 0 <= lower < upper.")
        if not (0.0 <= k_low < k_high):
            raise ValueError("decay_rate_bounds must satisfy 0 <= lower < upper.")
        if not d_low <= self.initial_diffusion <= d_high:
            raise ValueError("initial_diffusion must lie inside diffusion_bounds.")
        if not k_low <= self.initial_decay_rate <= k_high:
            raise ValueError("initial_decay_rate must lie inside decay_rate_bounds.")
        if self.max_nfev < 1:
            raise ValueError("max_nfev must be positive.")
        if self.identifiability_condition_limit <= 1.0:
            raise ValueError("identifiability_condition_limit must exceed 1.")


@dataclass(frozen=True)
class InverseCalibrationResult:
    """Recovered parameters and local identifiability diagnostics."""

    diffusion: float
    decay_rate: float
    diffusion_standard_error: float | None
    decay_rate_standard_error: float | None
    parameter_correlation: float | None
    jacobian_rank: int
    jacobian_condition_number: float
    identifiable: bool
    normalized_rmse: float
    reduced_chi_square: float
    at_bound: bool
    success: bool
    n_function_evaluations: int


def _validate_observation_grid(
    config: TransportReactionConfig,
    observation_times: NDArray[np.float64],
    cell_indices: NDArray[np.int64],
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    times = np.asarray(observation_times, dtype=np.float64)
    cells = np.asarray(cell_indices, dtype=np.int64)
    if times.ndim != 1 or times.size == 0:
        raise ValueError("observation_times must be a non-empty one-dimensional array.")
    if cells.ndim != 1 or cells.size == 0:
        raise ValueError("cell_indices must be a non-empty one-dimensional array.")
    if not np.isfinite(times).all():
        raise ValueError("observation_times must be finite.")
    if np.any(times < 0.0) or np.any(times > config.final_time):
        raise ValueError("observation_times must lie inside the simulated time interval.")
    if np.any(cells < 0) or np.any(cells >= config.n_cells):
        raise ValueError("cell_indices must lie inside the spatial grid.")

    scaled = times / config.dt
    rounded = np.rint(scaled).astype(np.int64)
    if not np.allclose(scaled, rounded, rtol=0.0, atol=1e-10):
        raise ValueError("observation_times must align with the solver time grid.")

    time_index = np.repeat(rounded, cells.size)
    cell_index = np.tile(cells, rounded.size)
    return time_index, cell_index


def _predict_observations(
    config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    time_index: NDArray[np.int64],
    cell_index: NDArray[np.int64],
) -> NDArray[np.float64]:
    result = solve_transport_reaction(config, initial_concentration)
    prediction = result.concentration[time_index, cell_index]
    return np.asarray(prediction, dtype=np.float64)


def simulate_transport_observations(
    config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    *,
    observation_times: NDArray[np.float64],
    cell_indices: NDArray[np.int64],
    noise_sigma: float,
    seed: int,
) -> TransportObservationSet:
    """Generate reproducible Gaussian-noise observations from known truth."""
    if noise_sigma <= 0.0 or not np.isfinite(noise_sigma):
        raise ValueError("noise_sigma must be positive and finite.")

    time_index, cell_index = _validate_observation_grid(
        config,
        observation_times,
        cell_indices,
    )
    mean = _predict_observations(
        config,
        initial_concentration,
        time_index,
        cell_index,
    )
    rng = np.random.default_rng(seed)
    observed = mean + rng.normal(0.0, noise_sigma, size=mean.shape)
    return TransportObservationSet(
        time_index=time_index,
        cell_index=cell_index,
        observed=np.asarray(observed, dtype=np.float64),
        noise_sigma=noise_sigma,
    )


def calibrate_transport_reaction(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    observations: TransportObservationSet,
    *,
    calibration: InverseCalibrationConfig | None = None,
) -> InverseCalibrationResult:
    """Estimate diffusion and decay and report local identifiability."""
    settings = calibration or InverseCalibrationConfig()

    if np.any(observations.time_index < 0) or np.any(
        observations.time_index > base_config.n_steps
    ):
        raise ValueError("observation time indices are outside the forward solution.")
    if np.any(observations.cell_index < 0) or np.any(
        observations.cell_index >= base_config.n_cells
    ):
        raise ValueError("observation cell indices are outside the spatial grid.")

    def residuals(parameters: NDArray[np.float64]) -> NDArray[np.float64]:
        trial = replace(
            base_config,
            diffusion=float(parameters[0]),
            decay_rate=float(parameters[1]),
        )
        predicted = _predict_observations(
            trial,
            initial_concentration,
            observations.time_index,
            observations.cell_index,
        )
        return np.asarray(
            (predicted - observations.observed) / observations.noise_sigma,
            dtype=np.float64,
        )

    d_bounds = settings.diffusion_bounds
    k_bounds = settings.decay_rate_bounds
    fit = least_squares(
        residuals,
        x0=np.asarray(
            [settings.initial_diffusion, settings.initial_decay_rate],
            dtype=np.float64,
        ),
        bounds=(
            np.asarray([d_bounds[0], k_bounds[0]], dtype=np.float64),
            np.asarray([d_bounds[1], k_bounds[1]], dtype=np.float64),
        ),
        x_scale="jac",
        max_nfev=settings.max_nfev,
    )

    residual = np.asarray(fit.fun, dtype=np.float64)
    jacobian = np.asarray(fit.jac, dtype=np.float64)
    singular_values = np.linalg.svd(jacobian, compute_uv=False)
    positive = singular_values[singular_values > np.finfo(np.float64).eps]
    rank = int(np.linalg.matrix_rank(jacobian))

    if positive.size < 2 or rank < 2:
        condition_number = float("inf")
        covariance = None
    else:
        condition_number = float(positive[0] / positive[-1])
        information = jacobian.T @ jacobian
        try:
            covariance = np.asarray(np.linalg.inv(information), dtype=np.float64)
        except np.linalg.LinAlgError:
            covariance = None
            condition_number = float("inf")

    if covariance is None:
        diffusion_se = None
        decay_se = None
        correlation = None
    else:
        diagonal = np.diag(covariance)
        diffusion_se = float(np.sqrt(max(float(diagonal[0]), 0.0)))
        decay_se = float(np.sqrt(max(float(diagonal[1]), 0.0)))
        denominator = diffusion_se * decay_se
        correlation = (
            float(covariance[0, 1] / denominator)
            if denominator > 0.0
            else None
        )

    degrees_of_freedom = max(observations.observed.size - 2, 1)
    reduced_chi_square = float(np.sum(residual**2) / degrees_of_freedom)
    normalized_rmse = float(np.sqrt(np.mean(residual**2)))

    lower = np.asarray([d_bounds[0], k_bounds[0]], dtype=np.float64)
    upper = np.asarray([d_bounds[1], k_bounds[1]], dtype=np.float64)
    estimate = np.asarray(fit.x, dtype=np.float64)
    scale = np.maximum(upper - lower, 1.0)
    tolerance = 1e-6 * scale
    at_bound = bool(
        np.any(np.abs(estimate - lower) <= tolerance)
        or np.any(np.abs(upper - estimate) <= tolerance)
    )

    identifiable = bool(
        rank == 2
        and np.isfinite(condition_number)
        and condition_number <= settings.identifiability_condition_limit
        and not at_bound
    )

    return InverseCalibrationResult(
        diffusion=float(estimate[0]),
        decay_rate=float(estimate[1]),
        diffusion_standard_error=diffusion_se,
        decay_rate_standard_error=decay_se,
        parameter_correlation=correlation,
        jacobian_rank=rank,
        jacobian_condition_number=condition_number,
        identifiable=identifiable,
        normalized_rmse=normalized_rmse,
        reduced_chi_square=reduced_chi_square,
        at_bound=at_bound,
        success=bool(fit.success),
        n_function_evaluations=int(fit.nfev),
    )
