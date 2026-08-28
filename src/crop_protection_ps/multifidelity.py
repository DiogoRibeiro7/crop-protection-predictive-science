"""Multi-fidelity screening for Crop Protection R&D candidate progression.

This module implements a controlled lab -> glasshouse -> field screening problem. The synthetic
DGP is intentionally explicit: lower-fidelity assays are informative but imperfect surrogates for
latent field efficacy. This makes it possible to test whether a multi-fidelity policy really
improves candidate selection under a fixed experimental budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score

PolicyName = Literal["field_only", "lab_field", "multifidelity"]

_DEFAULT_SEED: Final[int] = 20260828


@dataclass(frozen=True)
class FidelityCosts:
    """Relative cost of one replicate at each experimental fidelity."""

    lab: int = 1
    glasshouse: int = 4
    field: int = 20

    def __post_init__(self) -> None:
        if min(self.lab, self.glasshouse, self.field) <= 0:
            raise ValueError("All fidelity costs must be positive.")
        if not (self.lab < self.glasshouse < self.field):
            raise ValueError("Expected lab < glasshouse < field cost ordering.")


@dataclass(frozen=True)
class MultiFidelityConfig:
    """Design parameters for the controlled candidate-screening experiment."""

    n_candidates: int = 80
    n_selected: int = 8
    lab_replicates: int = 2
    glasshouse_replicates: int = 2
    field_replicates: int = 2
    n_glasshouse_multifidelity: int = 30
    n_field_multifidelity: int = 16
    n_field_lab_field: int = 22
    n_field_field_only: int = 26
    n_rollouts: int = 5_000
    calibration_train_size: int = 300
    calibration_test_size: int = 150
    ridge_alpha: float = 5.0
    seed: int = _DEFAULT_SEED
    costs: FidelityCosts = FidelityCosts()

    def __post_init__(self) -> None:
        integer_values = (
            self.n_candidates,
            self.n_selected,
            self.lab_replicates,
            self.glasshouse_replicates,
            self.field_replicates,
            self.n_glasshouse_multifidelity,
            self.n_field_multifidelity,
            self.n_field_lab_field,
            self.n_field_field_only,
            self.n_rollouts,
            self.calibration_train_size,
            self.calibration_test_size,
        )
        if min(integer_values) <= 0:
            raise ValueError("All count parameters must be positive.")
        if self.n_selected >= self.n_candidates:
            raise ValueError("n_selected must be smaller than n_candidates.")
        if self.n_field_multifidelity < self.n_selected:
            raise ValueError(
                "Multi-fidelity field stage must contain at least n_selected candidates."
            )
        if self.n_glasshouse_multifidelity < self.n_field_multifidelity:
            raise ValueError("Glasshouse stage must be at least as large as the field stage.")
        if self.n_field_lab_field < self.n_selected or self.n_field_field_only < self.n_selected:
            raise ValueError(
                "Every policy must field-test enough candidates to make the final selection."
            )
        if self.ridge_alpha < 0.0:
            raise ValueError("ridge_alpha must be non-negative.")

    @property
    def common_budget(self) -> int:
        """Return the exact experimental budget used by every policy."""
        multifidelity = (
            self.n_candidates * self.lab_replicates * self.costs.lab
            + self.n_glasshouse_multifidelity
            * self.glasshouse_replicates
            * self.costs.glasshouse
            + self.n_field_multifidelity * self.field_replicates * self.costs.field
        )
        lab_field = (
            self.n_candidates * self.lab_replicates * self.costs.lab
            + self.n_field_lab_field * self.field_replicates * self.costs.field
        )
        field_only = self.n_field_field_only * self.field_replicates * self.costs.field
        if len({multifidelity, lab_field, field_only}) != 1:
            raise ValueError(
                "Policy stage counts do not produce an equal budget: "
                f"multi={multifidelity}, lab_field={lab_field}, field_only={field_only}."
            )
        return int(multifidelity)


@dataclass(frozen=True)
class CandidateCohort:
    """Latent field efficacy and noisy observations at three experimental fidelities."""

    true_field_efficacy: NDArray[np.float64]
    lab: NDArray[np.float64]
    glasshouse: NDArray[np.float64]
    field: NDArray[np.float64]

    @property
    def n_candidates(self) -> int:
        """Number of candidate products in the cohort."""
        return int(self.true_field_efficacy.shape[0])

    def __post_init__(self) -> None:
        n = self.true_field_efficacy.shape[0]
        if self.true_field_efficacy.ndim != 1:
            raise ValueError("true_field_efficacy must be one-dimensional.")
        for name, values in (
            ("lab", self.lab),
            ("glasshouse", self.glasshouse),
            ("field", self.field),
        ):
            if values.ndim != 2 or values.shape[0] != n:
                raise ValueError(f"{name} must be a 2D array with one row per candidate.")
            if not np.isfinite(values).all():
                raise ValueError(f"{name} contains non-finite values.")
        if not np.isfinite(self.true_field_efficacy).all():
            raise ValueError("true_field_efficacy contains non-finite values.")


@dataclass(frozen=True)
class CalibrationModels:
    """Cross-fidelity calibration models trained on historical candidates."""

    lab_to_field: Ridge
    lab_glasshouse_to_field: Ridge


def simulate_candidate_cohort(
    n_candidates: int,
    *,
    n_lab_replicates: int = 2,
    n_glasshouse_replicates: int = 2,
    n_field_replicates: int = 2,
    rng: np.random.Generator,
) -> CandidateCohort:
    """Simulate one controlled multi-fidelity Crop Protection candidate cohort.

    The latent target is field efficacy. Lab and glasshouse assays are biased surrogates with
    candidate-specific discordance as well as measurement error. Glasshouse measurements are
    deliberately closer to field efficacy than lab measurements, but neither is a perfect proxy.
    """
    if n_candidates <= 0:
        raise ValueError("n_candidates must be positive.")
    if min(n_lab_replicates, n_glasshouse_replicates, n_field_replicates) <= 0:
        raise ValueError("Replicate counts must be positive.")

    theta = rng.normal(loc=2.0, scale=1.0, size=n_candidates).astype(np.float64)

    # Candidate-specific transfer mismatch remains even if measurement noise were averaged away.
    lab_latent = 0.50 + 0.65 * theta + rng.normal(0.0, 0.70, size=n_candidates)
    glasshouse_latent = 0.20 + 0.88 * theta + rng.normal(0.0, 0.35, size=n_candidates)

    lab = np.column_stack(
        [lab_latent + rng.normal(0.0, 0.70, size=n_candidates) for _ in range(n_lab_replicates)]
    ).astype(np.float64)
    glasshouse = np.column_stack(
        [
            glasshouse_latent + rng.normal(0.0, 0.45, size=n_candidates)
            for _ in range(n_glasshouse_replicates)
        ]
    ).astype(np.float64)
    field = np.column_stack(
        [theta + rng.normal(0.0, 0.45, size=n_candidates) for _ in range(n_field_replicates)]
    ).astype(np.float64)
    return CandidateCohort(theta, lab, glasshouse, field)


def fit_calibration_models(cohort: CandidateCohort, *, ridge_alpha: float) -> CalibrationModels:
    """Fit historical cross-fidelity calibration models against latent field efficacy."""
    if ridge_alpha < 0.0:
        raise ValueError("ridge_alpha must be non-negative.")
    lab_mean = cohort.lab.mean(axis=1)
    glasshouse_mean = cohort.glasshouse.mean(axis=1)
    # Historical calibration is trained against observed field means, never latent truth.
    target = cohort.field.mean(axis=1)

    lab_model = Ridge(alpha=ridge_alpha)
    lab_model.fit(lab_mean.reshape(-1, 1), target)

    combined_model = Ridge(alpha=ridge_alpha)
    combined_model.fit(np.column_stack([lab_mean, glasshouse_mean]), target)
    return CalibrationModels(lab_to_field=lab_model, lab_glasshouse_to_field=combined_model)


def evaluate_calibration(
    models: CalibrationModels,
    cohort: CandidateCohort,
) -> pd.DataFrame:
    """Evaluate lab-only and lab+glasshouse calibration on held-out historical candidates."""
    lab_mean = cohort.lab.mean(axis=1)
    glasshouse_mean = cohort.glasshouse.mean(axis=1)
    target = cohort.true_field_efficacy
    predictions = {
        "lab_only": models.lab_to_field.predict(lab_mean.reshape(-1, 1)),
        "lab_plus_glasshouse": models.lab_glasshouse_to_field.predict(
            np.column_stack([lab_mean, glasshouse_mean])
        ),
    }
    rows: list[dict[str, float | str]] = []
    for name, prediction in predictions.items():
        rmse = float(np.sqrt(mean_squared_error(target, prediction)))
        rows.append(
            {
                "calibration_model": name,
                "rmse_field_efficacy": rmse,
                "r2_field_efficacy": float(r2_score(target, prediction)),
                "correlation": float(np.corrcoef(target, prediction)[0, 1]),
            }
        )
    return pd.DataFrame.from_records(rows)


def policy_cost_table(config: MultiFidelityConfig) -> pd.DataFrame:
    """Return auditable stage counts and equal total cost for the three policies."""
    budget = config.common_budget
    records = [
        {
            "policy": "field_only",
            "lab_candidates": 0,
            "glasshouse_candidates": 0,
            "field_candidates": config.n_field_field_only,
            "total_cost_units": budget,
        },
        {
            "policy": "lab_field",
            "lab_candidates": config.n_candidates,
            "glasshouse_candidates": 0,
            "field_candidates": config.n_field_lab_field,
            "total_cost_units": budget,
        },
        {
            "policy": "multifidelity",
            "lab_candidates": config.n_candidates,
            "glasshouse_candidates": config.n_glasshouse_multifidelity,
            "field_candidates": config.n_field_multifidelity,
            "total_cost_units": budget,
        },
    ]
    return pd.DataFrame.from_records(records)


def _selection_metrics(
    true_efficacy: NDArray[np.float64],
    selected: NDArray[np.int64],
    *,
    n_selected: int,
) -> tuple[float, float, float]:
    """Return oracle recall, simple regret and selected mean latent field efficacy."""
    oracle = np.argsort(true_efficacy)[-n_selected:]
    selected_set = set(int(index) for index in selected)
    oracle_set = set(int(index) for index in oracle)
    recall = len(selected_set.intersection(oracle_set)) / n_selected
    oracle_mean = float(np.mean(true_efficacy[oracle]))
    selected_mean = float(np.mean(true_efficacy[selected]))
    return float(recall), float(oracle_mean - selected_mean), selected_mean


def simulate_screening_policies(
    models: CalibrationModels,
    *,
    config: MultiFidelityConfig,
) -> pd.DataFrame:
    """Evaluate equal-budget field-only, lab->field and full multi-fidelity policies.

    Every rollout uses common candidate truth and observations across policies. Field-only chooses
    its test set at random because, by definition, it has no lower-fidelity evidence with which to
    screen candidates. The other policies may use only evidence available at their current stage.
    """
    _ = config.common_budget  # Validate equal-budget accounting before simulation.
    rng = np.random.default_rng(config.seed + 17)
    records: list[dict[str, float | int | str]] = []

    for rollout in range(config.n_rollouts):
        cohort = simulate_candidate_cohort(
            config.n_candidates,
            n_lab_replicates=config.lab_replicates,
            n_glasshouse_replicates=config.glasshouse_replicates,
            n_field_replicates=config.field_replicates,
            rng=rng,
        )
        theta = cohort.true_field_efficacy
        lab_mean = cohort.lab.mean(axis=1)
        glasshouse_mean = cohort.glasshouse.mean(axis=1)
        field_mean = cohort.field.mean(axis=1)

        # Field-only: no cheap information is available before choosing which candidates to field.
        field_only_tested = rng.choice(
            config.n_candidates,
            size=config.n_field_field_only,
            replace=False,
        ).astype(np.int64)
        field_only_selected = field_only_tested[
            np.argsort(field_mean[field_only_tested])[-config.n_selected :]
        ]

        # Lab -> field: all candidates are screened by lab calibration before field progression.
        lab_pred = models.lab_to_field.predict(lab_mean.reshape(-1, 1))
        lab_field_tested = np.argsort(lab_pred)[-config.n_field_lab_field :].astype(np.int64)
        lab_field_selected = lab_field_tested[
            np.argsort(field_mean[lab_field_tested])[-config.n_selected :]
        ]

        # Multi-fidelity: lab screening narrows the set, glasshouse evidence refines progression,
        # then only the most promising candidates consume expensive field replicates.
        glasshouse_set = np.argsort(lab_pred)[-config.n_glasshouse_multifidelity :].astype(np.int64)
        combined_features = np.column_stack(
            [lab_mean[glasshouse_set], glasshouse_mean[glasshouse_set]]
        )
        combined_pred = models.lab_glasshouse_to_field.predict(combined_features)
        multifidelity_tested = glasshouse_set[
            np.argsort(combined_pred)[-config.n_field_multifidelity :]
        ]
        multifidelity_selected = multifidelity_tested[
            np.argsort(field_mean[multifidelity_tested])[-config.n_selected :]
        ]

        for policy, selected in (
            ("field_only", field_only_selected),
            ("lab_field", lab_field_selected),
            ("multifidelity", multifidelity_selected),
        ):
            recall, regret, selected_mean = _selection_metrics(
                theta,
                selected,
                n_selected=config.n_selected,
            )
            records.append(
                {
                    "rollout": rollout,
                    "policy": policy,
                    "oracle_top_k_recall": recall,
                    "simple_regret_field_efficacy": regret,
                    "selected_mean_true_field_efficacy": selected_mean,
                }
            )
    return pd.DataFrame.from_records(records)


def summarise_screening_policies(rollouts: pd.DataFrame) -> pd.DataFrame:
    """Summarise rollout means and Monte Carlo standard errors by policy."""
    required = {
        "rollout",
        "policy",
        "oracle_top_k_recall",
        "simple_regret_field_efficacy",
        "selected_mean_true_field_efficacy",
    }
    missing = required.difference(rollouts.columns)
    if missing:
        raise ValueError(f"Missing rollout columns: {sorted(missing)}")
    rows: list[dict[str, float | int | str]] = []
    for policy, group in rollouts.groupby("policy", observed=True):
        n = len(group)
        row: dict[str, float | int | str] = {"policy": str(policy), "n_rollouts": n}
        for metric in (
            "oracle_top_k_recall",
            "simple_regret_field_efficacy",
            "selected_mean_true_field_efficacy",
        ):
            values = group[metric].to_numpy(dtype=np.float64)
            row[f"mean_{metric}"] = float(np.mean(values))
            row[f"mcse_{metric}"] = float(np.std(values, ddof=1) / np.sqrt(n))
        rows.append(row)
    return pd.DataFrame.from_records(rows).sort_values("policy").reset_index(drop=True)


def paired_policy_difference(
    rollouts: pd.DataFrame,
    *,
    policy_a: PolicyName,
    policy_b: PolicyName,
    metric: str,
) -> dict[str, float]:
    """Return paired Monte Carlo difference ``policy_a - policy_b`` for one metric."""
    pivot = rollouts.pivot(index="rollout", columns="policy", values=metric)
    if policy_a not in pivot or policy_b not in pivot:
        raise ValueError("Both policies must be present in rollout results.")
    difference = (pivot[policy_a] - pivot[policy_b]).to_numpy(dtype=np.float64)
    mean = float(np.mean(difference))
    mcse = float(np.std(difference, ddof=1) / np.sqrt(len(difference)))
    return {
        "mean_difference": mean,
        "mc_standard_error": mcse,
        "mc95_low": mean - 1.96 * mcse,
        "mc95_high": mean + 1.96 * mcse,
    }
