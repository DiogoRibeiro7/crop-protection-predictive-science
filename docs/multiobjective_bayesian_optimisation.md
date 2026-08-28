# Constrained multi-objective Bayesian optimisation

Version 0.8.0 adds a controlled formulation/application search problem above the earlier field-trial,
experimental-design and portfolio layers. The scientific question is no longer only which candidate
should advance. It is:

> **Which condition should be tested next when potency, environmental performance and crop safety
> are all relevant at the same time?**

The experiment is synthetic by design. It does not invent proprietary formulation data. A finite
candidate grid provides hidden ground truth for controlled evaluation, while the optimiser sees only
noisy experimental observations.

## Search space

Each condition has three normalised design variables:

\[
x=(d,f,a),
\]

where the coordinates represent dose, a formulation property and adjuvant level. The controlled DGP
maps them to three responses:

\[
E(x)=\text{efficacy},
\qquad
B(x)=\text{environmental burden},
\qquad
I(x)=\text{crop injury}.
\]

The optimisation problem is

\[
\max E(x),
\qquad
\min B(x),
\]

subject to the hard feasibility rule

\[
I(x)\le 0.34.
\]

The response surfaces contain nonlinear dose response, formulation/adjuvant optima and interactions.
They are known only to the evaluation harness, never to the optimiser.

## Bayesian surrogate

For each endpoint, the repository fits an independent conjugate Bayesian nonlinear response surface

\[
y=\phi(x)^\top\beta+\varepsilon,
\qquad
\beta\sim N(0,\lambda^{-1}I),
\qquad
\varepsilon\sim N(0,\sigma^2).
\]

The basis \(\phi(x)\) contains polynomial terms, pairwise interactions, sinusoidal terms and a small
fixed radial-basis dictionary. This is deliberately more transparent than a heavily tuned black-box
surrogate: posterior means, posterior covariance and predictive uncertainty can all be inspected
analytically.

The model is not claimed to be a production surrogate. Its purpose is to make the Bayesian
optimisation mechanics auditable.

## Constrained acquisition

The multi-objective policy uses a ParEGO-style scalarisation. At sequential step \(t\), efficacy and
sustainability \(1-B(x)\) are combined as

\[
S_t(x)=w_t E(x)+(1-w_t)(1-B(x)),
\]

with deterministic weights spanning the trade-off during the optimisation run.

Expected improvement is then multiplied by posterior feasibility probability:

\[
\alpha_t(x)
=
EI_t(x)\,
P\{I(x)\le0.34\mid D_t\}^{\gamma}.
\]

The locked experiment uses \(\gamma=1.25\).

This is an approximation to constrained multi-objective Bayesian optimisation. It is intentionally
labelled as such. The value of the experiment comes from comparing its decisions against the hidden
feasible Pareto frontier, not from naming a sophisticated acquisition function.

## Equal-budget policies

All policies start with the same 12-point space-filling design and receive 18 additional evaluations,
for exactly 30 experiments each.

Three policies are compared:

1. **Random** — evaluates an unevaluated condition uniformly at random.
2. **Efficacy only** — constrained expected improvement on efficacy, ignoring environmental burden
   in the objective.
3. **Constrained Pareto** — scalarised efficacy/environmental expected improvement with posterior
   crop-safety feasibility.

The same noisy observation field is used across policies within a rollout so comparisons are paired.

## Evaluation metric

For controlled scoring, the hidden finite grid gives the exact safe Pareto set. Environmental burden
is converted to a larger-is-better sustainability score

\[
Q(x)=1-B(x).
\]

The main metric is feasible dominated hypervolume in

\[
(E,Q)
\]

relative to reference point \((0,0)\), expressed as a fraction of the oracle feasible Pareto
hypervolume.

The release also records:

- unsafe evaluation rate;
- recall of exact oracle-frontier grid points;
- number of balanced high-value conditions encountered;
- best feasible efficacy and environmental burden observed.

Hypervolume is preferred to a single weighted score because the scientific objective is explicitly a
trade-off rather than one pre-agreed utility function.

## Locked result

Across 50 paired rollouts, mean feasible hypervolume ratios are approximately:

| Policy | Hypervolume / oracle | Unsafe evaluation rate |
| --- | ---: | ---: |
| Random | 0.835 | 0.251 |
| Efficacy only | 0.832 | 0.296 |
| Constrained Pareto | **0.902** | **0.194** |

Thus the multi-objective policy improves mean hypervolume by about **8.4%** versus efficacy-only
search. The paired 95% Monte Carlo interval for the hypervolume-ratio difference is approximately

\[
\boxed{[0.064,\ 0.076]}.
\]

Its unsafe-evaluation rate is also lower than random search by about 5.7 percentage points, with the
paired interval remaining below zero.

The pre-specified promotion gate requires both:

1. at least 8% mean hypervolume improvement versus efficacy-only search; and
2. a paired 95% Monte Carlo interval for the hypervolume-ratio difference entirely above zero.

Both conditions pass.

## Interpretation

The main lesson is not that one acquisition function is universally best. It is that optimising only
for efficacy can be structurally wrong when the R&D decision is multi-objective.

\[
\boxed{
\text{best potency}
\neq
\text{best feasible scientific trade-off}
}
\]

The safety constraint also matters during exploration. A Bayesian optimiser should use uncertainty
about feasibility to decide where experimentation is scientifically defensible, not simply discover
unsafe regions after the fact.

## Limitations

- The entire v0.8 search space is controlled synthetic data.
- Dose, formulation and adjuvant coordinates are abstract normalised variables, not product-use
  recommendations.
- The three response surfaces are independent in the surrogate even though real endpoints may have
  correlated observation and process errors.
- The fixed basis is intentionally interpretable but may be misspecified.
- ParEGO-style scalarisation does not provide exact expected hypervolume improvement.
- The candidate space is finite; continuous constrained optimisation would require an additional
  optimisation layer.
- Crop safety is represented by one scalar threshold. Real safety and environmental assessment are
  substantially more complex and domain-specific.

These restrictions are part of the methodological demonstration rather than hidden shortcomings.
