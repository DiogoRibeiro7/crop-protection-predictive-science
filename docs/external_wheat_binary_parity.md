# Wheat binary-source verification: RData versus TSV

The original [Holst/BASF Zenodo release (v1.0)](https://zenodo.org/records/6521175)
publishes the wheat observations in two forms: `basf-wheat-diseases.txt`
and `basf-wheat-diseases.Rdata`. Earlier audits used the text file only,
because the R workspace had not been examined. This review imports that
original binary and compares it **cell by cell and in original row order**
against the checksum-pinned TSV.

## Main result

| Check | Verified finding |
| --- | --- |
| Publisher binary | 23,452 bytes; MD5 `943b8cd7276896dc2753c46bb6ed0c51` |
| R workspace objects | One object: `obs` |
| R `obs` dimensions | 2,276 rows × 17 columns |
| TSV dimensions | 2,276 rows × 17 columns |
| Ordered cells checked | **38,692** |
| Exact text/category/date/missingness mismatches | **0** |
| Unexplained numeric mismatches | **0** |
| Tiny numeric representation differences | **1**, within one IEEE-754 ULP |
| Additional plot, replicate or trial crosswalk fields | **None** |

The only binary/decimal representation difference is in `Value` on TSV
line 1161. RData stores `86.09091599999999`, whereas the TSV renders
`86.090916`, with absolute difference

\[
1.4210854715202004 \times 10^{-14}.
\]

This is a one-ULP conversion difference at that magnitude, not evidence
of a changed experimental observation. The comparison permits **at most one
ULP** between numeric double values and parsed text, and requires exact
matches for factor labels, missing-value positions, ISO dates, column order,
and observation order. It does not silently reorder rows or match records
by non-unique keys.

The original binary has the same columns as the TSV, including `TrialId`,
`Treatment`, `Organism`, `Parameter` and `Value`. Its `TreatmentA`–
`TreatmentD` strings are **factor levels**, not additional treatment
assignment columns. This rules out the hope that the binary workspace
contains a separately exposed plot dictionary or a trial crosswalk. It
does **not** rule out such documentation elsewhere in BASF's original files.

## Reproduce offline

The repo's development dependency `rdata==1.1.0` reads the R workspace.
`numpy` and `pandas` are existing project dependencies. Install the
locked development environment, then run:

```bash
poetry install --no-interaction
poetry run python -m crop_protection_ps.wheat_rdata_parity
poetry run python -m crop_protection_ps.wheat_rdata_parity --check
```

The read-only check fails if the generated JSON, the binary source checksum,
or any row-level comparison is different. The
[generated report](../results/external_wheat_rdata_parity.json) contains
the binary SHA-256, TSV SHA-256, publisher MD5, full ordered schema,
per-column missingness and any at-most-one-ULP differences with source lines.

The original binary is stored alongside the pinned wheat text file under
`data/external/zenodo_wheat_fungicide_6521175/`. Its checksum is taken from
the [previous source inventory](../data/external/wheat_publication_evidence.json),
which described the binary as *uninspected at that earlier review date*.
That historical observation is preserved. The general external manifest
remains unchanged to avoid changing provenance hashes for unrelated existing
descriptive audits; the new parity module independently verifies this
supplementary binary before parsing it.

## Scientific boundary

The published record calls the collection **56 trials**, while both original
data formats record **76 distinct `TrialId` codes**. Because the binary is
row-and-column equivalent to the TSV, it cannot resolve that discrepancy.
Matching two representations of the same observations is not independent
replication or confirmation of the experiment's design.

The eligibility contract's `trial_level_treatment_effect` decision remains
`requires_protocol`. We still need an authoritative physical-trial crosswalk,
plot/block replication, a treatment dictionary, and the disease/yield endpoint
protocol from the data owner. No causal estimate or model gate is changed.
