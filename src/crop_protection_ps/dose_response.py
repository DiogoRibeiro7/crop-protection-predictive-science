"""Non-linear dose-response estimation and cluster bootstrap uncertainty."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


@dataclass(frozen=True)
class DoseResponseFit:
    """Four-parameter logistic dose-response estimate."""

    bottom: float
    top: float
    ed50: float
    hill: float

    @property
    def ed90(self) -> float:
        """Dose reaching 90% of the fitted response range."""
        return float(self.ed50 * 9.0 ** (1.0 / self.hill))


def four_parameter_logistic(
    dose: np.ndarray,
    bottom: float,
    top: float,
    ed50: float,
    hill: float,
) -> np.ndarray:
    """Increasing four-parameter logistic response curve."""
    dose_arr = np.asarray(dose, dtype=float)
    safe_dose = np.maximum(dose_arr, 1e-9)
    return bottom + (top - bottom) / (1.0 + (ed50 / safe_dose) ** hill)


def fit_dose_response(frame: pd.DataFrame, *, formulation: str = "A") -> DoseResponseFit:
    """Fit a four-parameter logistic curve for one formulation."""
    subset = frame.loc[
        (frame["formulation"] == formulation) & (frame["dose_g_ai_ha"] > 0.0)
    ]
    if len(subset) < 12:
        raise ValueError("at least 12 positive-dose observations are required")

    dose = subset["dose_g_ai_ha"].to_numpy(dtype=float)
    response = subset["mortality_rate"].to_numpy(dtype=float)
    initial = np.asarray([0.02, 0.98, np.median(dose), 1.5], dtype=float)
    lower = np.asarray([0.0, 0.60, 0.05, 0.20], dtype=float)
    upper = np.asarray([0.30, 1.0, 200.0, 6.0], dtype=float)
    parameters, _ = curve_fit(
        four_parameter_logistic,
        dose,
        response,
        p0=initial,
        bounds=(lower, upper),
        maxfev=50_000,
    )
    return DoseResponseFit(*map(float, parameters))


def cluster_bootstrap_ed(
    frame: pd.DataFrame,
    *,
    formulation: str = "A",
    n_bootstrap: int = 500,
    seed: int = 20260826,
) -> pd.DataFrame:
    """Bootstrap ED50 and ED90 by resampling trial clusters, not individual rows."""
    if n_bootstrap < 100:
        raise ValueError("n_bootstrap must be at least 100")

    subset = frame.loc[frame["formulation"] == formulation].copy()
    cluster_ids = subset["trial_id"].drop_duplicates().to_numpy(dtype=str)
    if len(cluster_ids) < 4:
        raise ValueError("at least four independent trial clusters are required")

    rng = np.random.default_rng(seed)
    estimates: list[dict[str, float]] = []
    for _ in range(n_bootstrap):
        sampled_clusters = rng.choice(cluster_ids, size=len(cluster_ids), replace=True)
        parts: list[pd.DataFrame] = []
        for draw_index, cluster in enumerate(sampled_clusters):
            part = subset.loc[subset["trial_id"] == cluster].copy()
            # Unique synthetic cluster id preserves duplicated resampled clusters.
            part["trial_id"] = f"draw-{draw_index}-{cluster}"
            parts.append(part)
        bootstrap_frame = pd.concat(parts, ignore_index=True)
        try:
            fit = fit_dose_response(bootstrap_frame, formulation=formulation)
        except (RuntimeError, ValueError):
            continue
        estimates.append({"ed50": fit.ed50, "ed90": fit.ed90, "hill": fit.hill})

    if len(estimates) < int(0.8 * n_bootstrap):
        raise RuntimeError("too many bootstrap dose-response fits failed")
    return pd.DataFrame(estimates)


def bootstrap_interval(samples: pd.Series, *, confidence: float = 0.95) -> tuple[float, float]:
    """Return a two-sided percentile interval."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be in (0, 1)")
    alpha = (1.0 - confidence) / 2.0
    lower, upper = samples.quantile([alpha, 1.0 - alpha]).tolist()
    return float(lower), float(upper)
