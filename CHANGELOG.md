# Changelog

## 1.1.0 — 2026-09-09

### New empirical evidence

- added a second independent public Crop Protection field-data case using multi-environment Bipolaris / southern corn leaf blight phenotyping data;
- added scalar AUDPC burden and functional disease-trajectory analysis across 1,105 observations, six environments and 13 hybrids;
- added prospective leave-one-environment-out transport validation for global and hybrid-history baselines;
- added a pre-specified promotion contract for richer candidates and preserved the planting-window candidate as a negative result when it improved pooled error but won only three of six held-out environments;
- added an explicit model-selection stop boundary preventing further prospective promotion on the same six environments without genuinely new evidence.

### Reproducibility and engineering

- strengthened raw-data provenance and cross-pipeline scientific contracts;
- added fully offline locked-container scientific validation;
- enforced Poetry lock consistency and migrated static package metadata to PEP 621 without dependency-lock drift;
- pinned and hardened GitHub Actions dependencies and permissions;
- added wheel/sdist build validation plus clean-environment wheel installation and execution outside the repository tree;
- hardened Bipolaris LOEO identifier handling for numeric environment/hybrid IDs;
- changed pull-request CI to checkout the literal PR head SHA so release-candidate evidence refers to the exact tested commit.

### Scientific boundary

- no promotion criterion was relaxed after observing results;
- the planting-window result remains predictive metadata rather than a causal planting-date effect;
- no additional Bipolaris candidate should be prospectively promoted using only the same six environments;
- NumPy 2.4.x was intentionally not adopted because it was unnecessary for the validated numerical baseline and changed the typing/lock surface.

## 1.0.1 — 2026-08-28

### Publication patch

- removed ignored runtime cache directories from the release archive;
- removed stale references to private preparation documents from the public validation receipt;
- generalised one reviewer-facing heading so the repository remains application-neutral;
- regenerated release metadata and the SHA-256 artifact manifest from the final public tree;
- made no changes to models, data, numerical results, scientific claims or persisted analysis outputs.

## 1.0.0 — 2026-08-28

### Release focus

- froze the modelling scope after nine scientific layers; v1.0 adds no new predictive algorithm;
- replaced the release-history-style README with a concise four-result scientific entry point;
- added `docs/technical_walkthrough.md`, a five-minute route through the strongest evidence;
- added `docs/evidence_map.md` to label every result as public real data, real-data-derived, or controlled synthetic;
- added `docs/principal_scientist_review.md`, an adversarial review of external validity, identifiability, deployment risk and domain limitations;
- added `docs/validated_environment.md` with the exact direct package versions used in local release validation;
- removed private preparation documents from the public artifact;
- promoted package, citation and release metadata to 1.0.0.

### Presentation decision

The public release now foregrounds four results only: real-field transportability, multi-fidelity
progression, portfolio value of information, and applicability-domain/model-risk control. Bayesian
hierarchy, environment enrichment, adaptive replication and multi-objective optimisation remain
available as supporting depth rather than competing for front-page attention.

### Scientific boundary

The v1.0 evidence map makes the empirical/synthetic boundary explicit. Only the public fungicide
field-trial analyses are empirical Crop Protection results. Numerical gains from multi-fidelity,
portfolio, optimisation and model-risk experiments are properties of controlled DGPs and are not
industry performance estimates.

## 0.9.0 — 2026-08-28

### Added

- controlled applicability-domain stress audit built on the formulation/application response surface;
- strict separation of model fitting, in-domain calibration, near-shift calibration and final stress testing;
- compact quadratic ridge deployment model with no post-hoc clipping of extrapolative predictions;
- seven-nearest-neighbour applicability distance in standardised historical experimental space;
- pre-specified abstention threshold based only on in-domain calibration support;
- finite-sample split-conformal uncertainty with in-domain, global stress and distance-scaled variants;
- 50-rollout paired model-risk evaluation with Monte Carlo intervals and a promotion gate;
- `09_applicability_domain_model_risk.ipynb`, methodology documentation, figures, tests and CI integration.

### Scientific result

- Reusing the in-domain 90% interval across the shifted stress set yields only about 50.6% coverage.
- A single globally widened stress-calibrated interval reaches about 70.0% coverage.
- Distance-scaled uncertainty reaches about 92.9% stress-set coverage, but average interval width grows from roughly 0.43 to 0.83.
- The abstention rule rejects about 98.1% of shifted conditions and reduces latent efficacy MAE by about 70.4% among accepted predictions.
- The controlled result is presented as model-risk methodology, not as a product applicability criterion or regulatory guarantee.

## 0.8.0 — 2026-08-28

### Added

- controlled three-dimensional formulation/application candidate grid with hidden efficacy, environmental-burden and crop-injury response surfaces;
- independent conjugate Bayesian nonlinear response surfaces with posterior predictive uncertainty;
- constrained efficacy-only expected improvement and ParEGO-style multi-objective acquisition;
- posterior crop-injury feasibility probability inside the sequential acquisition rule;
- exact hidden feasible Pareto-front construction and two-objective hypervolume scoring;
- equal 30-evaluation budget comparison across random, efficacy-only and constrained multi-objective search;
- 50-rollout paired Monte Carlo evaluation and a pre-specified hypervolume promotion gate;
- `08_multiobjective_bayesian_optimisation.ipynb`, methodology documentation, figures and tests;

### Scientific result

- Mean feasible hypervolume ratio is about 0.902 for constrained multi-objective search versus 0.832 for efficacy-only search.
- The resulting improvement is about 8.4%, with a paired 95% Monte Carlo interval for the hypervolume-ratio difference of approximately [0.064, 0.076].
- The multi-objective policy evaluates fewer truly unsafe conditions than random search in the locked DGP.
- All numerical gains are explicitly scoped to the controlled formulation/application DGP and are not empirical product claims.

## 0.7.0 — 2026-08-28

### Added

- controlled R&D portfolio layer with uncertain efficacy and safety-margin states;
- heterogeneous downstream success reward and development cost for each candidate;
- exact count-and-budget 0/1 knapsack for the terminal advancement decision;
- efficacy-confirmation and safety-confirmation follow-up experiments with unequal costs;
- deterministic Gauss-Hermite integration for expected information gain;
- technical-success entropy acquisition and portfolio-boundary EVSI acquisition;
- equal-budget comparison of uniform, uncertainty-only and decision-aware follow-up policies;
- paired oracle-regret and realised-portfolio-value evaluation;
- pre-specified promotion gate tied to final decision quality rather than acquisition-score magnitude;
- `07_portfolio_decision.ipynb`, methodology documentation, figures, CLI and tests.

### Scientific result

- Every equal-budget policy spends exactly 24 follow-up cost units.
- Mean oracle regret is 149.51 for uniform allocation, 126.65 for uncertainty sampling and 105.45 for portfolio-VOI.
- Portfolio-VOI reduces regret by 16.74% versus uncertainty sampling and 29.47% versus uniform allocation.
- The paired regret difference versus uncertainty is -21.21 with Monte Carlo 95% interval [-26.36, -16.05].
- The numerical result is explicitly scoped to the controlled DGP and is not presented as a commercial portfolio estimate.

## 0.6.0 — 2026-08-28

### Added

- controlled lab → glasshouse → field candidate-progression simulation with known latent field truth;
- candidate-specific cross-fidelity discordance in addition to replicate measurement error;
- historical lab-only and lab+glasshouse calibration trained against observed field means;
- held-out calibration promotion gate before glasshouse evidence can influence progression;
- exact equal-budget comparison of field-only, lab→field and full multi-fidelity policies;
- 5,000-rollout common-random-number evaluation using oracle top-eight recall and field-selection regret;
- `06_multifidelity_candidate_progression.ipynb`, CLI, methodology documentation, figures and tests;
- CI and Makefile integration for the new pipeline.

### Scientific result

- Held-out field-calibration RMSE falls from about 0.7325 with lab-only evidence to 0.4700 with lab + glasshouse, a 35.8% improvement.
- At identical 1,040-unit experimental spend, the multi-fidelity policy recovers about 70.8% of the true top-eight candidates versus 64.9% for lab→field.
- Mean field-selection regret falls from about 0.2020 to 0.1401, a 30.7% reduction.
- The numerical gains are explicitly scoped to the controlled DGP and are not presented as empirical claims about a commercial Crop Protection pipeline.

## 0.5.0 — 2026-08-28

### Added

- decision-aware adaptive replication for the real fungicide timing problem;
- Normal-Normal sequential updating of product-specific timing contrasts;
- expected information gain about the **sign** of the Early-versus-Late decision;
- explicit comparison with continuous-parameter information gain and uniform replication;
- 10,000-rollout pre-posterior policy evaluation with common random numbers;
- Bayes timing regret, sign entropy and expected wrong-decision summaries across budgets;
- mean adaptive replication allocations by fungicide;
- `05_adaptive_experimental_design.ipynb` and dedicated methodology documentation;
- adaptive-design CLI, tests and CI execution.

### Scientific interpretation

- Parameter-centric design ranks Curzate as the next most informative experiment, while
  decision-centric design ranks Revus because its timing sign remains most uncertain.
- At a budget of 15 additional paired blocks, Decision-EIG reduces expected timing-decision Bayes
  regret by approximately 13.3% and sign entropy by approximately 9.5% relative to uniform
  replication under the current posterior model.
- The v0.4 environment evidence gate is preserved: the untreated sentinel defines the in-season
  decision stage, but product-by-sentinel timing interactions are not reintroduced after failing
  transportability validation.

## 0.4.0 - 2026-08-28

- Added public Corvallis February-May monthly weather summaries for 2009-2025 with explicit provenance.
- Added a fixed 2009-2016 pre-trial climatology for outcome-independent weather anomaly features.
- Added separate pre-season and application-window wetness representations.
- Added a same-year untreated-control sentinel as an explicitly in-season measure of realised disease pressure.
- Added genuine leave-one-year-out comparison of baseline, coarse-weather, sentinel and sentinel-G×E models.
- Added a regularisation sensitivity grid for the environment-state benchmarks.
- Added an evidence-based promotion gate for product-by-environment interaction complexity.
- Recorded a 39.3% LOYO RMSE reduction from the sentinel representation relative to treatment/timing only.
- Retained the failure of coarse weather and the failure of richer G×E interactions as scientific results.
- Added environment-state figures, documentation, tests and a fourth executed notebook.
- Expanded release tests from 19 to 24.

## 0.3.0 - 2026-08-28

- Added an explicit Bayesian hierarchical model for the real hop fungicide field trial.
- Added partial pooling of product effects, product-specific timing deviations, trial-year effects
  and blocks nested within year.
- Added a direct NumPy/SciPy conjugate Gibbs sampler with deterministic multi-chain execution.
- Added classical multi-chain R-hat reporting for timing effects and variance components.
- Added posterior predictive checks, row-level predictive intervals and support-violation auditing.
- Added genuine leave-one-year-out posterior predictive distributions that integrate over new year
  and new nested-block effects.
- Added variance-prior sensitivity analysis for the main timing inference.
- Added partial-pooling, unseen-year prediction and calibration figures.
- Added a third executed notebook and Bayesian case-study documentation.
- Expanded release tests from 15 to 19.

## 0.2.0 - 2026-08-26

- Added a real, public, multi-year fungicide field-trial case study on hop downy mildew.
- Added source provenance and local SHA-256 recording for the raw public CSV.
- Encoded the source-defined 2019 flooding exclusion explicitly while preserving the raw year.
- Added same-year untreated-control normalisation.
- Added 92 matched Early/Late year × block × product contrasts.
- Added year-block cluster-bootstrap uncertainty for the aggregate timing effect and product-level
  bootstrap intervals.
- Added a source-aligned Python fixed-effect re-analysis with an explicit non-equivalence caveat to
  the published SAS GLIMMIX/Kenward–Roger model.
- Added random-CV versus leave-one-year-out transportability auditing.
- Added real-data figures, result tables, documentation, tests and an executed notebook.
- Expanded release tests from 9 to 15.

## 0.1.0 - 2026-08-26

- Added explicit multi-site, multi-year crop-protection trial simulator.
- Added four-parameter logistic dose-response modelling and cluster-bootstrap uncertainty.
- Added random versus leave-one-site-out validation comparison.
- Added site random-intercept mixed-effects model.
- Added transparent D-optimal sequential experiment selector.
- Added public Fundecitrus real-data contract and provenance notes.
- Added tests, CI, Docker, notebook and generated analysis outputs.
