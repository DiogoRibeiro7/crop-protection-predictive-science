# Bipolaris prospective-model promotion contract

## Purpose

The southern corn leaf blight case now has a leave-one-environment-out benchmark based on same-hybrid history from the remaining field environments. A richer environment model must not be added simply because it fits the pooled data better.

This document fixes the evaluation contract **before** any richer candidate model is fitted.

## Evaluation population

Every candidate must use exactly the same held-out environments and the same evaluated hybrids per fold as the current leave-one-environment-out benchmark.

A candidate is invalid if it:

- drops a difficult held-out environment;
- evaluates fewer hybrids in a fold;
- uses held-out outcomes to construct features, select hyperparameters, choose covariates or tune preprocessing;
- changes the disease-progress window or functional grid only for the candidate.

Missing folds or changed hybrid counts are treated as evaluation errors, not as model performance.

## AUDPC burden promotion rule

The reference model is the existing same-hybrid history predictor:

\[
\widehat{AUDPC}_{h,e}
=
\operatorname{mean}_{e'\neq e} AUDPC_{h,e'}.
\]

A richer candidate is promoted only if **all** of the following hold on the identical leave-one-environment-out folds:

1. pooled held-out AUDPC RMSE is lower than the hybrid-history baseline;
2. candidate RMSE is lower in a strict majority of held-out environments;
3. weighted mean held-out hybrid-rank MAE does not increase.

The pooled RMSE reconstructs the overall mean squared error from fold RMSE and evaluated-hybrid counts rather than averaging fold RMSE values equally.

There is deliberately no post-hoc percentage-improvement threshold or significance test. The number of independent field environments is too small to justify pretending a conventional p-value establishes transportability.

## Functional-shape promotion rule

For normalized disease-curve trajectories, the reference predictor is the pointwise mean trajectory for the same hybrid in the training environments.

A richer shape model is promoted only if:

1. weighted held-out trajectory RMSE decreases;
2. the candidate wins a strict majority of held-out environments;
3. the evaluated environment and hybrid populations are unchanged.

## Why the rule is conjunctive

A pooled average alone can hide a model that performs very well in one environment and worse in most others. A fold-win rule alone can reward tiny improvements while allowing a large degradation elsewhere. Ranking alone can preserve ordering while badly missing absolute disease burden.

The promotion decision therefore requires both aggregate predictive improvement and environmental consistency, with ranking protected for the host-selection use case.

## Interpretation

Passing this gate would justify further investigation of a richer prospective environment model. It would **not** establish causal environmental effects, general cultivar recommendations or industry-wide transportability.

Failing the gate is a legitimate scientific result. In that case the repository should retain the simpler hybrid-history predictor and document that the richer candidate did not earn promotion.
