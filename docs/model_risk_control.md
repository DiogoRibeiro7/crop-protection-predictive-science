# Applicability domain and model-risk control

## Scientific question

A scientific model can always return a number. The operational question is different:

> **When is a prediction sufficiently supported by prior experiments to be used for an R&D
> decision, when should its uncertainty be widened, and when should the model abstain?**

Version 0.9.0 answers that question in a controlled stress experiment built on the synthetic
formulation/application response surface from the multi-objective case. The hidden response surface
is used only for evaluation. The deployable model sees noisy experiments from a deliberately
restricted historical support region.

## Historical support and distribution shift

The three normalised design variables represent dose, a formulation property and adjuvant level.
Historical experiments cover a moderate central region. Candidate conditions outside that region
are split before model fitting into:

- **in-domain** conditions from the same historical support;
- **near-shift** conditions just outside historical support;
- **far-shift** conditions at clearly extrapolative edges of the search space.

Every rollout has separate model-fitting, calibration and final stress-test rows. Nothing from the
final stress set is used to choose the applicability threshold or interval width.

## Deployment model

The response model is intentionally compact and inspectable. Efficacy is approximated with a
quadratic ridge surface,

\[
\hat f(x)=\beta_0+\sum_j\beta_j\phi_j(x),
\]

where the basis contains linear terms, squared terms and pairwise interactions. Predictions are
**not clipped to \([0,1]\)** during the audit because clipping would hide extrapolation failure.

This is deliberately not the richest model available in the repository. Model-risk controls should
be able to detect failure of a plausible deployable model rather than rely on a model being correct
by construction.

## Applicability-domain score

For each candidate condition, the repository standardises the original design variables using the
historical training set and computes the mean Euclidean distance to its seven nearest historical
experiments:

\[
D(x)=\frac{1}{7}\sum_{j=1}^{7}\lVert z(x)-z(x_{(j)})\rVert_2.
\]

The abstention threshold is fixed at the **85th percentile of in-domain calibration distances**.
This is an operating-risk choice made before the final stress set is evaluated.

A prediction is accepted only when

\[
D(x)\le D_{0.85}^{cal}.
\]

The score is not claimed to be a universal chemical applicability-domain metric. It is a transparent
controlled example of how experimental support can become an explicit model input to deployment
governance.

## Split-conformal uncertainty

The base interval uses finite-sample split conformal calibration on absolute residuals. For nominal
coverage \(1-\alpha=0.90\), the half-width is the appropriate finite-sample order statistic of

\[
R_i=|Y_i-\hat f(X_i)|.
\]

Three interval policies are compared.

### In-domain interval used everywhere

The first policy calibrates only on historical-support residuals and then applies the same interval
across the stress set. It answers the common but unsafe assumption that in-domain validation
uncertainty can simply be exported to extrapolative conditions.

### One global stress-calibrated interval

The second policy also sees a separate near-shift calibration set and computes one wider conformal
half-width. It still assumes a single uncertainty scale is adequate everywhere.

### Distance-scaled interval

The third policy defines

\[
s(x)=\max\left(1,\frac{D(x)}{D_{0.85}^{cal}}\right)^2
\]

and calibrates the normalised score

\[
R_i^*=\frac{|Y_i-\hat f(X_i)|}{s(X_i)}.
\]

At prediction time, the conformal base half-width is multiplied by the same \(s(x)\). The quadratic
inflation is pre-specified and is not tuned against the final stress set.

This procedure is a pragmatic stress-calibration device, **not a claim of distribution-free
coverage under arbitrary covariate shift**. Outside the calibration support, conformal guarantees do
not magically survive.

## Locked result

Across 50 paired rollouts:

| Risk control | Mean stress-set coverage |
| --- | ---: |
| In-domain 90% interval used everywhere | **50.6%** |
| One global stress-calibrated interval | **70.0%** |
| Distance-scaled interval | **92.9%** |
| In-domain interval among accepted predictions | **88.9%** |

Distance-aware widening therefore restores approximate nominal coverage on the full controlled
stress set, but its mean full interval width grows from about **0.43** for the global interval to
about **0.83** on an efficacy scale roughly bounded by zero and one.

That is not free performance. It is a warning that far-extrapolative predictions can become too
uncertain to be useful.

## Selective prediction

The abstention policy accepts only about **21.0%** of the deliberately shift-heavy final stress set
and rejects **98.1%** of conditions classified as near/far distribution shift.

Latent efficacy MAE is

\[
MAE_{all}=0.1695
\]

when a prediction is forced for every condition, versus

\[
MAE_{accepted}=0.0502
\]

inside the applicability domain. This is a reduction of approximately

\[
\boxed{70.4\%}.
\]

The purpose is not to maximise coverage by refusing almost everything. The operating point is made
visible so scientists can decide whether the retained experimental support is sufficiently broad for
the intended use case.

## Promotion gate

The model-risk layer is promoted only if all of the following hold across the locked paired
simulation:

1. distance-scaled stress coverage is at least 90%;
2. accepted-only interval coverage is at least 87%;
3. out-of-domain rejection is at least 95%;
4. selective MAE is at least 60% lower than forced-prediction MAE;
5. the paired Monte Carlo interval for scaled-minus-global coverage is entirely positive;
6. the paired Monte Carlo interval for selective-minus-forced MAE is entirely negative.

All six conditions pass in v0.9.0.

## R&D interpretation

The main distinction is

\[
\boxed{
\text{model can compute a prediction}
\neq
\text{prediction is inside validated scientific support}.
}
\]

A production predictive-science system should therefore expose more than a point estimate. It
should report the experimental support, uncertainty under the relevant shift, and an explicit
abstention/next-experiment action when the requested condition lies outside its validated domain.

For a real Crop Protection deployment, the applicability domain would need to be defined jointly
with domain scientists and could include chemistry descriptors, crop, pest/pathogen, formulation,
dose, geography, weather, phenology and assay/field protocol. The controlled three-dimensional
score in this repository is an auditable methodological prototype, not a regulatory or product-use
criterion.
