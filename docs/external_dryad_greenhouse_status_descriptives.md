# Dryad greenhouse: descriptive disease-status frequencies

The original [Dryad pathogen-temperature dataset](https://doi.org/10.5061/dryad.4mw6m90jv)
contains scored seedling records from the greenhouse experiment. This export
exercises only the `disease_status_frequencies` permission in the
[analysis-eligibility contract](external_analysis_eligibility.md). The separate
death-case workbook is **not** joined to the infection table.

## What the unchanged source actually contains

| Source property | Verified observation |
| --- | ---: |
| Scored infection rows | 1,112 |
| Recorded visit/design cells | 852 |
| Excess fully identical records | 141 |
| Source experimental-year code `22` | 1,033 rows |
| Source experimental-year code `23` | 79 rows |
| Observer code `DC` | 1,107 rows |
| Observer code `SPS` | 5 rows |
| Nonblank optional comments | 0 |

The original `Disease Status` strings occur with these frequencies:

| Literal status | Recorded rows |
| --- | ---: |
| `D` | 171 |
| `HF` | 507 |
| `HM` | 325 |
| `LD` | 109 |

They are **source labels**, not an approved binary disease outcome. The
original source description says observations are plant scores, but provides
no stable plant identifier. Fully matching source records may be distinct
plants: all 1,112 are retained, and the 141 repeated-row excess is reported
explicitly. No deduplication, classification of healthy versus infected, or
independence claim is made.

The finest descriptive grouping retains `year`, `Date`, `Temperature`,
`Smut Exposure`, `Time`, `Rep`, and `Family` exactly as recorded. `Date` is
the original Excel serial string; `year` is the experimental-year code.
We do not infer that they establish a validated calendar timeline or a
causal temperature exposure. `NA` in `Time` or `Family` remains a literal
source code, not an imputed value.

Of the 852 visit cells, 667 contain one scored row and the others contain
two to seven. A visit cell is **not** a verified experimental or biological
replicate. The coarser strata retain year, temperature, exposure, and time,
with all `D`, `HF`, `HM`, and `LD` counts and the number of contributing
visit cells. They permit transparent inspection of the unbalanced recorded
design, but no proportions are presented as infection probabilities.

## Reproduce and verify offline

From the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.dryad_greenhouse_status_descriptives
PYTHONPATH=src python -m crop_protection_ps.dryad_greenhouse_status_descriptives --check
```

Source checksums, worksheet schema, per-table permission, and the earlier
experimental-unit audit are verified before producing:

- [`status_by_visit_cell.csv`](../results/external_dryad_greenhouse_status/status_by_visit_cell.csv),
  one row per recorded seven-field visit cell, including all four status counts.
- [`status_by_stratum.csv`](../results/external_dryad_greenhouse_status/status_by_stratum.csv),
  the 21 recorded year/temperature/exposure/time combinations.
- [`summary.json`](../results/external_dryad_greenhouse_status/summary.json),
  with source-level reconciliation, fingerprints, and scientific limitations;
  the detailed grouped records are in the CSVs to avoid duplicated exports.

The `--check` command makes no writes and rejects missing or stale outputs.
The tests also reject new status codes, changed source fields, invalid numeric
codes, and any attempt to bypass the descriptive eligibility permission.

## Before any inferential analysis

The protocol must establish unique plants or the unit of independence,
the interpretation of every disease-status code, and the family/replicate
clustering structure. These are separate requirements from date alignment.

The 173-row **death-case-only** workbook cannot be joined to this table by
nonunique metadata, and its rows do not provide an at-risk denominator or
event times suitable for mortality rates or survival analysis. Neither a
temperature-response model nor a causal disease-risk estimate is supported.
