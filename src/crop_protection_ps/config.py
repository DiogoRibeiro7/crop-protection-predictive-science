"""Validated configuration objects."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TrialSimulationConfig(BaseModel):
    """Configuration for the synthetic multi-environment field-trial generator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int = Field(default=20260826, ge=0)
    n_sites: int = Field(default=8, ge=3, le=50)
    years: tuple[int, ...] = (2023, 2024, 2025)
    blocks_per_site_year: int = Field(default=4, ge=2, le=20)
    formulations: tuple[str, ...] = ("A", "B")
    doses_g_ai_ha: tuple[float, ...] = (0.0, 2.5, 5.0, 10.0, 20.0, 40.0)
    n_insects_per_plot: int = Field(default=60, ge=10, le=1000)

    @field_validator("years")
    @classmethod
    def validate_years(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        """Require at least two unique, ordered years."""
        if len(values) < 2 or len(set(values)) != len(values):
            raise ValueError("years must contain at least two unique values")
        if tuple(sorted(values)) != values:
            raise ValueError("years must be sorted")
        return values

    @field_validator("formulations")
    @classmethod
    def validate_formulations(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        """Require at least two unique non-empty formulations."""
        cleaned = tuple(value.strip() for value in values)
        if len(cleaned) < 2 or len(set(cleaned)) != len(cleaned) or any(not x for x in cleaned):
            raise ValueError("formulations must contain at least two unique non-empty labels")
        return cleaned

    @field_validator("doses_g_ai_ha")
    @classmethod
    def validate_doses(cls, values: tuple[float, ...]) -> tuple[float, ...]:
        """Require a control dose and strictly increasing non-negative doses."""
        if not values or values[0] != 0.0:
            raise ValueError("doses_g_ai_ha must start with a zero-dose control")
        if any(value < 0.0 for value in values):
            raise ValueError("doses must be non-negative")
        if tuple(sorted(set(values))) != values:
            raise ValueError("doses must be unique and strictly increasing")
        return values


def load_config(path: str | Path) -> TrialSimulationConfig:
    """Load and validate YAML configuration from ``path``."""
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("configuration must be a YAML mapping")
    return TrialSimulationConfig.model_validate(payload)
