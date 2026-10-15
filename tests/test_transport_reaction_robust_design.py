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
from crop_protection_ps.transport_reaction_robust_design import (
    TransportParameterScenario,
    score_design_robustness,
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


def test_robust_mixed_design_remains_full_rank_across_scenarios() -> None:
    config, initial = _problem()
    design = cartesian_design(
        np.asarray([20, 50, 80, 110], dtype=np.int64),
        np.asarray([5, 24, 43], dtype=np.int64),
    )

    result = score_design_robustness(
        config,
        initial,
        design,
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
    )

    assert result.robustly_identifiable
    assert result.rank_deficient_count == 0
    assert result.worst_case_d_optimality > 0.0
    assert result.mean_d_optimality >= result.worst_case_d_optimality
    assert result.nominal_d_optimality > 0.0
    assert np.isfinite(result.worst_case_condition_number)


def test_center_only_design_remains_weak_across_uncertainty_set() -> None:
    config, initial = _problem()
    center = config.n_cells // 2
    design = ObservationDesign(
        time_index=np.arange(10, 121, 10, dtype=np.int64),
        cell_index=np.full(12, center, dtype=np.int64),
    )

    result = score_design_robustness(
        config,
        initial,
        design,
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
    )

    assert not result.robustly_identifiable
    assert result.rank_deficient_count == len(result.scenarios)
    assert result.worst_case_d_optimality == 0.0
    assert result.mean_d_optimality == 0.0
    assert result.nominal_d_optimality == 0.0
    assert not np.isfinite(result.worst_case_condition_number)


def test_robust_aggregation_matches_scenario_scores() -> None:
    config, initial = _problem()
    design = cartesian_design(
        np.asarray([20, 50, 80, 110], dtype=np.int64),
        np.asarray([5, 24, 43], dtype=np.int64),
    )

    result = score_design_robustness(
        config,
        initial,
        design,
        _scenarios(),
        noise_sigma=0.003,
        nominal_index=2,
    )
    scores = np.asarray(
        [item.d_optimality for item in result.scenario_results],
        dtype=np.float64,
    )

    assert result.nominal_d_optimality == pytest.approx(scores[2])
    assert result.mean_d_optimality == pytest.approx(float(np.mean(scores)))
    assert result.worst_case_d_optimality == pytest.approx(float(np.min(scores)))


def test_robust_design_validates_scenarios_and_nominal_index() -> None:
    config, initial = _problem()
    design = cartesian_design(
        np.asarray([20, 50], dtype=np.int64),
        np.asarray([5, 43], dtype=np.int64),
    )

    with pytest.raises(ValueError, match="positive"):
        TransportParameterScenario(diffusion=0.0, decay_rate=0.1)

    with pytest.raises(ValueError, match="at least one"):
        score_design_robustness(
            config,
            initial,
            design,
            (),
            noise_sigma=0.003,
            nominal_index=0,
        )

    with pytest.raises(ValueError, match="nominal_index"):
        score_design_robustness(
            config,
            initial,
            design,
            _scenarios(),
            noise_sigma=0.003,
            nominal_index=99,
        )
