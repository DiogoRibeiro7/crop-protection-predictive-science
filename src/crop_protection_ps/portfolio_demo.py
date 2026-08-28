"""Executable R&D portfolio decision analysis."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from crop_protection_ps.portfolio_decision import (
    PortfolioConfig,
    paired_portfolio_difference,
    simulate_portfolio_policies,
    summarise_portfolio_policies,
)


def run_portfolio_demo(root: Path) -> dict[str, object]:
    """Run and persist the controlled budget-constrained portfolio decision experiment."""
    config = PortfolioConfig()
    results_dir = root / "results" / "portfolio_decision"
    figures_dir = results_dir / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    rollouts = simulate_portfolio_policies(config)
    rollouts.to_csv(results_dir / "portfolio_policy_rollouts.csv", index=False)
    metrics = summarise_portfolio_policies(rollouts)
    metrics.to_csv(results_dir / "portfolio_policy_metrics.csv", index=False)

    regret_vs_uncertainty = paired_portfolio_difference(
        rollouts,
        policy_a="portfolio_voi",
        policy_b="uncertainty",
        metric="oracle_regret",
    )
    regret_vs_uniform = paired_portfolio_difference(
        rollouts,
        policy_a="portfolio_voi",
        policy_b="uniform",
        metric="oracle_regret",
    )
    value_vs_uncertainty = paired_portfolio_difference(
        rollouts,
        policy_a="portfolio_voi",
        policy_b="uncertainty",
        metric="realised_portfolio_value",
    )

    indexed = metrics.set_index("policy")
    uniform_regret = float(indexed.loc["uniform", "mean_oracle_regret"])
    uncertainty_regret = float(indexed.loc["uncertainty", "mean_oracle_regret"])
    voi_regret = float(indexed.loc["portfolio_voi", "mean_oracle_regret"])
    regret_reduction_vs_uncertainty = 100.0 * (uncertainty_regret - voi_regret) / uncertainty_regret
    regret_reduction_vs_uniform = 100.0 * (uniform_regret - voi_regret) / uniform_regret

    # Promotion is deliberately tied to decision quality, not to an acquisition score itself.
    promotion_passed = bool(
        regret_reduction_vs_uncertainty >= 5.0
        and regret_vs_uncertainty["mc95_high"] < 0.0
        and regret_vs_uniform["mc95_high"] < 0.0
    )
    promotion_gate = {
        "minimum_regret_reduction_vs_uncertainty_percent": 5.0,
        "observed_regret_reduction_vs_uncertainty_percent": regret_reduction_vs_uncertainty,
        "observed_regret_reduction_vs_uniform_percent": regret_reduction_vs_uniform,
        "paired_regret_difference_portfolio_voi_minus_uncertainty": regret_vs_uncertainty,
        "paired_regret_difference_portfolio_voi_minus_uniform": regret_vs_uniform,
        "promoted": promotion_passed,
    }
    (results_dir / "portfolio_promotion_gate.json").write_text(
        json.dumps(promotion_gate, indent=2), encoding="utf-8"
    )

    order = ["no_followup", "uniform", "uncertainty", "portfolio_voi"]
    plotted = indexed.loc[order]
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.bar(plotted.index, plotted["mean_oracle_regret"])
    ax.set_ylabel("Mean regret versus oracle portfolio value")
    ax.set_xlabel("Follow-up allocation policy")
    ax.set_title("Decision-aware experiment allocation reduces portfolio regret")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(figures_dir / "portfolio_regret_by_policy.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    equal_budget = indexed.loc[["uniform", "uncertainty", "portfolio_voi"]]
    ax.bar(equal_budget.index, equal_budget["mean_advanced_technical_success_rate"])
    ax.set_ylabel("Technical success rate among advanced candidates")
    ax.set_xlabel("Equal-budget follow-up policy")
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Portfolio-aware information improves the quality of advancement decisions")
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    fig.savefig(figures_dir / "advanced_success_rate.png", dpi=180)
    plt.close(fig)

    summary: dict[str, object] = {
        "release": "0.7.0",
        "scientific_question": (
            "Under a fixed follow-up experimental budget, which candidate and which uncertainty "
            "should be measured next before making a constrained R&D advancement decision?"
        ),
        "scope": {
            "status": "controlled synthetic R&D portfolio experiment",
            "n_candidates_per_rollout": config.n_candidates,
            "max_candidates_advanced": config.max_advanced,
            "n_rollouts": config.n_rollouts,
            "followup_budget_units": config.followup_budget_units,
            "downstream_development_budget_units": config.downstream_budget_units,
            "warning": (
                "Value units, success thresholds, rewards and costs are simulation parameters, not "
                "estimates of the economics of any real Crop Protection programme."
            ),
        },
        "decision_structure": {
            "technical_success": "efficacy > threshold AND safety margin > threshold",
            "candidate_expected_value": "P(technical success) * success reward - development cost",
            "terminal_optimisation": "exact count-and-budget 0/1 knapsack",
            "adaptive_acquisition": (
                "Gauss-Hermite EVSI approximation around the current portfolio "
                "value-per-cost boundary"
            ),
        },
        "equal_followup_budget_result": {
            policy: {
                "mean_followup_cost_units": float(indexed.loc[policy, "mean_followup_cost_units"]),
                "mean_realised_portfolio_value": float(
                    indexed.loc[policy, "mean_realised_portfolio_value"]
                ),
                "mean_oracle_regret": float(indexed.loc[policy, "mean_oracle_regret"]),
                "mean_advanced_technical_success_rate": float(
                    indexed.loc[policy, "mean_advanced_technical_success_rate"]
                ),
                "mean_efficacy_followups": float(
                    indexed.loc[policy, "mean_n_efficacy_followups"]
                ),
                "mean_safety_followups": float(indexed.loc[policy, "mean_n_safety_followups"]),
            }
            for policy in ("uniform", "uncertainty", "portfolio_voi")
        },
        "no_followup_reference": {
            "mean_realised_portfolio_value": float(
                indexed.loc["no_followup", "mean_realised_portfolio_value"]
            ),
            "mean_oracle_regret": float(indexed.loc["no_followup", "mean_oracle_regret"]),
        },
        "promotion_gate": promotion_gate,
        "paired_value_difference_portfolio_voi_minus_uncertainty": value_vs_uncertainty,
        "interpretation": (
            "Technical uncertainty is not automatically decision-relevant uncertainty. The "
            "portfolio-aware policy spends follow-up evidence where a posterior change could alter "
            "a constrained advancement decision, whereas uncertainty sampling ignores reward, "
            "development cost and the opportunity cost of scarce portfolio capacity."
        ),
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    """CLI entry point."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_portfolio_demo(root), indent=2))


if __name__ == "__main__":
    main()
