# Descriptive mortality counts in four controlled aphid experiments

The public source [Wang et al., Zenodo 19805135](https://doi.org/10.5281/zenodo.19805135)
contains five worksheets. Four report 
`TOTAL` (aphids counted before treatment) and `DEAD` (aphids recorded dead)
under combinations of temperature and pesticide exposure. This export turns
those four worksheets into four reproducible **descriptive condition tables**.

The field worksheet, `Experiment5`, uses population estimates and derived
mortality rates, not integer `DEAD`/`TOTAL` cohorts. It is deliberately excluded
from every condition table and is governed by a separate eligibility policy.

## Reproduce the tables offline

From the project root:

```bash
PYTHONPATH=src python -m crop_protection_ps.aphid_controlled_descriptives
PYTHONPATH=src python -m crop_protection_ps.aphid_controlled_descriptives --check
```

The command validates the full [analysis eligibility
contract](external_analysis_eligibility.md) and checks source integrity against
the original file manifest. Only
`condition_mortality_description` is requested for the four controlled assets;
the more ambitious `binomial_temperature_interaction` remains
`requires_protocol`.

The five generated artifacts live in
[`results/external_aphid_controlled/`](../results/external_aphid_controlled/):

- [`summary.json`](../results/external_aphid_controlled/summary.json) contains
  condition-level counts, literal factor levels, aggregate validity checks,
  and provenance hashes.
- `experiment1_conditions.csv` through `experiment4_conditions.csv` contain
  only the factors recorded in each respective source sheet, followed by
  source-record count, counted aphids, deaths, and descriptive fractions.

The `--check` mode compares **all five files** byte-for-byte with newly
generated output and never modifies them. The original workbook is read but
not modified; no new data source is downloaded or joined.

## Counts and observed design balance

| Worksheet | Recorded cohort rows | Condition cells | Counted aphids | Recorded deaths |
| --- | ---: | ---: | ---: | ---: |
| Experiment 1 | 36 | 12 | 1,065 | 415 |
| Experiment 2 | 24 | 8 | 717 | 131 |
| Experiment 3 | 180 | 48 | 5,322 | 1,495 |
| Experiment 4 | 36 | 12 | 1,007 | 444 |

There are **276 controlled cohort rows** describing **8,111 counted aphids**.
These totals check the transcription and aggregation. They are **not** a
combined experiment or a pooled treatment-effect estimate.

Within a condition, the table reports:

- `source_records`: number of source worksheet rows, **not** a verified
  number of independently randomized units.
- `counted_aphids`, `recorded_deaths`: sums of the source `TOTAL` and `DEAD`
  values, validated as nonnegative integers with a positive denominator.
- `pooled_recorded_mortality`: the ratio of those two totals, rounded to ten
  decimal places. It is a descriptive fraction among counted aphids only.
- `min_source_cohort_fraction`, `max_source_cohort_fraction`: minimum and
  maximum per-row `DEAD/TOTAL` within that condition. This records observed
  spread without treating those rows as independent statistical replicates.

The condition factors are grouped by **literal source values**. No concentration
unit conversion, temperature transformation, duration normalization, or
cross-experiment harmonization is performed. The output rows use a stable
lexical ordering of original labels; ordering is not a numerical interpretation
of time or dose.

### Specific interpretation hazards

1. Experiment 2 contains `Treatment_Time` labels **`12h` and `90`**.
   The source readme does not establish a single unit for the unqualified `90`
   label. The exporter preserves both strings instead of guessing a common unit.
   The `12h` records appear only at **22°C**; the `90` records occur at **30,
   33 and 36°C**. Temperature and duration therefore lack independent
   variation in this recorded design, preventing an isolated effect estimate
   for both factors from these records alone.
2. Experiment 3 has **40 conditions with three rows, four with six, and four
   with nine**. A blanket assumption of three replicates per condition is
   false. Its workbook also contains **20 excess exact matching row encodings**;
   no matching rows are deduplicated because they could represent separate
   cohorts with identical observed values.
3. All four controlled workbooks lack explicit container, batch, or randomized
   unit IDs. The 8,111 counted aphids are an outcome denominator, **not** an
   experimental sample size for independent treatment assignment.
4. No confidence intervals, p-values, interaction coefficients, causal
   effects, experimental replication claims, or field validation are computed.

The [experimental-unit audit](external_aphid_dryad_units.md) provides the
original condition-cell counts and the distinct structure of Experiment 5.
Additional inferential use requires the publication's allocation protocol,
independent exposure-unit and batch definitions, and an appropriate clustered
or overdispersed analysis plan.
