# Aphid field follow-up: paired descriptive observations

This export describes the fifth worksheet (`Experiment5`) of the original
[aphid pesticide and temperature dataset](https://doi.org/10.5281/zenodo.19805135).
It is separate from the [four controlled-experiment condition tables](external_aphid_controlled_descriptives.md).
The original file is subject to the checked-in integrity manifest and
[analysis-eligibility contract](external_analysis_eligibility.md). The existing
`within_series_mortality_description` permission allows recording changes in
the published rates; field treatment-effect estimation still requires the
allocation, plot, and follow-up protocols.

## What is recorded

The workbook contains 54 rows. Grouping by the literal labels `Site`,
`Treat`, `Replicate`, `Date`, and `Interval` yields 27 provisional series.
Each has one `Day3_postpesticide` and one `Day7_postpesticide` record. The
source population baseline and pesticide/heat fields agree within each pair.

| Descriptive audit | Observed value |
| --- | ---: |
| Original field records | 54 |
| Provisional two-visit series | 27 |
| Langfang / Xinxiang series | 18 / 9 |
| Treatment-label A / B / C series | 6 / 9 / 12 |
| Series with fractional `Base_number` | 22 |
| Day-7 minus day-3 recorded mortality: positive / zero / negative | 25 / 2 / 0 |
| Pairs sharing one source `Date` serial | 27 |

The output retains every composite-key field, source exposure field, and
original `PopSize`, `Base_number`, and `Mortality` string for both visits. The
only new numeric field is `Day7_minus_Day3_Mortality`, computed as
`Day7_Mortality - Day3_Mortality` and rounded to ten decimal places. It is a
*within-series descriptive difference*, not a treatment contrast. There are
no mean-effect estimates, p-values, credible intervals, synthetic controls,
cluster corrections, or fitted models in this export.

### Why the source dates remain unconverted

The original README calls `Date` a sampling date. Yet the two nominal
visits of each recorded pair share the **same** source date serial. Langfang
has serials `45082` and `45083`; Xinxiang has `41414`. The export preserves
these strings exactly. They may represent an assignment date or a source
coding error; the source does not establish which. We neither infer a
four-day elapsed calendar interval from those serials nor silently correct
their discrepancy.

### Why rates are not binomial counts

The source uses `Mortality = 1 - PopSize / Base_number` to source rounding.
`Base_number` is fractional in 44 of 54 source rows, and `PopSize` is
fractional in 34. These are not the controlled experiments' integer `DEAD`
and `TOTAL` records. Neither the 54 row count nor the 27 provisional series
count establishes the number of independent randomized field plots.

The `Treat` values `A`, `B`, and `C` are kept as literal labels; they are
not recoded into dose, treated/control, or causal-assignment categories.

## Reproduce and verify

Run offline from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.aphid_field_pairs
PYTHONPATH=src python -m crop_protection_ps.aphid_field_pairs --check
```

The module first verifies the original source checksums and the restrictive
eligibility contract. It then writes two deterministic checked-in artifacts:

- [`results/external_aphid_field/summary.json`](../results/external_aphid_field/summary.json):
  source/contract fingerprints, audit counts, source date serials, caveats,
  and the literal series records.
- [`results/external_aphid_field/paired_series.csv`](../results/external_aphid_field/paired_series.csv):
  one ordered row per provisional series with both observed visits.

The `--check` mode only compares expected outputs to the committed files; it
does not change them. Missing/stale exports, invalid grouping, unexpected
source changes, or a revoked eligibility permission cause failure.

The next analytical gate is **protocol reconciliation**, not a regression:
identify physical plots and treatment assignment, explain whether `Date`
is a visit or baseline label, establish how populations were averaged, and
confirm which observations can be treated as independent experimental units.
