"""Exercise the discovery audit CLI with local synthetic-only records."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from crop_protection_ps.discovery_csv_cli import main
from crop_protection_ps.discovery_evidence import DiscoveryObservation


def _write_synthetic_csv(path: Path) -> None:
    """Create structurally linked stages with clearly synthetic metadata."""
    observed = datetime(2026, 1, 1, tzinfo=UTC)
    columns = list(DiscoveryObservation.model_fields)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for stage in ("lab", "glasshouse", "field"):
            writer.writerow(
                {
                    "candidate_id": "private-synthetic-candidate",
                    "study_id": f"synthetic-{stage}",
                    "experimental_unit_id": "replicate-1",
                    "stage": stage,
                    "endpoint": "inhibition",
                    "endpoint_unit": "percent",
                    "response": "25",
                    "observed_at": observed.isoformat(),
                    "available_at": (observed + timedelta(days=1)).isoformat(),
                    "dose": "1",
                    "dose_unit": "g/ha" if stage == "field" else "mg/L",
                    "experiment_cost": "100",
                    "cost_currency": "EUR",
                    "source_id": "synthetic-fixture",
                    "site_id": "synthetic-site" if stage == "field" else "",
                    "season": "2026" if stage == "field" else "",
                }
            )


def test_cli_outputs_safe_deterministic_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "synthetic.csv"
    _write_synthetic_csv(path)
    before = path.read_bytes()
    assert main([str(path)]) == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert captured.err == ""
    assert report["n_observations"] == 3
    assert report["n_fully_linked_candidates"] == 1
    assert report["stage_counts"] == {"field": 1, "glasshouse": 1, "lab": 1}
    assert "private-synthetic-candidate" not in captured.out
    assert "fully_linked_candidate_ids" not in report
    assert path.read_bytes() == before


def test_cli_opt_in_candidate_ids_and_invalid_csv(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "synthetic.csv"
    _write_synthetic_csv(path)
    assert main([str(path), "--include-candidate-ids"]) == 0
    assert json.loads(capsys.readouterr().out)["fully_linked_candidate_ids"] == [
        "private-synthetic-candidate"
    ]

    path.write_text("not,a,valid,header\n", encoding="utf-8")
    assert main([str(path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid CSV header" in captured.err


def test_cli_missing_file_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([str(tmp_path / "absent.csv")]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "discovery CSV audit failed" in captured.err
