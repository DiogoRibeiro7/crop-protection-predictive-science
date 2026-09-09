from pathlib import Path

import pytest
from pydantic import ValidationError

from crop_protection_ps.config import TrialSimulationConfig, load_config


def test_default_config_is_valid() -> None:
    config = TrialSimulationConfig()
    assert config.n_sites >= 3
    assert config.doses_g_ai_ha[0] == 0.0


def test_doses_must_start_with_control() -> None:
    with pytest.raises(ValidationError):
        TrialSimulationConfig(doses_g_ai_ha=(1.0, 2.0, 3.0))


def test_yaml_config_loads() -> None:
    path = Path(__file__).parents[1] / "configs" / "demo.yaml"
    config = load_config(path)
    assert config.seed == 20260826


def test_demo_yaml_matches_packaged_defaults() -> None:
    path = Path(__file__).parents[1] / "configs" / "demo.yaml"
    assert load_config(path) == TrialSimulationConfig()
