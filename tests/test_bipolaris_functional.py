from __future__ import annotations

import pandas as pd
import pytest

from crop_protection_ps.bipolaris_functional import (
    FunctionalProfileConfig,
    common_dae_grid,
    functional_profiles,
    functional_stability_summary,
    pairwise_functional_distances,
)


def _normalized_frame() -> pd.DataFrame:
    rows: list[dict[str, str | float]] = []
    days = [30.0, 50.0, 70.0, 90.0, 110.0]
    curves = {
        ("E1", "H1"): [1.0, 3.0, 8.0, 15.0, 20.0],
        ("E2", "H1"): [2.0, 6.0, 16.0, 30.0, 40.0],
        ("E1", "H2"): [1.0, 8.0, 18.0, 20.0, 20.0],
        ("E2", "H2"): [2.0, 16.0, 36.0, 40.0, 40.0],
        ("E1", "H3"): [1.0, 2.0, 4.0, 8.0, 16.0],
        ("E2", "H3"): [2.0, 4.0, 8.0, 16.0, 32.0],
    }
    for (environment, hybrid), severity in curves.items():
        for dae, value in zip(days, severity, strict=True):
            rows.append(
                {
                    "environment": environment,
                    "hybrid": hybrid,
                    "days_after_emergence": dae,
                    "severity_pct": value,
                }
            )
    return pd.DataFrame.from_records(rows)


def test_common_dae_grid_is_inclusive_and_exact() -> None:
    config = FunctionalProfileConfig(
        grid_start_dae=30.0,
        grid_end_dae=110.0,
        grid_step_dae=20.0,
    )

    assert common_dae_grid(config).tolist() == [30.0, 50.0, 70.0, 90.0, 110.0]


def test_profile_config_rejects_inexact_grid() -> None:
    with pytest.raises(ValueError, match="integer multiple"):
        FunctionalProfileConfig(
            grid_start_dae=30.0,
            grid_end_dae=110.0,
            grid_step_dae=7.0,
        )


def test_relative_shape_removes_pure_severity_scale_difference() -> None:
    config = FunctionalProfileConfig(grid_step_dae=20.0)
    profiles = functional_profiles(_normalized_frame(), config)
    distances = pairwise_functional_distances(profiles)

    same_h1 = distances.loc[
        (distances["hybrid_a"] == "H1")
        & (distances["hybrid_b"] == "H1")
    ].iloc[0]

    assert float(same_h1["raw_severity_rmse_pct"]) > 0.0
    assert float(same_h1["normalized_shape_rmse"]) == pytest.approx(0.0)


def test_functional_summary_separates_hybrid_identity_from_burden() -> None:
    config = FunctionalProfileConfig(grid_step_dae=20.0)
    profiles = functional_profiles(_normalized_frame(), config)
    distances = pairwise_functional_distances(profiles)
    summary = functional_stability_summary(distances)

    assert summary["same_hybrid_cross_environment_pairs"] == 3
    assert summary["different_hybrid_cross_environment_pairs"] == 6
    assert summary["different_hybrid_within_environment_pairs"] == 6
    assert summary["median_same_hybrid_cross_environment_shape_rmse"] == pytest.approx(0.0)
    ratio = summary["same_vs_different_cross_environment_shape_distance_ratio"]
    assert isinstance(ratio, float)
    assert ratio == pytest.approx(0.0)


def test_functional_profiles_skip_curves_without_full_grid_support() -> None:
    frame = _normalized_frame()
    truncated = frame.loc[
        ~(
            (frame["environment"] == "E2")
            & (frame["hybrid"] == "H3")
            & (frame["days_after_emergence"] == 110.0)
        )
    ]

    profiles = functional_profiles(
        truncated,
        FunctionalProfileConfig(grid_step_dae=20.0),
    )

    represented = set(
        profiles[["environment", "hybrid"]].itertuples(index=False, name=None)
    )
    assert ("E2", "H3") not in represented
