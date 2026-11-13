# Roadmap

## Current status

The current empirical modelling programme is complete for the data presently in the repository.
The project remains active as a reproducible portfolio and can be reopened when genuinely new
evidence changes the scientific question.

Three independent public field-data cases are now represented:

- a hop fungicide-timing experiment with source-defined exclusion handling, paired treatment
  contrasts and leave-one-year-out validation;
- a multi-environment southern corn leaf blight phenotyping dataset with scalar disease burden,
  functional trajectory comparison and prospective leave-one-environment-out transport.
- an independently published hop powdery-mildew scheduling trial with 12,880 plant assessments
  across eight site-year environments, original-source integrity checks and complete-block
  end-of-season comparisons against the risk-index schedule. A separate late-season experiment
  within the same paper contributes 140 quality plots from 2018–2022 and 1,120 cone infection
  records in four of those years, with 105 quality and 65 complete disease block-pair contrasts.

A **fourth independent public deposit is under source-only review**, not
promoted into the validated empirical case count. The potato late-blight Zenodo
TSV (UK/Ireland, 2013–2017) contains 127,034 source rows but only 9,013 distinct
complete-record signatures. Most excess rows occur as 1,192 exactly-100×
signatures in 2016. Although the title describes 18 trials, the release contains
18 geocoded site-year cells and 34 site-year/`Trial` code cells. The audit also
identifies 23 assessment keys with differing `Value` records. Only derived,
non-inferential source ledgers are committed; the original TSV remains at Zenodo.
The [source-identity and plot-design intake](docs/real_case_potato_source_audit.md)
must be reconciled with an original protocol and endpoint dictionary before
the source can support new estimands, effects or out-of-sample validation.

The follow-up [binary/text source-format parity audit](docs/real_case_potato_binary_parity.md)
compares the Zenodo RData and TSV at all 1,270,340 ordered cells and finds no
discrepancy. Their shared 2016 100× multiplicity is therefore not a TSV-only
artifact. Unused R factor levels are not observations or additional trials.
The IPM Decisions deliverable documents 0.1° geocode precision, further
limiting site identity. Six concrete protocol evidence gates remain open:
trial mapping, 2016 ETL lineage, subsample identities, endpoint semantics,
treatment allocation and source rights. The [original-source evidence request](results/real_potato_late_blight/protocol_evidence_request.md)
turns these into six answerable questions, with explicit decision rules and
no claim that the investigators have been contacted. No inferential program reopens on
parity evidence alone.

The third case reopens **source acquisition and descriptive field-study comparison only**. It
does not reopen the six-environment Bipolaris model-selection sequence or create prospective
out-of-sample evidence for the synthetic decision layers. The next scientifically defensible
step would require a predeclared follow-up estimand and independent validation, not an additional
post-hoc choice among the four scheduling arms.
The additional cone-quality outcomes do not lift that boundary. Their farm identities differ
across 2018–2020, Farm3 recurs after 2020, and an original alpha-acid extreme is retained with
systematic block-deletion diagnostics instead of being edited to improve a contrast.

The cone-disease missingness sensitivity now provides sharp worst-case ranges for
the same predefined field-block contrasts. It retains 19 additional partially
identified disease comparisons instead of dropping them or treating missing
plants as healthy. All 2018–2019 annual contrast ranges cross zero, so their
signs are not identified from the observed source data alone. In 2020 and
2022 the missing-data bounds collapse to observed point differences; that is
not a statement about sampling uncertainty or causal treatment effects.
The 2021 disease source is absent, not bounded as a disease-free year.

For the Bipolaris case, the current dataset contains 1,105 observations across six field
environments and 13 hybrids. The functional audit finds 74 environment×hybrid curves and all 74
satisfy the fixed 30–110 DAE support, assessment-count and mean-severity requirements. The current
functional-shape result is therefore not conditional on silent curve exclusions.

The same-hybrid history baseline improves mean held-out AUDPC RMSE relative to the global-training
mean and wins four of six held-out environments. A richer candidate that adds the pre-known
planting-window label improves pooled AUDPC RMSE from 533.24 to 467.96 and weighted shape RMSE from
0.29665 to 0.28251, but wins only three of six environments for each endpoint. The promotion rule
was frozen before that candidate was evaluated and requires four of six wins, so the candidate is
rejected for both burden and shape.

## Model-selection stop boundary

No additional Bipolaris model candidate should be promoted using only these same six environments.

The reason is not that further models are impossible. It is that repeated candidate invention after
seeing the same held-out folds would turn the six environments into an adaptive model-selection set.
A later candidate could look better simply because the analyst has learned the idiosyncrasies of
those environments through prior failures.

Accordingly:

- the current hybrid-history baseline remains the retained prospective burden model;
- the planting-window candidate remains a recorded negative result;
- new models fitted and compared only on the same six environments are exploratory and must not be
  described as prospectively promoted;
- the frozen promotion criteria must not be relaxed because the first richer candidate failed them;
- no new threshold should be chosen from the observed fold-level errors.

## What would justify reopening Bipolaris model selection

A new prospective model-selection round requires information that was not used to design the current
candidate sequence. Suitable triggers include at least one of the following:

1. New independent field environments or seasons with the same endpoint and enough hybrid overlap to
   support the existing leave-one-environment-out estimand.
2. Prospectively recorded field covariates such as weather, phenology, initial disease pressure,
   planting date or protocol metadata, with their availability time defined before outcome access.
3. A scientifically distinct external dataset that can be used as an untouched validation set.
4. A new biological or operational estimand agreed before modelling, rather than another feature
   search against the current six environments.

If new environments are added, candidate definitions and promotion rules should be frozen before the
new outcomes are opened wherever practical.

## Newly identified source candidate: NSW barley Ramularia (metadata-only)

The [2024–2025 NSW barley Ramularia source intake](docs/candidate_nsw_barley_ramularia.md)
records four publicly listed split-plot fungicide trials (240 advertised plot
records), original trial metadata, measurement workbooks and a separate methods
PDF under publisher-stated Creative Commons Attribution terms. The advertised
block, main-plot and subplot identifiers make this a promising independent
experimental-design candidate. **No downloaded bytes have yet been checked**,
and no fourth validated case or treatment-effect analysis is claimed. The next
PR should establish source checksums, verify joins and experimental-unit
hierarchy, and perform descriptive integrity checks before selecting an estimand.
The [original-source integrity audit](docs/real_case_nsw_barley_source_audit.md)
now pins the three original files, confirms four 60-plot trials and 240 distinct
plot identifiers, and identifies a year-specific discrepancy in exported
`Mainplot`/`Subplot` coding. A physical allocation reconciliation is required
before defining split-plot treatment contrasts.

## Highest-value future empirical work

The strongest extension would not be a more complex algorithm. It would be a linked discovery-stage
dataset spanning laboratory, glasshouse and field evidence with programme decisions and experimental
costs recorded prospectively. That would test the repository's multi-fidelity and portfolio ideas on
real decision history rather than controlled simulations.

Before any such dataset is analysed, apply the metadata intake and candidate-linkage
checks described in [`docs/discovery_evidence_intake.md`](docs/discovery_evidence_intake.md).
Passing them does not establish assay comparability or authorize model promotion;
study design, endpoint harmonization and independent validation remain separate
scientific requirements.

For the intervention side, multiple crop-protection trials across sites and seasons with
field-proximal weather, phenology, initial disease pressure, application conditions and protocol
metadata would provide the replication needed to revisit environment-response and interaction
models.

## Work that does not currently justify reopening the programme

The following are not useful next steps on the existing data alone:

- trying several additional planting-window encodings until one crosses the promotion gate;
- adding higher-capacity machine-learning models without new independent validation units;
- changing the four-of-six consistency requirement after observing the current three-of-six result;
- treating the 74 eligible functional curves as evidence that the conclusions generalise beyond
  these environments;
- interpreting descriptive trajectory differences as causal planting-date or cultivar
  recommendations;
- replacing the rejected candidate with a post-hoc feature combination chosen from the same folds.

## Stand-alone synthetic methods extensions

Synthetic methods work may continue when it is scientifically distinct from the
closed empirical model-selection loop. The verified one-dimensional
transport-reaction demonstration now includes both a checked forward model and a
known-truth inverse-calibration layer with explicit identifiability diagnostics,
without using the six Bipolaris environments for another model-promotion
attempt.

Inverse calibration and local identifiability are complete under issue #45.
The known-truth experiment recovers diffusion and decay under a declared Gaussian
observation model, while a uniform-profile negative control correctly identifies
diffusion as unidentifiable.

Issue #53 extends that result with profile likelihood. Each parameter is profiled
over a declared positive log-scale range while the nuisance parameter is
re-optimised. The identified known-truth experiment must produce closed
likelihood-ratio intervals containing the true parameters, while the uniform
negative control must leave the diffusion interval open at both search
boundaries. This adds practical non-local identifiability evidence without
claiming global structural identifiability.

Issue #55 moves from diagnosis to prospective design. Candidate space-time
observation sets are scored at a declared nominal parameter point using
finite-difference log-parameter sensitivities and local Fisher information.
Equal-budget centre-only, final-time spatial and mixed space-time designs are
compared transparently, with a uniform-field negative control required to remain
rank deficient. The design criterion is explicitly local and does not imply
global identifiability or real-world sampling optimality.

Issue #57 stress-tests that local design across a finite declared uncertainty
set for diffusion and decay. Each scenario reuses the same Fisher-information
scorer, and the design summary records nominal, mean and worst-case
D-optimality, worst-case conditioning and rank failures. The mixed design must
remain full rank across the declared scenarios, while the centre-only design
must remain structurally weak. This is finite-scenario robustness, not
continuous minimax optimality or Bayesian averaging.

Issue #59 turns those robust scores into an explicit finite-candidate decision.
Equal-budget candidates first face a hard gate requiring full-rank information
across every declared scenario. Eligible designs are then ranked by worst-case
D-optimality with deterministic secondary criteria and complete ranking output.
The result is optimal only within the declared candidate set and does not claim
continuous global design optimality.

Issue #61 makes the design process incremental. Starting from a fixed seed,
each candidate next observation is scored by the same robust criterion and the
best finite-pool augmentation is accepted greedily. The full decision history is
retained, input order cannot change the sequence, and worst-case information
must not decrease across accepted additions. This remains a greedy method, not a
guarantee of globally optimal fixed-budget design.

Issue #68 quantifies that limitation whenever the candidate pool is small enough
for exhaustive search. Every subset of the requested size is evaluated under the
same finite-scenario robust criterion, giving an exact finite-pool optimum and
an absolute/relative greedy optimality gap. A subset-count safety limit prevents
the code from pretending exhaustive search is tractable when combinatorics make
it inappropriate.

Issue #70 consolidates the transport-design chain into a regenerated scientific
evidence bundle at `results/transport_design/summary.json`. The CLI persists the
declared scenarios, candidate designs, robust selection, greedy history and exact
benchmark, and the scientific contract checks qualitative conclusions rather than
pinning brittle floating-point snapshots.

## Maintenance mode

Until a reopen criterion is met, the appropriate work is maintenance rather than further model
search:

- keep CI, provenance and dependency metadata current;
- regenerate the scientific bundle when code or dependencies change;
- preserve negative results and decision records;
- update documentation when external data or the scientific scope materially changes.

The repository should remain strongest as evidence of disciplined quantitative collaboration with
experimental scientists: define the decision, respect the experimental unit, validate against the
intended deployment shift, and stop when the available data no longer support a clean next claim.
