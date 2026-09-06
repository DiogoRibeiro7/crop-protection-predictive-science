"""Pre-registered promotion rules for prospective Bipolaris environment models.

The contract is deliberately evaluated on the existing leave-one-environment-out folds. A richer
candidate is promoted only when it improves held-out prediction without changing the evaluation
population or sacrificing the hybrid-ranking objective.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BurdenPromotionDecision:
    """Decision record for a candidate AUDPC transport model."""

    promoted: bool
    baseline_pooled_rmse: float
    candidate_pooled_rmse: float
    fold_wins: int
    required_fold_wins: int
    baseline_mean_rank_mae: float
    candidate_mean_rank_mae: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ShapePromotionDecision:
    """Decision record for a candidate normalized-trajectory transport model."""

    promoted: bool
    baseline_weighted_shape_rmse: float
    candidate_weighted_shape_rmse: float
    fold_wins: int
    required_fold_wins: int
    reasons: tuple[str, ...]


def _validate_fold_alignment(
    baseline: pd.DataFrame,
    candidate: pd.DataFrame,
) -> pd.DataFrame:
    """Join candidate and baseline folds only when the evaluation population is identical."""
    key = "held_out_environment"
    if key not in baseline.columns or key not in candidate.columns:
        raise ValueError("Both tables must contain held_out_environment.")
    if baseline[key].duplicated().any() or candidate[key].duplicated().any():
        raise ValueError("Each held-out environment must appear exactly once per fold table.")

    baseline_envs = set(map(str, baseline[key]))
    candidate_envs = set(map(str, candidate[key]))
    if baseline_envs != candidate_envs:
        missing_candidate = sorted(baseline_envs.difference(candidate_envs))
        extra_candidate = sorted(candidate_envs.difference(baseline_envs))
        raise ValueError(
            "Candidate and baseline folds differ: "
            f"missing={missing_candidate}, extra={extra_candidate}."
        )

    merged = baseline.merge(
        candidate,
        on=key,
        suffixes=("_baseline", "_candidate"),
        validate="one_to_one",
    )
    if "n_hybrids_baseline" in merged.columns and "n_hybrids_candidate" in merged.columns:
        mismatched_population = (
            merged["n_hybrids_baseline"].astype(int)
            != merged["n_hybrids_candidate"].astype(int)
        )
        if bool(mismatched_population.any()):
            bad = merged.loc[mismatched_population, key].astype(str).tolist()
            raise ValueError(
                "Candidate changed the evaluated hybrid population in folds: "
                f"{bad}."
            )
    return merged.sort_values(key).reset_index(drop=True)


def _strict_majority(n_folds: int) -> int:
    """Return the minimum number of wins required for a strict majority."""
    if n_folds < 1:
        raise ValueError("At least one fold is required.")
    return n_folds // 2 + 1


def _pooled_rmse(rmse: np.ndarray, counts: np.ndarray) -> float:
    """Pool fold RMSE values by reconstructing the weighted mean squared error."""
    if rmse.shape != counts.shape or rmse.size == 0:
        raise ValueError("RMSE and count arrays must be non-empty and aligned.")
    if not np.isfinite(rmse).all() or not np.isfinite(counts).all():
        raise ValueError("RMSE and count values must be finite.")
    if bool((rmse < 0).any()) or bool((counts <= 0).any()):
        raise ValueError("RMSE must be non-negative and counts must be positive.")
    return float(np.sqrt(np.sum(counts * np.square(rmse)) / np.sum(counts)))


def evaluate_burden_promotion(
    baseline_folds: pd.DataFrame,
    candidate_folds: pd.DataFrame,
) -> BurdenPromotionDecision:
    """Evaluate a richer AUDPC model against the same hybrid-history LOEO baseline.

    Promotion requires all of the following, declared before a candidate model is fitted:

    1. exactly the same held-out environments and evaluated hybrid counts;
    2. lower pooled held-out AUDPC RMSE;
    3. lower fold RMSE in a strict majority of environments;
    4. no increase in mean held-out hybrid-rank MAE.

    No p-value or post-hoc percentage threshold is used because the number of independent field
    environments is small.
    """
    baseline_required = {
        "held_out_environment",
        "n_hybrids",
        "hybrid_history_rmse",
        "hybrid_history_rank_mae",
    }
    candidate_required = {
        "held_out_environment",
        "n_hybrids",
        "candidate_rmse",
        "candidate_rank_mae",
    }
    baseline_missing = baseline_required.difference(baseline_folds.columns)
    candidate_missing = candidate_required.difference(candidate_folds.columns)
    if baseline_missing:
        raise ValueError(f"Missing baseline burden columns: {sorted(baseline_missing)}.")
    if candidate_missing:
        raise ValueError(f"Missing candidate burden columns: {sorted(candidate_missing)}.")

    merged = _validate_fold_alignment(baseline_folds, candidate_folds)
    counts = merged["n_hybrids_baseline"].to_numpy(dtype=float)
    baseline_rmse = merged["hybrid_history_rmse"].to_numpy(dtype=float)
    candidate_rmse = merged["candidate_rmse"].to_numpy(dtype=float)
    baseline_rank_mae = merged["hybrid_history_rank_mae"].to_numpy(dtype=float)
    candidate_rank_mae = merged["candidate_rank_mae"].to_numpy(dtype=float)

    if not np.isfinite(baseline_rank_mae).all() or not np.isfinite(candidate_rank_mae).all():
        raise ValueError("Rank MAE values must be finite.")
    if bool((baseline_rank_mae < 0).any()) or bool((candidate_rank_mae < 0).any()):
        raise ValueError("Rank MAE values must be non-negative.")

    baseline_pooled = _pooled_rmse(baseline_rmse, counts)
    candidate_pooled = _pooled_rmse(candidate_rmse, counts)
    fold_wins = int((candidate_rmse < baseline_rmse).sum())
    required_fold_wins = _strict_majority(len(merged))
    baseline_rank = float(np.average(baseline_rank_mae, weights=counts))
    candidate_rank = float(np.average(candidate_rank_mae, weights=counts))

    reasons: list[str] = []
    if candidate_pooled >= baseline_pooled:
        reasons.append("candidate does not improve pooled held-out AUDPC RMSE")
    if fold_wins < required_fold_wins:
        reasons.append("candidate does not win a strict majority of held-out environments")
    if candidate_rank > baseline_rank:
        reasons.append("candidate worsens weighted held-out hybrid-rank MAE")

    return BurdenPromotionDecision(
        promoted=not reasons,
        baseline_pooled_rmse=baseline_pooled,
        candidate_pooled_rmse=candidate_pooled,
        fold_wins=fold_wins,
        required_fold_wins=required_fold_wins,
        baseline_mean_rank_mae=baseline_rank,
        candidate_mean_rank_mae=candidate_rank,
        reasons=tuple(reasons),
    )


def evaluate_shape_promotion(
    baseline_folds: pd.DataFrame,
    candidate_folds: pd.DataFrame,
) -> ShapePromotionDecision:
    """Evaluate a candidate normalized-trajectory model on identical LOEO folds.

    The existing shape fold metric is a mean per-hybrid trajectory RMSE, so aggregation uses the
    evaluated hybrid counts as weights rather than treating folds of different sizes equally.
    """
    baseline_required = {
        "held_out_environment",
        "n_hybrids",
        "hybrid_history_shape_rmse",
    }
    candidate_required = {
        "held_out_environment",
        "n_hybrids",
        "candidate_shape_rmse",
    }
    baseline_missing = baseline_required.difference(baseline_folds.columns)
    candidate_missing = candidate_required.difference(candidate_folds.columns)
    if baseline_missing:
        raise ValueError(f"Missing baseline shape columns: {sorted(baseline_missing)}.")
    if candidate_missing:
        raise ValueError(f"Missing candidate shape columns: {sorted(candidate_missing)}.")

    merged = _validate_fold_alignment(baseline_folds, candidate_folds)
    counts = merged["n_hybrids_baseline"].to_numpy(dtype=float)
    baseline_error = merged["hybrid_history_shape_rmse"].to_numpy(dtype=float)
    candidate_error = merged["candidate_shape_rmse"].to_numpy(dtype=float)
    if not np.isfinite(baseline_error).all() or not np.isfinite(candidate_error).all():
        raise ValueError("Shape RMSE values must be finite.")
    if bool((baseline_error < 0).any()) or bool((candidate_error < 0).any()):
        raise ValueError("Shape RMSE values must be non-negative.")

    baseline_weighted = float(np.average(baseline_error, weights=counts))
    candidate_weighted = float(np.average(candidate_error, weights=counts))
    fold_wins = int((candidate_error < baseline_error).sum())
    required_fold_wins = _strict_majority(len(merged))

    reasons: list[str] = []
    if candidate_weighted >= baseline_weighted:
        reasons.append("candidate does not improve weighted held-out trajectory RMSE")
    if fold_wins < required_fold_wins:
        reasons.append("candidate does not win a strict majority of held-out environments")

    return ShapePromotionDecision(
        promoted=not reasons,
        baseline_weighted_shape_rmse=baseline_weighted,
        candidate_weighted_shape_rmse=candidate_weighted,
        fold_wins=fold_wins,
        required_fold_wins=required_fold_wins,
        reasons=tuple(reasons),
    )
