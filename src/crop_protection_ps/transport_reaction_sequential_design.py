"""Sequential robust augmentation of transport observation designs.

Starting from a fixed seed design, this module greedily adds one observation at
a time from a declared finite pool. Each candidate augmentation is scored with
the existing finite-scenario robust-design layer.

The procedure is deterministic and transparent. It is not globally optimal.
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


@dataclass(frozen=True, order=True)
class ObservationPoint:
    """One candidate observation identified by solver time and cell index."""

    time_index: int
    cell_index: int

    def __post_init__(self) -> None:
        if self.time_index < 0:
            raise ValueError("time_index must be non-negative.")
        if self.cell_index < 0:
            raise ValueError("cell_index must be non-negative.")


@dataclass(frozen=True)
class SequentialDesignStep:
    """One accepted greedy augmentation decision."""

    step: int
    added: ObservationPoint
    result: RobustDesignResult


@dataclass(frozen=True)
class SequentialDesignResult:
    """Final augmented design and complete greedy decision history."""

    seed: ObservationDesign
    final_design: ObservationDesign
    steps: tuple[SequentialDesignStep, ...]


def _design_points(design: ObservationDesign) -> tuple[ObservationPoint, ...]:
    return tuple(
        ObservationPoint(time_index=int(time), cell_index=int(cell))
        for time, cell in zip(design.time_index, design.cell_index, strict=True)
    )


def _append_point(
    design: ObservationDesign,
    point: ObservationPoint,
) -> ObservationDesign:
    return ObservationDesign(
        time_index=np.append(
            design.time_index,
            np.asarray(point.time_index, dtype=np.int64),
        ),
        cell_index=np.append(
            design.cell_index,
            np.asarray(point.cell_index, dtype=np.int64),
        ),
    )


def sequentially_augment_robust_design(
    base_config: TransportReactionConfig,
    initial_concentration: NDArray[np.float64],
    seed: ObservationDesign,
    pool: tuple[ObservationPoint, ...],
    scenarios: tuple[TransportParameterScenario, ...],
    *,
    noise_sigma: float,
    nominal_index: int,
    n_additions: int,
    relative_step: float = 1e-4,
) -> SequentialDesignResult:
    """Greedily add observations by worst-case robust D-optimality."""
    if n_additions < 1:
        raise ValueError("n_additions must be positive.")
    if len(pool) < n_additions:
        raise ValueError("candidate pool is smaller than n_additions.")
    if len(set(pool)) != len(pool):
        raise ValueError("candidate pool must not contain duplicate observations.")

    seed_points = set(_design_points(seed))
    if any(point in seed_points for point in pool):
        raise ValueError("candidate pool must not repeat seed observations.")

    current = seed
    remaining = list(pool)
    steps: list[SequentialDesignStep] = []

    for step_number in range(1, n_additions + 1):
        scored: list[tuple[ObservationPoint, RobustDesignResult]] = []
        for point in remaining:
            augmented = _append_point(current, point)
            result = score_design_robustness(
                base_config,
                initial_concentration,
                augmented,
                scenarios,
                noise_sigma=noise_sigma,
                nominal_index=nominal_index,
                relative_step=relative_step,
            )
            scored.append((point, result))

        scored.sort(
            key=lambda item: (
                item[1].worst_case_d_optimality,
                item[1].mean_d_optimality,
                -item[1].worst_case_condition_number
                if np.isfinite(item[1].worst_case_condition_number)
                else float("-inf"),
                -item[0].time_index,
                -item[0].cell_index,
            ),
            reverse=True,
        )

        chosen_point, chosen_result = scored[0]
        current = _append_point(current, chosen_point)
        remaining.remove(chosen_point)
        steps.append(
            SequentialDesignStep(
                step=step_number,
                added=chosen_point,
                result=chosen_result,
            )
        )

    return SequentialDesignResult(
        seed=seed,
        final_design=current,
        steps=tuple(steps),
    )
