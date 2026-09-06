# Cross-environment disease-curve shape stability

## Question

The second empirical field case initially reduced each southern corn leaf blight trajectory to AUDPC,
final severity, maximum severity and t50. Those summaries are useful, but they cannot determine
whether two hybrids with similar total disease burden follow the same epidemic trajectory.

This extension asks a narrower question:

> **Does hybrid-specific disease-progress shape persist across field environments after separating
> trajectory shape from overall disease severity scale?**

## Representation

Eligible environment-hybrid curves are interpolated only inside a common observed DAE support:

\[
30 \le DAE \le 110,
\]

on a fixed 2-day grid. Curves that do not span that interval are excluded rather than extrapolated.

Two representations are retained.

The first is raw interpolated severity, which preserves absolute disease burden. The second divides
that curve by its own time-average severity,

\[
\tilde y(t) = \frac{y(t)}{\bar y},
\qquad
\bar y = \frac{1}{T}\int y(t)\,dt,
\]

so that the normalized trajectory has time-average one. This intentionally removes pure multiplicative
severity differences while retaining relative onset, acceleration and plateau shape.

## Distance diagnostic

For every pair of eligible curves the analysis computes root-mean-square distance on both raw
severity and normalized shape. Pairs are classified as:

- same hybrid, different environment;
- different hybrid, same environment;
- different hybrid, different environment.

The key descriptive comparison is the median normalized-shape distance for the same hybrid across
environments relative to different hybrids across environments.

A ratio below one means that hybrid identity is associated with more stable trajectory shape than a
random cross-hybrid comparison. A ratio above one means the opposite. This is a descriptive
transportability diagnostic, not a causal effect, confirmatory test or model-promotion gate.

## Why this is deliberately nonparametric

The source paper uses a hierarchical generalized additive modelling framework for functional disease
curve comparison. This repository does **not** claim to reproduce that model in Python.

The purpose here is narrower: establish an auditable curve-shape baseline before considering richer
functional models. Linear interpolation on a shared support makes every transformation explicit and
keeps the distinction between disease burden and shape visible.

## Limitations

Scale normalization removes multiplicative burden differences by construction. That is useful for
isolating shape, but it can also hide scientifically meaningful absolute severity differences.
Therefore raw and normalized distances are reported together.

Interpolation also does not create information between assessment dates. The resulting profiles are
representations of observed trajectories, not latent biological truth.

Finally, the field environments are not randomized treatments. Any shape stability or instability
can reflect genotype, environment, measurement schedule and their interaction.
