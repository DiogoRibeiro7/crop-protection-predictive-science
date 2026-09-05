import numpy as np
import pandas as pd
import pytest

import crop_protection_ps.mixed_effects as mixed_effects


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "site": ["A", "A", "B", "B"],
            "formulation": ["X", "Y", "X", "Y"],
            "dose_g_ai_ha": [0.0, 10.0, 20.0, 40.0],
            "temperature_c": [20.0, 21.0, 22.0, 23.0],
            "relative_humidity_pct": [60.0, 62.0, 64.0, 66.0],
            "rainfall_mm_7d": [0.0, 1.0, 2.0, 3.0],
            "spray_coverage_pct": [70.0, 75.0, 80.0, 85.0],
            "mortality_count": [0, 5, 10, 20],
            "n_insects": [20, 20, 20, 20],
        }
    )


def test_prepare_mixed_effects_frame_requires_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        mixed_effects.prepare_mixed_effects_frame(pd.DataFrame({"site": ["A"]}))


def test_prepare_mixed_effects_frame_keeps_boundary_counts_finite() -> None:
    prepared = mixed_effects.prepare_mixed_effects_frame(_frame())
    assert np.all(np.isfinite(prepared["logit_mortality"]))
    assert prepared.loc[0, "log_dose"] == 0.0
    assert prepared.loc[3, "log_dose"] > prepared.loc[2, "log_dose"]


def test_fit_site_random_intercept_uses_powell_reml(monkeypatch) -> None:
    captured = {}
    sentinel = object()

    class _FakeModel:
        def fit(self, **kwargs):
            captured["fit"] = kwargs
            return sentinel

    def fake_mixedlm(formula, data, groups):
        captured["formula"] = formula
        captured["groups"] = groups.tolist()
        captured["columns"] = set(data.columns)
        return _FakeModel()

    monkeypatch.setattr(mixed_effects.smf, "mixedlm", fake_mixedlm)
    result = mixed_effects.fit_site_random_intercept_model(_frame())

    assert result is sentinel
    assert "logit_mortality ~ log_dose" in captured["formula"]
    assert captured["groups"] == ["A", "A", "B", "B"]
    assert {"log_dose", "logit_mortality"}.issubset(captured["columns"])
    assert captured["fit"] == {
        "reml": True,
        "method": "powell",
        "maxiter": 2000,
        "disp": False,
    }
