from __future__ import annotations

import numpy as np
import pytest

from crop_protection_ps.transport_reaction import (
    TransportReactionConfig,
    cosine_mode_initial,
)
from crop_protection_ps.transport_reaction_inverse import (
    InverseCalibrationConfig,
    simulate_transport_observations,
)
from crop_protection_ps.transport_reaction_profile import (
    ProfileLikelihoodConfig,
    profile_transport_reaction,
)


def _identified_problem() -> tuple[
    TransportReactionConfig,
    np.ndarray,
    object,
    InverseCalibrationConfig,
]:
    truth = TransportReactionConfig(
        diffusion=0.035,
        decay_rate=0.18,
        n_cells=48,
        dt=0.002,
        final_time=0.2,
    )
    initial = cosine_mode_initial(
        truth,
        mean=0.8,
        amplitude=0.45,
        mode=1,
    )
    observations = simulate_transport_observations(
        truth,
        initial,
        observation_times=np.asarray(
            [0.02, 0.05, 0.10, 0.15, 0.20],
            dtype=np.float64,
        ),
        cell_indices=np.asarray(
            [3, 9, 15, 23, 31, 39, 45],
            dtype=np.int64,
        ),
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
    return truth, initial, observations, calibration


def test_profile_likelihood_intervals_are_closed_and_contain_truth() -> None:
    truth, initial, observations, calibration = _identified_problem()

    result = profile_transport_reaction(
        truth,
        initial,
        observations,
        calibration=calibration,
        profile=ProfileLikelihoodConfig(n_grid=21),
    )

    assert result.diffusion.interval_closed
    assert result.decay_rate.interval_closed
    assert result.diffusion.lower <= truth.diffusion <= result.diffusion.upper
    assert result.decay_rate.lower <= truth.decay_rate <= result.decay_rate.upper
    assert result.diffusion.accepted_count < result.diffusion.values.size
    assert result.decay_rate.accepted_count < result.decay_rate.values.size
    assert np.all(np.isfinite(result.diffusion.objective_increase))
    assert np.all(np.isfinite(result.decay_rate.objective_increase))
    assert np.min(result.diffusion.objective_increase) >= 0.0
    assert np.min(result.decay_rate.objective_increase) >= 0.0
    assert result.threshold == pytest.approx(3.841458820694124, rel=1e-10)


def test_uniform_profile_leaves_diffusion_interval_open() -> None:
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
    calibration = InverseCalibrationConfig(
        initial_diffusion=0.03,
        initial_decay_rate=0.15,
        diffusion_bounds=(0.001, 0.10),
        decay_rate_bounds=(0.05, 0.40),
        identifiability_condition_limit=1e6,
    )

    result = profile_transport_reaction(
        truth,
        initial,
        observations,
        calibration=calibration,
        profile=ProfileLikelihoodConfig(n_grid=17),
    )

    assert not result.diffusion.interval_closed
    assert not result.diffusion.lower_closed
    assert not result.diffusion.upper_closed
    assert result.diffusion.lower == pytest.approx(
        calibration.diffusion_bounds[0]
    )
    assert result.diffusion.upper == pytest.approx(
        calibration.diffusion_bounds[1]
    )
    assert result.diffusion.accepted_count == result.diffusion.values.size


def test_profile_likelihood_configuration_validates_inputs() -> None:
    with pytest.raises(ValueError, match="n_grid"):
        ProfileLikelihoodConfig(n_grid=7)
    with pytest.raises(ValueError, match="confidence_level"):
        ProfileLikelihoodConfig(confidence_level=1.0)
    with pytest.raises(ValueError, match="nuisance_xatol"):
        ProfileLikelihoodConfig(nuisance_xatol=0.0)
