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
)
from crop_protection_ps.transport_reaction_design_selection import (
    NamedObservationDesign,
    select_robust_observation_design,
)
from crop_protection_ps.transport_reaction_robust_design import (
    TransportParameterScenario,
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


def _candidates(config: TransportReactionConfig) -> tuple[NamedObservationDesign, ...]:
    center = config.n_cells // 2
    center_temporal = NamedObservationDesign(
        name="center-temporal",
        design=ObservationDesign(
            time_index=np.arange(10, 121, 10, dtype=np.int64),
            cell_index=np.full(12, center, dtype=np.int64),
        ),
    )
    final_spatial = NamedObservationDesign(
        name="final-spatial",
        design=ObservationDesign(
            time_index=np.full(12, config.n_steps, dtype=np.int64),
            cell_index=np.asarray(
                [1, 5, 9, 13, 17, 21, 27, 31, 35, 39, 43, 47],
                dtype=np.int64,
            ),
        ),
    )
    mixed = NamedObservationDesign(
        name="mixed-space-time",
        design=cartesian_design(
            np.asarray([20, 50, 80, 110], dtype=np.int64),
            np.asarray([5, 24, 43], dtype=np.int64),
        ),
    )
    return center_temporal, final_spatial, mixed


def test_selector_excludes_rank_deficient_candidate_and_returns_full_ranking() -> None:
    config, initial = _problem()

    result = select_robust_observation_design(
        config,
        initial,
        _candidates(config),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
    )

    assert len(result.ranking) == 3
    assert result.ranking[-1].candidate.name == "center-temporal"
    assert not result.ranking[-1].eligible
    assert result.ranking[-1].robust_result.rank_deficient_count == len(
        _scenarios()
    )

    assert result.selected.name in {"final-spatial", "mixed-space-time"}
    assert result.selected_result.robustly_identifiable
    assert result.ranking[0].candidate.name == result.selected.name
    assert result.ranking[0].eligible


def test_selected_design_maximizes_worst_case_d_optimality_among_eligible() -> None:
    config, initial = _problem()

    result = select_robust_observation_design(
        config,
        initial,
        _candidates(config),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
    )
    eligible_scores = [
        item.robust_result.worst_case_d_optimality
        for item in result.ranking
        if item.eligible
    ]

    assert result.selected_result.worst_case_d_optimality == pytest.approx(
        max(eligible_scores)
    )


def test_selector_is_deterministic_for_candidate_order() -> None:
    config, initial = _problem()
    candidates = _candidates(config)

    first = select_robust_observation_design(
        config,
        initial,
        candidates,
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
    )
    second = select_robust_observation_design(
        config,
        initial,
        tuple(reversed(candidates)),
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
    )

    assert first.selected.name == second.selected.name
    assert [item.candidate.name for item in first.ranking] == [
        item.candidate.name for item in second.ranking
    ]


def test_selector_rejects_inconsistent_budgets_and_duplicate_names() -> None:
    config, initial = _problem()
    candidates = _candidates(config)

    short = NamedObservationDesign(
        name="short",
        design=ObservationDesign(
            time_index=np.asarray([10, 20], dtype=np.int64),
            cell_index=np.asarray([5, 43], dtype=np.int64),
        ),
    )
    with pytest.raises(ValueError, match="same observation budget"):
        select_robust_observation_design(
            config,
            initial,
            (candidates[0], short),
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
        )

    duplicate = NamedObservationDesign(
        name=candidates[0].name,
        design=candidates[1].design,
    )
    with pytest.raises(ValueError, match="unique"):
        select_robust_observation_design(
            config,
            initial,
            (candidates[0], duplicate),
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
        )


def test_selector_fails_when_all_candidates_are_rank_deficient() -> None:
    config, initial = _problem()
    center = config.n_cells // 2
    candidate = NamedObservationDesign(
        name="center-only",
        design=ObservationDesign(
            time_index=np.arange(10, 121, 10, dtype=np.int64),
            cell_index=np.full(12, center, dtype=np.int64),
        ),
    )

    with pytest.raises(RuntimeError, match="no candidate"):
        select_robust_observation_design(
            config,
            initial,
            (candidate,),
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=2,
        )
