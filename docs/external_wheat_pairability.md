# Wheat fungicide trials: endpoint pairability audit

This audit examines the **original tab-separated source** from Holst (2022),
[10.5281/zenodo.6521175](https://doi.org/10.5281/zenodo.6521175). It measures
whether untreated and treated observations are recorded under comparable
assessment conditions. It does **not** estimate treatment effects, infer
within-plot uncertainty, or create new fungicide-candidate identities.

Run from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.wheat_pairability \
  --data-dir data --output results/external_wheat_pairability.json
```

The non-writing freshness check is:

```bash
PYTHONPATH=src python -m crop_protection_ps.wheat_pairability \
  --data-dir data --output results/external_wheat_pairability.json --check
```

The code validates the entire external-source checksum manifest before
reading the wheat file. The committed JSON records a SHA-256 digest for this
exact TSV and includes one summary per `TrialId`.

## Operational pairing definition

An assessment is provisionally comparable only when the records match on:

`TrialId`, `Date`, `Daft`, `GsFrom`, `GsTo`, `Organism`, `Parameter`,
`Clarifier`, `Method`, `SampleUnit`, and `PlantPart`.

The matched group must have exactly one untreated record and at most one
record for each distinct treatment label. Spray count and treatment label can
vary between arms, as they are part of the intervention. Duplicate same-arm
records are **ambiguous** without a replicate identifier; they are excluded
from pair counts instead of being averaged. The report also checks that each
trial ID refers to one country, coordinate pair, and calendar year.

## Observed coverage

| Quantity | Value | Interpretation |
| --- | ---: | --- |
| Source records | 2,276 | Repeated disease or yield measurements, not independent trials |
| Distinct `TrialId` codes | 76 | Grouping identifiers, pending source protocol reconciliation |
| Distinct assessment groups | 1,164 | Unique combinations of the fields above |
| Matched assessment groups | 921 | One untreated record and at least one treated label |
| Matched treated records | 1,112 | Candidate descriptive contrasts at matched assessments |
| Matched untreated records | 921 | Reused by multiple arms in 161 multiarm assessment groups |
| Untreated records with no paired treatment | 239 | Cannot contribute a treated-control comparison |
| Treated records with no matching untreated | 4 | Two at TrialId 17 and two at TrialId 70 |
| Duplicate same-arm assessment groups | 0 | No ambiguous pairing detected in this source version |

Of the 921 matched groups, 779 assess the source's `INFECT` endpoint and 142
assess its `ERTRNE` yield endpoint. There are 760 matched groups with one treated
label, 131 with two, and 30 with three. All 76 identifiers include both
untreated and at least one treated record somewhere in their series, but that
does not imply complete outcome matching at every assessment date.

## Experimental-unit and inference limits

1. **Trial-definition discrepancy remains unresolved.** The Zenodo title and
   IPM Decisions deliverable describe 56 wheat trials. The actual TSV has 76
   distinct `TrialId` values, each associated with one location and year.
   Nothing in the imported fields explains the discrepancy. Neither number
   should be presented as a confirmed count of independent physical trials.
2. **No plot replicate identifier.** `SampleUnit` is a measurement code, not a
   unique plot identifier. Matched assessment records can share an untreated
   comparator; row-level confidence intervals would risk pseudoreplication.
3. **Treatment labels are opaque.** `TreatmentA` through `TreatmentD` must not
   be interpreted as fixed active substances or equal interventions across
   countries or years without the original application protocol.
4. **Endpoint definitions differ.** Infection and yield measurements, source
   methods, plant parts and measurement units cannot be pooled as one outcome.
   The report deliberately makes no percent-control or yield-gain claim.
5. **No cross-stage candidate linkage.** This field-only source cannot fill
   the laboratory–greenhouse–field fungicide candidate progression gap.

The next defensible step is to obtain the protocol or trial dictionary to
resolve the 56/76 discrepancy, plot-level replication, and treatment identities.
Only then choose a disease-specific estimand with trial-level grouping,
appropriate baseline control, and prespecified repeated-measure handling.
