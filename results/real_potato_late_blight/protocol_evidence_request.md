# Original-source protocol request: potato late-blight trials

**Status:** Draft evidence request only. No investigator or data owner has been contacted.

**Public source:** Holst & Donner (2022), *Data from 18 fungicide trials on potato late blight in UK and Ireland 2013–2017*, [Zenodo 6352735](https://doi.org/10.5281/zenodo.6352735). Context: [IPM Decisions D4.8](https://www.ipmdecisions.net/media/vovnkaon/d4-8-selected-datasets-are-made-available-for-validation-of-dss-systems-by-other-end-users.pdf).

## Verified facts requiring interpretation

| Observation | Source-supported count | Unresolved interpretation |
| --- | ---: | --- |
| Published trials in deposit title | 18 | Physical/randomized trial identifiers are not provided |
| Geocoded site-year cells | 18 | Locations are rounded to 0.1°, so one cell need not equal one trial |
| Site-year × literal `Trial` code cells | 34 | Code-to-physical-trial mapping is unknown |
| Candidate trial × `Plot` keys | 602 | Plot, block and experimental-unit definitions are unknown |
| Original rows in each published format | 127,034 | Rows are not independent replicates |
| Exact-repeat excess rows | 118,021 | In 2016, 1,192 distinct row signatures each appear exactly 100 times |
| Candidate assessment keys with distinct values | 23 | Missing subsample identifiers or other semantics may explain them |

The original RData and TSV agree in all 1,270,340 ordered cells, so the binary is not an independent replication and does not resolve these questions. The published R workspace contains only `obs` and no hidden experiment or endpoint dictionary.

## Six evidence requests to the data owner or depositor

1. **P1 — Trial identity and experimental units.** Provide a machine-readable mapping from the advertised 18 physical trials to the available country/site/year/`Trial` codes, with unique (possibly pseudonymized) physical site, field, block and plot IDs. Explain the 34 site-year/code cells. Supply the randomization unit and design layout for each trial.
2. **P2 — 2016 record lineage.** Provide the original extraction/transformation steps, source row identifiers and any weighting, replication or join rules that explain why 1,192 full 2016 signatures each occur 100 times in *both* original files. State whether the copies should be retained, weighted, or excluded for each intended analysis; do not infer a rule from their equality.
3. **P3 — Assessment and subsample identity.** Provide the repeated-measurement schedule, sampling hierarchy (plants, leaves, plots and scoring visits as applicable), source observation/subsample IDs and a documented explanation for the 23 candidate same-key events with differing `Value` entries.
4. **P4 — Response dictionary.** Define `Value` by trial, date and assessment type: disease incidence/severity, yield or other outcome; units, scale, transformations, zero/missing codes, censoring and whether a separate endpoint identifier exists in the original collection system.
5. **P5 — Treatments and allocation.** Supply trial-specific `Treatment` codes, active substances/products, doses, application dates, schedule, controls and interpretation of `Untreated`. Document assignment to plots/blocks, including codes with different untreated status across trial groups.
6. **P6 — Protocol and reuse rights.** Supply the contemporaneous protocol, data dictionary, provenance of the published export, and explicit licence/permissions for analysis and any redistribution of original observations. Distinguish consent to publish the deposit from downstream reuse terms.

Where identifiers cannot be released, an anonymized crosswalk that preserves the experimental hierarchy and grouping would be sufficient for a methodological review. An explicit “not recorded / unavailable” answer is useful; it must not be replaced by an inferred key.

## Proposed decision rules after a response

- Verify the authenticity, version and scope of each supplied document and preserve source citations and checksums.
- Reconcile every published trial and record without editing the original Zenodo files. Report unresolved or many-to-many mappings explicitly.
- Only after the experimental unit, endpoint and intervention dictionary are verified, pre-register a specific estimand, dependence structure, and site/season-held-out validation design.
- If any necessary identity or endpoint remains unresolved, retain `requires_protocol`. No pseudo-replication, 2016 deduplication by assumption, fungicide rankings or spray recommendations.
- Evaluate data-reuse terms independently before copying any upstream records into this repository.

## Evidence trail

- [Source identity intake](../docs/real_case_potato_source_audit.md)
- [RData/TSV parity audit and protocol gates](../docs/real_case_potato_binary_parity.md)
- Derived, non-inferential summaries in `results/real_potato_late_blight/`

**Current decision:** The fourth candidate remains source-only; the three validated empirical field cases are unchanged. This document is a request template, not a claim that the original protocol has been obtained.
