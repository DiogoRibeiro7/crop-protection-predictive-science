# Dryad greenhouse: descriptive death-case tallies

The [original Dryad pathogen-temperature dataset](https://doi.org/10.5061/dryad.4mw6m90jv)
includes a separate greenhouse death-case workbook. Its rows record cases,
not an experimental cohort with both deaths and non-deaths. This export
exercises only `death_case_tally` under the
[analysis-eligibility contract](external_analysis_eligibility.md).

## Verified source structure

| Source property | Observation |
| --- | ---: |
| Original death-case records | 173 |
| Recorded seven-field case cells | 115 |
| Fully identical excess source rows | 58 |
| Distinct recorded date-serial labels | 7 |
| Experimental-year code `21` | 62 case rows |
| Experimental-year code `22` | 111 case rows |
| Recorded temperature label `24` | 35 case rows |
| Recorded temperature label `26` | 84 case rows |
| Recorded temperature label `30` | 54 case rows |
| Coarse year/temperature/exposure/time strata | 19 |

All **173** rows contain the literal field value `dead=1`. This is not a
numerator to be divided by the 1,112 observations in the *separate*
[infection-status workbook](external_dryad_greenhouse_status_descriptives.md).
The two files have different original column names and partially different
source `year` codes; neither provides a stable cross-file plant identifier.

The detailed tally retains `year`, `date`, `temperature`, `smut exposure`,
`time`, `replicate`, and `family`, including the original lowercase source
spelling. `date` stays a literal Excel serial and `year` stays a source
experimental-year code. A shared family or replicate value does **not**
establish a unique plant or an independent treatment assignment.

The 58 fully matching rows are reported but never removed. They may be
different dead plants with identical recorded metadata. Of the 115 case
cells, 81 contain one case, with the remaining cells containing two to nine.
The coarser 19 strata provide only counts of cases and contributing cells;
no rates, denominators, or survival times are generated.

## Offline reproduction

Run from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.dryad_greenhouse_death_descriptives
PYTHONPATH=src python -m crop_protection_ps.dryad_greenhouse_death_descriptives --check
```

The exporter validates the original file checksums, worksheet schema,
explicit per-table permission, and the previous experimental-unit audit.
It writes three deterministic files:

- [`cases_by_recorded_cell.csv`](../results/external_dryad_greenhouse_deaths/cases_by_recorded_cell.csv):
  one source case count for each seven-field cell, all repeated rows kept.
- [`cases_by_stratum.csv`](../results/external_dryad_greenhouse_deaths/cases_by_stratum.csv):
  19 coarse year/temperature/exposure/time strata with contributing cell counts.
- [`summary.json`](../results/external_dryad_greenhouse_deaths/summary.json):
  concise provenance, source counts, repeat multiplicities, and limitations.

The `--check` option is read-only and fails for missing or stale artifacts.
The tests also fail on unexpected columns, noncase `dead` values, invalid
date/replicate codes, permission denial, and changed grouped totals.

## Inferential analyses remain ineligible

This dataset cannot establish the **number of plants initially at risk**,
the **identity linking death and infection**, or the **time of death and
censoring** needed for a survival analysis. It cannot support a mortality
percentage, hazard ratio, differential death risk, or causal temperature
effect. The source protocol and independent validation must first resolve
those missing pieces; the `plant_death_risk_model` action remains gated.
