from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from crop_protection_ps.bipolaris import (
    BipolarisSourceContract,
    curve_metrics,
    empirical_case_summary,
    environment_rank_stability,
    git_blob_sha1,
    load_bipolaris,
    validate_bipolaris_frame,
    validate_source_bytes,
)


def _raw_frame() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    curves = {
        ("E1", "H1"): [0.0, 5.0, 15.0, 30.0, 45.0],
        ("E1", "H2"): [0.0, 10.0, 25.0, 45.0, 65.0],
        ("E1", "H3"): [0.0, 2.0, 8.0, 18.0, 28.0],
        ("E2", "H1"): [0.0, 4.0, 12.0, 25.0, 40.0],
        ("E2", "H2"): [0.0, 12.0, 28.0, 48.0, 68.0],
        ("E2", "H3"): [0.0, 1.0, 6.0, 15.0, 24.0],
    }
    days = [25, 40, 55, 70, 85]
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
    return pd.DataFrame.from_records(rows)


def test_git_blob_sha1_matches_known_payload() -> None:
    assert git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_validate_source_bytes_rejects_mutated_payload() -> None:
    payload = b"abc"
    contract = BipolarisSourceContract(
        source_size_bytes=len(payload),
        source_git_blob_sha1=git_blob_sha1(payload),
    )
    validate_source_bytes(payload, contract)

    with pytest.raises(ValueError, match="byte length changed"):
        validate_source_bytes(payload + b"x", contract)

    mutated = b"abd"
    with pytest.raises(ValueError, match="Git blob identity changed"):
        validate_source_bytes(mutated, contract)


def test_validate_bipolaris_frame_rejects_duplicate_assessment() -> None:
    frame = _raw_frame()
    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="environment-hybrid-day"):
        validate_bipolaris_frame(duplicate)


def test_load_bipolaris_normalizes_source_columns(tmp_path: Path) -> None:
    path = tmp_path / "maize_bipolaris.csv"
    _raw_frame().to_csv(path, index=False)

    loaded = load_bipolaris(path)

    assert tuple(loaded.columns) == (
        "environment",
        "hybrid",
        "days_after_emergence",
        "phenology",
        "severity_pct",
    )
    assert loaded["environment"].nunique() == 2
    assert loaded["hybrid"].nunique() == 3


def test_curve_metrics_preserves_environment_specific_rankings(tmp_path: Path) -> None:
    path = tmp_path / "maize_bipolaris.csv"
    _raw_frame().to_csv(path, index=False)
    frame = load_bipolaris(path)

    metrics = curve_metrics(frame)
    correlations = environment_rank_stability(metrics)
    summary = empirical_case_summary(frame, metrics)

    assert len(metrics) == 6
    assert (metrics["n_assessments"] == 5).all()
    assert correlations.loc["E1", "E2"] == pytest.approx(1.0)
    assert summary == {
        "rows": 30,
        "environments": 2,
        "hybrids": 3,
        "eligible_curves": 6,
        "median_pairwise_spearman_audpc": pytest.approx(1.0),
    }
