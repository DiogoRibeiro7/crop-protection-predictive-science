# Candidate source intake: NSW barley Ramularia field trials (2024–2025)

**Status:** Publisher-metadata discovery only; original XLSX/PDF bytes have **not** yet been audited. This is a potential additional independent empirical case, not a validated case or treatment-effect result.

## Publisher and original resources

NSW Department of Primary Industries (DPI), GRDC project DPI2310-004RTX, *Understanding the epidemiology of Ramularia in barley*. The [Data.NSW dataset landing page](https://data.nsw.gov.au/data/dataset/ramularia-leaf-spot-disease-in-barley) describes these resources, last updated 24 June 2026.

| Resource | Publisher resource ID | Published type | Purpose |
| --- | --- | --- | --- |
| [Trial details](https://data.nsw.gov.au/data/dataset/ramularia-leaf-spot-disease-in-barley/resource/e8bdab44-6116-4af6-be8e-391ade9b6af6) | `e8bdab44-6116-4af6-be8e-391ade9b6af6` | XLSX | Trial/site/year and design metadata |
| [Plot-level measurements](https://data.nsw.gov.au/data/dataset/ramularia-leaf-spot-disease-in-barley/resource/22b96115-c36c-4789-9323-235d347d0193) | `22b96115-c36c-4789-9323-235d347d0193` | XLSX | Disease, pathogen DNA, yield and grain-quality responses |
| [Original methods](https://data.nsw.gov.au/data/dataset/ramularia-leaf-spot-disease-in-barley/resource/ebca632f-2511-44f0-b87c-a3a1493259c2) | `ebca632f-2511-44f0-b87c-a3a1493259c2` | PDF | Split-plot design, allocation, treatment rates/times, assessments and analyses |
| [Airborne spore monitoring](https://data.nsw.gov.au/data/dataset/ramularia-leaf-spot-disease-in-barley/resource/326ebc11-e0f2-40b6-98bf-235770264e79) | `326ebc11-e0f2-40b6-98bf-235770264e79` | XLSX | Potential external inoculum context; not automatically plot-level or pre-treatment |

The publisher labels the resources **Creative Commons Attribution**; exact reuse terms and attribution should be checked against downloaded files and applicable licence version before redistribution. This PR records links rather than vendoring source bytes.

## Metadata-backed design claims (not independently checked yet)

Four field-plot trials at Wagga Wagga Agricultural Institute, Australia:

| Trial code | Year | Environment |
| --- | --- | --- |
| `FPB245WIR` | 2024 | Irrigated |
| `FPB255WIR` | 2025 | Irrigated |
| `FPC245WIR` | 2024 | Rainfed |
| `FPC255WIR` | 2025 | Rainfed |

The publisher describes a DiGGer-generated **split-plot** design, two genotypes (RGT Planet and Spartacus CL), and six fungicide schedules including a nil control. The measurement file is described as **240 rows, one per plot**, with identifiers for trial/site/year, replicate, block, main plot and subplot. Outcomes include repeated ordinal and percentage disease severity, qPCR pathogen DNA, yield/biomass, and grain quality. Repeated assessment columns use numbered suffixes. The publisher's methods PDF describes timing, inoculation and statistical procedures.

These are stronger upfront design resources than the unresolved potato source, but they do **not** establish a particular independent unit or causal estimand without cross-checking the layout, allocation and missingness in the original files.

## Required reproducible intake before modelling

1. Download the three core originals (trial details, measurement XLSX and methods PDF) into a local cache; record final source URLs, download date, byte size, SHA-256 and any publisher checksums. Preserve the exact files unchanged.
2. Inspect actual worksheet names, schemas, datatypes, null codes, row totals and duplicate plot keys. Reconcile all 240 advertised plot rows to the four trial IDs; fail closed on unjoined records.
3. Verify the randomization and nesting structure from the methods PDF and data columns: which factor is assigned at main-plot versus subplot level, replication/block identities, and whether plot IDs recur across trials.
4. Build a treatment mapping for each trial and application date; distinguish planned treatments, actual application and any protocol deviations.
5. Inventory endpoints, units, detection limits, qPCR weights, missingness, assessment-time suffixes and any pre/post-treatment availability restrictions.
6. Assess leakage risks: trial-level `Year` and irrigation are confounded with trial environments; derived endpoints, quality scores and same-plot repeated measures must not leak into validation folds.
7. Freeze a first estimand and design-aware comparison **before** inspecting treatment effects. With only four environments, report within-trial inference separately from any exploratory held-out-trial transport results; do not claim broad predictive generalization.

## Candidate analysis sequence (conditional)

- **Gate A:** source integrity, licence, join keys and row-unit hierarchy reconciled.
- **Gate B:** descriptive trial balance, missingness and assessment timelines without treatment-effect testing.
- **Gate C:** prespecified within-trial split-plot treatment contrasts with the correct error strata, if randomization is verified.
- **Gate D:** exploratory between-environment robustness and genotype/treatment interaction sensitivity; explicitly acknowledge four-trial scope.

This work must not reopen the frozen six-environment Bipolaris model-selection programme or change the existing three validated empirical case count merely because a new publisher page was found.

## Secondary lead

Espino, Brim-DeForest & Greer (2026), [California rice stem rot fungicide trials](https://doi.org/10.5061/dryad.j3tx95xxf), Dryad, describes 19 randomized complete-block trials and plot-level disease/yield fields. This is a separate candidate for later assessment, **not** yet checked against downloaded rows or licensing details.
