"""Deterministic selection among finite robust observation-design candidates.

This module ranks an explicitly declared finite candidate set using the robust
transport-design diagnostics. Candidates must have equal observation budgets.

Selection uses a hard full-rank-across-scenarios gate, then maximises worst-case
D-optimality. Deterministic secondary keys make ties reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .transport_reaction import TransportReactionConfig
from .transport_reaction_design import ObservationDesign
from .transport_reaction_robust_design import (
    RobustDesignResult,
    TransportParameterScenario,
    score_design_robustness,
)


@dataclass(frozen=True)
class NamedObservationDesign:
    """A named finite-candidate observation design."""

    name: str
    design: ObservationDesign

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("candidate name must be non-empty.")


@dataclass(frozen=True)
class RankedObservationDesign:
    """One scored candidate and its deterministic rank."""

    rank: int
    candidate: NamedObservationDesign
    robust_result: RobustDesignResult
    eligible: bool


@dataclass(frozen=True)
class RobustDesignSelection:
    """Selected robust design plus complete deterministic candidate ranking."""

    selected: NamedObservationDesign
    selected_result: RobustDesignResult
    ranking: tuple[RankedObservationDesign, ...]


def select_robust_observation_design(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    candidates: tuple[NamedObservationDesign, ...],
    scenarios: tuple[TransportParameterScenario, ...],
    *,
    noise_sigma: float,
    nominal_index: int,
    relative_step: float = 1e-4,
) -> RobustDesignSelection:
    """Select the best eligible equal-budget design from a finite candidate set."""
    if not candidates:
        raise ValueError("candidates must contain at least one design.")

    names = [candidate.name for candidate in candidates]
    if len(set(names)) != len(names):
        raise ValueError("candidate names must be unique.")

    budgets = {candidate.design.n_observations for candidate in candidates}
    if len(budgets) != 1:
        raise ValueError("all candidate designs must use the same observation budget.")

    scored: list[tuple[NamedObservationDesign, RobustDesignResult]] = []
    for candidate in candidates:
        result = score_design_robustness(
            base_config,
            initial_concentration,
            candidate.design,
            scenarios,
            noise_sigma=noise_sigma,
            nominal_index=nominal_index,
            relative_step=relative_step,
        )
        scored.append((candidate, result))

    eligible = [
        item for item in scored if item[1].robustly_identifiable
    ]
    if not eligible:
        raise RuntimeError(
            "no candidate remains full rank across all declared scenarios."
        )

    def sort_key(
        item: tuple[NamedObservationDesign, RobustDesignResult],
    ) -> tuple[float, float, float, str]:
        candidate, result = item
        condition_key = (
            -result.worst_case_condition_number
            if result.worst_case_condition_number != float("inf")
            else float("-inf")
        )
        return (
            result.worst_case_d_optimality,
            result.mean_d_optimality,
            condition_key,
            candidate.name,
        )

    ordered_eligible = sorted(
        eligible,
        key=sort_key,
        reverse=True,
    )
    ineligible = sorted(
        (item for item in scored if not item[1].robustly_identifiable),
        key=lambda item: item[0].name,
    )
    ordered = ordered_eligible + ineligible

    ranking = tuple(
        RankedObservationDesign(
            rank=index + 1,
            candidate=candidate,
            robust_result=result,
            eligible=result.robustly_identifiable,
        )
        for index, (candidate, result) in enumerate(ordered)
    )

    selected_candidate, selected_result = ordered_eligible[0]
    return RobustDesignSelection(
        selected=selected_candidate,
        selected_result=selected_result,
        ranking=ranking,
    )
