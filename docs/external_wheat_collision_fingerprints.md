# Wheat source: observation overlap among trial IDs at shared geocodes

The [geocode hierarchy audit](external_wheat_site_hierarchy.md) established
that the original wheat source has 76 `TrialId` values, 65 rounded
geocode–years, and 56 rounded geocodes. Nine geocode–years contain more than
one trial ID. This follow-up asks **whether those IDs also share observation
dates, endpoint descriptions, or records**, without treating a shared
geocode as a confirmed physical trial.

The source is [Holst (2022), Zenodo 6521175](https://doi.org/10.5281/zenodo.6521175).
The [IPM Decisions D4.8 report](https://www.ipmdecisions.net/media/vovnkaon/d4-8-selected-datasets-are-made-available-for-validation-of-dss-systems-by-other-end-users.pdf)
documents its 0.1° georeferencing precision. Both references describe the
data context; neither provides a plot-level replicate dictionary here.

## Observed overlap in the unchanged source

| Descriptive statistic | Count |
| --- | ---: |
| Source records | 2,276 |
| Geocode–years containing multiple `TrialId` values | 9 |
| Distinct `TrialId` values in those groups | 20 |
| Pairwise comparisons among those IDs | 14 |
| Pairs with at least one shared assessment date | 10 |
| Pairs with at least one matching assessment signature | 3 |
| Pairs with records exactly matching except for `TrialId` | 3 |
| Total exact cross-ID record matches counted pairwise | **22** |

The three pairs with matching assessment signatures are:

| Country, year | Trial IDs | Shared assessment signatures | Exact record matches excluding `TrialId` |
| --- | --- | ---: | ---: |
| Bulgaria, 2019 | 31 and 32 | 13 | 8 |
| Bulgaria, 2019 | 33 and 34 | 17 | 11 |
| Poland, 2019 | 53 and 57 | 13 | 3 |

An *assessment signature* excludes trial ID, treatment and the response
value. It fixes observation date, days after treatment, growth stages,
organism, parameter, clarifier, measurement method, sample unit and plant
part. The reported **exact record matches** are stricter: all 16 original
source fields except `TrialId` must match, including the treatment label,
spray count and recorded value. Multiset intersection counts at most the
number of repeated records present in each trial ID, so a repeated row
cannot inflate the match beyond its counterpart's multiplicity.

The result is an observable source-data overlap, not an established
duplication of experiments or observations. For example, two independent
plots can have identical recorded values, and generic treatment codes may
be reused across unrelated trials. Even matching entire rows does not reveal
whether they came from the same field plot or from distinct plots under the
same measurement protocol.

## How to reproduce

Run from the repository root:

```bash
PYTHONPATH=src python -m crop_protection_ps.wheat_collision_fingerprints \
  --data-dir data --output results/external_wheat_collision_fingerprints.json
```

Check the committed report without writing:

```bash
PYTHONPATH=src python -m crop_protection_ps.wheat_collision_fingerprints \
  --data-dir data --output results/external_wheat_collision_fingerprints.json --check
```

The calculation first verifies original file checksums and regenerates the
earlier geocode hierarchy, rejecting a missing or stale predecessor report.
It then produces deterministic trial-level summaries and pairwise overlap
counts for all nine ambiguous geocode–years. It does not alter inputs,
impute missingness, drop overlapping rows, or fit a statistical model.

## Decision and follow-up evidence

The [external analysis-eligibility contract](external_analysis_eligibility.md)
still requires independent protocol evidence before a trial-level treatment
effect can be estimated. In particular:

1. Ask the data custodian whether `TrialId` codes `31/32`, `33/34`, and
   `53/57` represent separate experiments, repeated plot series or other
   administrative divisions.
2. Obtain plot/replicate identifiers and the randomization scheme for these
   IDs. Check how control plots and coded treatments were assigned.
3. Reconcile the publisher's 56-trial description with the 76 source IDs
   without assuming that equality with 56 rounded geocodes settles the issue.
4. If independent trial units become identifiable, specify the estimand and
   prevent duplicate source observations from being counted twice.

**No observations are declared duplicated or removed by this audit.**
