# Bayesian hierarchical extension of the real field trial

## Scientific objective

The frequentist analyses in the real-data case establish two things: there is evidence that timing
matters on average, and models that look strong under random cross-validation can fail badly on an
unseen season. Version 0.3.0 asks a more demanding question:

> How should uncertainty be propagated when product response, trial year and experimental block
> are all heterogeneous, and what does that uncertainty look like for a genuinely unseen year?

The Bayesian model is fitted to the 187 synthetic-fungicide timing observations after the
source-defined 2019 exclusion.

## Model

The source response is square-root transformed AUDPC. Before sampling, that response is standardised
for numerical stability. For observation \(i\),

\[
z_i = \alpha + a_{p[i]}
+ \left(\delta + d_{p[i]}\right)L_i
+ u_{y[i]} + b_{y[i],k[i]} + \varepsilon_i,
\]

where:

- \(L_i=1\) for a Late programme and 0 for Early;
- \(a_p\) is a partially pooled product effect;
- \(\delta+d_p\) is the product-specific Late-minus-Early timing effect;
- \(u_y\) is a partially pooled year effect;
- \(b_{y,k}\) is a block effect nested within year;
- \(\varepsilon_i\) is residual variation.

The exchangeable effects are Gaussian with variance components inferred from the data. Variance
components use explicit inverse-gamma priors. The sampler is a conjugate Gibbs implementation in
NumPy/SciPy rather than a hidden probabilistic-programming call, so the conditional updates and
random-effect structure are inspectable.

The response standardisation is reversed for all reported effects and predictions.

## Partial pooling

The population-average Late-minus-Early effect is

\[
\boxed{1.331\ \text{on the }\sqrt{AUDPC}\text{ scale}}
\]

with a 90% posterior interval

\[
\boxed{[0.724,\ 1.942]}.
\]

The posterior probability that Late timing produces greater disease burden than Early timing is

\[
\boxed{P(\Delta>0\mid D)=0.9997}.
\]

Product-specific effects are not estimated independently. They are shrunk toward the population
pattern in proportion to the information available for each product. This is preferable to treating
five noisy product estimates as unrelated or forcing them to be identical.

The posterior for Revus remains the least decisive: its 90% interval crosses zero, whereas the
other product-level intervals are positive in this model. The repository preserves that distinction.

## Sampler checks

The release uses four independent chains, 800 retained draws per chain, an 800-iteration burn-in
and thinning by two. The largest classical multi-chain R-hat among the monitored timing and variance
quantities is

\[
\boxed{1.0012},
\]

which gives no sign of chain-level non-convergence for those summaries.

This is deliberately reported as *classical R-hat*. The project does not claim the more advanced
rank-normalised diagnostics provided by dedicated Bayesian frameworks.

## Posterior predictive checks

The fitted model reproduces the overall mean and dispersion of the observed transformed response
well. Posterior predictive row coverage is:

- 90% interval: **93.0%**;
- 95% interval: **97.9%**.

The Gaussian model assigns a very small amount of probability to negative values on the transformed
sqrt(AUDPC) scale: approximately **0.0045%** of training posterior-predictive draws. This support
mismatch is retained as a model diagnostic rather than hidden by clipping predictions.

## Genuine leave-one-year-out prediction

The most important predictive experiment removes an entire trial year, refits the model and then
predicts that season as genuinely unseen.

For a held-out year, the model is not allowed to reuse the year effect or the year-block effects.
Instead, each posterior draw samples:

\[
u_{new}\sim N(0,\sigma^2_{year})
\]

and new nested block effects

\[
b_{new,k}\sim N(0,\sigma^2_{year:block}).
\]

This produces a posterior predictive *distribution* for a new season rather than a point forecast
that silently treats future environmental conditions as known.

Aggregated across all four held-out years:

- posterior-predictive mean RMSE: **8.36** on sqrt(AUDPC);
- MAE: **7.38**;
- nominal 90% interval coverage: **77.0%**;
- nominal 95% interval coverage: **91.4%**;
- mean 90% interval width: **24.60**;
- mean 95% interval width: **30.32**.

The undercoverage is scientifically important. In particular, 2020 is poorly predicted even after
integrating over new-year uncertainty. The model knows that years vary, but treatment, timing and a
random year intercept do not contain enough information to reconstruct an unusually difficult
season.

The correct conclusion is not to make the prior wider until nominal coverage is obtained. It is:

\[
\boxed{\text{new-season prediction needs measured environmental and biological state.}}
\]

Weather, phenology, disease pressure, inoculum, application conditions and potentially
product-by-environment interactions are natural next covariates.

## Prior sensitivity

The release multiplies all variance-prior scale parameters by 0.5, 1 and 2. The population timing
posterior mean remains approximately 1.33--1.36 on the sqrt(AUDPC) scale, and
\(P(\Delta>0\mid D)\) remains at least 0.999 in all three fits.

That does not prove prior irrelevance. It shows that the *main timing inference* is not being driven
by the tested variance-prior scale. Predictive uncertainty for a new year is much more sensitive to
how between-year variation is represented, because there are only four usable seasons.

## Why this matters for Crop Protection R&D

The model demonstrates a distinction that is easy to lose in generic ML workflows:

\[
\text{stable inference within observed experiments}
\not\Rightarrow
\text{reliable prediction in a new environment}.
\]

Partial pooling is useful because field trials contain many small, related experimental groups.
Posterior predictive distributions are useful because R&D decisions depend on uncertainty, not only
on ranking candidate point predictions. But a hierarchical model still cannot substitute for
missing scientific measurements.

That is the intended Predictive Science message of this extension.
