from __future__ import annotations

import numpy as np
import pytest

from crop_protection_ps.transport_reaction import (
    TransportReactionConfig,
    cosine_mode_initial,
)
from crop_protection_ps.transport_reaction_design import ObservationDesign
from crop_protection_ps.transport_reaction_exact_design import (
    benchmark_greedy_against_exact,
)
from crop_protection_ps.transport_reaction_robust_design import (
    TransportParameterScenario,
)
from crop_protection_ps.transport_reaction_sequential_design import ObservationPoint


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


def test_exact_benchmark_bounds_greedy_and_reports_gap() -> None:
    config, initial = _problem()

    result = benchmark_greedy_against_exact(
        config,
        initial,
        _seed(),
        _pool(),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
        n_additions=4,
    )

    assert result.subset_count == 70
    assert len(result.ranked_subsets) == 70
    assert result.optimal.result.worst_case_d_optimality + 1e-12 >= (
        result.greedy_result.worst_case_d_optimality
    )
    assert result.absolute_gap >= 0.0
    assert result.relative_gap >= 0.0
    assert result.relative_gap <= 1.0


def test_exact_optimum_is_invariant_to_pool_order() -> None:
    config, initial = _problem()

    first = benchmark_greedy_against_exact(
        config,
        initial,
        _seed(),
        _pool(),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
        n_additions=4,
    )
    second = benchmark_greedy_against_exact(
        config,
        initial,
        _seed(),
        tuple(reversed(_pool())),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
        n_additions=4,
    )

    assert first.optimal.added == second.optimal.added
    assert first.optimal.result.worst_case_d_optimality == pytest.approx(
        second.optimal.result.worst_case_d_optimality
    )
    assert first.relative_gap == pytest.approx(second.relative_gap)


def test_ranked_subsets_are_monotone_by_primary_criterion() -> None:
    config, initial = _problem()

    result = benchmark_greedy_against_exact(
        config,
        initial,
        _seed(),
        _pool(),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
        n_additions=3,
    )
    scores = [
        item.result.worst_case_d_optimality
        for item in result.ranked_subsets
    ]

    assert all(
        left + 1e-12 >= right
        for left, right in zip(scores, scores[1:])
    )


def test_exact_benchmark_rejects_invalid_or_intractable_requests() -> None:
    config, initial = _problem()
    pool = _pool()

    with pytest.raises(ValueError, match="positive"):
        benchmark_greedy_against_exact(
            config,
            initial,
            _seed(),
            pool,
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
            n_additions=0,
        )

    with pytest.raises(ValueError, match="cannot exceed"):
        benchmark_greedy_against_exact(
            config,
            initial,
            _seed(),
            pool,
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
            n_additions=len(pool) + 1,
        )

    with pytest.raises(ValueError, match="duplicate"):
        benchmark_greedy_against_exact(
            config,
            initial,
            _seed(),
            (pool[0], pool[0], pool[1]),
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
            n_additions=1,
        )

    with pytest.raises(ValueError, match="above max_subsets"):
        benchmark_greedy_against_exact(
            config,
            initial,
            _seed(),
            pool,
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
            n_additions=4,
            max_subsets=10,
        )
