from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from crop_protection_ps.bipolaris_demo import run_bipolaris_demo


def _write_raw_case(root: Path) -> None:
    """Write a compact three-hybrid/two-environment source-shaped fixture."""
    rows: list[dict[str, object]] = []
    days = [30, 50, 70, 90, 110]
    curves = {
        ("E1", "H1"): [0.0, 8.0, 20.0, 35.0, 50.0],
        ("E1", "H2"): [0.0, 12.0, 30.0, 50.0, 70.0],
        ("E1", "H3"): [0.0, 4.0, 12.0, 24.0, 36.0],
        ("E2", "H1"): [0.0, 10.0, 25.0, 42.0, 60.0],
        ("E2", "H2"): [0.0, 14.0, 34.0, 56.0, 78.0],
        ("E2", "H3"): [0.0, 5.0, 14.0, 28.0, 40.0],
    }
    for (environment, hybrid), severity in curves.items():
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


def test_demo_persists_functional_stability_bundle(tmp_path: Path) -> None:
    """The executable empirical case must persist functional analysis outputs."""
    _write_raw_case(tmp_path)

    summary = run_bipolaris_demo(tmp_path, download_if_missing=False)
    results_dir = tmp_path / "results" / "bipolaris"

    assert (results_dir / "functional_profiles.csv").exists()
    assert (results_dir / "functional_distances.csv").exists()
    assert (results_dir / "figures" / "functional_shape_stability.png").exists()

    persisted = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    assert "functional_shape_stability" in persisted
    assert persisted["functional_shape_stability"] == summary["functional_shape_stability"]
    assert (
        persisted["functional_shape_stability"][
            "same_hybrid_cross_environment_pairs"
        ]
        == 3
    )
