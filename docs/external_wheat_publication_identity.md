# Wheat source evidence: the advertised 56 trials versus 76 `TrialId` codes

The [original Zenodo version 1.0 record](https://zenodo.org/records/6521175),
deposited by Niels Holst, describes **56 fungicide field trials** conducted by
BASF across Europe during 2017–2019. The checksum-verified tab-separated file
has **76 distinct `TrialId` codes**. We have not established how those 76
codes correspond to independent physical trials, plots, or replicate blocks.

This review adds two pieces of source-backed evidence to the existing
[geocode hierarchy](external_wheat_site_hierarchy.md) and
[collision fingerprints](external_wheat_collision_fingerprints.md): the exact
published release-file inventory, and a separately checked decomposition of
the count discrepancy. Neither piece authorizes causal inference.

## What is visible in the original Zenodo release

The [source record](https://zenodo.org/records/6521175) lists five files:

| Original file | Source check | What it establishes |
| --- | --- | --- |
| `basf-wheat-diseases.txt` | Locally imported; original MD5 verified | Observed fields and recorded grouping keys |
| [`basf-wheat-diseases.R`](https://zenodo.org/records/6521175/files/basf-wheat-diseases.R?download=1) | Public R source inspected | Sources setup, loads binary observations, summarizes and maps them |
| [`setup.R`](https://zenodo.org/records/6521175/files/setup.R?download=1) | Public R source inspected | Provides geographic-map plotting logic and library setup |
| `basf-wheat-diseases.Rdata` | File listed; binary contents not reviewed | **No trial identity or metadata claim** |
| `basf-wheat-diseases-map.png` | File listed; image not reviewed | **No experimental design claim** |

The two inspected scripts do **not** define a `TrialId`-to-physical-trial
crosswalk or a randomization/replicate dictionary. That does not prove the
information is absent from the binary data, the original BASF protocol, or
other documents. Publisher-file MD5s for files *not locally imported* were
transcribed from Zenodo, not independently recomputed.

The dated, human-reviewed [publication evidence register](../data/external/wheat_publication_evidence.json)
records the Zenodo DOI, release version, all five publisher-reported file
checksums, the exact two scripts examined, and the scope limitations. It is
first-party research metadata, **not** an additional original experiment file.
The [IPM Decisions D4.8 report](https://www.ipmdecisions.net/media/vovnkaon/d4-8-selected-datasets-are-made-available-for-validation-of-dss-systems-by-other-end-users.pdf)
independently describes the 56-trial BASF release and its 0.1° georeferencing.

## Three groupings, three different questions

| Grouping of the pinned TSV | Distinct groups | Difference from preceding level |
| --- | ---: | ---: |
| Source `TrialId` code | 76 | — |
| `(Country, Latitude, Longitude, observation year)` | 65 | 11 fewer |
| `(Country, Latitude, Longitude)` | 56 | 9 fewer |

The numerical gap decomposes exactly into **11 within-geocode-year code
collapses + 9 across-year site-year collapses = 20 fewer groups**. This is
not an observed `TrialId`-to-trial mapping. In particular, collapsing the
nine across-year groups would silently equate events observed in different
calendar years; even the within-year groups may represent different physical
experiments. The match between the number of *rounded locations* and the
publisher's trial count is a hypothesis about naming, **not evidence of
independence or replication**.

For example:

- In Bulgaria in 2019, four trial codes (`31`, `32`, `33`, `34`) use the
  same recorded location `(43.3, 25.0)`.
- In France, `(48.0, 1.8)` contains codes `8` and `10` in 2017, code `23`
  in 2018, and code `46` in 2019.

These are *recorded 0.1° location matches* rather than asserted physical
field or plot matches. Their dates, treatments and observed endpoints are
not a substitute for an original experimental-design dictionary.

## Reproduce the review without internet access

From the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.wheat_publication_identity
PYTHONPATH=src python -m crop_protection_ps.wheat_publication_identity --check
```

The command verifies the original TSV against its source checksum; verifies
that the curated publication inventory matches the five publisher MD5s;
recomputes the geocode hierarchy and the exact 11 + 9 decomposition; checks
the full eligibility contract; and writes two deterministic artifacts:

- [external_wheat_publication_identity.json](../results/external_wheat_publication_identity.json):
  original source SHA-256, publisher-inventory digest, grouping counts,
  concrete collision examples and unchanged model permission.
- [external_wheat_protocol_identity_request.md](../results/external_wheat_protocol_identity_request.md):
  source-specific requests for the original trial-key crosswalk, layouts,
  plot replication, control/treatment definitions and endpoint protocol.

`--check` is read-only and fails if an artifact is missing or stale. It does
not request live Zenodo data, and it cannot verify a publisher script's
reported MD5 without downloading that file. This is an *offline review of a
dated source record*, not a continuous external-source freshness monitor.

## Research gate and next evidence needed

The `wheat_field` policy still marks `trial_level_treatment_effect` as
`requires_protocol` under the same four conditions:

1. Reconcile 56 published trials versus 76 `TrialId` codes with an
   authoritative experimental-trial key.
2. Obtain plot and replicate identities plus randomization information.
3. Obtain the fungicide treatment/product dictionary.
4. Obtain the full disease and yield endpoint protocol.

No permission in [analysis_eligibility.json](../data/external/analysis_eligibility.json)
is modified. No new treatment-effect model or pooled trial estimator is
introduced. No author has been contacted; the generated request is ready for
human review before any outreach.
