# Selecting a Robust Transport Observation Design

This note extends the synthetic transport-reaction design programme from
scoring candidate designs to selecting one design from a finite declared
candidate set.

The selection rule is intentionally simple and auditable.

## Decision contract

All candidates must use the same observation budget.

Each candidate is scored across the same declared diffusion/decay uncertainty
set using the finite-scenario robustness layer.

A candidate is eligible only if its local Fisher information matrix remains full
rank for every declared scenario.

Among eligible candidates, selection maximises worst-case D-optimality.

If multiple candidates tie on worst-case D-optimality, deterministic secondary
criteria are used:

1. larger mean D-optimality;
2. better worst-case conditioning;
3. candidate name as the final reproducible tie-break.

Rank-deficient candidates cannot win.

## Why use a hard rank gate?

Worst-case D-optimality already collapses to zero for a rank-deficient scenario,
but the rank gate is kept explicit because it represents a scientific
constraint:

> a design that fails to identify both parameters anywhere in the declared
> uncertainty set is not considered robustly admissible.

This separates feasibility from preference.

## Finite candidate set

The regression test compares the same three equal-budget designs used in the
earlier design work:

- centre-only temporal sampling;
- final-time spatial sampling;
- mixed space-time sampling.

Each uses 12 observations.

The centre-only design is deliberately rank deficient for every declared
transport scenario and is therefore ineligible.

The selector must choose one of the full-rank spatial or mixed designs according
to worst-case D-optimality.

## Deterministic ranking

The result contains the complete ranked candidate list, not only the winner.

Each ranked record includes:

- candidate name and design;
- robust scenario summary;
- eligibility status;
- deterministic rank.

This makes the final choice auditable and preserves rejected alternatives.

Candidate input order must not change the selected design or final ranking.

## Interpretation

This is finite-candidate robust selection.

It answers:

> Of these explicitly declared equal-budget designs, which admissible candidate
> has the strongest worst-case local information volume over the declared
> parameter scenarios?

It does not establish:

- global optimality over all possible observation designs;
- continuous minimax optimality;
- Bayesian expected utility;
- optimality under real sampling costs;
- global structural identifiability.

The candidate set itself remains part of the scientific design contract.

## Scope boundary

This remains controlled synthetic methods evidence.

It does not define:

- pesticide-monitoring schedules;
- environmental sampling networks;
- regulatory study designs;
- field sampling costs.

The transferable lesson is methodological: make the candidate set explicit,
enforce scientific feasibility before ranking, and preserve the complete
decision record rather than reporting only the winning design.
