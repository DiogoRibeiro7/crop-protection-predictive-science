# Release validation — v1.1.0

Date: 2026-09-09

## Release scope

v1.1.0 is the first release after the frozen v1.0.1 publication snapshot. It adds a second
independent public field-data case, prospective Bipolaris transport validation, explicit model
promotion and stopping rules, and substantial reproducibility and packaging hardening.

This release does **not** relax any scientific gate or promote a model after observing a failed
criterion.

## Evidence boundary

The repository now contains two independent public field-data cases:

1. the Richardson & Gent hop fungicide-timing experiment, analysed with paired contrasts and
   leave-one-year-out validation;
2. a multi-environment southern corn leaf blight/Bipolaris dataset with scalar burden,
   functional trajectory analysis and leave-one-environment-out validation.

Controlled multi-fidelity, portfolio, optimisation and model-risk experiments remain synthetic
methodology demonstrations rather than empirical industry-performance claims.

## Bipolaris prospective result

The retained hybrid-history burden baseline improves mean held-out AUDPC RMSE and wins four of six
held-out environments. A richer candidate using the pre-known planting-window label reduces pooled
held-out AUDPC RMSE from 533.24 to 467.96 and weighted trajectory-shape RMSE from 0.29665 to 0.28251,
but wins only three of six environments on each endpoint.

The promotion criterion was frozen before evaluation and requires four of six environment wins.
The richer candidate is therefore rejected for both burden and shape.

No further Bipolaris candidate may be prospectively promoted using only these same six environments.
The reopening conditions are recorded in `ROADMAP.md`.

## Reproducibility and engineering changes since v1.0.1

- raw-data provenance and cross-pipeline scientific contracts were strengthened;
- real Bipolaris source, functional-profile and promotion evidence were persisted;
- the scientific workflow can run fully offline in a locked container;
- Poetry and the dependency lock are checked explicitly;
- GitHub Actions dependencies and permissions are pinned/hardened;
- static package metadata was migrated to PEP 621 without dependency-lock drift;
- wheel and source distributions are built in CI;
- the built wheel is installed into a clean environment and executed outside the repository tree;
- generic LOEO identifier handling is robust to numeric environment/hybrid identifiers;
- NumPy 2.4.x was deliberately not adopted because it was unnecessary for the frozen numerical
  baseline and changed the typing/lock surface.

## Release-candidate CI contract

A v1.1.0 tag must not be created until the exact release-candidate commit passes all current jobs:

- `quality`: `poetry check --lock`, Ruff and strict mypy;
- `test`: Python 3.11, 3.12 and 3.13;
- `package-artifact`: build wheel/sdist, install the wheel in a clean environment and run the
  installed console entry point outside the repository;
- `scientific-smoke`: regenerate all scientific command-line outputs and verify the scientific
  contract;
- `container-scientific`: regenerate and verify the scientific contract offline inside the locked
  container.

Pull-request CI is configured to checkout the literal PR head SHA so this receipt can refer to the
same commit that was actually tested.

## Version metadata

The release candidate must agree on:

```text
pyproject.toml: 1.1.0
CITATION.cff: 1.1.0
crop_protection_ps.__version__: 1.1.0
```

`poetry.lock` is not regenerated solely for the version bump because project version metadata is not
part of the locked dependency graph.

## Artifact integrity

`results/artifact_manifest.json` belongs to the historical v1.0.1 publication artifact and remains
as evidence of that frozen archive. v1.1.0 distribution integrity is established by the exact tagged
commit plus the CI-built wheel/sdist. A new repository-wide manifest should only be generated from
the final tagged tree, not from a moving release-candidate branch.

## Remaining limitations

- neither field case justifies causal claims beyond its experimental/observational design;
- the Bipolaris planting-window result is predictive metadata, not a causal planting-date effect;
- the six Bipolaris environments have now been used for candidate evaluation and cannot support an
  unlimited sequence of prospectively promoted models;
- synthetic decision-policy gains do not establish commercial Crop Protection performance;
- further substantive Bipolaris model selection requires new independent environments, prospectively
  available covariates, an untouched external dataset, or a newly agreed estimand.
