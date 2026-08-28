"""Design-aware analysis utilities for the Richardson & Gent hop fungicide trial."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

SOURCE_REPOSITORY_URL: Final[str] = (
    "https://github.com/DavidGent-Lab/Richardon-and-Gent-2024-Plant-Health-Progress"
)
SOURCE_DATA_URL: Final[str] = f"{SOURCE_REPOSITORY_URL}/blob/main/Data%20Set.csv"
EXCLUDED_YEAR: Final[int] = 2019
EXPECTED_YEARS: Final[tuple[int, ...]] = (2017, 2018, 2019, 2020, 2021)
PRIMARY_YEARS: Final[tuple[int, ...]] = (2017, 2018, 2020, 2021)
EXPECTED_BLOCKS: Final[frozenset[str]] = frozenset({"I", "II", "III", "IV", "V"})
CONTROL_TREATMENTS: Final[frozenset[str]] = frozenset({"NT", "Kocide"})
EXPECTED_COLUMNS: Final[tuple[str, ...]] = (
    "Year",
    "TRT",
    "Block",
    "AUDPC",
    "Timing",
    "Treatment",
)


@dataclass(frozen=True)
class ValidationMetric:
    """Predictive validation metrics for one target and splitting strategy."""

    target: str
    strategy: str
    features: str
    n_folds: int
    rmse: float
    mae: float
    r2: float


def _require_columns(frame: pd.DataFrame, columns: Sequence[str]) -> None:
    """Raise a clear error if a required schema column is absent."""
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def load_hop_trial(path: Path) -> pd.DataFrame:
    """Load and validate the public multi-year hop downy-mildew field-trial data.

    Period symbols in the source file represent missing or inapplicable values. The returned
    frame uses lower-case canonical column names and adds analysis-safe derived identifiers.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Hop trial file not found: {path}")

    raw = pd.read_csv(path, na_values=["."])
    _require_columns(raw, EXPECTED_COLUMNS)

    frame = raw.loc[:, EXPECTED_COLUMNS].rename(
        columns={
            "Year": "year",
            "TRT": "trt",
            "Block": "block",
            "AUDPC": "audpc",
            "Timing": "timing",
            "Treatment": "treatment",
        }
    )
    frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype("int64")
    frame["audpc"] = pd.to_numeric(frame["audpc"], errors="coerce").astype("float64")
    frame["timing"] = frame["timing"].astype("string")
    frame["treatment"] = frame["treatment"].astype("string")
    frame["trt"] = frame["trt"].astype("string")
    frame["block"] = frame["block"].astype("string")

    observed_years = tuple(sorted(int(value) for value in frame["year"].unique()))
    if observed_years != EXPECTED_YEARS:
        raise ValueError(f"Unexpected trial years: {observed_years}; expected {EXPECTED_YEARS}")
    if set(frame["block"].dropna().unique()) != EXPECTED_BLOCKS:
        raise ValueError("Block structure does not match the documented I-V replication.")
    if (frame["audpc"].dropna() < 0).any():
        raise ValueError("AUDPC must be non-negative.")
    invalid_timing = set(frame["timing"].dropna().unique()).difference({"Early", "Late"})
    if invalid_timing:
        raise ValueError(f"Unexpected timing labels: {sorted(invalid_timing)}")

    frame["sqrt_audpc"] = np.sqrt(frame["audpc"])
    frame["year_block"] = frame["year"].astype(str) + ":" + frame["block"].astype(str)
    return frame


def prepare_primary_analysis(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the source-defined 2019 exclusion and add untreated-control normalisation.

    The original study excluded 2019 because flooding confounded disease measurements. This
    function keeps that exclusion explicit and computes a same-year untreated-control reference,
    which is useful for separating background disease pressure from treatment performance.
    """
    _require_columns(frame, ("year", "audpc", "treatment"))
    primary = frame.loc[(frame["year"] != EXCLUDED_YEAR) & frame["audpc"].notna()].copy()

    untreated = (
        primary.loc[primary["treatment"] == "NT"]
        .groupby("year", observed=True)["audpc"]
        .mean()
        .rename("untreated_mean_audpc")
    )
    if set(int(value) for value in untreated.index) != set(PRIMARY_YEARS):
        raise ValueError("Every primary year must contain an untreated control.")
    if (untreated <= 0).any():
        raise ValueError("Untreated mean AUDPC must be positive for normalisation.")

    primary = primary.join(untreated, on="year")
    primary["relative_disease"] = primary["audpc"] / primary["untreated_mean_audpc"]
    primary["control_efficacy"] = 1.0 - primary["relative_disease"]
    return primary


def prepare_timing_analysis(primary: pd.DataFrame) -> pd.DataFrame:
    """Return synthetic-fungicide observations used for early-vs-late timing analysis."""
    _require_columns(primary, ("treatment", "timing", "audpc", "sqrt_audpc"))
    mask = (
        ~primary["treatment"].isin(CONTROL_TREATMENTS)
        & primary["timing"].isin(["Early", "Late"])
        & primary["audpc"].notna()
    )
    timing = primary.loc[mask].copy()
    if timing.empty:
        raise ValueError("Timing analysis contains no valid observations.")
    return timing


def year_severity_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarise background disease pressure and source exclusion status by trial year."""
    _require_columns(frame, ("year", "audpc", "treatment"))
    overall = frame.groupby("year", observed=True)["audpc"].agg(
        all_treatments_mean_audpc="mean",
        n_observed="count",
    )
    untreated = (
        frame.loc[frame["treatment"] == "NT"]
        .groupby("year", observed=True)["audpc"]
        .agg(untreated_mean_audpc="mean", untreated_sd_audpc="std")
    )
    table = overall.join(untreated).reset_index()
    table["primary_analysis"] = table["year"] != EXCLUDED_YEAR
    return table


def treatment_timing_summary(timing: pd.DataFrame) -> pd.DataFrame:
    """Summarise observed disease and control-normalised efficacy by product and timing."""
    _require_columns(timing, ("treatment", "timing", "audpc", "control_efficacy"))
    return (
        timing.groupby(["treatment", "timing"], observed=True)
        .agg(
            n=("audpc", "size"),
            mean_audpc=("audpc", "mean"),
            sd_audpc=("audpc", "std"),
            mean_control_efficacy=("control_efficacy", "mean"),
            sd_control_efficacy=("control_efficacy", "std"),
        )
        .reset_index()
    )


def paired_timing_differences(timing: pd.DataFrame) -> pd.DataFrame:
    """Create within-year, within-block, within-product early-vs-late contrasts."""
    _require_columns(timing, ("year", "block", "treatment", "timing", "audpc", "sqrt_audpc"))

    audpc = timing.pivot_table(
        index=["year", "block", "treatment"],
        columns="timing",
        values="audpc",
        aggfunc="first",
    )
    sqrt_audpc = timing.pivot_table(
        index=["year", "block", "treatment"],
        columns="timing",
        values="sqrt_audpc",
        aggfunc="first",
    )
    paired = audpc.join(sqrt_audpc, lsuffix="_audpc", rsuffix="_sqrt_audpc")
    paired = paired.dropna(
        subset=["Early_audpc", "Late_audpc", "Early_sqrt_audpc", "Late_sqrt_audpc"]
    ).reset_index()
    paired = paired.rename(
        columns={
            "Early_audpc": "early_audpc",
            "Late_audpc": "late_audpc",
            "Early_sqrt_audpc": "early_sqrt_audpc",
            "Late_sqrt_audpc": "late_sqrt_audpc",
        }
    )
    paired["delta_audpc_late_minus_early"] = paired["late_audpc"] - paired["early_audpc"]
    paired["delta_sqrt_audpc_late_minus_early"] = (
        paired["late_sqrt_audpc"] - paired["early_sqrt_audpc"]
    )
    paired["year_block"] = paired["year"].astype(str) + ":" + paired["block"].astype(str)
    return paired


def _bootstrap_mean(
    values: np.ndarray,
    *,
    rng: np.random.Generator,
    n_bootstrap: int,
) -> tuple[float, float]:
    """Return a percentile bootstrap interval for a one-dimensional mean."""
    if values.ndim != 1 or len(values) < 2:
        raise ValueError("At least two one-dimensional observations are required.")
    indices = rng.integers(0, len(values), size=(n_bootstrap, len(values)))
    draws = values[indices].mean(axis=1)
    lower, upper = np.quantile(draws, [0.025, 0.975])
    return float(lower), float(upper)


def bootstrap_timing_effects(
    paired: pd.DataFrame,
    *,
    n_bootstrap: int = 5_000,
    seed: int = 20260826,
) -> pd.DataFrame:
    """Estimate uncertainty for paired early-vs-late timing contrasts.

    The overall interval resamples year-block clusters so correlated product contrasts from the
    same experimental block move together. Product-specific intervals resample that product's
    paired year-block observations.
    """
    if n_bootstrap < 100:
        raise ValueError("n_bootstrap must be at least 100.")
    _require_columns(
        paired,
        (
            "year",
            "block",
            "treatment",
            "delta_audpc_late_minus_early",
            "delta_sqrt_audpc_late_minus_early",
        ),
    )
    rng = np.random.default_rng(seed)
    cluster_keys = list(
        paired[["year", "block"]].drop_duplicates().itertuples(index=False, name=None)
    )
    if len(cluster_keys) < 2:
        raise ValueError("At least two year-block clusters are required.")

    cluster_stats = (
        paired.groupby(["year", "block"], observed=True)
        .agg(
            raw_sum=("delta_audpc_late_minus_early", "sum"),
            sqrt_sum=("delta_sqrt_audpc_late_minus_early", "sum"),
            n=("delta_audpc_late_minus_early", "size"),
        )
        .reindex(pd.MultiIndex.from_tuples(cluster_keys, names=["year", "block"]))
    )
    raw_sums = cluster_stats["raw_sum"].to_numpy(dtype=float)
    sqrt_sums = cluster_stats["sqrt_sum"].to_numpy(dtype=float)
    counts = cluster_stats["n"].to_numpy(dtype=float)
    selected = rng.integers(
        0, len(cluster_keys), size=(n_bootstrap, len(cluster_keys))
    )
    selected_counts = counts[selected].sum(axis=1)
    overall_draws_raw = raw_sums[selected].sum(axis=1) / selected_counts
    overall_draws_sqrt = sqrt_sums[selected].sum(axis=1) / selected_counts

    records: list[dict[str, object]] = [
        {
            "scope": "all_products",
            "treatment": "ALL",
            "n_pairs": int(len(paired)),
            "mean_delta_audpc_late_minus_early": float(
                paired["delta_audpc_late_minus_early"].mean()
            ),
            "ci95_low_audpc": float(np.quantile(overall_draws_raw, 0.025)),
            "ci95_high_audpc": float(np.quantile(overall_draws_raw, 0.975)),
            "mean_delta_sqrt_audpc_late_minus_early": float(
                paired["delta_sqrt_audpc_late_minus_early"].mean()
            ),
            "ci95_low_sqrt_audpc": float(np.quantile(overall_draws_sqrt, 0.025)),
            "ci95_high_sqrt_audpc": float(np.quantile(overall_draws_sqrt, 0.975)),
        }
    ]

    for treatment in sorted(str(value) for value in paired["treatment"].unique()):
        subset = paired.loc[paired["treatment"] == treatment]
        raw = subset["delta_audpc_late_minus_early"].to_numpy(dtype=float)
        sqrt_values = subset["delta_sqrt_audpc_late_minus_early"].to_numpy(dtype=float)
        raw_low, raw_high = _bootstrap_mean(raw, rng=rng, n_bootstrap=n_bootstrap)
        sqrt_low, sqrt_high = _bootstrap_mean(
            sqrt_values, rng=rng, n_bootstrap=n_bootstrap
        )
        records.append(
            {
                "scope": "product",
                "treatment": treatment,
                "n_pairs": int(len(subset)),
                "mean_delta_audpc_late_minus_early": float(np.mean(raw)),
                "ci95_low_audpc": raw_low,
                "ci95_high_audpc": raw_high,
                "mean_delta_sqrt_audpc_late_minus_early": float(np.mean(sqrt_values)),
                "ci95_low_sqrt_audpc": sqrt_low,
                "ci95_high_sqrt_audpc": sqrt_high,
            }
        )
    return pd.DataFrame.from_records(records)


def _make_ridge_pipeline(features: Sequence[str]) -> Pipeline:
    """Construct a deterministic one-hot + ridge benchmark for categorical trial predictors."""
    preprocessor = ColumnTransformer(
        [("categorical", OneHotEncoder(handle_unknown="ignore"), list(features))]
    )
    return Pipeline([("preprocess", preprocessor), ("model", Ridge(alpha=1.0))])


def _metric(
    *,
    target: str,
    strategy: str,
    features: Sequence[str],
    n_folds: int,
    actual: list[float],
    predicted: list[float],
) -> ValidationMetric:
    """Build one immutable validation result with consistent metrics."""
    y_true = np.asarray(actual, dtype=float)
    y_pred = np.asarray(predicted, dtype=float)
    return ValidationMetric(
        target=target,
        strategy=strategy,
        features=" + ".join(features),
        n_folds=n_folds,
        rmse=float(np.sqrt(mean_squared_error(y_true, y_pred))),
        mae=float(mean_absolute_error(y_true, y_pred)),
        r2=float(r2_score(y_true, y_pred)),
    )


def compare_year_transportability(
    timing: pd.DataFrame,
    *,
    seed: int = 20260826,
) -> pd.DataFrame:
    """Contrast random CV with prediction into an entirely unseen trial year.

    Two deliberately different targets are shown:

    * ``sqrt_audpc`` with a categorical year proxy demonstrates how random CV can exploit a
      trial-year identifier that has no transportable meaning for a future year.
    * ``relative_disease`` uses same-year untreated controls for calibration and only treatment
      and timing as predictors, providing a more defensible field-trial comparison.
    """
    specifications: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("sqrt_audpc", ("treatment", "timing", "year")),
        ("relative_disease", ("treatment", "timing")),
    )
    records: list[ValidationMetric] = []

    for target, features in specifications:
        _require_columns(timing, (*features, target, "year"))
        x = timing.loc[:, features]
        y = timing[target].to_numpy(dtype=float)

        random_splitter = KFold(n_splits=5, shuffle=True, random_state=seed)
        actual: list[float] = []
        predicted: list[float] = []
        for train_index, test_index in random_splitter.split(x):
            model = _make_ridge_pipeline(features)
            model.fit(x.iloc[train_index], y[train_index])
            actual.extend(y[test_index].tolist())
            predicted.extend(model.predict(x.iloc[test_index]).tolist())
        records.append(
            _metric(
                target=target,
                strategy="random_5fold",
                features=features,
                n_folds=random_splitter.get_n_splits(),
                actual=actual,
                predicted=predicted,
            )
        )

        groups = timing["year"].to_numpy(dtype=int)
        year_splitter = LeaveOneGroupOut()
        actual = []
        predicted = []
        n_folds = 0
        for train_index, test_index in year_splitter.split(x, y, groups):
            model = _make_ridge_pipeline(features)
            model.fit(x.iloc[train_index], y[train_index])
            actual.extend(y[test_index].tolist())
            predicted.extend(model.predict(x.iloc[test_index]).tolist())
            n_folds += 1
        records.append(
            _metric(
                target=target,
                strategy="leave_one_year_out",
                features=features,
                n_folds=n_folds,
                actual=actual,
                predicted=predicted,
            )
        )

    table = pd.DataFrame([record.__dict__ for record in records])
    gaps: dict[str, float] = {}
    for target in table["target"].unique():
        subset = table.loc[table["target"] == target].set_index("strategy")
        random_rmse = float(subset.loc["random_5fold", "rmse"])
        loyo_rmse = float(subset.loc["leave_one_year_out", "rmse"])
        gaps[str(target)] = 100.0 * (loyo_rmse / random_rmse - 1.0)
    table["loyo_rmse_increase_pct"] = table["target"].map(gaps)
    return table
