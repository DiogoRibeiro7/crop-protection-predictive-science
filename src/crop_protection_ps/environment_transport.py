"""Environment-aware transportability analysis for Crop Protection field trials.

The module deliberately separates three predictive contexts:

1. treatment and timing only;
2. coarse exogenous weather available for the trial environment;
3. an in-season untreated-control sentinel that measures realised disease pressure.

The purpose is not to claim that a four-year experiment identifies a general product-by-
environment response surface. Instead, genuine leave-one-year-out validation is used as a gate
before promoting additional interaction complexity.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

_MONTHS: Final[tuple[str, ...]] = ("February", "March", "April", "May")
_CLIMATOLOGY_YEARS: Final[tuple[int, ...]] = tuple(range(2009, 2017))
_PRIMARY_YEARS: Final[tuple[int, ...]] = (2017, 2018, 2020, 2021)
_WEATHER_COLUMNS: Final[tuple[str, ...]] = (
    "year",
    "month",
    "avg_temp_c",
    "sunshine_hours",
    "rainfall_mm",
    "rain_days",
)
ModelName = Literal["baseline", "coarse_weather", "sentinel", "sentinel_gxe"]


@dataclass(frozen=True)
class EnvironmentModelMetric:
    """One leave-one-year-out score for an environment-aware predictive model."""

    model: ModelName
    held_out_year: int | str
    n_test: int
    rmse: float
    mae: float
    r2: float


@dataclass(frozen=True)
class PromotionGate:
    """Decision record for whether extra GxE complexity survived deployment-style validation."""

    candidate_model: str
    reference_model: str
    aggregate_rmse_candidate: float
    aggregate_rmse_reference: float
    fold_wins: int
    n_folds: int
    promoted: bool


def _require_columns(frame: pd.DataFrame, columns: Sequence[str]) -> None:
    """Validate a dataframe contract with a useful error message."""
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def load_corvallis_weather(path: Path) -> pd.DataFrame:
    """Load and validate the versioned Corvallis monthly weather table."""
    if not path.is_file():
        raise FileNotFoundError(f"Weather file not found: {path}")
    frame = pd.read_csv(path)
    _require_columns(frame, _WEATHER_COLUMNS)
    frame = frame.loc[:, _WEATHER_COLUMNS].copy()
    frame["year"] = pd.to_numeric(frame["year"], errors="raise").astype("int64")
    frame["month"] = frame["month"].astype("string")
    for column in ("avg_temp_c", "sunshine_hours", "rainfall_mm", "rain_days"):
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("float64")
        if not np.isfinite(frame[column]).all():
            raise ValueError(f"Weather column {column!r} contains non-finite values.")
    if (frame[["sunshine_hours", "rainfall_mm", "rain_days"]] < 0).any().any():
        raise ValueError("Weather exposure variables must be non-negative.")
    if set(frame["month"].unique()) != set(_MONTHS):
        raise ValueError(f"Expected exactly the months {_MONTHS}.")
    counts = frame.groupby("year", observed=True)["month"].nunique()
    if not (counts == len(_MONTHS)).all():
        raise ValueError("Each weather year must contain February-May exactly once.")
    return frame.sort_values(["year", "month"]).reset_index(drop=True)


def _window_aggregate(
    frame: pd.DataFrame,
    *,
    months: tuple[str, ...],
    prefix: str,
) -> pd.DataFrame:
    """Aggregate monthly summaries into a scientifically named seasonal window."""
    subset = frame.loc[frame["month"].isin(months)].copy()
    days_in_month = {"February": 28.0, "March": 31.0, "April": 30.0, "May": 31.0}
    subset["temperature_weight"] = subset["month"].map(days_in_month).astype(float)
    subset["weighted_temperature"] = subset["avg_temp_c"] * subset["temperature_weight"]
    grouped = subset.groupby("year", observed=True).agg(
        rainfall_mm=("rainfall_mm", "sum"),
        rain_days=("rain_days", "sum"),
        sunshine_hours=("sunshine_hours", "sum"),
        weighted_temperature=("weighted_temperature", "sum"),
        temperature_weight=("temperature_weight", "sum"),
    )
    grouped["avg_temp_c"] = grouped["weighted_temperature"] / grouped["temperature_weight"]
    grouped = grouped.drop(columns=["weighted_temperature", "temperature_weight"])
    return grouped.add_prefix(f"{prefix}_").reset_index()


def derive_environment_features(weather: pd.DataFrame) -> pd.DataFrame:
    """Create external weather-state features using a pre-trial climatological reference.

    February-March is treated as a pre-application window, while April-May approximates the
    application/disease-development window described in the source experiment. Z-scores are
    fixed against 2009-2016 weather only, so the feature definition does not learn from trial
    outcomes or from later years.
    """
    _require_columns(weather, _WEATHER_COLUMNS)
    preseason = _window_aggregate(
        weather, months=("February", "March"), prefix="preseason"
    )
    application = _window_aggregate(
        weather, months=("April", "May"), prefix="application"
    )
    features = preseason.merge(application, on="year", validate="one_to_one")
    baseline = features.loc[features["year"].isin(_CLIMATOLOGY_YEARS)].copy()
    if tuple(sorted(int(value) for value in baseline["year"].unique())) != _CLIMATOLOGY_YEARS:
        raise ValueError("The complete 2009-2016 climatology is required.")

    for prefix in ("preseason", "application"):
        for variable in ("rainfall_mm", "rain_days", "sunshine_hours", "avg_temp_c"):
            column = f"{prefix}_{variable}"
            mean = float(baseline[column].mean())
            std = float(baseline[column].std(ddof=0))
            if not np.isfinite(std) or std <= 0:
                raise ValueError(f"Cannot standardise constant weather feature {column!r}.")
            features[f"{column}_z"] = (features[column] - mean) / std
        features[f"{prefix}_wetness_z"] = (
            features[f"{prefix}_rainfall_mm_z"]
            + features[f"{prefix}_rain_days_z"]
            - features[f"{prefix}_sunshine_hours_z"]
        ) / 3.0

    return features.sort_values("year").reset_index(drop=True)


def attach_environment_state(
    timing: pd.DataFrame,
    primary: pd.DataFrame,
    environment: pd.DataFrame,
) -> pd.DataFrame:
    """Attach exogenous weather plus a same-year untreated-control disease sentinel.

    The sentinel uses only rows whose treatment is ``NT``. It is therefore interpreted as an
    in-season state measurement, not as a pre-season covariate. That distinction is preserved in
    outputs because it changes the deployment question substantially.
    """
    _require_columns(timing, ("year", "treatment", "timing", "sqrt_audpc", "block"))
    _require_columns(primary, ("year", "treatment", "audpc"))
    _require_columns(
        environment,
        (
            "year",
            "preseason_wetness_z",
            "application_wetness_z",
            "application_avg_temp_c_z",
        ),
    )
    sentinel = (
        primary.loc[primary["treatment"] == "NT"]
        .groupby("year", observed=True)["audpc"]
        .agg(sentinel_mean_audpc="mean", sentinel_n="size")
        .reset_index()
    )
    if tuple(sorted(int(value) for value in sentinel["year"].unique())) != _PRIMARY_YEARS:
        raise ValueError("Every primary trial year needs an untreated-control sentinel.")
    if (sentinel["sentinel_mean_audpc"] <= 0).any():
        raise ValueError("Sentinel AUDPC must be strictly positive.")
    sentinel["sentinel_sqrt_audpc"] = np.sqrt(sentinel["sentinel_mean_audpc"])

    result = timing.merge(environment, on="year", how="left", validate="many_to_one")
    result = result.merge(sentinel, on="year", how="left", validate="many_to_one")
    required_values = result[
        [
            "preseason_wetness_z",
            "application_wetness_z",
            "application_avg_temp_c_z",
            "sentinel_sqrt_audpc",
        ]
    ]
    if required_values.isna().any().any():
        raise ValueError("Environment join introduced missing trial-year features.")
    return result


def _base_design(frame: pd.DataFrame, product_levels: tuple[str, ...]) -> pd.DataFrame:
    """Build a stable reference-coded treatment/timing design matrix."""
    matrix = pd.DataFrame(index=frame.index)
    matrix["intercept"] = 1.0
    matrix["late"] = (frame["timing"].astype(str) == "Late").astype(float)
    reference = product_levels[0]
    for product in product_levels[1:]:
        matrix[f"product[{product}]"] = (
            frame["treatment"].astype(str) == product
        ).astype(float)
    if (frame["treatment"].astype(str) == reference).sum() == 0:
        # A missing reference in a test fold is harmless; in training it is caught by the caller.
        pass
    return matrix


def _design_for_model(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    model: ModelName,
) -> tuple[NDArray[np.float64], NDArray[np.float64], tuple[str, ...]]:
    """Construct aligned train/test matrices without test-outcome leakage."""
    products = tuple(sorted(str(value) for value in train["treatment"].unique()))
    if len(products) < 2:
        raise ValueError("At least two products are required.")
    unseen_products = set(test["treatment"].astype(str).unique()).difference(products)
    if unseen_products:
        raise ValueError(f"Held-out year contains unseen products: {sorted(unseen_products)}")

    train_x = _base_design(train, products)
    test_x = _base_design(test, products)

    if model == "coarse_weather":
        numeric = (
            "preseason_wetness_z",
            "application_wetness_z",
            "application_avg_temp_c_z",
        )
        for column in numeric:
            # These values are already referenced to a fixed 2009-2016 climatology, so no
            # outcome-driven fold scaling is needed.
            train_x[column] = train[column].to_numpy(dtype=float)
            test_x[column] = test[column].to_numpy(dtype=float)
    elif model in ("sentinel", "sentinel_gxe"):
        mean = float(train["sentinel_sqrt_audpc"].mean())
        std = float(train["sentinel_sqrt_audpc"].std(ddof=0))
        if not np.isfinite(std) or std <= 0:
            raise ValueError("Sentinel state has no variation in the training years.")
        train_x["sentinel_z"] = (train["sentinel_sqrt_audpc"] - mean) / std
        test_x["sentinel_z"] = (test["sentinel_sqrt_audpc"] - mean) / std
        if model == "sentinel_gxe":
            train_x["late:sentinel_z"] = train_x["late"] * train_x["sentinel_z"]
            test_x["late:sentinel_z"] = test_x["late"] * test_x["sentinel_z"]
            for product in products[1:]:
                base_column = f"product[{product}]"
                interaction = f"{base_column}:sentinel_z"
                train_x[interaction] = train_x[base_column] * train_x["sentinel_z"]
                test_x[interaction] = test_x[base_column] * test_x["sentinel_z"]
    elif model != "baseline":
        raise ValueError(f"Unsupported environment model: {model}")

    if tuple(train_x.columns) != tuple(test_x.columns):
        raise RuntimeError("Train/test environment design matrices are misaligned.")
    return (
        train_x.to_numpy(dtype=np.float64),
        test_x.to_numpy(dtype=np.float64),
        tuple(str(value) for value in train_x.columns),
    )


def leave_one_year_out_environment_models(
    frame: pd.DataFrame,
    *,
    alpha: float = 10.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare environment representations under genuine leave-one-year-out prediction.

    ``alpha`` is fixed for the primary release analysis. A separate sensitivity table should be
    used to show whether conclusions depend materially on that regularisation choice.
    """
    if not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("alpha must be finite and positive.")
    _require_columns(
        frame,
        (
            "year",
            "block",
            "treatment",
            "timing",
            "sqrt_audpc",
            "preseason_wetness_z",
            "application_wetness_z",
            "application_avg_temp_c_z",
            "sentinel_sqrt_audpc",
        ),
    )
    years = tuple(sorted(int(value) for value in frame["year"].unique()))
    if years != _PRIMARY_YEARS:
        raise ValueError(f"Expected primary years {_PRIMARY_YEARS}, got {years}.")

    models: tuple[ModelName, ...] = (
        "baseline",
        "coarse_weather",
        "sentinel",
        "sentinel_gxe",
    )
    metric_records: list[EnvironmentModelMetric] = []
    prediction_frames: list[pd.DataFrame] = []

    for model in models:
        all_actual: list[float] = []
        all_predicted: list[float] = []
        for held_out_year in years:
            train = frame.loc[frame["year"] != held_out_year].copy()
            test = frame.loc[frame["year"] == held_out_year].copy().reset_index(drop=True)
            x_train, x_test, columns = _design_for_model(train, test, model=model)
            y_train = train["sqrt_audpc"].to_numpy(dtype=float)
            y_test = test["sqrt_audpc"].to_numpy(dtype=float)
            estimator = Ridge(alpha=alpha, fit_intercept=False)
            estimator.fit(x_train, y_train)
            predicted = estimator.predict(x_test)
            metric_records.append(
                EnvironmentModelMetric(
                    model=model,
                    held_out_year=held_out_year,
                    n_test=len(test),
                    rmse=float(np.sqrt(mean_squared_error(y_test, predicted))),
                    mae=float(mean_absolute_error(y_test, predicted)),
                    r2=float(r2_score(y_test, predicted)),
                )
            )
            fold_predictions = test.loc[
                :, ["year", "block", "treatment", "timing", "sqrt_audpc"]
            ].copy()
            fold_predictions["model"] = model
            fold_predictions["prediction"] = predicted
            fold_predictions["alpha"] = alpha
            fold_predictions["n_parameters"] = len(columns)
            prediction_frames.append(fold_predictions)
            all_actual.extend(y_test.tolist())
            all_predicted.extend(predicted.tolist())

        y_all = np.asarray(all_actual, dtype=float)
        p_all = np.asarray(all_predicted, dtype=float)
        metric_records.append(
            EnvironmentModelMetric(
                model=model,
                held_out_year="ALL",
                n_test=len(y_all),
                rmse=float(np.sqrt(mean_squared_error(y_all, p_all))),
                mae=float(mean_absolute_error(y_all, p_all)),
                r2=float(r2_score(y_all, p_all)),
            )
        )

    metrics = pd.DataFrame([record.__dict__ for record in metric_records])
    predictions = pd.concat(prediction_frames, ignore_index=True)
    return metrics, predictions


def regularisation_sensitivity(
    frame: pd.DataFrame,
    *,
    alphas: tuple[float, ...] = (1.0, 5.0, 10.0, 20.0),
) -> pd.DataFrame:
    """Report aggregate LOYO RMSE across a small, fixed ridge-penalty grid."""
    records: list[dict[str, object]] = []
    for alpha in alphas:
        metrics, _ = leave_one_year_out_environment_models(frame, alpha=alpha)
        aggregate = metrics.loc[metrics["held_out_year"] == "ALL"]
        for row in aggregate.itertuples(index=False):
            records.append(
                {
                    "alpha": alpha,
                    "model": row.model,
                    "rmse": float(row.rmse),
                    "mae": float(row.mae),
                    "r2": float(row.r2),
                }
            )
    return pd.DataFrame.from_records(records)


def gxe_promotion_gate(metrics: pd.DataFrame) -> PromotionGate:
    """Require genuine unseen-year gains before promoting product-by-environment interactions."""
    _require_columns(metrics, ("model", "held_out_year", "rmse"))
    reference = metrics.loc[metrics["model"] == "sentinel"].copy()
    candidate = metrics.loc[metrics["model"] == "sentinel_gxe"].copy()
    if reference.empty or candidate.empty:
        raise ValueError("Both sentinel and sentinel_gxe metrics are required.")

    ref_all = float(reference.loc[reference["held_out_year"] == "ALL", "rmse"].iloc[0])
    cand_all = float(candidate.loc[candidate["held_out_year"] == "ALL", "rmse"].iloc[0])
    ref_folds = reference.loc[reference["held_out_year"] != "ALL", ["held_out_year", "rmse"]]
    cand_folds = candidate.loc[candidate["held_out_year"] != "ALL", ["held_out_year", "rmse"]]
    paired = ref_folds.merge(
        cand_folds,
        on="held_out_year",
        suffixes=("_reference", "_candidate"),
        validate="one_to_one",
    )
    wins = int((paired["rmse_candidate"] < paired["rmse_reference"]).sum())
    n_folds = len(paired)
    promoted = bool(cand_all < ref_all and wins >= 3)
    return PromotionGate(
        candidate_model="sentinel_gxe",
        reference_model="sentinel",
        aggregate_rmse_candidate=cand_all,
        aggregate_rmse_reference=ref_all,
        fold_wins=wins,
        n_folds=n_folds,
        promoted=promoted,
    )
