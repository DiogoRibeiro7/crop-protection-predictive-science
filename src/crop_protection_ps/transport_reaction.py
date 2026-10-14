"""Verified one-dimensional diffusion-decay forward model.

This module is a controlled scientific-computing demonstration. It does not use
the empirical crop-protection field datasets in this repository and does not
change any model-selection decision recorded for those datasets.

The governing equation is

    dc/dt = D d2c/dx2 - k c

on a finite one-dimensional interval with homogeneous no-flux boundaries. The
spatial discretisation is cell-centred finite volume and time integration uses
implicit Euler. The resulting discrete diffusion operator is conservative, so
mass-balance residuals can be checked directly at every time step.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import solve_banded


@dataclass(frozen=True)
class TransportReactionConfig:
    """Numerical and physical configuration for the forward problem."""

    length: float = 1.0
    diffusion: float = 0.02
    decay_rate: float = 0.15
    n_cells: int = 80
    dt: float = 0.0025
    final_time: float = 0.5

    def __post_init__(self) -> None:
        if self.length <= 0.0:
            raise ValueError("length must be positive.")
        if self.diffusion < 0.0:
            raise ValueError("diffusion must be non-negative.")
        if self.decay_rate < 0.0:
            raise ValueError("decay_rate must be non-negative.")
        if self.n_cells < 3:
            raise ValueError("n_cells must be at least 3.")
        if self.dt <= 0.0:
            raise ValueError("dt must be positive.")
        if self.final_time <= 0.0:
            raise ValueError("final_time must be positive.")
        steps = self.final_time / self.dt
        if not np.isclose(steps, round(steps), rtol=0.0, atol=1e-12):
            raise ValueError("final_time must be an integer multiple of dt.")

    @property
    def dx(self) -> float:
        """Return the finite-volume cell width."""
        return self.length / self.n_cells

    @property
    def n_steps(self) -> int:
        """Return the number of implicit Euler updates."""
        return int(round(self.final_time / self.dt))


@dataclass(frozen=True)
class TransportReactionResult:
    """Full forward solution and verification diagnostics."""

    x: NDArray[np.float64]
    time: NDArray[np.float64]
    concentration: NDArray[np.float64]
    mass: NDArray[np.float64]
    mass_balance_residual: NDArray[np.float64]

    @property
    def max_mass_balance_error(self) -> float:
        """Maximum absolute discrete mass-balance residual."""
        if self.mass_balance_residual.size == 0:
            return 0.0
        return float(np.max(np.abs(self.mass_balance_residual)))


def cell_centres(config: TransportReactionConfig) -> NDArray[np.float64]:
    """Return cell-centre coordinates for the finite-volume grid."""
    dx = config.dx
    return (np.arange(config.n_cells, dtype=np.float64) + 0.5) * dx


def _implicit_banded_matrix(config: TransportReactionConfig) -> NDArray[np.float64]:
    """Build the tridiagonal implicit-Euler operator in banded form."""
    n = config.n_cells
    diffusion_number = config.diffusion * config.dt / config.dx**2
    decay_number = config.decay_rate * config.dt

    main = np.full(
        n,
        1.0 + 2.0 * diffusion_number + decay_number,
        dtype=np.float64,
    )
    main[0] = 1.0 + diffusion_number + decay_number
    main[-1] = 1.0 + diffusion_number + decay_number

    banded = np.zeros((3, n), dtype=np.float64)
    banded[0, 1:] = -diffusion_number
    banded[1, :] = main
    banded[2, :-1] = -diffusion_number
    return banded


def solve_transport_reaction(
    config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
) -> TransportReactionResult:
    """Solve the diffusion-decay equation with homogeneous no-flux boundaries."""
    initial = np.asarray(initial_concentration, dtype=np.float64)
    if initial.shape != (config.n_cells,):
        raise ValueError(
            f"initial_concentration must have shape ({config.n_cells},)."
        )
    if not np.isfinite(initial).all():
        raise ValueError("initial_concentration must contain only finite values.")
    if np.any(initial < 0.0):
        raise ValueError("initial_concentration must be non-negative.")

    n_steps = config.n_steps
    time = np.arange(n_steps + 1, dtype=np.float64) * config.dt
    concentration = np.empty(
        (n_steps + 1, config.n_cells),
        dtype=np.float64,
    )
    concentration[0] = initial
    mass = np.empty(n_steps + 1, dtype=np.float64)
    mass[0] = config.dx * float(np.sum(initial))
    residual = np.empty(n_steps, dtype=np.float64)
    banded = _implicit_banded_matrix(config)

    for step in range(n_steps):
        next_state = solve_banded(
            (1, 1),
            banded,
            concentration[step],
            check_finite=True,
        ).astype(np.float64)
        if not np.isfinite(next_state).all():
            raise RuntimeError("Forward solver produced a non-finite state.")
        if np.min(next_state) < -1e-12:
            raise RuntimeError("Forward solver violated non-negativity.")
        next_state = np.maximum(next_state, 0.0)
        concentration[step + 1] = next_state

        next_mass = config.dx * float(np.sum(next_state))
        mass[step + 1] = next_mass
        residual[step] = (
            (1.0 + config.decay_rate * config.dt) * next_mass - mass[step]
        )

    return TransportReactionResult(
        x=cell_centres(config),
        time=time,
        concentration=concentration,
        mass=mass,
        mass_balance_residual=residual,
    )


def uniform_decay_solution(
    initial_value: float,
    time: NDArray[np.float64],
    decay_rate: float,
) -> NDArray[np.float64]:
    """Analytic spatially uniform limiting solution."""
    if initial_value < 0.0:
        raise ValueError("initial_value must be non-negative.")
    if decay_rate < 0.0:
        raise ValueError("decay_rate must be non-negative.")
    t = np.asarray(time, dtype=np.float64)
    if np.any(t < 0.0):
        raise ValueError("time must be non-negative.")
    return initial_value * np.exp(-decay_rate * t)


def cosine_mode_initial(
    config: TransportReactionConfig,
    *,
    mean: float,
    amplitude: float,
    mode: int = 1,
) -> NDArray[np.float64]:
    """Return a non-negative cosine initial condition compatible with no flux."""
    if mean < 0.0:
        raise ValueError("mean must be non-negative.")
    if amplitude < 0.0:
        raise ValueError("amplitude must be non-negative.")
    if amplitude > mean:
        raise ValueError("amplitude must not exceed mean.")
    if mode < 1:
        raise ValueError("mode must be positive.")
    x = cell_centres(config)
    return (
        mean
        + amplitude * np.cos(mode * np.pi * x / config.length)
    ).astype(np.float64)


def cosine_mode_solution(
    config: TransportReactionConfig,
    *,
    mean: float,
    amplitude: float,
    time: float,
    mode: int = 1,
) -> NDArray[np.float64]:
    """Analytic cosine-mode solution for the continuous no-flux problem."""
    if time < 0.0:
        raise ValueError("time must be non-negative.")
    _ = cosine_mode_initial(
        config,
        mean=mean,
        amplitude=amplitude,
        mode=mode,
    )
    x = cell_centres(config)
    wave_number = mode * np.pi / config.length
    mean_component = mean * np.exp(-config.decay_rate * time)
    mode_rate = config.decay_rate + config.diffusion * wave_number**2
    mode_component = amplitude * np.exp(-mode_rate * time)
    return (
        mean_component
        + mode_component * np.cos(wave_number * x)
    ).astype(np.float64)


def relative_l2_error(
    numerical: NDArray[np.float64],
    reference: NDArray[np.float64],
) -> float:
    """Return the relative Euclidean error between two solution vectors."""
    numerical_array = np.asarray(numerical, dtype=np.float64)
    reference_array = np.asarray(reference, dtype=np.float64)
    if numerical_array.shape != reference_array.shape:
        raise ValueError("numerical and reference arrays must have matching shapes.")
    denominator = float(np.linalg.norm(reference_array))
    if denominator == 0.0:
        raise ValueError("reference norm must be positive.")
    return float(np.linalg.norm(numerical_array - reference_array) / denominator)
