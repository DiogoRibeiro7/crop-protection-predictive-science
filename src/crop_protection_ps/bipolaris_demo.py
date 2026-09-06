"""Executable second empirical case using public southern corn leaf blight data."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from crop_protection_ps.bipolaris import (
    BipolarisSourceContract,
    curve_metrics,
    download_bipolaris,
    empirical_case_summary,
    environment_rank_stability,
    load_bipolaris,
)
from crop_protection_ps.bipolaris_functional import (
    functional_profiles,
    functional_stability_summary,
    pairwise_functional_distances,
)
from crop_protection_ps.bipolaris_loeo import (
    burden_fold_metrics,
    leave_one_environment_out_burden,
    leave_one_environment_out_shape,
    loeo_summary,
    shape_fold_metrics,
)


def run_bipolaris_demo(root: Path, *, download_if_missing: bool = True) -> dict[str, object]:
    """Run the independent field-disease case and persist auditable outputs."""
    source = BipolarisSourceContract()
    raw_path = root / "data" / "raw" / "maize_bipolaris.csv"
    results_dir = root / "results" / "bipolaris"
    figures_dir = results_dir / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    if not raw_path.exists():
        if not download_if_missing:
            raise FileNotFoundError(raw_path)
        download_bipolaris(raw_path, contract=source)

    frame = load_bipolaris(raw_path)
    metrics = curve_metrics(frame)
    correlations = environment_rank_stability(metrics)
    case = empirical_case_summary(frame, metrics)
    profiles = functional_profiles(frame)
    functional_distances = pairwise_functional_distances(profiles)
    functional_summary = functional_stability_summary(functional_distances)

    burden_predictions = leave_one_environment_out_burden(metrics)
    burden_folds = burden_fold_metrics(burden_predictions)
    shape_predictions = leave_one_environment_out_shape(profiles)
    shape_folds = shape_fold_metrics(shape_predictions)
    prospective_summary = loeo_summary(burden_folds, shape_folds)

    metrics.to_csv(results_dir / "curve_metrics.csv", index=False)
    correlations.to_csv(results_dir / "environment_rank_spearman.csv")
    profiles.to_csv(results_dir / "functional_profiles.csv", index=False)
    functional_distances.to_csv(results_dir / "functional_distances.csv", index=False)
    burden_predictions.to_csv(results_dir / "loeo_burden_predictions.csv", index=False)
    burden_folds.to_csv(results_dir / "loeo_burden_folds.csv", index=False)
    shape_predictions.to_csv(results_dir / "loeo_shape_predictions.csv", index=False)
    shape_folds.to_csv(results_dir / "loeo_shape_folds.csv", index=False)

    environment_summary = (
        metrics.groupby("environment", observed=True)
        .agg(
            curves=("hybrid", "size"),
            median_audpc_pct_days=("audpc_pct_days", "median"),
            median_final_severity_pct=("final_severity_pct", "median"),
            median_t50_dae=("t50_dae", "median"),
        )
        .reset_index()
    )
    environment_summary.to_csv(results_dir / "environment_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    ordered = environment_summary.sort_values("median_audpc_pct_days")
    ax.bar(ordered["environment"], ordered["median_audpc_pct_days"])
    ax.set_xlabel("Field environment")
    ax.set_ylabel("Median AUDPC (percent-severity × day)")
    ax.set_title("Southern corn leaf blight burden varies across field environments")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(figures_dir / "median_audpc_by_environment.png", dpi=180)
    plt.close(fig)

    shape_categories = [
        "same hybrid\nacross environments",
        "different hybrids\nacross environments",
    ]
    shape_values = [
        functional_summary["median_same_hybrid_cross_environment_shape_rmse"],
        functional_summary["median_different_hybrid_cross_environment_shape_rmse"],
    ]
    if all(value is not None for value in shape_values):
        fig, ax = plt.subplots(figsize=(7.0, 4.8))
        ax.bar(shape_categories, [float(value) for value in shape_values])
        ax.set_ylabel("Median normalized trajectory RMSE")
        ax.set_title("Hybrid-specific disease-curve shape across environments")
        fig.tight_layout()
        fig.savefig(figures_dir / "functional_shape_stability.png", dpi=180)
        plt.close(fig)

    loeo_labels = ["global training mean", "hybrid history"]
    loeo_values = [
        float(prospective_summary["mean_fold_global_training_audpc_rmse"]),
        float(prospective_summary["mean_fold_hybrid_history_audpc_rmse"]),
    ]
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    ax.bar(loeo_labels, loeo_values)
    ax.set_ylabel("Mean held-out-environment AUDPC RMSE")
    ax.set_title("Prospective hybrid burden transport across environments")
    fig.tight_layout()
    fig.savefig(figures_dir / "loeo_audpc_transport.png", dpi=180)
    plt.close(fig)

    pairwise = correlations.where(np.triu(np.ones(correlations.shape, dtype=bool), k=1)).stack()
    finite_pairwise = pairwise[np.isfinite(pairwise)]
    minimum_pairwise = float(finite_pairwise.min()) if not finite_pairwise.empty else None
    maximum_pairwise = float(finite_pairwise.max()) if not finite_pairwise.empty else None

    summary: dict[str, object] = {
        "source": {
            "repository": source.repository_url,
            "commit": source.source_commit,
            "path": source.source_path,
            "git_blob_sha1": source.source_git_blob_sha1,
            "publication_doi": source.publication_doi,
            "local_file": str(raw_path.relative_to(root)),
        },
        "data": case,
        "cross_environment_audpc_ranking": {
            "median_pairwise_spearman": case["median_pairwise_spearman_audpc"],
            "minimum_pairwise_spearman": minimum_pairwise,
            "maximum_pairwise_spearman": maximum_pairwise,
            "interpretation": (
                "Descriptive stability of hybrid AUDPC rankings across environments; "
                "not a causal treatment effect or a substitute for full curve comparison."
            ),
        },
        "functional_shape_stability": {
            **functional_summary,
            "interpretation": (
                "Common-grid trajectory distances separate overall disease scale from "
                "scale-normalized epidemic shape. Values are descriptive and do not reproduce "
                "the source HGAM analysis."
            ),
        },
        "leave_one_environment_out": {
            **prospective_summary,
            "interpretation": (
                "Prospective validation compares an environment-agnostic training baseline with "
                "same-hybrid history learned only from the remaining environments. Held-out "
                "outcomes are never used to construct predictions."
            ),
        },
        "scope": {
            "empirical": True,
            "endpoint": "southern corn leaf blight severity progress in maize hybrids",
            "decision_context": "host-resistance phenotyping across field environments",
            "limitation": (
                "This independently broadens the real-field evidence base but is not "
                "linked lab/glasshouse/field discovery-programme data."
            ),
        },
    }
    (results_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
    )
    return summary


def main() -> None:
    """CLI entry point for the second empirical field-disease case."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_bipolaris_demo(root), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
