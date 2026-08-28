# Multi-fidelity candidate progression

Version 0.6.0 asks a different Crop Protection R&D question from the field-trial analyses:

> Can lower-cost lab and glasshouse evidence reduce the amount of expensive field experimentation
> required to identify the best candidates?

The public hop fungicide data contain field experiments only. They do not contain matched lab,
glasshouse and field measurements for the same candidate set. This extension is therefore a
**controlled synthetic experiment with known latent field truth** rather than a fabricated real-data
linkage.

## Data-generating structure

For candidate \(i\), latent field efficacy is

\[
\theta_i \sim N(2,1).
\]

Lab and glasshouse assays are biased, noisy surrogates:

\[
L_i = 0.50 + 0.65\theta_i + \eta_{Li} + \epsilon_{Li},
\]

\[
G_i = 0.20 + 0.88\theta_i + \eta_{Gi} + \epsilon_{Gi},
\]

where \(\eta\) represents candidate-specific cross-fidelity discordance that cannot be eliminated by
simply averaging more technical replicates. Field observations are

\[
F_{ij}=\theta_i+\epsilon_{Fij}.
\]

The glasshouse is intentionally more transportable to field performance than the laboratory assay,
but neither fidelity is perfect.

## Historical cross-fidelity calibration

A separate historical cohort is split into 300 calibration candidates and 150 held-out candidates.
The calibration models are trained against **observed historical field means**, never against latent
\(\theta_i\).

Two regularised linear transfer models are compared:

\[
\widehat F_i = f(L_i),
\]

and

\[
\widehat F_i = f(L_i,G_i).
\]

The held-out results are:

| Calibration model | RMSE to latent field efficacy | R² |
| --- | ---: | ---: |
| Lab only | 0.7325 | 0.3974 |
| Lab + glasshouse | 0.4700 | 0.7519 |

The pre-specified promotion rule requires at least a 10% held-out RMSE reduction before glasshouse
information is allowed into candidate progression. The observed reduction is about **35.8%**, so the
stage passes.

This gate matters. A cheaper assay is not useful merely because it is correlated with field outcome
in the training set.

## Equal-budget candidate progression

All policies receive exactly **1,040 relative cost units**. One replicate costs:

\[
C_L=1,\qquad C_G=4,\qquad C_F=20.
\]

Each candidate measured at a stage receives two replicates.

The three policies are:

| Policy | Lab candidates | Glasshouse candidates | Field candidates | Total cost |
| --- | ---: | ---: | ---: | ---: |
| Field only | 0 | 0 | 26 | 1040 |
| Lab → field | 80 | 0 | 22 | 1040 |
| Lab → glasshouse → field | 80 | 30 | 16 | 1040 |

The final decision is to select eight candidates. The oracle is the eight candidates with the
largest latent field efficacy \(\theta_i\).

The policies are scored using:

1. **oracle top-eight recall**;
2. **simple selection regret**,

\[
R = \overline\theta_{oracle}-\overline\theta_{selected}.
\]

The second metric is the more important one: missing an oracle candidate matters more when the
replacement is substantially worse in true field efficacy.

## Pre-posterior result

Across 5,000 common-random-number rollouts:

| Policy | Top-eight recall | Mean simple regret |
| --- | ---: | ---: |
| Field only | 0.3246 | 0.6633 |
| Lab → field | 0.6487 | 0.2020 |
| Lab → glasshouse → field | **0.7076** | **0.1401** |

Thus the full multi-fidelity policy reduces selection regret by approximately

\[
\boxed{30.7\%}
\]

relative to lab → field under exactly the same experimental spend.

The paired Monte Carlo difference in regret, multi-fidelity minus lab → field, is approximately

\[
-0.06194
\]

with a Monte Carlo 95% interval

\[
[-0.06450,-0.05938].
\]

## Scientific interpretation

The result does **not** say that lab or glasshouse data should always be trusted to predict field
performance. It says the opposite: lower-fidelity evidence becomes decision-relevant only after its
cross-fidelity relationship has survived held-out calibration.

The controlled experiment separates three questions that are often conflated:

\[
\text{cheap measurement}
\neq
\text{valid surrogate}
\neq
\text{useful progression policy}.
\]

A surrogate can correlate with field outcome and still fail to improve candidate-selection decisions
once its cost and transfer error are accounted for.

## Why this matters for Crop Protection R&D

A real pipeline may contain high-throughput biochemical assays, whole-organism laboratory assays,
glasshouse studies, small-plot field studies and larger multi-environment trials. The quantitative
problem is not just to fit each stage independently. It is to estimate how evidence transports
between stages and decide where the next unit of experimental capacity should be spent.

A production implementation would extend this controlled case with:

- active-ingredient and formulation descriptors;
- target/pathogen/crop structure;
- explicit assay-endpoint differences;
- environment and application covariates;
- heteroscedastic fidelity-specific error;
- Bayesian cross-fidelity uncertainty;
- candidate attrition and censoring;
- expected value of information under actual assay costs and development utilities.

The current release deliberately stops before those additions because the public data do not identify
them.
