# Budget-constrained R&D portfolio decision layer

## Question

After the initial lab and multi-fidelity screening layers, the next R&D question is not only which
candidate predicts best. It is:

> **Which candidates should be advanced under a finite development budget, and where should the next
> follow-up experiment be spent before that decision is made?**

Version 0.7.0 addresses that question with a controlled synthetic portfolio experiment. The public
hop trial does not contain candidate-level development economics or matched safety packages, so no
real commercial portfolio is fabricated.

## Controlled candidate state

Each rollout contains 36 candidates. Candidate \(i\) has two latent technical quantities:

\[
E_i = \text{field efficacy}, \qquad S_i = \text{safety margin}.
\]

Technical success is defined only for this controlled DGP as

\[
T_i = \mathbf 1\{E_i>0,\;S_i>0\}.
\]

Each candidate also has a known downstream reward \(V_i\) if technically successful and a known
development cost \(C_i\). These are dimensionless simulation value units. They are **not** estimates of real
NPV, programme costs or attrition thresholds.

All candidates first receive noisy lab evidence about efficacy and safety. Independent Gaussian
priors and Gaussian observation models give explicit conjugate posterior distributions.

The posterior technical-success probability is

\[
p_i
=
P(E_i>0\mid D)P(S_i>0\mid D),
\]

and posterior expected net development value is

\[
u_i = p_iV_i-C_i.
\]

## Exact terminal advancement decision

The final portfolio can advance at most six candidates and must satisfy a downstream development
budget of 130 units. Advancement therefore solves

\[
\max_{x_i\in\{0,1\}}
\sum_i x_i u_i
\]

subject to

\[
\sum_i x_i C_i\le130,
\qquad
\sum_i x_i\le6.
\]

This 0/1 count-and-budget knapsack is solved exactly by dynamic programming. Reward, development
cost and technical-success uncertainty therefore all enter the decision. Sorting by efficacy alone
cannot reproduce the portfolio rule.

For controlled evaluation only, the oracle replaces \(p_i\) with the realised latent technical
success indicator. Regret is

\[
R=U_{oracle}-U_{selected}.
\]

## Follow-up experiments

Before the final advancement decision, each policy receives exactly 24 follow-up cost units.
Two experiment types are available:

| Experiment | Relative cost | Observation SD | Purpose |
| --- | ---: | ---: | --- |
| efficacy confirmation | 4 | 0.45 | reduce uncertainty in \(E_i\) |
| safety confirmation | 2 | 0.50 | reduce uncertainty in \(S_i\) |

All policies see the same latent candidates and pre-generated observation streams within a rollout.

The equal-budget policies are:

1. **Uniform**: outcome-independent balanced follow-up allocation.
2. **Uncertainty**: choose the candidate/experiment with largest expected reduction in Bernoulli
   entropy of technical success per cost unit.
3. **Portfolio-VOI**: choose the candidate/experiment with largest decision-boundary expected value
   of sample information per cost unit.

A **no-follow-up** policy is retained only as a zero-cost reference; it is not an equal-budget
comparator.

## Deterministic acquisition integration

Future observations are not ranked with noisy nested Monte Carlo. Under Normal conjugacy, the
future posterior mean has a known Normal distribution. Expectations are therefore evaluated with
15-node Gauss-Hermite quadrature.

For the uncertainty policy the acquisition quantity is

\[
\frac{H(p_i)-E[H(p_i')]}{c_a},
\]

where \(c_a\) is the experiment cost.

For portfolio-VOI, the acquisition layer approximates the current constrained portfolio boundary by
a value-per-development-cost shadow threshold \(\tau\). It then computes the option value

\[
\operatorname{EVSI}_{ia}
=
E\left[(r_i'-\tau)_+\right]-(r_i-\tau)_+,
\qquad
r_i=\frac{u_i}{C_i},
\]

and divides by experiment cost.

This is deliberately labelled an **acquisition approximation**. The final advancement set is always
computed by the exact knapsack. The heuristic is not presented as an exact solution of a nested
Bayesian portfolio-design problem.

## Locked simulation result

Across 500 paired rollouts, every equal-budget policy spends exactly 24 follow-up units.

| Policy | Mean realised portfolio value | Mean oracle regret | Technical success among advanced |
| --- | ---: | ---: | ---: |
| uniform | 245.21 | 149.51 | 75.1% |
| uncertainty | 268.06 | 126.65 | 80.9% |
| **portfolio-VOI** | **289.27** | **105.45** | **83.4%** |

Portfolio-VOI reduces regret by

\[
\boxed{16.74\%}
\]

relative to uncertainty sampling, and by

\[
\boxed{29.47\%}
\]

relative to uniform allocation.

The paired difference in regret, portfolio-VOI minus uncertainty, is

\[
-21.21
\]

with Monte Carlo 95% interval

\[
\boxed{[-26.36,-16.05]}.
\]

The pre-specified promotion rule requires at least a 5% regret reduction versus uncertainty sampling
and paired 95% intervals below zero versus both equal-budget comparators. The portfolio layer passes
that gate.

## What changes operationally

Uncertainty sampling allocates, on average, about 11.0 safety confirmations and only 0.5 efficacy
confirmations. It is rational if the goal is simply to reduce uncertainty as cheaply as possible.

Portfolio-VOI instead allocates about 8.0 safety and 2.0 efficacy confirmations. It sometimes pays
for the more expensive efficacy experiment because the information can change a high-value,
capacity-constrained advancement decision.

The distinction is

\[
\boxed{\text{scientific uncertainty}\neq\text{decision-relevant uncertainty}.}
\]

## Boundary of the result

This layer is a controlled decision-science demonstration. The success thresholds, costs, rewards,
noise levels and numerical gains are properties of the locked DGP. They are not estimates of a
a real company portfolio, a pesticide registration process, or the economics of any real active ingredient.

A real implementation would need programme-specific endpoints, correlated efficacy/safety outcomes,
stage-specific attrition, registration and environmental constraints, and calibrated economic or
scientific value functions.
