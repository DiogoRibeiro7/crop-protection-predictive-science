from __future__ import annotations

import numpy as np
import pytest

from crop_protection_ps.transport_reaction import (
    TransportReactionConfig,
    cosine_mode_initial,
)
from crop_protection_ps.transport_reaction_design import ObservationDesign
from crop_protection_ps.transport_reaction_robust_design import (
    TransportParameterScenario,
)
from crop_protection_ps.transport_reaction_sequential_design import (
    ObservationPoint,
    sequentially_augment_robust_design,
)


def _problem() -> tuple[TransportReactionConfig, np.ndarray]:
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


def _scenarios() -> tuple[TransportParameterScenario, ...]:
    return (
        TransportParameterScenario(diffusion=0.020, decay_rate=0.12),
        TransportParameterScenario(diffusion=0.020, decay_rate=0.24),
        TransportParameterScenario(diffusion=0.035, decay_rate=0.18),
        TransportParameterScenario(diffusion=0.055, decay_rate=0.12),
        TransportParameterScenario(diffusion=0.055, decay_rate=0.24),
    )


def _seed() -> ObservationDesign:
    return ObservationDesign(
        time_index=np.asarray([20, 80], dtype=np.int64),
        cell_index=np.asarray([5, 43], dtype=np.int64),
    )


def _pool() -> tuple[ObservationPoint, ...]:
    return (
        ObservationPoint(20, 24),
        ObservationPoint(50, 5),
        ObservationPoint(50, 24),
        ObservationPoint(50, 43),
        ObservationPoint(80, 24),
        ObservationPoint(110, 5),
        ObservationPoint(110, 24),
        ObservationPoint(110, 43),
    )


def test_sequential_augmentation_is_deterministic_and_grows_budget() -> None:
    config, initial = _problem()

    result = sequentially_augment_robust_design(
        config,
        initial,
        _seed(),
        _pool(),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
        n_additions=4,
    )

    assert len(result.steps) == 4
    assert result.final_design.n_observations == 6
    assert [step.step for step in result.steps] == [1, 2, 3, 4]
    assert len({step.added for step in result.steps}) == 4


def test_worst_case_information_is_non_decreasing_across_accepted_steps() -> None:
    config, initial = _problem()

    result = sequentially_augment_robust_design(
        config,
        initial,
        _seed(),
        _pool(),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
        n_additions=5,
    )
    scores = [
        step.result.worst_case_d_optimality
        for step in result.steps
    ]

    assert all(next_score >= score for score, next_score in zip(scores, scores[1:], strict=True))


def test_candidate_pool_order_does_not_change_selected_sequence() -> None:
    config, initial = _problem()

    first = sequentially_augment_robust_design(
        config,
        initial,
        _seed(),
        _pool(),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
        n_additions=4,
    )
    second = sequentially_augment_robust_design(
        config,
        initial,
        _seed(),
        tuple(reversed(_pool())),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
        n_additions=4,
    )

    assert [step.added for step in first.steps] == [
        step.added for step in second.steps
    ]


def test_sequential_design_rejects_invalid_pool_contracts() -> None:
    config, initial = _problem()
    pool = _pool()

    with pytest.raises(ValueError, match="positive"):
        sequentially_augment_robust_design(
            config,
            initial,
            _seed(),
            pool,
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
            n_additions=0,
        )

    with pytest.raises(ValueError, match="smaller"):
        sequentially_augment_robust_design(
            config,
            initial,
            _seed(),
            pool[:2],
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
            n_additions=3,
        )

    duplicate_pool = (pool[0], pool[0], pool[1])
    with pytest.raises(ValueError, match="duplicate"):
        sequentially_augment_robust_design(
            config,
            initial,
            _seed(),
            duplicate_pool,
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
            n_additions=1,
        )

    repeated_seed = (ObservationPoint(20, 5), pool[1])
    with pytest.raises(ValueError, match="repeat seed"):
        sequentially_augment_robust_design(
            config,
            initial,
            _seed(),
            repeated_seed,
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
            n_additions=1,
        )
