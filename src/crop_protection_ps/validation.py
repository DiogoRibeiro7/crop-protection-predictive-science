"""Validation strategies that distinguish interpolation from domain extrapolation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class ValidationSummary:
    """Cross-validation summary for one strategy."""

    strategy: str
    n_folds: int
    rmse: float
    mae: float
    r2: float


FEATURE_COLUMNS: tuple[str, ...] = (
    "site",
    "year",
    "formulation",
    "dose_g_ai_ha",
    "temperature_c",
    "relative_humidity_pct",
    "rainfall_mm_7d",
    "spray_coverage_pct",
)


def _make_pipeline(seed: int) -> Pipeline:
    """Construct a reproducible mixed-type predictive pipeline."""
    categorical = ["site", "year", "formulation"]
    numeric = [column for column in FEATURE_COLUMNS if column not in categorical]

    preprocessing = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical),
            ("numeric", StandardScaler(), numeric),
        ]
    )
    model = RandomForestRegressor(
        n_estimators=350,
        min_samples_leaf=4,
        random_state=seed,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocessing), ("model", model)])


def _summarise(
    strategy: str,
    actual: list[float],
    predicted: list[float],
    n_folds: int,
) -> ValidationSummary:
    y_true = np.asarray(actual, dtype=float)
    y_pred = np.asarray(predicted, dtype=float)
    return ValidationSummary(
        strategy=strategy,
        n_folds=n_folds,
        rmse=float(np.sqrt(mean_squared_error(y_true, y_pred))),
        mae=float(mean_absolute_error(y_true, y_pred)),
        r2=float(r2_score(y_true, y_pred)),
    )


def random_kfold_validation(frame: pd.DataFrame, *, seed: int = 20260826) -> ValidationSummary:
    """Estimate interpolation performance under conventional random K-fold CV."""
    x = frame.loc[:, FEATURE_COLUMNS]
    y = frame["mortality_rate"].to_numpy(dtype=float)
    splitter = KFold(n_splits=5, shuffle=True, random_state=seed)

    actual: list[float] = []
    predicted: list[float] = []
    for train_idx, test_idx in splitter.split(x):
        pipeline = _make_pipeline(seed)
        pipeline.fit(x.iloc[train_idx], y[train_idx])
        fold_prediction = np.clip(pipeline.predict(x.iloc[test_idx]), 0.0, 1.0)
        actual.extend(y[test_idx].tolist())
        predicted.extend(fold_prediction.tolist())

    return _summarise("random_5fold", actual, predicted, splitter.get_n_splits())


def leave_one_site_out_validation(
    frame: pd.DataFrame,
    *,
    seed: int = 20260826,
) -> ValidationSummary:
    """Estimate performance when predicting an entirely unseen site."""
    x = frame.loc[:, FEATURE_COLUMNS]
    y = frame["mortality_rate"].to_numpy(dtype=float)
    groups = frame["site"].to_numpy(dtype=str)
    splitter = LeaveOneGroupOut()

    actual: list[float] = []
    predicted: list[float] = []
    n_folds = 0
    for train_idx, test_idx in splitter.split(x, y, groups):
        pipeline = _make_pipeline(seed)
        pipeline.fit(x.iloc[train_idx], y[train_idx])
        fold_prediction = np.clip(pipeline.predict(x.iloc[test_idx]), 0.0, 1.0)
        actual.extend(y[test_idx].tolist())
        predicted.extend(fold_prediction.tolist())
        n_folds += 1

    return _summarise("leave_one_site_out", actual, predicted, n_folds)


def validation_table(frame: pd.DataFrame, *, seed: int = 20260826) -> pd.DataFrame:
    """Compare conventional and scientifically aligned validation strategies."""
    summaries = [
        random_kfold_validation(frame, seed=seed),
        leave_one_site_out_validation(frame, seed=seed),
    ]
    return pd.DataFrame([summary.__dict__ for summary in summaries])
