"""Exact finite-pool benchmark for robust transport observation design.

For a declared seed design, finite candidate pool, and fixed number of
additions, this module exhaustively evaluates every candidate subset and
identifies the exact best subset under the existing robust-design criterion.

This is exact only within the declared finite pool and budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb

import numpy as np
from numpy.typing import NDArray

from .transport_reaction import TransportReactionConfig
from .transport_reaction_design import ObservationDesign
from .transport_reaction_robust_design import (
    RobustDesignResult,
    TransportParameterScenario,
    score_design_robustness,
)
from .transport_reaction_sequential_design import (
    ObservationPoint,
    SequentialDesignResult,
    sequentially_augment_robust_design,
)


@dataclass(frozen=True)
class ExactSubsetResult:
    """One exhaustively scored fixed-budget candidate subset."""

    added: tuple[ObservationPoint, ...]
    result: RobustDesignResult


@dataclass(frozen=True)
class ExactDesignBenchmark:
    """Exact finite-pool optimum and greedy optimality-gap diagnostics."""

    optimal: ExactSubsetResult
    greedy: SequentialDesignResult
    greedy_result: RobustDesignResult
    ranked_subsets: tuple[ExactSubsetResult, ...]
    absolute_gap: float
    relative_gap: float
    subset_count: int


def _append_points(
    seed: ObservationDesign,
    points: tuple[ObservationPoint, ...],
) -> ObservationDesign:
    time_index = np.concatenate(
        (
            seed.time_index,
            np.asarray([point.time_index for point in points], dtype=np.int64),
        )
    )
    cell_index = np.concatenate(
        (
            seed.cell_index,
            np.asarray([point.cell_index for point in points], dtype=np.int64),
        )
    )
    return ObservationDesign(time_index=time_index, cell_index=cell_index)


def benchmark_greedy_against_exact(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    seed: ObservationDesign,
    pool: tuple[ObservationPoint, ...],
    scenarios: tuple[TransportParameterScenario, ...],
    *,
    noise_sigma: float,
    nominal_index: int,
    n_additions: int,
    max_subsets: int = 10_000,
    relative_step: float = 1e-4,
) -> ExactDesignBenchmark:
    """Compare greedy augmentation with the exact finite-pool subset optimum."""
    if n_additions < 1:
        raise ValueError("n_additions must be positive.")
    if n_additions > len(pool):
        raise ValueError("n_additions cannot exceed candidate-pool size.")
    if len(set(pool)) != len(pool):
        raise ValueError("candidate pool must not contain duplicate observations.")
    if max_subsets < 1:
        raise ValueError("max_subsets must be positive.")

    subset_count = comb(len(pool), n_additions)
    if subset_count > max_subsets:
        raise ValueError(
            f"exact benchmark requires {subset_count} subsets, above max_subsets={max_subsets}."
        )

    seed_points = {
        (int(time), int(cell))
        for time, cell in zip(seed.time_index, seed.cell_index, strict=True)
    }
    if any((point.time_index, point.cell_index) in seed_points for point in pool):
        raise ValueError("candidate pool must not repeat seed observations.")

    ranked: list[ExactSubsetResult] = []
    for subset in combinations(sorted(pool), n_additions):
        design = _append_points(seed, subset)
        result = score_design_robustness(
            base_config,
            initial_concentration,
            design,
            scenarios,
            noise_sigma=noise_sigma,
            nominal_index=nominal_index,
            relative_step=relative_step,
        )
        ranked.append(ExactSubsetResult(added=subset, result=result))

    ranked.sort(
        key=lambda item: (
            item.result.robustly_identifiable,
            item.result.worst_case_d_optimality,
            item.result.mean_d_optimality,
            -item.result.worst_case_condition_number
            if np.isfinite(item.result.worst_case_condition_number)
            else float("-inf"),
            tuple((-point.time_index, -point.cell_index) for point in item.added),
        ),
        reverse=True,
    )
    optimal = ranked[0]

    greedy = sequentially_augment_robust_design(
        base_config,
        initial_concentration,
        seed,
        pool,
        scenarios,
        noise_sigma=noise_sigma,
        nominal_index=nominal_index,
        n_additions=n_additions,
        relative_step=relative_step,
    )
    greedy_result = score_design_robustness(
        base_config,
        initial_concentration,
        greedy.final_design,
        scenarios,
        noise_sigma=noise_sigma,
        nominal_index=nominal_index,
        relative_step=relative_step,
    )

    absolute_gap = (
        optimal.result.worst_case_d_optimality
        - greedy_result.worst_case_d_optimality
    )
    tolerance = 1e-10 * max(
        1.0,
        abs(optimal.result.worst_case_d_optimality),
    )
    if absolute_gap < -tolerance:
        raise RuntimeError("greedy score exceeds exact optimum beyond numerical tolerance.")
    absolute_gap = max(absolute_gap, 0.0)
    relative_gap = (
        absolute_gap / optimal.result.worst_case_d_optimality
        if optimal.result.worst_case_d_optimality > 0.0
        else 0.0
    )

    return ExactDesignBenchmark(
        optimal=optimal,
        greedy=greedy,
        greedy_result=greedy_result,
        ranked_subsets=tuple(ranked),
        absolute_gap=float(absolute_gap),
        relative_gap=float(relative_gap),
        subset_count=subset_count,
    )
