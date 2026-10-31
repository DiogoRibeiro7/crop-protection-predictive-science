# Longitudinal field-panel audit: Dryad fungal pathogen data

This audit characterizes the original, **unchanged** field data from
[*High temperatures reduce growth, infection, and transmission of a naturally
occurring fungal plant pathogen*](https://doi.org/10.5061/dryad.4mw6m90jv)
(Dryad version 3). It complements the
[experimental-unit review](external_aphid_dryad_units.md) without turning the
recorded status strings into disease indicators or imputing weather.

Run from the repository root, with no network access:

```bash
PYTHONPATH=src python -m crop_protection_ps.dryad_field_panel
PYTHONPATH=src python -m crop_protection_ps.dryad_field_panel --check
```

The command verifies the source manifest and the previous experimental-unit
report, reads the two original Excel workbooks with the existing standard-
library OOXML reader, and checks the original weather TSV. The deterministic
[report](../results/external_dryad_field_panel.json) contains aggregated
token frequencies and a visit-level inventory, not plant-level observations.
`--check` fails on missing/stale output and never overwrites it.

## Findings from the original files

| Source feature | Finding | Interpretation |
| --- | --- | --- |
| Plants | 178 distinct `Row` + `Position` pairs | One plant per source row, not one plant per date/status cell. |
| Raw `Status.*` visits | 27, dated 17 May–18 November 2021 | All 27 dates correspond to the 27 flowering-summary rows. |
| Derived `Infect.status.*` visits | 27 | All 27 dates correspond to the same flowering-summary date axis. |
| Raw status cells | 4,806 possible; 4,795 populated, 11 blank | Blank cells are preserved rather than called healthy or missing at random. |
| Infection-status cells | 2,944 populated, 1,862 blank | These are not additional plant replicates or necessarily diseased/healthy scores. |
| Raw status labels | 31 distinct nonblank strings | The README's short code list is not a complete empirical dictionary. |
| Raw labels outside enumerated README codes | 24 distinct strings, 1,124 occurrences | Primarily `H` (975), plus combined or annotated strings. Not evidence of invalid observations. |
| Infection-status labels | `D`, `H`, `PD`, `ST` and one `F` | `F` (one record) requires explicit codebook clarification. |
| `Ever.dis` column | 172 blank and six `0` entries | It must not be used as a complete derived ever-disease outcome. |
| Column-name typo | `Status.Spet.24` | Parsed as 24 September 2021, reported explicitly; the source header is unchanged. |
| Weather coverage | Dates present for all 27 visits | A date match alone does not establish a valid temperature exposure series. |
| Weather anomaly | 30 August 2021 missing `Low`; 31 August 2021 `Low > High` | The reversed pair falls on a field-visit date; the preceding day's missingness matters for lagged exposures. |

The README explicitly enumerates `V`, `B`, `D`, `PD`, `LD`, `X`, `PO`,
and `ST` for raw status fields, while the source also uses `H`, `D/H`,
`H/D`, `D/ST`, `LD/H`, `D (LIGHT)`, and other literal annotations. The
**unlisted** count is defined relative to that particular raw-status list;
for example, `H` is discussed elsewhere in the README as healthy in the
*infection-status* context. Unlisted does not mean wrong. The audit provides
exact token frequencies so investigators can build a source-supported
codebook before specifying an endpoint.

For date matching, the script checks the integer 1900-system Excel date
serials, compares elapsed days from the first survey with the summary's
`days` field, parses the visible month/day in the status headers, and matches
the weather's source dates. The sole observed misspelling (`Spet`) is an
explicit, recorded alias, not a silent change to the workbook.

## Statistical boundaries

1. No disease transition probabilities, treatment effects, or causal
   temperature effects are estimated. Plant observations over 27 visits are
   longitudinal, and repeated cells are not independent plants.
2. The raw `X` label is counted, but its terminal/censoring meaning is not
   asserted. Death and cessation of observation require the experimental
   protocol before defining transitions or absorbing states.
3. The coded/annotated raw statuses and the one unlisted infection-status
   value must be resolved with the authors' codebook. Do not automatically
   map `D/H` to disease or `ST` to absence of infection.
4. The weather values are preserved. In particular, **31 August is a
   measurement date with invalid high/low ordering**. Modelling a lagged
   exposure also requires resolving the preceding missing value and the
   weather-station/site relationship.
5. The [eligibility contract](external_analysis_eligibility.md) continues to
   classify longitudinal disease and temperature-causal models as
   `requires_protocol` and does not grant any new modelling permission.

The source-data [profile](../data/external/PROFILE.md),
[manifest](../data/external/manifest.json), and
[unit audit](../results/external_aphid_dryad_units.json) establish the
underlying row counts and provenance. Neither the workbooks nor the weather
file have been edited.
