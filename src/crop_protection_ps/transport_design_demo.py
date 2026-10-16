"""Executable transport-design evidence demonstration."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .transport_reaction import TransportReactionConfig, cosine_mode_initial
from .transport_reaction_design import ObservationDesign, cartesian_design, score_observation_design
from .transport_reaction_design_selection import (
    NamedObservationDesign,
    select_robust_observation_design,
)
from .transport_reaction_exact_design import benchmark_greedy_against_exact
from .transport_reaction_robust_design import (
    RobustDesignResult,
    TransportParameterScenario,
    score_design_robustness,
)
from .transport_reaction_sequential_design import ObservationPoint


def _design_payload(design: ObservationDesign) -> dict[str, object]:
    return {
        "n_observations": design.n_observations,
        "time_index": [int(value) for value in design.time_index],
        "cell_index": [int(value) for value in design.cell_index],
    }


def _robust_payload(result: RobustDesignResult) -> dict[str, object]:
    return {
        "nominal_d_optimality": float(result.nominal_d_optimality),
        "mean_d_optimality": float(result.mean_d_optimality),
        "worst_case_d_optimality": float(result.worst_case_d_optimality),
        "worst_case_condition_number": float(result.worst_case_condition_number),
        "rank_deficient_count": int(result.rank_deficient_count),
        "robustly_identifiable": bool(result.robustly_identifiable),
    }


def run_transport_design_demo(root: Path) -> dict[str, object]:
    """Regenerate the synthetic transport-design evidence bundle."""
    config = TransportReactionConfig(
        diffusion=0.035,
        decay_rate=0.18,
        n_cells=49,
        dt=0.002,
        final_time=0.24,
    )
    initial = cosine_mode_initial(config, mean=0.8, amplitude=0.45, mode=1)
    scenarios = (
        TransportParameterScenario(0.020, 0.12),
        TransportParameterScenario(0.020, 0.24),
        TransportParameterScenario(0.035, 0.18),
        TransportParameterScenario(0.055, 0.12),
        TransportParameterScenario(0.055, 0.24),
    )
    center = config.n_cells // 2

    center_temporal = ObservationDesign(
        time_index=np.arange(10, 121, 10, dtype=np.int64),
        cell_index=np.full(12, center, dtype=np.int64),
    )
    final_spatial = ObservationDesign(
        time_index=np.full(12, config.n_steps, dtype=np.int64),
        cell_index=np.asarray([1, 5, 9, 13, 17, 21, 27, 31, 35, 39, 43, 47], dtype=np.int64),
    )
    mixed = cartesian_design(
        np.asarray([20, 50, 80, 110], dtype=np.int64),
        np.asarray([5, 24, 43], dtype=np.int64),
    )

    named = (
        NamedObservationDesign("center-temporal", center_temporal),
        NamedObservationDesign("final-spatial", final_spatial),
        NamedObservationDesign("mixed-space-time", mixed),
    )

    local_scores = {
        candidate.name: {
            "rank": score_observation_design(
                config, initial, candidate.design, noise_sigma=0.003
            ).rank,
            "d_optimality": float(
                score_observation_design(
                    config, initial, candidate.design, noise_sigma=0.003
                ).d_optimality
            ),
        }
        for candidate in named
    }
    robust_scores = {
        candidate.name: _robust_payload(
            score_design_robustness(
                config,
                initial,
                candidate.design,
                scenarios,
                noise_sigma=0.003,
                nominal_index=2,
            )
        )
        for candidate in named
    }
    selection = select_robust_observation_design(
        config,
        initial,
        named,
        scenarios,
        noise_sigma=0.003,
        nominal_index=2,
    )

    seed = ObservationDesign(
        time_index=np.asarray([20, 80], dtype=np.int64),
        cell_index=np.asarray([5, 43], dtype=np.int64),
    )
    pool = (
        ObservationPoint(20, 24),
        ObservationPoint(50, 5),
        ObservationPoint(50, 24),
        ObservationPoint(50, 43),
        ObservationPoint(80, 24),
        ObservationPoint(110, 5),
        ObservationPoint(110, 24),
        ObservationPoint(110, 43),
    )
    benchmark = benchmark_greedy_against_exact(
        config,
        initial,
        seed,
        pool,
        scenarios,
        noise_sigma=0.003,
        nominal_index=2,
        n_additions=4,
    )

    summary: dict[str, object] = {
        "schema_version": 1,
        "evidence_status": "controlled synthetic methods evidence",
        "config": {
            "diffusion": config.diffusion,
            "decay_rate": config.decay_rate,
            "n_cells": config.n_cells,
            "dt": config.dt,
            "final_time": config.final_time,
            "noise_sigma": 0.003,
        },
        "scenarios": [
            {"diffusion": item.diffusion, "decay_rate": item.decay_rate}
            for item in scenarios
        ],
        "designs": {
            "center-temporal": _design_payload(center_temporal),
            "final-spatial": _design_payload(final_spatial),
            "mixed-space-time": _design_payload(mixed),
        },
        "local_scores": local_scores,
        "robust_scores": robust_scores,
        "selected_design": selection.selected.name,
        "seed_design": _design_payload(seed),
        "candidate_pool": [
            {"time_index": point.time_index, "cell_index": point.cell_index}
            for point in pool
        ],
        "sequential_history": [
            {
                "step": step.step,
                "time_index": step.added.time_index,
                "cell_index": step.added.cell_index,
                "worst_case_d_optimality": step.result.worst_case_d_optimality,
            }
            for step in benchmark.greedy.steps
        ],
        "exact_benchmark": {
            "subset_count": benchmark.subset_count,
            "optimal_added": [
                {"time_index": point.time_index, "cell_index": point.cell_index}
                for point in benchmark.optimal.added
            ],
            "optimal_worst_case_d_optimality": benchmark.optimal.result.worst_case_d_optimality,
            "greedy_worst_case_d_optimality": benchmark.greedy_result.worst_case_d_optimality,
            "absolute_gap": benchmark.absolute_gap,
            "relative_gap": benchmark.relative_gap,
        },
        "scope_warning": (
            "Synthetic known-truth observation-design evidence only; not a real crop-protection "
            "sampling, monitoring, regulatory, or cost model."
        ),
    }

    results_dir = root / "results" / "transport_design"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    """CLI entry point."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_transport_design_demo(root), indent=2))


if __name__ == "__main__":
    main()
