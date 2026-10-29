# Transport-Reaction Inverse Calibration

This note completes the stand-alone synthetic transport-reaction methods
demonstration introduced in
[Verified Transport-Reaction Forward Model](transport_reaction_verification.md).

It does **not** use the empirical hop or Bipolaris datasets, does not reopen the
closed Bipolaris model-selection programme, and does not estimate transport
parameters for a real crop-protection system.

## Question

Given noisy observations generated from the verified one-dimensional
diffusion-decay model,

\[
\frac{\partial c}{\partial t}
=
D\frac{\partial^2 c}{\partial x^2}
-
kc,
\]

can the inverse problem recover the known diffusion coefficient \(D\) and
first-order decay rate \(k\), and can the software detect when the experimental
design cannot identify both parameters?

## Known-truth experiment

The regression test uses a deliberately non-uniform cosine initial condition so
diffusion and decay affect the observations differently.

Known truth:

- \(D = 0.035\);
- \(k = 0.18\);
- 48 finite-volume cells;
- \(\Delta t = 0.002\);
- final time \(0.2\);
- cosine mean \(0.8\);
- cosine amplitude \(0.45\).

Observations are sampled at five time points and seven spatial cells.

Independent Gaussian observation noise is added with known standard deviation

\[
\sigma = 0.003.
\]

The random seed is fixed, so the synthetic inverse experiment is exactly
reproducible.

## Objective

Calibration minimizes normalized residuals

\[
r_i(D,k)
=
\frac{\hat c_i(D,k)-y_i}{\sigma},
\]

using bounded nonlinear least squares.

The bounds are part of the declared inverse problem, not discovered after
seeing the result.

The regression test requires both parameters to be recovered within 8% of the
known truth.

## Noise calibration diagnostics

Because the synthetic observation model supplies the true \(\sigma\), the
normalized residual scale has a direct interpretation.

The result reports:

- normalized RMSE;
- reduced chi-square;
- optimizer success;
- number of forward-model evaluations.

For a correctly specified synthetic noise model, reduced chi-square should be
of order one rather than being driven artificially close to zero.

## Held-out predictive validation

Parameter recovery on the fitted observations is not evidence of predictive
performance at new observation locations. The inverse module therefore also
provides `validate_inverse_holdout`, which evaluates fitted parameters at
time–cell pairs excluded from the inverse fit. Overlapping training and test
pairs are rejected before evaluation.

The diagnostic reports held-out RMSE, noise-normalised RMSE and empirical
coverage of a central 90% Gaussian observation interval. Its interval width
uses the declared observation-noise standard deviation, conditional on the
estimated parameters. A separate optional local delta-method interval adds
first-order parameter-estimation variance to observation-noise variance. It
uses finite-difference prediction sensitivities and the local covariance
reconstructed from the fitted parameter standard errors and correlation. It is
reported only when calibration succeeds and passes the local identifiability
checks. This approximation is not a profile-likelihood or bootstrap interval,
and neither interval includes structural model discrepancy, parameter
nonlinearity beyond first order, or a guarantee of field-data coverage.
For each empirical coverage fraction, the validator also reports a two-sided
95% Wilson score interval to show sampling uncertainty. This interval treats
the held-out coverage indicators as independent Bernoulli outcomes; spatial or
temporal dependence would make it optimistic. It is not a confidence interval
for the physical parameters, nor evidence that nominal 90% coverage is attained
by the underlying predictive procedure. In particular, 14 held-out observations
cannot estimate coverage precisely.
The validator also reports the mean Gaussian negative log likelihood (NLL)
for the noise-only prediction and, when available, the first-order local
parameter-uncertainty prediction. The per-observation score is

\[
\frac12\left[\log(2\pi v_i)+\frac{(y_i-\hat y_i)^2}{v_i}\right],
\]

where \(v_i\) is the declared predictive variance. Lower scores indicate a
better tradeoff between predictive accuracy and uncertainty width; inflating
the variance indefinitely incurs a logarithmic penalty. NLL values are
comparable only for observations in the same units and evaluation set. Like
the intervals themselves, these scores rely on the assumed Gaussian model
and do not establish field-level calibration.
The regression test also checks that deliberately misspecified parameters
increase the held-out prediction error and that a non-identifiable fit
does not receive a deceptively precise uncertainty-aware interval.

## Local identifiability

The inverse solver reports the local Jacobian of normalized residuals with
respect to \((D,k)\).

Diagnostics include:

- Jacobian rank;
- Jacobian condition number;
- local parameter standard errors from \((J^T J)^{-1}\) when invertible;
- parameter correlation;
- whether the optimum lies on a parameter bound.

A fit is marked identifiable only when:

1. the Jacobian has rank two;
2. its condition number is finite and below the declared threshold;
3. both parameters have tolerable relative standard error;
4. the optimum is not effectively pinned to a bound.

The parameter estimate and the identifiability decision are therefore separate
outputs. Optimizer convergence alone is not treated as evidence that both
physical parameters are estimable.

These are local diagnostics. The complementary likelihood-based analysis is
documented in
[Transport-Reaction Profile Likelihood](transport_reaction_profile_likelihood.md).

## Deliberate failure mode: uniform initial condition

A spatially uniform initial state is an important negative control.

Under homogeneous no-flux boundaries, a uniform profile remains spatially
uniform. The diffusion term is then zero everywhere, so

\[
c(t)=c_0 e^{-kt}
\]

contains information about \(k\) but no information about \(D\).

The test suite therefore creates noisy observations from a uniform initial
state and requires the inverse analysis to flag the two-parameter problem as
**not identifiable**.

This is a scientific feature, not a failed optimizer. A method that returned a
precise-looking diffusion estimate in this experiment would be misleading.

## Failure-mode checks

The inverse test suite also verifies that:

- observation times must lie on the declared solver time grid;
- spatial indices must lie inside the finite-volume grid;
- time and spatial indices must have an integer dtype; fractional positions and
  booleans are rejected, not silently truncated into grid indices;
- noise standard deviation must be positive and finite;
- parameter bounds and starting values must be internally consistent;
- synthetic observations are exactly reproducible for a fixed seed.

## Transferable scientific-computing evidence

The extension demonstrates a workflow that is transferable well beyond this
toy PDE:

- verify the forward model before solving an inverse problem;
- generate known-truth experiments before trusting parameter recovery;
- scale residuals using an explicit observation model;
- distinguish numerical convergence from parameter identifiability;
- inspect Jacobian rank, conditioning and parameter correlation;
- include experiments that are deliberately uninformative;
- report failure honestly instead of forcing a parameter estimate into a
  scientific claim.

## Scope boundary

This remains controlled synthetic methods evidence.

It does **not** establish:

- pesticide transport coefficients;
- environmental fate parameters;
- field dissipation rates;
- formulation properties;
- regulatory exposure estimates;
- agronomic recommendations.

No Piedade crop trials or other unpublished field data are used.

The purpose is to demonstrate verified forward modelling, inverse calibration,
identifiability analysis and failure-aware scientific software.
