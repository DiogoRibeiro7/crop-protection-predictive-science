# Environment-aware transportability and evidence-gated G×E modelling

Version 0.4.0 asks a deliberately operational question:

> If treatment and timing do not transport well to a new season, what kind of environment state
> actually improves prediction?

The answer is not assumed in advance. Four representations are compared under genuine
leave-one-year-out validation.

## External environment data

The source experiment was conducted in an experimental hop yard near Corvallis, Oregon. The
repository adds public Corvallis monthly summaries for February-May from 2009-2025 containing mean
temperature, sunshine hours, rainfall and rain days.

The weather data are intentionally treated as **coarse external proxies**, not exact plot-level
exposures. They come from public WeatherAPI year-by-year history tables, while the trial-location
statement comes from Richardson & Gent (2024).

The feature definition is outcome-independent. February-March forms a pre-application window and
April-May forms an application/disease-development window. Weather anomalies are referenced to a
fixed **2009-2016 pre-trial climatology**.

For a window \(w\), a simple wetness index is

\[
W_w = \frac{z(\text{rainfall}) + z(\text{rain days}) - z(\text{sunshine})}{3}.
\]

This index is not claimed to be a biological disease model. Its purpose is to provide a transparent,
externally defined environment summary that can be stress-tested without fitting the index weights
to the disease outcomes.

## Four predictive contexts

All models use ridge regression with a fixed primary penalty \(\alpha=10\) on the
\(\sqrt{AUDPC}\) target. The same conclusion is checked over \(\alpha\in\{1,5,10,20\}\).

### 1. Baseline

\[
\sqrt{AUDPC} \sim \text{product} + \text{timing}.
\]

This is the minimal transportable treatment model.

### 2. Coarse weather

The baseline is augmented with:

- February-March wetness;
- April-May wetness;
- April-May temperature anomaly.

These variables are exogenous to the treatment outcome, but they are monthly and geographically
coarse.

### 3. Same-year untreated sentinel

For each trial year,

\[
S_y = \sqrt{\overline{AUDPC}_{NT,y}}
\]

is computed only from the five untreated-control plots.

The model becomes

\[
\sqrt{AUDPC}_{i}
\sim
\text{product}_i + \text{timing}_i + S_{y[i]}.
\]

This is an **in-season** model. The held-out year's treated observations are never used in fitting,
but its untreated-control sentinel is assumed available. It therefore represents adaptive R&D after
the new environment has started to reveal itself, not a pre-season forecast.

### 4. Sentinel G×E

The richer candidate adds

\[
\text{product}\times S_y
\quad\text{and}\quad
\text{timing}\times S_y.
\]

These interactions are mathematically estimable, but with only four independent trial years they
are potentially fragile. The repository therefore does not promote them because they sound more
scientific. They must beat the simpler sentinel model under unseen-year validation.

## Locked leave-one-year-out result

With \(\alpha=10\):

| Model | LOYO RMSE | LOYO R² |
| --- | ---: | ---: |
| Treatment + timing | **8.531** | **-0.658** |
| + coarse weather | **20.214** | **-8.308** |
| + untreated sentinel | **5.176** | **0.390** |
| + sentinel G×E | **5.252** | **0.372** |

The untreated sentinel reduces RMSE by

\[
\boxed{39.3\%}
\]

relative to the treatment/timing baseline.

Coarse monthly weather makes prediction worse in this experiment. That is not interpreted as
"weather does not matter". It says the available environment representation is inadequate: only
four trial years are available, the covariates are monthly city-level summaries, and important
biological state variables are absent.

## Complexity promotion gate

The G×E candidate is promoted only if:

1. aggregate LOYO RMSE is lower than the simpler sentinel model; and
2. it wins in at least three of the four held-out-year folds.

It fails both parts:

\[
RMSE_{G\times E}=5.252 > 5.176=RMSE_{sentinel}
\]

and it wins

\[
\boxed{0/4}
\]

folds.

Therefore the repository records

\[
\boxed{\text{G×E status: exploratory, not promoted}}
\]

rather than presenting a product-specific environment response surface unsupported by deployment-
style validation.

## Scientific interpretation

The comparison separates three different questions that are often mixed together:

### Prospective environment prediction

Can coarse external weather available for a new season predict final disease burden? In this small
experiment, not reliably.

### In-season adaptation

Can a small number of untreated sentinel plots reveal realised disease pressure and help calibrate
predictions for treated plots in the same new season? Yes, materially.

### Product-specific environment response

Is there enough evidence to estimate stable product-by-environment slopes that improve prediction
into another year? Not here.

That distinction matters for R&D strategy. If in-season sentinel information is valuable, the next
experimental design might deliberately reserve low-cost untreated or reference plots as environment
anchors. If a truly prospective model is required, then higher-resolution weather, phenology,
inoculum pressure, soil/canopy moisture, application conditions and pathogen-state measurements
should be collected consistently across substantially more environments.

## Limitations

- Four primary trial years are insufficient for strong claims about general G×E structure.
- Monthly Corvallis weather is not the exact microclimate of the experimental plots.
- The untreated sentinel is an in-season measurement and cannot be presented as a pre-season
  predictor.
- Untreated plots may themselves have measurement error; the current model treats the five-plot mean
  as observed environment state rather than propagating sentinel uncertainty.
- The ridge benchmark is a transportability diagnostic, not a replacement for a mechanistic disease
  epidemiology model.

These limitations are part of the result rather than caveats added after model selection.
