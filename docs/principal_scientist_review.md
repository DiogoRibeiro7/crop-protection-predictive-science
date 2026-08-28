# Adversarial review from a Principal Scientist perspective

## Overall assessment

This is a credible senior quantitative portfolio project. Its strongest feature is not algorithmic
breadth; it is the repeated attempt to connect statistical validation to an R&D decision and to
preserve negative results when the evidence does not support a richer model.

I would use it as evidence that the author can work with scientists on experimental data. I would
**not** treat it as evidence of Crop Protection domain expertise equivalent to an agronomist,
pathologist, entomologist, formulation scientist or regulatory scientist.

The repository is strongest when it is explicit about that boundary.

## What I would consider genuinely strong

### 1. The real-data case respects experimental context

The 2019 exclusion is inherited from the source investigators because flooding confounded the
experiment. The repository retains the raw rows and applies the exclusion transparently rather than
deleting an inconvenient year after model inspection.

The Early/Late comparison is also paired within year, block and product rather than being presented
as a naive independent-row comparison.

### 2. Deployment-style validation is treated as a scientific choice

The random-versus-leave-one-year-out gap is a useful example because it demonstrates that a model
can have a strong conventional validation score while being poor at the actual extrapolation task.
This is directly relevant to field R&D, where new seasons, sites and biological states are not
random rows from an existing table.

### 3. The repository keeps failures

Coarse weather does not repair new-year prediction. Product × environment interactions do not earn
promotion. Bayesian partial pooling does not make the unseen-year calibration problem disappear.
Those negative results make the project more credible.

### 4. Decision quality is separated from parameter quality

The adaptive-design and portfolio layers distinguish learning a parameter precisely from learning
something that can change an R&D decision. That is a senior-level modelling distinction.

### 5. Applicability is treated as part of deployment

The final layer allows a model to say that a condition lies outside validated support. This is more
scientifically defensible than reporting a point prediction for every input by construction.

## Concerns I would raise in review

### 1. There is only one real Crop Protection dataset

Most of the breadth after the field-trial analysis is demonstrated with controlled synthetic data.
That is legitimate for method verification, but it limits external validity. The repository should
never imply that the synthetic regret, hypervolume or calibration gains are empirical industry
benchmarks.

**What I would want next:** a second independent field dataset or, ideally, historical linked
lab/glasshouse/field observations from a real discovery programme.

### 2. Four usable years are not enough to learn a general environment-response surface

After the source-defined 2019 exclusion, the real trial gives four usable years. That makes strong
claims about year-level weather response or product × environment interaction poorly identified.
The repository recognises this, which is why the failed G×E promotion gate is appropriate.

**What I would want next:** multiple sites and seasons with field-proximal weather, phenology,
initial disease pressure, application conditions and protocol metadata.

### 3. The source-aligned re-analysis is not the published mixed model

The Python fixed-effect approximation is useful for transparency but is not equivalent to the
source SAS GLIMMIX model with random effects and Kenward–Roger degrees of freedom.

**Acceptable answer:** the repository says this explicitly and does not claim numerical replication.
For a formal reproduction study, I would require a statistically equivalent mixed-model
implementation or comparison against the published software.

### 4. The untreated sentinel is informative but not fully prospective

Same-year untreated disease pressure helps leave-one-year-out prediction, but it is only available
after the new season has started. It is an in-season state measurement, not a pre-season predictor.

**Implication:** it can support adaptive decisions within a season, but not every early discovery or
planning decision.

### 5. The synthetic promotion gates are not externally preregistered

The project uses explicit thresholds before comparing alternatives inside each controlled
experiment. That is better than selecting the winning metric afterwards, but the thresholds were
not independently preregistered before the project existed.

**Implication:** treat them as engineering/scientific decision rules within a demonstration, not as
confirmatory evidence.

### 6. The applicability-domain metric is deliberately simple

Mean k-nearest-neighbour distance in standardised feature space is interpretable, but a real Crop
Protection applicability domain would need chemistry, formulation, crop, target organism, protocol,
geography, season and perhaps mechanistic constraints. Euclidean-style tabular distance is not a
substitute for domain knowledge.

Split-conformal calibration also does not magically retain distribution-free coverage under
arbitrary covariate shift. The distance-aware stress result is an empirical control in the defined
stress experiment, not a formal guarantee under all deployment shifts.

### 7. The multi-objective safety/environment variables are abstract

The Bayesian-optimisation layer is useful methodologically, but crop injury and environmental burden
are controlled response surfaces. They are not toxicology, environmental fate or regulatory risk
models.

**What I would want next:** domain-specific endpoints, constraints and measurement error models
defined with subject-matter experts.

### 8. Experimental economics are illustrative

The portfolio and multi-fidelity costs are relative simulation units. They show how to formulate a
resource-allocation problem but are not estimates of real programme economics.

### 9. Reproducibility is good but not environment-locked

The project supplies Poetry dependency ranges, tests, CI, persisted results and artifact hashes.
The v1.0 release also records the exact direct package versions used for validation. It still does
not provide a complete transitive lockfile generated from an external package index.

That limitation should remain explicit.

## Questions I would ask the author

1. What is the experimental unit in the real field trial, and why does it matter for uncertainty?
2. Why is leave-one-year-out validation harder than random folds here?
3. Why did coarse weather hurt transportability, and what measurements would you request instead?
4. What is the distinction between epistemic uncertainty and being outside the applicability domain?
5. When would you use a hierarchical model rather than a boosted-tree benchmark?
6. What evidence would persuade you to promote a product × environment interaction model?
7. Why can uncertainty sampling allocate experiments inefficiently for a portfolio decision?
8. How would you validate a lab or glasshouse surrogate before it influences field progression?
9. What parts of the model-risk layer would have to be co-designed with crop scientists?
10. Which result in the repository would you **not** generalise beyond the current data, and why?

## Bottom line

The repository is persuasive if it is presented as:

> a demonstration of rigorous quantitative collaboration with experimental scientists.

It becomes less persuasive if it is presented as:

> proof that the author already knows Crop Protection biology or that the simulated percentage gains
> will reproduce in a proprietary R&D pipeline.

The v1.0 front page is intentionally organised around that distinction.
