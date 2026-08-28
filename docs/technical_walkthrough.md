# Five-minute technical walkthrough

This is the shortest path through the repository. It is designed for a technical discussion, not a
complete methods review.

## 0:00–0:40 — Frame the problem

Open the repository README and start with one sentence:

> The project is about using statistical models to improve scientific R&D decisions, while making
> transportability, uncertainty and model failure explicit.

The recurring workflow is

\[
\text{experiment}
\rightarrow
\text{model}
\rightarrow
\text{deployment-style validation}
\rightarrow
\text{uncertainty}
\rightarrow
\text{next R&D decision}.
\]

Do not start by listing algorithms.

## 0:40–1:45 — Real field trial: validation must match deployment

Open:

- `notebooks/02_real_fungicide_field_trial.ipynb`
- `results/real_hop_trial/figures/year_transportability_gap.png`

The public field experiment gives 92 matched Early/Late timing contrasts after respecting the
source-defined 2019 flooding exclusion. The aggregate Late-minus-Early AUDPC contrast is **40.93**
with a year-block cluster-bootstrap 95% interval **[15.54, 67.21]**.

Then move immediately to the predictive failure:

- random five-fold RMSE: **2.72**;
- leave-one-year-out RMSE: **8.43**.

The point to make is:

> Trial year is a useful adjustment variable when the same environment is already represented, but
> it is not a deployable predictor of a future season. Random validation can therefore answer a
> materially easier question than the R&D decision.

If asked about the source paper, state explicitly that the Python source-aligned fixed-effect model
is **not** claimed to reproduce the original SAS GLIMMIX/Kenward–Roger analysis numerically.

## 1:45–2:40 — Multi-fidelity progression: a surrogate must earn promotion

Open:

- `results/multifidelity/figures/equal_budget_selection_regret.png`
- `docs/multifidelity_candidate_progression.md`

The glasshouse layer is not assumed to be useful because it is cheaper. It first has to improve
held-out prediction of field efficacy. It reduces calibration RMSE from **0.7325** to **0.4700**,
so it passes the pre-specified transfer gate.

Under the same 1,040-unit experimental budget, the full lab → glasshouse → field policy reduces
selection regret by **30.7%** relative to lab → field in the controlled DGP.

The point to make is:

> Lower-fidelity assays are useful only if their relationship to the field endpoint survives
> out-of-sample validation. Cheap measurements are not automatically informative measurements.

## 2:40–3:35 — Portfolio value of information: measure what can change the decision

Open:

- `results/portfolio_decision/figures/portfolio_regret_by_policy.png`
- `docs/portfolio_decision.md`

Every policy gets the same 24-unit follow-up budget. Uniform allocation gives mean oracle regret
**149.51**; uncertainty sampling gives **126.65**; portfolio-aware VOI gives **105.45**.

The terminal portfolio is an exact count-and-budget 0/1 knapsack. The acquisition rule asks whether
an efficacy or safety measurement can move a candidate across the current advancement boundary.

The point to make is:

> The largest statistical uncertainty need not be the most decision-relevant uncertainty. The value
> of a measurement depends on whether resolving it can change what R&D does.

## 3:35–4:35 — Model risk: know when to abstain

Open:

- `figures/model_risk/coverage_by_risk_control.png`
- `figures/model_risk/error_vs_applicability_distance.png`

A 90% interval calibrated in-domain covers only **50.6%** of the shifted stress set. Distance-aware
inflation recovers **92.9%** stress coverage, but average interval width grows to **0.83** on a
response scale roughly bounded by zero and one.

The applicability-domain policy therefore permits abstention. It rejects **98.1%** of genuinely
shifted conditions and reduces latent MAE from **0.1695** under forced prediction to **0.0502** among
accepted predictions.

The point to make is:

> A model being able to return a number is not evidence that the number lies inside validated
> scientific support. Sometimes the correct model output is a request for another experiment.

## 4:35–5:00 — Close

The four results are connected by the same principle:

\[
\boxed{
\text{prediction quality is meaningful only relative to the scientific decision and its domain}
}
\]

The rest of the repository supplies supporting depth:

- `03_bayesian_hierarchical_field_trial.ipynb`: partial pooling and posterior predictive checks;
- `04_environment_transportability.ipynb`: prospective weather versus in-season sentinel state;
- `05_adaptive_experimental_design.ipynb`: parameter information versus decision information;
- `08_multiobjective_bayesian_optimisation.ipynb`: feasible efficacy/environment trade-offs.

## Questions to welcome rather than avoid

A strong technical discussion should probe the limits of the project. Good questions include:

- Why is one public field dataset not enough to establish general Crop Protection transportability?
- Why does the untreated sentinel help while coarse weather does not?
- What would replace the synthetic lab/glasshouse transfer model with proprietary historical data?
- Why is the applicability-domain score a deployment heuristic rather than a formal guarantee?
- Which decision thresholds would have to come from scientists rather than from the modeller?

Those questions are addressed directly in `docs/principal_scientist_review.md`.
