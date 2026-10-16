# Release validation — v1.3.0

Date: 2026-10-16

## Release scope

v1.3.0 consolidates the post-v1.2 synthetic transport-design programme.

This release adds no new empirical crop-protection model candidate and does not reopen the closed
Bipolaris six-environment promotion loop.

## Scientific methods added

The release includes:

- profile-likelihood identifiability for diffusion and decay;
- prospective Fisher-information observation design;
- finite-scenario robustness across declared diffusion/decay uncertainty points;
- deterministic equal-budget robust candidate selection;
- greedy sequential observation augmentation;
- exact finite-pool subset benchmarking of the greedy method;
- a regenerated `results/transport_design/summary.json` evidence bundle.

The profile-likelihood layer complements local covariance/Jacobian diagnostics by re-optimising the
nuisance parameter over a declared positive log-scale grid and distinguishing finite intervals from
profiles that remain open at parameter bounds.

The design layer uses finite-difference sensitivities with respect to log diffusion and log decay and
scores designs with the local Fisher information matrix. Robust design re-evaluates the same
candidate design across a finite declared parameter uncertainty set and reports nominal, mean and
worst-case D-optimality, conditioning and rank failures.

Finite-candidate selection imposes a hard full-rank-across-scenarios gate before ranking equal-budget
designs by worst-case information. Sequential augmentation greedily selects the next observation from
a declared finite pool. Exact subset enumeration provides an exact optimum only when the declared
pool and budget are small enough for exhaustive search.

## Persisted evidence contract

The `crop-protection-transport-design` CLI regenerates:

`results/transport_design/summary.json`

The stable schema records:

- the known-truth transport configuration and Gaussian observation-noise scale;
- the declared parameter scenarios;
- centre-only, final-time spatial and mixed designs;
- local and robust information diagnostics;
- the selected robust candidate;
- the sequential augmentation history;
- the exact finite-pool optimum;
- absolute and relative greedy optimality gaps;
- an explicit synthetic-scope warning.

The scientific contract checks qualitative conclusions rather than brittle exact floating-point
snapshots.

## Reproducibility and CI

The exact v1.3.0 release-candidate commit must pass:

- `quality`: Poetry lock consistency, Ruff and strict mypy;
- `test`: Python 3.11, 3.12 and 3.13;
- `package-artifact`: wheel/sdist build, clean-environment installation and execution;
- `scientific-smoke`: regeneration of all scientific command outputs plus scientific-contract checks;
- `container-scientific`: offline regeneration and scientific-contract verification inside the locked container;
- `Dependabot policy`: validation by `DiogoRibeiro7/safe-dependabot@v1`.

The direct scientific-smoke job uploads both the Bipolaris decision bundle and the transport-design
evidence bundle together with `pyproject.toml` and `poetry.lock`.

## Dependency policy

The project dependency graph is unchanged for the 1.3.0 version bump, so `poetry.lock` is not
regenerated solely because the package version changed.

Dependabot coverage now includes:

- pip;
- GitHub Actions;
- Docker;
- pre-commit.

Routine version updates are constrained to minor/patch updates by the shared Safe Dependabot policy,
without suppressing security remediation.

## Scientific boundary

The transport-design programme remains controlled synthetic known-truth evidence only.

It does not establish:

- real pesticide diffusion or decay parameters;
- environmental-fate estimates;
- real field sampling costs;
- regulatory monitoring designs;
- agronomic recommendations.

The published empirical hop and Bipolaris conclusions, promotion rules, negative results and stop
boundaries remain unchanged.

## Version metadata

The final release commit must agree on:

```text
pyproject.toml: 1.3.0
CITATION.cff: 1.3.0
crop_protection_ps.__version__: 1.3.0
.zenodo.json: 1.3.0
CHANGELOG.md: 1.3.0
```

## Release procedure

After this release-preparation PR is merged and push CI on `main` is green:

1. capture the exact 40-character `main` SHA;
2. run the manual `Release` workflow with:
   - `version = 1.3.0`;
   - `target_sha = <exact green main SHA>`;
   - `prerelease = false`;
   - `dry_run = true`;
3. inspect the dry-run result;
4. rerun the same version/SHA with `dry_run = false`;
5. verify tag `v1.3.0`, wheel, sdist, `SHA256SUMS`, GitHub Release and Zenodo metadata.

The release workflow must refuse any target that is not the current green `main` commit.

## Remaining limitations

- profile/Fisher diagnostics are design- and model-dependent;
- finite-scenario robustness does not prove global minimax optimality;
- exact subset benchmarking is exact only within the declared finite candidate pool;
- the Gaussian observation model and one-dimensional PDE remain deliberately simplified;
- no empirical crop-protection transport data are introduced by this release.
