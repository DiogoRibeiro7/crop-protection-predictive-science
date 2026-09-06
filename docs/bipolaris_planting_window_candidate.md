# Bipolaris planting-window candidate

## Purpose

The prospective leave-one-environment-out baseline asks whether same-hybrid history from other field environments transports better than an environment-agnostic training mean. The promotion contract is already fixed independently of any richer model.

This candidate tests the smallest additional environment signal already available in the public field labels: planting window, encoded as `Cedo` or `Preferencial`.

The candidate is intentionally interpretable. For held-out environment \(e\), hybrid \(h\), and known planting-window class \(w(e)\), the AUDPC prediction is

\[
\widehat y_{h,e}
=
\bar y_{h,-e}
+
\bar y_{w(e),-e}
-
\bar y_{-e},
\]

where every mean is computed only from the training environments. The held-out environment's disease outcomes are never used to estimate any component.

The same additive decomposition is applied pointwise to the existing scale-normalized disease-curve representation.

## Why this model

This is deliberately not a general environment-response model. It adds one pre-known categorical field-design variable to the existing hybrid-history baseline. That makes a positive result interpretable: the planting-window label carries prospective information beyond hybrid identity alone.

A negative result is equally useful. It would say that this coarse design label does not justify extra model complexity under the existing held-out-environment task.

## Promotion rule

The model does not define its own success criterion. It is evaluated by the already-merged promotion contract.

For AUDPC burden it must:

1. use exactly the same held-out environments and evaluated hybrids as the hybrid-history baseline;
2. reduce pooled held-out RMSE;
3. win a strict majority of held-out environments;
4. not worsen weighted hybrid-rank MAE.

For normalized trajectory shape it must reduce weighted held-out error and win a strict majority of environments on the same evaluation population.

No p-value or post-hoc percentage threshold is introduced.

## Interpretation boundary

The suffix `Cedo` / `Preferencial` is treated as a field-design label, not as a mechanistic weather or phenology measurement. Promotion would support only the claim that this known categorical label improves prospective prediction in this specific public dataset. It would not establish a causal planting-date effect or justify cultivar recommendations.
