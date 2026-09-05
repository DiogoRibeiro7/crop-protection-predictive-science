"""Bayesian hierarchical modelling for replicated Crop Protection field trials.

The implementation deliberately uses an explicit conjugate Gibbs sampler instead of a
probabilistic-programming framework. This keeps the model, priors, partial pooling and
posterior-predictive mechanism visible in a compact portfolio repository.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.linalg import solve_triangular
from sklearn.metrics import mean_absolute_error, mean_squared_error

_FLOAT_EPS: Final[float] = 1.0e-12
_VARIANCE_NAMES: Final[tuple[str, ...]] = (
    "residual",
    "product",
    "product_timing",
    "year",
    "year_block",
)


@dataclass(frozen=True)
class BayesianSamplerConfig:
    """Configuration for reproducible multi-chain Gibbs sampling."""

    n_chains: int = 4
    burn_in: int = 800
    draws_per_chain: int = 800
    thin: int = 2
    seed: int = 20260828

    def __post_init__(self) -> None:
        if self.n_chains < 1:
            raise ValueError("n_chains must be positive.")
        if self.burn_in < 0:
            raise ValueError("burn_in cannot be negative.")
        if self.draws_per_chain < 50:
            raise ValueError("draws_per_chain must be at least 50.")
        if self.thin < 1:
            raise ValueError("thin must be positive.")


@dataclass(frozen=True)
class BayesianPrior:
    """Weakly regularising priors on a standardised sqrt(AUDPC) response.

    Variance components use inverse-gamma priors with common shape and component-specific
    scales. The scales are intentionally exposed so the release can report prior sensitivity.
    """

    variance_shape: float = 2.0
    residual_scale: float = 0.20
    product_scale: float = 0.10
    product_timing_scale: float = 0.05
    year_scale: float = 1.00
    year_block_scale: float = 0.10
    intercept_sd: float = 2.0
    population_timing_sd: float = 1.0

    def __post_init__(self) -> None:
        numeric = (
            self.variance_shape,
            self.residual_scale,
            self.product_scale,
            self.product_timing_scale,
            self.year_scale,
            self.year_block_scale,
            self.intercept_sd,
            self.population_timing_sd,
        )
        if not all(np.isfinite(value) and value > 0 for value in numeric):
            raise ValueError("All Bayesian prior parameters must be finite and positive.")

    def scaled(self, multiplier: float) -> BayesianPrior:
        """Scale variance-prior scale parameters for a sensitivity analysis."""
        if not np.isfinite(multiplier) or multiplier <= 0:
            raise ValueError("Prior scale multiplier must be finite and positive.")
        return BayesianPrior(
            variance_shape=self.variance_shape,
            residual_scale=self.residual_scale * multiplier,
            product_scale=self.product_scale * multiplier,
            product_timing_scale=self.product_timing_scale * multiplier,
            year_scale=self.year_scale * multiplier,
            year_block_scale=self.year_block_scale * multiplier,
            intercept_sd=self.intercept_sd,
            population_timing_sd=self.population_timing_sd,
        )


@dataclass(frozen=True)
class _ModelLayout:
    """Column layout and categorical levels for the hierarchical design matrix."""

    product_levels: tuple[str, ...]
    year_levels: tuple[int, ...]
    year_block_levels: tuple[str, ...]
    columns: tuple[str, ...]
    intercept_index: int
    population_timing_index: int
    product_slice: slice
    product_timing_slice: slice
    year_slice: slice
    year_block_slice: slice


@dataclass(frozen=True)
class BayesianHierarchicalFit:
    """Posterior draws and metadata for the hierarchical field-trial model."""

    beta_draws: NDArray[np.float64]
    variance_draws: NDArray[np.float64]
    layout: _ModelLayout
    response_mean: float
    response_scale: float
    prior: BayesianPrior
    config: BayesianSamplerConfig

    def __post_init__(self) -> None:
        if self.beta_draws.ndim != 3:
            raise ValueError("beta_draws must have shape (chain, draw, parameter).")
        if self.variance_draws.ndim != 3:
            raise ValueError("variance_draws must have shape (chain, draw, component).")
        if self.beta_draws.shape[:2] != self.variance_draws.shape[:2]:
            raise ValueError("Posterior beta and variance draws must align by chain and draw.")
        if self.beta_draws.shape[2] != len(self.layout.columns):
            raise ValueError("Posterior beta width does not match model layout.")
        if self.variance_draws.shape[2] != len(_VARIANCE_NAMES):
            raise ValueError("Unexpected number of variance components.")
        if not np.isfinite(self.response_mean):
            raise ValueError("response_mean must be finite.")
        if not np.isfinite(self.response_scale) or self.response_scale <= 0:
            raise ValueError("response_scale must be finite and positive.")


@dataclass(frozen=True)
class PosteriorPredictiveResult:
    """Posterior-predictive samples and row-level summaries."""

    draws: NDArray[np.float64]
    summary: pd.DataFrame


def _require_columns(frame: pd.DataFrame, columns: Sequence[str]) -> None:
    """Validate that all required model columns are present."""
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def _build_layout(frame: pd.DataFrame) -> _ModelLayout:
    """Create a stable, fully explicit hierarchical parameter layout."""
    _require_columns(frame, ("treatment", "year", "year_block"))
    products = tuple(sorted(str(value) for value in frame["treatment"].unique()))
    years = tuple(sorted(int(value) for value in frame["year"].unique()))
    year_blocks = tuple(sorted(str(value) for value in frame["year_block"].unique()))
    if len(products) < 2 or len(years) < 2 or len(year_blocks) < 2:
        raise ValueError("Hierarchical model requires multiple products, years and blocks.")

    offset = 0
    intercept_index = offset
    offset += 1
    population_timing_index = offset
    offset += 1
    product_slice = slice(offset, offset + len(products))
    offset += len(products)
    product_timing_slice = slice(offset, offset + len(products))
    offset += len(products)
    year_slice = slice(offset, offset + len(years))
    offset += len(years)
    year_block_slice = slice(offset, offset + len(year_blocks))
    offset += len(year_blocks)

    columns = (
        "intercept",
        "population_late",
        *(f"product[{value}]" for value in products),
        *(f"product_late_deviation[{value}]" for value in products),
        *(f"year[{value}]" for value in years),
        *(f"year_block[{value}]" for value in year_blocks),
    )
    if len(columns) != offset:
        raise RuntimeError("Internal model-layout size mismatch.")
    return _ModelLayout(
        product_levels=products,
        year_levels=years,
        year_block_levels=year_blocks,
        columns=tuple(columns),
        intercept_index=intercept_index,
        population_timing_index=population_timing_index,
        product_slice=product_slice,
        product_timing_slice=product_timing_slice,
        year_slice=year_slice,
        year_block_slice=year_block_slice,
    )


def _design_matrix(frame: pd.DataFrame, layout: _ModelLayout) -> NDArray[np.float64]:
    """Construct the training design matrix for known years and nested blocks."""
    _require_columns(frame, ("treatment", "timing", "year", "year_block"))
    n_rows = len(frame)
    matrix = np.zeros((n_rows, len(layout.columns)), dtype=np.float64)
    matrix[:, layout.intercept_index] = 1.0
    late = (frame["timing"].astype(str).to_numpy() == "Late").astype(np.float64)
    matrix[:, layout.population_timing_index] = late

    product_lookup = {value: index for index, value in enumerate(layout.product_levels)}
    year_lookup = {value: index for index, value in enumerate(layout.year_levels)}
    block_lookup = {value: index for index, value in enumerate(layout.year_block_levels)}

    for row_index, (product, year, year_block, late_value) in enumerate(
        zip(
            frame["treatment"].astype(str),
            frame["year"].astype(int),
            frame["year_block"].astype(str),
            late,
            strict=True,
        )
    ):
        if product not in product_lookup:
            raise ValueError(f"Unknown product level: {product}")
        if year not in year_lookup:
            raise ValueError(f"Unknown year level: {year}")
        if year_block not in block_lookup:
            raise ValueError(f"Unknown year-block level: {year_block}")
        product_index = product_lookup[product]
        matrix[row_index, layout.product_slice.start + product_index] = 1.0
        matrix[row_index, layout.product_timing_slice.start + product_index] = late_value
        matrix[row_index, layout.year_slice.start + year_lookup[year]] = 1.0
        matrix[row_index, layout.year_block_slice.start + block_lookup[year_block]] = 1.0
    return matrix


def _sample_inverse_gamma(
    *, shape: float, scale: float, rng: np.random.Generator
) -> float:
    """Sample InvGamma(shape, scale) using the reciprocal-gamma representation."""
    gamma_draw = rng.gamma(shape=shape, scale=1.0 / max(scale, _FLOAT_EPS))
    return float(1.0 / max(gamma_draw, _FLOAT_EPS))


def _variance_scales(prior: BayesianPrior) -> Mapping[str, float]:
    return {
        "residual": prior.residual_scale,
        "product": prior.product_scale,
        "product_timing": prior.product_timing_scale,
        "year": prior.year_scale,
        "year_block": prior.year_block_scale,
    }


def _run_chain(
    x: NDArray[np.float64],
    z: NDArray[np.float64],
    *,
    layout: _ModelLayout,
    prior: BayesianPrior,
    config: BayesianSamplerConfig,
    seed: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Run one Gibbs chain for the Gaussian hierarchical model."""
    rng = np.random.default_rng(seed)
    n_rows, n_parameters = x.shape
    total_iterations = config.burn_in + config.draws_per_chain * config.thin
    beta_saved = np.empty((config.draws_per_chain, n_parameters), dtype=np.float64)
    variance_saved = np.empty(
        (config.draws_per_chain, len(_VARIANCE_NAMES)), dtype=np.float64
    )

    xtx = x.T @ x
    xtz = x.T @ z
    beta = np.zeros(n_parameters, dtype=np.float64)
    variances: dict[str, float] = {
        "residual": 0.30,
        "product": 0.10,
        "product_timing": 0.05,
        "year": 1.00,
        "year_block": 0.10,
    }
    scales = _variance_scales(prior)
    save_index = 0

    for iteration in range(total_iterations):
        prior_precision = np.zeros(n_parameters, dtype=np.float64)
        prior_precision[layout.intercept_index] = 1.0 / prior.intercept_sd**2
        prior_precision[layout.population_timing_index] = (
            1.0 / prior.population_timing_sd**2
        )
        prior_precision[layout.product_slice] = 1.0 / variances["product"]
        prior_precision[layout.product_timing_slice] = 1.0 / variances["product_timing"]
        prior_precision[layout.year_slice] = 1.0 / variances["year"]
        prior_precision[layout.year_block_slice] = 1.0 / variances["year_block"]

        residual_variance = max(variances["residual"], _FLOAT_EPS)
        precision = xtx / residual_variance + np.diag(prior_precision)
        cholesky = np.linalg.cholesky(precision)
        rhs = xtz / residual_variance
        mean = solve_triangular(
            cholesky.T,
            solve_triangular(cholesky, rhs, lower=True),
            lower=False,
        )
        noise = solve_triangular(
            cholesky.T,
            rng.standard_normal(n_parameters),
            lower=False,
        )
        beta = mean + noise

        residuals = z - x @ beta
        variances["residual"] = _sample_inverse_gamma(
            shape=prior.variance_shape + n_rows / 2.0,
            scale=scales["residual"] + 0.5 * float(residuals @ residuals),
            rng=rng,
        )

        component_slices = {
            "product": layout.product_slice,
            "product_timing": layout.product_timing_slice,
            "year": layout.year_slice,
            "year_block": layout.year_block_slice,
        }
        for name, component_slice in component_slices.items():
            values = beta[component_slice]
            variances[name] = _sample_inverse_gamma(
                shape=prior.variance_shape + len(values) / 2.0,
                scale=scales[name] + 0.5 * float(values @ values),
                rng=rng,
            )

        if iteration >= config.burn_in and (
            iteration - config.burn_in
        ) % config.thin == 0:
            beta_saved[save_index] = beta
            variance_saved[save_index] = np.array(
                [variances[name] for name in _VARIANCE_NAMES], dtype=np.float64
            )
            save_index += 1

    if save_index != config.draws_per_chain:
        raise RuntimeError("Sampler did not save the requested number of posterior draws.")
    return beta_saved, variance_saved


def fit_hierarchical_timing_model(
    timing: pd.DataFrame,
    *,
    config: BayesianSamplerConfig | None = None,
    prior: BayesianPrior | None = None,
) -> BayesianHierarchicalFit:
    """Fit a partially pooled Bayesian model to sqrt(AUDPC).

    Model on the standardised response ``z``::

        z_i = alpha + a_product[i]
              + (delta + d_product[i]) * late_i
              + u_year[i] + b_year:block[i] + epsilon_i

    Product effects, product-specific timing deviations, year effects and nested block effects
    are Gaussian exchangeable effects. Their variance components are inferred rather than fixed.
    """
    sampler = config or BayesianSamplerConfig()
    model_prior = prior or BayesianPrior()
    _require_columns(
        timing,
        ("sqrt_audpc", "treatment", "timing", "year", "year_block"),
    )
    if timing["sqrt_audpc"].isna().any():
        raise ValueError("sqrt_audpc cannot contain missing values for Bayesian fitting.")

    layout = _build_layout(timing)
    x = _design_matrix(timing, layout)
    response = timing["sqrt_audpc"].to_numpy(dtype=np.float64)
    response_mean = float(np.mean(response))
    response_scale = float(np.std(response, ddof=1))
    if response_scale <= 0 or not np.isfinite(response_scale):
        raise ValueError("sqrt_audpc must have positive finite variation.")
    z = (response - response_mean) / response_scale

    beta_chains: list[NDArray[np.float64]] = []
    variance_chains: list[NDArray[np.float64]] = []
    seed_sequence = np.random.SeedSequence(sampler.seed)
    child_sequences = seed_sequence.spawn(sampler.n_chains)
    for child in child_sequences:
        chain_seed = int(child.generate_state(1, dtype=np.uint32)[0])
        beta_draws, variance_draws = _run_chain(
            x,
            z,
            layout=layout,
            prior=model_prior,
            config=sampler,
            seed=chain_seed,
        )
        beta_chains.append(beta_draws)
        variance_chains.append(variance_draws)

    return BayesianHierarchicalFit(
        beta_draws=np.stack(beta_chains, axis=0),
        variance_draws=np.stack(variance_chains, axis=0),
        layout=layout,
        response_mean=response_mean,
        response_scale=response_scale,
        prior=model_prior,
        config=sampler,
    )


def _classical_rhat(draws: NDArray[np.float64]) -> float:
    """Compute the classical multi-chain potential scale-reduction statistic."""
    if draws.ndim != 2:
        raise ValueError("R-hat input must have shape (chain, draw).")
    n_chains, n_draws = draws.shape
    if n_chains < 2 or n_draws < 2:
        return float("nan")
    chain_means = np.mean(draws, axis=1)
    within = float(np.mean(np.var(draws, axis=1, ddof=1)))
    between = float(n_draws * np.var(chain_means, ddof=1))
    if within <= _FLOAT_EPS:
        return 1.0 if between <= _FLOAT_EPS else float("inf")
    variance_hat = ((n_draws - 1.0) / n_draws) * within + between / n_draws
    return float(np.sqrt(max(variance_hat / within, 0.0)))


def product_timing_effect_draws(
    fit: BayesianHierarchicalFit,
) -> dict[str, NDArray[np.float64]]:
    """Return posterior late-minus-early effects on the sqrt(AUDPC) scale by product."""
    population = fit.beta_draws[:, :, fit.layout.population_timing_index]
    deviations = fit.beta_draws[:, :, fit.layout.product_timing_slice]
    effects: dict[str, NDArray[np.float64]] = {}
    for product_index, product in enumerate(fit.layout.product_levels):
        effects[product] = (
            population + deviations[:, :, product_index]
        ) * fit.response_scale
    return effects


def posterior_timing_summary(fit: BayesianHierarchicalFit) -> pd.DataFrame:
    """Summarise partially pooled product-specific and population-average timing effects."""
    effect_map = product_timing_effect_draws(fit)
    stacked = np.stack([effect_map[key] for key in fit.layout.product_levels], axis=2)
    average = np.mean(stacked, axis=2)
    records: list[dict[str, object]] = []

    def add_record(scope: str, treatment: str, values: NDArray[np.float64]) -> None:
        flat = values.reshape(-1)
        records.append(
            {
                "scope": scope,
                "treatment": treatment,
                "posterior_mean_delta_sqrt_audpc": float(np.mean(flat)),
                "posterior_sd": float(np.std(flat, ddof=1)),
                "q05": float(np.quantile(flat, 0.05)),
                "q50": float(np.quantile(flat, 0.50)),
                "q95": float(np.quantile(flat, 0.95)),
                "prob_late_greater_disease": float(np.mean(flat > 0.0)),
                "rhat": _classical_rhat(values),
            }
        )

    add_record("population_average", "ALL", average)
    for product in fit.layout.product_levels:
        add_record("product", product, effect_map[product])
    return pd.DataFrame.from_records(records)


def posterior_variance_summary(fit: BayesianHierarchicalFit) -> pd.DataFrame:
    """Summarise hierarchical standard deviations on the sqrt(AUDPC) response scale."""
    records: list[dict[str, object]] = []
    for component_index, component in enumerate(_VARIANCE_NAMES):
        sd_draws = np.sqrt(fit.variance_draws[:, :, component_index]) * fit.response_scale
        flat = sd_draws.reshape(-1)
        records.append(
            {
                "component": component,
                "posterior_mean_sd": float(np.mean(flat)),
                "q05_sd": float(np.quantile(flat, 0.05)),
                "q50_sd": float(np.quantile(flat, 0.50)),
                "q95_sd": float(np.quantile(flat, 0.95)),
                "rhat": _classical_rhat(sd_draws),
            }
        )
    return pd.DataFrame.from_records(records)


def posterior_predict_training(
    fit: BayesianHierarchicalFit,
    timing: pd.DataFrame,
    *,
    seed: int = 20260828,
    max_draws: int = 1_200,
) -> PosteriorPredictiveResult:
    """Generate posterior-predictive draws for observed design points."""
    if max_draws < 100:
        raise ValueError("max_draws must be at least 100.")
    x = _design_matrix(timing, fit.layout)
    beta = fit.beta_draws.reshape(-1, fit.beta_draws.shape[2])
    variances = fit.variance_draws.reshape(-1, fit.variance_draws.shape[2])
    draw_count = min(max_draws, len(beta))
    selected = np.linspace(0, len(beta) - 1, draw_count, dtype=int)
    beta = beta[selected]
    residual_variance = variances[selected, _VARIANCE_NAMES.index("residual")]
    rng = np.random.default_rng(seed)
    means_z = beta @ x.T
    residual_noise = rng.standard_normal(means_z.shape) * np.sqrt(residual_variance)[:, None]
    predictive_sqrt = fit.response_mean + fit.response_scale * (means_z + residual_noise)

    observed = timing["sqrt_audpc"].to_numpy(dtype=np.float64)
    lower90, median, upper90 = np.quantile(predictive_sqrt, [0.05, 0.50, 0.95], axis=0)
    lower95, upper95 = np.quantile(predictive_sqrt, [0.025, 0.975], axis=0)
    summary = timing.loc[:, ["year", "block", "treatment", "timing", "sqrt_audpc"]].copy()
    summary["posterior_predictive_mean"] = np.mean(predictive_sqrt, axis=0)
    summary["posterior_predictive_median"] = median
    summary["pi90_low"] = lower90
    summary["pi90_high"] = upper90
    summary["pi95_low"] = lower95
    summary["pi95_high"] = upper95
    summary["covered_90"] = (observed >= lower90) & (observed <= upper90)
    summary["covered_95"] = (observed >= lower95) & (observed <= upper95)
    return PosteriorPredictiveResult(draws=predictive_sqrt, summary=summary)


def posterior_predictive_diagnostics(
    fit: BayesianHierarchicalFit,
    timing: pd.DataFrame,
    *,
    seed: int = 20260828,
    max_draws: int = 1_200,
) -> pd.DataFrame:
    """Compare observed and replicated datasets using interpretable discrepancy statistics."""
    predictive = posterior_predict_training(fit, timing, seed=seed, max_draws=max_draws)
    observed = timing["sqrt_audpc"].to_numpy(dtype=np.float64)
    replicated = predictive.draws
    statistics: tuple[tuple[str, float, NDArray[np.float64]], ...] = (
        ("mean", float(np.mean(observed)), np.mean(replicated, axis=1)),
        ("sd", float(np.std(observed, ddof=1)), np.std(replicated, axis=1, ddof=1)),
        ("minimum", float(np.min(observed)), np.min(replicated, axis=1)),
        ("maximum", float(np.max(observed)), np.max(replicated, axis=1)),
    )
    records: list[dict[str, object]] = []
    for name, observed_value, replicated_values in statistics:
        records.append(
            {
                "statistic": name,
                "observed": observed_value,
                "replicated_mean": float(np.mean(replicated_values)),
                "replicated_q05": float(np.quantile(replicated_values, 0.05)),
                "replicated_q95": float(np.quantile(replicated_values, 0.95)),
                "bayesian_p_upper": float(np.mean(replicated_values >= observed_value)),
            }
        )
    records.extend(
        [
            {
                "statistic": "row_coverage_90",
                "observed": float(predictive.summary["covered_90"].mean()),
                "replicated_mean": 0.90,
                "replicated_q05": np.nan,
                "replicated_q95": np.nan,
                "bayesian_p_upper": np.nan,
            },
            {
                "statistic": "row_coverage_95",
                "observed": float(predictive.summary["covered_95"].mean()),
                "replicated_mean": 0.95,
                "replicated_q05": np.nan,
                "replicated_q95": np.nan,
                "bayesian_p_upper": np.nan,
            },
            {
                "statistic": "negative_sqrt_prediction_fraction",
                "observed": 0.0,
                "replicated_mean": float(np.mean(replicated < 0.0)),
                "replicated_q05": np.nan,
                "replicated_q95": np.nan,
                "bayesian_p_upper": np.nan,
            },
        ]
    )
    return pd.DataFrame.from_records(records)


def _new_year_predictive_draws(
    fit: BayesianHierarchicalFit,
    test: pd.DataFrame,
    *,
    seed: int,
    max_draws: int,
) -> NDArray[np.float64]:
    """Predict a completely unseen year by integrating over new random effects."""
    _require_columns(test, ("treatment", "timing", "block"))
    if max_draws < 100:
        raise ValueError("max_draws must be at least 100.")
    beta = fit.beta_draws.reshape(-1, fit.beta_draws.shape[2])
    variances = fit.variance_draws.reshape(-1, fit.variance_draws.shape[2])
    draw_count = min(max_draws, len(beta))
    selected = np.linspace(0, len(beta) - 1, draw_count, dtype=int)
    beta = beta[selected]
    variances = variances[selected]
    rng = np.random.default_rng(seed)

    product_lookup = {value: index for index, value in enumerate(fit.layout.product_levels)}
    blocks = tuple(sorted(str(value) for value in test["block"].unique()))
    block_lookup = {value: index for index, value in enumerate(blocks)}
    n_test = len(test)

    fixed_z = np.empty((draw_count, n_test), dtype=np.float64)
    population = beta[:, fit.layout.population_timing_index]
    intercept = beta[:, fit.layout.intercept_index]
    product_effects = beta[:, fit.layout.product_slice]
    timing_deviations = beta[:, fit.layout.product_timing_slice]

    for row_index, (product, timing_value) in enumerate(
        zip(test["treatment"].astype(str), test["timing"].astype(str), strict=True)
    ):
        if product not in product_lookup:
            raise ValueError(
                f"Cannot predict product {product!r}: it was absent from training data."
            )
        product_index = product_lookup[product]
        late = 1.0 if timing_value == "Late" else 0.0
        fixed_z[:, row_index] = (
            intercept
            + product_effects[:, product_index]
            + late * (population + timing_deviations[:, product_index])
        )

    year_sd = np.sqrt(variances[:, _VARIANCE_NAMES.index("year")])
    block_sd = np.sqrt(variances[:, _VARIANCE_NAMES.index("year_block")])
    residual_sd = np.sqrt(variances[:, _VARIANCE_NAMES.index("residual")])
    new_year = rng.standard_normal(draw_count) * year_sd
    new_blocks = rng.standard_normal((draw_count, len(blocks))) * block_sd[:, None]
    residuals = rng.standard_normal((draw_count, n_test)) * residual_sd[:, None]

    predictive_z = fixed_z + new_year[:, None] + residuals
    for row_index, block in enumerate(test["block"].astype(str)):
        predictive_z[:, row_index] += new_blocks[:, block_lookup[block]]
    return fit.response_mean + fit.response_scale * predictive_z


def leave_one_year_out_posterior_predictive(
    timing: pd.DataFrame,
    *,
    config: BayesianSamplerConfig | None = None,
    prior: BayesianPrior | None = None,
    max_predictive_draws: int = 800,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate genuine unseen-year posterior predictive distributions.

    Each fold refits the model without the held-out year. Prediction integrates over a *new*
    year random effect and *new* nested block effects, rather than recycling held-out labels.
    """
    sampler = config or BayesianSamplerConfig(
        n_chains=2, burn_in=500, draws_per_chain=500, thin=2, seed=20260828
    )
    model_prior = prior or BayesianPrior()
    _require_columns(timing, ("year", "sqrt_audpc"))
    years = tuple(sorted(int(value) for value in timing["year"].unique()))
    fold_metrics: list[dict[str, object]] = []
    prediction_rows: list[pd.DataFrame] = []

    for fold_index, held_out_year in enumerate(years):
        train = timing.loc[timing["year"] != held_out_year].copy()
        test = timing.loc[timing["year"] == held_out_year].copy().reset_index(drop=True)
        fold_config = BayesianSamplerConfig(
            n_chains=sampler.n_chains,
            burn_in=sampler.burn_in,
            draws_per_chain=sampler.draws_per_chain,
            thin=sampler.thin,
            seed=sampler.seed + 1009 * (fold_index + 1),
        )
        fit = fit_hierarchical_timing_model(train, config=fold_config, prior=model_prior)
        predictive = _new_year_predictive_draws(
            fit,
            test,
            seed=sampler.seed + 7919 * (fold_index + 1),
            max_draws=max_predictive_draws,
        )
        observed = test["sqrt_audpc"].to_numpy(dtype=np.float64)
        mean_prediction = np.mean(predictive, axis=0)
        q05, q95 = np.quantile(predictive, [0.05, 0.95], axis=0)
        q025, q975 = np.quantile(predictive, [0.025, 0.975], axis=0)
        coverage90 = (observed >= q05) & (observed <= q95)
        coverage95 = (observed >= q025) & (observed <= q975)
        fold_metrics.append(
            {
                "held_out_year": held_out_year,
                "n_test": len(test),
                "rmse": float(np.sqrt(mean_squared_error(observed, mean_prediction))),
                "mae": float(mean_absolute_error(observed, mean_prediction)),
                "coverage_90": float(np.mean(coverage90)),
                "coverage_95": float(np.mean(coverage95)),
                "mean_pi90_width": float(np.mean(q95 - q05)),
                "mean_pi95_width": float(np.mean(q975 - q025)),
                "predictive_negative_fraction": float(np.mean(predictive < 0.0)),
            }
        )
        rows = test.loc[:, ["year", "block", "treatment", "timing", "sqrt_audpc"]].copy()
        rows["posterior_predictive_mean"] = mean_prediction
        rows["pi90_low"] = q05
        rows["pi90_high"] = q95
        rows["pi95_low"] = q025
        rows["pi95_high"] = q975
        rows["covered_90"] = coverage90
        rows["covered_95"] = coverage95
        prediction_rows.append(rows)

    metrics = pd.DataFrame.from_records(fold_metrics)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    observed_all = predictions["sqrt_audpc"].to_numpy(dtype=np.float64)
    mean_all = predictions["posterior_predictive_mean"].to_numpy(dtype=np.float64)
    aggregate = pd.DataFrame(
        [
            {
                "held_out_year": "ALL",
                "n_test": len(predictions),
                "rmse": float(np.sqrt(mean_squared_error(observed_all, mean_all))),
                "mae": float(mean_absolute_error(observed_all, mean_all)),
                "coverage_90": float(predictions["covered_90"].mean()),
                "coverage_95": float(predictions["covered_95"].mean()),
                "mean_pi90_width": float(
                    np.mean(predictions["pi90_high"] - predictions["pi90_low"])
                ),
                "mean_pi95_width": float(
                    np.mean(predictions["pi95_high"] - predictions["pi95_low"])
                ),
                "predictive_negative_fraction": np.nan,
            }
        ]
    )
    metrics = pd.concat([metrics, aggregate], ignore_index=True)
    return metrics, predictions


def prior_sensitivity(
    timing: pd.DataFrame,
    *,
    multipliers: Sequence[float] = (0.5, 1.0, 2.0),
    config: BayesianSamplerConfig | None = None,
) -> pd.DataFrame:
    """Check whether the main timing conclusion depends materially on variance-prior scale."""
    sampler = config or BayesianSamplerConfig(
        n_chains=2, burn_in=500, draws_per_chain=500, thin=2, seed=20260828
    )
    baseline_prior = BayesianPrior()
    records: list[dict[str, object]] = []
    for index, multiplier in enumerate(multipliers):
        fit_config = BayesianSamplerConfig(
            n_chains=sampler.n_chains,
            burn_in=sampler.burn_in,
            draws_per_chain=sampler.draws_per_chain,
            thin=sampler.thin,
            seed=sampler.seed + index * 3571,
        )
        fit = fit_hierarchical_timing_model(
            timing,
            config=fit_config,
            prior=baseline_prior.scaled(float(multiplier)),
        )
        timing_summary = posterior_timing_summary(fit)
        average = timing_summary.loc[timing_summary["scope"] == "population_average"].iloc[0]
        variance = posterior_variance_summary(fit).set_index("component")
        records.append(
            {
                "variance_prior_scale_multiplier": float(multiplier),
                "population_timing_mean": float(average["posterior_mean_delta_sqrt_audpc"]),
                "population_timing_q05": float(average["q05"]),
                "population_timing_q95": float(average["q95"]),
                "prob_late_greater_disease": float(average["prob_late_greater_disease"]),
                "year_sd_mean": float(variance.loc["year", "posterior_mean_sd"]),
                "residual_sd_mean": float(variance.loc["residual", "posterior_mean_sd"]),
            }
        )
    return pd.DataFrame.from_records(records)
