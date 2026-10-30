"""Synthetic, local-only CSV intake tests; no external experiment data."""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from crop_protection_ps.discovery_csv import (
    DiscoveryCSVError,
    audit_discovery_csv,
    load_discovery_csv,
)
from crop_protection_ps.discovery_evidence import DiscoveryObservation


def _synthetic_row(stage: str) -> dict[str, str]:
    observed = datetime(2026, 1, 1, tzinfo=UTC)
    return {
        "candidate_id": "candidate-synthetic",
        "study_id": f"synthetic-{stage}",
        "experimental_unit_id": "replicate-1",
        "stage": stage,
        "endpoint": "inhibition",
        "endpoint_unit": "percent",
        "response": "25.0",
        "observed_at": observed.isoformat(),
        "available_at": (observed + timedelta(days=1)).isoformat(),
        "dose": "1.0",
        "dose_unit": "mg/L" if stage != "field" else "g/ha",
        "experiment_cost": "100.0",
        "cost_currency": "EUR",
        "source_id": "synthetic-only",
        "site_id": "synthetic-site" if stage == "field" else "",
        "season": "2026" if stage == "field" else "",
    }


def _write_csv(path: Path, rows: list[dict[str, str]], fields: list[str] | None = None) -> None:
    columns = fields if fields is not None else list(DiscoveryObservation.model_fields)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def test_load_and_audit_linked_synthetic_stages(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.csv"
    _write_csv(path, [_synthetic_row(stage) for stage in ("lab", "glasshouse", "field")])
    records = load_discovery_csv(path)
    assert len(records) == 3
    assert records[2].site_id == "synthetic-site"
    assert records[0].site_id is None
    result = audit_discovery_csv(path)
    assert result.fully_linked_candidate_ids == ("candidate-synthetic",)


def test_optional_columns_may_be_absent_for_lab(tmp_path: Path) -> None:
    path = tmp_path / "lab.csv"
    columns = [
        name for name in DiscoveryObservation.model_fields if name not in {"site_id", "season"}
    ]
    _write_csv(path, [_synthetic_row("lab")], columns)
    assert load_discovery_csv(path)[0].season is None


@pytest.mark.parametrize("removed", ["response", "source_id", "observed_at"])
def test_reject_missing_required_header(tmp_path: Path, removed: str) -> None:
    path = tmp_path / "missing.csv"
    columns = [name for name in DiscoveryObservation.model_fields if name != removed]
    _write_csv(path, [_synthetic_row("lab")], columns)
    with pytest.raises(DiscoveryCSVError, match="missing"):
        load_discovery_csv(path)


def test_reject_duplicate_and_unknown_headers(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("candidate_id,candidate_id\na,b\n", encoding="utf-8")
    with pytest.raises(DiscoveryCSVError, match="duplicate CSV columns"):
        load_discovery_csv(path)
    _write_csv(path, [_synthetic_row("lab")], [*DiscoveryObservation.model_fields, "unknown"])
    with pytest.raises(DiscoveryCSVError, match="unexpected"):
        load_discovery_csv(path)


def test_reject_extra_or_missing_values_with_line_number(tmp_path: Path) -> None:
    path = tmp_path / "invalid.csv"
    _write_csv(path, [_synthetic_row("lab")])
    with path.open("a", encoding="utf-8") as handle:
        handle.write("too,many,fields,for,the,declared,header\n")
    with pytest.raises(DiscoveryCSVError, match="line 3: malformed"):
        load_discovery_csv(path)


def test_reject_invalid_field_record_with_line_number(tmp_path: Path) -> None:
    path = tmp_path / "field.csv"
    _write_csv(path, [_synthetic_row("field") | {"season": ""}])
    with pytest.raises(DiscoveryCSVError, match="line 2"):
        load_discovery_csv(path)


def test_reject_empty_csv(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    _write_csv(path, [])
    with pytest.raises(DiscoveryCSVError, match="no observations"):
        load_discovery_csv(path)
