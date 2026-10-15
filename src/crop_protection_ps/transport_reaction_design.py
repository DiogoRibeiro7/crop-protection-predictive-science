"""Prospective observation design for transport-parameter identifiability.

This module uses local finite-difference sensitivities and Fisher information to
compare candidate observation designs before synthetic outcomes are generated.

The criteria are local to a declared nominal parameter point. They do not prove
global identifiability and do not represent real sampling costs or field
monitoring recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .transport_reaction import TransportReactionConfig, solve_transport_reaction


@dataclass(frozen=True)
class ObservationDesign:
    """Paired solver time/cell indices defining an observation design."""

    time_index: NDArray[np.int64]
    cell_index: NDArray[np.int64]

    def __post_init__(self) -> None:
        if self.time_index.ndim != 1 or self.cell_index.ndim != 1:
            raise ValueError("design indices must be one-dimensional.")
        if self.time_index.shape != self.cell_index.shape:
            raise ValueError("time_index and cell_index must have matching shapes.")
        if self.time_index.size < 2:
            raise ValueError("an observation design requires at least two points.")

    @property
    def n_observations(self) -> int:
        """Return the fixed observation budget."""
        return int(self.time_index.size)


@dataclass(frozen=True)
class FisherDesignResult:
    """Local Fisher-information diagnostics for one observation design."""

    design: ObservationDesign
    sensitivities: NDArray[np.float64]
    information: NDArray[np.float64]
    rank: int
    condition_number: float
    log_determinant: float
    d_optimality: float

    @property
    def identifiable(self) -> bool:
        """Whether the local two-parameter information matrix is full rank."""
        return self.rank == 2 and np.isfinite(self.condition_number)


def cartesian_design(
    time_indices: NDArray[np.int64],
    cell_indices: NDArray[np.int64],
) -> ObservationDesign:
    """Return all time × cell combinations as paired observation points."""
    times = np.asarray(time_indices, dtype=np.int64)
    cells = np.asarray(cell_indices, dtype=np.int64)
    if times.ndim != 1 or times.size == 0:
        raise ValueError("time_indices must be a non-empty one-dimensional array.")
    if cells.ndim != 1 or cells.size == 0:
        raise ValueError("cell_indices must be a non-empty one-dimensional array.")
    return ObservationDesign(
        time_index=np.repeat(times, cells.size),
        cell_index=np.tile(cells, times.size),
    )


def validate_design(
    config: TransportReactionConfig,
    design: ObservationDesign,
) -> None:
    """Validate design indices against the forward-solver grid."""
    if np.any(design.time_index < 0) or np.any(design.time_index > config.n_steps):
        raise ValueError("design time indices lie outside the solver time grid.")
    if np.any(design.cell_index < 0) or np.any(design.cell_index >= config.n_cells):
        raise ValueError("design cell indices lie outside the spatial grid.")


def _predictions(
    config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    design: ObservationDesign,
) -> NDArray[np.float64]:
    validate_design(config, design)
    result = solve_transport_reaction(config, initial_concentration)
    return np.asarray(
        result.concentration[design.time_index, design.cell_index],
        dtype=np.float64,
    )


def log_parameter_sensitivities(
    config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    design: ObservationDesign,
    *,
    relative_step: float = 1e-4,
) -> NDArray[np.float64]:
    """Central finite-difference sensitivities to log diffusion and log decay."""
    if relative_step <= 0.0 or relative_step >= 0.1:
        raise ValueError("relative_step must lie strictly between 0 and 0.1.")
    if config.diffusion <= 0.0 or config.decay_rate <= 0.0:
        raise ValueError("nominal diffusion and decay_rate must be positive.")

    log_d = float(np.log(config.diffusion))
    log_k = float(np.log(config.decay_rate))
    sensitivities = np.empty((design.n_observations, 2), dtype=np.float64)

    for column, (log_value, parameter) in enumerate(
        ((log_d, "diffusion"), (log_k, "decay_rate"))
    ):
        plus_value = float(np.exp(log_value + relative_step))
        minus_value = float(np.exp(log_value - relative_step))

        if parameter == "diffusion":
            plus = TransportReactionConfig(
                length=config.length,
                diffusion=plus_value,
                decay_rate=config.decay_rate,
                n_cells=config.n_cells,
                dt=config.dt,
                final_time=config.final_time,
            )
            minus = TransportReactionConfig(
                length=config.length,
                diffusion=minus_value,
                decay_rate=config.decay_rate,
                n_cells=config.n_cells,
                dt=config.dt,
                final_time=config.final_time,
            )
        else:
            plus = TransportReactionConfig(
                length=config.length,
                diffusion=config.diffusion,
                decay_rate=plus_value,
                n_cells=config.n_cells,
                dt=config.dt,
                final_time=config.final_time,
            )
            minus = TransportReactionConfig(
                length=config.length,
                diffusion=config.diffusion,
                decay_rate=minus_value,
                n_cells=config.n_cells,
                dt=config.dt,
                final_time=config.final_time,
            )

        plus_prediction = _predictions(plus, initial_concentration, design)
        minus_prediction = _predictions(minus, initial_concentration, design)
        sensitivities[:, column] = (
            plus_prediction - minus_prediction
        ) / (2.0 * relative_step)

    return sensitivities


def score_observation_design(
    config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    design: ObservationDesign,
    *,
    noise_sigma: float,
    relative_step: float = 1e-4,
) -> FisherDesignResult:
    """Score a design with local Fisher-information diagnostics."""
    if noise_sigma <= 0.0 or not np.isfinite(noise_sigma):
        raise ValueError("noise_sigma must be positive and finite.")

    sensitivity = log_parameter_sensitivities(
        config,
        initial_concentration,
        design,
        relative_step=relative_step,
    ) / noise_sigma
    information = np.asarray(sensitivity.T @ sensitivity, dtype=np.float64)
    singular_values = np.linalg.svd(information, compute_uv=False)
    tolerance = (
        float(singular_values[0]) * 1e-10
        if singular_values.size > 0 and singular_values[0] > 0.0
        else 0.0
    )
    rank = int(np.sum(singular_values > tolerance))

    if rank < 2 or singular_values[-1] <= 0.0:
        condition_number = float("inf")
        log_determinant = float("-inf")
        d_optimality = 0.0
    else:
        condition_number = float(singular_values[0] / singular_values[-1])
        sign, logdet = np.linalg.slogdet(information)
        if sign <= 0.0:
            log_determinant = float("-inf")
            d_optimality = 0.0
        else:
            log_determinant = float(logdet)
            d_optimality = float(np.exp(0.5 * logdet))

    return FisherDesignResult(
        design=design,
        sensitivities=np.asarray(sensitivity, dtype=np.float64),
        information=information,
        rank=rank,
        condition_number=condition_number,
        log_determinant=log_determinant,
        d_optimality=d_optimality,
    )
