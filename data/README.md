# Data

## Synthetic demonstration

`processed/synthetic_field_trials.csv` is generated from an explicit, seeded data-generating
process. It is **not proprietary company data** and is not intended to reproduce any proprietary trial.

## Real hop fungicide trial

`raw/richardson_gent_hop_downy_mildew.csv` is a line-ending-normalised copy of the public data set
released with:

Richardson, B. J. & Gent, D. H. (2024), *Suppression of Hop Downy Mildew as Influenced by the
Timing of Selected Fungicides*, Plant Health Progress 25(3):324–326,
DOI `10.1094/PHP-10-23-0086-BR`.

Source repository:
https://github.com/DavidGent-Lab/Richardon-and-Gent-2024-Plant-Health-Progress

The source file has 290 rows from 2017–2021 and three missing AUDPC observations. The original
study excluded 2019 because flooding confounded disease measurements. The raw 2019 rows remain in
this repository; the exclusion is applied only in the primary-analysis function.

Generated real-data outputs are written to:

- `processed/hop_trial_primary.csv`;
- `../results/real_hop_trial/`.

The raw-file SHA-256 is persisted in `results/real_hop_trial/summary.json`.

## Corvallis environment covariates

`raw/corvallis_monthly_weather_2009_2025.csv` contains public February-May monthly weather
summaries for Corvallis, Oregon from 2009-2025. It is used only as a **coarse external
environment representation** for the v0.4.0 transportability experiment. The exact source pages,
retrieval date and limitations are recorded in
`raw/corvallis_monthly_weather_2009_2025.provenance.json`.

The field paper states that the experiments were conducted in an experimental hop yard near
Corvallis. The weather file is not claimed to be the exact plot microclimate. Monthly values are
therefore used to test whether a cheap external proxy can improve unseen-year prediction, not to
make a causal weather-effect claim.

The 2009-2016 rows define the fixed pre-trial climatological reference. Trial outcomes are not used
to construct the weather anomaly features.

## Optional Fundecitrus extension

`src/crop_protection_ps/real_data.py` retains a schema-inspection contract for Fundecitrus citrus
Crop Protection workbooks. Those workbooks require source-side access/download steps and are not
needed to reproduce v0.2.0.
