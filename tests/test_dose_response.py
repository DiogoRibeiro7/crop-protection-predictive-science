import numpy as np
import pandas as pd
import pytest

from crop_protection_ps.config import TrialSimulationConfig
from crop_protection_ps.dose_response import (
    bootstrap_interval,
    cluster_bootstrap_ed,
    fit_dose_response,
    four_parameter_logistic,
)
from crop_protection_ps.simulate import simulate_field_trials


def test_four_parameter_logistic_is_increasing() -> None:
    dose = np.asarray([1.0, 2.0, 4.0, 8.0, 16.0])
    response = four_parameter_logistic(dose, 0.02, 0.98, 8.0, 1.5)
    assert np.all(np.diff(response) > 0)


def test_fit_recovers_plausible_ed50() -> None:
    config = TrialSimulationConfig(n_sites=5, years=(2023, 2024, 2025))
    frame = simulate_field_trials(config)
    fit = fit_dose_response(frame, formulation="A")
    assert 3.0 < fit.ed50 < 25.0
    assert fit.ed90 > fit.ed50


def test_fit_requires_enough_positive_doses() -> None:
    frame = pd.DataFrame(
        {
            "formulation": ["A"] * 11,
            "dose_g_ai_ha": np.arange(1.0, 12.0),
            "mortality_rate": np.linspace(0.1, 0.9, 11),
        }
    )
    with pytest.raises(ValueError, match="at least 12"):
        fit_dose_response(frame)


def test_cluster_bootstrap_validates_requested_draws() -> None:
    with pytest.raises(ValueError, match="at least 100"):
        cluster_bootstrap_ed(pd.DataFrame(), n_bootstrap=99)


def test_cluster_bootstrap_requires_independent_trials() -> None:
    frame = pd.DataFrame(
        {
            "formulation": ["A"] * 12,
            "trial_id": ["trial-1"] * 12,
        }
    )
    with pytest.raises(ValueError, match="four independent trial clusters"):
        cluster_bootstrap_ed(frame, n_bootstrap=100)


def test_bootstrap_interval_returns_percentile_bounds() -> None:
    samples = pd.Series(np.arange(101, dtype=float))
    lower, upper = bootstrap_interval(samples, confidence=0.80)
    assert lower == pytest.approx(10.0)
    assert upper == pytest.approx(90.0)


def test_bootstrap_interval_validates_confidence() -> None:
    with pytest.raises(ValueError):
        bootstrap_interval(pd.Series([1.0, 2.0, 3.0]), confidence=1.0)
