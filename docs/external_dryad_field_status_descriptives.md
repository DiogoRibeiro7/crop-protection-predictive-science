# Within-plant field-status descriptions: Dryad pathogen observations

These exports retain the original longitudinal status records from
[*High temperatures reduce growth, infection, and transmission of a naturally
occurring fungal plant pathogen*](https://doi.org/10.5061/dryad.4mw6m90jv),
Dryad version 3, without constructing a disease outcome or fitting a model.
They exercise only the pre-existing `within_plant_status_description`
permission for `dryad_field_plants` in the
[analysis eligibility contract](external_analysis_eligibility.md).

Run from the repository root. Neither command needs network access:

```bash
PYTHONPATH=src python -m crop_protection_ps.dryad_field_status_descriptives
PYTHONPATH=src python -m crop_protection_ps.dryad_field_status_descriptives --check
```

The implementation validates the checksum-pinned source manifest, analysis
contract and [existing field-panel audit](external_dryad_field_panel.md)
before exporting anything. `--check` compares the complete generated files
with their committed counterparts and never writes to disk. An invalid
permission, stale audit, duplicate plant key or unexpected measurement-date
column fails the export.

## Reproducible outputs

| File | Grain | Contents |
| --- | --- | --- |
| [`plant_visit_status.csv`](../results/external_dryad_field_statuses/plant_visit_status.csv) | One **recorded visit** of one source plant | Source sheet row index, `Row`/`Position` plant key, 1–27 visit order, 2021 calendar date, original `Status.*` and `Infect.status.*` header names, and their exact unmodified strings. |
| [`status_labels_by_visit.csv`](../results/external_dryad_field_statuses/status_labels_by_visit.csv) | One **literal label** in one field on one visit | Counts of source plant rows with that label. Empty strings have explicit count rows; each visit/field has 178 plant records as its structural denominator. |
| [`summary.json`](../results/external_dryad_field_statuses/summary.json) | Source-level audit metadata | Permission, file/report checksums, original unit counts, literal status vocabulary counts, and limitations. Row-level records are held only in CSV. |

The source workbook holds 178 plant records, identified within the sheet by
unique `(Row, Position)` pairs. Each record has 27 raw-status measurements
and 27 parallel infection-status cells dated 17 May–18 November 2021. Thus:

| Measure | Original records |
| --- | ---: |
| Source plants | 178 |
| Dated visits per plant | 27 |
| Plant–visit records | 4,806 |
| Populated raw-status cells | 4,795 |
| Blank raw-status cells | 11 |
| Populated infection-status cells | 2,944 |
| Blank infection-status cells | 1,862 |

The 4,806 plant–visit rows **do not represent 4,806 independent plants**.
All 27 rows for a particular `(Row, Position)` retain the same plant key and
the original source-sheet row index. Counts by visit are observational
frequencies, not independent Bernoulli trial denominators or disease risks.

## Source labels and dates

- Raw labels are literal, including unlisted strings such as `H`, `D/H`,
  and annotated forms. The infection-status column's `F` is also retained.
  We do **not** convert either field to a healthy/diseased indicator.
- Empty source values remain empty CSV fields. No interpolation, imputation,
  or replacement by `0`, `healthy`, or `NA` is performed.
- The source's `Status.Spet.24` header remains exactly that string in CSV,
  while its aligned calendar date is explicitly `2021-09-24`. The date axis
  is validated against the original flower-summary workbook.
- The incomplete `Ever.dis` column is never read as an outcome; the separate
  flowering-summary and daily-weather worksheets are not joined to individual
  plant statuses to make exposure or effect claims.

The existing [field-panel audit](external_dryad_field_panel.md) documents
the incomplete codebook and weather anomalies (including a high/low reversal
on 31 August 2021). Those gaps remain unresolved by these exports.

## Inference not supported

The files do not establish whether `X` is an absorbing state or whether
compound status labels should be classified as infections. They also do not
establish a risk set or censoring mechanism for each plant and date.
Accordingly, these exports estimate **no** transition matrix, time-to-event
quantity, infection probability, temperature effect, or causal relationship.
Any such analysis remains subject to the protocol and codebook prerequisites
in the [eligibility contract](external_analysis_eligibility.md).
