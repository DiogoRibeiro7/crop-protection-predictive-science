from __future__ import annotations

import pandas as pd
import pytest

from crop_protection_ps.bipolaris_loeo import (
    burden_fold_metrics,
    leave_one_environment_out_burden,
    leave_one_environment_out_shape,
    loeo_summary,
    shape_fold_metrics,
)


def _metrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"environment": "E1", "hybrid": "H1", "audpc_pct_days": 10.0},
            {"environment": "E1", "hybrid": "H2", "audpc_pct_days": 30.0},
            {"environment": "E2", "hybrid": "H1", "audpc_pct_days": 12.0},
            {"environment": "E2", "hybrid": "H2", "audpc_pct_days": 28.0},
            {"environment": "E3", "hybrid": "H1", "audpc_pct_days": 14.0},
            {"environment": "E3", "hybrid": "H2", "audpc_pct_days": 26.0},
        ]
    )


def _profiles() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    grid = [30.0, 50.0, 70.0]
    curves = {
        ("E1", "H1"): [0.5, 1.0, 1.5],
        ("E1", "H2"): [0.7, 1.0, 1.3],
        ("E2", "H1"): [0.4, 1.0, 1.6],
        ("E2", "H2"): [0.8, 1.0, 1.2],
        ("E3", "H1"): [0.3, 1.0, 1.7],
        ("E3", "H2"): [0.9, 1.0, 1.1],
    }
    for (environment, hybrid), values in curves.items():
        for dae, value in zip(grid, values, strict=True):
            rows.append(
                {
                    "environment": environment,
                    "hybrid": hybrid,
                    "days_after_emergence": dae,
                    "relative_shape": value,
                }
            )
    return pd.DataFrame.from_records(rows)


def test_burden_predictions_use_training_environments_only() -> None:
    predictions = leave_one_environment_out_burden(_metrics())

    held_e3 = predictions.loc[predictions["held_out_environment"] == "E3"].set_index("hybrid")

    assert held_e3.loc["H1", "global_training_mean_prediction"] == pytest.approx(20.0)
    assert held_e3.loc["H2", "global_training_mean_prediction"] == pytest.approx(20.0)
    assert held_e3.loc["H1", "hybrid_history_prediction"] == pytest.approx(11.0)
    assert held_e3.loc["H2", "hybrid_history_prediction"] == pytest.approx(29.0)
    assert held_e3.loc["H1", "training_environments_for_hybrid"] == 2


def test_burden_fold_metrics_reward_transportable_hybrid_identity() -> None:
    predictions = leave_one_environment_out_burden(_metrics())
    folds = burden_fold_metrics(predictions)

    assert (folds["hybrid_history_rmse"] < folds["global_training_mean_rmse"]).all()
    assert folds["hybrid_history_spearman"].tolist() == pytest.approx([1.0, 1.0, 1.0])


def test_shape_predictions_use_same_hybrid_history_without_leakage() -> None:
    predictions = leave_one_environment_out_shape(_profiles())

    held_e3 = predictions.loc[predictions["held_out_environment"] == "E3"].set_index("hybrid")
    assert held_e3.loc["H1", "training_environments_for_hybrid"] == 2
    assert held_e3.loc["H2", "training_environments_for_hybrid"] == 2
    assert held_e3.loc["H1", "hybrid_history_shape_rmse"] < held_e3.loc[
        "H1", "global_training_shape_rmse"
    ]
    assert held_e3.loc["H2", "hybrid_history_shape_rmse"] < held_e3.loc[
        "H2", "global_training_shape_rmse"
    ]


def test_loeo_summary_reports_fold_wins_without_promotion_gate() -> None:
    burden_predictions = leave_one_environment_out_burden(_metrics())
    burden_folds = burden_fold_metrics(burden_predictions)
    shape_predictions = leave_one_environment_out_shape(_profiles())
    shape_folds = shape_fold_metrics(shape_predictions)

    summary = loeo_summary(burden_folds, shape_folds)

    assert summary["burden_folds"] == 3
    assert summary["shape_folds"] == 3
    assert summary["burden_fold_wins_for_hybrid_history"] == 3
    assert summary["shape_fold_wins_for_hybrid_history"] == 2
    assert summary["hybrid_history_audpc_rmse_change_pct"] is not None
    assert summary["hybrid_history_shape_rmse_change_pct"] is not None
