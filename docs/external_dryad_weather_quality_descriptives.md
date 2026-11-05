# Dryad daily-weather source-quality review

The original *High temperatures reduce growth, infection, and transmission of
a naturally occurring fungal plant pathogen* dataset
([Dryad DOI](https://doi.org/10.5061/dryad.4mw6m90jv), version 3) includes
`daily_high_temps.txt`. Its source README identifies the **Beltsville weather
station** and states that the series was used for Figure 3a. The file
contains both `High` and `Low` columns, despite its high-temperature name.

This export implements only `source_weather_quality_review`, already permitted
for `dryad_daily_weather` in the
[analysis eligibility contract](external_analysis_eligibility.md). A station
reading is a **calendar-day record**, not a randomized plant or a verified
plant-level exposure. No units are inferred or converted from the recorded
temperature strings.

## Reproduce and check

Run from the repository root, offline:

```bash
PYTHONPATH=src python -m crop_protection_ps.dryad_weather_quality_descriptives
PYTHONPATH=src python -m crop_protection_ps.dryad_weather_quality_descriptives --check
```

The exporter validates the checksum-pinned manifest, unaltered eligibility
contract and predecessor
[field-panel audit](external_dryad_field_panel.md). It independently checks
each present temperature, preserves the literal source strings and uses the
field panel's 27 original dates only to indicate matching calendar dates.
The `--check` mode is read-only and fails on missing or stale artifacts.

## Source findings

| Quality check | Result |
| --- | ---: |
| Original weather records and unique calendar dates | 214 |
| Recorded date range | 1 May–30 November 2021 |
| Days missing between first and last recorded dates | 0 |
| Source rows with both temperatures present and ordered | 212 |
| Missing `High` component | 0 |
| Missing `Low` component | 1 |
| `Low` exceeding `High` | 1 |
| Field visits with a matching station calendar date | 27 of 27 |
| Field visits coinciding with a flagged station reading | 1 |

Two source values require attention:

| Recorded date | Original `High` | Original `Low` | Quality issue | Field visit on same day? |
| --- | ---: | ---: | --- | --- |
| 30 August 2021 | `91.00` | *blank* | Missing low-temperature observation | No |
| 31 August 2021 | `85.00` | `90.00` | Reported low exceeds reported high | Yes |

The 30 August entry directly precedes a field-visit date; this fact does **not**
define or justify any lagged exposure. No interpolation, filling, clipping,
value swapping or implied correction is applied to either day.

## Reproducible outputs

| Artifact | Contents |
| --- | --- |
| [`source_daily_weather.csv`](../results/external_dryad_weather_quality/source_daily_weather.csv) | All 214 original `Date`, `High`, `Low` strings, with order, ISO calendar date, quality indicators and same-day field-visit flag. Source blanks and decimal formatting are preserved. |
| [`quality_events.csv`](../results/external_dryad_weather_quality/quality_events.csv) | One row per detected missing or reversed component, recording original values and same-day visit alignment. |
| [`summary.json`](../results/external_dryad_weather_quality/summary.json) | Source and contract SHA-256 provenance, row/date counts, quality tallies, calendar gaps and limitations, without duplicating raw observations. |

The corresponding
[research-readiness ledger](external_analysis_readiness.md) now has
metadata-crosschecked reports for all 36 permitted descriptive actions.
That does **not** clear any of its 19 protocol-gated inferential questions.

## What remains unvalidated

The field study's source documentation names a weather station, but does not
by itself establish which station readings approximate each plant's
microclimate. The recorded anomalous dates must be resolved with defensible
source or protocol evidence before a temperature-exposure model is considered.
The separate field summary contains moving-temperature and other weather-like
variables; reproducing a date match does not validate their derivation,
aggregation windows, time lags, measurement units or confounders.

The current work does not fit a weather–disease correlation, estimate a
temperature effect, infer transitions, or change any
`requires_protocol`/`blocked` permission.
