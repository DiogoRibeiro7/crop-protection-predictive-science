# Wheat observations: cross-fold overlap under four split rules

The original [BASF wheat field-trial release](https://doi.org/10.5281/zenodo.6521175)
contains 2,276 observations but does not identify experimental plots or
replicates. Its 76 recorded `TrialId` labels sit within 65 **rounded
geocode–years** and 56 **rounded geocodes**. The upstream
[IPM Decisions D4.8 deliverable](https://www.ipmdecisions.net/media/vovnkaon/d4-8-selected-datasets-are-made-available-for-validation-of-dss-systems-by-other-end-users.pdf)
confirms 0.1° location precision and describes 56 trials, but does not supply
a 76-to-56 trial crosswalk. The [binary source audit](external_wheat_binary_parity.md)
found no additional trial or plot identifier.

This audit addresses a distinct question: **what recorded source groups
could appear on both sides of a five-fold validation partition?** It
compares four deterministic assignments without fitting any model,
estimating an effect, deduplicating rows, or claiming that a recorded group
is an independent trial.

## Results on the unchanged 2,276-row dataset

| Split assignment | Trial IDs across folds | Geocode–years across folds | Geocodes across folds | Cross-ID exact-record signatures across folds |
| --- | ---: | ---: | ---: | ---: |
| Random source rows | **76 / 76** | **65 / 65** | **56 / 56** | **19 / 22** |
| Whole `TrialId` | 0 / 76 | **9 / 65** | **10 / 56** | **22 / 22** |
| Whole geocode–year | 0 / 76 | 0 / 65 | **6 / 56** | 0 / 22 |
| Whole geocode | 0 / 76 | 0 / 65 | 0 / 56 | 0 / 22 |

“Across folds” means a recorded grouping key occurs in more than one of
the five assigned test folds; equivalently, that key is present in the
training complement of at least one test fold. It is **not** proof that the
same physical trial or plot occurs on both sides.

The `TrialId`-grouped split is the striking case. Although it keeps every
`TrialId` in a single fold, it leaves **nine geocode–years with records in
multiple folds**, encompassing **522 source rows**. Moreover, **22 distinct
full-record signatures** shared by different `TrialId` labels appear across
folds, covering **44 rows**. Those are exact *source-value* matches after
excluding `TrialId`, not verified duplicate experiments. A matching crop
measurement can arise independently in separate plots.

Grouping by geocode–year removes those recorded collisions in this
five-fold partition, but still leaves six rounded geocodes represented in
multiple folds (438 rows). Grouping by geocode keeps each published
location entirely in one fold. Given the 0.1° coordinate precision, this
last rule may overgroup distinct physical fields, and it is **not** a
replacement for the missing protocol.

The fold sizes (rows, in fold order) are:

| Split assignment | Fold 1 | Fold 2 | Fold 3 | Fold 4 | Fold 5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Random source rows | 456 | 455 | 455 | 455 | 455 |
| Whole `TrialId` | 454 | 454 | 454 | 461 | 453 |
| Whole geocode–year | 455 | 454 | 453 | 460 | 454 |
| Whole geocode | 459 | 459 | 450 | 458 | 450 |

## Reproduction and interpretation

The [committed JSON audit](../results/external_wheat_split_contamination.json)
uses **five folds** and the fixed seed `20261106`. Source rows are shuffled
by that seed for the row-wise split. Grouped splits use whole keys, shuffling
the sorted keys before assigning larger groups to the currently least-filled
fold, with deterministic tie-breaking. No response values enter assignment
decisions. The exact-record comparison uses all 16 original columns except
`TrialId` and counts only signatures observed under different trial IDs.

The script checks source checksums and verifies that its preceding
[site hierarchy](external_wheat_site_hierarchy.md) and
[collision fingerprint](external_wheat_collision_fingerprints.md) reports
still match the published input.

Generate or check the report from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.wheat_split_contamination \
  --data-dir data --output results/external_wheat_split_contamination.json

PYTHONPATH=src python -m crop_protection_ps.wheat_split_contamination \
  --data-dir data --output results/external_wheat_split_contamination.json --check
```

This is a partition-structure diagnostic, **not an external-validation
score**. Row-wise cross-fold overlap is especially problematic if the
intended deployment is prediction for a previously unseen trial or area.
If the use case instead concerns additional observations within known
trials, the evaluation question would differ; neither design resolves
within-plot correlation or guarantees absence of information leakage.

The existing [analysis eligibility policy](../data/external/analysis_eligibility.json)
continues to classify `trial_level_treatment_effect` as `requires_protocol`.
We still need the original mapping of 56 claimed trials to 76 IDs, plot and
replicate identity, treatment-code definitions, and endpoint protocol.
**No observational grouping is promoted to an experimentally identified
unit by this audit.**
