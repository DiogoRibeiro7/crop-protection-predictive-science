import numpy as np

from crop_protection_ps.config import TrialSimulationConfig
from crop_protection_ps.simulate import simulate_field_trials


def test_simulation_is_deterministic() -> None:
    config = TrialSimulationConfig(n_sites=3, years=(2024, 2025), blocks_per_site_year=2)
    first = simulate_field_trials(config)
    second = simulate_field_trials(config)
    assert first.equals(second)


def test_mortality_counts_are_valid() -> None:
    frame = simulate_field_trials(TrialSimulationConfig(n_sites=3, years=(2024, 2025)))
    assert (frame["mortality_count"] >= 0).all()
    assert (frame["mortality_count"] <= frame["n_insects"]).all()
    assert np.allclose(frame["mortality_rate"], frame["mortality_count"] / frame["n_insects"])
