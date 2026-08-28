"""Executable decision-aware adaptive replication analysis."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from crop_protection_ps.adaptive_design import (
    AdaptiveSimulationConfig,
    acquisition_table,
    beliefs_from_release_tables,
    paired_policy_difference,
    simulate_adaptive_policies,
    summarise_allocations,
    summarise_policy_simulation,
)


def run_adaptive_demo(root: Path) -> dict[str, object]:
    """Run and persist the sequential decision-aware field-trial design case."""
    bayesian_dir = root / "results" / "real_hop_trial" / "bayesian"
    posterior_path = bayesian_dir / "posterior_timing_effects.csv"
    pooling_path = bayesian_dir / "partial_pooling_comparison.csv"
    if not posterior_path.exists() or not pooling_path.exists():
        raise FileNotFoundError(
            "Adaptive design requires the checked-in v0.3 Bayesian posterior summaries. "
            "Run crop-protection-bayesian if those artifacts are absent."
        )

    results_dir = root / "results" / "real_hop_trial" / "adaptive_design"
    figures_dir = results_dir / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    posterior = pd.read_csv(posterior_path)
    paired = pd.read_csv(pooling_path)
    beliefs = beliefs_from_release_tables(posterior, paired)
    acquisition = acquisition_table(beliefs)
    acquisition.to_csv(results_dir / "initial_acquisition_ranking.csv", index=False)

    config = AdaptiveSimulationConfig(
        n_rollouts=10_000,
        max_budget=20,
        checkpoints=(0, 5, 10, 15, 20),
        seed=20260828,
    )
    simulation = simulate_adaptive_policies(beliefs, config=config)
    policy_summary = summarise_policy_simulation(simulation)
    allocation_summary = summarise_allocations(simulation)
    policy_summary.to_csv(results_dir / "policy_budget_metrics.csv", index=False)
    allocation_summary.to_csv(results_dir / "mean_replication_allocations.csv", index=False)

    # Keep rollout-level data out of the release by default; it is reproducible from the seed and
    # only summary outputs are required to audit the conclusion.
    budget = 15
    regret_difference = paired_policy_difference(
        simulation,
        budget=budget,
        metric="total_bayes_regret_sqrt_audpc",
    )
    entropy_difference = paired_policy_difference(
        simulation,
        budget=budget,
        metric="total_sign_entropy_nats",
    )

    at_budget = policy_summary.loc[policy_summary["budget_paired_blocks"] == budget].set_index(
        "policy"
    )
    adaptive_regret = float(at_budget.loc["decision_eig", "mean_bayes_regret_sqrt_audpc"])
    uniform_regret = float(at_budget.loc["uniform", "mean_bayes_regret_sqrt_audpc"])
    adaptive_entropy = float(at_budget.loc["decision_eig", "mean_sign_entropy_nats"])
    uniform_entropy = float(at_budget.loc["uniform", "mean_sign_entropy_nats"])
    regret_reduction = 100.0 * (uniform_regret - adaptive_regret) / uniform_regret
    entropy_reduction = 100.0 * (uniform_entropy - adaptive_entropy) / uniform_entropy

    first_decision = acquisition.sort_values("decision_eig_rank").iloc[0]
    first_parameter = acquisition.sort_values("parameter_eig_rank").iloc[0]
    allocation_15 = allocation_summary.loc[
        (allocation_summary["budget_paired_blocks"] == budget)
        & (allocation_summary["policy"] == "decision_eig")
    ].iloc[0]
    product_columns = [
        column
        for column in allocation_summary.columns
        if column not in {"policy", "budget_paired_blocks"}
    ]

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    for policy, group in policy_summary.groupby("policy", observed=True):
        ordered = group.sort_values("budget_paired_blocks")
        ax.plot(
            ordered["budget_paired_blocks"],
            ordered["mean_bayes_regret_sqrt_audpc"],
            marker="o",
            label=str(policy),
        )
    ax.set_xlabel("Additional paired-block replicates")
    ax.set_ylabel("Expected posterior timing regret (sqrt(AUDPC))")
    ax.set_title("Decision-aware replication targets timing uncertainty")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "policy_regret_by_budget.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    acquisition_ordered = acquisition.sort_values("decision_sign_eig_nats", ascending=True)
    ax.barh(acquisition_ordered["treatment"], acquisition_ordered["decision_sign_eig_nats"])
    ax.set_xlabel("Expected sign-information gain from one paired block (nats)")
    ax.set_ylabel("Fungicide")
    ax.set_title("The next replicate should target the unresolved decision")
    fig.tight_layout()
    fig.savefig(figures_dir / "initial_decision_information_gain.png", dpi=180)
    plt.close(fig)

    summary: dict[str, object] = {
        "release": "0.5.0",
        "decision_problem": {
            "estimand": "product-specific Late-minus-Early effect on sqrt(AUDPC)",
            "action": (
                "choose Early when posterior mean Late-minus-Early is positive; otherwise Late"
            ),
            "experimental_unit": (
                "one additional paired block containing Early and Late timing for the same product"
            ),
            "loss": (
                "magnitude of the latent timing contrast when the selected timing sign is wrong"
            ),
        },
        "upstream_evidence_gate": {
            "environment_state": (
                "v0.4 showed that a same-year untreated sentinel is useful for disease-level "
                "transportability, but product-by-sentinel timing interactions failed promotion"
            ),
            "consequence": (
                "sentinel information defines the in-season decision stage but is not forced into "
                "product-specific timing effects without supporting GxE evidence"
            ),
        },
        "initial_acquisition": {
            "decision_aware_first_product": str(first_decision["treatment"]),
            "decision_sign_eig_nats": float(first_decision["decision_sign_eig_nats"]),
            "prob_wrong_timing_if_act_now": float(first_decision["prob_wrong_timing_if_act_now"]),
            "parameter_information_first_product": str(first_parameter["treatment"]),
            "interpretation": (
                "Parameter-centric and decision-centric design select different first experiments."
            ),
        },
        "preposterior_simulation": {
            "n_rollouts": config.n_rollouts,
            "max_budget_paired_blocks": config.max_budget,
            "checkpoints": list(config.checkpoints),
            "common_random_numbers": True,
            "budget_15": {
                "decision_eig_mean_bayes_regret": adaptive_regret,
                "uniform_mean_bayes_regret": uniform_regret,
                "regret_reduction_vs_uniform_percent": regret_reduction,
                "decision_eig_mean_sign_entropy_nats": adaptive_entropy,
                "uniform_mean_sign_entropy_nats": uniform_entropy,
                "sign_entropy_reduction_vs_uniform_percent": entropy_reduction,
                "paired_regret_difference_decision_minus_uniform": regret_difference,
                "paired_entropy_difference_decision_minus_uniform": entropy_difference,
                "mean_decision_eig_allocation": {
                    product: float(allocation_15[product]) for product in product_columns
                },
            },
        },
        "interpretation": (
            "When the scientific action is an Early-versus-Late timing choice, replication should "
            "target uncertainty about the sign of the treatment contrast rather than maximise "
            "generic parameter information. The result is conditional on the current posterior "
            "model and historical paired-block variability, not a grower recommendation."
        ),
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    """CLI entry point for decision-aware adaptive replication."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_adaptive_demo(root), indent=2))


if __name__ == "__main__":
    main()
