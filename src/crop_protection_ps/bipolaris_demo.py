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


def run_bipolaris_demo(root: Path, *, download_if_missing: bool = True) -> dict[str, object]:
    """Run the independent field-disease case and persist auditable outputs.

    Parameters
    ----------
    root:
        Repository root containing ``data`` and ``results`` directories.
    download_if_missing:
        Download the commit-pinned public CSV when the local raw file is absent.
        Set to ``False`` for fully offline execution.
    """
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

    metrics.to_csv(results_dir / "curve_metrics.csv", index=False)
    correlations.to_csv(results_dir / "environment_rank_spearman.csv")

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

    # The figure is intentionally descriptive. It exposes environment-specific disease
    # burden without treating a scalar AUDPC summary as a complete representation of
    # disease-curve shape.
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

    pairwise = correlations.where(
        np.triu(np.ones(correlations.shape, dtype=bool), k=1)
    ).stack()
    finite_pairwise = pairwise[np.isfinite(pairwise)]
    minimum_pairwise = (
        float(finite_pairwise.min()) if not finite_pairwise.empty else None
    )
    maximum_pairwise = (
        float(finite_pairwise.max()) if not finite_pairwise.empty else None
    )

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
