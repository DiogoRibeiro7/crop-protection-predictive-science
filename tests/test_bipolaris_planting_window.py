from __future__ import annotations

import pandas as pd

from crop_protection_ps.bipolaris_planting_window import (
    loeo_planting_window_burden,
    loeo_planting_window_shape,
    planting_window,
)
from crop_protection_ps.bipolaris_promotion import (
    evaluate_burden_promotion,
    evaluate_shape_promotion,
)


def _burden_metrics() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    hybrid_effect = {"H1": -10.0, "H2": 10.0}
    window_effect = {"Cedo": -5.0, "Preferencial": 5.0}
    environments = [
        "SiteA_Cedo",
        "SiteB_Cedo",
        "SiteC_Preferencial",
        "SiteD_Preferencial",
    ]
    for environment in environments:
        window = planting_window(environment)
        for hybrid in ("H1", "H2"):
            rows.append(
                {
                    "environment": environment,
                    "hybrid": hybrid,
                    "audpc_pct_days": 50.0 + hybrid_effect[hybrid] + window_effect[window],
                }
            )
    return pd.DataFrame.from_records(rows)


def _shape_profiles() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    environments = [
        "SiteA_Cedo",
        "SiteB_Cedo",
        "SiteC_Preferencial",
        "SiteD_Preferencial",
    ]
    grid = [30.0, 50.0, 70.0]
    hybrid_component = {
        "H1": [-0.1, 0.0, 0.1],
        "H2": [0.1, 0.0, -0.1],
    }
    window_component = {
        "Cedo": [-0.05, 0.0, 0.05],
        "Preferencial": [0.05, 0.0, -0.05],
    }
    for environment in environments:
        window = planting_window(environment)
        for hybrid in ("H1", "H2"):
            values = [
                1.0 + h + w
                for h, w in zip(
                    hybrid_component[hybrid], window_component[window], strict=True
                )
            ]
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


def test_planting_window_extracts_suffix() -> None:
    assert planting_window("2024_Arapoti_Cedo") == "Cedo"
    assert planting_window("2024_Ponta Grossa_Preferencial") == "Preferencial"


def test_additive_burden_candidate_recovers_known_window_effect() -> None:
    predictions, folds = loeo_planting_window_burden(_burden_metrics())

    assert len(predictions) == 8
    assert (folds["candidate_rmse"] == 0.0).all()
    assert (folds["candidate_rank_mae"] == 0.0).all()


def test_additive_shape_candidate_recovers_known_window_effect() -> None:
    predictions, folds = loeo_planting_window_shape(_shape_profiles())

    assert len(predictions) == 8
    assert (folds["candidate_shape_rmse"] < 1e-12).all()


def test_candidate_is_evaluated_by_frozen_promotion_contract() -> None:
    _, candidate_burden = loeo_planting_window_burden(_burden_metrics())
    baseline_burden = candidate_burden.rename(
        columns={
            "candidate_rmse": "hybrid_history_rmse",
            "candidate_rank_mae": "hybrid_history_rank_mae",
        }
    ).copy()
    baseline_burden["hybrid_history_rmse"] = 5.0
    baseline_burden["hybrid_history_rank_mae"] = 0.5

    _, candidate_shape = loeo_planting_window_shape(_shape_profiles())
    baseline_shape = candidate_shape.rename(
        columns={"candidate_shape_rmse": "hybrid_history_shape_rmse"}
    ).copy()
    baseline_shape["hybrid_history_shape_rmse"] = 0.1

    burden_decision = evaluate_burden_promotion(baseline_burden, candidate_burden)
    shape_decision = evaluate_shape_promotion(baseline_shape, candidate_shape)

    assert burden_decision.promoted is True
    assert shape_decision.promoted is True
