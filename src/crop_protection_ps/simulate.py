"""Synthetic field-trial generator with an explicit data-generating process."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from crop_protection_ps.config import TrialSimulationConfig


def _expit(value: np.ndarray | float) -> np.ndarray | float:
    """Numerically stable logistic transform."""
    arr = np.asarray(value, dtype=float)
    positive = arr >= 0
    out = np.empty_like(arr)
    out[positive] = 1.0 / (1.0 + np.exp(-arr[positive]))
    exp_value = np.exp(arr[~positive])
    out[~positive] = exp_value / (1.0 + exp_value)
    if np.isscalar(value):
        return float(out.item())
    return out


def simulate_field_trials(config: TrialSimulationConfig) -> pd.DataFrame:
    """Simulate blocked multi-site insecticide efficacy trials.

    The generator encodes non-linear dose response, formulation potency,
    spray-coverage mediation, environmental effects, and site/year heterogeneity.
    Mortality is sampled from a binomial distribution, keeping the observation
    model explicit rather than adding Gaussian noise to percentages.
    """
    rng = np.random.default_rng(config.seed)
    site_labels = [f"S{i:02d}" for i in range(1, config.n_sites + 1)]

    site_latent = {site: float(rng.normal(0.0, 0.85)) for site in site_labels}
    year_latent = {year: float(rng.normal(0.0, 0.25)) for year in config.years}

    rows: list[dict[str, int | float | str]] = []
    for site, year, block, formulation, dose in itertools.product(
        site_labels,
        config.years,
        range(1, config.blocks_per_site_year + 1),
        config.formulations,
        config.doses_g_ai_ha,
    ):
        site_effect = site_latent[site]
        year_effect = year_latent[year]

        temperature_c = 24.0 + 1.2 * site_effect + rng.normal(0.0, 1.4)
        humidity_pct = 67.0 - 2.0 * site_effect + rng.normal(0.0, 4.0)
        rainfall_mm_7d = max(0.0, 20.0 - 1.5 * site_effect + rng.gamma(2.0, 4.0))

        spray_coverage_pct = np.clip(
            58.0
            + 7.0 * (formulation == "B")
            - 0.18 * rainfall_mm_7d
            + rng.normal(0.0, 7.0),
            20.0,
            95.0,
        )

        # Potency depends on formulation and site; B has lower ED50 on average.
        log_ed50 = (
            np.log(9.5)
            - 0.28 * (formulation == "B")
            + 0.35 * site_effect
            + 0.08 * year_effect
        )
        ed50 = float(np.exp(log_ed50))
        hill = 1.65
        bottom = 0.035
        top = 0.97

        if dose <= 0.0:
            dose_response = bottom
        else:
            dose_response = bottom + (top - bottom) / (1.0 + (ed50 / dose) ** hill)

        # Environment and deposition modify efficacy on the logit scale.
        base_logit = np.log(dose_response / (1.0 - dose_response))
        environmental_shift = (
            0.015 * (spray_coverage_pct - 60.0)
            - 0.020 * (temperature_c - 25.0) ** 2 / 4.0
            - 0.010 * max(rainfall_mm_7d - 20.0, 0.0)
            + 0.08 * year_effect
            + 0.65 * site_effect
        )
        mortality_probability = float(
            np.clip(_expit(base_logit + environmental_shift), 0.005, 0.995)
        )
        mortality_count = int(
            rng.binomial(config.n_insects_per_plot, mortality_probability)
        )

        rows.append(
            {
                "site": site,
                "year": int(year),
                "block": int(block),
                "trial_id": f"{site}-{year}-B{block}",
                "formulation": formulation,
                "dose_g_ai_ha": float(dose),
                "temperature_c": float(temperature_c),
                "relative_humidity_pct": float(humidity_pct),
                "rainfall_mm_7d": float(rainfall_mm_7d),
                "spray_coverage_pct": float(spray_coverage_pct),
                "n_insects": int(config.n_insects_per_plot),
                "mortality_count": mortality_count,
                "mortality_rate": mortality_count / config.n_insects_per_plot,
                "true_mortality_probability": mortality_probability,
            }
        )

    frame = pd.DataFrame(rows)
    frame = frame.sort_values(["site", "year", "block", "formulation", "dose_g_ai_ha"])
    return frame.reset_index(drop=True)
