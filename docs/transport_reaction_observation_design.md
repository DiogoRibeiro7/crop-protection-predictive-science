# Designing Observations for Transport-Parameter Identifiability

This note extends the synthetic transport-reaction methods programme from
diagnosing identifiability after observations exist to designing observations
prospectively.

It does not use empirical crop-protection data and does not represent a real
monitoring or regulatory sampling plan.

## Question

Suppose the forward model

\[
\frac{\partial c}{\partial t}
=
D\frac{\partial^2 c}{\partial x^2}
-
kc
\]

is already verified and a nominal parameter point \((D,k)\) is available.

Before generating observations, where and when should measurements be taken so
that diffusion and decay influence the data in distinguishable ways?

## Local sensitivities

The design layer works in log-parameter space because both physical parameters
are positive.

For an observation prediction \(\mu_i\), the sensitivity vector is

\[
s_i
=
\left(
\frac{\partial \mu_i}{\partial \log D},
\frac{\partial \mu_i}{\partial \log k}
\right).
\]

Sensitivities are computed by symmetric finite differences around the declared
nominal parameter point.

With Gaussian observation noise of known standard deviation \(\sigma\), the
normalized sensitivity is

\[
\tilde s_i = \frac{s_i}{\sigma}.
\]

## Fisher information

For an observation design containing \(n\) space-time locations, the local
Fisher information matrix is

\[
I
=
\sum_{i=1}^n
\tilde s_i^T \tilde s_i.
\]

The implementation reports:

- numerical rank;
- condition number;
- log determinant;
- D-optimality score \(\sqrt{\det I}\).

For two parameters, a rank-one matrix means the design cannot locally separate
diffusion from decay.

## Equal-budget comparison

The regression tests compare designs with exactly 12 observations.

### Centre-only temporal design

The cosine initial condition is evaluated on an odd finite-volume grid so there
is an exact centre cell.

At the centre of the first cosine mode,

\[
\cos(\pi x/L)=0,
\]

so repeated centre-cell measurements largely track the decaying mean component.
They are intentionally poor for learning diffusion.

This design is expected to be rank deficient.

### Final-time spatial design

Twelve spatial locations are observed at the final time.

The spatial shape carries information about diffusion while the overall level
contains decay information, so the information matrix should become full rank.

### Mixed space-time design

Four time points and three spatial locations are crossed to give the same
12-observation budget.

This design uses both temporal evolution and spatial shape and should also be
full rank.

The comparison is intentionally finite and transparent. No black-box search is
needed to establish the methodological point.

## Uniform-field negative control

A second negative control uses a spatially uniform initial concentration.

With homogeneous no-flux boundaries,

\[
\frac{\partial^2 c}{\partial x^2}=0,
\]

so the observations contain no physical information about \(D\), regardless
of where they are sampled.

The test therefore requires:

- rank one;
- zero D-optimality;
- effectively zero diffusion sensitivity;
- infinite condition number.

A design algorithm should not manufacture diffusion information when the
experiment itself contains none.

## Observation noise

Because the Fisher matrix uses normalized sensitivities,

\[
I \propto \frac{1}{\sigma^2}.
\]

Doubling the observation-noise standard deviation therefore divides the
information matrix by four.

The test suite verifies this scaling directly.

## Interpretation

The design criterion is local.

It answers:

> At this nominal parameter point, which proposed observation design creates
> the strongest local separation of diffusion and decay?

It does not prove:

- global structural identifiability;
- robustness to severe parameter misspecification;
- optimality under unknown heterogeneous measurement errors;
- optimality under real sampling costs or operational constraints.

The existing profile-likelihood layer remains the complementary non-local
diagnostic after synthetic observations are generated.

## Scope boundary

This is controlled scientific-computing evidence only.

It does not specify:

- pesticide-monitoring locations;
- environmental sampling schedules;
- regulatory study designs;
- field dissipation protocols;
- real laboratory costs.

The transferable lesson is methodological: verify the model, inspect
identifiability, and design measurements so that the parameters of interest
actually perturb the observable system in distinguishable ways.
