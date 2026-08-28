# Real case study: fungicide timing in hop downy mildew

## Scientific question

How does the timing of synthetic fungicides, when rotated with a copper-based fungicide, relate to
downy-mildew disease burden across replicated field experiments conducted in different years?

The response is **AUDPC**, the area under the disease progress curve. Lower AUDPC corresponds to
less cumulative disease over the assessment period.

## Source and provenance

The analysis uses the public reproducibility data for Richardson & Gent (2024):

- Briana J. Richardson and David H. Gent;
- *Suppression of Hop Downy Mildew as Influenced by the Timing of Selected Fungicides*;
- Plant Health Progress 25(3):324–326;
- DOI `10.1094/PHP-10-23-0086-BR`;
- source repository:
  https://github.com/DavidGent-Lab/Richardon-and-Gent-2024-Plant-Health-Progress

The local raw file is a line-ending-normalised copy of the source CSV. Its SHA-256 is recorded in
`results/real_hop_trial/summary.json`.

## Experimental structure

The data include:

- year;
- treatment sequence;
- block I–V;
- AUDPC;
- early or late timing;
- fungicide product.

The treatment sequence encodes four applications. For example, `KKFF` represents two Kocide
applications followed by two FungiPhi applications. Early and late programmes therefore represent
where the synthetic fungicide appears in the sequence, not merely a timestamp attached to an
otherwise unrelated observation.

The paired analysis respects that structure by comparing Early and Late observations only within:

\[
\boxed{\text{same year} \times \text{same block} \times \text{same product}}.
\]

## Why 2019 is excluded

The source investigators report that April 2019 flooding led to uneven spring growth and confounded
disease measurements. The source paper therefore excluded 2019 from its statistical analysis.

This repository follows the same rule. Crucially, the raw 2019 rows remain present. The exclusion
is encoded as `EXCLUDED_YEAR = 2019` and covered by a unit test.

That distinction matters scientifically:

\[
\text{documented experimental confounding}
\neq
\text{post-hoc deletion of a difficult year}.
\]

## Analysis 1: paired timing contrast

For each complete year-block-product pair,

\[
\Delta_{ybp}=AUDPC^{Late}_{ybp}-AUDPC^{Early}_{ybp}.
\]

Positive values mean the late programme had greater disease burden.

There are 92 complete pairs. The release estimate is

\[
\bar\Delta=40.93,
\]

with a 95% cluster-bootstrap interval

\[
[15.54,67.21].
\]

The cluster bootstrap resamples **year-blocks**, so multiple product contrasts observed in the same
field block are moved together. On the square-root scale used by the source study,

\[
\bar\Delta_{\sqrt{AUDPC}}=1.252,
\]

with 95% interval

\[
[0.513,1.996].
\]

Product-specific intervals are reported rather than suppressed. Several overlap zero, so the
aggregate timing effect should not be interpreted as evidence that every product has the same
magnitude of response.

## Analysis 2: source-aligned statistical model

The published analysis used `sqrt(AUDPC)` and a general linear mixed model with fungicide, timing
and their interaction as fixed effects, and year/block-related random effects. Degrees of freedom
were calculated using the Kenward–Roger approximation in SAS GLIMMIX.

The repository deliberately does not claim exact reproduction. Its Python approximation is

\[
\sqrt{AUDPC}
=
\beta_0
+
\text{Treatment}
+
\text{Timing}
+
\text{Treatment}\times\text{Timing}
+
\text{Year}
+
\text{Year:Block}
+
\epsilon.
\]

Year and year-block are represented as fixed effects. This makes the adjustment transparent but is
not identical to the source random-effects likelihood or its degrees-of-freedom calculation.

The approximation obtains \(R^2=0.884\). Its Type-II ANOVA finds large year/year-block effects,
which is consistent with the raw data: mean untreated AUDPC ranges from about 188 in 2018 to about
942 in 2021 among the primary years.

## Analysis 3: transportability audit

A model can be excellent at explaining represented trial years and fail at prediction in a future
season.

The first benchmark uses one-hot encoded treatment, timing and year with ridge regression. Random
five-fold CV gives

\[
RMSE=2.72,\quad R^2=0.832
\]

on `sqrt(AUDPC)`. Leave-one-year-out validation gives

\[
RMSE=8.43,\quad R^2=-0.618.
\]

The RMSE increase is approximately 210%.

This is not presented as a good deployment model. It is an explicit demonstration of why a trial
year can be a useful adjustment factor for inference but a non-transportable predictive feature.

A second benchmark divides AUDPC by the same-year untreated-control mean and predicts this relative
disease target from treatment and timing only. The random-CV to unseen-year RMSE gap falls to about
9.4%, but predictive R² remains weak. That failure is informative: a future production model would
need measured environmental and biological drivers rather than a year label.

## What a stronger R&D model would add

A realistic next version of this analysis would link trial observations to covariates such as:

- rainfall and leaf-wetness duration;
- temperature and humidity;
- disease pressure at treatment initiation;
- crop phenological stage;
- application volume and coverage;
- formulation and active-ingredient properties;
- prior treatments and resistance-management constraints.

A hierarchical model could then separate persistent treatment effects from environment-specific
responses and estimate uncertainty for a genuinely new season or site.

## Decision relevance

This real case is included because it demonstrates three behaviours expected from predictive
science in R&D:

1. respect the experimental unit and source-defined exclusions;
2. distinguish explanatory adjustment from deployable prediction;
3. treat model failure under domain shift as scientific information about what needs to be measured
   next.
