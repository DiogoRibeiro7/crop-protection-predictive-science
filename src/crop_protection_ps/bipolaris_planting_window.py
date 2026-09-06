"""Interpretable planting-window candidate for Bipolaris prospective transport.

Environment labels encode a field location and planting window such as ``Cedo`` or
``Preferencial``. The candidate uses only the planting-window component, which is known before
held-out disease outcomes are observed. Predictions combine same-hybrid history and the training
planting-window mean through an additive two-way decomposition.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def planting_window(environment: str) -> str:
    """Extract the final underscore-delimited planting-window label."""
    value = str(environment).strip()
    if "_" not in value:
        raise ValueError(f"Environment does not encode a planting window: {environment!r}.")
    window = value.rsplit("_", maxsplit=1)[1].strip()
    if not window:
        raise ValueError(f"Environment has an empty planting-window label: {environment!r}.")
    return window


def _rmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    if observed.shape != predicted.shape or observed.size == 0:
        raise ValueError("Observed and predicted arrays must be non-empty and aligned.")
    return float(np.sqrt(np.mean(np.square(observed - predicted))))


def _rank_mae(observed: pd.Series, predicted: pd.Series) -> float:
    observed_rank = observed.rank(method="average").to_numpy(dtype=float)
    predicted_rank = predicted.rank(method="average").to_numpy(dtype=float)
    return float(np.mean(np.abs(observed_rank - predicted_rank)))


def loeo_planting_window_burden(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Predict held-out AUDPC using hybrid history plus a planting-window correction."""
    required = {"environment", "hybrid", "audpc_pct_days"}
    missing = required.difference(metrics.columns)
    if missing:
        raise ValueError(f"Missing Bipolaris metric columns: {sorted(missing)}.")
    if metrics.empty:
        raise ValueError("Bipolaris curve metrics must not be empty.")

    working = metrics.copy()
    working["planting_window"] = working["environment"].map(planting_window)
    environments = sorted(str(value) for value in working["environment"].unique())
    if len(environments) < 2:
        raise ValueError("At least two environments are required.")

    prediction_rows: list[dict[str, str | int | float]] = []
    for held_out_environment in environments:
        train = working.loc[working["environment"] != held_out_environment].copy()
        test = working.loc[working["environment"] == held_out_environment].copy()
        held_window = planting_window(held_out_environment)
        global_mean = float(train["audpc_pct_days"].mean())
        hybrid_mean = train.groupby("hybrid", observed=True)["audpc_pct_days"].mean()
        window_mean = train.groupby("planting_window", observed=True)["audpc_pct_days"].mean()
        hybrid_counts = train.groupby("hybrid", observed=True)["environment"].nunique()

        if held_window not in window_mean.index:
            continue
        for row in test.itertuples(index=False):
            hybrid = str(row.hybrid)
            if hybrid not in hybrid_mean.index:
                continue
            prediction = (
                float(hybrid_mean.loc[hybrid])
                + float(window_mean.loc[held_window])
                - global_mean
            )
            prediction_rows.append(
                {
                    "held_out_environment": held_out_environment,
                    "hybrid": hybrid,
                    "planting_window": held_window,
                    "observed_audpc_pct_days": float(row.audpc_pct_days),
                    "candidate_prediction": prediction,
                    "training_environments_for_hybrid": int(hybrid_counts.loc[hybrid]),
                }
            )

    predictions = pd.DataFrame.from_records(prediction_rows)
    if predictions.empty:
        raise ValueError("No planting-window burden predictions were produced.")
    predictions = predictions.sort_values(["held_out_environment", "hybrid"]).reset_index(drop=True)

    fold_rows: list[dict[str, str | int | float]] = []
    for held_out_environment, fold in predictions.groupby(
        "held_out_environment", sort=True, observed=True
    ):
        observed = fold["observed_audpc_pct_days"].to_numpy(dtype=float)
        predicted = fold["candidate_prediction"].to_numpy(dtype=float)
        fold_rows.append(
            {
                "held_out_environment": str(held_out_environment),
                "n_hybrids": len(fold),
                "candidate_rmse": _rmse(observed, predicted),
                "candidate_rank_mae": _rank_mae(
                    fold["observed_audpc_pct_days"], fold["candidate_prediction"]
                ),
            }
        )
    folds = pd.DataFrame.from_records(fold_rows)
    return predictions, folds.sort_values("held_out_environment").reset_index(drop=True)


def loeo_planting_window_shape(profiles: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Predict held-out normalized trajectory shape with additive hybrid/window effects."""
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

    working = profiles.copy()
    working["planting_window"] = working["environment"].map(planting_window)
    environments = sorted(str(value) for value in working["environment"].unique())
    if len(environments) < 2:
        raise ValueError("At least two environments are required.")

    rows: list[dict[str, str | int | float]] = []
    for held_out_environment in environments:
        train = working.loc[working["environment"] != held_out_environment].copy()
        test = working.loc[working["environment"] == held_out_environment].copy()
        held_window = planting_window(held_out_environment)

        global_shape = train.groupby("days_after_emergence", observed=True)["relative_shape"].mean()
        hybrid_shape = train.groupby(
            ["hybrid", "days_after_emergence"], observed=True
        )["relative_shape"].mean()
        window_shape = train.groupby(
            ["planting_window", "days_after_emergence"], observed=True
        )["relative_shape"].mean()
        hybrid_counts = train.groupby("hybrid", observed=True)["environment"].nunique()

        if held_window not in window_shape.index.get_level_values(0):
            continue
        held_window_shape = window_shape.loc[held_window]
        for hybrid, held_curve in test.groupby("hybrid", sort=True, observed=True):
            hybrid_name = str(hybrid)
            if hybrid_name not in hybrid_counts.index:
                continue
            ordered = held_curve.sort_values("days_after_emergence")
            grid = ordered["days_after_emergence"].to_numpy(dtype=float)
            observed = ordered["relative_shape"].to_numpy(dtype=float)
            try:
                hybrid_component = hybrid_shape.loc[hybrid_name].reindex(grid)
            except KeyError:
                continue
            global_component = global_shape.reindex(grid)
            window_component = held_window_shape.reindex(grid)
            if (
                hybrid_component.isna().any()
                or global_component.isna().any()
                or window_component.isna().any()
            ):
                raise ValueError("Candidate and held-out profiles must share the same DAE grid.")
            predicted = (
                hybrid_component.to_numpy(dtype=float)
                + window_component.to_numpy(dtype=float)
                - global_component.to_numpy(dtype=float)
            )
            rows.append(
                {
                    "held_out_environment": held_out_environment,
                    "hybrid": hybrid_name,
                    "planting_window": held_window,
                    "candidate_shape_rmse": _rmse(observed, predicted),
                    "training_environments_for_hybrid": int(hybrid_counts.loc[hybrid_name]),
                }
            )

    predictions = pd.DataFrame.from_records(rows)
    if predictions.empty:
        raise ValueError("No planting-window shape predictions were produced.")
    predictions = predictions.sort_values(["held_out_environment", "hybrid"]).reset_index(drop=True)
    folds = (
        predictions.groupby("held_out_environment", sort=True, observed=True)
        .agg(
            n_hybrids=("hybrid", "size"),
            candidate_shape_rmse=("candidate_shape_rmse", "mean"),
        )
        .reset_index()
    )
    return predictions, folds
