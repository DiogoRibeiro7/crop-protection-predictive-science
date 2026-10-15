# Robust Observation Design Under Parameter Uncertainty

This note extends the local Fisher-information observation-design layer for the
synthetic transport-reaction model.

The earlier design analysis scores candidate space-time observation sets at one
declared nominal parameter point. That is useful but can be brittle when the
nominal diffusion or decay rate is wrong.

The robust-design layer therefore evaluates the same fixed observation design
over a finite declared uncertainty set of positive transport parameters.

## Question

Given a fixed observation budget, does a design remain informative when the
true diffusion and decay differ from the nominal design point?

For each scenario

\[
(D_j,k_j),
\]

the existing Fisher-information machinery produces a local design score.

The robust layer aggregates those scenario-specific results without changing
the underlying forward model or sensitivity calculation.

## Declared uncertainty set

The regression tests use five scenarios:

\[
(0.020,0.12),\quad
(0.020,0.24),\quad
(0.035,0.18),\quad
(0.055,0.12),\quad
(0.055,0.24).
\]

The middle point

\[
(D,k)=(0.035,0.18)
\]

is the nominal scenario used in the earlier known-truth inverse experiment.

The other scenarios deliberately vary diffusion and decay in both directions.

This finite set is a design stress test, not a probability distribution.

## Reported diagnostics

For each candidate design, the implementation reports:

- D-optimality at the nominal scenario;
- mean D-optimality across the declared scenarios;
- worst-case D-optimality;
- worst-case information-matrix condition number;
- number of rank-deficient scenarios.

A design is called robustly identifiable over this declared set only when every
scenario produces a full-rank local Fisher information matrix.

## Equal-budget comparison

The same 12-observation budget is retained from the local design analysis.

### Centre-only temporal design

Repeated measurements at the centre cell of the cosine-mode initial condition
remain weak for diffusion.

The robust test requires this design to stay rank deficient across every
declared parameter scenario.

Accordingly:

- nominal D-optimality is zero;
- mean D-optimality is zero;
- worst-case D-optimality is zero;
- every scenario is rank deficient.

This demonstrates a structural design weakness rather than a bad nominal
parameter choice.

### Mixed space-time design

The mixed design uses four time points and three spatial locations, again for
12 observations in total.

The robust test requires this design to remain full rank across all declared
scenarios and to retain positive worst-case D-optimality.

The point is not that this design is globally optimal. The point is that its
ability to separate diffusion and decay is not confined to one finely tuned
nominal parameter point.

## Why worst-case information?

Nominal D-optimality answers:

> How informative is this design at the parameter point I used to construct it?

Worst-case D-optimality asks:

> Across the parameter scenarios I declared plausible, how bad can the
> information volume become?

This is a useful robustness diagnostic because a design that looks excellent at
one nominal point can collapse elsewhere.

The mean score is also retained, but it is not given a probabilistic
interpretation because no prior distribution is assumed.

## Interpretation

This extension is finite-scenario robust design.

It is not:

- Bayesian design;
- expected-utility optimisation;
- continuous minimax optimisation;
- proof of global structural identifiability;
- evidence that the selected scenario grid spans all scientifically plausible
  transport behaviour.

Its value is transparency: the uncertainty set is explicit, every scenario is
scored with the same local Fisher machinery, and worst-case failure cannot be
hidden inside an average.

## Scope boundary

This remains controlled scientific-computing evidence.

It does not define:

- pesticide sampling plans;
- environmental monitoring networks;
- real laboratory costs;
- regulatory study designs;
- real transport-parameter ranges.

The transferable lesson is methodological: when an observation design depends
on uncertain model parameters, test the design across a declared uncertainty
set rather than assuming nominal-point optimality will automatically persist.
