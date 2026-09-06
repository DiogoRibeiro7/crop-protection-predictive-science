# Roadmap

## Current status

The current empirical modelling programme is complete for the data presently in the repository.
The project remains active as a reproducible portfolio and can be reopened when genuinely new
evidence changes the scientific question.

Two independent public field-data cases are now represented:

- a hop fungicide-timing experiment with source-defined exclusion handling, paired treatment
  contrasts and leave-one-year-out validation;
- a multi-environment southern corn leaf blight phenotyping dataset with scalar disease burden,
  functional trajectory comparison and prospective leave-one-environment-out transport.

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

## Highest-value future empirical work

The strongest extension would not be a more complex algorithm. It would be a linked discovery-stage
dataset spanning laboratory, glasshouse and field evidence with programme decisions and experimental
costs recorded prospectively. That would test the repository's multi-fidelity and portfolio ideas on
real decision history rather than controlled simulations.

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
