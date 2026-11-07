# Trial-year and field-block sensitivity of the hop timing effect

## Question

Does the observed advantage of applying a synthetic fungicide earlier depend
on one particular trial year or on a small number of blocks?

This analysis reuses the original public Richardson & Gent (2024) field data
and the existing 92 complete comparisons. Each comparison remains paired
within **year × block × product**. As required by the source paper, 2019
is excluded because flooding confounded the experiment; its raw data remain
untouched in the repository.

## Estimands and design

For each observed early/late pair, define

\[
\Delta_{ybp}=\operatorname{AUDPC}_{ybp}^{\mathrm{late}}
-\operatorname{AUDPC}_{ybp}^{\mathrm{early}}.
\]

Positive values indicate greater accumulated disease under the late programme.
Two summaries answer different questions:

1. **Pair-weighted contrast:** mean of all complete product pairs, retaining
   the observed distribution of products across seasons.
2. **Equal-year contrast:** mean of the within-year contrasts, giving each
   of the four eligible years the same influence.

The diagnostics also recompute both estimates after omitting each trial year,
and after omitting each complete *year × block* cluster. Missing comparisons
are never filled in and the excluded year is never reintroduced.

## Results on the public data

| Diagnostic | AUDPC difference (late − early) |
| --- | ---: |
| Original pair-weighted mean, 92 pairs | 40.93 |
| Mean giving each of four years equal weight | 39.43 |
| Range after omitting one full year | 32.69 to 45.57 |
| Largest absolute shift after omitting a year × block | 8.30 |
| Two-stage year-and-block bootstrap, pair-weighted percentile range | 14.00 to 74.40 |

All four annual mean contrasts have the same positive direction. The
year-equal estimate is close to the original pair-weighted estimate; there is
no reversal after dropping any one eligible year. The range of omitted-year
estimates is a direct finite-dataset sensitivity result, not a probability
interval.

The nested bootstrap draws whole trial years with replacement, then resamples
whole blocks within each selected year; all observed product comparisons in a
sampled block move together. This preserves the dependence structure more
fully than resampling 92 individual pairs. The random seed and 5,000 draws are
fixed in the result receipt.

## Limits

These analyses are **diagnostic**, not a new causal identification claim.
The treatment programmes and randomisation protocol have not been reverified
here, and the original paired analysis is not a formal randomisation test.
With only four eligible years, a hierarchical bootstrap percentile range is
not guaranteed to have nominal frequentist coverage. It should not be
presented as a calibrated 95% confidence interval or evidence of transfer
to new sites, seasons, products or disease pressures.

The lack of a sign reversal in four years is useful evidence of stability
*inside this particular experiment*. Independent, protocol-rich intervention
trials are still needed for external validation.

## Reproduction

The analysis uses the original CSV; no fresh model is fitted and no later
test environment is used for model selection.

```bash
PYTHONPATH=src python -m crop_protection_ps.hop_timing_sensitivity
```

Outputs are stored in
`results/real_hop_trial/timing_sensitivity/`:

- `by_year.csv`: annual effects and within-year block/product coverage;
- `leave_one_year_out.csv`: all four omitted-year estimates;
- `leave_one_year_block_out.csv`: 20 omitted-cluster estimates and shifts;
- `summary.json`: source SHA-256, estimands, resampling seed, percentile ranges
  and interpretation limits.

The source study and data provenance are described in
[the original hop case study](real_case_hop_downy_mildew.md).
