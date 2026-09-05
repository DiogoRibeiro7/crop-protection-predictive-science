"""Executable environment-aware transportability analysis for the real hop field trial."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from crop_protection_ps.environment_transport import (
    attach_environment_state,
    derive_environment_features,
    gxe_promotion_gate,
    leave_one_year_out_environment_models,
    load_corvallis_weather,
    regularisation_sensitivity,
)
from crop_protection_ps.hop_trial import (
    load_hop_trial,
    prepare_primary_analysis,
    prepare_timing_analysis,
)


def run_environment_demo(root: Path) -> dict[str, object]:
    """Run and persist the environment-state transportability case study."""
    trial_path = root / "data" / "raw" / "richardson_gent_hop_downy_mildew.csv"
    weather_path = root / "data" / "raw" / "corvallis_monthly_weather_2009_2025.csv"
    results_dir = root / "results" / "real_hop_trial" / "environment"
    figures_dir = results_dir / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    trial = load_hop_trial(trial_path)
    primary = prepare_primary_analysis(trial)
    timing = prepare_timing_analysis(primary)
    weather = load_corvallis_weather(weather_path)
    environment = derive_environment_features(weather)
    modelling = attach_environment_state(timing, primary, environment)

    trial_environment = (
        modelling[
            [
                "year",
                "preseason_wetness_z",
                "application_wetness_z",
                "application_avg_temp_c_z",
                "sentinel_mean_audpc",
                "sentinel_sqrt_audpc",
                "sentinel_n",
            ]
        ]
        .drop_duplicates()
        .sort_values("year")
        .reset_index(drop=True)
    )
    trial_environment.to_csv(results_dir / "environment_state_by_year.csv", index=False)

    alpha = 10.0
    metrics, predictions = leave_one_year_out_environment_models(modelling, alpha=alpha)
    metrics.to_csv(results_dir / "leave_one_year_out_model_metrics.csv", index=False)
    predictions.to_csv(results_dir / "leave_one_year_out_predictions.csv", index=False)

    sensitivity = regularisation_sensitivity(modelling)
    sensitivity.to_csv(results_dir / "regularisation_sensitivity.csv", index=False)

    gate = gxe_promotion_gate(metrics)
    (results_dir / "gxe_promotion_gate.json").write_text(
        json.dumps(asdict(gate), indent=2), encoding="utf-8"
    )

    aggregate = metrics.loc[metrics["held_out_year"] == "ALL"].set_index("model")
    baseline_rmse = float(aggregate.loc["baseline", "rmse"])
    weather_rmse = float(aggregate.loc["coarse_weather", "rmse"])
    sentinel_rmse = float(aggregate.loc["sentinel", "rmse"])
    gxe_rmse = float(aggregate.loc["sentinel_gxe", "rmse"])
    sentinel_reduction = 100.0 * (baseline_rmse - sentinel_rmse) / baseline_rmse
    weather_change = 100.0 * (weather_rmse - baseline_rmse) / baseline_rmse
    gxe_change = 100.0 * (gxe_rmse - sentinel_rmse) / sentinel_rmse

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    ax.scatter(
        trial_environment["application_wetness_z"],
        trial_environment["sentinel_mean_audpc"],
        s=70,
    )
    for row in trial_environment.itertuples(index=False):
        ax.annotate(
            str(row.year),
            (row.application_wetness_z, row.sentinel_mean_audpc),
            xytext=(5, 4),
            textcoords="offset points",
        )
    ax.set_xlabel("April-May wetness index (pre-trial climatology z-scale)")
    ax.set_ylabel("Same-year untreated mean AUDPC")
    ax.set_title("Coarse monthly weather does not explain realised disease pressure")
    fig.tight_layout()
    fig.savefig(figures_dir / "weather_vs_realised_disease_pressure.png", dpi=180)
    plt.close(fig)

    ordered_models = ["baseline", "coarse_weather", "sentinel", "sentinel_gxe"]
    labels = ["Treatment + timing", "Coarse weather", "Sentinel", "Sentinel + G×E"]
    values = [float(aggregate.loc[name, "rmse"]) for name in ordered_models]
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    positions = np.arange(len(values))
    ax.bar(positions, values)
    ax.set_xticks(positions, labels, rotation=15, ha="right")
    ax.set_ylabel("Leave-one-year-out RMSE on sqrt(AUDPC)")
    ax.set_title("Environment representation matters more than interaction complexity")
    for position, value in zip(positions, values, strict=True):
        ax.text(float(position), value + 0.25, f"{value:.2f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(figures_dir / "environment_model_comparison.png", dpi=180)
    plt.close(fig)

    sentinel_predictions = predictions.loc[predictions["model"] == "sentinel"].copy()
    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    ax.scatter(
        sentinel_predictions["sqrt_audpc"],
        sentinel_predictions["prediction"],
        alpha=0.65,
    )
    lower = float(
        min(sentinel_predictions["sqrt_audpc"].min(), sentinel_predictions["prediction"].min())
    )
    upper = float(
        max(sentinel_predictions["sqrt_audpc"].max(), sentinel_predictions["prediction"].max())
    )
    ax.plot([lower, upper], [lower, upper], linestyle="--")
    ax.set_xlim(lower, upper)
    ax.set_ylim(lower, upper)
    ax.set_xlabel("Observed sqrt(AUDPC)")
    ax.set_ylabel("Prediction using same-year untreated sentinel")
    ax.set_title("In-season environment anchoring improves unseen-year prediction")
    fig.tight_layout()
    fig.savefig(figures_dir / "sentinel_leave_one_year_out_predictions.png", dpi=180)
    plt.close(fig)

    summary: dict[str, object] = {
        "release": "0.4.0",
        "environment_data": {
            "trial_location": "experimental hop yard near Corvallis, Oregon",
            "weather_resolution": "monthly Corvallis-area summaries",
            "weather_months": ["February", "March", "April", "May"],
            "external_climatology_years": list(range(2009, 2017)),
            "primary_trial_years": [2017, 2018, 2020, 2021],
            "limitation": (
                "Weather is a coarse geographic/monthly proxy and is not treated as exact "
                "plot exposure."
            ),
        },
        "models": {
            "ridge_alpha": alpha,
            "baseline": "treatment + timing",
            "coarse_weather": (
                "treatment + timing + pre-season wetness + application-window wetness + "
                "application-window temperature anomaly"
            ),
            "sentinel": "treatment + timing + same-year untreated-control disease pressure",
            "sentinel_gxe": (
                "sentinel model + timing-by-sentinel and product-by-sentinel interactions"
            ),
        },
        "leave_one_year_out": {
            "baseline_rmse": baseline_rmse,
            "coarse_weather_rmse": weather_rmse,
            "sentinel_rmse": sentinel_rmse,
            "sentinel_gxe_rmse": gxe_rmse,
            "sentinel_rmse_reduction_vs_baseline_percent": sentinel_reduction,
            "coarse_weather_rmse_change_vs_baseline_percent": weather_change,
            "gxe_rmse_change_vs_sentinel_percent": gxe_change,
            "sentinel_r2": float(aggregate.loc["sentinel", "r2"]),
        },
        "gxe_promotion_gate": asdict(gate),
        "deployment_interpretation": {
            "preseason": (
                "The available coarse weather summaries are inadequate for a reliable prospective "
                "new-year predictor in this four-year trial."
            ),
            "in_season": (
                "A small untreated sentinel signal measures realised disease pressure and "
                "materially improves transportability, but is only available after the new "
                "season has begun."
            ),
            "interaction_complexity": (
                "Product-by-environment interactions are mathematically estimable but fail the "
                "unseen-year promotion gate and remain exploratory."
            ),
        },
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    """CLI entry point for environment-aware transportability analysis."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_environment_demo(root), indent=2))


if __name__ == "__main__":
    main()
