# Evidence map

This file separates empirical evidence from controlled demonstrations. Numerical results from a
controlled DGP should never be presented as estimates of real Crop Protection performance.

| Layer | Evidence status | Main question | Primary analysis | Key persisted evidence | Main limitation |
| --- | --- | --- | --- | --- | --- |
| Multi-site dose response | Controlled synthetic | Can dose response and site shift be audited against known truth? | `01_predictive_science_demo.ipynb` | `results/summary.json` | Synthetic environmental structure |
| Fungicide field trial | **Public real data** | What does the experimental design support, and how does validation change for a new year? | `02_real_fungicide_field_trial.ipynb` | `results/real_hop_trial/summary.json` | One intervention experiment; four usable years after source exclusion |
| Southern corn leaf blight phenotyping | **Independent public real data** | How well do hybrid burden and disease-curve shape transport to unseen field environments, and does a pre-known planting-window label improve that transport? | `crop-protection-bipolaris` | `results/bipolaris/summary.json`, `functional_eligibility.csv` | Host-resistance phenotyping, not a fungicide intervention trial; only six field environments |
| Hop powdery-mildew schedule validation | **Independent public real data** | How does the risk-index spray schedule compare with 10-, 14- and 21-day intervals within field blocks and site-years? | `src/crop_protection_ps/hop_powdery_field.py` | `results/real_hop_powdery_mildew/field_interval/summary.json`, `environment_contrasts.csv` | No untreated arm or spray-count/cost outcomes; site-year differences descriptive; original CSV retained upstream |
| Hop cone disease and quality | **Public real data, distinct late-season experiment in third study** | Does extending the final fungicide schedule coincide with cone disease and chemistry changes within the same trial block? | `src/crop_protection_ps/hop_cone_quality.py` | `results/real_hop_powdery_mildew/late_season/summary.json`, `year_comparisons.csv`, `block_influence.csv` | 2021 cone mildew absent, 2018–19 incomplete, one extreme alpha-acid observation, same farm reused across years |
| Hop cone infection missingness sensitivity | **Partial-identification audit of the same real experiment** | What field-block disease differences remain identifiable if every unscored plant could have zero to ten infected cones? | `src/crop_protection_ps/hop_cone_bounds.py` | `results/real_hop_powdery_mildew/late_season/bounds/summary.json`, `paired_bounds.csv`, `year_bounds.csv` | Identified intervals are not confidence intervals; no 2021 disease data; no untreated control or treatment recommendation |
| Potato late-blight trial deposit | **New independent candidate source; intake only** | How many exact source records, geocoded site-years, trial codes and provisional plot identities can be distinguished without overcounting 2016 repetitions? | `src/crop_protection_ps/potato_source_audit.py` | `results/real_potato_late_blight/source_audit/summary.json`, `years.csv`, `site_years.csv`, `trial_aliases.csv`, `conflicting_events.csv` | 127,034 original rows include 118,021 exact-repeat excess; title's 18 trials do not map directly to 34 source trial-code cells; no validated endpoint/plot dictionary or causal inference |
| Potato binary/text source-parity audit | **Same fourth candidate source; still protocol-gated** | Does the original R workspace add outcomes, IDs or resolved records absent from TSV? | `src/crop_protection_ps/potato_binary_parity.py` | `results/real_potato_late_blight/binary_parity.json` | All 1,270,340 ordered cells match; unused R factor labels do not identify experiments; 0.1° geocodes are not unique trial IDs |
| Bayesian hierarchy | Real-data-derived | Does partial pooling stabilise inference and predictive uncertainty? | `03_bayesian_hierarchical_field_trial.ipynb` | `results/real_hop_trial/bayesian/summary.json` | Gaussian transformed-response hierarchy; limited years |
| Environment transportability | Real field data + public weather | Which environment information transports to a held-out season? | `04_environment_transportability.ipynb` | `results/real_hop_trial/environment/summary.json` | Coarse city weather; sentinel is in-season, not fully prospective |
| Adaptive replication | Real-data-derived decision simulation | Which additional paired block reduces decision uncertainty most? | `05_adaptive_experimental_design.ipynb` | `results/real_hop_trial/adaptive_design/summary.json` | No prospective follow-up experiment was actually run |
| Multi-fidelity progression | Controlled synthetic | Can validated lab/glasshouse evidence reduce field-selection regret? | `06_multifidelity_candidate_progression.ipynb` | `results/multifidelity/summary.json` | Cross-fidelity relationships are simulated |
| Portfolio VOI | Controlled synthetic | Where should finite follow-up budget be spent before constrained advancement? | `07_portfolio_decision.ipynb` | `results/portfolio_decision/summary.json` | Rewards, costs and thresholds are simulation parameters |
| Multi-objective BO | Controlled synthetic | How should efficacy and environmental burden be searched under a crop-safety constraint? | `08_multiobjective_bayesian_optimisation.ipynb` | `results/multiobjective_bo/summary.json` | Abstract design variables and synthetic response surfaces |
| Applicability domain | Controlled synthetic | When should uncertainty be widened or a prediction withheld under shift? | `09_applicability_domain_model_risk.ipynb` | `results/model_risk/summary.json` | kNN support distance is a heuristic, not a scientific-domain guarantee |
| Transport-reaction forward verification | Controlled synthetic | Can a diffusion-decay forward model be verified against conservation laws and analytic truth? | `src/crop_protection_ps/transport_reaction.py` | `tests/test_transport_reaction.py`, `docs/transport_reaction_verification.md` | Synthetic methods evidence only; no real transport parameters |
| Transport-reaction inverse calibration | Controlled synthetic | Can known diffusion and decay parameters be recovered, unidentifiable designs detected, and predictions checked on disjoint held-out observations? | `src/crop_protection_ps/transport_reaction_inverse.py` | `tests/test_transport_reaction_inverse.py`, `docs/transport_reaction_inverse.md` | Local identifiability remains design dependent; held-out intervals separate noise-only and first-order parameter uncertainty, neither covers structural discrepancy |
| Transport-reaction profile likelihood | Controlled synthetic | Do likelihood profiles support finite parameter intervals, or does nuisance compensation reveal weak identification? | `src/crop_protection_ps/transport_reaction_profile.py` | `tests/test_transport_reaction_profile.py`, `docs/transport_reaction_profile_likelihood.md` | Profile intervals are practical-identifiability evidence, not proof of global structural identifiability |
| Transport-reaction observation design | Controlled synthetic | Can a fixed observation budget be placed in space and time to improve local separation of diffusion and decay? | `src/crop_protection_ps/transport_reaction_design.py` | `tests/test_transport_reaction_design.py`, `docs/transport_reaction_observation_design.md` | Fisher-information optimality is local to the declared nominal parameter point and noise model |
| Robust transport observation design | Controlled synthetic | Does an observation design remain informative across a declared set of plausible diffusion/decay scenarios? | `src/crop_protection_ps/transport_reaction_robust_design.py` | `tests/test_transport_reaction_robust_design.py`, `docs/transport_reaction_robust_observation_design.md` | Finite-scenario robustness is not continuous minimax optimality or a probabilistic prior average |
| Robust transport design selection | Controlled synthetic | Which equal-budget candidate design should be selected under a hard full-rank robustness gate and worst-case information criterion? | `src/crop_protection_ps/transport_reaction_design_selection.py` | `tests/test_transport_reaction_design_selection.py`, `docs/transport_reaction_design_selection.md` | Optimal only within the declared finite candidate set |
| Sequential robust transport design | Controlled synthetic | Given a seed design, where should the next observation be added to maximise worst-case information over the declared scenarios? | `src/crop_protection_ps/transport_reaction_sequential_design.py` | `tests/test_transport_reaction_sequential_design.py`, `docs/transport_reaction_sequential_design.md` | Greedy finite-pool augmentation is not globally optimal fixed-budget design |
| Exact finite-pool transport design benchmark | Controlled synthetic | How far is greedy sequential design from the exact best subset in a tractable declared candidate pool? | `src/crop_protection_ps/transport_reaction_exact_design.py` | `tests/test_transport_reaction_exact_design.py`, `docs/transport_reaction_exact_design_benchmark.md` | Exact only within the declared finite pool, budget and scenario set |
| Persisted transport-design evidence bundle | Controlled synthetic | Can the complete design decision chain be regenerated as one auditable artifact? | `crop-protection-transport-design` | `results/transport_design/summary.json`, `tests/test_scientific_contract.py` | Synthetic known-truth bundle; regenerated values are not empirical crop-protection quantities |

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

The exact upstream CSV is vendored at `data/raw/maize_bipolaris.csv`. Its acquisition contract pins
the upstream Git commit, path, byte length and Git blob identity. Normal reproduction is therefore
offline; commit-pinned download remains only an explicit recovery path. See
[`second_empirical_case_bipolaris.md`](second_empirical_case_bipolaris.md).

### Hop powdery-mildew fungicide-schedule field validation

The third empirical case uses the independently published Gent, Richardson & Massie (2025),
*A Modified Disease Risk Index for Hop Powdery Mildew*,
[10.1094/PHYTOFR-10-24-0117-R](https://doi.org/10.1094/PHYTOFR-10-24-0117-R).
The publisher makes the article available as CC0. The original CSV and SAS files are maintained
in the authors' public GitHub repository, which has no separate data-license declaration; the
original CSV is not vendored here. The source identity, 12,880 records, eight site-year
environments, 165 block-matched contrasts and one erroneous plant identifier are documented in
[`real_case_hop_powdery_mildew_interval.md`](real_case_hop_powdery_mildew_interval.md).
The independent experiment broadens field-intervention evidence but does not evaluate the same
disease, treatments or estimand as the first hop downy-mildew study.

The same third publication reports a **separate late-season fungicide-ending
experiment**, observed through `Cascade.csv` (2018–2022 cone quality) and
`Mildew.csv` (2018, 2019, 2020, 2022 cone disease). The sources can be paired
only at year–block–treatment level. The 2021 absence is explicitly recorded;
all five quality metrics receive a systematic leave-one-block diagnostic.
See [`real_case_hop_cone_quality.md`](real_case_hop_cone_quality.md) for data
identity, exact matching, incomplete plots and the source-provided alpha-acid
extreme.

The follow-up [worst-case disease-outcome bounds](real_case_hop_cone_bounds.md)
preserve all 84 source-covered disease contrasts. Among these, 65 are
point-identified and 19 are partially identified because of unscored plants;
2021 remains missing at the source. The 2018–2019 annual ranges all cross
zero under unrestricted missingness. This corrects potential overinterpretation
of observed zero infections without adding inferential or causal claims.

### Potato late-blight data (candidate case, not validated modelling evidence)

The Holst & Donner (2022) Zenodo deposit
[10.5281/zenodo.6352735](https://doi.org/10.5281/zenodo.6352735)
describes 18 Corteva potato late-blight fungicide trials in the UK and Ireland
from 2013 to 2017. The original TSV is not redistributed. A reproducible
checksum-pinned [source-identity audit](real_case_potato_source_audit.md) and
offline derived evidence record 9,013 distinct full-row signatures among
127,034 rows, 18 candidate site-years, 34 source trial-code cells, 602
provisional plot keys and 23 event keys with multiple numeric responses.
These candidate identifiers are **not verified experimental units**. A source
protocol, treatment dictionary, endpoint identity and duplication explanation
are required before any treatment-effect or predictive-model claim.

The [RData/TSV parity audit](real_case_potato_binary_parity.md) checks the
binary's published MD5, its independent SHA-256 pin and its sole `obs` data
frame against all 127,034 text rows. The 1,270,340 exact cell matches show
that the exceptional 2016 row repetition occurs in both formats. The source
publisher's IPM Decisions report documents 0.1° geolocation precision, so
even an apparent 18-site-year count does not uniquely identify 18 independent
trials. Six original-protocol evidence questions remain unresolved.

## Real-data claims that can be made

For the hop experiment, the repository supports statements such as:

- the source-defined primary dataset contains 227 observed rows after exclusion and missingness;
- there are 92 matched Early/Late timing comparisons within year, block and product;
- the aggregate Late-minus-Early AUDPC contrast is 40.93 with a year-block cluster-bootstrap 95%
  interval [15.54, 67.21];
- a random-fold prediction benchmark performs much better than leave-one-year-out prediction;
- same-year untreated disease pressure is materially more predictive of a held-out season than the
  coarse monthly weather representation used here.

For the southern corn leaf blight dataset, the repository supports a more explicitly prospective
set of claims:

- disease progress is observed repeatedly for maize hybrids across six field environments;
- per-curve AUDPC, final severity, maximum severity and interpolated t50 are computed under a fixed
  analysis window;
- normalized disease-curve shape is compared only for curves that satisfy the pre-specified
  functional-profile eligibility rules, with every inclusion and exclusion persisted in
  `functional_eligibility.csv`;
- leave-one-environment-out validation compares global training history with same-hybrid history
  without using held-out outcomes to construct predictions;
- a planting-window candidate using only the pre-known `Cedo`/`Preferencial` label improves pooled
  burden RMSE and weighted shape RMSE, but is rejected under the promotion rules frozen before
  evaluation because it wins only three of six held-out environments on each endpoint;
- that rejection is retained rather than changing the model or success threshold after inspection.

These statements concern the specific public datasets. They are not general pesticide-use,
resistance-management, planting-date or cultivar recommendations.

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
