# Potato late-blight data: RData/TSV parity and protocol gate

## Outcome

**The two published formats represent precisely the same data, not independent
evidence.** The complete RData and TSV releases agree in all 1,270,340
row-position/column-position values after decoding R categorical factors and
R `Date` epoch-day integers. Both contain 127,034 rows and the same ten fields.
The additional binary format therefore does **not** resolve the unusual 2016
duplicate multiplicity, missing trial identifiers or unnamed response types.

This follow-up changes neither the number of validated empirical field cases
(three) nor the model permission (`requires_protocol`). It contains no
treatment comparisons, predictive models or sample-size inflation.

## Independent upstream records

1. Holst, N., & Donner, M. (2022), [*Data from 18 fungicide trials on potato
   late blight in UK and Ireland 2013–2017*](https://doi.org/10.5281/zenodo.6352735),
   Zenodo v1.0. The deposit explicitly provides both formats and describes
   disease, crop-stage and yield observations.
2. IPM Decisions, [Deliverable D4.8, *Selected datasets are made available for
   validation of DSS systems by other end users*](https://www.ipmdecisions.net/media/vovnkaon/d4-8-selected-datasets-are-made-available-for-validation-of-dss-systems-by-other-end-users.pdf),
   March 2022, executive summary and section 4.3. The project reports that its
   georeferencing uses **0.1-degree spatial precision** and that Corteva
   approved open access to its submitted datasets. Neither statement supplies
   a plot randomization, repeated-measures or endpoint codebook.
3. The deposit's 288-byte `corteva-potato-late-blight.R` script loads one
   R workspace and plots `obs` on a map. It provides no separate experimental
   unit dictionary, allocation, response-type legend or modeling protocol.

Original files are not redistributed in this repository. The exact upstream
source identities used here are:

| Original artifact | Zenodo-advertised MD5 | Audited SHA-256 |
| --- | --- | --- |
| [`corteva-potato-late-blight.txt`](https://zenodo.org/records/6352735/files/corteva-potato-late-blight.txt?download=1) | `4bd9fa37126cf6f6842bb3491a1779e7` | `e89e391b32915df358f66ccd95e20c3d2d922c8ccfb5d1c6efb8b5ccdf198096` |
| [`corteva-potato-late-blight.Rdata`](https://zenodo.org/records/6352735/files/corteva-potato-late-blight.Rdata?download=1) | `a592e55691af3f08ef6928c51fa03a93` | `7f7844a868ae10a621679a832a7de10b348a96684c8e948ad1700f808b084940` |

The binary is verified against both hashes and its RDX3/XDR header before
deserialization. Its object inventory contains only `obs` (one data frame),
with exactly the TSV column names and order. R `Date` is decoded from integer
days since 1970-01-01; all other numeric values are compared as exact binary
doubles after TSV parsing, not using a tolerance. The audit also checks exact
factor/text labels, row ordering and source missingness. There are zero
observed differences across the 1,270,340 cells.

### Factor vocabulary does not add records

The R workspace retains unused categorical labels, which the TSV does not
encode as separate metadata. These are **unused category levels**, not extra
trials, treatments, plots or assessments:

| Factor | Declared levels | Observed labels | Unused levels |
| --- | ---: | ---: | --- |
| `Country` | 2 | 2 | None |
| `CropStage` | 89 | 79 | `13`, `15`, `19`, `23`, `47`, `49`, `57`, `97`, `99`, `BBCH` |
| `Trial` | 9 | 8 | `0` |
| `Plot` | 112 | 109 | `44`, `55`, `56` |
| `Treatment` | 19 | 19 | None |
| `Untreated` | 2 | 2 | None |

In particular, the unused `Trial` code `0` is not a nineteenth trial, and
`BBCH` is not a validated endpoint or treatment label. There are still no
separate fields for yield, disease versus yield endpoint type, plot block,
treatment dose, randomization unit, spray timing or observation/subsample ID.

## What the binary comparison establishes

- The TSV is a faithful representation of the R data frame, including row
  order, categorical labels, numeric precision and dates.
- The 2016 pattern of **1,192 complete-record signatures repeated 100 times**
  occurs in both originals. It cannot be attributed solely to a defect in
  the TSV-export procedure; the origin of the repetitions remains unknown.
- The 23 candidate assessment keys with multiple recorded `Value` entries
  remain unresolved. They may represent legitimate unlabelled within-plot
  subsamples or other source semantics, not necessarily measurement errors.
- The previous **18 geocoded site-year cells** cannot be equated automatically
  with 18 independently randomized trials. The project explicitly rounds
  geocodes to a tenth of a degree; 34 site-year/`Trial` cells still require
  reconciliation against the 18 trials claimed in the dataset title.
- Neither source format resolves whether `Value` represents disease incidence,
  severity, yield or some trial-specific mixture of outcomes.

These statements do not justify removing duplicates, averaging observations,
mapping treatment codes globally or performing row-wise cross-validation.

## Investigator protocol questions (priority order)

| Gate | Exact evidence needed | Consequence if absent |
| --- | --- | --- |
| P1: trial identity | Mapping of each published trial to source site/year, `Trial` code, real site ID and block/allocation scheme; explanation for 34 candidate trial-code cells versus 18 titled trials | Cannot count independent experiments or define site-held-out validation |
| P2: 2016 multiplicity | Original extract/ETL lineage, record/replicate schema and an explanation for 1,192 exact rows repeated 100× in **both** source formats | No principled deduplication or effective sample size |
| P3: observation identity | Repeated-assessment protocol, within-plot scoring units, subsample IDs and explanation for 23 same-key events with distinct response values | Cannot specify observational or residual correlation structure |
| P4: response endpoints | Full codebook for `Value`, units, possible disease/yield mixtures, zeros, censoring and measurement times | No valid endpoint harmonization or efficacy estimand |
| P5: intervention assignments | Treatment ID to fungicide/product, dose, application date, comparator and untreated status, including block assignment by trial | No causal contrast or recommendation |
| P6: provenance/rights | Trial protocol or authoritative supplement with reusable data/documentation terms | Cannot redistribute source rows or promote a model without verified design |

The EuroBlight methodology for other potato trials is **not** assumed to be
the Corteva study's protocol. Its sites, treatments, controls and years may
differ. An analogous design is not evidence of this specific randomization.

## Reproduction and artifact contract

With the two exact original Zenodo files saved locally **outside** this
repository, install the development dependencies (including `rdata==1.1.0`),
then run:

```bash
python -m crop_protection_ps.potato_binary_parity \
  --rdata /path/to/corteva-potato-late-blight.Rdata \
  --tsv /path/to/corteva-potato-late-blight.txt \
  --output results/real_potato_late_blight/binary_parity.json
```

Repeat with `--check` to fail if the output diverges from the committed
report. The [module](../src/crop_protection_ps/potato_binary_parity.py)
compares the original bytes without modifying or silently correcting either
source. The [offline tests](../tests/test_potato_binary_parity.py) use toy
data frames for rejection cases and verify the checksum-pinned derived report;
CI does not fetch either Zenodo file. This is **source-format validation**,
not a fourth empirical efficacy or model-validation result.
