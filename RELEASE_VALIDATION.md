# Release validation — v1.0.1

Date: 2026-08-28

## Release scope

v1.0.1 is a **publication-hygiene patch** over v1.0.0. It does not change the scientific scope,
models, data-generating processes, estimands, validation strategies, promotion rules, numerical
claims or persisted analysis results.

The patch makes three public-release corrections:

1. ignored runtime cache directories are excluded from the release archive;
2. stale references to private preparation material are removed from public documentation;
3. package, citation and artifact-manifest metadata are advanced to 1.0.1.

The public repository remains organised around four headline results: real-field transportability,
validated multi-fidelity progression, portfolio-aware value of information, and
applicability-domain/model-risk control.

## Scientific evidence boundary

The repository distinguishes three evidence classes:

- **public real field data**: the Richardson & Gent hop fungicide experiment;
- **real-data-derived methods**: Bayesian hierarchy, environment transportability and adaptive
  replication built from that public case;
- **controlled synthetic methods**: multi-site simulation, multi-fidelity progression, portfolio
  VOI, multi-objective optimisation and model-risk stress testing.

Synthetic regret, hypervolume, calibration and model-risk gains are properties of explicit
controlled DGPs. They are not empirical performance estimates for a commercial Crop Protection
pipeline.

See `docs/evidence_map.md` and `docs/principal_scientist_review.md`.

## Patch-diff audit

The v1.0.1 publication tree was compared against the frozen v1.0.0 release before the new artifact
manifest was generated.

Scientific Python source is byte-identical to v1.0.0 except for the package version string in
`src/crop_protection_ps/__init__.py`. Persisted scientific data and result files are also retained
byte-for-byte from v1.0.0.

The intentional content changes are limited to:

- version metadata;
- changelog and release-validation prose;
- one neutral reviewer-facing heading;
- removal of ignored runtime caches;
- regeneration of the final artifact manifest.

No model result was recomputed or replaced for the patch release.

## Automated tests

Command:

```bash
PYTHONPATH=src pytest -q
```

Result:

```text
....................................................                     [100%]
```

**52/52 tests passed.**

## Python compilation

Command:

```bash
python -m compileall -q src tests
```

Result: **PASS**.

## Line-length audit

A full scan of `src/**/*.py` and `tests/**/*.py` found:

```text
violations 0
```

The repository's 100-character Python line rule is therefore satisfied by the v1.0.1 tree.

## Public-artifact audit

The public tree was scanned for company-specific naming and references to private preparation
material. The final scan returned zero matches for the prohibited publication-only terms used in
that audit.

The public artifact contains the neutral reviewer-facing documents:

```text
docs/technical_walkthrough.md
docs/evidence_map.md
docs/principal_scientist_review.md
docs/validated_environment.md
```

## README audit

The README remains the curated v1.0 scientific entry point. It foregrounds four results rather than
replaying the full development history, and the headline claims are linked to persisted evidence.

## Version metadata

Final release metadata:

```text
pyproject.toml: 1.0.1
CITATION.cff: 1.0.1
crop_protection_ps.__version__: 1.0.1
```

## Full scientific execution record

v1.0.0 froze the scientific scope and completed the full execution audit: all nine pipelines and all
nine notebooks were executed from the release checkout, with the notebook audit using fresh kernels.

Because v1.0.1 changes no scientific implementation or persisted analysis result, the patch does not
claim a second full Monte Carlo/notebook recomputation. Instead it re-runs the complete unit-test and
compilation gates and verifies by byte comparison that scientific source and result artifacts are
unchanged apart from the package version string.

This avoids introducing new floating-point serialisation or timestamp-only differences into a
publication-only patch.

## Validated environment

The direct package versions used for the frozen scientific release are recorded in
`docs/validated_environment.md`. That file is a tested-environment snapshot, not a complete
transitive dependency lock.

## Ruff and mypy

Ruff and mypy are declared development dependencies and remain configured in CI, but they are not
installed in this offline local runtime. This receipt therefore **does not claim local Ruff or mypy
execution**.

The patch-specific local checks actually run were pytest, Python compilation, the complete Python
line-length audit, publication-specificity scanning, version checks, byte-diff checks, artifact
manifest verification, Git worktree verification and ZIP integrity validation.

## Known scientific limitations retained in v1.0.1

The patch does not suppress the project's main limitations:

- only one public Crop Protection field dataset is analysed;
- only four trial years remain after the source-defined 2019 flooding exclusion;
- the Python source-aligned model is not numerically equivalent to the published SAS GLIMMIX /
  Kenward–Roger analysis;
- the untreated sentinel is an in-season state signal, not a fully prospective pre-season predictor;
- controlled promotion gates are explicit project rules, not independently preregistered trials;
- synthetic multi-fidelity, portfolio, optimisation and model-risk gains do not establish external
  industry performance;
- kNN applicability distance is an interpretable heuristic, not a domain-science or regulatory
  guarantee;
- no complete transitive dependency lockfile is included in this offline release.

These limitations are developed in `docs/principal_scientist_review.md`.

## Final artifact integrity

The final repository manifest is stored at:

```text
results/artifact_manifest.json
```

It is regenerated only after the publication tree is frozen. Every listed SHA-256 digest is then
recomputed against the final file bytes before the ZIP is created.

The external ZIP checksum is stored beside the release archive in
`crop-protection-predictive-science-v1.0.1.zip.sha256`.
