"""Sensitivity of the hop timing contrast to field blocks and trial years.

The source study excluded the flooded 2019 season. All diagnostics here retain
the original within-year, within-block, within-product pairing and treat a
trial year as a distinct environment. The bootstrap is a descriptive
resampling sensitivity analysis, not randomisation-based causal inference.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from crop_protection_ps.hop_trial import (
    EXCLUDED_YEAR,
    load_hop_trial,
    paired_timing_differences,
    prepare_primary_analysis,
    prepare_timing_analysis,
)

_RAW_DELTA = "delta_audpc_late_minus_early"
_SQRT_DELTA = "delta_sqrt_audpc_late_minus_early"
_FIELDS = ("year", "block", "treatment", _RAW_DELTA, _SQRT_DELTA)
_REPORT_DECIMALS = 10


@dataclass(frozen=True)
class TimingSensitivity:
    """Analysis tables and a JSON-compatible reproducibility summary."""

    by_year: pd.DataFrame
    without_year: pd.DataFrame
    without_year_block: pd.DataFrame
    summary: dict[str, Any]


def _validated_pairs(paired: pd.DataFrame) -> pd.DataFrame:
    """Validate independent cluster keys and finite, source-paired outcomes."""
    missing = sorted(set(_FIELDS).difference(paired.columns))
    if missing:
        raise ValueError(f"missing paired timing columns: {missing}")
    if paired.empty:
        raise ValueError("paired timing data cannot be empty")
    if paired.loc[:, ["year", "block", "treatment"]].isna().any().any():
        raise ValueError("paired year, block and product identifiers must be present")
    if paired.duplicated(["year", "block", "treatment"]).any():
        raise ValueError("duplicate year-block-product comparisons")
    if not pd.api.types.is_integer_dtype(paired["year"]):
        raise ValueError("year must be an integer identifier")
    if (paired["year"] == EXCLUDED_YEAR).any():
        raise ValueError("source-excluded 2019 cannot enter the primary sensitivity analysis")
    deltas = paired.loc[:, [_RAW_DELTA, _SQRT_DELTA]].to_numpy(dtype=float)
    if not np.isfinite(deltas).all():
        raise ValueError("all paired timing differences must be finite")
    if paired["year"].nunique() < 2:
        raise ValueError("at least two independent trial years are required")
    blocks_per_year = paired.groupby("year", observed=True)["block"].nunique()
    if (blocks_per_year < 2).any():
        raise ValueError("each trial year requires at least two field blocks")
    return paired.sort_values(["year", "block", "treatment"]).reset_index(drop=True)


def _estimates(frame: pd.DataFrame) -> dict[str, float]:
    """Compute row-pair-weighted and equally-year-weighted contrasts."""
    by_year = frame.groupby("year", observed=True)[[_RAW_DELTA, _SQRT_DELTA]].mean()
    return {
        "pair_weighted_audpc": round(float(frame[_RAW_DELTA].mean()), _REPORT_DECIMALS),
        "equal_year_audpc": round(float(by_year[_RAW_DELTA].mean()), _REPORT_DECIMALS),
        "pair_weighted_sqrt_audpc": round(float(frame[_SQRT_DELTA].mean()), _REPORT_DECIMALS),
        "equal_year_sqrt_audpc": round(float(by_year[_SQRT_DELTA].mean()), _REPORT_DECIMALS),
    }


def _nested_bootstrap(
    paired: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
) -> dict[str, dict[str, float]]:
    """Resample trial years, then whole field blocks within selected years.

    All product comparisons within a selected block move together. When a year
    is sampled twice, its blocks are sampled independently in each appearance.
    Product composition is retained within a selected block; no pseudo-pairs
    are created for missing products.
    """
    grouped = (
        paired.groupby(["year", "block"], observed=True)
        .agg(raw_sum=(_RAW_DELTA, "sum"), sqrt_sum=(_SQRT_DELTA, "sum"), pairs=(_RAW_DELTA, "size"))
        .reset_index()
    )
    years = sorted(int(value) for value in grouped["year"].unique())
    block_matrices = [
        grouped.loc[grouped["year"] == year, ["raw_sum", "sqrt_sum", "pairs"]].to_numpy(
            dtype=float
        )
        for year in years
    ]
    rng = np.random.default_rng(seed)
    draws = np.empty((n_bootstrap, 4), dtype=float)

    for draw_index in range(n_bootstrap):
        drawn_years = rng.integers(0, len(years), size=len(years))
        drawn_blocks = []
        for year_index in drawn_years:
            clusters = block_matrices[int(year_index)]
            indices = rng.integers(0, len(clusters), size=len(clusters))
            # Each sampled field block contributes every observed product pair.
            drawn_blocks.append(clusters[indices].sum(axis=0))
        totals = np.vstack(drawn_blocks)
        grand = totals.sum(axis=0)
        draws[draw_index, 0] = grand[0] / grand[2]
        draws[draw_index, 1] = float(np.mean(totals[:, 0] / totals[:, 2]))
        draws[draw_index, 2] = grand[1] / grand[2]
        draws[draw_index, 3] = float(np.mean(totals[:, 1] / totals[:, 2]))

    names = (
        "pair_weighted_audpc",
        "equal_year_audpc",
        "pair_weighted_sqrt_audpc",
        "equal_year_sqrt_audpc",
    )
    return {
        name: {
            "lower_95_percentile": round(
                float(np.quantile(draws[:, column], 0.025)), _REPORT_DECIMALS
            ),
            "upper_95_percentile": round(
                float(np.quantile(draws[:, column], 0.975)), _REPORT_DECIMALS
            ),
        }
        for column, name in enumerate(names)
    }


def analyse_hop_timing_sensitivity(
    paired: pd.DataFrame,
    *,
    n_bootstrap: int = 5_000,
    seed: int = 20261107,
) -> TimingSensitivity:
    """Audit timing contrast stability under omitted years and whole field blocks.

    The year-equal estimand gives each trial season equal weight, whereas the
    original pair-weighted estimand reflects the observed number of complete
    product pairs in each year. Differences between them are compositional.
    """
    if isinstance(n_bootstrap, bool) or not isinstance(n_bootstrap, int) or n_bootstrap < 100:
        raise ValueError("n_bootstrap must be an integer of at least 100")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    clean = _validated_pairs(paired)
    estimates = _estimates(clean)

    yearly = (
        clean.groupby("year", observed=True)
        .agg(
            n_pairs=(_RAW_DELTA, "size"),
            n_blocks=("block", "nunique"),
            n_products=("treatment", "nunique"),
            mean_delta_audpc=(_RAW_DELTA, "mean"),
            mean_delta_sqrt_audpc=(_SQRT_DELTA, "mean"),
        )
        .reset_index()
    )
    without_year_records: list[dict[str, float | int]] = []
    for year in yearly["year"]:
        subset = clean.loc[clean["year"] != year]
        if subset.empty:
            raise ValueError("omitting a trial year removed all comparisons")
        without_year_records.append(
            {"omitted_year": int(year), "n_pairs": len(subset), **_estimates(subset)}
        )

    without_cluster_records: list[dict[str, float | int | str]] = []
    for (year, block), _ in clean.groupby(["year", "block"], sort=True, observed=True):
        subset = clean.loc[(clean["year"] != year) | (clean["block"] != block)]
        subset_estimates = _estimates(subset)
        without_cluster_records.append(
            {
                "omitted_year": int(year),
                "omitted_block": str(block),
                "n_pairs": len(subset),
                **subset_estimates,
                "raw_effect_shift": round(
                    subset_estimates["pair_weighted_audpc"] - estimates["pair_weighted_audpc"],
                    _REPORT_DECIMALS,
                ),
            }
        )

    without_year = pd.DataFrame.from_records(without_year_records)
    without_cluster = pd.DataFrame.from_records(without_cluster_records)
    bootstrap_intervals = _nested_bootstrap(clean, n_bootstrap=n_bootstrap, seed=seed)
    by_year_signs = np.sign(yearly["mean_delta_audpc"].to_numpy(dtype=float))
    summary: dict[str, Any] = {
        "n_trial_years": len(yearly),
        "n_year_blocks": len(without_cluster),
        "n_complete_product_pairs": len(clean),
        "source_excluded_year": EXCLUDED_YEAR,
        "estimands": estimates,
        "year_effects_sign_agreement": bool((by_year_signs == by_year_signs[0]).all()),
        "leave_one_year_out_pair_weighted_raw_range": [
            round(float(without_year["pair_weighted_audpc"].min()), _REPORT_DECIMALS),
            round(float(without_year["pair_weighted_audpc"].max()), _REPORT_DECIMALS),
        ],
        "maximum_absolute_year_block_influence_audpc": round(
            float(without_cluster["raw_effect_shift"].abs().max()), _REPORT_DECIMALS
        ),
        "nested_year_block_bootstrap": {
            "resamples": n_bootstrap,
            "seed": seed,
            "percentile_intervals": bootstrap_intervals,
        },
        "interpretation_boundary": (
            "Four eligible years, after the source-defined exclusion of 2019. "
            "Nested bootstrap percentiles are sensitivity summaries, not "
            "small-sample calibrated confidence intervals, randomisation tests, "
            "or evidence of transportability to new locations or years."
        ),
    }
    return TimingSensitivity(yearly, without_year, without_cluster, summary)


def run_hop_timing_sensitivity(root: Path) -> dict[str, Any]:
    """Write deterministic sensitivity tables from the original public hop CSV."""
    raw_path = root / "data/raw/richardson_gent_hop_downy_mildew.csv"
    paired = paired_timing_differences(
        prepare_timing_analysis(prepare_primary_analysis(load_hop_trial(raw_path)))
    )
    analysis = analyse_hop_timing_sensitivity(paired)
    output = root / "results/real_hop_trial/timing_sensitivity"
    output.mkdir(parents=True, exist_ok=True)
    # Published digits are fixed to avoid irrelevant cross-runtime float noise.
    float_format = f"%.{_REPORT_DECIMALS}f"
    analysis.by_year.to_csv(output / "by_year.csv", index=False, float_format=float_format)
    analysis.without_year.to_csv(
        output / "leave_one_year_out.csv", index=False, float_format=float_format
    )
    analysis.without_year_block.to_csv(
        output / "leave_one_year_block_out.csv", index=False, float_format=float_format
    )
    summary: dict[str, Any] = {
        "source_path": raw_path.relative_to(root).as_posix(),
        "source_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        **analysis.summary,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    """CLI for regenerating the checked-in hop sensitivity artifacts."""
    print(json.dumps(run_hop_timing_sensitivity(Path(__file__).resolve().parents[2]), indent=2))


if __name__ == "__main__":
    main()
