from __future__ import annotations

import numpy as np
import pytest

from crop_protection_ps.transport_reaction import (
    TransportReactionConfig,
    cosine_mode_initial,
    cosine_mode_solution,
    relative_l2_error,
    solve_transport_reaction,
    uniform_decay_solution,
)


def test_transport_config_validates_physical_and_numerical_inputs() -> None:
    with pytest.raises(ValueError, match="diffusion"):
        TransportReactionConfig(diffusion=-0.1)
    with pytest.raises(ValueError, match="decay_rate"):
        TransportReactionConfig(decay_rate=-0.1)
    with pytest.raises(ValueError, match="integer multiple"):
        TransportReactionConfig(dt=0.03, final_time=0.1)


def test_uniform_state_matches_analytic_decay_limit() -> None:
    config = TransportReactionConfig(
        diffusion=0.04,
        decay_rate=0.25,
        n_cells=40,
        dt=0.0005,
        final_time=0.1,
    )
    initial = np.full(config.n_cells, 0.8, dtype=np.float64)

    result = solve_transport_reaction(config, initial)
    analytic = uniform_decay_solution(0.8, result.time, config.decay_rate)

    assert np.max(np.ptp(result.concentration, axis=1)) < 1e-12
    assert result.concentration[-1, 0] == pytest.approx(
        analytic[-1],
        rel=2e-5,
    )


def test_solver_preserves_finite_nonnegative_states() -> None:
    config = TransportReactionConfig(
        diffusion=0.08,
        decay_rate=0.2,
        n_cells=60,
        dt=0.001,
        final_time=0.08,
    )
    x = (np.arange(config.n_cells, dtype=np.float64) + 0.5) * config.dx
    initial = np.exp(-((x - 0.35) / 0.08) ** 2)

    result = solve_transport_reaction(config, initial)

    assert np.isfinite(result.concentration).all()
    assert np.min(result.concentration) >= 0.0
    assert np.all(np.diff(result.mass) <= 1e-12)


def test_discrete_no_flux_mass_balance_closes() -> None:
    config = TransportReactionConfig(
        diffusion=0.07,
        decay_rate=0.3,
        n_cells=50,
        dt=0.001,
        final_time=0.05,
    )
    initial = cosine_mode_initial(
        config,
        mean=0.7,
        amplitude=0.25,
    )

    result = solve_transport_reaction(config, initial)

    assert result.max_mass_balance_error < 2e-14


def test_zero_decay_conserves_total_mass() -> None:
    config = TransportReactionConfig(
        diffusion=0.05,
        decay_rate=0.0,
        n_cells=50,
        dt=0.001,
        final_time=0.05,
    )
    initial = cosine_mode_initial(
        config,
        mean=0.6,
        amplitude=0.3,
    )

    result = solve_transport_reaction(config, initial)

    assert result.mass[-1] == pytest.approx(result.mass[0], abs=2e-13)


def test_cosine_mode_error_decreases_under_grid_refinement() -> None:
    errors: list[float] = []
    for n_cells, n_steps in ((20, 20), (40, 80), (80, 320)):
        final_time = 0.02
        config = TransportReactionConfig(
            diffusion=0.05,
            decay_rate=0.1,
            n_cells=n_cells,
            dt=final_time / n_steps,
            final_time=final_time,
        )
        initial = cosine_mode_initial(
            config,
            mean=0.8,
            amplitude=0.35,
        )
        result = solve_transport_reaction(config, initial)
        reference = cosine_mode_solution(
            config,
            mean=0.8,
            amplitude=0.35,
            time=final_time,
        )
        errors.append(relative_l2_error(result.concentration[-1], reference))

    assert errors[1] < errors[0]
    assert errors[2] < errors[1]
    assert errors[2] < 0.3 * errors[0]


def test_initial_state_validation_rejects_invalid_states() -> None:
    config = TransportReactionConfig(n_cells=10, dt=0.01, final_time=0.1)

    with pytest.raises(ValueError, match="shape"):
        solve_transport_reaction(config, np.ones(9))
    with pytest.raises(ValueError, match="finite"):
        invalid = np.ones(10)
        invalid[2] = np.nan
        solve_transport_reaction(config, invalid)
    with pytest.raises(ValueError, match="non-negative"):
        invalid = np.ones(10)
        invalid[2] = -0.1
        solve_transport_reaction(config, invalid)
