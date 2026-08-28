# Scientific case: from field trial to R&D decision

## Question

How should a predictive scientist estimate insecticide efficacy across heterogeneous environments,
quantify the risk of over-optimistic validation, and choose the next informative experiment?

## Statistical structure

The demonstrator treats field observations as a hierarchical experiment rather than IID rows.
A site-year-block contains formulation × dose combinations, with mortality generated from an
explicit binomial observation model.

The latent efficacy process contains:

- a non-linear dose-response curve;
- formulation-specific potency;
- site and year heterogeneity;
- spray-coverage mediation;
- temperature and rainfall effects;
- finite-sample binomial variation.

This structure creates a useful validation problem: random K-fold CV estimates interpolation into
sites already represented in training data, whereas leave-one-site-out validation estimates a
more demanding R&D question — performance at a new site.

## Modelling choices

1. **Four-parameter logistic dose-response** to estimate ED50 and ED90.
2. **Cluster bootstrap** over trial IDs to preserve within-trial dependence.
3. **Random-intercept mixed model** to make site heterogeneity explicit.
4. **Random-forest predictive model** as a flexible non-linear benchmark.
5. **Leave-one-site-out validation** to measure extrapolation risk.
6. **D-optimal sequential design** to select future conditions that add information rather than
   merely repeating high-confidence regions.

## Decision principle

The model is not the endpoint. The intended chain is:

> scientific question → experiment → model → uncertainty → validation → next experiment

That is the central design principle of this repository.
