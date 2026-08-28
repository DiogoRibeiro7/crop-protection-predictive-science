"""Sequential experimental design using a simple D-optimality criterion."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _candidate_vector(row: pd.Series) -> np.ndarray:
    """Map a candidate condition to a compact design vector."""
    return np.asarray(
        [
            1.0,
            np.log1p(float(row["dose_g_ai_ha"])),
            (float(row["temperature_c"]) - 25.0) / 5.0,
            (float(row["spray_coverage_pct"]) - 60.0) / 15.0,
        ],
        dtype=float,
    )


def _information_contribution(vector: np.ndarray, probability: float) -> np.ndarray:
    """Approximate Bernoulli Fisher information contribution."""
    weight = max(probability * (1.0 - probability), 1e-6)
    return weight * np.outer(vector, vector)


def make_candidate_grid() -> pd.DataFrame:
    """Create plausible next-experiment conditions around the informative dose range."""
    rows: list[dict[str, float]] = []
    for dose in (3.0, 5.0, 7.5, 10.0, 15.0, 25.0, 40.0):
        for temperature in (20.0, 25.0, 30.0):
            for coverage in (45.0, 65.0, 85.0):
                rows.append(
                    {
                        "dose_g_ai_ha": dose,
                        "temperature_c": temperature,
                        "spray_coverage_pct": coverage,
                    }
                )
    return pd.DataFrame(rows)


def select_d_optimal_candidates(
    candidates: pd.DataFrame,
    *,
    ed50: float,
    hill: float,
    n_select: int = 6,
) -> pd.DataFrame:
    """Greedily choose candidates maximising log-determinant information gain.

    The response probability is approximated from the fitted dose-response curve.
    This is deliberately transparent: the aim is to demonstrate how model
    uncertainty can drive the next experiment rather than to claim a final
    production-grade design policy.
    """
    required = {"dose_g_ai_ha", "temperature_c", "spray_coverage_pct"}
    missing = required.difference(candidates.columns)
    if missing:
        raise ValueError(f"candidate grid is missing columns: {sorted(missing)}")
    if not 1 <= n_select <= len(candidates):
        raise ValueError("n_select must be between 1 and the number of candidates")

    selected: list[int] = []
    information = np.eye(4, dtype=float) * 1e-3

    for _ in range(n_select):
        best_index: int | None = None
        best_score = -np.inf
        for index, row in candidates.iterrows():
            if int(index) in selected:
                continue
            dose = float(row["dose_g_ai_ha"])
            probability = 1.0 / (1.0 + (ed50 / dose) ** hill)
            vector = _candidate_vector(row)
            candidate_info = information + _information_contribution(vector, probability)
            sign, logdet = np.linalg.slogdet(candidate_info)
            score = logdet if sign > 0 else -np.inf
            if score > best_score:
                best_score = score
                best_index = int(index)

        if best_index is None:
            raise RuntimeError("failed to select a D-optimal candidate")
        row = candidates.loc[best_index]
        probability = 1.0 / (1.0 + (ed50 / float(row["dose_g_ai_ha"])) ** hill)
        information += _information_contribution(_candidate_vector(row), probability)
        selected.append(best_index)

    output = candidates.loc[selected].copy().reset_index(drop=True)
    output.insert(0, "rank", np.arange(1, len(output) + 1, dtype=int))
    return output
