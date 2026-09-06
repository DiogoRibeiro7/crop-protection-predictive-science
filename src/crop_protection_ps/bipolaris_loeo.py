"""Prospective leave-one-environment-out validation for the Bipolaris field case.

The benchmarks in this module are intentionally simple. They ask whether hybrid-specific history
from other environments adds predictive information beyond an environment-agnostic training mean.
No held-out environment outcomes are used to construct predictions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _rmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    """Return root-mean-square error for equally sized vectors."""
    if observed.shape != predicted.shape:
        raise ValueError("Observed and predicted arrays must have the same shape.")
    if observed.size == 0:
        raise ValueError("At least one observation is required.")
    return float(np.sqrt(np.mean(np.square(observed - predicted))))


def _mae(observed: np.ndarray, predicted: np.ndarray) -> float:
    """Return mean absolute error for equally sized vectors."""
    if observed.shape != predicted.shape:
        raise ValueError("Observed and predicted arrays must have the same shape.")
    if observed.size == 0:
        raise ValueError("At least one observation is required.")
    return float(np.mean(np.abs(observed - predicted)))


def _spearman_or_none(observed: pd.Series, predicted: pd.Series) -> float | None:
    """Return Spearman correlation when a fold contains enough non-constant information."""
    if len(observed) < 2 or observed.nunique() < 2 or predicted.nunique() < 2:
        return None
    value = observed.corr(predicted, method="spearman")
    if pd.isna(value):
        return None
    return float(value)


def leave_one_environment_out_burden(metrics: pd.DataFrame) -> pd.DataFrame:
    """Predict held-out-environment AUDPC from training environments only.

    Two predictions are produced for every held-out hybrid with historical observations:

    ``global_training_mean``
        Mean AUDPC across every training environment and hybrid.
    ``hybrid_history_mean``
        Mean AUDPC for that hybrid across the remaining environments.

    The second benchmark can beat the first only when hybrid identity transports across
    environments strongly enough to add information beyond the global training burden.
    """
    required = {"environment", "hybrid", "audpc_pct_days"}
    missing = required.difference(metrics.columns)
    if missing:
        raise ValueError(f"Missing Bipolaris metric columns: {sorted(missing)}.")
    if metrics.empty:
        raise ValueError("Bipolaris curve metrics must not be empty.")

    records: list[dict[str, str | int | float]] = []
    environments = sorted(str(value) for value in metrics["environment"].unique())
    if len(environments) < 2:
        raise ValueError("At least two environments are required for leave-one-environment-out.")

    for held_out_environment in environments:
        train = metrics.loc[metrics["environment"] != held_out_environment].copy()
        test = metrics.loc[metrics["environment"] == held_out_environment].copy()
        if train.empty or test.empty:
            continue

        global_training_mean = float(train["audpc_pct_days"].mean())
        hybrid_history = train.groupby("hybrid", observed=True)["audpc_pct_days"].agg(
            ["mean", "count"]
        )

        for row in test.itertuples(index=False):
            hybrid = str(row.hybrid)
            if hybrid not in hybrid_history.index:
                continue
            history = hybrid_history.loc[hybrid]
            records.append(
                {
                    "held_out_environment": held_out_environment,
                    "hybrid": hybrid,
                    "observed_audpc_pct_days": float(row.audpc_pct_days),
                    "global_training_mean_prediction": global_training_mean,
                    "hybrid_history_prediction": float(history["mean"]),
                    "training_environments_for_hybrid": int(history["count"]),
                }
            )

    predictions = pd.DataFrame.from_records(records)
    if predictions.empty:
        raise ValueError("No held-out hybrids have training-environment history.")
    return predictions.sort_values(["held_out_environment", "hybrid"]).reset_index(drop=True)


def burden_fold_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Score global-mean and hybrid-history AUDPC predictions within each held-out environment."""
    required = {
        "held_out_environment",
        "hybrid",
        "observed_audpc_pct_days",
        "global_training_mean_prediction",
        "hybrid_history_prediction",
    }
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Missing burden-prediction columns: {sorted(missing)}.")

    records: list[dict[str, str | int | float | None]] = []
    grouped = predictions.groupby("held_out_environment", sort=True, observed=True)
    for held_out_environment, fold in grouped:
        observed = fold["observed_audpc_pct_days"].to_numpy(dtype=float)
        global_prediction = fold["global_training_mean_prediction"].to_numpy(dtype=float)
        hybrid_prediction = fold["hybrid_history_prediction"].to_numpy(dtype=float)

        observed_rank = fold["observed_audpc_pct_days"].rank(method="average")
        predicted_rank = fold["hybrid_history_prediction"].rank(method="average")
        records.append(
            {
                "held_out_environment": str(held_out_environment),
                "n_hybrids": len(fold),
                "global_training_mean_rmse": _rmse(observed, global_prediction),
                "hybrid_history_rmse": _rmse(observed, hybrid_prediction),
                "global_training_mean_mae": _mae(observed, global_prediction),
                "hybrid_history_mae": _mae(observed, hybrid_prediction),
                "hybrid_history_spearman": _spearman_or_none(
                    fold["observed_audpc_pct_days"], fold["hybrid_history_prediction"]
                ),
                "hybrid_history_rank_mae": float(
                    np.mean(np.abs(observed_rank.to_numpy() - predicted_rank.to_numpy()))
                ),
            }
        )

    folds = pd.DataFrame.from_records(records)
    if folds.empty:
        raise ValueError("No leave-one-environment-out burden folds were scored.")
    return folds.sort_values("held_out_environment").reset_index(drop=True)


def leave_one_environment_out_shape(profiles: pd.DataFrame) -> pd.DataFrame:
    """Predict a held-out normalized disease trajectory from other environments.

    The global baseline is the mean normalized trajectory across all training curves. The
    hybrid-history prediction is the pointwise mean normalized trajectory for the same hybrid in
    the remaining environments. Both are constructed without held-out-environment outcomes.
    """
    required = {
        "environment",
        "hybrid",
        "days_after_emergence",
        "relative_shape",
    }
    missing = required.difference(profiles.columns)
    if missing:
        raise ValueError(f"Missing functional-profile columns: {sorted(missing)}.")
    if profiles.empty:
        raise ValueError("Functional profiles must not be empty.")

    environments = sorted(str(value) for value in profiles["environment"].unique())
    if len(environments) < 2:
        raise ValueError("At least two environments are required for leave-one-environment-out.")

    records: list[dict[str, str | int | float]] = []
    for held_out_environment in environments:
        train = profiles.loc[profiles["environment"] != held_out_environment].copy()
        test = profiles.loc[profiles["environment"] == held_out_environment].copy()
        if train.empty or test.empty:
            continue

        global_shape = train.groupby("days_after_emergence", observed=True)["relative_shape"].mean()
        hybrid_shapes = train.groupby(
            ["hybrid", "days_after_emergence"], observed=True
        )["relative_shape"].mean()
        hybrid_counts = train.groupby("hybrid", observed=True)["environment"].nunique()

        for hybrid, held_curve in test.groupby("hybrid", sort=True, observed=True):
            hybrid_name = str(hybrid)
            if hybrid_name not in hybrid_counts.index:
                continue

            ordered = held_curve.sort_values("days_after_emergence")
            grid = ordered["days_after_emergence"].to_numpy(dtype=float)
            observed = ordered["relative_shape"].to_numpy(dtype=float)

            global_prediction = global_shape.reindex(grid)
            try:
                hybrid_prediction = hybrid_shapes.loc[hybrid_name].reindex(grid)
            except KeyError:
                continue
            if global_prediction.isna().any() or hybrid_prediction.isna().any():
                raise ValueError(
                    "Training and held-out functional profiles must share one DAE grid."
                )

            records.append(
                {
                    "held_out_environment": held_out_environment,
                    "hybrid": hybrid_name,
                    "global_training_shape_rmse": _rmse(
                        observed, global_prediction.to_numpy(dtype=float)
                    ),
                    "hybrid_history_shape_rmse": _rmse(
                        observed, hybrid_prediction.to_numpy(dtype=float)
                    ),
                    "training_environments_for_hybrid": int(hybrid_counts.loc[hybrid_name]),
                }
            )

    predictions = pd.DataFrame.from_records(records)
    if predictions.empty:
        raise ValueError("No held-out functional profiles have training-environment history.")
    return predictions.sort_values(["held_out_environment", "hybrid"]).reset_index(drop=True)


def shape_fold_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    """Summarize normalized-trajectory error within each held-out environment."""
    required = {
        "held_out_environment",
        "global_training_shape_rmse",
        "hybrid_history_shape_rmse",
    }
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"Missing shape-prediction columns: {sorted(missing)}.")

    folds = (
        predictions.groupby("held_out_environment", sort=True, observed=True)
        .agg(
            n_hybrids=("hybrid", "size"),
            global_training_shape_rmse=("global_training_shape_rmse", "mean"),
            hybrid_history_shape_rmse=("hybrid_history_shape_rmse", "mean"),
        )
        .reset_index()
    )
    if folds.empty:
        raise ValueError("No leave-one-environment-out shape folds were scored.")
    return folds


def loeo_summary(
    burden_folds: pd.DataFrame,
    shape_folds: pd.DataFrame,
) -> dict[str, int | float | None]:
    """Summarize prospective transport without introducing a promotion gate."""
    burden_required = {
        "n_hybrids",
        "global_training_mean_rmse",
        "hybrid_history_rmse",
        "hybrid_history_spearman",
    }
    shape_required = {
        "n_hybrids",
        "global_training_shape_rmse",
        "hybrid_history_shape_rmse",
    }
    burden_missing = burden_required.difference(burden_folds.columns)
    shape_missing = shape_required.difference(shape_folds.columns)
    if burden_missing:
        raise ValueError(f"Missing burden-fold columns: {sorted(burden_missing)}.")
    if shape_missing:
        raise ValueError(f"Missing shape-fold columns: {sorted(shape_missing)}.")

    burden_global = float(burden_folds["global_training_mean_rmse"].mean())
    burden_hybrid = float(burden_folds["hybrid_history_rmse"].mean())
    shape_global = float(shape_folds["global_training_shape_rmse"].mean())
    shape_hybrid = float(shape_folds["hybrid_history_shape_rmse"].mean())

    valid_spearman = burden_folds["hybrid_history_spearman"].dropna()
    mean_spearman = float(valid_spearman.mean()) if not valid_spearman.empty else None

    burden_change = (
        100.0 * (burden_hybrid - burden_global) / burden_global
        if burden_global > 0.0
        else None
    )
    shape_change = (
        100.0 * (shape_hybrid - shape_global) / shape_global if shape_global > 0.0 else None
    )

    return {
        "burden_folds": len(burden_folds),
        "burden_evaluated_hybrid_rows": int(burden_folds["n_hybrids"].sum()),
        "mean_fold_global_training_audpc_rmse": burden_global,
        "mean_fold_hybrid_history_audpc_rmse": burden_hybrid,
        "hybrid_history_audpc_rmse_change_pct": burden_change,
        "burden_fold_wins_for_hybrid_history": int(
            (
                burden_folds["hybrid_history_rmse"]
                < burden_folds["global_training_mean_rmse"]
            ).sum()
        ),
        "mean_fold_hybrid_history_spearman": mean_spearman,
        "shape_folds": len(shape_folds),
        "shape_evaluated_hybrid_rows": int(shape_folds["n_hybrids"].sum()),
        "mean_fold_global_training_shape_rmse": shape_global,
        "mean_fold_hybrid_history_shape_rmse": shape_hybrid,
        "hybrid_history_shape_rmse_change_pct": shape_change,
        "shape_fold_wins_for_hybrid_history": int(
            (
                shape_folds["hybrid_history_shape_rmse"]
                < shape_folds["global_training_shape_rmse"]
            ).sum()
        ),
    }
