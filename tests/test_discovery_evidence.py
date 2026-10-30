"""Synthetic fixtures for the prospective discovery-evidence intake contract."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from crop_protection_ps.discovery_evidence import (
    DiscoveryObservation,
    DiscoveryStage,
    audit_linked_discovery_evidence,
)


def _record(stage: DiscoveryStage, **changes: object) -> DiscoveryObservation:
    observed = datetime(2026, 1, 15, tzinfo=UTC)
    values: dict[str, object] = {
        "candidate_id": "candidate-A",
        "study_id": f"synthetic-{stage.value}",
        "experimental_unit_id": "replicate-1",
        "stage": stage,
        "endpoint": "inhibition",
        "endpoint_unit": "percent",
        "response": 25.0,
        "observed_at": observed,
        "available_at": observed + timedelta(days=1),
        "dose": 1.0,
        "dose_unit": "mg/L",
        "experiment_cost": 100.0,
        "cost_currency": "EUR",
        "source_id": "synthetic-fixture-not-empirical",
        "site_id": "synthetic-site" if stage == DiscoveryStage.FIELD else None,
        "season": "2026" if stage == DiscoveryStage.FIELD else None,
    }
    values.update(changes)
    return DiscoveryObservation.model_validate(values)


def test_audit_counts_only_candidates_present_at_all_three_stages() -> None:
    records = [
        _record(DiscoveryStage.LAB),
        _record(DiscoveryStage.GLASSHOUSE),
        _record(DiscoveryStage.FIELD),
        _record(DiscoveryStage.LAB, candidate_id="candidate-B", experimental_unit_id="replicate-2"),
    ]
    result = audit_linked_discovery_evidence(records)
    assert result.n_observations == 4
    assert result.n_candidates == 2
    assert result.fully_linked_candidate_ids == ("candidate-A",)
    assert result.stage_counts[DiscoveryStage.FIELD] == 1


def test_intake_rejects_ambiguous_provenance_and_invalid_values() -> None:
    with pytest.raises(ValidationError, match="site_id and season"):
        _record(DiscoveryStage.FIELD, site_id=None)
    with pytest.raises(ValidationError, match="timezones"):
        _record(DiscoveryStage.LAB, observed_at=datetime(2026, 1, 15))
    with pytest.raises(ValidationError, match="cannot precede"):
        _record(
            DiscoveryStage.LAB,
            available_at=datetime(2026, 1, 14, tzinfo=UTC),
        )
    with pytest.raises(ValidationError):
        _record(DiscoveryStage.LAB, dose=-1.0)
    with pytest.raises(ValidationError):
        _record(DiscoveryStage.LAB, response=float("nan"))
    with pytest.raises(ValidationError):
        _record(DiscoveryStage.LAB, source_id="")
    with pytest.raises(ValidationError):
        _record(DiscoveryStage.LAB, unknown_field="not allowed")


def test_audit_refuses_duplicates_and_mixed_unharmonized_units() -> None:
    first = _record(DiscoveryStage.LAB)
    second_lab = {"study_id": "synthetic-second-lab", "experimental_unit_id": "replicate-2"}
    with pytest.raises(ValueError, match="duplicate"):
        audit_linked_discovery_evidence([first, first])
    with pytest.raises(ValueError, match="mixed units"):
        audit_linked_discovery_evidence(
            [first, _record(DiscoveryStage.LAB, endpoint_unit="fraction", **second_lab)]
        )
    with pytest.raises(ValueError, match="mixed dose units"):
        audit_linked_discovery_evidence(
            [first, _record(DiscoveryStage.LAB, dose_unit="g/ha", **second_lab)]
        )
    # Cross-stage endpoints and application doses need not share physical units.
    cross_stage = audit_linked_discovery_evidence(
        [first, _record(DiscoveryStage.FIELD, dose_unit="g/ha", endpoint_unit="fraction")]
    )
    assert cross_stage.n_observations == 2
    with pytest.raises(ValueError, match="mixed cost currencies"):
        audit_linked_discovery_evidence(
            [first, _record(DiscoveryStage.FIELD, cost_currency="USD")]
        )
    with pytest.raises(ValueError, match="at least one"):
        audit_linked_discovery_evidence([])
