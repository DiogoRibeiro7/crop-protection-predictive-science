# Second empirical case: southern corn leaf blight across field environments

## Why this case exists

The repository's first real-data case is a multi-year hop fungicide-timing experiment. That case is
useful for experimental structure and prospective validation, but one empirical Crop Protection
dataset is too narrow to support a broad portfolio claim.

This second case adds an independent public field dataset on southern corn leaf blight of maize. It
comes from the analysis accompanying Del Ponte (2026), *From Scalar Summaries to Functional
Comparisons: A Framework for Analyzing Plant Disease Progress Curves*, DOI
`10.1094/PHYTO-01-26-0009-LE`.

The source study contains repeated disease-progress observations for maize hybrids across multiple
field environments. The scientific question here remains narrower than the source paper's modelling
question:

> **How stable are hybrid disease burden and trajectory shape across field environments, and do those
> hybrid-specific signals help in a completely held-out environment?**

## Source contract

The canonical CSV is committed at `data/raw/maize_bipolaris.csv` so the empirical workflow can be
reproduced without network access. It is the exact Git object pinned to:

- source repository: `https://github.com/emdelponte/paper-hgam-curves`;
- source commit: `d793d54c17ad404df2f6618d2681c993fcf144cf`;
- source path: `maize_bipolaris.csv`;
- Git blob SHA-1: `433a2d1c37ba4f6069d04d8ffc9f7916f0a8adc3`;
- expected size: 53,293 bytes;
- expected columns: `Ambiente`, `Hibrido`, `DAE`, `Fenologia`, `Bipolaris`.

The local committed file has the same Git blob identity as the upstream object. Unit tests verify
that byte length and object identity before parsing the dataset. The upstream repository is MIT
licensed. SHA-1 appears here only because Git blob identity is defined by SHA-1; it is not being used
as a general-purpose cryptographic integrity claim.

A commit-pinned download helper remains available as an explicit recovery path if the local raw file
is removed. Normal repository execution does not use it.

## Scalar analysis contract

The scalar analysis follows the source workflow's disease-progress window:

\[
20 < DAE < 116,
\]

and requires at least five assessments per environment-hybrid curve.

For each eligible curve the repository computes four transparent summaries:

\[
AUDPC = \int y(t)\,dt,
\]

approximated by trapezoidal integration on the observed assessment days, final observed severity,
maximum observed severity, and an interpolated \(t_{50}\), the first day at which severity reaches
half of that curve's observed maximum.

Hybrid rankings are compared across environments using pairwise Spearman correlations of AUDPC.
This is a descriptive transportability diagnostic. A high correlation means hybrids have similar
relative disease burden in two environments; it does not imply equal absolute disease pressure or a
stable causal treatment effect.

## Functional shape analysis

AUDPC cannot distinguish curves that have similar total burden but different onset, acceleration or
late-season behaviour. The empirical workflow therefore also constructs a common disease-progress
grid from 30 to 110 DAE in two-day increments without extrapolation.

For each eligible curve, the interpolated severity trajectory retains absolute disease burden. A
second representation divides the trajectory by its own time-average severity:

\[
\tilde y_i(t)=\frac{y_i(t)}{\bar y_i}.
\]

This removes overall scale while preserving relative trajectory shape. Pairwise root-mean-square
distances are then computed for both the raw severity curves and the normalized shapes. The main
descriptive comparison asks whether the same hybrid observed in different environments has a
smaller normalized shape distance than different hybrids observed in different environments.

This is not a reproduction of the source HGAM analysis, not a significance test, and not a
promotion gate. It is an auditable nonparametric diagnostic of cross-environment trajectory
stability. The implementation details and limitations are documented in
[`bipolaris_curve_shape_stability.md`](bipolaris_curve_shape_stability.md).

## Prospective leave-one-environment-out validation

Descriptive stability does not establish predictive transport. The empirical workflow therefore
holds out each field environment in turn and constructs predictions using only the remaining
environments.

For scalar disease burden, two deliberately simple predictors are compared:

1. the global mean training AUDPC across all hybrids and environments;
2. the held-out hybrid's own mean AUDPC across the remaining environments.

The second predictor earns a lower held-out error only when hybrid identity carries information that
transports beyond the overall training disease burden.

For normalized disease-curve shape, the same logic is applied pointwise on the common DAE grid. The
baseline is the mean normalized trajectory across every training curve. The hybrid-history predictor
is the mean normalized trajectory for that hybrid across the remaining environments.

The leave-one-environment-out outputs report RMSE, MAE, fold-level hybrid ranking correlation and
fold wins. No held-out outcome is used to construct either predictor. There is deliberately no
promotion threshold or confirmatory significance test: this stage asks whether a simple
hybrid-specific signal transports at all before a richer model is justified.

## What this adds to the portfolio

The project now has two independent empirical field cases with different scientific structures:

1. a fungicide-timing experiment with paired treatment contrasts and unseen-year validation;
2. multi-environment disease-progress phenotyping with repeated temporal measurements, scalar host
   rankings, trajectory-shape comparisons and prospective held-out-environment validation.

It does **not** solve every external-validity concern. The Bipolaris dataset is not a second fungicide
intervention trial, and neither public case is linked historical lab, glasshouse and field evidence
from an industrial discovery programme. The controlled multi-fidelity and portfolio results remain
method demonstrations rather than empirical estimates of industry performance.

## Reproduce

From the repository root:

```bash
poetry run crop-protection-bipolaris
```

The command uses the committed `data/raw/maize_bipolaris.csv` and requires no network access. If the
raw file is intentionally removed, `download_bipolaris()` can recover the exact commit-pinned source
and verifies its Git blob identity before writing it locally.

Outputs are written under `results/bipolaris/`:

- `curve_metrics.csv`;
- `environment_summary.csv`;
- `environment_rank_spearman.csv`;
- `functional_profiles.csv`;
- `functional_distances.csv`;
- `loeo_burden_predictions.csv`;
- `loeo_burden_folds.csv`;
- `loeo_shape_predictions.csv`;
- `loeo_shape_folds.csv`;
- `summary.json`;
- `figures/median_audpc_by_environment.png`;
- `figures/functional_shape_stability.png`;
- `figures/loeo_audpc_transport.png`.

The `summary.json` file contains scalar, functional and prospective-validation summaries in one
reproducible empirical result bundle. CI now executes this full empirical workflow as part of the
scientific-smoke job, using only the committed source data.

## Next scientific extension

Only if same-hybrid history materially improves held-out-environment performance should a richer
prospective model be considered. The next candidate would need genuinely prospective environment
covariates or a structured environment model, and it should be promoted only if it beats these
simple leave-one-environment-out baselines consistently rather than merely fitting the pooled data
better.
