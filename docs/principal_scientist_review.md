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

### 1. The real-data cases respect experimental context

The 2019 exclusion in the hop trial is inherited from the source investigators because flooding
confounded the experiment. The repository retains the raw rows and applies the exclusion
transparently rather than deleting an inconvenient year after model inspection.

The Early/Late comparison is also paired within year, block and product rather than being presented
as a naive independent-row comparison.

The independent southern corn leaf blight case adds a different empirical structure: repeated
disease-progress measurements of maize hybrids across multiple field environments. It is not
presented as another fungicide trial, and scalar summaries are retained only as an auditable
baseline rather than being confused with full disease-curve information.

### 2. Deployment-style validation is treated as a scientific choice

The random-versus-leave-one-year-out gap is a useful example because it demonstrates that a model
can have a strong conventional validation score while being poor at the actual extrapolation task.
This is directly relevant to field R&D, where new seasons, sites and biological states are not
random rows from an existing table.

The Bipolaris case extends that principle to leave-one-environment-out validation. Same-hybrid
history improves held-out AUDPC prediction relative to a global training mean and wins four of six
held-out environments, so the transport claim is tied to independent environment units rather than
random rows.

### 3. The repository keeps failures and respects frozen decision rules

Coarse weather does not repair new-year prediction. Product × environment interactions do not earn
promotion. Bayesian partial pooling does not make the unseen-year calibration problem disappear.

The strongest example is the Bipolaris planting-window candidate. Its promotion criteria were frozen
before the real candidate result was opened. The candidate improves pooled AUDPC RMSE and weighted
trajectory-shape RMSE, but wins only three of six held-out environments for each endpoint when four
wins were required. It is therefore retained as rejected rather than rescued by changing the rule
after inspection.

That behaviour is more scientifically persuasive than reporting the numerically better aggregate
metric alone.

### 4. Functional preprocessing is now auditable rather than implicit

The Bipolaris functional analysis now records eligibility for every environment×hybrid curve. All 74
curves satisfy the fixed assessment-count, 30–110 DAE support and mean-severity requirements. The
reported trajectory-shape comparison is therefore not being driven by silent removal of resistant,
short-support or sparsely observed curves in this dataset.

This does not make the result universal, but it removes an avoidable ambiguity about the analysed
population.

### 5. Decision quality is separated from parameter quality

The adaptive-design and portfolio layers distinguish learning a parameter precisely from learning
something that can change an R&D decision. That is a senior-level modelling distinction.

### 6. Applicability is treated as part of deployment

The final layer allows a model to say that a condition lies outside validated support. This is more
scientifically defensible than reporting a point prediction for every input by construction.

## Concerns I would raise in review

### 1. Empirical breadth has improved, but it is still not an industrial discovery dataset

The repository now contains two independent public field-data cases: the hop fungicide-timing trial
and a multi-environment southern corn leaf blight phenotyping dataset. That removes the earlier
single-dataset weakness and makes it harder to dismiss the empirical layer as one carefully chosen
example.

It does **not** turn the later synthetic layers into empirical industry evidence. The Bipolaris case
is host-resistance phenotyping rather than a second fungicide intervention trial, and neither public
case links historical lab, glasshouse and field observations from a discovery programme.

**What I would want next:** real linked discovery-stage evidence across assay fidelities, preferably
with programme decisions and experimental costs recorded prospectively.

### 2. The Bipolaris model-selection set is small and should now be treated as exhausted

Six field environments are enough to demonstrate why random-row validation would be misleading, but
not enough to support indefinite candidate search. The repository has already used these environments
to compare the baseline and one richer preregistered candidate.

Repeatedly inventing new features after seeing the same six fold-level results would turn those
environments into an adaptive model-selection set and weaken the prospective claim.

**Acceptable answer:** stop candidate search on the current six environments. Reopen only with new
independent environments, prospectively available field covariates, an untouched external dataset,
or a genuinely new estimand defined before modelling.

### 3. Four usable years are not enough to learn a general environment-response surface

After the source-defined 2019 exclusion, the hop trial gives four usable years. That makes strong
claims about year-level weather response or product × environment interaction poorly identified.
The repository recognises this, which is why the failed G×E promotion gate is appropriate.

The second empirical case supplies multiple field environments but a different scientific endpoint
and experimental structure. It should not be used to pretend that the hop intervention model has
suddenly acquired independent site-season replication.

**What I would want next:** multiple intervention trials across sites and seasons with field-proximal
weather, phenology, initial disease pressure, application conditions and protocol metadata.

### 4. The source-aligned re-analysis is not the published mixed model

The Python fixed-effect approximation is useful for transparency but is not equivalent to the
source SAS GLIMMIX model with random effects and Kenward–Roger degrees of freedom.

**Acceptable answer:** the repository says this explicitly and does not claim numerical replication.
For a formal reproduction study, I would require a statistically equivalent mixed-model
implementation or comparison against the published software.

### 5. The untreated sentinel is informative but not fully prospective

Same-year untreated disease pressure helps leave-one-year-out prediction, but it is only available
after the new season has started. It is an in-season state measurement, not a pre-season predictor.

**Implication:** it can support adaptive decisions within a season, but not every early discovery or
planning decision.

### 6. Promotion rules are project-level decision contracts, not external confirmatory standards

The project now demonstrates a valuable discipline: define a promotion rule before opening a richer
candidate result and keep the rejection when the rule is not met. That is much stronger than
post-hoc thresholding.

The rule itself, however, was not externally preregistered before the wider project existed and has
not been validated as a Crop Protection industry standard.

**Implication:** treat the rule as a transparent internal scientific decision contract, not as
confirmatory regulatory or biological evidence.

### 7. The applicability-domain metric is deliberately simple

Mean k-nearest-neighbour distance in standardised feature space is interpretable, but a real Crop
Protection applicability domain would need chemistry, formulation, crop, target organism, protocol,
geography, season and perhaps mechanistic constraints. Euclidean-style tabular distance is not a
substitute for domain knowledge.

Split-conformal calibration also does not magically retain distribution-free coverage under
arbitrary covariate shift. The distance-aware stress result is an empirical control in the defined
stress experiment, not a formal guarantee under all deployment shifts.

### 8. The multi-objective safety/environment variables are abstract

The Bayesian-optimisation layer is useful methodologically, but crop injury and environmental burden
are controlled response surfaces. They are not toxicology, environmental fate or regulatory risk
models.

**What I would want next:** domain-specific endpoints, constraints and measurement error models
defined with subject-matter experts.

### 9. Experimental economics are illustrative

The portfolio and multi-fidelity costs are relative simulation units. They show how to formulate a
resource-allocation problem but are not estimates of real programme economics.

### 10. Reproducibility is good but not environment-locked

The project supplies Poetry dependency ranges, tests, CI, persisted results and artifact hashes.
The v1.0 release also records the exact direct package versions used for validation. It still does
not provide a complete transitive lockfile generated from an external package index.

That limitation should remain explicit.

## Questions I would ask the author

1. What is the experimental unit in the hop field trial, and why does it matter for uncertainty?
2. Why is leave-one-year-out validation harder than random folds here?
3. Why did coarse weather hurt transportability, and what measurements would you request instead?
4. What does the Bipolaris case add that the hop trial could not, and what does it still not add?
5. When does AUDPC hide scientifically relevant disease-progress information?
6. Why was the planting-window candidate rejected despite better pooled error?
7. Why should new Bipolaris candidate search stop on the current six environments?
8. Why can uncertainty sampling allocate experiments inefficiently for a portfolio decision?
9. How would you validate a lab or glasshouse surrogate before it influences field progression?
10. What parts of the model-risk layer would have to be co-designed with crop scientists?
11. Which result in the repository would you **not** generalise beyond the current data, and why?

## Bottom line

The repository is persuasive if it is presented as:

> a demonstration of rigorous quantitative collaboration with experimental scientists.

It becomes less persuasive if it is presented as:

> proof that the author already knows Crop Protection biology or that the simulated percentage gains
> will reproduce in a proprietary R&D pipeline.

The recent Bipolaris work strengthens the first claim because it now combines prospective
environment-level validation, a frozen promotion rule, a retained negative result and an explicit
model-selection stop boundary. It does not change the second boundary.
