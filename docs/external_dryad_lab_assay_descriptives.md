# Dryad laboratory germination and conjugation: descriptive count exports

The [original Dryad dataset](https://doi.org/10.5061/dryad.4mw6m90jv)
reports fungal germination, conjugation, and colony growth under varying
temperatures. This export covers **only the four count-based laboratory
workbooks**: germination and conjugation of strains 2, 3, and 4. Growth
colony counts, greenhouse plants, field observations, and weather remain
separate source designs.

The [analysis-eligibility contract](external_analysis_eligibility.md)
explicitly permits `assay_count_description` for these four assets. Fitting a
temperature-response model still requires evidence about chamber/run
allocation, temperature-replicate independence, and within-run clustering.

## Verified structure

Each workbook has 14 recorded temperatures from 4 to 30 °C, two recorded
`Temp.Rep` labels per temperature, and three assay `Rep` rows per recorded
(`Temperature`, `Temp.Rep`, `Run.Num`) group. The grouping key is descriptive;
it does not identify 28 independent treatment assignments.

| Original workbook | Source assay rows | Temperature/run groups | `Sum.Total` | Recorded successes |
| --- | ---: | ---: | ---: | ---: |
| Germination | 84 | 28 | 11,174 | 6,774 (`Sum.Germ`) |
| Conjugation, strain 2 | 84 | 28 | 30,908 | 9,101 (`Sum.Mating`) |
| Conjugation, strain 3 | 84 | 28 | 30,145 | 8,264 (`Sum.Mating`) |
| Conjugation, strain 4 | 84 | 28 | 26,479 | 7,010 (`Sum.Mating`) |

The 336 assay rows contain 98,706 counted observations in their source
denominators. These are **not** 98,706 randomized experimental units. Source
`Rep` values are retained, and repeated run codes across temperatures are
not treated as unique global chamber or batch identifiers.

For each temperature/run grouping, the exported fraction is

\[
\widehat{p}_{\mathrm{recorded}} =
\frac{\sum_{r}\mathrm{successes}_{r}}{\sum_{r}\mathrm{Sum.Total}_{r}}.
\]

This is a count-weighted *descriptive* fraction, not the mean of row
percentages and not a fitted probability. Each row's `Sum.Prop` is first
checked against the original integer numerator and denominator. The export
also records the minimum and maximum published row fractions within each
group so that aggregation does not conceal the source spread.

No results are pooled across germination and conjugation, or across strains.
There are no temperature-effect contrasts, confidence intervals, p-values,
or models. The 28 groups per workbook and three source rows per group cannot
be interpreted as 84 independent experimental replicates without the protocol.

## Reproducible export

Run from the repository root without network access:

```bash
PYTHONPATH=src python -m crop_protection_ps.dryad_lab_assay_descriptives
PYTHONPATH=src python -m crop_protection_ps.dryad_lab_assay_descriptives --check
```

The command checks original workbook fingerprints, eligibility permissions,
worksheet names, source counts, recorded proportions, nested replicate keys,
and expected group counts. The five deterministic outputs are:

- [`summary.json`](../results/external_dryad_lab_assays/summary.json):
  provenance, source/eligibility fingerprints, per-assay group details, and
  scientific limitations.
- [`germination_temperature_runs.csv`](../results/external_dryad_lab_assays/germination_temperature_runs.csv)
- [`conjugation_strain_2_temperature_runs.csv`](../results/external_dryad_lab_assays/conjugation_strain_2_temperature_runs.csv)
- [`conjugation_strain_3_temperature_runs.csv`](../results/external_dryad_lab_assays/conjugation_strain_3_temperature_runs.csv)
- [`conjugation_strain_4_temperature_runs.csv`](../results/external_dryad_lab_assays/conjugation_strain_4_temperature_runs.csv)

The `--check` option is read-only and fails if reports are missing or stale.
Unexpected schemas, invalid counts, duplicate assay replicate labels, source
changes, or revoked descriptive permission also cause failure.

Before any model of heat response, the study protocol must establish
allocation and clustering: which exposure chambers were independently
assigned a temperature, how `Temp.Rep` and `Run.Num` relate to physical
runs, and whether the three `Rep` rows are nested subsamples.
