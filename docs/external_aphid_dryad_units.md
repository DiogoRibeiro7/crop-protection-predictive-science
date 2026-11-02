# Aphid and fungal-pathogen data: experimental-unit audit

This read-only audit examines the original workbooks from two independent
studies:

- [Aphid pesticide and heat experiments](https://doi.org/10.5281/zenodo.19805135)
  (Zenodo 19805135).
- [Fungal-pathogen temperature experiments](https://doi.org/10.5061/dryad.4mw6m90jv)
  (Dryad 4mw6m90jv).

The aim is to identify observational records, assay replicates, repeated
measurements, and the grouping metadata necessary for statistical inference.
It does **not** fit models, calculate treatment effects, or declare the number
of independently randomized units.

Run from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.aphid_dryad_units
```

Check the committed report without writing any file:

```bash
PYTHONPATH=src python -m crop_protection_ps.aphid_dryad_units --check
```

The program validates the external-source checksum manifest, reads original
OOXML cached cell values and TSV rows, then writes
[`results/external_aphid_dryad_units.json`](../results/external_aphid_dryad_units.json).
No workbook is changed, no formula is evaluated, and identical observation
rows are preserved. The report contains only aggregate counts, factor names,
source date serials, and source-provenance metadata.

## Aphid experiments

The source readme identifies five distinct experiments. Experiments 1–4
contain `TOTAL` and `DEAD` counts; Experiment 5 has a different field design.

| Experiment | Rows | Distinct recorded conditions | Records per condition |
| --- | ---: | ---: | --- |
| 1: temperature × pesticide concentration | 36 | 12 | 3 each |
| 2: temperature × concentration × exposure duration | 24 | 8 | 3 each |
| 3: temperature × concentration × duration × interval × order | 180 | 48 | 40 conditions × 3, 4 × 6, 4 × 9 |
| 4: temperature × concentration × duration × interval | 36 | 12 | 3 each |

All **276 controlled records** have positive integer `TOTAL` values and
integer `DEAD` counts between zero and `TOTAL`. In aggregate, they count
**8,111 aphids**, but this is an individual-animal denominator, not a count of
independent treatments or exposure chambers. The four sheets lack explicit
replicate or batch identifiers. Even within a condition, rows should not be
assumed independent treatment assignments without the original protocol.
Experiment 3 has uneven recorded multiplicity, so assuming exactly three
replicates per treatment is demonstrably incorrect.

The [controlled-aphid descriptive exports](external_aphid_controlled_descriptives.md)
provide one condition-level CSV per controlled experiment, including counts,
observed cohort-rate ranges, and literal source time/dose labels. They do not
grant an inferential analysis or combine the field design with laboratory
counts.

### Field follow-up structure

Experiment 5 contains **54 rows** but only **27 provisional observational
series** when keyed by:

`Site`, `Treat`, `Replicate`, `Date`, and `Interval`.

Each series has exactly one observation at day 3 and one at day 7. All 27
retain a constant recorded baseline population and heat/pesticide exposure
within the series. The same replicate labels can recur at different intervals,
so `Replicate` alone is **not** a unique series identifier. This composite key
is a practical repeated-measure identifier, pending confirmation of actual
field plot or sampling units in the source protocol.

The `Mortality` field agrees, within source rounding, with
`1 - PopSize / Base_number`. It is a **derived field rate**, not a second
independent outcome. `Base_number` is fractional in 44 of the 54 rows, and
`PopSize` is fractional in 34. The field outcome must therefore not be
forced into the integer binomial `DEAD`/`TOTAL` likelihood used for the
controlled experiments.

The Excel date serials differ sharply by site: Langfang uses `45082`–`45083`,
while Xinxiang uses `41414`. These raw serials are preserved in the audit.
They need source-level validation before treating the records as a common
calendar-period field trial; this report does not silently amend the dates.

The [paired field-follow-up exports](external_aphid_field_pairs.md) preserve
all 27 provisional day-3/day-7 series and their reported mortality-rate
differences. They also flag that each pair's nominal visits have the same
recorded source `Date` serial. These are descriptive changes, not pesticide
effect estimates or verified independent plots.

## Dryad pathogen experiments

### Laboratory assays

The seven laboratory workbooks contain temperature and within-run replicate
labels. Each uses **14 tested temperatures**, with two recorded
`Temp.Rep` levels per temperature. The `Rep` or `Replicate` fields provide
three records per relevant assay condition.

| Dataset | Rows per workbook | Temperature/run groups | Records per group |
| --- | ---: | ---: | --- |
| Germination | 84 | 28 | 3 |
| Conjugation, each of strains 2–4 | 84 | 28 | 3 |
| Growth, strains 2 and 4 | 168 | 28 | 6 (two mating types × three records) |
| Growth, strain 3 | 168 | 30 | 26 groups × 6 and 4 groups × 3 |

The strain-3 growth file has 30 distinct
(`Temperature`, `Temp.Rep`, `Run.Num`) combinations because some mating-type
records carry different run codes. This is not a reason to drop observations
or force an artificial 28-group structure.

For germination and conjugation, all count denominators are positive,
numerators are within their denominators, and the published `Sum.Prop` values
agree with the counts to rounding precision. For growth, all colony counts are
nonnegative integers. Each growth workbook has **168 rows but only 84 distinct
`Picture ID` labels**; those IDs repeat across temperature replicates and
must not be used as unique records without the remaining fields.

The source's `Run.Num` and `Temp.Rep` labels make within-batch dependence
observable. A temperature-run group with three assay records is not
automatically three independent experimental assignments.

The [Dryad germination and conjugation descriptive tables](external_dryad_lab_assay_descriptives.md)
preserve the nested `Rep` labels and report original counted numerator and
denominator totals by recorded temperature/run group. They exclude the growth
workbooks and make no claims about independent chambers or heat effects.

### Greenhouse seedlings

- Infection workbook: **1,112 scored rows** in **852 recorded design cells**
  (year, date, temperature, inoculation status, timing, replicate, family).
- It has **141 excess fully identical rows**. The source readme says the
  observations are per plant, but provides no unique plant identifier; these
  identical records may be distinct plants and are never deduplicated.
- Recorded disease codes are `D`, `LD`, `HF`, and `HM`. Binary endpoint
  construction needs the protocol's explicit status mapping.
- Death workbook: **173 rows**, all with `dead=1`, and **58 excess fully
  identical rows**. It is a case-oriented death record, not a risk denominator.
  The source does not provide a stable plant ID for linking the death and
  infection sheets. A mortality proportion or survival curve cannot be
  reconstructed by counting these cases alone.

The `Rep`/`replicate` fields and family labels can help stratify future
analyses; they do not restore the missing individual-plant links.

### Field plants, summaries, and weather

- The raw field workbook has **178 distinct plant positions**, keyed by
  `Row` and `Position`, with **27 raw-status date columns** and **27
  infection-status date columns**. Its **4,795 populated raw-status cells**
  are repeated observations on the same plants, not independent units.
- The flowering summary has **27 rows with 27 recorded dates**. These are
  aggregated summaries of the field process, not another sample of plants.
- The weather TSV has **214 daily records**, including one missing temperature
  and one row with recorded `Low` greater than `High`. These are kept
  visible, with no imputation or correction in the source data.

The [longitudinal field-panel audit](external_dryad_field_panel.md) additionally
verifies the 27-visit date alignment, inventories all literal status labels
(including mixed and unlisted source codes), and identifies the exact weather
anomaly dates without creating disease transitions or new experimental units.

## What these data currently support

The imported data can support descriptive, source-specific analysis with
explicitly declared observational units. Future inferential work needs:

1. The aphid **allocation and replication protocol**: containers, independent
   treatment assignments, batches, and the identity of field plots over time.
2. The Dryad **run and chamber design** to identify dependence among
   `Temp.Rep`, `Run.Num`, and within-condition replicates.
3. The greenhouse **plant-level identifiers, disease codebook, and
   denominators** before pooling infection/death outcomes or estimating risks.
4. Reconciliation of the aphid field dates and the two original Dryad weather
   anomalies before any time-aligned exposure model.

The three publications represented in this repository are separate biological
studies. They do not establish a shared treatment candidate or a laboratory
to greenhouse to field pipeline. This audit intentionally does not join them
into one efficacy dataset.
