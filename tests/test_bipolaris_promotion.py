from __future__ import annotations

import pandas as pd
import pytest

from crop_protection_ps.bipolaris_promotion import (
    evaluate_burden_promotion,
    evaluate_shape_promotion,
)


def _burden_baseline() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "held_out_environment": ["E1", "E2", "E3"],
            "n_hybrids": [10, 10, 10],
            "hybrid_history_rmse": [12.0, 10.0, 11.0],
            "hybrid_history_rank_mae": [1.2, 1.0, 1.1],
        }
    )


def _shape_baseline() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "held_out_environment": ["E1", "E2", "E3"],
            "n_hybrids": [10, 10, 10],
            "hybrid_history_shape_rmse": [0.30, 0.25, 0.28],
        }
    )


def test_burden_candidate_must_improve_error_majority_and_ranking() -> None:
    candidate = pd.DataFrame(
        {
            "held_out_environment": ["E1", "E2", "E3"],
            "n_hybrids": [10, 10, 10],
            "candidate_rmse": [10.0, 9.0, 12.0],
            "candidate_rank_mae": [1.0, 0.9, 1.1],
        }
    )

    decision = evaluate_burden_promotion(_burden_baseline(), candidate)

    assert decision.promoted
    assert decision.fold_wins == 2
    assert decision.required_fold_wins == 2
    assert decision.candidate_pooled_rmse < decision.baseline_pooled_rmse
    assert decision.candidate_mean_rank_mae <= decision.baseline_mean_rank_mae
    assert decision.reasons == ()


def test_burden_candidate_is_rejected_when_ranking_worsens() -> None:
    candidate = pd.DataFrame(
        {
            "held_out_environment": ["E1", "E2", "E3"],
            "n_hybrids": [10, 10, 10],
            "candidate_rmse": [10.0, 9.0, 10.0],
            "candidate_rank_mae": [1.4, 1.3, 1.5],
        }
    )

    decision = evaluate_burden_promotion(_burden_baseline(), candidate)

    assert not decision.promoted
    assert "rank" in " ".join(decision.reasons)


def test_burden_candidate_cannot_change_evaluation_population() -> None:
    candidate = pd.DataFrame(
        {
            "held_out_environment": ["E1", "E2", "E3"],
            "n_hybrids": [10, 9, 10],
            "candidate_rmse": [10.0, 9.0, 10.0],
            "candidate_rank_mae": [1.0, 0.9, 1.0],
        }
    )

    with pytest.raises(ValueError, match="evaluated hybrid population"):
        evaluate_burden_promotion(_burden_baseline(), candidate)


def test_shape_candidate_requires_strict_majority_fold_wins() -> None:
    candidate = pd.DataFrame(
        {
            "held_out_environment": ["E1", "E2", "E3"],
            "n_hybrids": [10, 10, 10],
            "candidate_shape_rmse": [0.25, 0.24, 0.31],
        }
    )

    decision = evaluate_shape_promotion(_shape_baseline(), candidate)

    assert decision.promoted
    assert decision.fold_wins == 2
    assert decision.required_fold_wins == 2


def test_shape_candidate_is_rejected_on_average_only_improvement() -> None:
    candidate = pd.DataFrame(
        {
            "held_out_environment": ["E1", "E2", "E3"],
            "n_hybrids": [10, 10, 10],
            "candidate_shape_rmse": [0.20, 0.26, 0.29],
        }
    )

    decision = evaluate_shape_promotion(_shape_baseline(), candidate)

    assert not decision.promoted
    assert decision.fold_wins == 1
    assert "strict majority" in " ".join(decision.reasons)
