# Transport-Reaction Inverse Calibration

This note documents the inverse-problem layer built on the verified synthetic
transport-reaction forward solver. It remains completely separate from the
empirical hop and Bipolaris analyses.

## Statistical model

The latent concentration field follows

\[
\frac{\partial c}{\partial t}
=
D\frac{\partial^2 c}{\partial x^2}
-
k c,
\]

with the same zero-flux boundary conditions and finite-volume solver documented
in [`transport_reaction_verification.md`](transport_reaction_verification.md).

Synthetic observations are generated at selected cells and times as

\[
y_j = c(x_j,t_j;D,k)+\varepsilon_j,
\qquad
\varepsilon_j\sim\mathcal N(0,\sigma^2),
\]

with known observation-noise standard deviation \(\sigma\).

Calibration minimizes the standardized residual sum of squares. The optimizer
works on \((\log D,\log k)\), so positivity is enforced by construction while
the reported estimates remain on the physical \((D,k)\) scale.

## Known-truth recovery design

The deterministic verification case uses:

- true diffusion \(D=0.035\);
- true decay rate \(k=0.18\);
- a non-uniform cosine initial profile;
- five observation times from 0.02 to 0.20;
- seven spatial sensor cells;
- Gaussian noise with \(\sigma=0.003\);
- a fixed random seed.

For that locked design, the recovered values are approximately:

| Quantity | Value |
| --- | ---: |
| Diffusion estimate | 0.0331 |
| Decay-rate estimate | 0.1834 |
| Diffusion standard error | 0.00148 |
| Decay-rate standard error | 0.00532 |
| Parameter correlation | -0.372 |
| Jacobian condition number | 1.80 |
| Reduced \(\chi^2\) | 1.01 |
| Normalized RMSE | 0.97 |

The point of the example is not that these exact errors are universally small.
It is that, under a design with spatial and temporal information, the known
parameters are recovered and the residual scale is consistent with the stated
noise model.

## Local identifiability diagnostic

The weighted residual Jacobian is computed at the optimum in log-parameter
space. The local information approximation is

\[
J^\top J.
\]

When full rank, its inverse provides a Gauss-Newton covariance approximation for
\((\log D,\log k)\). Standard errors are mapped back to the physical parameter
scale with the delta method.

The implementation reports:

- Jacobian rank;
- Jacobian condition number;
- physical-scale standard errors;
- parameter correlation;
- whether the optimum lies at a parameter bound;
- a combined local `identifiable` flag.

These diagnostics describe local numerical identifiability under the assumed
observation design and noise model. They are not a global proof of parameter
identifiability.

## Failure modes

### Spatially uniform initial condition

A uniform concentration profile contains no diffusion information: the
diffusion term vanishes and only decay is visible in the ideal continuous
problem.

The locked failure-mode test therefore uses a uniform initial state. The fitted
Jacobian becomes extremely ill-conditioned (condition number roughly
\(2.7\times10^6\) in the deterministic test), and the calibration is correctly
flagged as non-identifiable under the configured threshold.

This is a useful experimental-design lesson: a parameter cannot be recovered
merely because the optimizer returns a number.

### Mis-specified observation noise

A second failure-mode test generates observations with a substantially larger
noise standard deviation than the value supplied to the calibration.

The resulting reduced \(\chi^2\) becomes much larger than one, exposing the
over-confident noise assumption. The diagnostic therefore checks more than point
parameter recovery.

## Transferable scientific-computing skills

This synthetic case demonstrates:

- verified forward modelling before inversion;
- known-truth parameter-recovery experiments;
- explicit observation-noise assumptions;
- positivity-preserving parameterization;
- local sensitivity and identifiability diagnostics;
- deliberate failure-mode construction.

It does **not** estimate transport or degradation parameters for a real
crop-protection product, does not use Piedade trial data, and does not reopen
the six-environment Bipolaris model-selection loop.
