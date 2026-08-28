"""Tests for decision-aware adaptive field-trial replication."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crop_protection_ps.adaptive_design import (
    AdaptiveSimulationConfig,
    NormalTimingBelief,
    acquisition_table,
    bayes_timing_regret,
    posterior_sign_probability,
    sign_entropy,
    sign_information_gain,
    simulate_adaptive_policies,
    summarise_allocations,
    summarise_policy_simulation,
    update_normal_belief,
)


def test_normal_update_reduces_variance_and_moves_toward_observation() -> None:
    belief = NormalTimingBelief(mean=1.0, variance=1.0, observation_variance=4.0)
    updated = update_normal_belief(belief, observation=-1.0)
    assert updated.variance < belief.variance
    assert -1.0 < updated.mean < 1.0


def test_sign_metrics_are_bounded_and_information_gain_is_nonnegative() -> None:
    belief = NormalTimingBelief(mean=0.3, variance=0.8, observation_variance=2.0)
    probability = posterior_sign_probability(belief)
    entropy = sign_entropy(belief)
    gain = sign_information_gain(belief)
    regret = bayes_timing_regret(belief)
    assert 0.0 < probability < 1.0
    assert 0.0 <= entropy <= np.log(2.0)
    assert 0.0 <= gain <= entropy
    assert regret >= 0.0


def test_uninformative_observation_has_smaller_sign_information_gain() -> None:
    precise = NormalTimingBelief(mean=0.1, variance=1.0, observation_variance=0.5)
    noisy = NormalTimingBelief(mean=0.1, variance=1.0, observation_variance=500.0)
    assert sign_information_gain(precise) > sign_information_gain(noisy)


def test_decision_objective_targets_ambiguous_sign_not_largest_parameter_gain() -> None:
    beliefs = {
        "clear": NormalTimingBelief(mean=2.5, variance=1.0, observation_variance=1.0),
        "uncertain": NormalTimingBelief(mean=0.05, variance=0.4, observation_variance=2.0),
    }
    table = acquisition_table(beliefs)
    decision_first = table.sort_values("decision_eig_rank").iloc[0]["treatment"]
    assert decision_first == "uncertain"


def test_policy_simulation_is_deterministic_and_respects_budget() -> None:
    beliefs = {
        "A": NormalTimingBelief(mean=0.2, variance=0.8, observation_variance=2.0),
        "B": NormalTimingBelief(mean=1.5, variance=0.5, observation_variance=1.0),
    }
    config = AdaptiveSimulationConfig(
        n_rollouts=500,
        max_budget=4,
        checkpoints=(0, 2, 4),
        seed=11,
    )
    first = simulate_adaptive_policies(beliefs, config=config)
    second = simulate_adaptive_policies(beliefs, config=config)
    pd.testing.assert_frame_equal(first.rollout_metrics, second.rollout_metrics)
    pd.testing.assert_frame_equal(first.allocation_paths, second.allocation_paths)

    allocations = summarise_allocations(first)
    final = allocations.loc[allocations["budget_paired_blocks"] == 4]
    assert np.allclose(final[["A", "B"]].sum(axis=1), 4.0)


def test_policy_summary_contains_all_three_policies() -> None:
    beliefs = {
        "A": NormalTimingBelief(mean=0.1, variance=1.0, observation_variance=2.0),
        "B": NormalTimingBelief(mean=1.5, variance=0.5, observation_variance=1.0),
    }
    result = simulate_adaptive_policies(
        beliefs,
        config=AdaptiveSimulationConfig(
            n_rollouts=500,
            max_budget=2,
            checkpoints=(0, 2),
            seed=7,
        ),
    )
    summary = summarise_policy_simulation(result)
    assert set(summary["policy"]) == {"uniform", "parameter_eig", "decision_eig"}
    assert set(summary["budget_paired_blocks"]) == {0, 2}


def test_invalid_belief_is_rejected() -> None:
    with pytest.raises(ValueError):
        NormalTimingBelief(mean=0.0, variance=0.0, observation_variance=1.0)
