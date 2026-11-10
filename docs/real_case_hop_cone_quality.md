# Hop cone disease and quality: the late-season experiment

This note extends the third empirical case, Gent, Richardson & Massie (2025),
[*A Modified Disease Risk Index for Hop Powdery Mildew*](https://doi.org/10.1094/PHYTOFR-10-24-0117-R).
It does **not** combine data from the earlier Richardson–Gent hop downy-mildew experiment.
The authors published two separate late-season CSV sources and their SAS analysis code:

- [`Cascade.csv`](https://github.com/DavidGent-Lab/Gent-et-al-2025-A-Modified-Disease-Risk-Index-for-Hop-Powdery-Mildew-PhytoFrontiers-/raw/refs/heads/main/Cascade.csv): cone chemistry and quality in 2018–2022.
- [`Mildew.csv`](https://github.com/DavidGent-Lab/Gent-et-al-2025-A-Modified-Disease-Risk-Index-for-Hop-Powdery-Mildew-PhytoFrontiers-/raw/refs/heads/main/Mildew.csv): infected cones counted in 2018, 2019, 2020 and 2022.

The journal article is labelled CC0, but the public GitHub repository has no separate
data licence. We publish reproducible derived summaries, retaining the original CSVs at
their authors' source instead of redistributing them. The downstream parser insists on
the pinned source checksums shown below.

## Scientific question and experimental units

Four schedules refer to the **date of the final fungicide application**:

| Treatment | Timing |
| --- | --- |
| 1 | Cease applications at bloom (reference) |
| 2 | One additional application after bloom |
| 3 | Two additional applications after bloom |
| 4 | Three additional applications after bloom |

For each year, treatment and replicate block (I–VII), `Cascade.csv` has one plot
measurement of dry matter, alpha and beta acids (both adjusted to 8% moisture),
Hop Storage Index (HSI) and cone colour. `Mildew.csv` samples ten plants per plot,
with `PM` counting infected cones among ten assessed cones on that plant.
The **experimental unit is the year–block–treatment plot**, not a cone or plant.

Only the year, block and treatment identify matching plots across source tables.
The disease table has no `Field` column. The join is therefore valid only because
the quality source has exactly one named farm for each year (Farm1 in 2018, Farm2 in
2019, Farm3 in 2020–2022). The farm labels are retained; Farm3's three years are not
independent farms. Disease and chemistry assessment dates can differ by one day;
the actual offset is kept in `linked_plots.csv`.

## Coverage, missing data and comparability

| Original source | Raw observations | Plot-level interpretation |
| --- | ---: | --- |
| `Cascade.csv` | 140 | Five years × seven blocks × four treatments, complete quality records |
| `Mildew.csv` | 1,120 | Four years × seven blocks × four treatments × ten plants |
| `Mildew.csv` missing `PM` | 203 plant records | Literal `.` markers; 23 of 112 source plots are incomplete |
| Quality-only 2021 | 28 plots | No 2021 rows in the mildew source; **not zero infection** |

Of 112 plots with mildew source records, 89 have all ten plants observed. We do not
construct a full-plot disease incidence estimate for the remaining 23, even where some
plants show no infection. Disease comparisons require both plots to be complete.

The 105 quality contrasts use all seven field-block pairs for each of the 15
year × additional-treatment cells. Only **65** of these comparisons have a complete
paired cone-infection outcome.

The 2018 and 2019 **observed** mildew counts are all zero, but 203 plant-level
missing values across those two years prevent interpreting them as fully disease-free
trial years. In 2020 there are 503 infected cones among 2,800 evaluated cones;
in 2022 there are 12 among 2,800. Cross-year pooling would hide these substantial
differences in observed disease pressure.

## Predefined contrasts and influence analysis

The method calculates, within the same year and block,

\[
\Delta_{y,b,t}^{(m)}
= m_{y,b,t} - m_{y,b,1},
\qquad t\in\{2,3,4\},
\]

where \(m\) is either complete-plot infected-cone incidence or one of the five
quality metrics. Positive values mean a higher measured outcome after the additional
fungicide applications. A higher value is **not automatically better**: quality metrics
have different directions, units and commercial implications, and no field costs or
product prices are present.

The source contains one unusually high alpha-acid value:

- 2022, Farm3, block VII, treatment 2: **13.50%** alpha acids.
- The next largest value across all 140 original records is **9.31%**.
- With all seven blocks, the 2022 treatment-2 minus treatment-1 mean alpha-acid
  difference is **+1.2143 percentage points**.
- Leaving out the entire block VII pair changes this descriptive difference to
  **−0.0833 percentage points**.

This does **not** prove a data error, and the observation remains unchanged.
The [block influence table](../results/real_hop_powdery_mildew/late_season/block_influence.csv)
systematically repeats the leave-one-block comparison for **all five quality
metrics, years and treatment contrasts** (525 records). Metric-specific influence
maxima are reported separately, since comparing absolute changes in HSI to percentage
points of acid content is meaningless.

As a second illustration, the complete 2020 mildew comparison for one extra
application versus stopping at bloom is **−5.57 percentage points**, based on seven
block pairs. This is a within-trial descriptive difference, not evidence of efficacy
against an untreated arm or a transferable application recommendation.

No new machine-learning model, hypothesis test, predictive validation gate or
cross-study causal comparison was introduced.

A separately reproducible
[missing-disease partial-identification analysis](real_case_hop_cone_bounds.md)
now quantifies the uncertainty from the 203 unscored plant outcomes without
imputing zero infections. It preserves this analysis's complete-plot contrasts
and records wider bounds wherever source disease observations are incomplete.

## Reproducibility

Download the two original CSVs linked above. From the repository root, run:

```bash
poetry run python -m crop_protection_ps.hop_cone_quality \
  --mildew downloads/Mildew.csv \
  --cascade downloads/Cascade.csv \
  --output results/real_hop_powdery_mildew/late_season
```

The program checks SHA-256 of UTF-8 source text with CRLF normalised to LF:

| Source | Canonical SHA-256 | Upstream Git blob |
| --- | --- | --- |
| `Mildew.csv` | `2e26ce77ea392fee7e177b3b8f05a1411ebdde204af2c8d3da91758a272b5f75` | `bba8fffb6bfc77d57040ef568d50d5f4cde8e432` |
| `Cascade.csv` | `d8dbca537d19cd1c6894a442c0b7e9f1eecb74d2ee1c2ba8b0971c3892de0be4` | `aaa91ec59ec21b36d16289b79f165d51e813421b` |

Derived files:

1. `linked_plots.csv`: all 140 quality plots, infection coverage, source dates and original quality values.
2. `paired_blocks.csv`: all 105 quality comparisons, with 65 valid infection differences.
3. `year_comparisons.csv`: 15 year × comparator summaries, missing infection shown explicitly.
4. `block_influence.csv`: 525 systematic leave-one-block sensitivity records.
5. `summary.json`: source identity, anomalies, eligibility totals and scope boundaries.

Tests use constructed miniature CSVs offline. A separate persisted-output contract
recomputes plot pair differences from the recorded originals and checks the notable
2022 block influence without needing network access in CI.
