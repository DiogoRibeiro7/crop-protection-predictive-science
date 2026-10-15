# Release validation — v1.2.0

Date: 2026-10-15

## Release scope

v1.2.0 adds a stand-alone synthetic scientific-computing extension built around a verified
one-dimensional diffusion-decay transport model and a known-truth inverse-calibration study.

This release does **not** reopen the empirical Bipolaris model-selection programme and does not
change any previously reported field-data result, promotion criterion, stopping rule, or dependency
constraint.

## Forward-model verification

The new forward model solves

\[
\frac{\partial c}{\partial t}
=
D\frac{\partial^2 c}{\partial x^2}
-
kc
\]

on a finite one-dimensional domain with homogeneous no-flux boundaries.

The implementation uses:

- a cell-centred finite-volume spatial discretisation;
- implicit Euler time integration;
- a tridiagonal banded linear solve.

Verification covers:

- the spatially uniform analytic decay limit;
- non-negative and finite numerical states;
- exact discrete no-flux mass-balance closure;
- zero-decay mass conservation;
- cosine-mode analytic comparison;
- monotone error reduction under grid/time-step refinement.

## Inverse-calibration evidence

The inverse layer generates reproducible Gaussian-noise observations from known truth and estimates
diffusion and decay with bounded nonlinear least squares in log-parameter space.

The main regression experiment uses:

- true diffusion \(D = 0.035\);
- true decay \(k = 0.18\);
- declared observation noise \(\sigma = 0.003\);
- a non-uniform cosine initial profile;
- fixed spatial and temporal observation locations;
- a fixed random seed.

The test contract requires both parameters to recover within 8% of known truth.

## Identifiability contract

Optimizer convergence is not treated as sufficient evidence for a scientifically meaningful inverse
solution.

The inverse result reports:

- Jacobian rank;
- Jacobian condition number;
- local covariance and parameter standard errors when available;
- parameter correlation;
- reduced chi-square and normalized RMSE;
- whether an estimate is effectively bound-limited;
- a separate practical-identifiability decision.

Practical identifiability requires both structural/local conditioning and tolerable relative
parameter uncertainty.

A spatially uniform negative-control experiment is deliberately included. Under no-flux boundaries
the diffusion term vanishes for a uniform profile, so diffusion must be reported as unidentifiable.
The test verifies that the fitted diffusion uncertainty is materially larger than the estimate rather
than accepting a numerically converged but scientifically meaningless value.

## Noise-model failure mode

A separate test deliberately understates the observation noise scale. The resulting inflated reduced
chi-square is retained as evidence that the declared noise model is diagnostically consequential.

## Scientific boundary

The transport-reaction work is controlled synthetic methods evidence only.

It does not establish:

- pesticide transport coefficients;
- environmental-fate parameters;
- formulation properties;
- field dissipation rates;
- regulatory exposure estimates;
- agronomic recommendations.

No Piedade trials or unpublished crop-protection field data are used.

## CI contract

The exact v1.2.0 release-candidate commit must pass:

- `quality`: Poetry lock consistency, Ruff, strict mypy;
- `test`: Python 3.11, 3.12 and 3.13;
- `package-artifact`: wheel/sdist build plus clean-environment installation and execution;
- `scientific-smoke`: regeneration and verification of the established scientific command outputs;
- `container-scientific`: offline regeneration and verification in the locked scientific container.

The new transport-reaction code is covered directly by pytest while the established empirical and
decision-analysis command outputs remain unchanged.

## Version metadata

The final release commit must agree on:

```text
pyproject.toml: 1.2.0
CITATION.cff: 1.2.0
crop_protection_ps.__version__: 1.2.0
.zenodo.json: 1.2.0
CHANGELOG.md: 1.2.0
```

The dependency graph is unchanged, so `poetry.lock` is not regenerated solely for this version bump.

## Release procedure

After the release-preparation PR is merged and push CI on `main` is green:

1. capture the exact 40-character `main` SHA;
2. run the manual `Release` workflow with:
   - `version = 1.2.0`;
   - `target_sha = <exact green main SHA>`;
   - `prerelease = false`;
   - `dry_run = true`;
3. inspect the dry-run result;
4. rerun the same version/SHA with `dry_run = false`;
5. verify tag `v1.2.0`, wheel, sdist, `SHA256SUMS`, GitHub Release, and Zenodo metadata.

The permanent release workflow refuses to release a non-current `main` commit and requires a
successful push CI for the exact target SHA.

## Remaining limitations

- the new inverse-calibration result is known-truth synthetic evidence, not empirical transport
  calibration;
- local covariance/Jacobian diagnostics do not prove global parameter identifiability;
- the Gaussian observation model is deliberately simple;
- the empirical Bipolaris stop boundary remains unchanged;
- real deployment would require domain-specific transport physics, observation models, parameter
  priors/bounds, and independent data.
