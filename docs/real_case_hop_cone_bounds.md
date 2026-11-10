# Hop cone infection: what can be learned without assuming missing means healthy?

This is a missing-outcome sensitivity extension to the independently published
[Gent et al. (2025) late-season hop experiment](real_case_hop_cone_quality.md).
It uses the **same two checksum-pinned original source CSV files**, the same
year–block–treatment plot identifiers and the same predefined comparison with
ceasing fungicide applications at bloom. No new experimental data or machine-learning
candidate is introduced.

## Identification rather than imputation

`Mildew.csv` describes ten plant slots in each plot. When scored, a plant's `PM`
is the number of infected cones **out of ten**; when unscored, `PM` is a literal
`.`. A plot therefore has 100 scheduled cone assessments.

For plot \((y,b,t)\), write \(o_{ybt}\) for the total infected cones among
scored plants and \(m_{ybt}\) for its number of unscored plant slots. Without
assuming anything about why a plant is unscored, its true full-plot infection
rate, in percent, satisfies:

\[
  L_{ybt} = o_{ybt}
  \;\leq\;
  I_{ybt} \;\leq\;
  o_{ybt}+10m_{ybt} = U_{ybt}.
\]

The bounds are **sharp conditional on the stated 10-cone sampling frame**:
each missing plant can contribute between zero and ten infected cones, and no
further restriction is supplied by the data. In particular, an observed zero
on eight plants with two unscored plants represents a **0–20% range**, not
zero infection. Ten unscored plant slots represent **0–100%**, distinct from
a year that has **no disease data source at all**.

For each within-year, within-block intervention comparison \(t\in\{2,3,4\}\)
against treatment 1 (cease at bloom), the difference in infection incidence
in percentage points is bounded by:

\[
  \Delta_{ybt}
  \in [\,L_{ybt}-U_{yb1},\; U_{ybt}-L_{yb1}\,].
\]

The annual **seven-block descriptive mean** is bounded by the arithmetic
means of those pairwise lower and upper endpoints, provided every block pair
has source coverage. No pair is discarded merely because one plant was unscored.
A pair or year without any source disease data remains `not_in_source`; it is
not reported as a `0–100%` interval or included in an average.

## Real source results

| Coverage item | Count |
| --- | ---: |
| Quality plots | 140 |
| Plots with disease-source rows | 112 |
| Complete, point-identified disease plots | 89 |
| Partially identified disease plots | 23 |
| Plant outcomes missing as literal `.` | 203 |
| Quality contrasts | 105 |
| Disease contrasts with source coverage | 84 |
| Point-identified disease contrasts | 65 |
| Additional bounded, partially identified disease contrasts | 19 |
| Contrasts with no disease source (2021) | 21 |

For the annual mean of seven paired plots, all estimates below are **percentage
point** differences against ceasing applications at bloom:

| Year | One extra application | Two extra | Three extra |
| --- | ---: | ---: | ---: |
| 2018 | [−30.00, +28.57] | [−30.00, +31.43] | [−30.00, +28.57] |
| 2019 | [−42.86, +42.86] | [−42.86, +42.86] | [−42.86, +42.86] |
| 2020 | −5.57 | −2.00 | −4.57 |
| 2021 | No disease source | No disease source | No disease source |
| 2022 | −0.71 | −0.43 | −0.57 |

All 2018–2019 *observed* disease counts were zero, but the missing plant
assessments make every annual treatment-difference interval cross zero. Those
source years therefore **do not identify the direction** of the annual
differences under arbitrary missingness. The 2020 and 2022 point values have
no missing plant counts, so the missing-data bounds collapse to the ordinary
within-block descriptive differences. Their negative algebraic signs do not
establish a treatment effect, statistical significance or commercial benefit.

## What this analysis cannot establish

- These are **identified ranges**, not confidence intervals. They quantify
  missing-outcome ambiguity and deliberately do not model sampling variation,
  block dependence, randomization or multiple-testing uncertainty.
- Although ten plants are assessed within each plot, plants are subsamples;
  they are not independent treatment replicates. The annual unit remains the
  seven field blocks.
- In 2021 no `Mildew.csv` records exist. We cannot infer disease-free plots or
  a meaningful disease contrast from that year's quality measurements.
- All treatment arms received fungicide; there is no untreated comparator,
  application cost or field-yield evidence. These intervals are not a fungicide
  strategy recommendation or estimates of untreated biological efficacy.
- No bound is used to tune a new predictor or reopen the six-environment
  Bipolaris promotion gate.

The original [quality and block-influence analysis](real_case_hop_cone_quality.md)
remains unchanged. In particular, the original 2022 alpha-acid outlier remains
in the quality data; infection missingness bounds do not address its influence.

## Reproduce and audit

Download the original `Mildew.csv` and `Cascade.csv` directly from the
[authors' public source repository](https://github.com/DavidGent-Lab/Gent-et-al-2025-A-Modified-Disease-Risk-Index-for-Hop-Powdery-Mildew-PhytoFrontiers-).
Do not redistribute the source files from this repository. Both inputs are
validated using their pinned canonical SHA-256 hashes, original schema and
experimental-unit constraints before bounds are computed.

```bash
poetry run python -m crop_protection_ps.hop_cone_bounds \
  --mildew downloads/Mildew.csv \
  --cascade downloads/Cascade.csv \
  --output results/real_hop_powdery_mildew/late_season/bounds
```

The **derived-only** files are:

1. [`plot_bounds.csv`](../results/real_hop_powdery_mildew/late_season/bounds/plot_bounds.csv)
   — 140 source quality plots, including 28 with no disease source.
2. [`paired_bounds.csv`](../results/real_hop_powdery_mildew/late_season/bounds/paired_bounds.csv)
   — 105 predefined block-matched contrasts, 84 of them bounded.
3. [`year_bounds.csv`](../results/real_hop_powdery_mildew/late_season/bounds/year_bounds.csv)
   — 15 annual comparisons with missing-data identification status.
4. [`summary.json`](../results/real_hop_powdery_mildew/late_season/bounds/summary.json)
   — pinned provenance, coverage counts and explicit assumptions.

Offline tests exercise asymmetric missingness, a fully unobserved plot, point
identification, sign identification and absent-year handling. They also
recompute each persisted pair bound from its recorded plot endpoints, so a
stale or accidentally edited result fails CI without re-downloading sources.
