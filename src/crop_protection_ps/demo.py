"""End-to-end demonstrator for the repository."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from crop_protection_ps.config import load_config
from crop_protection_ps.design import make_candidate_grid, select_d_optimal_candidates
from crop_protection_ps.dose_response import (
    bootstrap_interval,
    cluster_bootstrap_ed,
    fit_dose_response,
    four_parameter_logistic,
)
from crop_protection_ps.mixed_effects import fit_site_random_intercept_model
from crop_protection_ps.simulate import simulate_field_trials
from crop_protection_ps.validation import validation_table


def run_demo(root: Path) -> dict[str, object]:
    """Run the complete synthetic field-trial analysis and persist outputs."""
    config = load_config(root / "configs" / "demo.yaml")
    frame = simulate_field_trials(config)
    processed_dir = root / "data" / "processed"
    results_dir = root / "results"
    figures_dir = results_dir / "figures"
    processed_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    frame.to_csv(processed_dir / "synthetic_field_trials.csv", index=False)

    cv_table = validation_table(frame, seed=config.seed)
    cv_table.to_csv(results_dir / "validation_comparison.csv", index=False)

    fit = fit_dose_response(frame, formulation="A")
    bootstrap = cluster_bootstrap_ed(
        frame,
        formulation="A",
        n_bootstrap=300,
        seed=config.seed,
    )
    bootstrap.to_csv(results_dir / "dose_response_bootstrap.csv", index=False)
    ed50_interval = bootstrap_interval(bootstrap["ed50"])
    ed90_interval = bootstrap_interval(bootstrap["ed90"])

    design = select_d_optimal_candidates(
        make_candidate_grid(),
        ed50=fit.ed50,
        hill=fit.hill,
        n_select=6,
    )
    design.to_csv(results_dir / "next_experiment_design.csv", index=False)

    mixed = fit_site_random_intercept_model(frame)
    (results_dir / "mixed_effects_summary.txt").write_text(
        mixed.summary().as_text(), encoding="utf-8"
    )

    # Dose-response figure with aggregated observed response.
    positive = frame.loc[(frame["formulation"] == "A") & (frame["dose_g_ai_ha"] > 0)]
    observed = positive.groupby("dose_g_ai_ha", as_index=False)["mortality_rate"].mean()
    x_grid = np.geomspace(
        max(positive["dose_g_ai_ha"].min() * 0.8, 0.1),
        positive["dose_g_ai_ha"].max() * 1.2,
        200,
    )
    y_grid = four_parameter_logistic(x_grid, fit.bottom, fit.top, fit.ed50, fit.hill)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.scatter(observed["dose_g_ai_ha"], observed["mortality_rate"], label="Observed mean")
    ax.plot(x_grid, y_grid, label="4PL fit")
    ax.axvline(fit.ed50, linestyle="--", label=f"ED50 = {fit.ed50:.2f}")
    ax.set_xscale("log")
    ax.set_xlabel("Dose (g a.i./ha)")
    ax.set_ylabel("Mortality rate")
    ax.set_title("Formulation A dose-response")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "dose_response.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    plot_table = cv_table.set_index("strategy")[["rmse", "mae"]]
    plot_table.plot(kind="bar", ax=ax)
    ax.set_ylabel("Error")
    ax.set_xlabel("")
    ax.set_title("Random CV versus unseen-site validation")
    ax.tick_params(axis="x", rotation=0)
    fig.tight_layout()
    fig.savefig(figures_dir / "validation_gap.png", dpi=180)
    plt.close(fig)

    summary: dict[str, object] = {
        "n_rows": int(len(frame)),
        "n_sites": int(frame["site"].nunique()),
        "years": sorted(map(int, frame["year"].unique())),
        "dose_response": {
            "formulation": "A",
            "ed50": fit.ed50,
            "ed50_ci95": list(ed50_interval),
            "ed90": fit.ed90,
            "ed90_ci95": list(ed90_interval),
            "hill": fit.hill,
        },
        "validation": cv_table.to_dict(orient="records"),
        "selected_next_experiments": design.to_dict(orient="records"),
        "site_random_intercept_variance": float(np.asarray(mixed.cov_re).squeeze()),
    }
    (results_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    """CLI entry point."""
    root = Path(__file__).resolve().parents[2]
    summary = run_demo(root)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
