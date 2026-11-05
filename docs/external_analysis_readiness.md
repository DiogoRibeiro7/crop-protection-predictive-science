# Research readiness: what is descriptive, what remains gated

This inventory is an operational companion to the
[analysis eligibility contract](../data/external/analysis_eligibility.json),
not a new approval policy. It answers three different questions:

1. Which **source-verified descriptive actions** are permitted now?
2. For which permitted actions do committed, metadata-crosschecked outputs exist?
3. Which proposed inferential questions still require protocol evidence, and
   which operations are explicitly blocked?

Run offline from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.external_analysis_readiness
PYTHONPATH=src python -m crop_protection_ps.external_analysis_readiness --check
```

The source profile, unit audits, and analysis contract are validated again
before this ledger is generated. Existing descriptive reports are checked
against their policy, recorded source rows, grouping counts, manifest hash,
and contract hash where the report includes them. A shared report must cover
**every** source sheet under its policy, not just one convenient example.
The full original-source regeneration is still owned by each report's test
suite; a matching summary alone is not an experimental-unit proof.

## Current boundaries

| Status | Recorded result | Meaning |
| --- | ---: | --- |
| Source observation tables | 18 | Complete, audited original-data coverage across ten policy families. |
| Permitted source-level descriptive actions | 36 | One structural inventory and one scoped descriptive action per source table. |
| Permitted actions with crosschecked committed reports | 35 | Includes 18 common structural inventories and 17 additional scoped descriptions. |
| Permitted descriptions without standalone exports | 1 | Dryad source weather quality. It may be implemented without changing permission. |
| Protocol-gated inferential questions | 19 | Each currently requires an explicit, separately reviewed policy revision. |
| Recorded prerequisite checklist entries | 59 | Repeated per source table where experiments share a policy; **not** 59 independently verified gaps. |
| Explicitly blocked source/action combinations | 34 | Examples include treating repeated observations as independent replicates and invalid cross-publication joins. |

The report distinguishes **permission** from **implementation**. A permitted
description without an export remains permitted; a tested descriptive export
does not authorize a treatment effect or causal model. A protocol prerequisite
marked `not_cleared_by_contract` means no current clearance; it does not
prove that the underlying paper or authors lack the information.

## Reproducible artifacts

| Output | Unit of each row | Purpose |
| --- | --- | --- |
| [`allowed_descriptives.csv`](../results/external_analysis_readiness/allowed_descriptives.csv) | Source table × permitted action | Recorded source rows/groups, permitted action, report path and implementation status. |
| [`protocol_requirements.csv`](../results/external_analysis_readiness/protocol_requirements.csv) | Source table × proposed question × prerequisite | A review checklist. No gate is automatically marked resolved. |
| [`blocked_analyses.csv`](../results/external_analysis_readiness/blocked_analyses.csv) | Source table × explicitly prohibited operation | Guards against pseudo-replication, false source linkage and unsupported conversions. |
| [`summary.json`](../results/external_analysis_readiness/summary.json) | Inventory metadata | Counts, source/contract hashes and statistical limitations; detailed rows live only in CSV. |

`--check` is read-only and fails if any of these committed files are absent
or stale. New policy families, discrepancies in reported source units, and
unexpected promotion of gated actions fail closed.

## Scientific questions we can address now

The following are observational descriptions, not causal answers:

- Wheat: treatment/untreated endpoint matching, coverage and data quality
  across recorded trial codes, without treating all endpoint rows as trials.
- Aphid experiments 1–4: recorded mortality totals and denominators by
  temperature/concentration **condition**, without claiming independently
  randomized aphids or a temperature–pesticide interaction.
- Aphid experiment 5: paired day-3/day-7 source-rate descriptions within
  provisional series, without trial-effect identification.
- Dryad laboratory, colony growth and greenhouse infection/death files:
  count and status descriptions at their recorded units, without inventing
  independent chamber replicates, plant identities, or risk denominators.
- Dryad field: literal status histories for 178 plants on 27 aligned visits,
  retaining mixed code labels and blanks; no disease transition probabilities.

The [Dryad flowering-summary export](external_dryad_flowering_summary_descriptives.md)
now also covers 27 visit-level source aggregates and reports arithmetic
agreement for the recorded component sums and rounded proportions.

The remaining **already allowed** descriptive deliverable is:

1. Dryad weather-quality review (214 source dates): isolate missing and
   reversed high/low records, retain source values, and avoid interpreting
   an unverified station/site series as plant-level causal exposure.

## Protocol requests before inferential work

These questions are useful, but currently not identifiable or sufficiently
validated from the committed evidence alone:

| Research question | Evidence or clarification to request |
| --- | --- |
| Wheat treatment efficacy across trials | Reconcile the paper's 56 trials with 76 recorded `TrialId` codes; define physical plots, randomized treatment labels, repeats and endpoint semantics. |
| Aphid temperature × pesticide response | Identify randomized exposure units, run/batch or chamber structure, replicate identities, and an analysis plan for clustering/overdispersion. |
| Aphid field treatment effect | Recover field plot allocation, observation dates, source rate definitions and within-series dependence; cannot use 54 rows as independent plots. |
| Dryad laboratory temperature effects | Establish chamber/run assignment and biological versus technical replicates for germination, conjugation and colony growth. |
| Dryad greenhouse disease and death risk | Clarify status codebook, unique plant identities, family/replicate structure, true at-risk denominators, and event/censoring definitions; the case-only death file cannot supply its own denominator. |
| Dryad field disease transitions | Resolve the mixed status codes, whether `X` is terminal, event/censoring semantics and plant-history timing. Calendar alignment alone does not resolve the transition model. |
| Dryad field and flowering weather relationships | Resolve missing/reversed temperature readings, measurement station/site linkage, aggregation denominators, lag choices, confounding and causal identification design. |

Even after collecting one prerequisite, the full applicable set must be
reviewed before changing the eligibility contract. The inventory does not
propose a cross-publication candidate identity, pooled fungicide-effect
meta-model, or causal result from a shared temperature label.
