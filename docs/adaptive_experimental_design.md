# Decision-aware adaptive replication

## Scientific question

The earlier analyses establish two facts that matter for experimental design:

1. product-specific Early-versus-Late timing effects remain uncertain after partial pooling; and
2. the same-year untreated sentinel improves disease-level transportability, but product-by-sentinel
   interactions did not survive deployment-style validation.

Version 0.5.0 therefore does **not** add another interaction surface. It asks a narrower R&D
question:

> If a limited number of additional field-trial blocks can be run, which product should receive the
> next Early/Late comparison so that the timing decision becomes more defensible?

The unit of additional information is one paired block for a single product: an Early-timing plot
and a Late-timing plot evaluated in the same block.

## Decision variable

For product \(p\), define

\[
\theta_p
=
E\{\sqrt{AUDPC}_{Late}-\sqrt{AUDPC}_{Early}\}.
\]

Lower disease burden is preferred. Therefore

\[
\theta_p>0 \Rightarrow \text{Early is preferred},
\qquad
\theta_p<0 \Rightarrow \text{Late is preferred}.
\]

The current Bayesian posterior is approximated by

\[
\theta_p\mid D \approx N(\mu_p,v_p),
\]

using the product-level posterior mean and standard deviation from the v0.3 hierarchical model.
The predictive variability of a new paired block is estimated from the historical within-product
paired contrasts,

\[
y_{p,new}\mid\theta_p\sim N(\theta_p,\sigma_p^2).
\]

This is deliberately a compact decision model. It does not claim that the normal approximation
captures every source of field heterogeneity.

## Why D-optimality is not enough here

The synthetic case already uses D-optimal design to increase information about continuous model
parameters. That is appropriate when the scientific objective is parameter precision.

Here the action is binary: **Early or Late**. A design that maximises generic parameter information
can therefore spend resources refining an effect whose sign is already clear.

For comparison, one paired block has continuous-parameter expected information gain

\[
I_p^{parameter}
=
\frac12\log\left(1+\frac{v_p}{\sigma_p^2}\right).
\]

In the release state this criterion ranks **Curzate** first.

## Decision-aware information gain

Let

\[
S_p=\mathbf 1(\theta_p>0)
\]

encode the timing decision. Its posterior uncertainty is the binary entropy

\[
H(S_p\mid D)
=-q_p\log q_p-(1-q_p)\log(1-q_p),
\qquad
q_p=P(\theta_p>0\mid D).
\]

The acquisition score for one candidate paired block is

\[
A_p
=
H(S_p\mid D)
-
E_{y_{p,new}\mid D}
\left[H(S_p\mid D,y_{p,new})\right].
\]

This is expected information gain about the **sign** of the timing effect. The expectation is
computed deterministically by Gauss-Hermite quadrature under the Normal-Normal update.

This follows the broader Bayesian optimal-design principle of choosing experiments by expected
information gain, but makes the quantity of interest the actual R&D decision rather than the whole
parameter vector. Expected value of sample information similarly formalises the value of additional
research in terms of reduced decision uncertainty; here the utility is explicitly scientific
regret on the transformed disease scale, not money.

## Current acquisition ranking

The current posterior makes the distinction visible:

| Product | P(Late > Early disease) | Sign entropy (nats) | Parameter EIG | Decision-sign EIG |
| --- | ---: | ---: | ---: | ---: |
| Revus | 0.905 | 0.313 | 0.0326 | **0.0106** |
| Curzate | 0.987 | 0.0675 | **0.0434** | 0.00357 |
| FungiPhi | 0.981 | 0.0929 | 0.0180 | 0.00202 |
| Ranman | 0.984 | 0.0839 | 0.0151 | 0.00155 |
| Presidio | 0.994 | 0.0343 | 0.00887 | 0.000400 |

Thus:

\[
\boxed{\text{parameter information} \Rightarrow \text{Curzate first}}
\]

while

\[
\boxed{\text{decision information} \Rightarrow \text{Revus first}.}
\]

Revus is not selected because its effect is largest. It is selected because the current evidence
leaves the greatest probability of choosing the wrong timing.

## Pre-posterior policy evaluation

Three policies are evaluated before collecting any new data:

- **Uniform**: round-robin allocation across the five products.
- **Parameter EIG**: select the product with maximum information gain about the continuous effect.
- **Decision EIG**: select the product with maximum expected information gain about the sign.

For each of 10,000 Monte Carlo rollouts, future paired-block observations are generated from the
current posterior predictive distribution. Common standard-normal draws are used across policies to
reduce Monte Carlo noise in comparisons. The policies are evaluated at budgets of 0, 5, 10, 15 and
20 additional paired blocks.

The primary decision loss is

\[
L(a_p,\theta_p)
=
|\theta_p|\,\mathbf 1\{a_p\text{ chooses the wrong sign}\}.
\]

The reported Bayes regret integrates this loss under the posterior at the end of each simulated
sampling path.

At a budget of 15 paired blocks:

| Policy | Mean total sign entropy | Mean Bayes regret |
| --- | ---: | ---: |
| Decision EIG | **0.4904** | **0.03465** |
| Parameter EIG | 0.5218 | 0.03987 |
| Uniform | 0.5417 | 0.03995 |

Relative to uniform replication, decision-aware allocation reduces expected Bayes regret by
**13.3%** and sign entropy by **9.5%**.

The paired Monte Carlo estimate of the regret difference, Decision EIG minus Uniform, is

\[
-0.00530
\]

with Monte Carlo standard error \(0.00035\). The corresponding 95% interval for Monte Carlo error
of the estimated expected difference is approximately

\[
[-0.00598,-0.00462].
\]

This interval is **not** a biological confidence interval. It only quantifies numerical uncertainty
from the pre-posterior simulation under the current model.

## Where the adaptive budget goes

At budget 15, the average Decision-EIG allocation is approximately:

| Product | Mean additional paired blocks |
| --- | ---: |
| Revus | **11.66** |
| Curzate | 2.05 |
| FungiPhi | 0.97 |
| Ranman | 0.32 |
| Presidio | 0.00 |

Uniform allocation spends three blocks on every product. The adaptive policy instead concentrates
resources where the timing decision can still plausibly change.

This is not an instruction to run 11.66 physical blocks. The fractional values are averages across
10,000 possible future data paths. A realised sequential experiment always allocates integer blocks.

## Role of the environment sentinel

The untreated sentinel remains important, but its role is constrained by evidence from v0.4.
It supplies in-season information about realised disease pressure and improved prediction of the
new season's disease level. However, the product-by-sentinel timing-interaction model failed its
promotion gate.

Therefore v0.5 uses the sentinel to define the **decision stage**—adaptation can occur after the new
season has revealed itself—but does not let the sentinel alter product-specific timing contrasts
without validation evidence.

This separation avoids a common modelling mistake:

\[
\text{a useful environment state variable}
\not\Rightarrow
\text{identified treatment-by-environment interaction}.
\]

## Limitations

- Product timing posteriors are approximated as Gaussian using v0.3 posterior summaries.
- Future paired-block variability is estimated from a small historical sample.
- Costs are treated as equal across products and paired blocks.
- No spatial interference, plot loss, delayed observations or operational scheduling constraints are
  modelled.
- The utility is a scientific timing-decision regret on \(\sqrt{AUDPC}\), not commercial value.
- The design is conditional on the historical posterior and is not a crop-protection use
  recommendation.

A production R&D system would replace these simplifying assumptions with actual per-experiment
costs, richer predictive distributions, operational constraints and agreed decision utilities.

## Methodological references

- Tsilifis, P., Ghanem, R. G., & Hajali, P. (2017). *Efficient Bayesian Experimentation Using an
  Expected Information Gain Lower Bound*. SIAM/ASA Journal on Uncertainty Quantification.
  https://doi.org/10.1137/15M1043303
- Heath, A. et al. (2022). *Simulating Study Data to Support Expected Value of Sample Information
  Calculations: A Tutorial*. Medical Decision Making, 42(2).
  https://doi.org/10.1177/0272989X211026292
- Agronomy Journal (2025). *Bayesian-optimized experimental designs for estimating the economic
  optimum nitrogen rate: a model-averaging approach*. https://doi.org/10.1002/agj2.70087
