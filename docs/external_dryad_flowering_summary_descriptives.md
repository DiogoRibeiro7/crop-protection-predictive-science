# Dryad flowering-summary descriptions and source arithmetic checks

The original *High temperatures reduce growth, infection, and transmission of
a naturally occurring fungal plant pathogen* dataset
([Dryad DOI](https://doi.org/10.5061/dryad.4mw6m90jv), version 3) includes
the workbook `flower_summary_data.xlsx`. Its 27 rows summarize observations
across the original field plants. **They are visits, not newly sampled
individual plants or independent disease trials.**

The analysis exercises only the existing
`aggregate_flowering_description` permission for `dryad_flowering_summary`
in the [eligibility contract](external_analysis_eligibility.md). It does not
estimate a temperature effect or fit the source paper's longitudinal model.

## Reproduce and verify

Run from the repository root, without network access:

```bash
PYTHONPATH=src python -m crop_protection_ps.dryad_flowering_summary_descriptives
PYTHONPATH=src python -m crop_protection_ps.dryad_flowering_summary_descriptives --check
```

The command validates the checksum-pinned source manifest and the analysis
contract, loads the unchanged worksheet with the existing OOXML reader,
aligns its dates to the audited longitudinal field panel, and checks the
previous field-panel report for staleness. `--check` compares all output
bytes and never writes.

## Exported records

| Artifact | Contents |
| --- | --- |
| [`source_flowering_visits.csv`](../results/external_dryad_flowering_summary/source_flowering_visits.csv) | All 27 dates, 29 original source columns, Excel date serials and `days` strings, plus aligned `calendar_date` and `visit_order`. Original numeric representations, weather-like fields and blanks are preserved verbatim. |
| [`source_arithmetic_checks.csv`](../results/external_dryad_flowering_summary/source_arithmetic_checks.csv) | Per-visit checks of source component totals and reported rounded ratios. Outcomes are `agrees`, `disagrees`, or `not_recorded`, never imputed scores. |
| [`summary.json`](../results/external_dryad_flowering_summary/summary.json) | Provenance, date range, flags, nonblank cell counts, check tallies and limitations; raw visit records appear only in CSV. |

The original source distinguishes two measurement layers:

| Source measurement | Visits with source values |
| --- | ---: |
| `Flwr.plants`, `Fully.Smutty.plants`, `Partial.dis`, `any.disease` | 27 of 27 |
| `Prop.any.dis`, `prop.flwr` | 27 of 27 |
| `Flwer.data=1`: detailed flower measurements | 19 of 27 |
| `total.D.flwr`, `total.H.flwr`, `proportion` | 19 of 27 |
| `Flwer.data=0`: no detailed flower measurements | 8 of 27 |
| `total`: recorded zero on seven of the above unmeasured visits, blank on one | 26 of 27 overall |

Those empty detailed-flower cells are **not zeros**. In particular, an
unmeasured detailed flower total must not be conflated with the nonzero
number of flowering plants on the same source date.

The source uses the literal spelling `Flwer.data`; it is preserved. The
converted date axis runs from 17 May through 18 November 2021, with the
calendar correspondence verified against the previous
[field-panel audit](external_dryad_field_panel.md).

## Reconciliation, not inference

With the source count of 178 original field plant rows used strictly as a
check denominator, the committed summary finds:

| Source arithmetic | Matching rows | Not recorded |
| --- | ---: | ---: |
| `total.D.flwr + total.H.flwr = total` | 19 | 8 |
| `total.D.flwr / total ≈ proportion` | 19 | 8 |
| `Fully.Smutty.plants + Partial.dis = any.disease` | 27 | 0 |
| `any.disease / Flwr.plants ≈ Prop.any.dis` | 27 | 0 |
| `Flwr.plants / 178 ≈ prop.flwr` | 27 | 0 |

The original proportions are rounded. Comparisons use an absolute tolerance
of `0.00501` for `proportion` (two decimal places) and `0.00051` for
`Prop.any.dis` and `prop.flwr` (three decimal places). A discrepancy would be
**reported** rather than corrected. These equalities document how values
appear to have been constructed; they do not establish independent
denominators, event or censoring rules, or model validity.

The original worksheet also contains `high`, `low`, moving-temperature
summaries, precipitation and evaporation columns. These remain **literal
source strings** in the export. The separate weather record has documented
missing and reversed high/low readings; no station/site exposure alignment,
weather association or causal estimate is attempted here. Those questions
remain [protocol-gated](external_analysis_readiness.md).
