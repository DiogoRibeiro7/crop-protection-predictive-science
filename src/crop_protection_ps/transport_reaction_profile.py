"""Profile-likelihood diagnostics for transport-reaction inverse calibration.

This module extends the known-truth inverse demonstration beyond local
Jacobian/covariance diagnostics. It profiles one positive parameter at a time
on a declared log-scale grid while re-optimising the other parameter.

The resulting confidence intervals are likelihood-ratio intervals for the
synthetic Gaussian observation model. They are practical-identifiability
evidence, not proof of global structural identifiability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize_scalar
from scipy.stats import chi2

from .transport_reaction import TransportReactionConfig
from .transport_reaction_inverse import (
    InverseCalibrationConfig,
    TransportObservationSet,
    calibrate_transport_reaction,
    normalized_transport_residuals,
)

ProfileParameter = Literal["diffusion", "decay_rate"]


@dataclass(frozen=True)
class ProfileLikelihoodConfig:
    """Numerical configuration for one-dimensional likelihood profiles."""

    n_grid: int = 31
    confidence_level: float = 0.95
    nuisance_xatol: float = 1e-7
    nuisance_maxiter: int = 200

    def __post_init__(self) -> None:
        if self.n_grid < 9:
            raise ValueError("n_grid must be at least 9.")
        if not 0.0 < self.confidence_level < 1.0:
            raise ValueError("confidence_level must lie strictly between 0 and 1.")
        if self.nuisance_xatol <= 0.0:
            raise ValueError("nuisance_xatol must be positive.")
        if self.nuisance_maxiter < 1:
            raise ValueError("nuisance_maxiter must be positive.")


@dataclass(frozen=True)
class ParameterProfile:
    """Likelihood profile and grid-based confidence interval for one parameter."""

    parameter: ProfileParameter
    values: NDArray[np.float64]
    objective_increase: NDArray[np.float64]
    threshold: float
    lower: float
    upper: float
    lower_closed: bool
    upper_closed: bool
    accepted_count: int

    @property
    def interval_closed(self) -> bool:
        """Whether both confidence-interval endpoints are resolved inside the grid."""
        return self.lower_closed and self.upper_closed


@dataclass(frozen=True)
class TransportProfileLikelihoodResult:
    """Joint optimum plus diffusion and decay profile-likelihood diagnostics."""

    diffusion_mle: float
    decay_rate_mle: float
    minimum_objective: float
    confidence_level: float
    threshold: float
    diffusion: ParameterProfile
    decay_rate: ParameterProfile


def _objective(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    observations: TransportObservationSet,
    *,
    diffusion: float,
    decay_rate: float,
) -> float:
    residual = normalized_transport_residuals(
        base_config,
        initial_concentration,
        observations,
        diffusion=diffusion,
        decay_rate=decay_rate,
    )
    return float(np.sum(residual**2))


def _profile_one_parameter(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    observations: TransportObservationSet,
    *,
    parameter: ProfileParameter,
    grid: NDArray[np.float64],
    nuisance_bounds: tuple[float, float],
    minimum_objective: float,
    threshold: float,
    profile_config: ProfileLikelihoodConfig,
) -> ParameterProfile:
    nuisance_log_bounds = (
        float(np.log(nuisance_bounds[0])),
        float(np.log(nuisance_bounds[1])),
    )
    profile_objective = np.empty(grid.size, dtype=np.float64)

    for index, fixed_value in enumerate(grid):

        def nuisance_objective(log_nuisance: float) -> float:
            nuisance = float(np.exp(log_nuisance))
            if parameter == "diffusion":
                return _objective(
                    base_config,
                    initial_concentration,
                    observations,
                    diffusion=float(fixed_value),
                    decay_rate=nuisance,
                )
            return _objective(
                base_config,
                initial_concentration,
                observations,
                diffusion=nuisance,
                decay_rate=float(fixed_value),
            )

        optimized = minimize_scalar(
            nuisance_objective,
            bounds=nuisance_log_bounds,
            method="bounded",
            options={
                "xatol": profile_config.nuisance_xatol,
                "maxiter": profile_config.nuisance_maxiter,
            },
        )
        if not optimized.success or not np.isfinite(optimized.fun):
            raise RuntimeError(
                f"nuisance optimisation failed while profiling {parameter}."
            )
        profile_objective[index] = float(optimized.fun)

    increase = np.maximum(profile_objective - minimum_objective, 0.0)
    accepted = increase <= threshold
    accepted_indices = np.flatnonzero(accepted)
    if accepted_indices.size == 0:
        raise RuntimeError(
            f"profile grid for {parameter} does not contain the confidence region."
        )

    first = int(accepted_indices[0])
    last = int(accepted_indices[-1])
    return ParameterProfile(
        parameter=parameter,
        values=np.asarray(grid, dtype=np.float64),
        objective_increase=np.asarray(increase, dtype=np.float64),
        threshold=threshold,
        lower=float(grid[first]),
        upper=float(grid[last]),
        lower_closed=first > 0,
        upper_closed=last < grid.size - 1,
        accepted_count=int(accepted_indices.size),
    )


def profile_transport_reaction(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    observations: TransportObservationSet,
    *,
    calibration: InverseCalibrationConfig | None = None,
    profile: ProfileLikelihoodConfig | None = None,
) -> TransportProfileLikelihoodResult:
    """Profile diffusion and decay around the calibrated joint optimum."""
    calibration_config = calibration or InverseCalibrationConfig()
    profile_config = profile or ProfileLikelihoodConfig()

    fit = calibrate_transport_reaction(
        base_config,
        initial_concentration,
        observations,
        calibration=calibration_config,
    )
    if not fit.success:
        raise RuntimeError("joint inverse calibration failed before profiling.")

    minimum_objective = _objective(
        base_config,
        initial_concentration,
        observations,
        diffusion=fit.diffusion,
        decay_rate=fit.decay_rate,
    )
    threshold = float(chi2.ppf(profile_config.confidence_level, df=1))
    if not np.isfinite(threshold) or threshold <= 0.0:
        raise RuntimeError("invalid likelihood-ratio threshold.")

    d_low, d_high = calibration_config.diffusion_bounds
    k_low, k_high = calibration_config.decay_rate_bounds
    diffusion_grid = np.geomspace(
        d_low,
        d_high,
        profile_config.n_grid,
        dtype=np.float64,
    )
    decay_grid = np.geomspace(
        k_low,
        k_high,
        profile_config.n_grid,
        dtype=np.float64,
    )

    diffusion_profile = _profile_one_parameter(
        base_config,
        initial_concentration,
        observations,
        parameter="diffusion",
        grid=diffusion_grid,
        nuisance_bounds=calibration_config.decay_rate_bounds,
        minimum_objective=minimum_objective,
        threshold=threshold,
        profile_config=profile_config,
    )
    decay_profile = _profile_one_parameter(
        base_config,
        initial_concentration,
        observations,
        parameter="decay_rate",
        grid=decay_grid,
        nuisance_bounds=calibration_config.diffusion_bounds,
        minimum_objective=minimum_objective,
        threshold=threshold,
        profile_config=profile_config,
    )

    return TransportProfileLikelihoodResult(
        diffusion_mle=fit.diffusion,
        decay_rate_mle=fit.decay_rate,
        minimum_objective=minimum_objective,
        confidence_level=profile_config.confidence_level,
        threshold=threshold,
        diffusion=diffusion_profile,
        decay_rate=decay_profile,
    )
