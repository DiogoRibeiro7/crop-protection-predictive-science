# Protocol evidence requests for external source studies

These questions are **not** a grant to fit treatment, temperature or causal models.
The 19 gated source-table questions require 59 prerequisite entries, condensed here into 35 distinct requests.
An archived README phrase provides context only; it never clears a gate.

## aphid_cohort: binomial_temperature_interaction

### batch_and_replicate_identity

- **Question:** Can each TOTAL/DEAD row be assigned to a unique batch, chamber, container and biological replicate?
- **Evidence requested:** Run-level replicate keys and physical batch/chamber logs.
- **Existing original-source context only:** [aphid_controlled_conditions](../../data/external/zenodo_aphid_pesticide_19805135/README.txt#L4) (line 4).

### clustering_and_overdispersion_plan

- **Question:** How should shared exposure chambers, batches and overdispersion be represented in inference across experiments 1–4?
- **Evidence requested:** Investigator-supported dependence structure and prespecified statistical analysis plan.
- **Original-source context:** No curated local README anchor; the full protocol may still contain this information.

### randomized_exposure_unit

- **Question:** Was temperature and pesticide randomized at the aphid, container, chamber or run level in experiments 1–4?
- **Evidence requested:** Original allocation schedule and physical exposure-unit definitions.
- **Existing original-source context only:** [aphid_controlled_conditions](../../data/external/zenodo_aphid_pesticide_19805135/README.txt#L4) (line 4).

## aphid_field: field_treatment_effect

### experimental_plot_identity

- **Question:** Does the Replicate field identify an independent randomized plot, and is its meaning stable across both sampling days and sites?
- **Evidence requested:** Plot map, stable plot ID and replicate/block definitions.
- **Existing original-source context only:** [aphid_field_replicate](../../data/external/zenodo_aphid_pesticide_19805135/README.txt#L63) (line 63).

### field_date_reconciliation

- **Question:** What actual calendar dates and treatment dates do the source Excel date serials represent at each site?
- **Evidence requested:** Date-system declaration, sampling calendar and treatment logs.
- **Existing original-source context only:** [aphid_field_date](../../data/external/zenodo_aphid_pesticide_19805135/README.txt#L65) (line 65).

### repeated_measure_analysis_plan

- **Question:** Which day-3 and day-7 measurements share the same plot and how should rate denominators and correlation be modelled?
- **Evidence requested:** Plot-level longitudinal identifier, mortality-rate definition and dependence plan.
- **Existing original-source context only:** [aphid_field_replicate](../../data/external/zenodo_aphid_pesticide_19805135/README.txt#L63) (line 63), [aphid_field_mortality](../../data/external/zenodo_aphid_pesticide_19805135/README.txt#L72) (line 72).

### treatment_allocation_protocol

- **Question:** How were treatment groups A, B and C allocated within each site, replicate and environmental condition?
- **Evidence requested:** Randomization and treatment-timing protocol with field plot assignments.
- **Existing original-source context only:** [aphid_field_treatment](../../data/external/zenodo_aphid_pesticide_19805135/README.txt#L62) (line 62), [aphid_field_replicate](../../data/external/zenodo_aphid_pesticide_19805135/README.txt#L63) (line 63).

## dryad_binomial_lab: temperature_response_model

### run_and_chamber_allocation

- **Question:** Which germination or conjugation runs shared incubators, chambers and randomized temperature assignments?
- **Evidence requested:** Run-to-incubator allocation and experiment-specific randomization schedule.
- **Existing original-source context only:** [dryad_lab_germination](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L51) (line 51).

### temperature_replicate_independence

- **Question:** Which counted spores are technical subsamples versus distinct independently exposed biological replicates?
- **Evidence requested:** Source biological-replicate hierarchy and exposure-unit design.
- **Original-source context:** No curated local README anchor; the full protocol may still contain this information.

### within_run_clustering_plan

- **Question:** Which counts are nested in common temperature runs, and what within-run dependence should a response model allow?
- **Evidence requested:** Chamber/run grouping keys and modelling or dispersion protocol.
- **Original-source context:** No curated local README anchor; the full protocol may still contain this information.

## dryad_field: longitudinal_disease_model

### date_alignment

- **Question:** What is the actual plant scoring schedule, including missed visits or delayed measurements, beyond the matching calendar headers?
- **Evidence requested:** Original field visit logs and plant observation dates.
- **Existing original-source context only:** [dryad_field_dates](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L89) (line 89).

### death_and_censoring_handling

- **Question:** Is recorded X a terminal death state and how are blank visits, missed visits and postreproductive plants handled?
- **Evidence requested:** Field observation and mortality/censoring rules.
- **Existing original-source context only:** [dryad_field_codes](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L115) (line 115).

### state_transition_codebook

- **Question:** How should mixed or undocumented source status labels be interpreted, and which transitions between V, D, PD, LD, X and other labels are biologically admissible?
- **Evidence requested:** Complete field status/transition codebook, including mixed labels.
- **Existing original-source context only:** [dryad_field_plant](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L113) (line 113), [dryad_field_codes](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L115) (line 115), [dryad_flower_status](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L117) (line 117).

## dryad_field: temperature_causal_effect

### causal_identification_design

- **Question:** What intervention or quasi-experiment would identify a causal temperature effect rather than seasonal correlation?
- **Evidence requested:** Investigator-supported estimand, identification assumptions and sensitivity plan.
- **Original-source context:** No curated local README anchor; the full protocol may still contain this information.

### confounder_measurement

- **Question:** Which site, plant, seasonal and management variables affected both measured field temperature and disease expression?
- **Evidence requested:** Causal covariate map and measured confounder sources.
- **Existing original-source context only:** [dryad_field_dates](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L89) (line 89), [dryad_station](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L107) (line 107).

### weather_quality_resolution

- **Question:** Can the missing 30 August low and reversed 31 August high/low source values be independently verified or explicitly excluded under a prespecified rule?
- **Evidence requested:** Original station records and an investigator-approved quality rule.
- **Existing original-source context only:** [dryad_station](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L107) (line 107).

## dryad_greenhouse_death: plant_death_risk_model

### at_risk_plant_denominators

- **Question:** How many live and at-risk plants were followed in every death-case cell, including those that never died?
- **Evidence requested:** Complete initial plant registry and risk-set counts by treatment/time.
- **Existing original-source context only:** [dryad_greenhouse_deaths](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L85) (line 85).

### event_time_and_censoring_definition

- **Question:** On which date did each plant die or leave observation, and how were survivors and censoring defined?
- **Evidence requested:** Plant-level event chronology and censoring protocol.
- **Existing original-source context only:** [dryad_greenhouse_deaths](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L85) (line 85).

### unique_plant_linkage

- **Question:** Is there a validated unique plant key connecting the greenhouse infection and death records without ambiguous many-to-many joins?
- **Evidence requested:** Author-supplied unique cross-workbook identifiers or linkage codebook.
- **Existing original-source context only:** [dryad_greenhouse_deaths](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L85) (line 85).

## dryad_greenhouse_infection: disease_risk_model

### disease_status_codebook

- **Question:** What exactly do the greenhouse disease/healthy codes mean, including unscored, sterile and uncertain cases?
- **Evidence requested:** Experiment-2-specific scoring codebook and exclusions.
- **Existing original-source context only:** [dryad_greenhouse_temperatures](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L63) (line 63).

### family_and_replicate_clustering

- **Question:** Which greenhouse plants share seed families, inoculum batches, chamber exposure and biological replicates?
- **Evidence requested:** Family, batch, chamber and replicate assignments.
- **Original-source context:** No curated local README anchor; the full protocol may still contain this information.

### plant_level_independence_or_identity

- **Question:** Do the 1,112 scored rows identify distinct plants, or do some rows repeatedly score the same plant?
- **Evidence requested:** Unique plant keys and observation/replicate linkage.
- **Existing original-source context only:** [dryad_greenhouse_temperatures](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L63) (line 63).

## dryad_growth: temperature_response_model

### nested_replicate_structure

- **Question:** What is the true biological unit behind strain, mating-type, run and picture labels, including repeated picture IDs?
- **Evidence requested:** Biological replicate and picture-to-culture mapping.
- **Existing original-source context only:** [dryad_lab_growth](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L55) (line 55).

### run_and_chamber_allocation

- **Question:** Which colonies of strains 2–4 were exposed together, and how were temperatures assigned to independent chambers or runs?
- **Evidence requested:** Temperature allocation schedule, run log and chamber identities.
- **Existing original-source context only:** [dryad_lab_growth](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L55) (line 55).

### strain_and_mating_type_plan

- **Question:** Were strain and mating-type comparisons prespecified and independently replicated across temperatures?
- **Evidence requested:** Factorial allocation, strain/mating-type protocol and statistical plan.
- **Existing original-source context only:** [dryad_lab_growth](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L55) (line 55).

## dryad_summary: weather_association_model

### aggregation_and_denominator_definitions

- **Question:** How were visit-level flower and plant totals aggregated and which denominator and risk set are valid for each endpoint?
- **Evidence requested:** Source aggregation code and endpoint/denominator specification.
- **Existing original-source context only:** [dryad_field_plant](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L113) (line 113), [dryad_flower_status](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L117) (line 117).

### field_date_alignment

- **Question:** How exactly were visit dates, flower sampling and any prior-day weather windows joined?
- **Evidence requested:** Original date-join logic and field sampling schedule.
- **Existing original-source context only:** [dryad_field_dates](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L89) (line 89), [dryad_station](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L107) (line 107).

### weather_quality_resolution

- **Question:** How were moving temperature windows constructed from station dates containing the two flagged 30–31 August anomalies?
- **Evidence requested:** Original weather preprocessing, missing-data rules and window definitions.
- **Existing original-source context only:** [dryad_station](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L107) (line 107).

## dryad_weather: weather_exposure_model

### resolve_low_above_high

- **Question:** Which, if either, of the recorded 31 August 2021 High=85.00 and Low=90.00 values is incorrect?
- **Evidence requested:** Unmodified source-station archive and documented correction decision.
- **Existing original-source context only:** [dryad_station](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L107) (line 107).

### resolve_missing_temperature

- **Question:** What is the verified Beltsville station low temperature for 30 August 2021, or the defensible rule if it is irrecoverable?
- **Evidence requested:** Original station log, station ID, units and correction or missingness policy.
- **Existing original-source context only:** [dryad_station](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L107) (line 107).

### site_and_date_alignment

- **Question:** Which plant sites and time zones are represented by the Beltsville station, and how should daily readings map to individual exposure intervals?
- **Evidence requested:** Site–station geolocation, observing-window definitions and exposure validation.
- **Existing original-source context only:** [dryad_station](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L107) (line 107), [dryad_field_dates](../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L89) (line 89).

## wheat_field: trial_level_treatment_effect

### endpoint_protocol

- **Question:** How and when were disease incidence, severity and yield recorded, and which endpoint observations repeat the same experimental plot?
- **Evidence requested:** Endpoint scoring protocol, observation schedule and repeated-measure definitions.
- **Original-source context:** No curated local README anchor; the full protocol may still contain this information.

### plot_replicate_identity

- **Question:** Which original plot, block and replicate identifiers belong to each treatment and endpoint row?
- **Evidence requested:** Field layout, plot keys, block and replication metadata.
- **Original-source context:** No curated local README anchor; the full protocol may still contain this information.

### reconcile_56_published_trials_vs_76_trial_ids

- **Question:** What physical trial entity does each TrialId represent, and how do 76 recorded TrialIds map to the 56 trials described by the source?
- **Evidence requested:** Trial-code crosswalk and field-season-site definitions from the investigators.
- **Original-source context:** No curated local README anchor; the full protocol may still contain this information.

### treatment_dictionary

- **Question:** What are the exact treated/untreated labels, products, application timings, doses and randomization protocol?
- **Evidence requested:** Treatment allocation and intervention codebook.
- **Original-source context:** No curated local README anchor; the full protocol may still contain this information.

## Review boundary

The question list does not assert that the original authors omitted any requested details. Source papers, experimental logs and original analysis scripts may supply additional evidence, but each applicable prerequisite requires a separate scientific review and an explicit eligibility-contract revision before modelling.
