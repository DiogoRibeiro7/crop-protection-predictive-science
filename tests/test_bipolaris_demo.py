from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from crop_protection_ps.bipolaris_demo import run_bipolaris_demo


def _write_raw_case(root: Path) -> None:
    """Write a compact three-hybrid/four-environment source-shaped fixture."""
    rows: list[dict[str, object]] = []
    days = [30, 50, 70, 90, 110]
    base_curves = {
        "H1": [0.0, 8.0, 20.0, 35.0, 50.0],
        "H2": [0.0, 12.0, 30.0, 50.0, 70.0],
        "H3": [0.0, 4.0, 12.0, 24.0, 36.0],
    }
    environment_scale = {
        "SiteA_Cedo": 0.90,
        "SiteB_Cedo": 1.00,
        "SiteC_Preferencial": 1.10,
        "SiteD_Preferencial": 1.20,
    }
    for environment, scale in environment_scale.items():
        for hybrid, base_severity in base_curves.items():
            severity = [value * scale for value in base_severity]
            for day, value in zip(days, severity, strict=True):
                rows.append(
                    {
                        "Ambiente": environment,
                        "Hibrido": hybrid,
                        "DAE": day,
                        "Fenologia": "R1",
                        "Bipolaris": value,
                    }
                )

    raw_dir = root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame.from_records(rows).to_csv(raw_dir / "maize_bipolaris.csv", index=False)


def test_demo_persists_functional_prospective_and_promotion_bundle(tmp_path: Path) -> None:
    """The executable empirical case must persist baseline and candidate outputs."""
    _write_raw_case(tmp_path)
    summary = run_bipolaris_demo(tmp_path, download_if_missing=False)
    results_dir = tmp_path / "results" / "bipolaris"

    expected_outputs = (
        "functional_eligibility.csv",
        "functional_profiles.csv",
        "functional_distances.csv",
        "loeo_burden_predictions.csv",
        "loeo_burden_folds.csv",
        "loeo_shape_predictions.csv",
        "loeo_shape_folds.csv",
        "planting_window_burden_predictions.csv",
        "planting_window_burden_folds.csv",
        "planting_window_shape_predictions.csv",
        "planting_window_shape_folds.csv",
    )
    for filename in expected_outputs:
        assert (results_dir / filename).exists()

    assert (results_dir / "figures" / "functional_shape_stability.png").exists()
    assert (results_dir / "figures" / "loeo_audpc_transport.png").exists()

    persisted = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    assert persisted["functional_shape_stability"] == summary["functional_shape_stability"]
    assert persisted["leave_one_environment_out"] == summary["leave_one_environment_out"]
    assert persisted["planting_window_candidate"] == summary["planting_window_candidate"]
    assert persisted["functional_shape_stability"]["same_hybrid_cross_environment_pairs"] == 18
    assert persisted["functional_shape_stability"]["eligibility"]["total_curves"] == 12
    assert persisted["functional_shape_stability"]["eligibility"]["eligible_curves"] == 12
    assert persisted["leave_one_environment_out"]["burden_folds"] == 4
    assert persisted["leave_one_environment_out"]["shape_folds"] == 4
    assert isinstance(persisted["planting_window_candidate"]["burden"]["promoted"], bool)
    assert isinstance(persisted["planting_window_candidate"]["shape"]["promoted"], bool)
