from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from crop_protection_ps.transport_reaction import (
    TransportReactionConfig,
    cosine_mode_initial,
)
from crop_protection_ps.transport_reaction_inverse import (
    InverseCalibrationConfig,
    TransportObservationSet,
    _wilson_coverage_interval,
    calibrate_transport_reaction,
    simulate_transport_observations,
    validate_inverse_holdout,
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
    assert result.diffusion_standard_error is not None
    assert result.diffusion_standard_error / result.diffusion > 2.0


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


def test_observation_indices_reject_fractional_and_boolean_locations() -> None:
    truth, initial, times, cells = _truth_problem()

    for invalid in (
        np.asarray([3.7, 9.0, 15.0], dtype=np.float64),
        np.asarray([True, False], dtype=np.bool_),
    ):
        with pytest.raises(ValueError, match="integer grid indices"):
            simulate_transport_observations(
                truth,
                initial,
                observation_times=times,
                cell_indices=invalid,
                noise_sigma=0.003,
                seed=1,
            )

    valid = simulate_transport_observations(
        truth,
        initial,
        observation_times=times,
        cell_indices=cells,
        noise_sigma=0.003,
        seed=1,
    )
    with pytest.raises(ValueError, match="time_index must contain integer"):
        replace(valid, time_index=valid.time_index.astype(np.float64))
    with pytest.raises(ValueError, match="cell_index must contain integer"):
        replace(valid, cell_index=valid.cell_index.astype(np.float64))

    # Explicit construction is subject to the same contract as synthetic generation.
    with pytest.raises(ValueError, match="cell_index must contain integer"):
        TransportObservationSet(
            time_index=valid.time_index,
            cell_index=valid.cell_index.astype(np.float64),
            observed=valid.observed,
            noise_sigma=valid.noise_sigma,
        )


def test_inverse_configuration_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="diffusion_bounds"):
        InverseCalibrationConfig(diffusion_bounds=(0.2, 0.1))
    with pytest.raises(ValueError, match="initial_decay_rate"):
        InverseCalibrationConfig(
            initial_decay_rate=0.8,
            decay_rate_bounds=(0.05, 0.4),
        )


def test_misspecified_noise_scale_is_detected_by_reduced_chi_square() -> None:
    truth, initial, observation_times, cell_indices = _truth_problem()
    observations = simulate_transport_observations(
        truth,
        initial,
        observation_times=observation_times,
        cell_indices=cell_indices,
        noise_sigma=0.01,
        seed=99,
    )
    overconfident = replace(observations, noise_sigma=0.002)

    result = calibrate_transport_reaction(
        truth,
        initial,
        overconfident,
        calibration=InverseCalibrationConfig(
            initial_diffusion=0.02,
            initial_decay_rate=0.10,
            diffusion_bounds=(0.005, 0.10),
            decay_rate_bounds=(0.05, 0.40),
        ),
    )

    assert result.success
    assert result.reduced_chi_square > 5.0


def test_inverse_holdout_is_disjoint_and_detects_predictive_misspecification() -> None:
    truth, initial, _, cell_indices = _truth_problem()
    training = simulate_transport_observations(
        truth,
        initial,
        observation_times=np.asarray([0.02, 0.05, 0.10], dtype=np.float64),
        cell_indices=cell_indices,
        noise_sigma=0.003,
        seed=1729,
    )
    holdout = simulate_transport_observations(
        truth,
        initial,
        observation_times=np.asarray([0.15, 0.20], dtype=np.float64),
        cell_indices=cell_indices,
        noise_sigma=0.003,
        seed=1730,
    )
    fit = calibrate_transport_reaction(
        truth,
        initial,
        training,
        calibration=InverseCalibrationConfig(
            diffusion_bounds=(0.005, 0.10),
            decay_rate_bounds=(0.05, 0.40),
        ),
    )
    evaluated = validate_inverse_holdout(truth, initial, training, holdout, fit)
    misspecified = validate_inverse_holdout(
        truth,
        initial,
        training,
        holdout,
        replace(fit, diffusion=0.10, decay_rate=0.40),
    )

    assert evaluated.n_observations == 14
    assert evaluated.normalized_rmse < 2.0
    assert np.isfinite(evaluated.gaussian_mean_negative_log_likelihood)
    assert 0.0 <= evaluated.gaussian_90_coverage <= 1.0
    lower, upper = evaluated.gaussian_90_coverage_ci95
    assert 0.0 <= lower <= evaluated.gaussian_90_coverage <= upper <= 1.0
    assert upper - lower > 0.1  # Fourteen observations do not tightly resolve coverage.
    assert evaluated.local_parameter_90_coverage is not None
    assert evaluated.local_parameter_mean_negative_log_likelihood is not None
    assert np.isfinite(evaluated.local_parameter_mean_negative_log_likelihood)
    assert evaluated.local_parameter_90_coverage_ci95 is not None
    local_lower, local_upper = evaluated.local_parameter_90_coverage_ci95
    assert local_lower <= evaluated.local_parameter_90_coverage <= local_upper
    assert evaluated.local_parameter_90_coverage >= evaluated.gaussian_90_coverage
    assert evaluated.local_parameter_mean_half_width is not None
    assert evaluated.local_parameter_mean_half_width >= 1.6448536269514722 * 0.003
    assert misspecified.rmse > evaluated.rmse
    assert (
        misspecified.gaussian_mean_negative_log_likelihood
        > evaluated.gaussian_mean_negative_log_likelihood
    )

    assert fit.diffusion_standard_error is not None
    assert fit.decay_rate_standard_error is not None
    widened = validate_inverse_holdout(
        truth,
        initial,
        training,
        holdout,
        replace(
            fit,
            diffusion_standard_error=10.0 * fit.diffusion_standard_error,
            decay_rate_standard_error=10.0 * fit.decay_rate_standard_error,
        ),
    )
    assert widened.local_parameter_mean_half_width is not None
    assert widened.local_parameter_mean_half_width > evaluated.local_parameter_mean_half_width

    excessively_wide = validate_inverse_holdout(
        truth,
        initial,
        training,
        holdout,
        replace(
            fit,
            diffusion_standard_error=10000.0 * fit.diffusion_standard_error,
            decay_rate_standard_error=10000.0 * fit.decay_rate_standard_error,
        ),
    )
    assert excessively_wide.local_parameter_mean_negative_log_likelihood is not None
    assert (
        excessively_wide.local_parameter_mean_negative_log_likelihood
        > evaluated.local_parameter_mean_negative_log_likelihood
    )

    unidentifiable = validate_inverse_holdout(
        truth,
        initial,
        training,
        holdout,
        replace(fit, identifiable=False),
    )
    assert unidentifiable.local_parameter_90_coverage is None
    assert unidentifiable.local_parameter_mean_negative_log_likelihood is None
    assert unidentifiable.local_parameter_90_coverage_ci95 is None
    assert unidentifiable.local_parameter_mean_half_width is None

    with pytest.raises(ValueError, match="disjoint"):
        validate_inverse_holdout(truth, initial, training, training, fit)


def test_wilson_interval_handles_extreme_and_small_sample_coverage() -> None:
    all_missed = _wilson_coverage_interval(0, 14)
    all_covered = _wilson_coverage_interval(14, 14)
    assert all_missed[0] == 0.0
    assert all_missed[1] > 0.0
    assert all_covered[0] < 1.0
    assert all_covered[1] == 1.0
    assert _wilson_coverage_interval(7, 14)[0] < 0.5
    assert _wilson_coverage_interval(7, 14)[1] > 0.5
    with pytest.raises(ValueError, match="coverage counts"):
        _wilson_coverage_interval(2, 1)
