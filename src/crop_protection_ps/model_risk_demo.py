"""Executable applicability-domain and model-risk demonstration."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from crop_protection_ps.model_risk import (
    ModelRiskConfig,
    simulate_model_risk_audit,
    summarise_model_risk,
)


def run_model_risk_demo(root: Path) -> dict[str, object]:
    """Run the locked model-risk audit and persist reproducible outputs."""
    config = ModelRiskConfig()
    results_dir = root / "results" / "model_risk"
    figures_dir = root / "figures" / "model_risk"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    metrics, example = simulate_model_risk_audit(config)
    summary = summarise_model_risk(metrics)
    metrics.to_csv(results_dir / "rollout_metrics.csv", index=False)
    example.to_csv(results_dir / "example_stress_predictions.csv", index=False)
    summary_rows = []
    for metric, interval in summary["metrics"].items():
        summary_rows.append({"metric": metric, **interval})
    pd.DataFrame(summary_rows).to_csv(results_dir / "summary_metrics.csv", index=False)
    (results_dir / "promotion_gate.json").write_text(
        json.dumps(summary["promotion_gate"], indent=2),
        encoding="utf-8",
    )

    coverage_names = [
        "naive_id_interval_coverage",
        "stress_global_interval_coverage",
        "distance_scaled_interval_coverage",
        "selective_interval_coverage",
    ]
    coverage_labels = [
        "ID conformal\non stress set",
        "Global stress\nconformal",
        "Distance-scaled\nconformal",
        "Accepted-only\nID conformal",
    ]
    coverage_values = [float(metrics[name].mean()) for name in coverage_names]
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    ax.bar(coverage_labels, coverage_values)
    ax.axhline(config.nominal_coverage, linestyle="--", linewidth=1.2)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Empirical interval coverage")
    ax.set_title("Distribution shift exposes miscalibration and triggers model-risk controls")
    fig.tight_layout()
    fig.savefig(figures_dir / "coverage_by_risk_control.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.scatter(
        example["applicability_distance"],
        example["absolute_latent_error"],
        alpha=0.55,
    )
    threshold = float(metrics.loc[0, "acceptance_threshold"])
    ax.axvline(threshold, linestyle="--", linewidth=1.2)
    ax.set_xlabel("Applicability-domain distance")
    ax.set_ylabel("Absolute latent efficacy error")
    ax.set_title("Prediction error grows as experiments leave historical support")
    fig.tight_layout()
    fig.savefig(figures_dir / "error_vs_applicability_distance.png", dpi=180)
    plt.close(fig)

    full_summary: dict[str, object] = {
        "release": "0.9.0",
        "scientific_question": (
            "When should a scientific prediction be widened, flagged or withheld because the "
            "candidate condition lies outside the experimentally validated applicability domain?"
        ),
        "scope": {
            "status": "controlled applicability-domain stress experiment",
            "n_rollouts": config.n_rollouts,
            "nominal_interval_coverage": config.nominal_coverage,
            "historical_training_rows_per_rollout": config.n_train,
            "final_stress_rows_per_rollout": (
                config.n_test_id + config.n_test_near + config.n_test_far
            ),
            "warning": (
                "The response surface and support boundaries are controlled simulation choices. "
                "Numerical gains are model-risk demonstrations, not empirical product claims."
            ),
        },
        "risk_controls": {
            "applicability_score": (
                "mean seven-nearest-neighbour distance in standardised historical design space"
            ),
            "abstention_threshold": (
                "85th percentile of in-domain calibration distances, fixed before final testing"
            ),
            "base_interval": "finite-sample 90% split conformal absolute-residual interval",
            "shift_calibration": (
                "separate near-shift calibration set; final in-domain, near-shift and far-shift "
                "stress rows remain unseen"
            ),
            "distance_scaled_interval": (
                "conformal residual score divided by max(1, distance/threshold)^2 during "
                "calibration, with the same factor restored at prediction time"
            ),
        },
        **summary,
        "interpretation": (
            "A single global uncertainty band is not enough under extrapolation. Distance-aware "
            "inflation can recover stress-set coverage, but the resulting intervals can become so "
            "wide that abstention is the more useful scientific action. The applicability-domain "
            "policy therefore separates 'model can compute a number' from 'R&D should trust this "
            "number without another experiment'."
        ),
    }
    (results_dir / "summary.json").write_text(
        json.dumps(full_summary, indent=2),
        encoding="utf-8",
    )
    return full_summary


def main() -> None:
    """CLI entry point."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_model_risk_demo(root), indent=2))


if __name__ == "__main__":
    main()
