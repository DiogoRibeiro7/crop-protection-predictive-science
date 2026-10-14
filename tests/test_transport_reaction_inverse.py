from __future__ import annotations

import numpy as np
import pytest

from crop_protection_ps.transport_reaction import (
    TransportReactionConfig,
    cosine_mode_initial,
)
from crop_protection_ps.transport_reaction_inverse import (
    InverseCalibrationConfig,
    calibrate_transport_reaction,
    simulate_transport_observations,
)


def _truth_problem() -> tuple[
    TransportReactionConfig,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    config = TransportReactionConfig(
        diffusion=0.035,
        decay_rate=0.18,
        n_cells=48,
        dt=0.002,
        final_time=0.2,
    )
    initial = cosine_mode_initial(
        config,
        mean=0.8,
        amplitude=0.45,
        mode=1,
    )
    observation_times = np.asarray(
        [0.02, 0.05, 0.10, 0.15, 0.20],
        dtype=np.float64,
    )
    cell_indices = np.asarray(
        [3, 9, 15, 23, 31, 39, 45],
        dtype=np.int64,
    )
    return config, initial, observation_times, cell_indices


def test_known_truth_inverse_recovery_is_accurate_and_identifiable() -> None:
    truth, initial, observation_times, cell_indices = _truth_problem()
    observations = simulate_transport_observations(
        truth,
        initial,
        observation_times=observation_times,
        cell_indices=cell_indices,
        noise_sigma=0.003,
        seed=1729,
    )
    calibration = InverseCalibrationConfig(
        initial_diffusion=0.02,
        initial_decay_rate=0.10,
        diffusion_bounds=(0.005, 0.10),
        decay_rate_bounds=(0.05, 0.40),
        identifiability_condition_limit=1e5,
    )

    result = calibrate_transport_reaction(
        truth,
        initial,
        observations,
        calibration=calibration,
    )

    assert result.success
    assert result.identifiable
    assert not result.at_bound
    assert result.jacobian_rank == 2
    assert result.diffusion == pytest.approx(truth.diffusion, rel=0.08)
    assert result.decay_rate == pytest.approx(truth.decay_rate, rel=0.08)
    assert result.diffusion_standard_error is not None
    assert result.decay_rate_standard_error is not None
    assert result.parameter_correlation is not None
    assert abs(result.parameter_correlation) < 0.98
    assert 0.3 < result.reduced_chi_square < 2.0
    assert result.normalized_rmse < 1.5


def test_synthetic_observations_are_reproducible_for_fixed_seed() -> None:
    truth, initial, observation_times, cell_indices = _truth_problem()

    first = simulate_transport_observations(
        truth,
        initial,
        observation_times=observation_times,
        cell_indices=cell_indices,
        noise_sigma=0.005,
        seed=42,
    )
    second = simulate_transport_observations(
        truth,
        initial,
        observation_times=observation_times,
        cell_indices=cell_indices,
        noise_sigma=0.005,
        seed=42,
    )

    np.testing.assert_array_equal(first.time_index, second.time_index)
    np.testing.assert_array_equal(first.cell_index, second.cell_index)
    np.testing.assert_allclose(first.observed, second.observed, rtol=0.0, atol=0.0)


def test_uniform_initial_state_flags_diffusion_as_unidentifiable() -> None:
    truth = TransportReactionConfig(
        diffusion=0.04,
        decay_rate=0.2,
        n_cells=36,
        dt=0.002,
        final_time=0.12,
    )
    initial = np.full(truth.n_cells, 0.75, dtype=np.float64)
    observations = simulate_transport_observations(
        truth,
        initial,
        observation_times=np.asarray(
            [0.02, 0.04, 0.08, 0.12],
            dtype=np.float64,
        ),
        cell_indices=np.asarray(
            [2, 10, 18, 26, 34],
            dtype=np.int64,
        ),
        noise_sigma=0.002,
        seed=7,
    )

    result = calibrate_transport_reaction(
        truth,
        initial,
        observations,
        calibration=InverseCalibrationConfig(
            initial_diffusion=0.03,
            initial_decay_rate=0.15,
            diffusion_bounds=(0.001, 0.10),
            decay_rate_bounds=(0.05, 0.40),
            identifiability_condition_limit=1e6,
        ),
    )

    assert result.success
    assert not result.identifiable
    assert result.jacobian_rank < 2 or not np.isfinite(
        result.jacobian_condition_number
    )


def test_observation_grid_must_align_with_solver_time_grid() -> None:
    truth, initial, _, cell_indices = _truth_problem()

    with pytest.raises(ValueError, match="align"):
        simulate_transport_observations(
            truth,
            initial,
            observation_times=np.asarray([0.013], dtype=np.float64),
            cell_indices=cell_indices,
            noise_sigma=0.003,
            seed=1,
        )


def test_inverse_configuration_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="diffusion_bounds"):
        InverseCalibrationConfig(diffusion_bounds=(0.2, 0.1))
    with pytest.raises(ValueError, match="initial_decay_rate"):
        InverseCalibrationConfig(
            initial_decay_rate=0.8,
            decay_rate_bounds=(0.05, 0.4),
        )
