# Wheat field trials: TrialId versus recorded geocode hierarchy

The source release from [Holst (2022), Zenodo 6521175](https://doi.org/10.5281/zenodo.6521175)
is titled *Data from 56 fungicide trials in wheat fields across Europe
2017–2019*. The original TSV instead contains 76 distinct `TrialId` values.
This reproducible audit explores the discrepancy by examining **only the
recorded country, latitude, longitude, year, and trial ID**. It does not
estimate treatment effects or infer unique physical fields.

The upstream [IPM Decisions deliverable D4.8](https://www.ipmdecisions.net/media/vovnkaon/d4-8-selected-datasets-are-made-available-for-validation-of-dss-systems-by-other-end-users.pdf)
describes the BASF wheat release as 56 trials (section 4.6, page 7) and
states that the published data use a georeferencing precision of 0.1°
(section 5, page 8). This limits what a coordinate match can establish.

## Exact, independently reproducible counts

| Source-recorded grouping | Count |
| --- | ---: |
| Source observation rows | 2,276 |
| Distinct `TrialId` values | 76 |
| Distinct `(country, latitude, longitude, year)` combinations | 65 |
| Distinct `(country, latitude, longitude)` combinations | **56** |
| Geocodes represented in more than one year | 8 |
| Geocode–year combinations holding multiple `TrialId` values | 9 |
| Trial IDs associated with those nine shared geocode–years | 20 |

The 65 geocode–year groups contain 56 singleton groups, eight groups with two
`TrialId` values and one with four. In Bulgaria in 2019, for example, codes
`31`, `32`, `33` and `34` all share the published geocode `(43.3, 25.0)`.
Across years, 48 distinct geocodes occur in one year, seven in two years and
one in three years.

The numerical equality between **56 distinct geocodes** and **56 trials in
the source title** is a plausible *site-count interpretation*, but it is
not a reconciliation supported by trial-level protocol. A 0.1° geocode can
represent different fields or plots, and the same field can host different
experiments. Multiple trial IDs at one geocode–year are therefore neither
confirmed repeats of one trial nor evidence of independent replicates.

## What the audit validates

- Each `TrialId` is associated with one source country, coordinate pair and
  observation year. Reuse across locations or years fails validation.
- Coordinates must be finite, in geographic range and consistent with the
  recorded one-decimal-degree precision; equivalent representations such as
  `48` and `48.0` are grouped together without further rounding.
- Country is part of each geocode. Numeric coordinates are sorted
  deterministically to make generated reports reproducible.
- The original external-source checksum manifest is verified before reading
  the source. The committed JSON records the wheat TSV's SHA-256 digest.
- The audit reports the nine geocode–year collisions, eight geocodes used
  across multiple years, country-level counts, and all 56 grouped geocodes.
  It does not duplicate the original response values.

To regenerate the evidence report from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.wheat_site_hierarchy \
  --data-dir data --output results/external_wheat_site_hierarchy.json
```

To check it without writing any files:

```bash
PYTHONPATH=src python -m crop_protection_ps.wheat_site_hierarchy \
  --data-dir data --output results/external_wheat_site_hierarchy.json --check
```

The report complements the
[within-trial endpoint pairability audit](external_wheat_pairability.md),
which finds 921 potentially matched assessment groups. Neither report
identifies randomized plots, their replicate numbers, fungicide substances,
or the unit of statistical independence.

## Protocol question remains open

The [analysis-eligibility contract](../data/external/analysis_eligibility.json)
must continue to mark `trial_level_treatment_effect` as `requires_protocol`.
To resolve the discrepancy and make an inferential analysis defensible, obtain
from the data owner the definition of a *trial*, unique site/field and plot
identifiers, assignment and replication, relationships among `TrialId`
values at shared geocodes, and treatment/product dictionaries.

No 76-to-56 mapping is asserted here. In particular, **never collapse all
records sharing a 0.1° geocode into an experimental unit**.
