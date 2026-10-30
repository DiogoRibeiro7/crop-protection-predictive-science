# Prospective linked-discovery evidence intake

The main empirical programme is closed for the data currently available.
Reopening multi-fidelity model selection requires new independent evidence, not
another candidate tuned against the existing six Bipolaris environments.

`crop_protection_ps.discovery_evidence` defines a typed, data-free intake
contract for a future lab–glasshouse–field discovery dataset. It does not
download, impute, fabricate or validate biological outcomes.

## Minimum observation contract

Each row must identify:

- a stable candidate, study and experimental unit;
- a declared assay stage (`lab`, `glasshouse`, `field`);
- an endpoint, endpoint unit, observed response and applied dose with units;
- timezone-aware observation and data-availability timestamps;
- experimental cost and its currency;
- an independently auditable source reference;
- for field observations, site and season identifiers.

The contract rejects ambiguous missing metadata, invalid numerical quantities,
duplicate study/unit/stage/candidate/endpoint/timestamp readings and mixed
endpoint or dose units *within a stage*, or mixed cost currencies, that have
not been harmonized explicitly. Different stages may legitimately use different
physical dose units (for example mg/L in the lab and g/ha in the field);
the audit does not convert or equate them.
Zero-dose controls and zero-cost observations are permitted. A repeated
measurement at a distinct timestamp is permitted; source-specific replicate
semantics must still be assessed before analysis.

## What the audit means

`audit_linked_discovery_evidence(records)` reports the observation count,
candidate count, stage counts and candidate identifiers represented at all
three stages. This is only a structural coverage check. Candidate linkage does
not demonstrate matched experimental protocols, comparable endpoint scales,
transportability, absence of confounding or identifiable causal effects.

An analyst must separately document candidate-name reconciliation, assay
comparability, treatment randomization, quality controls, missingness,
experimental-unit independence, cost allocation, site-season nesting,
provenance and decision-time availability. Freeze model-selection criteria and
hold out genuinely new field environments before examining their outcomes.

No user-provided or third-party field records are included in this repository
by this change. The tests use explicitly labelled synthetic metadata only.

## Use from Python

```python
from crop_protection_ps.discovery_evidence import (
    DiscoveryObservation,
    audit_linked_discovery_evidence,
)

records: list[DiscoveryObservation] = [
    DiscoveryObservation.model_validate(row) for row in external_rows
]
audit = audit_linked_discovery_evidence(records)
```

`external_rows` represents records acquired and reviewed through an authorized
scientific data source. There is intentionally no bundled example pretending
that synthetic lab, glasshouse and field outcomes are empirical observations.
