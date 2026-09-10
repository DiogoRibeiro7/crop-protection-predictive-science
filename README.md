# Crop Protection Predictive Science

A reproducible scientific-modelling portfolio for **Crop Protection R&D**. The repository is built
around one question:

> **What decision is the model meant to support, does the validation design match that decision,
> and when is another experiment more valuable than another prediction?**

The project combines two independent public field-data cases with controlled experiments that make
model failure, transfer error and decision quality auditable against known truth. It is deliberately
closer to predictive science than to generic tabular machine learning.

## Start here

If you have five minutes, read [`docs/technical_walkthrough.md`](docs/technical_walkthrough.md).
It points to four results that capture the project without requiring a tour of every notebook.

If you want to audit what is empirical versus simulated, use
[`docs/evidence_map.md`](docs/evidence_map.md).

If you want the critical version rather than the sales version, read
[`docs/principal_scientist_review.md`](docs/principal_scientist_review.md).

## Four results worth opening

### 1. Real field data: random validation can answer the wrong question

The public Richardson & Gent hop downy-mildew experiment contains 290 plot-level rows from
2017–2021. The source investigators excluded 2019 because flooding confounded disease measurement;
this repository preserves those rows and applies the exclusion explicitly rather than treating the
year as a statistical outlier.

The primary analysis contains 92 matched Early/Late fungicide-timing contrasts. Across those pairs,

\[
\widehat{\Delta}_{AUDPC}
=
AUDPC_{Late}-AUDPC_{Early}
=
40.93,
\]

with a year-block cluster-bootstrap 95% interval

\[
\boxed{[15.54,\ 67.21]}.
\]

The more important predictive result is the validation gap:

| Validation design | RMSE on \(\sqrt{AUDPC}\) | \(R^2\) |
| --- | ---: | ---: |
| Random five-fold | **2.72** | **0.832** |
| Leave-one-year-out | **8.43** | **-0.618** |

The unseen-year RMSE is about **210% higher**. A trial-year label is useful for adjustment when that
year is already represented, but it has no transportable meaning for a future season.

Open:
[`02_real_fungicide_field_trial.ipynb`](notebooks/02_real_fungicide_field_trial.ipynb) ·
[`year_transportability_gap.png`](results/real_hop_trial/figures/year_transportability_gap.png) ·
[`real_case_hop_downy_mildew.md`](docs/real_case_hop_downy_mildew.md)

### 2. Multi-fidelity evidence: cheap assays must earn the right to influence field decisions

A controlled lab → glasshouse → field experiment asks whether lower-cost evidence can reduce the
number of expensive field experiments without degrading candidate selection.

The glasshouse stage first has to pass an out-of-sample transfer gate. On held-out historical
candidates, adding glasshouse evidence reduces field-efficacy calibration RMSE from **0.7325** to
**0.4700**, a **35.8%** improvement.

Only then is it allowed into the equal-budget progression experiment. With every policy spending
1,040 relative cost units:

| Policy | Field candidates | Top-8 recall | Selection regret |
| --- | ---: | ---: | ---: |
| Field only | 26 | 0.3246 | 0.6633 |
| Lab → field | 22 | 0.6487 | 0.2020 |
| **Lab → glasshouse → field** | **16** | **0.7076** | **0.1401** |

The full hierarchy reduces regret by **30.7%** relative to lab → field under the controlled DGP and
the same experimental budget.

Open:
[`06_multifidelity_candidate_progression.ipynb`](notebooks/06_multifidelity_candidate_progression.ipynb) ·
[`equal_budget_selection_regret.png`](results/multifidelity/figures/equal_budget_selection_regret.png) ·
[`multifidelity_candidate_progression.md`](docs/multifidelity_candidate_progression.md)

### 3. Value of information: uncertainty is not automatically decision-relevant

A controlled portfolio experiment gives every policy the same 24-unit follow-up budget before a
count-and-cost-constrained advancement decision. The terminal portfolio is solved exactly; only the
one-step acquisition rule is approximate.

| Follow-up policy | Realised portfolio value | Oracle regret |
| --- | ---: | ---: |
| Uniform | 245.21 | 149.51 |
| Uncertainty reduction | 268.06 | 126.65 |
| **Portfolio-aware VOI** | **289.27** | **105.45** |

Portfolio-aware value of information reduces regret by **16.7%** relative to uncertainty sampling.
The policy does not simply chase the largest standard error: it spends evidence where a posterior
change can alter the constrained advancement decision.

Open:
[`07_portfolio_decision.ipynb`](notebooks/07_portfolio_decision.ipynb) ·
[`portfolio_regret_by_policy.png`](results/portfolio_decision/figures/portfolio_regret_by_policy.png) ·
[`portfolio_decision.md`](docs/portfolio_decision.md)

### 4. Model risk: sometimes the correct prediction is “do another experiment”

The deployment stress test separates model fitting, in-domain calibration, near-shift calibration
and final shift-heavy testing. A nominal 90% conformal interval calibrated in-domain covers only
**50.6%** of the shifted stress set.

Distance-aware uncertainty inflation recovers **92.9%** stress-set coverage, but average interval
width rises from about **0.43** to **0.83** on a response scale roughly bounded by zero and one.
That width is itself a warning.

An explicit applicability-domain policy therefore allows abstention. It rejects **98.1%** of
genuinely shifted conditions and reduces latent efficacy MAE from **0.1695** under forced prediction
to **0.0502** among accepted predictions, a **70.4% reduction**.

Open:
[`09_applicability_domain_model_risk.ipynb`](notebooks/09_applicability_domain_model_risk.ipynb) ·
[`coverage_by_risk_control.png`](figures/model_risk/coverage_by_risk_control.png) ·
[`model_risk_control.md`](docs/model_risk_control.md)

## A second empirical field case

The independent southern corn leaf blight case adds repeated disease-progress observations for
maize hybrids across multiple field environments. It is used to examine environment-specific
disease burden and the stability of hybrid AUDPC rankings while keeping scalar summaries separate
from full curve-shape information.

This is real field phenotyping, not a second fungicide intervention trial. It broadens the empirical
base without pretending to validate the simulated discovery-programme economics or multi-fidelity
gains.

Open [`docs/second_empirical_case_bipolaris.md`](docs/second_empirical_case_bipolaris.md), or run:

```bash
poetry run crop-protection-bipolaris
```

## What is real and what is controlled

The project never mixes simulated performance numbers with empirical Crop Protection claims.

| Layer | Evidence type | Purpose |
| --- | --- | --- |
| Multi-site dose response | Controlled synthetic | Audit dose response, site shift and D-optimal design against known truth |
| Fungicide timing re-analysis | **Public real field data** | Experimental structure, paired contrasts, provenance and transportability |
| Southern corn leaf blight phenotyping | **Independent public real field data** | Multi-environment disease-progress summaries and ranking stability |
| Bayesian hierarchy | Real-data-derived | Partial pooling, posterior checks and leave-one-year-out uncertainty |
| Environment transportability | Real field data + public weather | Test prospective versus in-season environment information |
| Adaptive replication | Real-data-derived decision simulation | Ask which additional paired block is decision-most-informative |
| Lab → glasshouse → field | Controlled synthetic | Test cross-fidelity calibration and equal-budget candidate progression |
| Portfolio VOI | Controlled synthetic | Allocate scarce evidence before constrained advancement |
| Multi-objective optimisation | Controlled synthetic | Search efficacy/environment trade-offs under crop-injury constraints |
| Applicability domain | Controlled synthetic | Stress uncertainty calibration, support detection and abstention |

See [`docs/evidence_map.md`](docs/evidence_map.md) for source files, analyses, outputs and limitations.

## Scientific principles demonstrated

The repository is organised around a few recurring rules rather than a catalogue of algorithms:

1. **Start from the experimental unit.** Blocks, years, sites and treatment sequences determine what
   can be learned.
2. **Validation must resemble deployment.** Random folds are not evidence for performance in a new
   site, season, formulation region or experimental regime.
3. **Lower-fidelity evidence is a surrogate, not truth.** It must demonstrate held-out transfer to
   the field endpoint before it changes advancement decisions.
4. **Quantify uncertainty at the decision level.** Parameter information and decision information
   can point to different next experiments.
5. **Do not promote complexity automatically.** Product × environment interactions are left
   exploratory when deployment-style validation does not support them.
6. **Treat applicability as part of the model.** A system should expose when a prediction lies
   outside experimentally validated support and be allowed to abstain.

## Supporting methods

The supporting notebooks cover the deeper statistical path behind those four headline results:

- four-parameter logistic dose response with ED50/ED90 and trial-cluster bootstrap uncertainty;
- hierarchical site effects and leave-one-site-out validation;
- source-aligned re-analysis of a public fungicide experiment without claiming numerical equivalence
  to SAS GLIMMIX;
- explicit Bayesian partial pooling over products, years and nested blocks;
- posterior-predictive checks, prior sensitivity and genuine leave-one-year-out prediction;
- environment enrichment with a fixed pre-trial climatology and same-year untreated sentinel;
- decision-specific expected information gain for additional paired blocks;
- D-optimal sequential design;
- constrained multi-objective Bayesian optimisation over efficacy, environmental burden and crop
  injury.

The complete technical index is in [`docs/evidence_map.md`](docs/evidence_map.md).

## Repository map

```text
.
├── configs/
├── data/
│   ├── raw/                   # public source data + provenance contracts
│   └── processed/
├── docs/
│   ├── technical_walkthrough.md
│   ├── evidence_map.md
│   ├── principal_scientist_review.md
│   ├── second_empirical_case_bipolaris.md
│   └── ... method notes ...
├── notebooks/                 # 01–09 executed analyses
├── results/                   # persisted metrics, tables and figures
├── src/crop_protection_ps/    # typed Python package
└── tests/
```

## Reproduce

With Poetry:

```bash
poetry install
poetry run pytest
poetry run crop-protection-real
poetry run crop-protection-bipolaris
poetry run crop-protection-bayesian
poetry run crop-protection-environment
poetry run crop-protection-adaptive
poetry run crop-protection-multifidelity
poetry run crop-protection-portfolio
poetry run crop-protection-multiobjective
poetry run crop-protection-model-risk
```

Without Poetry:

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src python -m crop_protection_ps.real_demo
PYTHONPATH=src python -m crop_protection_ps.bipolaris_demo
PYTHONPATH=src python -m crop_protection_ps.multifidelity_demo
PYTHONPATH=src python -m crop_protection_ps.portfolio_demo
PYTHONPATH=src python -m crop_protection_ps.model_risk_demo
```

The exact direct dependency versions used for the v1.0 validation run are recorded in
[`docs/validated_environment.md`](docs/validated_environment.md). Poetry dependency ranges remain
the package contract; the environment file is a reproducibility snapshot, not a full lockfile.

## Scope and limitations

This is a **portfolio and research-methods demonstrator**, not a pesticide-use recommendation,
registration study, regulatory risk assessment, or estimate of any company's R&D economics.

The empirical evidence now comes from two independent public field-data cases: a multi-year hop
fungicide-timing experiment and multi-environment maize disease-progress phenotyping. The later
decision layers are controlled simulations designed to make methodological behaviour measurable
against known truth. They demonstrate how the methods work; they do not establish that the reported
percentage gains will transfer to a real discovery pipeline.

The repository also does not claim agronomy, formulation chemistry, toxicology or regulatory subject
matter expertise. In a real R&D setting, model structure, applicability domains, scientific
constraints and decision thresholds would be co-defined with domain scientists.

For the deliberately critical version of these limitations, see
[`docs/principal_scientist_review.md`](docs/principal_scientist_review.md).

## Engineering and release validation

The package uses typed Python, Pydantic data/configuration checks, deterministic seeds, pytest,
pre-commit, CI, Docker, persisted analysis outputs and SHA-256 artifact verification.

The v1.1.0 release validation is documented in [`RELEASE_VALIDATION.md`](RELEASE_VALIDATION.md).
The repeatable release procedure is documented in [`docs/releasing.md`](docs/releasing.md).

## Source data

The first real-data case uses the public data accompanying:

> Richardson, B. J. & Gent, D. H. (2024). *Suppression of Hop Downy Mildew as Influenced by the
> Timing of Selected Fungicides*. Plant Health Progress, 25(3), 324–326.
> DOI: `10.1094/PHP-10-23-0086-BR`.

Source repository:
`https://github.com/DavidGent-Lab/Richardon-and-Gent-2024-Plant-Health-Progress`

The second real-data case uses `maize_bipolaris.csv` from:

> Del Ponte, E. M. (2026). *From Scalar Summaries to Functional Comparisons: A Framework for
> Analyzing Plant Disease Progress Curves*. DOI: `10.1094/PHYTO-01-26-0009-LE`.

Source repository:
`https://github.com/emdelponte/paper-hgam-curves`

Product trade names appear only because they are present in the source experiment.

## Licence

MIT. See [`LICENSE`](LICENSE).
