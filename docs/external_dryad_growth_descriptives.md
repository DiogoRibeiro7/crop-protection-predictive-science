# Dryad laboratory growth: descriptive colony-count exports

The [Dryad source dataset](https://doi.org/10.5061/dryad.4mw6m90jv)
contains one-week colony-count assays for three fungal strains. These
workbooks are distinct from the [germination and conjugation count assays](external_dryad_lab_assay_descriptives.md),
the greenhouse experiments, and longitudinal field observations.

The [analysis-eligibility contract](external_analysis_eligibility.md) permits
`colony_count_description` for these three strain-specific tables. Temperature
response models still require documented chamber allocation, nested
replication, and a strain/mating-type analysis plan.

## Source structure and reconciliation

All three workbooks have 168 recorded observations across 14 temperatures,
two recorded `Temp.Rep` levels, and two `Mating.Type` labels (`A1`, `A2`).
Each strain × temperature × temperature-replicate × run × mating-type cell
contains three rows labelled `Replicate` 1–3.

| Source workbook | Rows | Temperature/run groups | Strain/run/mating cells | Recorded colony total |
| --- | ---: | ---: | ---: | ---: |
| Growth, strain 2 | 168 | 28 | 56 | 5,729 |
| Growth, strain 3 | 168 | 30 | 56 | 4,437 |
| Growth, strain 4 | 168 | 28 | 56 | 4,940 |

The 504 original rows record 15,106 colonies in total. These are **counts
of observed colonies**, not numbers of independent experimental units.
The original source field is spelled `Colonly.Count`, and the exporter uses
that literal name during validation to avoid an undocumented schema change.

Strain 3 has **30** temperature/run combinations, rather than 28. Four
combinations have three rows and 26 have six because some mating-type records
carry different `Run.Num` labels. Summarizing by the five-field key retains
the 56 distinct strain/run/mating cells without forcing the run codes to
match across mating types.

### The `Picture ID` collision

Each 168-row workbook has only 84 distinct `Picture ID` strings: 84 rows
repeat a label used elsewhere, commonly across recorded temperature
replicates. Those repeated labels do not prove duplicate biological
observations. The exporter keeps **all 168 rows per strain**, records every
original picture label within its group, and publishes the collision count.
It never uses `Picture ID` alone to identify a sample or discard a row.

The per-cell summary contains:

- The literal `Strain`, `Temperature`, `Temp.Rep`, `Run.Num`, and `Mating.Type`
  fields.
- Original replicate and picture-ID labels for traceability.
- Source row count, total observed colonies, and the arithmetic mean,
  minimum, and maximum **per recorded source row**.

These means are descriptive summaries, **not** independent treatment
replicates, effect sizes, or fitted temperature curves. Strains and mating
types are not pooled; the two recorded temperature-replicate labels and the
run codes are not assumed to identify independent growth chambers.

## Reproduce and verify

Run offline from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.dryad_growth_descriptives
PYTHONPATH=src python -m crop_protection_ps.dryad_growth_descriptives --check
```

The program validates original-file checksums, table-specific analysis
permissions, source worksheet names, nested records, picture-ID collisions,
and agreed row/group counts before generating these files:

- [`summary.json`](../results/external_dryad_growth/summary.json), including
  source fingerprints, collision counts, all grouped records, and caveats.
- [`strain_2_mating_type_runs.csv`](../results/external_dryad_growth/strain_2_mating_type_runs.csv)
- [`strain_3_mating_type_runs.csv`](../results/external_dryad_growth/strain_3_mating_type_runs.csv)
- [`strain_4_mating_type_runs.csv`](../results/external_dryad_growth/strain_4_mating_type_runs.csv)

The `--check` operation compares against the checked-in artifacts without
writing files. Changes in the source schema, counts, grouping, permissions,
or report contents cause a failure.

Before fitting a growth-response model, source protocol evidence must
establish temperature assignment, run/chamber dependence, the role of
`Mating.Type`, and the meaning and reuse of `Picture ID`.
