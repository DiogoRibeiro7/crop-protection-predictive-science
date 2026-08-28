import numpy as np
import pandas as pd
import pytest

from crop_protection_ps.config import TrialSimulationConfig
from crop_protection_ps.dose_response import (
    bootstrap_interval,
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


def test_bootstrap_interval_validates_confidence() -> None:
    with pytest.raises(ValueError):
        bootstrap_interval(pd.Series([1.0, 2.0, 3.0]), confidence=1.0)
