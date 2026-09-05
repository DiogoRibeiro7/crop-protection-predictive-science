"""Budget-constrained Crop Protection R&D portfolio decisions under uncertainty.

This controlled experiment adds a portfolio layer above the multi-fidelity candidate-screening case.
Each candidate has uncertain efficacy and safety-margin states, a known development reward, and a
known downstream development cost. Initial laboratory evidence is available for every candidate.
A fixed follow-up experimental budget can then be spent on either efficacy confirmation or safety
confirmation before a final set of candidates is advanced.

The terminal advancement problem is solved exactly as a count-and-budget 0/1 knapsack. Adaptive
experiment allocation is deliberately cheaper: it uses either technical-success entropy reduction
or a transparent decision-boundary expected-value-of-sample-information (EVSI) approximation.
The numerical results are properties of the explicit synthetic DGP, not claims about a real
commercial Crop Protection portfolio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, cast

import numpy as np
import pandas as pd
from numpy.polynomial.hermite import hermgauss
from numpy.typing import NDArray
from scipy.special import ndtr

PortfolioPolicy = Literal["no_followup", "uniform", "uncertainty", "portfolio_voi"]
ExperimentType = Literal["efficacy", "safety"]

_DEFAULT_SEED: Final[int] = 20260828


@dataclass(frozen=True)
class FollowUpExperiment:
    """One follow-up experiment type in the controlled portfolio problem."""

    name: ExperimentType
    cost_units: int
    noise_sd: float

    def __post_init__(self) -> None:
        if self.cost_units <= 0:
            raise ValueError("Experiment cost must be positive.")
        if self.noise_sd <= 0.0:
            raise ValueError("Experiment noise_sd must be positive.")


@dataclass(frozen=True)
class PortfolioConfig:
    """Locked design for the portfolio-level decision experiment."""

    n_candidates: int = 36
    max_advanced: int = 6
    downstream_budget_units: int = 130
    followup_budget_units: int = 24
    n_rollouts: int = 500
    prior_mean_efficacy: float = 0.0
    prior_mean_safety: float = 0.0
    prior_sd: float = 1.2
    lab_efficacy_noise_sd: float = 1.0
    lab_safety_noise_sd: float = 1.15
    efficacy_success_threshold: float = 0.0
    safety_success_threshold: float = 0.0
    quadrature_nodes: int = 15
    seed: int = _DEFAULT_SEED
    efficacy_followup: FollowUpExperiment = FollowUpExperiment("efficacy", 4, 0.45)
    safety_followup: FollowUpExperiment = FollowUpExperiment("safety", 2, 0.50)

    def __post_init__(self) -> None:
        count_values = (
            self.n_candidates,
            self.max_advanced,
            self.downstream_budget_units,
            self.followup_budget_units,
            self.n_rollouts,
            self.quadrature_nodes,
        )
        if min(count_values) <= 0:
            raise ValueError("All count and budget parameters must be positive.")
        if self.max_advanced >= self.n_candidates:
            raise ValueError("max_advanced must be smaller than n_candidates.")
        if self.prior_sd <= 0.0:
            raise ValueError("prior_sd must be positive.")
        if min(self.lab_efficacy_noise_sd, self.lab_safety_noise_sd) <= 0.0:
            raise ValueError("Laboratory noise scales must be positive.")
        costs = (self.efficacy_followup.cost_units, self.safety_followup.cost_units)
        if self.followup_budget_units % min(costs) != 0:
            raise ValueError("Follow-up budget must be exactly spendable with the cheapest action.")


@dataclass(frozen=True)
class PortfolioCohort:
    """Latent candidate states plus common noisy evidence streams used by every policy."""

    efficacy: NDArray[np.float64]
    safety_margin: NDArray[np.float64]
    reward_if_success: NDArray[np.float64]
    development_cost: NDArray[np.int64]
    lab_efficacy: NDArray[np.float64]
    lab_safety: NDArray[np.float64]
    efficacy_followups: NDArray[np.float64]
    safety_followups: NDArray[np.float64]

    def __post_init__(self) -> None:
        n = self.efficacy.shape[0]
        one_dimensional = {
            "efficacy": self.efficacy,
            "safety_margin": self.safety_margin,
            "reward_if_success": self.reward_if_success,
            "development_cost": self.development_cost,
            "lab_efficacy": self.lab_efficacy,
            "lab_safety": self.lab_safety,
        }
        for name, values in one_dimensional.items():
            if values.ndim != 1 or values.shape[0] != n:
                raise ValueError(f"{name} must be one-dimensional with one row per candidate.")
            if not np.isfinite(values).all():
                raise ValueError(f"{name} contains non-finite values.")
        for name, values in (
            ("efficacy_followups", self.efficacy_followups),
            ("safety_followups", self.safety_followups),
        ):
            if values.ndim != 2 or values.shape[0] != n:
                raise ValueError(f"{name} must be 2D with one row per candidate.")
            if not np.isfinite(values).all():
                raise ValueError(f"{name} contains non-finite values.")
        if np.any(self.development_cost <= 0):
            raise ValueError("Development costs must be positive.")
        if np.any(self.reward_if_success <= 0.0):
            raise ValueError("Success rewards must be positive.")

    @property
    def n_candidates(self) -> int:
        """Return cohort size."""
        return int(self.efficacy.shape[0])

    def technical_success(self, config: PortfolioConfig) -> NDArray[np.bool_]:
        """Return latent technical-success indicators used only for controlled evaluation."""
        return (self.efficacy > config.efficacy_success_threshold) & (
            self.safety_margin > config.safety_success_threshold
        )


@dataclass
class PosteriorState:
    """Independent Gaussian posterior state for candidate efficacy and safety margins."""

    efficacy_mean: NDArray[np.float64]
    efficacy_var: NDArray[np.float64]
    safety_mean: NDArray[np.float64]
    safety_var: NDArray[np.float64]

    def copy(self) -> PosteriorState:
        """Deep-copy arrays so each policy evolves independently from common initial evidence."""
        return PosteriorState(
            self.efficacy_mean.copy(),
            self.efficacy_var.copy(),
            self.safety_mean.copy(),
            self.safety_var.copy(),
        )


def simulate_portfolio_cohort(
    config: PortfolioConfig,
    *,
    rng: np.random.Generator,
) -> PortfolioCohort:
    """Simulate one candidate portfolio and all evidence streams needed by adaptive policies."""
    n = config.n_candidates
    efficacy = rng.normal(0.35, 1.0, n).astype(np.float64)
    safety = rng.normal(0.25, 1.0, n).astype(np.float64)

    # Reward and downstream development cost are treated as known portfolio attributes. They are
    # deliberately heterogeneous so the final decision is not equivalent to efficacy ranking.
    reward = rng.uniform(45.0, 110.0, n).astype(np.float64)
    development_cost = rng.integers(15, 36, n, dtype=np.int64)

    lab_efficacy = (
        efficacy + rng.normal(0.0, config.lab_efficacy_noise_sd, n)
    ).astype(np.float64)
    lab_safety = (safety + rng.normal(0.0, config.lab_safety_noise_sd, n)).astype(np.float64)

    max_efficacy = config.followup_budget_units // config.efficacy_followup.cost_units
    max_safety = config.followup_budget_units // config.safety_followup.cost_units
    efficacy_followups = np.column_stack(
        [
            efficacy + rng.normal(0.0, config.efficacy_followup.noise_sd, n)
            for _ in range(max_efficacy)
        ]
    ).astype(np.float64)
    safety_followups = np.column_stack(
        [
            safety + rng.normal(0.0, config.safety_followup.noise_sd, n)
            for _ in range(max_safety)
        ]
    ).astype(np.float64)
    return PortfolioCohort(
        efficacy=efficacy,
        safety_margin=safety,
        reward_if_success=reward,
        development_cost=development_cost,
        lab_efficacy=lab_efficacy,
        lab_safety=lab_safety,
        efficacy_followups=efficacy_followups,
        safety_followups=safety_followups,
    )


def _normal_update(
    mean: NDArray[np.float64],
    var: NDArray[np.float64],
    observation: NDArray[np.float64],
    noise_var: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Conjugate Gaussian update with known observation variance."""
    if noise_var <= 0.0:
        raise ValueError("noise_var must be positive.")
    posterior_var = 1.0 / (1.0 / var + 1.0 / noise_var)
    posterior_mean = posterior_var * (mean / var + observation / noise_var)
    return posterior_mean.astype(np.float64), posterior_var.astype(np.float64)


def initial_posterior(cohort: PortfolioCohort, config: PortfolioConfig) -> PosteriorState:
    """Build candidate posteriors after the common initial laboratory screen."""
    prior_var = config.prior_sd**2
    n = cohort.n_candidates
    efficacy_mean, efficacy_var = _normal_update(
        np.full(n, config.prior_mean_efficacy, dtype=np.float64),
        np.full(n, prior_var, dtype=np.float64),
        cohort.lab_efficacy,
        config.lab_efficacy_noise_sd**2,
    )
    safety_mean, safety_var = _normal_update(
        np.full(n, config.prior_mean_safety, dtype=np.float64),
        np.full(n, prior_var, dtype=np.float64),
        cohort.lab_safety,
        config.lab_safety_noise_sd**2,
    )
    return PosteriorState(efficacy_mean, efficacy_var, safety_mean, safety_var)


def technical_success_probability(
    state: PosteriorState,
    config: PortfolioConfig,
) -> NDArray[np.float64]:
    """Posterior probability that both efficacy and safety thresholds are exceeded."""
    efficacy_z = (state.efficacy_mean - config.efficacy_success_threshold) / np.sqrt(
        state.efficacy_var
    )
    safety_z = (state.safety_mean - config.safety_success_threshold) / np.sqrt(state.safety_var)
    return cast(
        NDArray[np.float64],
        (ndtr(efficacy_z) * ndtr(safety_z)).astype(np.float64),
    )


def expected_development_value(
    state: PosteriorState,
    cohort: PortfolioCohort,
    config: PortfolioConfig,
) -> NDArray[np.float64]:
    """Posterior expected net development value for advancing each candidate."""
    p_success = technical_success_probability(state, config)
    return p_success * cohort.reward_if_success - cohort.development_cost


def solve_budgeted_portfolio(
    candidate_value: NDArray[np.float64],
    development_cost: NDArray[np.int64],
    *,
    budget_units: int,
    max_advanced: int,
) -> tuple[NDArray[np.int64], float]:
    """Solve the terminal count-and-budget 0/1 knapsack exactly by dynamic programming."""
    if candidate_value.ndim != 1 or development_cost.ndim != 1:
        raise ValueError("candidate_value and development_cost must be one-dimensional.")
    if candidate_value.shape[0] != development_cost.shape[0]:
        raise ValueError("candidate_value and development_cost must have equal length.")
    if budget_units <= 0 or max_advanced <= 0:
        raise ValueError("budget_units and max_advanced must be positive.")
    if np.any(development_cost <= 0):
        raise ValueError("development_cost must be positive.")

    n = candidate_value.shape[0]
    dp = np.full((n + 1, max_advanced + 1, budget_units + 1), -np.inf, dtype=np.float64)
    dp[0, 0, :] = 0.0
    for i in range(1, n + 1):
        dp[i] = dp[i - 1]
        value = float(candidate_value[i - 1])
        cost = int(development_cost[i - 1])
        if value <= 0.0 or cost > budget_units:
            continue
        for k in range(1, max_advanced + 1):
            proposal = dp[i - 1, k - 1, : budget_units + 1 - cost] + value
            target = dp[i, k, cost:]
            mask = proposal > target
            target[mask] = proposal[mask]

    final_k, final_budget = np.unravel_index(np.argmax(dp[n]), dp[n].shape)
    best_value = float(dp[n, final_k, final_budget])
    selected: list[int] = []
    k = int(final_k)
    budget = int(final_budget)
    for i in range(n, 0, -1):
        value = float(candidate_value[i - 1])
        cost = int(development_cost[i - 1])
        if value <= 0.0 or k <= 0 or budget < cost:
            continue
        previous = dp[i - 1, k - 1, budget - cost]
        # Require strict improvement over the state that skips the item to resolve ties
        # deterministically in favour of the smaller portfolio.
        if (
            np.isfinite(previous)
            and np.isclose(dp[i, k, budget], previous + value)
            and dp[i, k, budget] > dp[i - 1, k, budget] + 1e-12
        ):
            selected.append(i - 1)
            k -= 1
            budget -= cost
    selected.reverse()
    return np.asarray(selected, dtype=np.int64), best_value


def _bernoulli_entropy(probability: NDArray[np.float64]) -> NDArray[np.float64]:
    """Natural-log Bernoulli entropy with stable clipping at the boundaries."""
    p = np.clip(probability, 1e-12, 1.0 - 1e-12)
    return cast(
        NDArray[np.float64],
        -(p * np.log(p) + (1.0 - p) * np.log(1.0 - p)),
    )


def _portfolio_ratio_threshold(
    state: PosteriorState,
    cohort: PortfolioCohort,
    config: PortfolioConfig,
) -> float:
    """Approximate the current portfolio boundary by a value-per-cost shadow threshold."""
    expected_value = expected_development_value(state, cohort, config)
    ratio = expected_value / cohort.development_cost

    # Acquisition uses a fast Lagrangian-style boundary approximation, not another exact knapsack
    # solve for every hypothetical measurement. Candidates are greedily packed by expected
    # value-per-cost only to estimate the current shadow threshold. The terminal advancement
    # decision remains the exact dynamic-programming solution.
    order = np.argsort(ratio)[::-1]
    selected: list[int] = []
    spent = 0
    for candidate in order:
        if ratio[candidate] <= 0.0 or len(selected) >= config.max_advanced:
            break
        cost = int(cohort.development_cost[candidate])
        if spent + cost <= config.downstream_budget_units:
            selected.append(int(candidate))
            spent += cost
    if not selected:
        return max(0.0, float(np.max(ratio)))

    selected_array = np.asarray(selected, dtype=np.int64)
    selected_mask = np.zeros(cohort.n_candidates, dtype=bool)
    selected_mask[selected_array] = True
    selected_floor = float(np.min(ratio[selected_array]))
    if np.all(selected_mask):
        return max(0.0, selected_floor)
    excluded_ceiling = float(np.max(ratio[~selected_mask]))
    return max(0.0, 0.5 * (selected_floor + excluded_ceiling))


def acquisition_scores(
    state: PosteriorState,
    cohort: PortfolioCohort,
    config: PortfolioConfig,
    experiment: FollowUpExperiment,
) -> pd.DataFrame:
    """Return deterministic uncertainty and decision-EVSI scores for one experiment type.

    Expected utilities are integrated with Gauss-Hermite quadrature. Under conjugate Normal
    updating, the future posterior mean conditional on current information is Normal with variance
    equal to ``current_var - future_var``. This removes Monte Carlo noise from experiment ranking.

    ``decision_evsi_per_cost`` is intentionally an acquisition approximation. It values the option
    to cross the current value-per-development-cost portfolio boundary after observing one more
    experiment. The final advancement set is still solved by the exact knapsack above.
    """
    nodes, weights = hermgauss(config.quadrature_nodes)
    weights = weights / np.sqrt(np.pi)
    noise_var = experiment.noise_sd**2
    p_current = technical_success_probability(state, config)
    current_value = p_current * cohort.reward_if_success - cohort.development_cost
    current_ratio = current_value / cohort.development_cost
    threshold = _portfolio_ratio_threshold(state, cohort, config)

    if experiment.name == "efficacy":
        current_mean = state.efficacy_mean
        current_var = state.efficacy_var
    else:
        current_mean = state.safety_mean
        current_var = state.safety_var
    future_var = 1.0 / (1.0 / current_var + 1.0 / noise_var)
    mean_variance = np.maximum(current_var - future_var, 0.0)
    future_mean = current_mean[:, None] + np.sqrt(2.0 * mean_variance)[:, None] * nodes[None, :]

    if experiment.name == "efficacy":
        efficacy_probability = ndtr(
            (future_mean - config.efficacy_success_threshold) / np.sqrt(future_var)[:, None]
        )
        safety_probability = ndtr(
            (state.safety_mean - config.safety_success_threshold) / np.sqrt(state.safety_var)
        )[:, None]
    else:
        efficacy_probability = ndtr(
            (state.efficacy_mean - config.efficacy_success_threshold)
            / np.sqrt(state.efficacy_var)
        )[:, None]
        safety_probability = ndtr(
            (future_mean - config.safety_success_threshold) / np.sqrt(future_var)[:, None]
        )
    future_success_probability = efficacy_probability * safety_probability

    expected_entropy = np.sum(
        _bernoulli_entropy(future_success_probability) * weights[None, :], axis=1
    )
    entropy_gain = np.maximum(_bernoulli_entropy(p_current) - expected_entropy, 0.0)

    future_value = (
        future_success_probability * cohort.reward_if_success[:, None]
        - cohort.development_cost[:, None]
    )
    future_ratio = future_value / cohort.development_cost[:, None]
    future_positive_margin = np.maximum(future_ratio - threshold, 0.0)
    expected_positive_margin = np.sum(future_positive_margin * weights[None, :], axis=1)
    current_positive_margin = np.maximum(current_ratio - threshold, 0.0)
    decision_evsi = np.maximum(expected_positive_margin - current_positive_margin, 0.0)

    return pd.DataFrame(
        {
            "candidate": np.arange(cohort.n_candidates, dtype=np.int64),
            "experiment": experiment.name,
            "experiment_cost_units": experiment.cost_units,
            "technical_success_probability": p_current,
            "entropy_gain_per_cost": entropy_gain / experiment.cost_units,
            "decision_evsi_per_cost": decision_evsi / experiment.cost_units,
            "portfolio_ratio_threshold": threshold,
        }
    )


def _apply_followup(
    state: PosteriorState,
    cohort: PortfolioCohort,
    *,
    candidate: int,
    experiment: FollowUpExperiment,
    replicate_index: int,
) -> None:
    """Update one candidate posterior using a pre-generated common-random-number replicate."""
    index = np.asarray([candidate], dtype=np.int64)
    noise_var = experiment.noise_sd**2
    if experiment.name == "efficacy":
        observation = np.asarray([cohort.efficacy_followups[candidate, replicate_index]])
        mean, var = _normal_update(
            state.efficacy_mean[index], state.efficacy_var[index], observation, noise_var
        )
        state.efficacy_mean[candidate] = mean[0]
        state.efficacy_var[candidate] = var[0]
    else:
        observation = np.asarray([cohort.safety_followups[candidate, replicate_index]])
        mean, var = _normal_update(
            state.safety_mean[index], state.safety_var[index], observation, noise_var
        )
        state.safety_mean[candidate] = mean[0]
        state.safety_var[candidate] = var[0]


def _uniform_action_plan(
    cohort: PortfolioCohort,
    config: PortfolioConfig,
    *,
    rng: np.random.Generator,
) -> list[tuple[int, FollowUpExperiment]]:
    """Construct an outcome-independent balanced follow-up plan with exact budget use."""
    plan: list[tuple[int, FollowUpExperiment]] = []
    remaining = config.followup_budget_units
    permutation = rng.permutation(cohort.n_candidates)
    pointer = 0
    prefer_efficacy = True
    while remaining > 0:
        candidate = int(permutation[pointer % cohort.n_candidates])
        pointer += 1
        if prefer_efficacy and remaining >= config.efficacy_followup.cost_units:
            experiment = config.efficacy_followup
        else:
            experiment = config.safety_followup
        if experiment.cost_units > remaining:
            experiment = config.safety_followup
        plan.append((candidate, experiment))
        remaining -= experiment.cost_units
        prefer_efficacy = not prefer_efficacy
    return plan


def run_followup_policy(
    cohort: PortfolioCohort,
    config: PortfolioConfig,
    *,
    policy: PortfolioPolicy,
    uniform_rng: np.random.Generator,
) -> dict[str, float | int | str]:
    """Run one follow-up allocation policy and make the exact terminal advancement decision."""
    state = initial_posterior(cohort, config)
    efficacy_counts = np.zeros(cohort.n_candidates, dtype=np.int64)
    safety_counts = np.zeros(cohort.n_candidates, dtype=np.int64)
    spent = 0

    uniform_plan = (
        _uniform_action_plan(cohort, config, rng=uniform_rng) if policy == "uniform" else []
    )
    uniform_pointer = 0
    while policy != "no_followup" and spent < config.followup_budget_units:
        remaining = config.followup_budget_units - spent
        eligible: list[FollowUpExperiment] = []
        if config.efficacy_followup.cost_units <= remaining:
            eligible.append(config.efficacy_followup)
        if config.safety_followup.cost_units <= remaining:
            eligible.append(config.safety_followup)
        if not eligible:
            break

        if policy == "uniform":
            candidate, experiment = uniform_plan[uniform_pointer]
            uniform_pointer += 1
        else:
            best_score = -np.inf
            candidate = 0
            experiment = eligible[0]
            score_column = (
                "entropy_gain_per_cost" if policy == "uncertainty" else "decision_evsi_per_cost"
            )
            for candidate_experiment in eligible:
                scores = acquisition_scores(state, cohort, config, candidate_experiment)
                index = int(scores[score_column].idxmax())
                score = float(scores.loc[index, score_column])
                if score > best_score:
                    best_score = score
                    candidate = int(scores.loc[index, "candidate"])
                    experiment = candidate_experiment

        if experiment.name == "efficacy":
            replicate_index = int(efficacy_counts[candidate])
            _apply_followup(
                state,
                cohort,
                candidate=candidate,
                experiment=experiment,
                replicate_index=replicate_index,
            )
            efficacy_counts[candidate] += 1
        else:
            replicate_index = int(safety_counts[candidate])
            _apply_followup(
                state,
                cohort,
                candidate=candidate,
                experiment=experiment,
                replicate_index=replicate_index,
            )
            safety_counts[candidate] += 1
        spent += experiment.cost_units

    posterior_value = expected_development_value(state, cohort, config)
    selected, expected_objective = solve_budgeted_portfolio(
        posterior_value,
        cohort.development_cost,
        budget_units=config.downstream_budget_units,
        max_advanced=config.max_advanced,
    )
    technical_success = cohort.technical_success(config)
    realised_candidate_value = (
        technical_success.astype(np.float64) * cohort.reward_if_success - cohort.development_cost
    )
    oracle_selected, oracle_value = solve_budgeted_portfolio(
        realised_candidate_value,
        cohort.development_cost,
        budget_units=config.downstream_budget_units,
        max_advanced=config.max_advanced,
    )
    realised_value = float(np.sum(realised_candidate_value[selected]))
    selected_success_rate = (
        float(np.mean(technical_success[selected])) if selected.size > 0 else 0.0
    )
    return {
        "policy": policy,
        "followup_cost_units": spent,
        "n_efficacy_followups": int(np.sum(efficacy_counts)),
        "n_safety_followups": int(np.sum(safety_counts)),
        "n_advanced": int(selected.size),
        "downstream_cost_units": int(np.sum(cohort.development_cost[selected])),
        "posterior_expected_portfolio_value": float(expected_objective),
        "realised_portfolio_value": realised_value,
        "oracle_portfolio_value": float(oracle_value),
        "oracle_regret": float(oracle_value - realised_value),
        "advanced_technical_success_rate": selected_success_rate,
        "oracle_n_advanced": int(oracle_selected.size),
    }


def simulate_portfolio_policies(config: PortfolioConfig) -> pd.DataFrame:
    """Evaluate all policies on paired candidate cohorts and common evidence streams."""
    cohort_rng = np.random.default_rng(config.seed + 101)
    records: list[dict[str, float | int | str]] = []
    policies: tuple[PortfolioPolicy, ...] = (
        "no_followup",
        "uniform",
        "uncertainty",
        "portfolio_voi",
    )
    for rollout in range(config.n_rollouts):
        cohort = simulate_portfolio_cohort(config, rng=cohort_rng)
        for policy_index, policy in enumerate(policies):
            uniform_rng = np.random.default_rng(config.seed + 10_000 * rollout + policy_index)
            result = run_followup_policy(
                cohort,
                config,
                policy=policy,
                uniform_rng=uniform_rng,
            )
            records.append({"rollout": rollout, **result})
    return pd.DataFrame.from_records(records)


def summarise_portfolio_policies(rollouts: pd.DataFrame) -> pd.DataFrame:
    """Summarise portfolio outcomes and Monte Carlo standard errors by policy."""
    required = {
        "rollout",
        "policy",
        "followup_cost_units",
        "realised_portfolio_value",
        "oracle_regret",
        "advanced_technical_success_rate",
    }
    missing = required.difference(rollouts.columns)
    if missing:
        raise ValueError(f"Missing rollout columns: {sorted(missing)}")
    metrics = (
        "followup_cost_units",
        "n_efficacy_followups",
        "n_safety_followups",
        "n_advanced",
        "downstream_cost_units",
        "posterior_expected_portfolio_value",
        "realised_portfolio_value",
        "oracle_portfolio_value",
        "oracle_regret",
        "advanced_technical_success_rate",
    )
    records: list[dict[str, float | int | str]] = []
    for policy, group in rollouts.groupby("policy", observed=True):
        n = len(group)
        row: dict[str, float | int | str] = {"policy": str(policy), "n_rollouts": n}
        for metric in metrics:
            values = group[metric].to_numpy(dtype=np.float64)
            row[f"mean_{metric}"] = float(np.mean(values))
            row[f"mcse_{metric}"] = float(np.std(values, ddof=1) / np.sqrt(n))
        records.append(row)
    return pd.DataFrame.from_records(records).sort_values("policy").reset_index(drop=True)


def paired_portfolio_difference(
    rollouts: pd.DataFrame,
    *,
    policy_a: PortfolioPolicy,
    policy_b: PortfolioPolicy,
    metric: str,
) -> dict[str, float]:
    """Return paired Monte Carlo difference ``policy_a - policy_b`` for one metric."""
    pivot = rollouts.pivot(index="rollout", columns="policy", values=metric)
    if policy_a not in pivot or policy_b not in pivot:
        raise ValueError("Both policies must be present in rollout results.")
    difference = (pivot[policy_a] - pivot[policy_b]).to_numpy(dtype=np.float64)
    mean = float(np.mean(difference))
    mcse = float(np.std(difference, ddof=1) / np.sqrt(difference.size))
    return {
        "mean_difference": mean,
        "mc_standard_error": mcse,
        "mc95_low": mean - 1.96 * mcse,
        "mc95_high": mean + 1.96 * mcse,
    }
