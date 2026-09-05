"""CLI demo for constrained multi-objective Bayesian optimisation."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from crop_protection_ps.multiobjective_bo import (
    BOConfig,
    build_candidate_grid,
    oracle_frontier,
    paired_difference,
    simulate_policies,
    summarise_policies,
)


def run_multiobjective_demo(root: Path) -> dict[str, object]:
    """Run the locked v0.8 experiment and persist auditable outputs."""
    config = BOConfig()
    results_dir = root / "results" / "multiobjective_bo"
    figures_dir = results_dir / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    grid = build_candidate_grid(config)
    frontier_indices, oracle_hv = oracle_frontier(grid, config)
    raw = simulate_policies(config)
    summary_table = summarise_policies(raw)
    raw.to_csv(results_dir / "paired_rollout_metrics.csv", index=False)
    summary_table.to_csv(results_dir / "policy_metrics.csv", index=False)

    hv_vs_efficacy = paired_difference(
        raw,
        metric="hypervolume_ratio",
        policy_a="constrained_pareto",
        policy_b="efficacy_only",
    )
    unsafe_vs_random = paired_difference(
        raw,
        metric="unsafe_evaluation_rate",
        policy_a="constrained_pareto",
        policy_b="random",
    )
    indexed = summary_table.set_index("policy")
    hv_pareto = float(indexed.loc["constrained_pareto", "mean_hypervolume_ratio"])
    hv_efficacy = float(indexed.loc["efficacy_only", "mean_hypervolume_ratio"])
    improvement = 100.0 * (hv_pareto - hv_efficacy) / hv_efficacy
    promotion_passed = bool(improvement >= 8.0 and hv_vs_efficacy["mc95_low"] > 0.0)
    promotion_gate = {
        "minimum_hypervolume_improvement_vs_efficacy_only_percent": 8.0,
        "observed_hypervolume_improvement_vs_efficacy_only_percent": improvement,
        "paired_hypervolume_ratio_difference_constrained_pareto_minus_efficacy_only": (
            hv_vs_efficacy
        ),
        "paired_unsafe_rate_difference_constrained_pareto_minus_random": unsafe_vs_random,
        "promoted": promotion_passed,
    }
    (results_dir / "promotion_gate.json").write_text(
        json.dumps(promotion_gate, indent=2), encoding="utf-8"
    )

    frontier = pd.DataFrame(
        {
            "candidate": frontier_indices,
            "dose": grid.x[frontier_indices, 0],
            "formulation": grid.x[frontier_indices, 1],
            "adjuvant": grid.x[frontier_indices, 2],
            "efficacy": grid.efficacy[frontier_indices],
            "environmental_burden": grid.environmental_burden[frontier_indices],
            "crop_injury": grid.crop_injury[frontier_indices],
        }
    )
    frontier.to_csv(results_dir / "oracle_feasible_pareto_frontier.csv", index=False)

    order = ["random", "efficacy_only", "constrained_pareto"]
    plotted = indexed.loc[order]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.bar(plotted.index, plotted["mean_hypervolume_ratio"])
    ax.set_ylabel("Discovered feasible hypervolume / oracle hypervolume")
    ax.set_xlabel("Equal-budget search policy")
    ax.set_ylim(0.0, 1.05)
    ax.set_title("Constrained multi-objective search recovers more of the feasible trade-off")
    ax.tick_params(axis="x", rotation=12)
    fig.tight_layout()
    fig.savefig(figures_dir / "hypervolume_ratio_by_policy.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.bar(plotted.index, plotted["mean_unsafe_evaluation_rate"])
    ax.set_ylabel("Fraction of evaluated conditions violating crop-injury limit")
    ax.set_xlabel("Equal-budget search policy")
    ax.set_ylim(0.0, max(0.45, float(plotted["mean_unsafe_evaluation_rate"].max()) * 1.15))
    ax.set_title("Feasibility-aware acquisition limits unsafe experimentation")
    ax.tick_params(axis="x", rotation=12)
    fig.tight_layout()
    fig.savefig(figures_dir / "unsafe_evaluation_rate.png", dpi=180)
    plt.close(fig)

    summary: dict[str, object] = {
        "release": "0.8.0",
        "scientific_question": (
            "Under a fixed experimental budget, which formulation/application condition should be "
            "tested next when efficacy and environmental burden are competing objectives and crop "
            "injury is a hard safety constraint?"
        ),
        "scope": {
            "status": "controlled synthetic formulation/application optimisation experiment",
            "grid_candidates": grid.n_candidates,
            "initial_evaluations": config.n_initial,
            "sequential_evaluations": config.n_sequential,
            "total_evaluations_per_policy": config.n_initial + config.n_sequential,
            "n_rollouts": config.n_rollouts,
            "injury_limit": config.injury_limit,
            "warning": (
                "Response surfaces, thresholds and design variables are controlled simulation "
                "parameters, not claims about a real formulation or Crop "
                "Protection product."
            ),
        },
        "optimisation_structure": {
            "objective_1": "maximise efficacy",
            "objective_2": "minimise environmental burden",
            "hard_constraint": "crop injury <= injury_limit",
            "surrogate": "independent conjugate Bayesian nonlinear response surfaces",
            "acquisition": (
                "ParEGO-style deterministic scalarised expected improvement multiplied by "
                "posterior feasibility probability"
            ),
            "evaluation": (
                "true feasible two-objective hypervolume on a hidden finite candidate grid"
            ),
        },
        "oracle": {
            "n_feasible_pareto_candidates": int(frontier_indices.size),
            "feasible_pareto_hypervolume": oracle_hv,
        },
        "equal_budget_policy_results": {
            policy: {
                "mean_hypervolume_ratio": float(indexed.loc[policy, "mean_hypervolume_ratio"]),
                "mean_unsafe_evaluation_rate": float(
                    indexed.loc[policy, "mean_unsafe_evaluation_rate"]
                ),
                "mean_oracle_frontier_recall": float(
                    indexed.loc[policy, "mean_oracle_frontier_recall"]
                ),
                "mean_balanced_high_value_evaluated": float(
                    indexed.loc[policy, "mean_n_balanced_high_value_evaluated"]
                ),
            }
            for policy in order
        },
        "promotion_gate": promotion_gate,
        "interpretation": (
            "An efficacy-only optimiser can find potent conditions while systematically neglecting "
            "the environmental objective. Constrained multi-objective acquisition instead searches "
            "for feasible efficacy-versus-burden trade-offs and explicitly accounts for posterior "
            "uncertainty about crop injury."
        ),
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    """CLI entry point."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_multiobjective_demo(root), indent=2))


if __name__ == "__main__":
    main()
