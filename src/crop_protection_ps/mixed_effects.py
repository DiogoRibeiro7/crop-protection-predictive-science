"""Hierarchical statistical baseline for blocked field-trial data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.regression.mixed_linear_model import MixedLMResultsWrapper


def prepare_mixed_effects_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Create stable transformed variables for hierarchical modelling."""
    required = {
        "site",
        "formulation",
        "dose_g_ai_ha",
        "temperature_c",
        "relative_humidity_pct",
        "rainfall_mm_7d",
        "spray_coverage_pct",
        "mortality_count",
        "n_insects",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"missing columns for mixed model: {sorted(missing)}")

    prepared = frame.copy()
    prepared["log_dose"] = np.log1p(prepared["dose_g_ai_ha"].astype(float))
    # Empirical-logit correction keeps 0/1 observations finite.
    proportion = (prepared["mortality_count"] + 0.5) / (prepared["n_insects"] + 1.0)
    prepared["logit_mortality"] = np.log(proportion / (1.0 - proportion))
    return prepared


def fit_site_random_intercept_model(frame: pd.DataFrame) -> MixedLMResultsWrapper:
    """Fit an interpretable random-intercept model with site heterogeneity."""
    prepared = prepare_mixed_effects_frame(frame)
    formula = (
        "logit_mortality ~ log_dose + I(log_dose ** 2) + C(formulation) "
        "+ temperature_c + relative_humidity_pct + rainfall_mm_7d + spray_coverage_pct"
    )
    model = smf.mixedlm(formula, data=prepared, groups=prepared["site"])
    result = model.fit(reml=True, method="powell", maxiter=2000, disp=False)
    return result
