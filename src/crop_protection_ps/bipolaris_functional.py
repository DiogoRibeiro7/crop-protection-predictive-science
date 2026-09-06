"""Functional disease-progress comparisons for the Bipolaris field case."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FunctionalProfileConfig:
    """Configuration for common-grid disease-progress representations."""

    grid_start_dae: float = 30.0
    grid_end_dae: float = 110.0
    grid_step_dae: float = 2.0
    min_assessments: int = 5
    minimum_mean_severity: float = 1e-8

    def __post_init__(self) -> None:
        """Validate a scientifically meaningful interpolation grid."""
        values = (
            self.grid_start_dae,
            self.grid_end_dae,
            self.grid_step_dae,
            self.minimum_mean_severity,
        )
        if not all(np.isfinite(value) for value in values):
            raise ValueError("Functional-profile configuration values must be finite.")
        if self.grid_start_dae >= self.grid_end_dae:
            raise ValueError("grid_start_dae must be smaller than grid_end_dae.")
        if self.grid_step_dae <= 0:
            raise ValueError("grid_step_dae must be positive.")
        if self.min_assessments < 2:
            raise ValueError("min_assessments must be at least 2.")
        if self.minimum_mean_severity <= 0:
            raise ValueError("minimum_mean_severity must be positive.")

        span = self.grid_end_dae - self.grid_start_dae
        intervals = span / self.grid_step_dae
        if not isclose(intervals, round(intervals), rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("The DAE span must be an integer multiple of grid_step_dae.")


def common_dae_grid(config: FunctionalProfileConfig | None = None) -> np.ndarray:
    """Return the exact inclusive DAE grid defined by *config*."""
    profile_config = config or FunctionalProfileConfig()
    intervals = round(
        (profile_config.grid_end_dae - profile_config.grid_start_dae)
        / profile_config.grid_step_dae
    )
    return np.linspace(
        profile_config.grid_start_dae,
        profile_config.grid_end_dae,
        intervals + 1,
        dtype=float,
    )


def _validate_frame(frame: pd.DataFrame) -> None:
    required = {
        "environment",
        "hybrid",
        "days_after_emergence",
        "severity_pct",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing normalized Bipolaris columns: {sorted(missing)}.")


def functional_profile_eligibility(
    frame: pd.DataFrame,
    config: FunctionalProfileConfig | None = None,
) -> pd.DataFrame:
    """Audit which environment×hybrid curves are eligible for shape analysis."""
    _validate_frame(frame)
    profile_config = config or FunctionalProfileConfig()
    grid = common_dae_grid(profile_config)
    duration = profile_config.grid_end_dae - profile_config.grid_start_dae

    records: list[dict[str, str | int | float | bool]] = []
    grouped = frame.groupby(["environment", "hybrid"], sort=True, observed=True)
    for (environment, hybrid), group in grouped:
        ordered = group.sort_values("days_after_emergence")
        days = ordered["days_after_emergence"].to_numpy(dtype=float)
        severity = ordered["severity_pct"].to_numpy(dtype=float)

        enough_assessments = len(ordered) >= profile_config.min_assessments
        covers_grid_start = bool(days[0] <= profile_config.grid_start_dae)
        covers_grid_end = bool(days[-1] >= profile_config.grid_end_dae)
        mean_severity: float | None = None
        above_severity_floor = False
        if enough_assessments and covers_grid_start and covers_grid_end:
            interpolated = np.interp(grid, days, severity)
            mean_severity = float(np.trapezoid(interpolated, grid) / duration)
            above_severity_floor = mean_severity > profile_config.minimum_mean_severity

        eligible = (
            enough_assessments
            and covers_grid_start
            and covers_grid_end
            and above_severity_floor
        )
        if not enough_assessments:
            reason = "too_few_assessments"
        elif not covers_grid_start:
            reason = "starts_after_grid"
        elif not covers_grid_end:
            reason = "ends_before_grid"
        elif not above_severity_floor:
            reason = "mean_severity_below_floor"
        else:
            reason = "eligible"

        records.append(
            {
                "environment": str(environment),
                "hybrid": str(hybrid),
                "n_assessments": len(ordered),
                "min_dae": float(days[0]),
                "max_dae": float(days[-1]),
                "mean_severity_pct": (
                    mean_severity if mean_severity is not None else np.nan
                ),
                "enough_assessments": enough_assessments,
                "covers_grid_start": covers_grid_start,
                "covers_grid_end": covers_grid_end,
                "above_severity_floor": above_severity_floor,
                "eligible": eligible,
                "reason": reason,
            }
        )

    return pd.DataFrame.from_records(records).sort_values(
        ["environment", "hybrid"]
    ).reset_index(drop=True)


def functional_profiles(
    frame: pd.DataFrame,
    config: FunctionalProfileConfig | None = None,
) -> pd.DataFrame:
    """Interpolate eligible disease curves on a common grid.

    Raw interpolated severity retains disease burden. ``relative_shape`` divides
    each curve by its own time-average severity, so it has time-average one and
    isolates trajectory shape from overall disease scale.
    """
    _validate_frame(frame)
    profile_config = config or FunctionalProfileConfig()
    grid = common_dae_grid(profile_config)
    duration = profile_config.grid_end_dae - profile_config.grid_start_dae
    eligibility = functional_profile_eligibility(frame, profile_config)
    eligible_pairs = set(
        eligibility.loc[
            eligibility["eligible"], ["environment", "hybrid"]
        ].itertuples(index=False, name=None)
    )

    records: list[dict[str, str | float]] = []
    grouped = frame.groupby(["environment", "hybrid"], sort=True, observed=True)
    for (environment, hybrid), group in grouped:
        key = (str(environment), str(hybrid))
        if key not in eligible_pairs:
            continue
        ordered = group.sort_values("days_after_emergence")
        days = ordered["days_after_emergence"].to_numpy(dtype=float)
        severity = ordered["severity_pct"].to_numpy(dtype=float)
        interpolated = np.interp(grid, days, severity)
        mean_severity = float(np.trapezoid(interpolated, grid) / duration)
        relative_shape = interpolated / mean_severity
        for dae, severity_pct, shape_value in zip(
            grid, interpolated, relative_shape, strict=True
        ):
            records.append(
                {
                    "environment": str(environment),
                    "hybrid": str(hybrid),
                    "days_after_emergence": float(dae),
                    "severity_pct": float(severity_pct),
                    "relative_shape": float(shape_value),
                    "mean_severity_pct": mean_severity,
                }
            )

    profiles = pd.DataFrame.from_records(records)
    if profiles.empty:
        raise ValueError("No Bipolaris curves span the requested functional-analysis grid.")
    return profiles.sort_values(
        ["environment", "hybrid", "days_after_emergence"]
    ).reset_index(drop=True)


def _relationship(
    environment_a: str,
    hybrid_a: str,
    environment_b: str,
    hybrid_b: str,
) -> str:
    """Classify a pair of disease curves by environment and hybrid identity."""
    same_environment = environment_a == environment_b
    same_hybrid = hybrid_a == hybrid_b
    if same_environment and same_hybrid:
        raise ValueError("A curve must not be compared with itself.")
    if same_hybrid:
        return "same_hybrid_different_environment"
    if same_environment:
        return "different_hybrid_same_environment"
    return "different_hybrid_different_environment"


def pairwise_functional_distances(profiles: pd.DataFrame) -> pd.DataFrame:
    """Compute raw-burden and scale-normalized shape distances between curves."""
    required = {
        "environment",
        "hybrid",
        "days_after_emergence",
        "severity_pct",
        "relative_shape",
    }
    missing = required.difference(profiles.columns)
    if missing:
        raise ValueError(f"Missing functional-profile columns: {sorted(missing)}.")

    curves: list[tuple[str, str, np.ndarray, np.ndarray]] = []
    grouped = profiles.groupby(["environment", "hybrid"], sort=True, observed=True)
    expected_grid: np.ndarray | None = None
    for (environment, hybrid), group in grouped:
        ordered = group.sort_values("days_after_emergence")
        grid = ordered["days_after_emergence"].to_numpy(dtype=float)
        if expected_grid is None:
            expected_grid = grid
        elif len(grid) != len(expected_grid) or not np.allclose(grid, expected_grid):
            raise ValueError("All functional profiles must share the same DAE grid.")
        curves.append(
            (
                str(environment),
                str(hybrid),
                ordered["severity_pct"].to_numpy(dtype=float),
                ordered["relative_shape"].to_numpy(dtype=float),
            )
        )

    if len(curves) < 2:
        raise ValueError("At least two functional profiles are required.")

    records: list[dict[str, str | float]] = []
    for index_a, curve_a in enumerate(curves[:-1]):
        environment_a, hybrid_a, severity_a, shape_a = curve_a
        for curve_b in curves[index_a + 1 :]:
            environment_b, hybrid_b, severity_b, shape_b = curve_b
            records.append(
                {
                    "environment_a": environment_a,
                    "hybrid_a": hybrid_a,
                    "environment_b": environment_b,
                    "hybrid_b": hybrid_b,
                    "relationship": _relationship(
                        environment_a,
                        hybrid_a,
                        environment_b,
                        hybrid_b,
                    ),
                    "raw_severity_rmse_pct": float(
                        np.sqrt(np.mean(np.square(severity_a - severity_b)))
                    ),
                    "normalized_shape_rmse": float(
                        np.sqrt(np.mean(np.square(shape_a - shape_b)))
                    ),
                }
            )
    return pd.DataFrame.from_records(records)


def functional_stability_summary(
    distances: pd.DataFrame,
) -> dict[str, int | float | None]:
    """Summarize whether hybrid-specific trajectory shape persists across environments."""
    required = {"relationship", "raw_severity_rmse_pct", "normalized_shape_rmse"}
    missing = required.difference(distances.columns)
    if missing:
        raise ValueError(f"Missing functional-distance columns: {sorted(missing)}.")

    same = distances.loc[
        distances["relationship"] == "same_hybrid_different_environment"
    ]
    cross_other = distances.loc[
        distances["relationship"] == "different_hybrid_different_environment"
    ]
    within_other = distances.loc[
        distances["relationship"] == "different_hybrid_same_environment"
    ]

    def median_or_none(table: pd.DataFrame, column: str) -> float | None:
        if table.empty:
            return None
        return float(table[column].median())

    same_shape = median_or_none(same, "normalized_shape_rmse")
    cross_other_shape = median_or_none(cross_other, "normalized_shape_rmse")
    ratio: float | None = None
    if same_shape is not None and cross_other_shape is not None and cross_other_shape > 0.0:
        ratio = same_shape / cross_other_shape

    return {
        "same_hybrid_cross_environment_pairs": len(same),
        "different_hybrid_cross_environment_pairs": len(cross_other),
        "different_hybrid_within_environment_pairs": len(within_other),
        "median_same_hybrid_cross_environment_raw_rmse_pct": median_or_none(
            same, "raw_severity_rmse_pct"
        ),
        "median_same_hybrid_cross_environment_shape_rmse": same_shape,
        "median_different_hybrid_cross_environment_shape_rmse": cross_other_shape,
        "median_different_hybrid_within_environment_shape_rmse": median_or_none(
            within_other, "normalized_shape_rmse"
        ),
        "same_vs_different_cross_environment_shape_distance_ratio": ratio,
    }
