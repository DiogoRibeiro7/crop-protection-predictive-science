"""Executable real-data case study for the public hop fungicide field trial."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from crop_protection_ps.hop_trial import (
    EXCLUDED_YEAR,
    SOURCE_DATA_URL,
    bootstrap_timing_effects,
    compare_year_transportability,
    load_hop_trial,
    paired_timing_differences,
    prepare_primary_analysis,
    prepare_timing_analysis,
    treatment_timing_summary,
    year_severity_table,
)


def _sha256(path: Path) -> str:
    """Compute a SHA-256 digest for provenance reporting."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_real_demo(root: Path) -> dict[str, object]:
    """Run the real fungicide field-trial case study and persist reproducible outputs."""
    raw_path = root / "data" / "raw" / "richardson_gent_hop_downy_mildew.csv"
    results_dir = root / "results" / "real_hop_trial"
    figures_dir = results_dir / "figures"
    processed_dir = root / "data" / "processed"
    results_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    raw = load_hop_trial(raw_path)
    primary = prepare_primary_analysis(raw)
    timing = prepare_timing_analysis(primary)
    paired = paired_timing_differences(timing)

    primary.to_csv(processed_dir / "hop_trial_primary.csv", index=False)
    year_table = year_severity_table(raw)
    year_table.to_csv(results_dir / "year_severity.csv", index=False)
    timing_table = treatment_timing_summary(timing)
    timing_table.to_csv(results_dir / "treatment_timing_summary.csv", index=False)
    paired.to_csv(results_dir / "paired_timing_differences.csv", index=False)

    bootstrap = bootstrap_timing_effects(paired, n_bootstrap=5_000)
    bootstrap.to_csv(results_dir / "timing_effect_bootstrap.csv", index=False)

    transportability = compare_year_transportability(timing)
    transportability.to_csv(results_dir / "year_transportability.csv", index=False)

    # Source-aligned re-analysis: the paper used a GLIMMIX model on sqrt(AUDPC) with
    # Treatment × Timing and random year/block terms. Here we use explicit year and
    # year-block fixed effects as a transparent Python approximation, not as a claim of
    # numerical equivalence to SAS GLIMMIX/Kenward-Roger inference.
    analysis = timing.copy()
    fixed_formula = (
        "sqrt_audpc ~ C(treatment) * C(timing) + C(year) + C(year_block)"
    )
    fixed_model = smf.ols(fixed_formula, data=analysis).fit()
    anova = sm.stats.anova_lm(fixed_model, typ=2)
    anova.index.name = "term"
    anova.reset_index().to_csv(results_dir / "source_aligned_fixed_effects_anova.csv", index=False)
    (results_dir / "source_aligned_fixed_effects_summary.txt").write_text(
        fixed_model.summary().as_text(), encoding="utf-8"
    )

    # Figure 1: show why trial-year context matters, including the source-excluded 2019 year.
    figure_table = year_table.copy()
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(figure_table["year"], figure_table["untreated_mean_audpc"], marker="o")
    ax.axvline(EXCLUDED_YEAR, linestyle="--")
    ax.set_xlabel("Trial year")
    ax.set_ylabel("Mean untreated AUDPC")
    ax.set_title("Background disease pressure differs strongly by trial year")
    ax.text(EXCLUDED_YEAR + 0.04, ax.get_ylim()[1] * 0.88, "2019: source-excluded")
    fig.tight_layout()
    fig.savefig(figures_dir / "year_disease_pressure.png", dpi=180)
    plt.close(fig)

    # Figure 2: paired product-specific early-vs-late contrasts. Positive means late timing
    # produced higher AUDPC (more disease) than early timing in the same year/block/product.
    product_effects = bootstrap.loc[bootstrap["scope"] == "product"].copy()
    product_effects = product_effects.sort_values("mean_delta_audpc_late_minus_early")
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    x = product_effects["mean_delta_audpc_late_minus_early"]
    xerr = [
        x - product_effects["ci95_low_audpc"],
        product_effects["ci95_high_audpc"] - x,
    ]
    ax.errorbar(x, product_effects["treatment"], xerr=xerr, fmt="o", capsize=3)
    ax.axvline(0.0, linestyle="--")
    ax.set_xlabel("Late − early AUDPC (paired mean, 95% bootstrap interval)")
    ax.set_ylabel("Product")
    ax.set_title("Timing effect varies by fungicide")
    fig.tight_layout()
    fig.savefig(figures_dir / "paired_timing_effects.png", dpi=180)
    plt.close(fig)

    # Figure 3: random CV can dramatically overstate future-year performance.
    raw_target = transportability.loc[transportability["target"] == "sqrt_audpc"].copy()
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.bar(raw_target["strategy"], raw_target["rmse"])
    ax.set_ylabel("RMSE on sqrt(AUDPC)")
    ax.set_xlabel("")
    ax.set_title("Random CV versus an entirely unseen trial year")
    ax.tick_params(axis="x", rotation=0)
    fig.tight_layout()
    fig.savefig(figures_dir / "year_transportability_gap.png", dpi=180)
    plt.close(fig)

    overall = bootstrap.loc[bootstrap["scope"] == "all_products"].iloc[0]
    raw_cv = transportability.loc[
        (transportability["target"] == "sqrt_audpc")
        & (transportability["strategy"] == "random_5fold")
    ].iloc[0]
    raw_loyo = transportability.loc[
        (transportability["target"] == "sqrt_audpc")
        & (transportability["strategy"] == "leave_one_year_out")
    ].iloc[0]
    normalised_cv = transportability.loc[
        (transportability["target"] == "relative_disease")
        & (transportability["strategy"] == "random_5fold")
    ].iloc[0]
    normalised_loyo = transportability.loc[
        (transportability["target"] == "relative_disease")
        & (transportability["strategy"] == "leave_one_year_out")
    ].iloc[0]

    summary: dict[str, object] = {
        "source": {
            "url": SOURCE_DATA_URL,
            "local_file": str(raw_path.relative_to(root)),
            "local_sha256": _sha256(raw_path),
        },
        "data": {
            "raw_rows": int(len(raw)),
            "missing_audpc": int(raw["audpc"].isna().sum()),
            "years": sorted(int(value) for value in raw["year"].unique()),
            "source_excluded_year": EXCLUDED_YEAR,
            "primary_rows": int(len(primary)),
            "timing_analysis_rows": int(len(timing)),
            "paired_timing_comparisons": int(len(paired)),
        },
        "paired_timing": {
            "interpretation": "positive late-minus-early means greater disease under late timing",
            "mean_delta_audpc_late_minus_early": float(
                overall["mean_delta_audpc_late_minus_early"]
            ),
            "ci95_audpc": [
                float(overall["ci95_low_audpc"]),
                float(overall["ci95_high_audpc"]),
            ],
            "mean_delta_sqrt_audpc_late_minus_early": float(
                overall["mean_delta_sqrt_audpc_late_minus_early"]
            ),
            "ci95_sqrt_audpc": [
                float(overall["ci95_low_sqrt_audpc"]),
                float(overall["ci95_high_sqrt_audpc"]),
            ],
        },
        "transportability": {
            "raw_sqrt_audpc_random_rmse": float(raw_cv["rmse"]),
            "raw_sqrt_audpc_leave_one_year_out_rmse": float(raw_loyo["rmse"]),
            "raw_rmse_increase_pct": float(raw_loyo["loyo_rmse_increase_pct"]),
            "control_normalised_random_rmse": float(normalised_cv["rmse"]),
            "control_normalised_leave_one_year_out_rmse": float(normalised_loyo["rmse"]),
            "control_normalised_rmse_increase_pct": float(
                normalised_loyo["loyo_rmse_increase_pct"]
            ),
        },
        "source_aligned_fixed_effects": {
            "formula": fixed_formula,
            "r_squared": float(fixed_model.rsquared),
            "note": (
                "Transparent Python fixed-effect approximation; not a numerical reproduction "
                "of the source SAS GLIMMIX/Kenward-Roger analysis."
            ),
        },
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    """CLI entry point for the public real-data case study."""
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(run_real_demo(root), indent=2))


if __name__ == "__main__":
    main()
