# Transport-Reaction Profile Likelihood

This note extends the synthetic transport-reaction inverse-calibration
demonstration beyond local Jacobian/covariance diagnostics.

It remains fully separate from the empirical hop and Bipolaris programmes and
does not estimate real crop-protection transport parameters.

## Why profile likelihood?

The v1.2.0 inverse layer reports local diagnostics at the fitted optimum:

- Jacobian rank;
- Jacobian condition number;
- local covariance;
- standard errors;
- parameter correlation;
- relative parameter uncertainty.

Those are useful, but they describe the objective only near the optimum. A
locally well-behaved quadratic approximation does not by itself establish that
a parameter is practically identifiable over the admissible parameter region.

Profile likelihood asks a different question.

For one parameter of interest, hold that parameter fixed, re-optimise the other
parameter, and measure how much the normalized residual objective worsens.

For diffusion,

\[
Q_D(D)
=
\min_k
\sum_i
\left[
\frac{\hat c_i(D,k)-y_i}{\sigma}
\right]^2,
\]

and analogously for decay,

\[
Q_k(k)
=
\min_D
\sum_i
\left[
\frac{\hat c_i(D,k)-y_i}{\sigma}
\right]^2.
\]

The reported profile is

\[
\Delta Q(\theta)
=
Q_\theta(\theta)-Q_{\min}.
\]

## Likelihood-ratio interval

Under the declared independent Gaussian observation model with known
\(\sigma\), the residual sum of squares is proportional to minus twice the
log-likelihood up to an additive constant.

For one profiled parameter, the default 95% likelihood-ratio threshold is

\[
\chi^2_{1,0.95}
\approx
3.84146.
\]

The confidence region is the set of profiled parameter values satisfying

\[
\Delta Q(\theta)
\le
3.84146.
\]

The implementation evaluates each parameter on a declared logarithmic grid,
because both physical parameters are strictly positive, and re-optimises the
nuisance parameter in log space at every grid point.

## Closed versus open intervals

A finite-looking numerical estimate is not enough.

If the accepted likelihood-ratio region crosses the threshold on both sides
inside the declared search grid, the profile interval is reported as closed.

If the accepted region reaches a search boundary, that side of the interval is
reported as open. The correct interpretation is then not that the boundary is
a confidence limit, but that the data did not resolve the limit within the
declared admissible range.

This distinction is especially important for the deliberately uninformative
uniform-profile experiment.

## Known-truth identified case

The identified regression experiment is the same non-uniform cosine problem
used for v1.2.0 inverse calibration:

- true diffusion \(D=0.035\);
- true decay \(k=0.18\);
- Gaussian observation noise \(\sigma=0.003\);
- five observation times;
- seven spatial observation cells;
- fixed random seed.

The profile-likelihood test requires:

- a closed diffusion interval;
- a closed decay interval;
- both true parameter values to lie inside their respective profile intervals.

This complements, rather than replaces, the local standard-error and
conditioning checks.

## Uniform-profile negative control

For a spatially uniform initial condition under homogeneous no-flux boundaries,

\[
\frac{\partial^2 c}{\partial x^2}=0,
\]

so the forward model reduces to

\[
c(t)=c_0e^{-kt}.
\]

The observations contain no physical information about diffusion.

Accordingly, profiling diffusion while re-optimising decay should remain
essentially flat across the declared diffusion range. The regression test
requires the diffusion confidence region to remain open at both grid
boundaries.

That is stronger evidence than merely obtaining a large local standard error:
the objective itself shows that a wide range of diffusion values can explain
the observations equally well.

## Interpretation

Local and profile diagnostics answer related but different questions.

Local diagnostics are useful for:

- detecting near-singular curvature;
- estimating local uncertainty;
- identifying strong local parameter correlation;
- checking whether a numerical optimum is practically precise.

Profile likelihood is useful for:

- exposing asymmetric uncertainty;
- revealing flat objective directions;
- detecting confidence regions that run into parameter bounds;
- checking whether nuisance-parameter compensation hides weak identification.

Neither method proves global structural identifiability for an arbitrary PDE
model. Here they are controlled practical-identifiability diagnostics for a
two-parameter known-truth experiment.

## Scope boundary

This extension does not establish real:

- diffusion coefficients;
- pesticide dissipation rates;
- environmental-fate parameters;
- formulation properties;
- regulatory exposure quantities.

Its purpose is methodological: demonstrate how a verified forward model,
explicit observation model, local inverse diagnostics, and likelihood profiling
can be combined without converting numerical convergence into an unsupported
scientific claim.
