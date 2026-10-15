from __future__ import annotations

import numpy as np
import pytest

from crop_protection_ps.transport_reaction import (
    TransportReactionConfig,
    cosine_mode_initial,
)
from crop_protection_ps.transport_reaction_design import (
    ObservationDesign,
    cartesian_design,
    score_observation_design,
)


def _nominal_problem() -> tuple[TransportReactionConfig, np.ndarray]:
    config = TransportReactionConfig(
        diffusion=0.035,
        decay_rate=0.18,
        n_cells=49,
        dt=0.002,
        final_time=0.24,
    )
    initial = cosine_mode_initial(
        config,
        mean=0.8,
        amplitude=0.45,
        mode=1,
    )
    return config, initial


def test_uniform_initial_condition_has_no_diffusion_information() -> None:
    config, _ = _nominal_problem()
    uniform = np.full(config.n_cells, 0.8, dtype=np.float64)
    design = cartesian_design(
        np.asarray([20, 50, 80, 110], dtype=np.int64),
        np.asarray([5, 24, 43], dtype=np.int64),
    )

    result = score_observation_design(
        config,
        uniform,
        design,
        noise_sigma=0.003,
    )

    assert result.rank == 1
    assert not result.identifiable
    assert result.d_optimality == 0.0
    assert not np.isfinite(result.condition_number)
    assert np.max(np.abs(result.sensitivities[:, 0])) < 1e-7


def test_equal_budget_designs_expose_and_break_center_sampling_degeneracy() -> None:
    config, initial = _nominal_problem()
    center = config.n_cells // 2

    center_temporal = ObservationDesign(
        time_index=np.arange(10, 121, 10, dtype=np.int64),
        cell_index=np.full(12, center, dtype=np.int64),
    )
    final_spatial = ObservationDesign(
        time_index=np.full(12, config.n_steps, dtype=np.int64),
        cell_index=np.asarray(
            [1, 5, 9, 13, 17, 21, 27, 31, 35, 39, 43, 47],
            dtype=np.int64,
        ),
    )
    mixed = cartesian_design(
        np.asarray([20, 50, 80, 110], dtype=np.int64),
        np.asarray([5, 24, 43], dtype=np.int64),
    )

    center_result = score_observation_design(
        config,
        initial,
        center_temporal,
        noise_sigma=0.003,
    )
    spatial_result = score_observation_design(
        config,
        initial,
        final_spatial,
        noise_sigma=0.003,
    )
    mixed_result = score_observation_design(
        config,
        initial,
        mixed,
        noise_sigma=0.003,
    )

    assert center_temporal.n_observations == 12
    assert final_spatial.n_observations == 12
    assert mixed.n_observations == 12

    assert not center_result.identifiable
    assert center_result.d_optimality == 0.0

    assert spatial_result.identifiable
    assert mixed_result.identifiable
    assert spatial_result.d_optimality > center_result.d_optimality
    assert mixed_result.d_optimality > center_result.d_optimality
    assert np.isfinite(spatial_result.condition_number)
    assert np.isfinite(mixed_result.condition_number)


def test_design_information_scales_with_observation_noise() -> None:
    config, initial = _nominal_problem()
    design = cartesian_design(
        np.asarray([20, 50, 80, 110], dtype=np.int64),
        np.asarray([5, 24, 43], dtype=np.int64),
    )

    low_noise = score_observation_design(
        config,
        initial,
        design,
        noise_sigma=0.003,
    )
    high_noise = score_observation_design(
        config,
        initial,
        design,
        noise_sigma=0.006,
    )

    np.testing.assert_allclose(
        high_noise.information,
        low_noise.information / 4.0,
        rtol=1e-10,
        atol=1e-12,
    )
    assert high_noise.d_optimality == pytest.approx(
        low_noise.d_optimality / 4.0,
        rel=1e-10,
    )


def test_design_validation_rejects_invalid_inputs() -> None:
    config, initial = _nominal_problem()

    with pytest.raises(ValueError, match="matching shapes"):
        ObservationDesign(
            time_index=np.asarray([1, 2], dtype=np.int64),
            cell_index=np.asarray([1, 2, 3], dtype=np.int64),
        )

    invalid = ObservationDesign(
        time_index=np.asarray([1, config.n_steps + 1], dtype=np.int64),
        cell_index=np.asarray([1, 2], dtype=np.int64),
    )
    with pytest.raises(ValueError, match="time indices"):
        score_observation_design(
            config,
            initial,
            invalid,
            noise_sigma=0.003,
        )

    valid = ObservationDesign(
        time_index=np.asarray([1, 2], dtype=np.int64),
        cell_index=np.asarray([1, 2], dtype=np.int64),
    )
    with pytest.raises(ValueError, match="noise_sigma"):
        score_observation_design(
            config,
            initial,
            valid,
            noise_sigma=0.0,
        )
