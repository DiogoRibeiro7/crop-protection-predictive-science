"""Finite-scenario robustness diagnostics for transport observation designs.

This module evaluates a fixed observation design across a declared uncertainty
set of positive diffusion/decay parameter scenarios using the existing local
Fisher-information scorer.

The result is a transparent finite-scenario robustness summary. It is not a
continuous minimax solution and it does not imply global identifiability.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .transport_reaction import TransportReactionConfig
from .transport_reaction_design import (
    FisherDesignResult,
    ObservationDesign,
    score_observation_design,
)


@dataclass(frozen=True)
class TransportParameterScenario:
    """One positive diffusion/decay scenario in the robustness set."""

    diffusion: float
    decay_rate: float

    def __post_init__(self) -> None:
        if self.diffusion <= 0.0:
            raise ValueError("diffusion must be positive.")
        if self.decay_rate <= 0.0:
            raise ValueError("decay_rate must be positive.")


@dataclass(frozen=True)
class RobustDesignResult:
    """Scenario-level and aggregate diagnostics for one fixed design."""

    design: ObservationDesign
    scenarios: tuple[TransportParameterScenario, ...]
    scenario_results: tuple[FisherDesignResult, ...]
    nominal_index: int
    nominal_d_optimality: float
    mean_d_optimality: float
    worst_case_d_optimality: float
    worst_case_condition_number: float
    rank_deficient_count: int

    @property
    def robustly_identifiable(self) -> bool:
        """Whether every declared scenario is locally full rank."""
        return self.rank_deficient_count == 0


def score_design_robustness(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    design: ObservationDesign,
    scenarios: tuple[TransportParameterScenario, ...],
    *,
    noise_sigma: float,
    nominal_index: int,
    relative_step: float = 1e-4,
) -> RobustDesignResult:
    """Score one design across a finite declared parameter uncertainty set."""
    if not scenarios:
        raise ValueError("scenarios must contain at least one parameter point.")
    if nominal_index < 0 or nominal_index >= len(scenarios):
        raise ValueError("nominal_index is outside the scenario set.")

    results: list[FisherDesignResult] = []
    for scenario in scenarios:
        config = TransportReactionConfig(
            length=base_config.length,
            diffusion=scenario.diffusion,
            decay_rate=scenario.decay_rate,
            n_cells=base_config.n_cells,
            dt=base_config.dt,
            final_time=base_config.final_time,
        )
        results.append(
            score_observation_design(
                config,
                initial_concentration,
                design,
                noise_sigma=noise_sigma,
                relative_step=relative_step,
            )
        )

    scenario_results = tuple(results)
    d_scores = np.asarray(
        [result.d_optimality for result in scenario_results],
        dtype=np.float64,
    )
    conditions = np.asarray(
        [result.condition_number for result in scenario_results],
        dtype=np.float64,
    )
    rank_deficient_count = sum(
        result.rank < 2 for result in scenario_results
    )

    return RobustDesignResult(
        design=design,
        scenarios=scenarios,
        scenario_results=scenario_results,
        nominal_index=nominal_index,
        nominal_d_optimality=float(d_scores[nominal_index]),
        mean_d_optimality=float(np.mean(d_scores)),
        worst_case_d_optimality=float(np.min(d_scores)),
        worst_case_condition_number=float(np.max(conditions)),
        rank_deficient_count=rank_deficient_count,
    )
