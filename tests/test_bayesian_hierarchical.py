from pathlib import Path

import numpy as np

from crop_protection_ps.bayesian_hierarchical import (
    BayesianSamplerConfig,
    fit_hierarchical_timing_model,
    leave_one_year_out_posterior_predictive,
    posterior_predictive_diagnostics,
    posterior_timing_summary,
    posterior_variance_summary,
)
from crop_protection_ps.hop_trial import (
    load_hop_trial,
    prepare_primary_analysis,
    prepare_timing_analysis,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "richardson_gent_hop_downy_mildew.csv"


def _timing_data():
    return prepare_timing_analysis(prepare_primary_analysis(load_hop_trial(RAW)))


def test_bayesian_sampler_is_reproducible_for_fixed_seed() -> None:
    timing = _timing_data()
    config = BayesianSamplerConfig(
        n_chains=1,
        burn_in=60,
        draws_per_chain=60,
        thin=1,
        seed=123,
    )
    first = fit_hierarchical_timing_model(timing, config=config)
    second = fit_hierarchical_timing_model(timing, config=config)
    assert np.array_equal(first.beta_draws, second.beta_draws)
    assert np.array_equal(first.variance_draws, second.variance_draws)


def test_partial_pooling_produces_one_timing_effect_per_product() -> None:
    timing = _timing_data()
    fit = fit_hierarchical_timing_model(
        timing,
        config=BayesianSamplerConfig(
            n_chains=2,
            burn_in=80,
            draws_per_chain=80,
            thin=1,
            seed=456,
        ),
    )
    summary = posterior_timing_summary(fit)
    products = summary.loc[summary["scope"] == "product", "treatment"]
    assert set(products) == set(timing["treatment"].unique())
    population = summary.loc[summary["scope"] == "population_average"].iloc[0]
    assert population["posterior_mean_delta_sqrt_audpc"] > 0.0
    assert 0.0 <= population["prob_late_greater_disease"] <= 1.0
    variance = posterior_variance_summary(fit)
    assert set(variance["component"]) == {
        "residual",
        "product",
        "product_timing",
        "year",
        "year_block",
    }


def test_posterior_predictive_checks_are_finite_and_bounded() -> None:
    timing = _timing_data()
    fit = fit_hierarchical_timing_model(
        timing,
        config=BayesianSamplerConfig(
            n_chains=1,
            burn_in=60,
            draws_per_chain=60,
            thin=1,
            seed=789,
        ),
    )
    diagnostics = posterior_predictive_diagnostics(fit, timing, max_draws=100)
    coverage = diagnostics.loc[
        diagnostics["statistic"].isin(["row_coverage_90", "row_coverage_95"]), "observed"
    ]
    assert np.isfinite(coverage).all()
    assert ((coverage >= 0.0) & (coverage <= 1.0)).all()


def test_leave_one_year_out_predicts_every_primary_timing_row() -> None:
    timing = _timing_data()
    metrics, predictions = leave_one_year_out_posterior_predictive(
        timing,
        config=BayesianSamplerConfig(
            n_chains=1,
            burn_in=50,
            draws_per_chain=60,
            thin=1,
            seed=987,
        ),
        max_predictive_draws=100,
    )
    assert len(predictions) == len(timing) == 187
    assert set(metrics["held_out_year"].astype(str)) == {"2017", "2018", "2020", "2021", "ALL"}
    aggregate = metrics.loc[metrics["held_out_year"] == "ALL"].iloc[0]
    assert aggregate["rmse"] > 0.0
    assert 0.0 <= aggregate["coverage_90"] <= 1.0
    assert 0.0 <= aggregate["coverage_95"] <= 1.0
