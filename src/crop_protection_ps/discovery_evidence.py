"""Prospective intake contract for linked crop-protection discovery evidence.

This module validates metadata, not biological efficacy or causal assumptions.
No empirical dataset is bundled and no model is promoted by this audit.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from math import isfinite
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DiscoveryStage(StrEnum):
    """Declared assay fidelity, without assuming comparable endpoints."""

    LAB = "lab"
    GLASSHOUSE = "glasshouse"
    FIELD = "field"


class DiscoveryObservation(BaseModel):
    """One endpoint reading with prospective provenance and availability times."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: NonEmpty
    study_id: NonEmpty
    experimental_unit_id: NonEmpty
    stage: DiscoveryStage
    endpoint: NonEmpty
    endpoint_unit: NonEmpty
    response: float = Field(allow_inf_nan=False)
    observed_at: datetime
    available_at: datetime
    dose: float = Field(ge=0.0, allow_inf_nan=False)
    dose_unit: NonEmpty
    experiment_cost: float = Field(ge=0.0, allow_inf_nan=False)
    cost_currency: NonEmpty
    source_id: NonEmpty
    site_id: NonEmpty | None = None
    season: NonEmpty | None = None

    @model_validator(mode="after")
    def check_provenance(self) -> DiscoveryObservation:
        """Disallow ambiguous timestamps and missing field-trial grouping."""
        if self.observed_at.utcoffset() is None or self.available_at.utcoffset() is None:
            raise ValueError("observation and availability times must have timezones")
        if self.available_at < self.observed_at:
            raise ValueError("available_at cannot precede observed_at")
        if self.stage == DiscoveryStage.FIELD and (self.site_id is None or self.season is None):
            raise ValueError("field observations require site_id and season")
        return self


class LinkedEvidenceAudit(BaseModel):
    """Structural completeness only; not an efficacy or transportability result."""

    model_config = ConfigDict(frozen=True)

    n_observations: int
    n_candidates: int
    stage_counts: dict[DiscoveryStage, int]
    fully_linked_candidate_ids: tuple[str, ...]


def audit_linked_discovery_evidence(
    observations: Sequence[DiscoveryObservation],
) -> LinkedEvidenceAudit:
    """Audit candidate linkage and refuse ambiguous duplicate or mixed-unit records.

    A candidate is *fully linked* only if it appears at lab, glasshouse and field
    stages. This is a coverage inventory, not a claim that the observations form
    a matched causal experiment or that outcomes are comparable across stages.
    """
    if not observations:
        raise ValueError("at least one discovery observation is required")

    seen: set[tuple[str, str, DiscoveryStage, str, str, datetime]] = set()
    endpoint_units: dict[tuple[DiscoveryStage, str], str] = {}
    dose_units: dict[DiscoveryStage, str] = {}
    currencies: set[str] = set()
    candidate_stages: dict[str, set[DiscoveryStage]] = defaultdict(set)
    stage_counts = {stage: 0 for stage in DiscoveryStage}

    for observation in observations:
        key = (
            observation.study_id,
            observation.experimental_unit_id,
            observation.stage,
            observation.endpoint,
            observation.candidate_id,
            observation.observed_at,
        )
        if key in seen:
            raise ValueError("duplicate study/unit/candidate/endpoint/timestamp observation")
        seen.add(key)

        existing_unit = endpoint_units.setdefault(
            (observation.stage, observation.endpoint), observation.endpoint_unit
        )
        if existing_unit != observation.endpoint_unit:
            raise ValueError("mixed units for the same stage/endpoint require harmonization")
        existing_dose_unit = dose_units.setdefault(observation.stage, observation.dose_unit)
        if existing_dose_unit != observation.dose_unit:
            raise ValueError("mixed dose units within one stage require harmonization")
        currencies.add(observation.cost_currency)
        if not isfinite(observation.response):
            raise ValueError("response must be finite")
        stage_counts[observation.stage] += 1
        candidate_stages[observation.candidate_id].add(observation.stage)

    if len(currencies) != 1:
        raise ValueError("mixed cost currencies require explicit conversion")

    required = set(DiscoveryStage)
    linked = tuple(
        sorted(candidate for candidate, stages in candidate_stages.items() if required <= stages)
    )
    return LinkedEvidenceAudit(
        n_observations=len(observations),
        n_candidates=len(candidate_stages),
        stage_counts=stage_counts,
        fully_linked_candidate_ids=linked,
    )
