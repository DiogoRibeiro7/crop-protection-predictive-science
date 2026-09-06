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
field environments. The scientific question here is deliberately narrower than the source paper's
functional modelling question:

> **How stable are simple hybrid disease-burden rankings across field environments, and how much
> information is lost when a disease curve is reduced to one scalar?**

## Source contract

The canonical CSV is not copied into the repository. Acquisition is pinned to:

- source repository: `https://github.com/emdelponte/paper-hgam-curves`;
- source commit: `d793d54c17ad404df2f6618d2681c993fcf144cf`;
- source path: `maize_bipolaris.csv`;
- Git blob SHA-1: `433a2d1c37ba4f6069d04d8ffc9f7916f0a8adc3`;
- expected size: 53,293 bytes;
- expected columns: `Ambiente`, `Hibrido`, `DAE`, `Fenologia`, `Bipolaris`.

The upstream repository is MIT licensed. SHA-1 appears here only because Git blob identity is defined
by SHA-1. It is not being used as a general-purpose cryptographic integrity claim.

## Analysis contract

The default analysis follows the source workflow's disease-progress window:

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

Hybrid rankings are then compared across environments using pairwise Spearman correlations of
AUDPC. This is a descriptive transportability diagnostic. A high correlation means hybrids have
similar relative disease burden in two environments; it does not imply equal absolute disease
pressure or a stable causal treatment effect.

## Why scalar summaries are not enough

This case intentionally starts with AUDPC because it is familiar and auditable, not because it is
assumed sufficient. Two disease-progress curves can have similar AUDPC while differing in onset,
acceleration, plateau or late-season behaviour. The source paper is specifically motivated by that
limitation.

Accordingly, the scalar analysis is a baseline for a later functional comparison. It should answer
questions such as whether a hybrid that looks resistant by total disease burden retains that rank
across environments, while making clear when the full curve shape still carries information that
AUDPC removes.

## What this adds to the portfolio

This dataset changes one important limitation: the project no longer rests on a single empirical
field dataset. The two real-data cases now cover different scientific structures:

1. a fungicide-timing experiment with paired treatment contrasts and unseen-year validation;
2. multi-environment disease-progress phenotyping with repeated temporal measurements and
   environment-specific host rankings.

That is a meaningful increase in empirical breadth.

It does **not** solve every external-validity concern. The Bipolaris dataset is not a second fungicide
intervention trial, and neither public case is linked historical lab, glasshouse and field evidence
from an industrial discovery programme. The controlled multi-fidelity and portfolio results remain
method demonstrations rather than empirical estimates of industry performance.

## Reproduce

From the repository root:

```bash
poetry run crop-protection-bipolaris
```

If `data/raw/maize_bipolaris.csv` is absent, the command downloads the exact commit-pinned upstream
object and verifies its Git blob identity before analysis. Unit tests remain offline and do not
require network access.

Outputs are written under `results/bipolaris/`:

- `curve_metrics.csv`;
- `environment_summary.csv`;
- `environment_rank_spearman.csv`;
- `summary.json`;
- `figures/median_audpc_by_environment.png`.

## Next scientific extension

The natural next step is not a more complex tabular learner. It is to test whether the scalar
ranking conclusion changes when disease-progress **shape** is retained. A defensible extension would
compare environment-hybrid curves using a functional representation or smooth model, then ask
whether leave-one-environment-out host rankings are better explained by total burden, timing, curve
shape, or some combination of them.
