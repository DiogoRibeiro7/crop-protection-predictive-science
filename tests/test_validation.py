import numpy as np
import pandas as pd

import crop_protection_ps.validation as validation


def _frame() -> pd.DataFrame:
    rows = []
    for i in range(15):
        rows.append(
            {
                "site": f"S{i % 3}",
                "year": 2023 + (i % 2),
                "formulation": "A" if i % 2 == 0 else "B",
                "dose_g_ai_ha": float(i + 1),
                "temperature_c": 20.0 + i / 10,
                "relative_humidity_pct": 60.0 + i,
                "rainfall_mm_7d": float(i % 4),
                "spray_coverage_pct": 80.0 + i / 2,
                "mortality_rate": 0.1 + 0.8 * i / 14,
            }
        )
    return pd.DataFrame(rows)


class _MeanPipeline:
    def fit(self, x: pd.DataFrame, y: np.ndarray) -> "_MeanPipeline":
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        return np.full(len(x), self.mean_, dtype=float)


def test_random_kfold_reports_five_folds(monkeypatch) -> None:
    monkeypatch.setattr(validation, "_make_pipeline", lambda seed: _MeanPipeline())
    summary = validation.random_kfold_validation(_frame(), seed=7)
    assert summary.strategy == "random_5fold"
    assert summary.n_folds == 5
    assert summary.rmse >= 0.0
    assert summary.mae >= 0.0
    assert np.isfinite(summary.r2)


def test_leave_one_site_out_uses_each_site_once(monkeypatch) -> None:
    monkeypatch.setattr(validation, "_make_pipeline", lambda seed: _MeanPipeline())
    summary = validation.leave_one_site_out_validation(_frame(), seed=7)
    assert summary.strategy == "leave_one_site_out"
    assert summary.n_folds == 3
    assert summary.rmse >= 0.0


def test_validation_table_contains_both_strategies(monkeypatch) -> None:
    monkeypatch.setattr(validation, "_make_pipeline", lambda seed: _MeanPipeline())
    table = validation.validation_table(_frame(), seed=7)
    assert table["strategy"].tolist() == ["random_5fold", "leave_one_site_out"]
    assert table["n_folds"].tolist() == [5, 3]
