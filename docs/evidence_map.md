# Evidence map

This file separates empirical evidence from controlled demonstrations. Numerical results from a
controlled DGP should never be presented as estimates of real Crop Protection performance.

| Layer | Evidence status | Main question | Primary analysis | Key persisted evidence | Main limitation |
| --- | --- | --- | --- | --- | --- |
| Multi-site dose response | Controlled synthetic | Can dose response and site shift be audited against known truth? | `01_predictive_science_demo.ipynb` | `results/summary.json` | Synthetic environmental structure |
| Fungicide field trial | **Public real data** | What does the experimental design support, and how does validation change for a new year? | `02_real_fungicide_field_trial.ipynb` | `results/real_hop_trial/summary.json` | One intervention experiment; four usable years after source exclusion |
| Southern corn leaf blight phenotyping | **Independent public real data** | How stable are hybrid disease-burden rankings across field environments, and what can scalar curve summaries hide? | `crop-protection-bipolaris` | `results/bipolaris/summary.json` | Host-resistance phenotyping, not a fungicide intervention trial; scalar baseline only |
| Bayesian hierarchy | Real-data-derived | Does partial pooling stabilise inference and predictive uncertainty? | `03_bayesian_hierarchical_field_trial.ipynb` | `results/real_hop_trial/bayesian/summary.json` | Gaussian transformed-response hierarchy; limited years |
| Environment transportability | Real field data + public weather | Which environment information transports to a held-out season? | `04_environment_transportability.ipynb` | `results/real_hop_trial/environment/summary.json` | Coarse city weather; sentinel is in-season, not fully prospective |
| Adaptive replication | Real-data-derived decision simulation | Which additional paired block reduces decision uncertainty most? | `05_adaptive_experimental_design.ipynb` | `results/real_hop_trial/adaptive_design/summary.json` | No prospective follow-up experiment was actually run |
| Multi-fidelity progression | Controlled synthetic | Can validated lab/glasshouse evidence reduce field-selection regret? | `06_multifidelity_candidate_progression.ipynb` | `results/multifidelity/summary.json` | Cross-fidelity relationships are simulated |
| Portfolio VOI | Controlled synthetic | Where should finite follow-up budget be spent before constrained advancement? | `07_portfolio_decision.ipynb` | `results/portfolio_decision/summary.json` | Rewards, costs and thresholds are simulation parameters |
| Multi-objective BO | Controlled synthetic | How should efficacy and environmental burden be searched under a crop-safety constraint? | `08_multiobjective_bayesian_optimisation.ipynb` | `results/multiobjective_bo/summary.json` | Abstract design variables and synthetic response surfaces |
| Applicability domain | Controlled synthetic | When should uncertainty be widened or a prediction withheld under shift? | `09_applicability_domain_model_risk.ipynb` | `results/model_risk/summary.json` | kNN support distance is a heuristic, not a scientific-domain guarantee |

## Real-data provenance

### Hop fungicide-timing experiment

The first empirical case uses the public data accompanying:

> Richardson, B. J. & Gent, D. H. (2024). *Suppression of Hop Downy Mildew as Influenced by the
> Timing of Selected Fungicides*. Plant Health Progress, 25(3), 324–326.

The raw CSV is stored at `data/raw/richardson_gent_hop_downy_mildew.csv`. Its provenance record and
SHA-256 hash are stored in `data/raw/richardson_gent_hop_downy_mildew.provenance.json`.

The source investigators state that 2019 was not used because flooding caused uneven spring growth
and confounded disease measurements. The raw rows are retained locally and the exclusion is applied
explicitly in the primary analysis.

### Southern corn leaf blight disease-progress data

The second empirical case uses the public `maize_bipolaris.csv` dataset accompanying:

> Del Ponte, E. M. (2026). *From Scalar Summaries to Functional Comparisons: A Framework for
> Analyzing Plant Disease Progress Curves*. DOI `10.1094/PHYTO-01-26-0009-LE`.

The source repository is `https://github.com/emdelponte/paper-hgam-curves`. The repository does not
vendor the CSV. Instead, the acquisition contract pins the exact upstream Git commit, path, byte
length and Git blob identity before analysis. See
[`second_empirical_case_bipolaris.md`](second_empirical_case_bipolaris.md).

## Real-data claims that can be made

For the hop experiment, the repository supports statements such as:

- the source-defined primary dataset contains 227 observed rows after exclusion and missingness;
- there are 92 matched Early/Late timing comparisons within year, block and product;
- the aggregate Late-minus-Early AUDPC contrast is 40.93 with a year-block cluster-bootstrap 95%
  interval [15.54, 67.21];
- a random-fold prediction benchmark performs much better than leave-one-year-out prediction;
- same-year untreated disease pressure is materially more predictive of a held-out season than the
  coarse monthly weather representation used here.

For the southern corn leaf blight dataset, the empirical claims are deliberately descriptive:

- disease progress is observed repeatedly for maize hybrids across multiple field environments;
- per-curve AUDPC, final severity, maximum severity and interpolated t50 can be compared across those
  environments under a fixed analysis window;
- pairwise Spearman correlations quantify how stable hybrid AUDPC rankings are across environments;
- scalar agreement does not establish that disease-curve shape is equivalent, which is why this
  analysis is treated as a baseline rather than the final model.

These statements concern the specific public datasets. They are not general pesticide-use,
resistance-management or cultivar recommendations.

## Controlled claims that can be made

The later simulations support methodological statements such as:

- a validated lower-fidelity surrogate can improve selection under a fixed synthetic cost model;
- decision-aware information allocation can outperform raw uncertainty sampling under a controlled
  portfolio objective;
- constrained multi-objective acquisition can recover more of a synthetic feasible Pareto frontier;
- a support-aware abstention rule can reduce error under a deliberately constructed distribution
  shift.

They do **not** support claims that the same percentage gains would occur in a real company,
chemical series, crop, pathogen, formulation programme or regulatory setting.
