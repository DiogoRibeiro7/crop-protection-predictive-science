"""Decision-aware adaptive replication for Crop Protection field trials.

The module treats each fungicide timing contrast as a scalar Bayesian decision problem. A new
experimental unit is a *paired block*: one Early and one Late plot for the same product in the same
block, producing a noisy observation of the Late-minus-Early contrast on the sqrt(AUDPC) scale.

The goal is not generic parameter estimation. The scientific decision is whether Early or Late
application has lower expected disease burden for each product. Candidate replication is therefore
ranked by the expected reduction in posterior entropy of the sign of that contrast.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt
from typing import Final, Literal, Mapping, Sequence

import numpy as np
import pandas as pd
from numpy.polynomial.hermite import hermgauss
from numpy.typing import NDArray
from scipy.special import ndtr

PolicyName = Literal["uniform", "parameter_eig", "decision_eig"]

_FLOAT_EPS: Final[float] = 1.0e-12
_ENTROPY_EPS: Final[float] = 1.0e-15
_DEFAULT_QUADRATURE_NODES: Final[int] = 21


@dataclass(frozen=True)
class NormalTimingBelief:
    """Normal approximation for one product-specific Late-minus-Early timing effect.

    Parameters
    ----------
    mean:
        Posterior mean of the treatment contrast on the sqrt(AUDPC) scale. Positive values imply
        more disease under Late timing and therefore favour Early timing.
    variance:
        Posterior variance of the latent product-specific contrast.
    observation_variance:
        Predictive variance of a new paired-block contrast around the latent effect.
    """

    mean: float
    variance: float
    observation_variance: float

    def __post_init__(self) -> None:
        values = (self.mean, self.variance, self.observation_variance)
        if not all(np.isfinite(value) for value in values):
            raise ValueError("Belief parameters must be finite.")
        if self.variance <= 0.0:
            raise ValueError("Posterior variance must be positive.")
        if self.observation_variance <= 0.0:
            raise ValueError("Observation variance must be positive.")


@dataclass(frozen=True)
class AdaptiveSimulationConfig:
    """Configuration for reproducible pre-posterior policy evaluation."""

    n_rollouts: int = 10_000
    max_budget: int = 20
    checkpoints: tuple[int, ...] = (0, 5, 10, 15, 20)
    seed: int = 20260828

    def __post_init__(self) -> None:
        if self.n_rollouts < 500:
            raise ValueError("n_rollouts must be at least 500 for stable policy summaries.")
        if self.max_budget < 1:
            raise ValueError("max_budget must be positive.")
        if not self.checkpoints:
            raise ValueError("At least one checkpoint is required.")
        if any(value < 0 or value > self.max_budget for value in self.checkpoints):
            raise ValueError("Checkpoints must lie between zero and max_budget.")
        if tuple(sorted(set(self.checkpoints))) != self.checkpoints:
            raise ValueError("Checkpoints must be unique and sorted.")


@dataclass(frozen=True)
class AdaptivePolicyResult:
    """Monte Carlo policy trajectories and average replication allocations."""

    rollout_metrics: pd.DataFrame
    allocation_paths: pd.DataFrame


def _binary_entropy(probability: NDArray[np.float64] | float) -> NDArray[np.float64] | float:
    """Return binary entropy in nats, numerically stabilised near zero and one."""
    values = np.asarray(probability, dtype=np.float64)
    clipped = np.clip(values, _ENTROPY_EPS, 1.0 - _ENTROPY_EPS)
    entropy = -(clipped * np.log(clipped) + (1.0 - clipped) * np.log1p(-clipped))
    if np.isscalar(probability):
        return float(entropy.item())
    return entropy


def posterior_sign_probability(belief: NormalTimingBelief) -> float:
    """Return ``P(Late - Early > 0)`` under a normal posterior approximation."""
    return float(ndtr(belief.mean / sqrt(belief.variance)))


def sign_entropy(belief: NormalTimingBelief) -> float:
    """Return posterior uncertainty about which timing has lower disease burden."""
    return float(_binary_entropy(posterior_sign_probability(belief)))


def bayes_timing_regret(belief: NormalTimingBelief) -> float:
    """Expected regret of the posterior-optimal Early/Late decision.

    Loss is the magnitude of the latent timing contrast when the selected sign is wrong. The units
    are therefore sqrt(AUDPC), not money or a regulatory utility.
    """
    sd = sqrt(belief.variance)
    z = belief.mean / sd
    density = np.exp(-0.5 * z * z) / sqrt(2.0 * pi)
    cdf = float(ndtr(z))
    regret_if_late = sd * density + belief.mean * cdf
    regret_if_early = sd * density - belief.mean * (1.0 - cdf)
    return float(min(regret_if_early, regret_if_late))


def update_normal_belief(belief: NormalTimingBelief, observation: float) -> NormalTimingBelief:
    """Apply a conjugate Normal-Normal update for one new paired-block contrast."""
    if not np.isfinite(observation):
        raise ValueError("Observation must be finite.")
    posterior_variance = 1.0 / (
        1.0 / belief.variance + 1.0 / belief.observation_variance
    )
    posterior_mean = posterior_variance * (
        belief.mean / belief.variance + observation / belief.observation_variance
    )
    return NormalTimingBelief(
        mean=float(posterior_mean),
        variance=float(posterior_variance),
        observation_variance=belief.observation_variance,
    )


def parameter_information_gain(belief: NormalTimingBelief) -> float:
    """Expected information gain about the continuous timing effect from one paired block."""
    return float(0.5 * np.log1p(belief.variance / belief.observation_variance))


def sign_information_gain(
    belief: NormalTimingBelief,
    *,
    quadrature_nodes: int = _DEFAULT_QUADRATURE_NODES,
) -> float:
    """Expected reduction in entropy of the sign of the timing contrast.

    The posterior variance after one normal observation is deterministic. The posterior mean before
    observing the new result follows a normal pre-posterior distribution. Gauss-Hermite quadrature
    therefore gives a fast deterministic approximation to

    ``H(sign(theta) | D) - E_y[H(sign(theta) | D, y)]``.
    """
    if quadrature_nodes < 9:
        raise ValueError("quadrature_nodes must be at least 9.")
    posterior_variance = 1.0 / (
        1.0 / belief.variance + 1.0 / belief.observation_variance
    )
    preposterior_variance = max(belief.variance - posterior_variance, 0.0)
    nodes, weights = hermgauss(quadrature_nodes)
    posterior_means = belief.mean + sqrt(2.0 * preposterior_variance) * nodes
    posterior_positive = ndtr(posterior_means / sqrt(posterior_variance))
    expected_entropy = float(
        np.sum(weights * np.asarray(_binary_entropy(posterior_positive), dtype=np.float64))
        / sqrt(pi)
    )
    gain = sign_entropy(belief) - expected_entropy
    # Small negative values can arise from floating-point quadrature error.
    return float(max(gain, 0.0))


def acquisition_table(beliefs: Mapping[str, NormalTimingBelief]) -> pd.DataFrame:
    """Rank products for one additional paired-block replicate under two design objectives."""
    if not beliefs:
        raise ValueError("At least one timing belief is required.")
    records: list[dict[str, float | str]] = []
    for product in sorted(beliefs):
        belief = beliefs[product]
        probability = posterior_sign_probability(belief)
        records.append(
            {
                "treatment": product,
                "posterior_mean_delta_sqrt_audpc": belief.mean,
                "posterior_sd": sqrt(belief.variance),
                "paired_observation_sd": sqrt(belief.observation_variance),
                "prob_late_greater_disease": probability,
                "prob_wrong_timing_if_act_now": min(probability, 1.0 - probability),
                "sign_entropy_nats": sign_entropy(belief),
                "parameter_eig_nats": parameter_information_gain(belief),
                "decision_sign_eig_nats": sign_information_gain(belief),
                "bayes_regret_sqrt_audpc": bayes_timing_regret(belief),
            }
        )
    frame = pd.DataFrame.from_records(records)
    frame["decision_eig_rank"] = (
        frame["decision_sign_eig_nats"].rank(method="first", ascending=False).astype(int)
    )
    frame["parameter_eig_rank"] = (
        frame["parameter_eig_nats"].rank(method="first", ascending=False).astype(int)
    )
    return frame.sort_values("decision_eig_rank").reset_index(drop=True)


def beliefs_from_release_tables(
    posterior_timing: pd.DataFrame,
    paired_summary: pd.DataFrame,
) -> dict[str, NormalTimingBelief]:
    """Build decision beliefs from the v0.3 posterior and empirical paired-block variability."""
    required_posterior = {
        "scope",
        "treatment",
        "posterior_mean_delta_sqrt_audpc",
        "posterior_sd",
    }
    required_pairs = {"treatment", "raw_paired_sd", "n_pairs"}
    missing_posterior = required_posterior.difference(posterior_timing.columns)
    missing_pairs = required_pairs.difference(paired_summary.columns)
    if missing_posterior or missing_pairs:
        raise ValueError(
            "Missing release-table columns: "
            f"posterior={sorted(missing_posterior)}, pairs={sorted(missing_pairs)}"
        )
    product_posterior = posterior_timing.loc[posterior_timing["scope"] == "product"].copy()
    merged = product_posterior.merge(
        paired_summary.loc[:, ["treatment", "raw_paired_sd", "n_pairs"]],
        on="treatment",
        how="inner",
        validate="one_to_one",
    )
    if len(merged) != len(product_posterior):
        raise ValueError("Every product posterior must have a paired-block variability estimate.")
    beliefs: dict[str, NormalTimingBelief] = {}
    for row in merged.itertuples(index=False):
        posterior_sd = float(row.posterior_sd)
        observation_sd = float(row.raw_paired_sd)
        if posterior_sd <= 0.0 or observation_sd <= 0.0:
            raise ValueError("Posterior and paired observation SDs must be positive.")
        beliefs[str(row.treatment)] = NormalTimingBelief(
            mean=float(row.posterior_mean_delta_sqrt_audpc),
            variance=posterior_sd**2,
            observation_variance=observation_sd**2,
        )
    return beliefs


def _vector_entropy(probability: NDArray[np.float64]) -> NDArray[np.float64]:
    """Vector-only entropy helper for pre-posterior policy simulation."""
    return np.asarray(_binary_entropy(probability), dtype=np.float64)


def _vector_bayes_regret(
    mean: NDArray[np.float64],
    variance: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Vectorised posterior-optimal timing regret for rollout matrices."""
    sd = np.sqrt(variance)
    z = mean / sd
    density = np.exp(-0.5 * z * z) / sqrt(2.0 * pi)
    cdf = ndtr(z)
    regret_if_late = sd * density + mean * cdf
    regret_if_early = sd * density - mean * (1.0 - cdf)
    return np.minimum(regret_if_early, regret_if_late)


def _vector_sign_information_gain(
    mean: NDArray[np.float64],
    variance: NDArray[np.float64],
    observation_variance: NDArray[np.float64],
    *,
    quadrature_nodes: int = _DEFAULT_QUADRATURE_NODES,
) -> NDArray[np.float64]:
    """Vectorised decision information gain for rollout × product matrices."""
    nodes, weights = hermgauss(quadrature_nodes)
    weights = weights / sqrt(pi)
    posterior_variance = 1.0 / (
        1.0 / variance + 1.0 / observation_variance[None, :]
    )
    preposterior_sd = np.sqrt(np.maximum(variance - posterior_variance, 0.0))
    posterior_means = (
        mean[:, :, None] + sqrt(2.0) * preposterior_sd[:, :, None] * nodes[None, None, :]
    )
    posterior_positive = ndtr(
        posterior_means / np.sqrt(posterior_variance)[:, :, None]
    )
    expected_entropy = np.sum(
        _vector_entropy(posterior_positive) * weights[None, None, :], axis=2
    )
    current_entropy = _vector_entropy(ndtr(mean / np.sqrt(variance)))
    return np.maximum(current_entropy - expected_entropy, 0.0)


def _record_rollout_state(
    *,
    policy: PolicyName,
    budget: int,
    means: NDArray[np.float64],
    variances: NDArray[np.float64],
    counts: NDArray[np.int64],
    products: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Persist rollout-level decision metrics and allocation counts at one budget checkpoint."""
    probabilities = ndtr(means / np.sqrt(variances))
    metrics = pd.DataFrame(
        {
            "rollout": np.arange(len(means), dtype=int),
            "policy": policy,
            "budget_paired_blocks": int(budget),
            "total_sign_entropy_nats": np.sum(_vector_entropy(probabilities), axis=1),
            "total_bayes_regret_sqrt_audpc": np.sum(
                _vector_bayes_regret(means, variances), axis=1
            ),
            "expected_wrong_timing_decisions": np.sum(
                np.minimum(probabilities, 1.0 - probabilities), axis=1
            ),
        }
    )
    allocation = pd.DataFrame(
        {
            "rollout": np.arange(len(means), dtype=int),
            "policy": policy,
            "budget_paired_blocks": int(budget),
            **{product: counts[:, index] for index, product in enumerate(products)},
        }
    )
    return metrics, allocation


def simulate_adaptive_policies(
    beliefs: Mapping[str, NormalTimingBelief],
    *,
    config: AdaptiveSimulationConfig | None = None,
) -> AdaptivePolicyResult:
    """Evaluate adaptive replication policies by pre-posterior Monte Carlo simulation.

    Each rollout simulates future observations from the current posterior predictive
    distribution. The final metrics are posterior decision quantities, so latent ``truth`` is not
    exposed to the policy and no oracle information is used.

    Policies
    --------
    uniform:
        Round-robin replication across products.
    parameter_eig:
        Select the product with the largest expected information gain about the continuous effect.
    decision_eig:
        Select the product with the largest expected information gain about the sign of the effect,
        i.e. the Early-versus-Late timing decision.
    """
    if not beliefs:
        raise ValueError("At least one timing belief is required.")
    simulation = config or AdaptiveSimulationConfig()
    products = tuple(sorted(beliefs))
    means0 = np.asarray([beliefs[value].mean for value in products], dtype=np.float64)
    variances0 = np.asarray([beliefs[value].variance for value in products], dtype=np.float64)
    observation_variances = np.asarray(
        [beliefs[value].observation_variance for value in products], dtype=np.float64
    )
    if np.any(variances0 <= _FLOAT_EPS) or np.any(observation_variances <= _FLOAT_EPS):
        raise ValueError("All policy variances must be positive.")

    rng = np.random.default_rng(simulation.seed)
    # Common standard-normal draws reduce Monte Carlo noise in policy comparisons.
    standard_normals = rng.standard_normal((simulation.n_rollouts, simulation.max_budget))
    rollout_frames: list[pd.DataFrame] = []
    allocation_frames: list[pd.DataFrame] = []
    policies: tuple[PolicyName, ...] = ("uniform", "parameter_eig", "decision_eig")
    rollout_index = np.arange(simulation.n_rollouts, dtype=int)

    for policy in policies:
        means = np.tile(means0, (simulation.n_rollouts, 1))
        variances = np.tile(variances0, (simulation.n_rollouts, 1))
        counts = np.zeros((simulation.n_rollouts, len(products)), dtype=np.int64)

        if 0 in simulation.checkpoints:
            metrics, allocation = _record_rollout_state(
                policy=policy,
                budget=0,
                means=means,
                variances=variances,
                counts=counts,
                products=products,
            )
            rollout_frames.append(metrics)
            allocation_frames.append(allocation)

        for step in range(simulation.max_budget):
            if policy == "uniform":
                selected = np.full(
                    simulation.n_rollouts, step % len(products), dtype=np.int64
                )
            elif policy == "parameter_eig":
                scores = 0.5 * np.log1p(
                    variances / observation_variances[None, :]
                )
                selected = np.argmax(scores, axis=1).astype(np.int64)
            else:
                scores = _vector_sign_information_gain(
                    means, variances, observation_variances
                )
                selected = np.argmax(scores, axis=1).astype(np.int64)

            selected_mean = means[rollout_index, selected]
            selected_variance = variances[rollout_index, selected]
            selected_observation_variance = observation_variances[selected]
            predictive_sd = np.sqrt(selected_variance + selected_observation_variance)
            observation = (
                selected_mean + predictive_sd * standard_normals[:, step]
            )
            posterior_variance = 1.0 / (
                1.0 / selected_variance + 1.0 / selected_observation_variance
            )
            posterior_mean = posterior_variance * (
                selected_mean / selected_variance
                + observation / selected_observation_variance
            )
            means[rollout_index, selected] = posterior_mean
            variances[rollout_index, selected] = posterior_variance
            counts[rollout_index, selected] += 1

            budget = step + 1
            if budget in simulation.checkpoints:
                metrics, allocation = _record_rollout_state(
                    policy=policy,
                    budget=budget,
                    means=means,
                    variances=variances,
                    counts=counts,
                    products=products,
                )
                rollout_frames.append(metrics)
                allocation_frames.append(allocation)

    return AdaptivePolicyResult(
        rollout_metrics=pd.concat(rollout_frames, ignore_index=True),
        allocation_paths=pd.concat(allocation_frames, ignore_index=True),
    )


def summarise_policy_simulation(result: AdaptivePolicyResult) -> pd.DataFrame:
    """Aggregate pre-posterior policy performance with Monte Carlo standard errors."""
    frame = result.rollout_metrics
    required = {
        "policy",
        "budget_paired_blocks",
        "total_sign_entropy_nats",
        "total_bayes_regret_sqrt_audpc",
        "expected_wrong_timing_decisions",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Rollout metrics are missing columns: {sorted(missing)}")
    grouped = frame.groupby(["policy", "budget_paired_blocks"], observed=True)
    summary = grouped.agg(
        n_rollouts=("rollout", "size"),
        mean_sign_entropy_nats=("total_sign_entropy_nats", "mean"),
        sd_sign_entropy_nats=("total_sign_entropy_nats", "std"),
        mean_bayes_regret_sqrt_audpc=("total_bayes_regret_sqrt_audpc", "mean"),
        sd_bayes_regret_sqrt_audpc=("total_bayes_regret_sqrt_audpc", "std"),
        mean_expected_wrong_timing_decisions=("expected_wrong_timing_decisions", "mean"),
        sd_expected_wrong_timing_decisions=("expected_wrong_timing_decisions", "std"),
    ).reset_index()
    root_n = np.sqrt(summary["n_rollouts"].to_numpy(dtype=float))
    summary["mcse_sign_entropy_nats"] = summary["sd_sign_entropy_nats"] / root_n
    summary["mcse_bayes_regret_sqrt_audpc"] = (
        summary["sd_bayes_regret_sqrt_audpc"] / root_n
    )
    summary["mcse_expected_wrong_timing_decisions"] = (
        summary["sd_expected_wrong_timing_decisions"] / root_n
    )
    return summary


def summarise_allocations(result: AdaptivePolicyResult) -> pd.DataFrame:
    """Return mean number of paired blocks allocated to each product by policy and budget."""
    frame = result.allocation_paths
    id_columns = {"rollout", "policy", "budget_paired_blocks"}
    products = tuple(column for column in frame.columns if column not in id_columns)
    if not products:
        raise ValueError("No product allocation columns were found.")
    records: list[dict[str, float | int | str]] = []
    for (policy, budget), group in frame.groupby(
        ["policy", "budget_paired_blocks"], observed=True
    ):
        record: dict[str, float | int | str] = {
            "policy": str(policy),
            "budget_paired_blocks": int(budget),
        }
        for product in products:
            record[product] = float(group[product].mean())
        records.append(record)
    return pd.DataFrame.from_records(records).sort_values(
        ["budget_paired_blocks", "policy"]
    ).reset_index(drop=True)


def paired_policy_difference(
    result: AdaptivePolicyResult,
    *,
    budget: int,
    metric: str,
    policy_a: PolicyName = "decision_eig",
    policy_b: PolicyName = "uniform",
) -> dict[str, float]:
    """Estimate a paired policy difference using common Monte Carlo random numbers.

    The returned interval quantifies Monte Carlo error of the *estimated expected difference*; it is
    not a confidence interval for biological generalisation beyond the historical posterior model.
    """
    frame = result.rollout_metrics.loc[
        result.rollout_metrics["budget_paired_blocks"] == budget,
        ["rollout", "policy", metric],
    ]
    pivot = frame.pivot(index="rollout", columns="policy", values=metric)
    if policy_a not in pivot.columns or policy_b not in pivot.columns:
        raise ValueError("Requested policies are not available at the selected budget.")
    differences = pivot[policy_a].to_numpy(dtype=float) - pivot[policy_b].to_numpy(dtype=float)
    mean = float(np.mean(differences))
    standard_error = float(np.std(differences, ddof=1) / sqrt(len(differences)))
    return {
        "mean_difference": mean,
        "mc_standard_error": standard_error,
        "mc95_low": mean - 1.96 * standard_error,
        "mc95_high": mean + 1.96 * standard_error,
    }
