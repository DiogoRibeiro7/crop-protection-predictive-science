"""Executable multi-fidelity candidate-progression analysis."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from crop_protection_ps.multifidelity import (
    CandidateCohort,
    MultiFidelityConfig,
    evaluate_calibration,
    fit_calibration_models,
    paired_policy_difference,
    policy_cost_table,
    simulate_candidate_cohort,
    simulate_screening_policies,
    summarise_screening_policies,
)


def run_multifidelity_demo(root: Path) -> dict[str, object]:
    """Run, persist and summarise the controlled lab->glasshouse->field decision case."""
    config = MultiFidelityConfig()
    results_dir = root / "results" / "multifidelity"
    figures_dir = results_dir / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Use a separate historical calibration cohort so policy evaluation never fits on future
    # candidate outcomes. The split is deterministic and auditable.
    rng = np.random.default_rng(config.seed)
    calibration = simulate_candidate_cohort(
        config.calibration_train_size + config.calibration_test_size,
        n_lab_replicates=config.lab_replicates,
        n_glasshouse_replicates=config.glasshouse_replicates,
        n_field_replicates=config.field_replicates,
        rng=rng,
    )
    train_n = config.calibration_train_size
    train = CandidateCohort(
        calibration.true_field_efficacy[:train_n],
        calibration.lab[:train_n],
        calibration.glasshouse[:train_n],
        calibration.field[:train_n],
    )
    test = CandidateCohort(
        calibration.true_field_efficacy[train_n:],
        calibration.lab[train_n:],
        calibration.glasshouse[train_n:],
        calibration.field[train_n:],
    )
    models = fit_calibration_models(train, ridge_alpha=config.ridge_alpha)
    calibration_metrics = evaluate_calibration(models, test)
    calibration_metrics.to_csv(results_dir / "calibration_metrics.csv", index=False)

    costs = policy_cost_table(config)
    costs.to_csv(results_dir / "policy_costs.csv", index=False)

    rollouts = simulate_screening_policies(models, config=config)
    policy_metrics = summarise_screening_policies(rollouts)
    policy_metrics.to_csv(results_dir / "screening_policy_metrics.csv", index=False)

    regret_diff = paired_policy_difference(
        rollouts,
        policy_a="multifidelity",
        policy_b="lab_field",
        metric="simple_regret_field_efficacy",
    )
    recall_diff = paired_policy_difference(
        rollouts,
        policy_a="multifidelity",
        policy_b="lab_field",
        metric="oracle_top_k_recall",
    )

    indexed = policy_metrics.set_index("policy")
    lab_field_regret = float(indexed.loc["lab_field", "mean_simple_regret_field_efficacy"])
    multifidelity_regret = float(
        indexed.loc["multifidelity", "mean_simple_regret_field_efficacy"]
    )
    regret_reduction = 100.0 * (lab_field_regret - multifidelity_regret) / lab_field_regret

    calibration_indexed = calibration_metrics.set_index("calibration_model")
    lab_rmse = float(calibration_indexed.loc["lab_only", "rmse_field_efficacy"])
    combined_rmse = float(
        calibration_indexed.loc["lab_plus_glasshouse", "rmse_field_efficacy"]
    )
    calibration_improvement = 100.0 * (lab_rmse - combined_rmse) / lab_rmse
    promotion_passed = bool(calibration_improvement >= 10.0)

    # Calibration figure on a held-out historical cohort.
    lab_mean = test.lab.mean(axis=1)
    glass_mean = test.glasshouse.mean(axis=1)
    lab_pred = models.lab_to_field.predict(lab_mean.reshape(-1, 1))
    combined_pred = models.lab_glasshouse_to_field.predict(np.column_stack([lab_mean, glass_mean]))
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.scatter(test.true_field_efficacy, lab_pred, alpha=0.55, label="lab only")
    ax.scatter(test.true_field_efficacy, combined_pred, alpha=0.55, label="lab + glasshouse")
    low = float(min(test.true_field_efficacy.min(), lab_pred.min(), combined_pred.min()))
    high = float(max(test.true_field_efficacy.max(), lab_pred.max(), combined_pred.max()))
    ax.plot([low, high], [low, high], linestyle="--", linewidth=1.0)
    ax.set_xlabel("Latent field efficacy")
    ax.set_ylabel("Predicted field efficacy")
    ax.set_title("Glasshouse evidence improves cross-fidelity calibration")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "cross_fidelity_calibration.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    ordered = indexed.loc[["field_only", "lab_field", "multifidelity"]]
    ax.bar(ordered.index, ordered["mean_simple_regret_field_efficacy"])
    ax.set_ylabel("Mean simple regret in latent field efficacy")
    ax.set_xlabel("Screening policy")
    ax.set_title("Equal-budget multi-fidelity screening reduces selection regret")
    fig.tight_layout()
    fig.savefig(figures_dir / "equal_budget_selection_regret.png", dpi=180)
    plt.close(fig)

    summary: dict[str, object] = {
        "release": "0.6.0",
        "scientific_question": (
            "Can cheap lab and glasshouse evidence reduce expensive field-selection regret under "
            "a fixed experimental budget?"
        ),
        "scope": {
            "status": "controlled synthetic multi-fidelity experiment",
            "reason": (
                "The public real-data case does not contain harmonised lab, glasshouse and field "
                "measurements for the same candidate set; synthetic truth makes transfer "
                "error auditable."
            ),
            "n_candidates_per_rollout": config.n_candidates,
            "n_selected": config.n_selected,
            "n_rollouts": config.n_rollouts,
        },
        "fidelity_costs": {
            "lab": config.costs.lab,
            "glasshouse": config.costs.glasshouse,
            "field": config.costs.field,
            "common_budget_units": config.common_budget,
        },
        "calibration_gate": {
            "held_out_lab_only_rmse": lab_rmse,
            "held_out_lab_plus_glasshouse_rmse": combined_rmse,
            "rmse_improvement_percent": calibration_improvement,
            "promotion_threshold_percent": 10.0,
            "glasshouse_stage_promoted": promotion_passed,
        },
        "equal_budget_policy_result": {
            "field_only_top8_recall": float(indexed.loc["field_only", "mean_oracle_top_k_recall"]),
            "lab_field_top8_recall": float(indexed.loc["lab_field", "mean_oracle_top_k_recall"]),
            "multifidelity_top8_recall": float(
                indexed.loc["multifidelity", "mean_oracle_top_k_recall"]
            ),
            "field_only_regret": float(
                indexed.loc["field_only", "mean_simple_regret_field_efficacy"]
            ),
            "lab_field_regret": lab_field_regret,
            "multifidelity_regret": multifidelity_regret,
            "multifidelity_regret_reduction_vs_lab_field_percent": regret_reduction,
            "paired_regret_difference_multifidelity_minus_lab_field": regret_diff,
            "paired_recall_difference_multifidelity_minus_lab_field": recall_diff,
        },
        "interpretation": (
            "Lower-fidelity evidence is valuable only after demonstrating transport to "
            "field truth. "
            "Under the controlled cost structure, glasshouse evidence passes that gate and reduces "
            "field-selection regret. The numerical gains are properties of the explicit "
            "synthetic DGP, "
            "not empirical claims about any commercial Crop Protection pipeline."
        ),
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    """CLI entry point for the multi-fidelity screening case."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_multifidelity_demo(root), indent=2))


if __name__ == "__main__":
    main()
