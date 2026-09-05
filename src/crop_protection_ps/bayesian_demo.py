"""Executable Bayesian hierarchical analysis for the public hop fungicide field trial."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from crop_protection_ps.bayesian_hierarchical import (
    BayesianSamplerConfig,
    fit_hierarchical_timing_model,
    leave_one_year_out_posterior_predictive,
    posterior_predict_training,
    posterior_predictive_diagnostics,
    posterior_timing_summary,
    posterior_variance_summary,
    prior_sensitivity,
)
from crop_protection_ps.hop_trial import (
    load_hop_trial,
    paired_timing_differences,
    prepare_primary_analysis,
    prepare_timing_analysis,
)


def run_bayesian_demo(root: Path) -> dict[str, object]:
    """Fit, validate and persist the Bayesian hierarchical real-data case study."""
    raw_path = root / "data" / "raw" / "richardson_gent_hop_downy_mildew.csv"
    results_dir = root / "results" / "real_hop_trial" / "bayesian"
    figures_dir = results_dir / "figures"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    timing = prepare_timing_analysis(prepare_primary_analysis(load_hop_trial(raw_path)))
    paired = paired_timing_differences(timing)

    main_config = BayesianSamplerConfig(
        n_chains=4,
        burn_in=800,
        draws_per_chain=800,
        thin=2,
        seed=20260828,
    )
    fit = fit_hierarchical_timing_model(timing, config=main_config)
    timing_summary = posterior_timing_summary(fit)
    variance_summary = posterior_variance_summary(fit)
    ppc_diagnostics = posterior_predictive_diagnostics(fit, timing, max_draws=1_200)
    ppc_rows = posterior_predict_training(fit, timing, max_draws=1_200).summary

    timing_summary.to_csv(results_dir / "posterior_timing_effects.csv", index=False)
    variance_summary.to_csv(results_dir / "variance_components.csv", index=False)
    ppc_diagnostics.to_csv(results_dir / "posterior_predictive_checks.csv", index=False)
    ppc_rows.to_csv(results_dir / "posterior_predictive_rows.csv", index=False)

    loyo_config = BayesianSamplerConfig(
        n_chains=2,
        burn_in=500,
        draws_per_chain=500,
        thin=2,
        seed=20260828,
    )
    loyo_metrics, loyo_predictions = leave_one_year_out_posterior_predictive(
        timing,
        config=loyo_config,
        max_predictive_draws=800,
    )
    loyo_metrics.to_csv(results_dir / "leave_one_year_out_metrics.csv", index=False)
    loyo_predictions.to_csv(results_dir / "leave_one_year_out_predictions.csv", index=False)

    sensitivity = prior_sensitivity(
        timing,
        config=BayesianSamplerConfig(
            n_chains=2,
            burn_in=500,
            draws_per_chain=500,
            thin=2,
            seed=20260828,
        ),
    )
    sensitivity.to_csv(results_dir / "prior_sensitivity.csv", index=False)

    # Compare unpooled paired product means with partially pooled posterior effects.
    raw_product = (
        paired.groupby("treatment", observed=True)["delta_sqrt_audpc_late_minus_early"]
        .agg(raw_paired_mean="mean", raw_paired_sd="std", n_pairs="size")
        .reset_index()
    )
    product_posterior = timing_summary.loc[timing_summary["scope"] == "product"].copy()
    pooling = product_posterior.merge(
        raw_product, on="treatment", how="left", validate="one_to_one"
    )
    pooling.to_csv(results_dir / "partial_pooling_comparison.csv", index=False)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ordered = pooling.sort_values("posterior_mean_delta_sqrt_audpc").reset_index(drop=True)
    y_positions = np.arange(len(ordered), dtype=float)
    posterior_mean = ordered["posterior_mean_delta_sqrt_audpc"].to_numpy(dtype=float)
    posterior_low = ordered["q05"].to_numpy(dtype=float)
    posterior_high = ordered["q95"].to_numpy(dtype=float)
    ax.errorbar(
        posterior_mean,
        y_positions,
        xerr=[posterior_mean - posterior_low, posterior_high - posterior_mean],
        fmt="o",
        capsize=3,
        label="Bayesian partial pooling (90% interval)",
    )
    ax.scatter(
        ordered["raw_paired_mean"],
        y_positions,
        marker="x",
        s=55,
        label="Raw paired mean",
    )
    ax.axvline(0.0, linestyle="--")
    ax.set_yticks(y_positions, ordered["treatment"])
    ax.set_xlabel("Late − early effect on sqrt(AUDPC)")
    ax.set_ylabel("Product")
    ax.set_title("Partial pooling stabilises product-specific timing effects")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "partial_pooling_timing_effects.png", dpi=180)
    plt.close(fig)

    # Posterior-predictive calibration by genuinely held-out year.
    yearly = loyo_metrics.loc[loyo_metrics["held_out_year"] != "ALL"].copy()
    yearly["held_out_year"] = yearly["held_out_year"].astype(int)
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(yearly["held_out_year"], yearly["coverage_90"], marker="o", label="90% interval")
    ax.plot(yearly["held_out_year"], yearly["coverage_95"], marker="o", label="95% interval")
    ax.axhline(0.90, linestyle="--")
    ax.axhline(0.95, linestyle=":")
    ax.set_ylim(0.0, 1.05)
    ax.set_xlabel("Held-out trial year")
    ax.set_ylabel("Empirical interval coverage")
    ax.set_title("Unseen-year uncertainty is informative but not fully calibrated")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures_dir / "leave_one_year_out_coverage.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.3, 5.6))
    ax.scatter(
        loyo_predictions["sqrt_audpc"],
        loyo_predictions["posterior_predictive_mean"],
        alpha=0.65,
    )
    observed_min = float(loyo_predictions["sqrt_audpc"].min())
    predicted_min = float(loyo_predictions["posterior_predictive_mean"].min())
    observed_max = float(loyo_predictions["sqrt_audpc"].max())
    predicted_max = float(loyo_predictions["posterior_predictive_mean"].max())
    limits = (min(observed_min, predicted_min), max(observed_max, predicted_max))
    ax.plot(limits, limits, linestyle="--")
    ax.set_xlim(limits)
    ax.set_ylim(limits)
    ax.set_xlabel("Observed sqrt(AUDPC)")
    ax.set_ylabel("Posterior predictive mean")
    ax.set_title("True leave-one-year-out prediction")
    fig.tight_layout()
    fig.savefig(figures_dir / "leave_one_year_out_predictions.png", dpi=180)
    plt.close(fig)

    population = timing_summary.loc[timing_summary["scope"] == "population_average"].iloc[0]
    aggregate_loyo = loyo_metrics.loc[loyo_metrics["held_out_year"] == "ALL"].iloc[0]
    ppc_coverage90 = ppc_diagnostics.loc[
        ppc_diagnostics["statistic"] == "row_coverage_90", "observed"
    ].iloc[0]
    ppc_coverage95 = ppc_diagnostics.loc[
        ppc_diagnostics["statistic"] == "row_coverage_95", "observed"
    ].iloc[0]
    negative_fraction = ppc_diagnostics.loc[
        ppc_diagnostics["statistic"] == "negative_sqrt_prediction_fraction", "replicated_mean"
    ].iloc[0]
    max_rhat = float(
        max(
            timing_summary["rhat"].dropna().max(),
            variance_summary["rhat"].dropna().max(),
        )
    )

    summary: dict[str, object] = {
        "model": {
            "response": "sqrt_audpc standardised before fitting",
            "structure": (
                "population timing + partially pooled product effects + partially pooled "
                "product timing deviations + year random effects + year:block random effects"
            ),
            "chains": main_config.n_chains,
            "draws_per_chain": main_config.draws_per_chain,
            "burn_in": main_config.burn_in,
            "thin": main_config.thin,
            "max_classical_rhat": max_rhat,
            "prior": {
                "variance_shape": fit.prior.variance_shape,
                "residual_scale": fit.prior.residual_scale,
                "product_scale": fit.prior.product_scale,
                "product_timing_scale": fit.prior.product_timing_scale,
                "year_scale": fit.prior.year_scale,
                "year_block_scale": fit.prior.year_block_scale,
                "intercept_sd": fit.prior.intercept_sd,
                "population_timing_sd": fit.prior.population_timing_sd,
            },
        },
        "population_timing_effect": {
            "posterior_mean_delta_sqrt_audpc": float(
                population["posterior_mean_delta_sqrt_audpc"]
            ),
            "q05": float(population["q05"]),
            "q95": float(population["q95"]),
            "prob_late_greater_disease": float(population["prob_late_greater_disease"]),
        },
        "posterior_predictive_checks": {
            "training_coverage_90": float(ppc_coverage90),
            "training_coverage_95": float(ppc_coverage95),
            "negative_sqrt_prediction_fraction": float(negative_fraction),
        },
        "leave_one_year_out": {
            "rmse": float(aggregate_loyo["rmse"]),
            "mae": float(aggregate_loyo["mae"]),
            "coverage_90": float(aggregate_loyo["coverage_90"]),
            "coverage_95": float(aggregate_loyo["coverage_95"]),
            "mean_pi90_width": float(aggregate_loyo["mean_pi90_width"]),
            "mean_pi95_width": float(aggregate_loyo["mean_pi95_width"]),
        },
        "prior_sensitivity": {
            "multipliers": sensitivity["variance_prior_scale_multiplier"].tolist(),
            "population_timing_means": sensitivity["population_timing_mean"].tolist(),
            "prob_late_greater_disease": sensitivity["prob_late_greater_disease"].tolist(),
        },
        "interpretation": (
            "Partial pooling stabilises treatment-specific timing estimates, while honest "
            "unseen-year posterior prediction remains limited by absent environmental and "
            "biological covariates."
        ),
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    """CLI entry point for Bayesian hierarchical field-trial modelling."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_bayesian_demo(root), indent=2))


if __name__ == "__main__":
    main()
