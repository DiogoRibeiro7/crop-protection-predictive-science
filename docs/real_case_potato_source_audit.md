# Potato late-blight trials: source-identity and experimental-unit intake

## Decision status

**New candidate source, not a fourth validated modelling case.** This is an
integrity and candidate-design inventory only. No dose–response, treatment
effect, fungicide ranking, yield contrast or model-accuracy estimate has been
calculated. The existing three validated public field-data cases are unchanged.

The source is a potentially valuable extension because it reports fungicide
field trials conducted in two countries over five growing seasons. However,
the source's row and trial identities must be reconciled before statistical
inference. Treating raw records as independent observations would produce
drastically misleading apparent sample sizes.

## Original public deposit and byte-level identity

Holst, N., & Donner, M. (2022). *Data from 18 fungicide trials on potato late
blight in UK and Ireland 2013–2017.* Zenodo.
[DOI 10.5281/zenodo.6352735](https://doi.org/10.5281/zenodo.6352735).

- Upstream original: [`corteva-potato-late-blight.txt`](https://zenodo.org/records/6352735/files/corteva-potato-late-blight.txt?download=1)
- Original declared MD5: `4bd9fa37126cf6f6842bb3491a1779e7`
- Audited original SHA-256: `e89e391b32915df358f66ccd95e20c3d2d922c8ccfb5d1c6efb8b5ccdf198096`
- Source columns: `Country`, `Latitude`, `Longitude`, `Date`, `CropStage`,
  `Trial`, `Plot`, `Treatment`, `Untreated`, `Value`.
- The source TSV is **not vendored**. The deposit page does not provide a
  sufficiently clear data-reuse license for this repository to redistribute
  the original observations; source rows remain at Zenodo.

Hash-pinned audit source:
`src/crop_protection_ps/potato_source_audit.py`.
Only summary tables, candidate identifiers and conflict counts are committed.

## Findings from the original TSV

| Measure | Observed count | What it does and does not mean |
| --- | ---: | --- |
| Original rows | 127,034 | Source records, **not** independent observations |
| Distinct complete row signatures | 9,013 | Raw strings after exact complete-record comparison |
| Exact-repeat excess | 118,021 | Additional identical lines after their first appearance |
| Signatures appearing exactly 100 times | 1,192 | All in 2016; not 100 replicates |
| Geocoded site-year cells | 18 | Candidate location/year groupings, not authenticated unique trials |
| Distinct literal `Trial` labels | 8 | Labels recur across sites or seasons |
| Site-year × `Trial` code cells | 34 | Not interchangeable with the published title's 18 trials |
| Candidate site-year × trial × plot keys | 602 | Provisional plot identities, pending experimental design |
| Candidate plot/date/crop-stage event keys | 8,990 | Repeated longitudinal assessments may belong to the same plot |
| Event keys containing distinct `Value` entries | 23 | All in 2015; may be missing sub-plot identifiers or source inconsistencies; no cause inferred |

### Where the multiplicity occurs

| Season | Original rows | Distinct full records | Excess identical rows | Signatures occurring 100× |
| --- | ---: | ---: | ---: | ---: |
| 2013 | 1,628 | 1,624 | 4 | 0 |
| 2014 | 2,594 | 2,594 | 0 | 0 |
| 2015 | 2,212 | 2,203 | 9 | 0 |
| 2016 | 119,772 | 1,764 | 118,008 | 1,192 |
| 2017 | 828 | 828 | 0 | 0 |

The counts above are an inspection of the **exact upstream bytes**. The
2016 pattern could reflect an export procedure, internal source structure or
deliberate repetition. The audit does **not** assert a cause. No rows are
deleted, imputed, averaged or passed into a model.

The `Treatment` code is not a global untreated/treated classifier: the same
code appears with different `Untreated` statuses across trial groups. The
source also has no explicit endpoint-type field identifying `Value` as disease
severity versus tuber yield. The deposit's descriptive claim that trial data
include yield is not sufficient to identify such observations in this TSV.
The 23 multi-value event keys may reflect legitimate within-plot subsamples
that the available columns cannot distinguish; **they are not proven errors**.
The original `.Rdata` and setup files have not been accepted as evidence of
additional identified endpoints without a separate, verified format audit.

## Candidate identity and inference boundaries

- Candidate site-year: `(Country, Latitude, Longitude, calendar year)`.
- Candidate trial: site-year plus literal `Trial` code.
- Candidate plot: candidate trial plus literal `Plot` code.
- Candidate assessment event: candidate plot plus `Date` and `CropStage`.

The audit checks that repeated records for each candidate plot do not change
the recorded treatment or untreated flag. It retains exact-record
multiplicities, reports ambiguous event keys and rejects changed schema,
out-of-range values, nonfinite numbers, malformed dates and contradictory
assignments. These are **quality-control identities**, not established
randomization, treatment, timepoint or block units.

No inferential analysis is permitted until the following are resolved by an
original protocol, data dictionary or authoritative supplementary source:

1. Reconcile the 18 titled trials, 34 site-year/trial-code cells and the
   allocation of plots to randomized units and blocks.
2. Explain the 100× 2016 exact-row duplication and the 23 nonidentical
   values on otherwise identical candidate assessment keys.
3. Document the scale, unit, endpoint semantics, censoring and missingness of
   `Value`, including where yield, if present, is recorded.
4. Resolve treatment labels, doses and untreated arms within trial and
   across seasons; define any valid matched contrasts and independence units.
5. Predeclare an estimand, a defensible repeated-measures model and a
   site/season-level validation strategy **before** inspecting effects.

No pooled row-wise comparison, p-value, efficacy estimate, spray recommendation
or fourth-case model claim is justified by this intake.

## Reproduce without redistributing original observations

Download the source from the Zenodo link above into a local directory outside
the repository. The audit automatically rejects changed source bytes by
checking both the source's MD5 and the independent SHA-256 pin.

```bash
python -m crop_protection_ps.potato_source_audit \
  --source /path/to/corteva-potato-late-blight.txt \
  --output results/real_potato_late_blight/source_audit
```

Outputs (`summary.json`, `years.csv`, `site_years.csv`, `trial_aliases.csv` and
`conflicting_events.csv`) are sorted, deterministic **derived** evidence.
The summary records what is and is not permitted. The ambiguous-event export
contains keys and distinct-value counts, not the contested source responses.
The persisted evidence is independently checked by
`tests/test_potato_source_audit.py` in offline CI. Tests of source parsing use
synthetic toy observations; no network access or external original TSV is
needed in CI.
