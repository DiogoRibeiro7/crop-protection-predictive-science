# Independent field validation: Hop powdery-mildew fungicide schedules

This is a **third empirical field-data case**, independent of the Richardson–Gent hop
downy-mildew timing trial and the Del Ponte maize disease-progress dataset.
It uses the original `Interval.csv` accompanying:

> Gent, D. H., Richardson, B. J. & Massie, S. T. (2025). *A Modified Disease Risk Index for
> Hop Powdery Mildew*. *PhytoFrontiers* 5(1), 30–41.
> [DOI: 10.1094/PHYTOFR-10-24-0117-R](https://doi.org/10.1094/PHYTOFR-10-24-0117-R).

The publisher labels the article CC0. The authors separately provide the data and SAS analysis code
in their [public repository](https://github.com/DavidGent-Lab/Gent-et-al-2025-A-Modified-Disease-Risk-Index-for-Hop-Powdery-Mildew-PhytoFrontiers-).
The repository itself has no separate LICENSE file, so this project does **not** redistribute its
original CSV. It does publish original, small, derived analysis tables and source provenance.

## Experimental structure

`Interval.csv` covers the foliar phase of powdery mildew in hops at two Washington locations,
Toppenish and Prosser, in 2020–2023. Four fungicide strategies are represented:

| Original `TRT` | Fungicide scheduling strategy |
| --- | --- |
| 1 | Fixed 10-day application interval |
| 2 | Fixed 14-day application interval |
| 3 | Fixed 21-day application interval |
| 4 | Weather-driven, modified risk-index schedule |

The original `REP` field is the field-block replicate (I–VII). At each assessment date, ten
`PLANT` records per plot each report the number of infected leaves among ten evaluated leaves.
Repeated visits of the same plot and the individual plants are **not additional independent
randomised treatment units**.

The source provides 12,880 substantive plant records across eight site-year environments and 46
site-specific assessment dates. The audit also preserves three source anomalies:

- One all-empty CSV record is ignored as a non-observation.
- Exactly 100 plant outcomes contain the source's literal missing marker `.`; these are **not
  disease-free observations**.
- One 2020 Prosser early visit repeats `PLANT=2` in the same plot and does not contain `PLANT=1`.
  We flag that visit as having invalid plant identifiers; no value or identifier is invented.

The unmodified source has 1,288 plot visits. End-of-season analyses use the latest assessment date
*within each site-year*, rather than mixing final dates between sites. There are 224 end-of-season
plots and 221 with all ten plant measurements. Three incomplete plots are excluded from paired
contrasts. The one source identifier collision occurs at an earlier visit and does not change the
end-of-season paired sample.

## Estimand and first descriptive results

The contrast is formed separately within each site-year and field block:

\[
\Delta_{y,s,b,k}
=\operatorname{Incidence}_{y,s,b,\text{risk index}}
-\operatorname{Incidence}_{y,s,b,k},
\qquad k\in\{10,14,21\text{ days}\}.
\]

Incidence is 100 × diseased leaves / assessed leaves, aggregated across the ten plants of a
**complete** end-of-season field plot. Negative differences favour the risk-index strategy over
that particular fixed interval on this descriptive endpoint. Across eight site-year environments,
three fixed comparators and up to seven matched blocks, there are **165 complete within-block
comparisons**, not 1,650 independent plant observations.

The heterogeneous environments are the primary scientific result. For illustration:

| Site-year | Mean end-of-season incidence across complete plots | Risk index minus 21-day interval |
| --- | ---: | ---: |
| Toppenish 2020 | 5.04% | −5.14 percentage points (7 blocks) |
| Toppenish 2022 | 20.93% | −17.00 percentage points (7 blocks) |
| Prosser 2020 | 0.00% | 0.00 percentage points (7 blocks) |
| Prosser 2023 | 0.29% | +0.14 percentage points (7 blocks) |

The remaining environment-specific contrasts, including the three 14-day comparisons with only
six complete blocks, are in
[`environment_contrasts.csv`](../results/real_hop_powdery_mildew/field_interval/environment_contrasts.csv).
The data do **not** support pooling those illustrative contrasts into a universal effectiveness
claim. Most environments have negligible observed end-of-season disease, and the source provides
no unsprayed arm, treatment-specific spray counts, product identity, application expenditure or
yield benefit. This is not a direct profitability or pesticide-reduction analysis.

This is a source-preserving, **descriptive** replication: no p-values, candidate model fitting,
post-hoc parameter search or evidence of out-of-season generalisation is claimed. The existing
Bipolaris model-promotion freeze and its six held-out environments remain unchanged.

## Reproduce from the original source

1. Download the authors' [unmodified Interval.csv](https://github.com/DavidGent-Lab/Gent-et-al-2025-A-Modified-Disease-Risk-Index-for-Hop-Powdery-Mildew-PhytoFrontiers-/raw/refs/heads/main/Interval.csv)
   into a local file, such as `downloads/Gent_2025_Interval.csv`. The original file is deliberately
   not committed here.
2. Run the analysis from the repository root:

```bash
poetry run python -m crop_protection_ps.hop_powdery_field \
  --input downloads/Gent_2025_Interval.csv \
  --output results/real_hop_powdery_mildew/field_interval
```

Input verification is mandatory in the CLI. It checks the SHA-256 of the source text after
canonical CRLF→LF newline conversion:

`55feee5674bede0357a8eb404a149f10cf3dc9db4845783f800a52315688eb3b`

The upstream Git blob identity is `f88b19a34592ab23990bae4509eacdeb2876761e`. If the source
changes, the program stops rather than silently publishing modified analyses. The normalized
checksum is pinned so Windows and POSIX checkout line endings produce the same verification.

Outputs, generated from the published original on **2026-11-09**, are:

| Output | Meaning |
| --- | --- |
| `plot_visits.csv` | All 1,288 plot visits with plant coverage and identifier integrity |
| `end_season_plots.csv` | 224 final site-year-block-treatment plots; incomplete outcomes explicitly blank |
| `paired_risk_vs_fixed.csv` | 165 risk-minus-fixed complete-block comparisons |
| `environment_quality.csv` | Eight site-year coverage and missingness reports |
| `environment_contrasts.csv` | 24 environment × comparator descriptive means and matched-block counts |
| `summary.json` | Provenance, verification identity, unit counts and scientific constraints |

Tests use deliberately constructed CSV data, so normal CI runs without downloading upstream
files or substituting synthetic records for the documented real observations.
