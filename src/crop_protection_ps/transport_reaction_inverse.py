"""Known-truth inverse calibration for the verified transport-reaction model.

This module is a controlled scientific-computing demonstration built on the
verified forward solver in :mod:`crop_protection_ps.transport_reaction`.

It does not use empirical crop-protection field data and does not alter any
model-selection decision elsewhere in the repository. Calibration assumes
independent Gaussian observation noise with known standard deviation and
optimises strictly positive diffusion/decay parameters in log space.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import cast

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
    identifiability_relative_se_limit: float = 2.0

    def __post_init__(self) -> None:
        d_low, d_high = self.diffusion_bounds
        k_low, k_high = self.decay_rate_bounds
        if not (0.0 < d_low < d_high):
            raise ValueError("diffusion_bounds must satisfy 0 < lower < upper.")
        if not (0.0 < k_low < k_high):
            raise ValueError("decay_rate_bounds must satisfy 0 < lower < upper.")
        if not d_low <= self.initial_diffusion <= d_high:
            raise ValueError("initial_diffusion must lie inside diffusion_bounds.")
        if not k_low <= self.initial_decay_rate <= k_high:
            raise ValueError("initial_decay_rate must lie inside decay_rate_bounds.")
        if self.max_nfev < 1:
            raise ValueError("max_nfev must be positive.")
        if self.identifiability_condition_limit <= 1.0:
            raise ValueError("identifiability_condition_limit must exceed 1.")
        if self.identifiability_relative_se_limit <= 0.0:
            raise ValueError("identifiability_relative_se_limit must be positive.")


@dataclass(frozen=True)
class InverseCalibrationResult:
    """Recovered physical parameters and local log-parameter diagnostics."""

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


@dataclass(frozen=True)
class HoldoutValidationResult:
    """Predictive diagnostics on observations excluded from inverse fitting."""

    n_observations: int
    rmse: float
    normalized_rmse: float
    gaussian_90_coverage: float
    local_parameter_90_coverage: float | None
    local_parameter_mean_half_width: float | None


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


def normalized_transport_residuals(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    observations: TransportObservationSet,
    *,
    diffusion: float,
    decay_rate: float,
) -> NDArray[np.float64]:
    """Return observation-noise-normalized residuals for fixed parameters."""
    if diffusion <= 0.0:
        raise ValueError("diffusion must be positive.")
    if decay_rate <= 0.0:
        raise ValueError("decay_rate must be positive.")

    trial = replace(
        base_config,
        diffusion=diffusion,
        decay_rate=decay_rate,
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

    def residuals(log_parameters: NDArray[np.float64]) -> NDArray[np.float64]:
        parameters = np.exp(log_parameters)
        return normalized_transport_residuals(
            base_config,
            initial_concentration,
            observations,
            diffusion=float(parameters[0]),
            decay_rate=float(parameters[1]),
        )

    d_bounds = settings.diffusion_bounds
    k_bounds = settings.decay_rate_bounds
    lower_log = np.log(
        np.asarray([d_bounds[0], k_bounds[0]], dtype=np.float64)
    )
    upper_log = np.log(
        np.asarray([d_bounds[1], k_bounds[1]], dtype=np.float64)
    )
    fit = least_squares(
        residuals,
        x0=np.log(
            np.asarray(
                [settings.initial_diffusion, settings.initial_decay_rate],
                dtype=np.float64,
            )
        ),
        bounds=(lower_log, upper_log),
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

    estimate = np.exp(np.asarray(fit.x, dtype=np.float64))
    if covariance is None:
        diffusion_se = None
        decay_se = None
        correlation = None
    else:
        diagonal = np.diag(covariance)
        log_diffusion_se = float(np.sqrt(max(float(diagonal[0]), 0.0)))
        log_decay_se = float(np.sqrt(max(float(diagonal[1]), 0.0)))
        diffusion_se = float(estimate[0] * log_diffusion_se)
        decay_se = float(estimate[1] * log_decay_se)
        denominator = log_diffusion_se * log_decay_se
        correlation = (
            float(covariance[0, 1] / denominator)
            if denominator > 0.0
            else None
        )

    degrees_of_freedom = max(observations.observed.size - 2, 1)
    reduced_chi_square = float(np.sum(residual**2) / degrees_of_freedom)
    normalized_rmse = float(np.sqrt(np.mean(residual**2)))

    tolerance = 1e-6
    at_bound = bool(
        np.any(np.abs(np.asarray(fit.x, dtype=np.float64) - lower_log) <= tolerance)
        or np.any(np.abs(upper_log - np.asarray(fit.x, dtype=np.float64)) <= tolerance)
    )

    relative_diffusion_se = (
        diffusion_se / float(estimate[0])
        if diffusion_se is not None and estimate[0] > 0.0
        else float("inf")
    )
    relative_decay_se = (
        decay_se / float(estimate[1])
        if decay_se is not None and estimate[1] > 0.0
        else float("inf")
    )

    identifiable = bool(
        rank == 2
        and np.isfinite(condition_number)
        and condition_number <= settings.identifiability_condition_limit
        and relative_diffusion_se <= settings.identifiability_relative_se_limit
        and relative_decay_se <= settings.identifiability_relative_se_limit
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
        n_function_evaluations=cast(int, fit.nfev),
    )


def validate_inverse_holdout(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    training: TransportObservationSet,
    holdout: TransportObservationSet,
    fit: InverseCalibrationResult,
) -> HoldoutValidationResult:
    """Evaluate fixed fitted parameters on disjoint, independently observed cells/times.

    Also report a first-order delta-method interval when the local parameter
    covariance is available and the fit is identifiable. Neither interval
    accounts for structural model error or guarantees future-field coverage.
    """
    for observations in (training, holdout):
        if np.any(observations.time_index < 0) or np.any(
            observations.time_index > base_config.n_steps
        ):
            raise ValueError("observation time indices are outside the forward solution.")
        if np.any(observations.cell_index < 0) or np.any(
            observations.cell_index >= base_config.n_cells
        ):
            raise ValueError("observation cell indices are outside the spatial grid.")

    training_pairs = set(
        zip(training.time_index.tolist(), training.cell_index.tolist(), strict=True)
    )
    holdout_pairs = set(
        zip(holdout.time_index.tolist(), holdout.cell_index.tolist(), strict=True)
    )
    if not training_pairs.isdisjoint(holdout_pairs):
        raise ValueError("training and holdout observation locations must be disjoint.")

    prediction = _predict_observations(
        replace(base_config, diffusion=fit.diffusion, decay_rate=fit.decay_rate),
        initial_concentration,
        holdout.time_index,
        holdout.cell_index,
    )
    residual = prediction - holdout.observed
    normalized = residual / holdout.noise_sigma
    # Central 90% normal interval: z_(0.95), conditional on the fitted parameters.
    gaussian_90_half_width = 1.6448536269514722 * holdout.noise_sigma
    local_coverage: float | None = None
    local_half_width: float | None = None
    standard_errors = (fit.diffusion_standard_error, fit.decay_rate_standard_error)
    if (
        fit.success
        and fit.identifiable
        and fit.parameter_correlation is not None
        and all(se is not None and np.isfinite(se) and se >= 0.0 for se in standard_errors)
        and np.isfinite(fit.parameter_correlation)
        and abs(fit.parameter_correlation) <= 1.0
    ):
        diffusion_se, decay_se = standard_errors
        assert diffusion_se is not None and decay_se is not None
        covariance = np.asarray(
            [
                [diffusion_se**2, fit.parameter_correlation * diffusion_se * decay_se],
                [fit.parameter_correlation * diffusion_se * decay_se, decay_se**2],
            ],
            dtype=np.float64,
        )
        # Central differences of held-out predictions in physical parameters.
        gradient = np.empty((holdout.observed.size, 2), dtype=np.float64)
        for column, name in enumerate(("diffusion", "decay_rate")):
            parameter = float(getattr(fit, name))
            step = parameter * 1e-4
            positive = replace(base_config, diffusion=fit.diffusion, decay_rate=fit.decay_rate)
            if name == "diffusion":
                upper_config = replace(positive, diffusion=parameter + step)
                lower_config = replace(positive, diffusion=parameter - step)
            else:
                upper_config = replace(positive, decay_rate=parameter + step)
                lower_config = replace(positive, decay_rate=parameter - step)
            upper = _predict_observations(
                upper_config,
                initial_concentration,
                holdout.time_index,
                holdout.cell_index,
            )
            lower = _predict_observations(
                lower_config,
                initial_concentration,
                holdout.time_index,
                holdout.cell_index,
            )
            gradient[:, column] = (upper - lower) / (2.0 * step)
        parameter_variance = np.einsum("ni,ij,nj->n", gradient, covariance, gradient)
        widths = 1.6448536269514722 * np.sqrt(
            holdout.noise_sigma**2 + np.maximum(parameter_variance, 0.0)
        )
        local_coverage = float(np.mean(np.abs(residual) <= widths))
        local_half_width = float(np.mean(widths))
    return HoldoutValidationResult(
        n_observations=int(holdout.observed.size),
        rmse=float(np.sqrt(np.mean(residual**2))),
        normalized_rmse=float(np.sqrt(np.mean(normalized**2))),
        gaussian_90_coverage=float(np.mean(np.abs(residual) <= gaussian_90_half_width)),
        local_parameter_90_coverage=local_coverage,
        local_parameter_mean_half_width=local_half_width,
    )
