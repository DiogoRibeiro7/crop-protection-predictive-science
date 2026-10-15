# Exact Finite-Pool Benchmark for Greedy Transport Design

This note quantifies the optimality gap of the greedy sequential robust design
used in the synthetic transport-reaction programme.

The earlier sequential method chooses the next observation greedily from a
finite candidate pool. That is practical and transparent, but it is not
guaranteed to produce the globally best fixed-budget subset.

For the current small candidate pool, exhaustive subset enumeration is
tractable. The exact benchmark therefore turns that qualitative limitation into
a measurable quantity.

## Problem

Given:

- a fixed seed observation design;
- a finite candidate pool of additional space-time observations;
- a required number of additions;
- a declared diffusion/decay uncertainty set;

enumerate every candidate subset of the required size and score the resulting
completed design with the existing finite-scenario robust Fisher-information
criterion.

For each completed design, the primary score is worst-case D-optimality across
the declared parameter scenarios.

## Exact finite-pool optimum

If the candidate pool contains \(m\) observations and exactly \(r\) must be
added, the number of subsets is

\[
\binom{m}{r}.
\]

Every subset is evaluated.

The best subset is selected with the same deterministic ranking logic used
elsewhere in the repository:

1. robust full-rank status;
2. worst-case D-optimality;
3. mean D-optimality;
4. worst-case conditioning;
5. deterministic space-time tie-breaking.

The result is exact for the declared finite pool and budget.

## Greedy comparison

The same seed, candidate pool, scenario set and number of additions are passed
to the sequential greedy method.

The benchmark reports:

- exact optimal subset;
- exact optimal worst-case D-optimality;
- greedy final design;
- greedy worst-case D-optimality;
- absolute optimality gap;
- relative optimality gap.

The absolute gap is

\[
\Delta
=
D_{\text{exact}}
-
D_{\text{greedy}},
\]

and the relative gap is

\[
\frac{\Delta}{D_{\text{exact}}}
\]

when the exact score is positive.

The greedy score is required never to exceed the exact optimum beyond numerical
tolerance.

## Determinism

The exact optimum must not depend on the order in which the candidate pool is
supplied.

Subsets are generated from a sorted candidate pool and ranked
deterministically.

This matters because reproducibility should not depend on incidental input
ordering.

## Combinatorial safety limit

Exhaustive enumeration grows combinatorially.

The implementation therefore requires an explicit maximum number of subsets.
If

\[
\binom{m}{r}
\]

exceeds that safety limit, the benchmark refuses to run.

This keeps the method honest: exhaustive search is used only when it is
actually exhaustive and computationally reasonable.

## Interpretation

This benchmark answers:

> For this exact finite candidate pool, seed, uncertainty set and budget, how
> far is the greedy sequential design from the best possible subset?

It does not establish:

- continuous global design optimality;
- optimality over unenumerated space-time points;
- Bayesian expected-utility optimality;
- optimality under real sampling costs;
- global structural identifiability.

The candidate pool remains part of the design contract.

## Scope boundary

This remains controlled synthetic methods evidence.

It does not define:

- pesticide sampling schedules;
- regulatory monitoring plans;
- environmental sensor placement;
- real field measurement costs.

The transferable lesson is methodological: when a greedy design method is used
on a small finite candidate set, benchmark it against the exact finite optimum
rather than relying only on qualitative caveats.
