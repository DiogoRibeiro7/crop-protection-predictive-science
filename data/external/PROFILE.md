# Structural review of external research data

The checked-in [`profile.json`](profile.json) is a reproducible inventory of
the 16 **original** files in `manifest.json`. It reports worksheet names, source
headers, row counts, and blank or literal-`NA` cells. XLSX sheet data are read
from cached OOXML cell values with the Python standard library; no third-party
Excel parsing package, formula evaluation, or source-file conversion is needed.

Regenerate it from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.external_profile \
  --data-dir data --output data/external/profile.json
```

Check that committed metadata still matches the verified source files, without
writing anything:

```bash
PYTHONPATH=src python -m crop_protection_ps.external_profile \
  --data-dir data --output data/external/profile.json --check
```

The profiler first verifies every source file against the recorded byte size
and publisher checksum. It fails on missing or modified files. A blank physical
cell is counted under `missing_cells`; the strings `NA` and `N/A` are retained
as literal values and counted separately under `literal_na_cells`. For Excel
dates, distinct-value counts use stored numeric serials, not interpreted dates.
The output contains **no individual observations** and does not count readme
worksheets as experimental records.

## Observed structure

| Study | Observation tables | Source rows | Important qualification |
| --- | ---: | ---: | --- |
| Wheat fungicide field trials (Zenodo 6521175) | 1 | 2,276 | 76 distinct `TrialId` values; rows are repeated endpoint observations, not 2,276 independent trials. |
| Aphid pesticide and temperature (Zenodo 19805135) | 5 | 330 | Four controlled experiments (36, 24, 180, 36 records), and a distinct 54-record field dataset. |
| Fungal pathogen temperature (Dryad 4mw6m90jv) | 12 | 2,544 | Laboratory, greenhouse, field and daily-weather tables; ten additional workbook readme sheets are excluded. |

These are counts of **rows in source tables**, not interchangeable estimates of
biological or experimental sample size. The Dryad field file stores 178 plants
in 124 columns with repeated measurements across dates; treating its columns as
independent plants would be pseudoreplication. Some blanks are consequently
structural. The Dryad infection workbook also has 1,112 blank optional comment
cells, which must not be interpreted as missing disease outcomes.

## Checks and open questions

1. **Wheat trial units.** The upstream title describes 56 fungicide trials, but
   the file contains 76 distinct `TrialId` codes. These counts need definition
   and provenance reconciliation before using a trial-level grouping variable.
2. **Coded missingness.** The wheat TSV has 1,101 literal `NA` tokens and no
   physically empty cells. Do not coerce all codes to numeric zero or silently
   equate them with blank observations.
3. **Aphid endpoint denominator.** All 276 controlled observations satisfy
   `0 <= DEAD <= TOTAL`. The 54 field records instead contain `PopSize`,
   `Base_number`, and a reported `Mortality` rate; do not treat these as the
   same binomial sampling design without reviewing the field protocol.
4. **Weather quality.** The Dryad `daily_high_temps.txt` has one blank
   temperature cell and a recorded day (31 August 2021) with `Low` exceeding
   `High`. Preserve those original records and review against the source before
   any temperature-dependent modelling.
5. **Experimental linkage.** There is no demonstrated fungicide candidate
   identity linking laboratory, greenhouse and field stages across the three
   independent publications. No cross-study matching, treatment-effect
   inference, imputation, or model training is performed by the profiler.

The source-specific licensing and DOIs remain in [README.md](README.md) and
`manifest.json`. The blocked Mendeley source remains excluded until its files
can be obtained through an authorized download.

The [wheat endpoint pairability audit](../../docs/external_wheat_pairability.md)
assesses which treated measurements have a comparable untreated observation
within the same trial, while retaining the trial-unit uncertainty.

The [wheat geocode hierarchy audit](../../docs/external_wheat_site_hierarchy.md)
finds 56 rounded country–coordinate combinations, 65 geocode–years, and 76
distinct `TrialId` codes. The match to the publisher's *56 trials* title is
suggestive, but cannot establish unique physical fields or plot replicates.

The [cross-ID collision fingerprint audit](../../docs/external_wheat_collision_fingerprints.md)
compares dates, endpoint signatures and exact raw records within the nine
shared geocode–years. It finds overlap but does not reclassify records as
duplicate experimental units.

The [aphid and fungal-pathogen experimental-unit audit](../../docs/external_aphid_dryad_units.md)
separates controlled cohort records, field repeat measurements, laboratory
assay batches, greenhouse plant records, and longitudinal field observations.

The [controlled-aphid descriptive tables](../../docs/external_aphid_controlled_descriptives.md)
aggregate only the four permitted `DEAD`/`TOTAL` worksheets by their literal
experimental conditions. The fifth, field-design worksheet is not combined
with these counts.

The [field-follow-up paired tables](../../docs/external_aphid_field_pairs.md)
retain both `Experiment5` visits for each of its 27 provisional series and
compute only the observed day-7 minus day-3 mortality-rate difference. No
sampling calendar, randomized plot assignment, or treatment effect is inferred.

The [Dryad field-panel audit](../../docs/external_dryad_field_panel.md)
reconciles the original field-status header dates, flower-summary dates and
weather observations; catalogs source status strings without recoding them;
and locates the two known weather anomalies on the calendar.

The [Dryad germination/conjugation descriptive exports](../../docs/external_dryad_lab_assay_descriptives.md)
retain the original run and replicate labels in four distinct source-assay
tables. They sum recorded numerator/denominator counts within each
temperature/run label but do not estimate independent temperature effects.

The [analysis-eligibility contract](../../docs/external_analysis_eligibility.md)
turns these audits into explicit table-level permissions: descriptive checks
that are currently safe, inferential analyses awaiting protocol evidence, and
prohibited assumptions. Its validation command fails closed on changed sources
or reports, missing tables, and unsupported permissions.
