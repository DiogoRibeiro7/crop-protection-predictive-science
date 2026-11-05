# External research protocol evidence review and request pack

The [research-readiness ledger](external_analysis_readiness.md) now has
source-checked reports for **all 36 permitted descriptive actions**. That
milestone does not resolve the experimental-design requirements for
inferential analyses. The next step is to request verifiable protocol evidence
from the original sources.

This review converts the 59 requirements in the
[eligibility contract](../data/external/analysis_eligibility.json)
into **35 distinct, specific requests**, without changing any permission.
The 59 entries refer to 19 source-table analysis questions; some of the same
protocol requirements apply to several aphid experiments or Dryad strains.
They are not 59 independent research tasks.

## Reproduce and inspect

Run offline from the repository root:

    PYTHONPATH=src python -m crop_protection_ps.external_protocol_review
    PYTHONPATH=src python -m crop_protection_ps.external_protocol_review --check

The command:

1. Revalidates the checksum-pinned original snapshots, the eligibility
   contract and all existing descriptive reports via the readiness ledger.
2. Requires every existing protocol requirement to have exactly one
   human-reviewed question and a concrete description of the evidence needed.
3. Locates 14 exact context phrases in the unmodified aphid and Dryad source
   READMEs, recording original file paths, SHA-256 hashes and line numbers.
4. Verifies that the compiled request keys exactly match the 59 still-gated
   source-table requirements, without adding or clearing an action.

The questions themselves are held in a separate, editable
[request configuration](../data/external/protocol_review_questions.json).
It is a research work plan, **not** part of the imported source data or an
authorization to train models.

## What the output establishes

| Scope | Count | Interpretation |
| --- | ---: | --- |
| Source observation tables | 18 | Same original assets as the eligibility contract. |
| Source policy families | 10 | Group related questions without pooling study designs. |
| Gated source-table analysis questions | 19 | No inferred clearance. |
| Required protocol entries | 59 | Remain not_cleared_by_contract. |
| Distinct requirement templates | 35 | Investigator questions with requested evidence types. |
| Exact original-README anchors | 14 | Navigable partial context, not protocol certification. |
| Requirement entries with a linked README clue | 41 | A source phrase was located, but the requirement remains gated. |
| Requirement entries without curated README clue | 18 | Not evidence that the source paper lacks the information. |
| Approved inferential actions | 0 | The eligibility contract is unchanged. |

### Generated artifacts

| File | Use |
| --- | --- |
| [author_evidence_requests.md](../results/external_protocol_review/author_evidence_requests.md) | Shareable set of 35 distinct, actionable investigator questions, grouped by policy and model proposal. |
| [requirement_requests.csv](../results/external_protocol_review/requirement_requests.csv) | Traceable 59-row asset/analysis/requirement registry with the original permission, question and requested evidence. |
| [original_source_anchors.csv](../results/external_protocol_review/original_source_anchors.csv) | Exact source README phrases and locations; inspect context before relying on any interpretation. |
| [summary.json](../results/external_protocol_review/summary.json) | Source and contract hashes, count reconciliation, still-uncleared status and review limitations. |

The read-only check fails if source anchors, contract/question coverage,
counts or committed artifacts are stale.

## Practical order for evidence acquisition

1. **Resolve experimental units before effect sizes.** Start with wheat's 56
   advertised trials versus 76 recorded trial IDs, including plot/block
   identities and the treatment dictionary. The geocode hierarchy audit
   suggests potential explanations but does not establish a physical-trial key.
2. **Request plot and randomization definitions for the aphid field study.**
   Its README names Replicate, Treat, Date and Mortality, but does not
   independently establish randomized plots or the dependence between
   day-3/day-7 measurements. The four controlled aphid experiments require
   their own chamber/batch allocation evidence.
3. **Reconcile the Dryad weather defects against station records.** The
   30 August 2021 low is missing, and 31 August has Low above High.
   Date matching is known; the actual exposure interpretation is not.
4. **Obtain chamber, run and plant-identity protocols for Dryad assays.**
   Source README summaries identify trait measurements, field status codes
   and the weather station, but do not specify the full independent
   experimental-unit and censoring structure. The README mentions seven
   analysis R scripts that are not present in the imported archive.

This order is a practical suggestion, not a claim that those documents are
available, sufficient or absent from the full original publications.

## Scientific boundaries

- Original README snippets are recorded as *original_readme_hint_only*,
  never as approved protocol evidence. No snippet alone establishes
  randomization, independence, event definitions or causal identification.
- *no_curated_readme_hint* means this limited review has no selected anchor.
  Consult the original paper and researchers before concluding the
  information is unavailable.
- The wheat source import does not contain a separately pinned original-source
  README. The review therefore does not manufacture a source-text citation for
  its unresolved requirements.
- Obtaining one document or resolving one reading is not enough to promote an
  inferential model. All applicable requirements must be reviewed together,
  followed by a separately tested versioned change to the eligibility contract.
- No author has been contacted by this repository workflow, and no source
  measurements, statistical outcomes, or causal estimates have been changed.
