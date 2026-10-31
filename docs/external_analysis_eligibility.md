# Analysis eligibility of the original external research datasets

The table-level [eligibility contract](../data/external/analysis_eligibility.json)
records what the original source snapshots support **today**. It is a
conservative gate for downstream analysis proposals, not a general grant to
fit models or interpret effects. Its 18 assets correspond exactly to the
observation tables in the [structural profile](../data/external/PROFILE.md).
Workbook documentation sheets are deliberately excluded.

Each asset references one of ten policies. All permit a structural inventory;
the additional descriptive permissions, protocol requirements, and explicit
prohibitions are summarized below.

| Data family | Permitted description | Requires protocol review | Explicitly blocked example |
| --- | --- | --- | --- |
| Wheat field trial endpoints | Coverage of paired treated and untreated endpoints | Trial-level treatment effects: reconcile 56 published trials versus 76 `TrialId` codes, plots, treatment labels, endpoints | Treating 2,276 endpoint rows as independent trials |
| Aphid controlled experiments 1–4 | Mortality counts and denominators by recorded condition | Temperature–pesticide interaction: randomized exposure unit, batches, cluster/dispersion plan | Treating individual counted aphids as randomized units |
| Aphid experiment 5 (field) | Mortality-rate observations within provisional repeated series | Field treatment effects: plot/allocation protocol, dates, repeated measures | Treating 54 rows as independent plots or derived rates as integer death counts |
| Dryad germination/conjugation | Assay counts within recorded temperature/run structure | Temperature response: temperature allocation, chamber/run identity and clustering | Treating counted spores as randomized units |
| Dryad growth experiments | Colony counts within recorded temperature/run structure | Temperature response: nested replicates, strain/mating-type plan | Treating picture ID as a unique record ID |
| Dryad greenhouse infection | Frequencies of disease-status codes | Disease-risk model: plant independence, status codebook, family clustering | Linking infection and death cases through non-unique fields |
| Dryad greenhouse death cases | Count of recorded death-case rows | Plant death risk: at-risk denominator, unique linkage, event time/censoring | Calculating mortality rates from death-case-only records |
| Dryad longitudinal field plants | Within-plant recorded disease status by date | Longitudinal state model or temperature causal effect: codebook, dates, weather validation, identification design | Treating successive status cells as independent plants |
| Dryad flower summary | Aggregate recorded flowering series | Weather association: denominator, aggregation, date alignment | Recasting aggregate dates as new individual plants |
| Dryad weather | Missing/inconsistent source temperature checks | Weather exposure: resolve missing value and `Low > High`, align site/date | Using unverified weather as causal exposure |

## What the statuses mean

- `allowed`: a named descriptive check only. It does **not** imply that a
  sampling unit is randomized or observations are independent.
- `requires_protocol`: the stated research question is **not yet eligible**.
  The listed requirements must be resolved from source protocol evidence and
  reviewed before a new versioned contract explicitly changes policy.
- `blocked`: explicitly prohibited, unrecognized, or requested for an unknown
  dataset. There is no catch-all permission.

Group counts refer to *recorded labels or design cells*, not independent
experimental units. In particular, 76 wheat trial codes are not 76 proven
independent trials, 27 aphid field series are not verified randomized plots,
and 852 Dryad greenhouse infection design cells are not 852 distinct plants.
The three publications do not establish a common candidate identity for a
cross-study discovery funnel.

The [wheat geocode hierarchy audit](external_wheat_site_hierarchy.md) adds
evidence for the 56-versus-76 question: 56 recorded geocodes but 65
geocode–years and 76 trial codes. This finding does not clear the protocol
gate for trial-level inference.

The [cross-ID collision fingerprint audit](external_wheat_collision_fingerprints.md)
finds 22 exact pairwise record matches once `TrialId` is excluded. These are
not automatically duplicate plots; the source's allocation and replicate
protocol remain necessary.

The [Dryad longitudinal field-panel audit](external_dryad_field_panel.md)
confirms calendar-date alignment but shows mixed and unlisted status codes,
an incomplete `Ever.dis` field, and a reversed weather high/low measurement on
a field-visit date. These findings do not lift the field or weather protocol
requirements.

## Reproducible checks

Run from the repository root, with no network requests:

```bash
PYTHONPATH=src python -m crop_protection_ps.analysis_eligibility --check

PYTHONPATH=src python -m crop_protection_ps.analysis_eligibility \
  --dataset aphid_experiment_5_field \
  --analysis within_series_mortality_description

PYTHONPATH=src python -m crop_protection_ps.analysis_eligibility \
  --dataset dryad_greenhouse_death \
  --analysis plant_death_risk_model
```

The CLI emits a JSON decision; exit code `0` means allowed, `2` means gated or
blocked, and `1` means the evidence or contract is invalid. The validator
checks four checked-in SHA-256 report hashes, regenerates the existing
[source profile](../data/external/PROFILE.md),
[wheat pairability audit](external_wheat_pairability.md), and
[aphid/Dryad unit audit](external_aphid_dryad_units.md) against the original
source files, then checks table coverage, row counts, group claims, and
policy consistency. Changed inputs, missing tables, stale reports, or an
attempt to promote an inferential analysis to descriptive status cause failure.

Do not edit the policy file simply to bypass a `requires_protocol` result.
Resolve the documented scientific and design uncertainties first, and propose
a separately reviewed policy revision with source evidence and regression
tests. The current contract neither trains models nor alters source data.
