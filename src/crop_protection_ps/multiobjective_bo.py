"""Constrained multi-objective Bayesian optimisation for a controlled Crop Protection search.

The experiment is intentionally synthetic. Candidate formulation/application conditions are
mapped to
three latent scientific responses: efficacy, environmental burden, and crop injury. Efficacy is
maximised, environmental burden is minimised, and crop injury is a hard feasibility constraint.

Independent Bayesian response surfaces provide posterior means and predictive uncertainty. A
constrained ParEGO-style acquisition uses deterministic scalarisation weights, expected improvement,
and posterior feasibility probability. The implementation uses a finite candidate grid so that the
true Pareto frontier is known for controlled evaluation; latent truth is never exposed to the
optimiser.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.special import ndtr

Policy = Literal["random", "efficacy_only", "constrained_pareto"]

_DEFAULT_SEED: Final[int] = 20260828


@dataclass(frozen=True)
class BOConfig:
    """Locked design for the constrained multi-objective optimisation experiment."""

    dose_levels: int = 15
    formulation_levels: int = 12
    adjuvant_levels: int = 10
    n_initial: int = 12
    n_sequential: int = 18
    n_rollouts: int = 50
    injury_limit: float = 0.34
    efficacy_noise_sd: float = 0.035
    environment_noise_sd: float = 0.025
    injury_noise_sd: float = 0.030
    prior_precision: float = 1.0
    ridge_jitter: float = 1e-9
    feasibility_exponent: float = 1.25
    seed: int = _DEFAULT_SEED

    def __post_init__(self) -> None:
        grid_counts = (self.dose_levels, self.formulation_levels, self.adjuvant_levels)
        if min(grid_counts) < 3:
            raise ValueError("Each design dimension requires at least three levels.")
        if self.n_initial < 6 or self.n_sequential <= 0 or self.n_rollouts <= 0:
            raise ValueError(
                "Initial, sequential and rollout counts must be positive and non-trivial."
            )
        n_grid = int(np.prod(grid_counts))
        if self.n_initial + self.n_sequential >= n_grid:
            raise ValueError("Evaluation budget must be smaller than the candidate grid.")
        if not 0.0 < self.injury_limit < 1.0:
            raise ValueError("injury_limit must lie strictly between zero and one.")
        noise = (self.efficacy_noise_sd, self.environment_noise_sd, self.injury_noise_sd)
        if min(noise) <= 0.0:
            raise ValueError("Observation noise scales must be positive.")
        if self.prior_precision <= 0.0 or self.ridge_jitter <= 0.0:
            raise ValueError("Bayesian precision and jitter must be positive.")
        if self.feasibility_exponent <= 0.0:
            raise ValueError("feasibility_exponent must be positive.")


@dataclass(frozen=True)
class CandidateGrid:
    """Finite candidate grid and its hidden controlled response surfaces."""

    x: NDArray[np.float64]
    efficacy: NDArray[np.float64]
    environmental_burden: NDArray[np.float64]
    crop_injury: NDArray[np.float64]

    def __post_init__(self) -> None:
        if self.x.ndim != 2 or self.x.shape[1] != 3:
            raise ValueError("x must be a two-dimensional array with three design variables.")
        n = self.x.shape[0]
        for name, values in (
            ("efficacy", self.efficacy),
            ("environmental_burden", self.environmental_burden),
            ("crop_injury", self.crop_injury),
        ):
            if values.ndim != 1 or values.shape[0] != n:
                raise ValueError(f"{name} must have one value per candidate.")
            if not np.isfinite(values).all():
                raise ValueError(f"{name} contains non-finite values.")
        if np.any((self.x < 0.0) | (self.x > 1.0)):
            raise ValueError("Design variables must be normalised to [0, 1].")

    @property
    def n_candidates(self) -> int:
        """Return the number of candidate conditions."""
        return int(self.x.shape[0])


@dataclass(frozen=True)
class ObservationStreams:
    """Common-random-number observations for a single optimisation rollout."""

    efficacy: NDArray[np.float64]
    environmental_burden: NDArray[np.float64]
    crop_injury: NDArray[np.float64]


@dataclass(frozen=True)
class BayesianSurface:
    """Conjugate Bayesian linear response surface with known observation variance."""

    posterior_mean: NDArray[np.float64]
    posterior_cov: NDArray[np.float64]
    noise_var: float

    def predict(
        self, features: NDArray[np.float64]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Return latent-function posterior mean and standard deviation."""
        mean = features @ self.posterior_mean
        projected = features @ self.posterior_cov
        var = np.sum(projected * features, axis=1)
        return mean.astype(np.float64), np.sqrt(np.maximum(var, 0.0)).astype(np.float64)


def build_candidate_grid(config: BOConfig) -> CandidateGrid:
    """Construct the controlled formulation/application search space and hidden truth surfaces."""
    dose = np.linspace(0.05, 1.0, config.dose_levels)
    formulation = np.linspace(0.0, 1.0, config.formulation_levels)
    adjuvant = np.linspace(0.0, 1.0, config.adjuvant_levels)
    mesh = np.meshgrid(dose, formulation, adjuvant, indexing="ij")
    x = np.column_stack([axis.ravel() for axis in mesh]).astype(np.float64)
    d, f, a = x.T

    # Efficacy rises with dose but has a formulation/adjuvant optimum and a mild antagonistic ridge.
    dose_response = 1.0 / (1.0 + np.exp(-8.0 * (d - 0.38)))
    formulation_match = 0.18 * np.exp(-((f - 0.67) ** 2) / 0.035)
    adjuvant_match = 0.13 * np.exp(-((a - 0.58) ** 2) / 0.050)
    interaction = 0.10 * np.sin(np.pi * f) * np.sin(np.pi * a) - 0.07 * d * (a - 0.75) ** 2
    efficacy = np.clip(
        0.08 + 0.67 * dose_response + formulation_match + adjuvant_match + interaction,
        0.0,
        1.0,
    )

    # Environmental burden is driven principally by dose, with formulation persistence and
    # adjuvant terms creating a genuine efficacy-versus-burden trade-off.
    environmental_burden = np.clip(
        0.05
        + 0.58 * d
        + 0.18 * f**2
        + 0.10 * a
        + 0.07 * d * f
        - 0.08 * np.exp(-((f - 0.18) ** 2) / 0.025),
        0.0,
        1.0,
    )

    # Crop injury is a safety constraint. High dose and high adjuvant jointly create a risk region,
    # while a formulation-specific compatibility pocket lowers injury around a moderate setting.
    crop_injury = np.clip(
        0.025
        + 0.22 * d**1.7
        + 0.17 * a**2
        + 0.20 * d * a
        + 0.08 * (f - 0.45) ** 2
        - 0.075 * np.exp(-(((f - 0.46) ** 2) + ((a - 0.36) ** 2)) / 0.030),
        0.0,
        1.0,
    )
    return CandidateGrid(
        x=x,
        efficacy=efficacy,
        environmental_burden=environmental_burden,
        crop_injury=crop_injury,
    )


def response_features(x: NDArray[np.float64]) -> NDArray[np.float64]:
    """Create a compact nonlinear basis used by every Bayesian response surface."""
    if x.ndim != 2 or x.shape[1] != 3:
        raise ValueError("x must have shape (n, 3).")
    d, f, a = x.T
    centres = np.asarray(
        [
            [0.30, 0.25, 0.25],
            [0.40, 0.65, 0.55],
            [0.65, 0.45, 0.35],
            [0.80, 0.75, 0.70],
        ],
        dtype=np.float64,
    )
    rbf = []
    for centre in centres:
        distance_sq = np.sum((x - centre[None, :]) ** 2, axis=1)
        rbf.append(np.exp(-distance_sq / 0.085))
    return np.column_stack(
        [
            np.ones(x.shape[0]),
            d,
            f,
            a,
            d**2,
            f**2,
            a**2,
            d * f,
            d * a,
            f * a,
            np.sin(np.pi * d),
            np.sin(np.pi * f),
            np.sin(np.pi * a),
            *rbf,
        ]
    ).astype(np.float64)


def fit_bayesian_surface(
    features: NDArray[np.float64],
    observations: NDArray[np.float64],
    *,
    noise_sd: float,
    prior_precision: float,
    jitter: float,
) -> BayesianSurface:
    """Fit a zero-centred conjugate Bayesian linear response surface."""
    if features.ndim != 2 or observations.ndim != 1:
        raise ValueError("features must be 2D and observations must be 1D.")
    if features.shape[0] != observations.shape[0]:
        raise ValueError("features and observations must contain the same number of rows.")
    if noise_sd <= 0.0 or prior_precision <= 0.0 or jitter <= 0.0:
        raise ValueError("Noise, prior precision and jitter must be positive.")
    d = features.shape[1]
    noise_var = noise_sd**2
    precision = prior_precision * np.eye(d) + (features.T @ features) / noise_var
    precision += jitter * np.eye(d)
    covariance = np.linalg.inv(precision)
    mean = covariance @ (features.T @ observations / noise_var)
    return BayesianSurface(mean.astype(np.float64), covariance.astype(np.float64), noise_var)


def _expected_improvement(
    mean: NDArray[np.float64],
    sd: NDArray[np.float64],
    incumbent: float,
) -> NDArray[np.float64]:
    """Expected improvement for a quantity to be maximised."""
    safe_sd = np.maximum(sd, 1e-12)
    improvement = mean - incumbent
    z = improvement / safe_sd
    density = np.exp(-0.5 * z**2) / np.sqrt(2.0 * np.pi)
    ei = improvement * ndtr(z) + safe_sd * density
    ei = np.where(sd <= 1e-12, np.maximum(improvement, 0.0), ei)
    return np.maximum(ei, 0.0).astype(np.float64)


def pareto_mask(points: NDArray[np.float64]) -> NDArray[np.bool_]:
    """Return non-dominated mask for two objectives that are both maximised."""
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points must have shape (n, 2).")
    n = points.shape[0]
    mask = np.ones(n, dtype=bool)
    for i in range(n):
        if not mask[i]:
            continue
        dominates_i = np.all(points >= points[i], axis=1) & np.any(points > points[i], axis=1)
        if np.any(dominates_i):
            mask[i] = False
    return mask


def hypervolume_2d(
    points: NDArray[np.float64],
    *,
    reference: tuple[float, float] = (0.0, 0.0),
) -> float:
    """Compute dominated hypervolume for two objectives that are both maximised."""
    if points.size == 0:
        return 0.0
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("points must have shape (n, 2).")
    ref = np.asarray(reference, dtype=np.float64)
    clipped = points[np.all(points > ref[None, :], axis=1)]
    if clipped.size == 0:
        return 0.0
    frontier = clipped[pareto_mask(clipped)]
    frontier = frontier[np.argsort(frontier[:, 0])]
    area = 0.0
    previous_x = ref[0]
    for x_value, y_value in frontier:
        area += max(float(x_value - previous_x), 0.0) * max(float(y_value - ref[1]), 0.0)
        previous_x = float(x_value)
    return float(area)


def oracle_frontier(grid: CandidateGrid, config: BOConfig) -> tuple[NDArray[np.int64], float]:
    """Return the hidden feasible Pareto frontier and its hypervolume for controlled scoring."""
    feasible = grid.crop_injury <= config.injury_limit
    indices = np.flatnonzero(feasible)
    objectives = np.column_stack(
        [grid.efficacy[feasible], 1.0 - grid.environmental_burden[feasible]]
    )
    frontier_local = pareto_mask(objectives)
    frontier_indices = indices[frontier_local].astype(np.int64)
    return frontier_indices, hypervolume_2d(objectives[frontier_local])


def _initial_design(grid: CandidateGrid, config: BOConfig) -> NDArray[np.int64]:
    """Deterministic space-filling initial design shared by every policy and rollout."""
    x = grid.x
    # Greedy maximin design seeded at a moderate central condition.
    centre = np.asarray([0.40, 0.50, 0.40], dtype=np.float64)
    first = int(np.argmin(np.sum((x - centre[None, :]) ** 2, axis=1)))
    selected = [first]
    min_distance = np.sum((x - x[first]) ** 2, axis=1)
    while len(selected) < config.n_initial:
        min_distance[np.asarray(selected, dtype=np.int64)] = -np.inf
        nxt = int(np.argmax(min_distance))
        selected.append(nxt)
        distance = np.sum((x - x[nxt]) ** 2, axis=1)
        min_distance = np.minimum(min_distance, distance)
    return np.asarray(selected, dtype=np.int64)


def simulate_observations(
    grid: CandidateGrid,
    config: BOConfig,
    *,
    rng: np.random.Generator,
) -> ObservationStreams:
    """Generate one common observation stream over the entire finite candidate grid."""
    return ObservationStreams(
        efficacy=(
            grid.efficacy + rng.normal(0.0, config.efficacy_noise_sd, grid.n_candidates)
        ).astype(np.float64),
        environmental_burden=(
            grid.environmental_burden
            + rng.normal(0.0, config.environment_noise_sd, grid.n_candidates)
        ).astype(np.float64),
        crop_injury=(
            grid.crop_injury + rng.normal(0.0, config.injury_noise_sd, grid.n_candidates)
        ).astype(np.float64),
    )


def _fit_surfaces(
    features: NDArray[np.float64],
    evaluated: NDArray[np.int64],
    observations: ObservationStreams,
    config: BOConfig,
) -> tuple[BayesianSurface, BayesianSurface, BayesianSurface]:
    """Fit efficacy, environment and injury surrogates on currently evaluated candidates."""
    observed_features = features[evaluated]
    efficacy = fit_bayesian_surface(
        observed_features,
        observations.efficacy[evaluated],
        noise_sd=config.efficacy_noise_sd,
        prior_precision=config.prior_precision,
        jitter=config.ridge_jitter,
    )
    environment = fit_bayesian_surface(
        observed_features,
        observations.environmental_burden[evaluated],
        noise_sd=config.environment_noise_sd,
        prior_precision=config.prior_precision,
        jitter=config.ridge_jitter,
    )
    injury = fit_bayesian_surface(
        observed_features,
        observations.crop_injury[evaluated],
        noise_sd=config.injury_noise_sd,
        prior_precision=config.prior_precision,
        jitter=config.ridge_jitter,
    )
    return efficacy, environment, injury


def acquisition_values(
    grid: CandidateGrid,
    features: NDArray[np.float64],
    evaluated: NDArray[np.int64],
    observations: ObservationStreams,
    config: BOConfig,
    *,
    policy: Policy,
    scalar_weight: float,
) -> pd.DataFrame:
    """Compute acquisition values for every currently unevaluated candidate."""
    if not 0.0 <= scalar_weight <= 1.0:
        raise ValueError("scalar_weight must lie in [0, 1].")
    if policy == "random":
        raise ValueError("Random policy does not use model-based acquisition values.")
    efficacy_model, environment_model, injury_model = _fit_surfaces(
        features, evaluated, observations, config
    )
    efficacy_mean, efficacy_sd = efficacy_model.predict(features)
    environment_mean, environment_sd = environment_model.predict(features)
    injury_mean, injury_sd = injury_model.predict(features)
    safe_injury_sd = np.maximum(injury_sd, 1e-12)
    feasibility_probability = ndtr((config.injury_limit - injury_mean) / safe_injury_sd)

    if policy == "efficacy_only":
        scalar_mean = efficacy_mean
        scalar_sd = efficacy_sd
        incumbent_values = observations.efficacy[evaluated]
    else:
        # Environment is converted to a larger-is-better sustainability score. Independent
        # posterior surfaces make the scalarised variance additive under the locked approximation.
        scalar_mean = (
            scalar_weight * efficacy_mean
            + (1.0 - scalar_weight) * (1.0 - environment_mean)
        )
        scalar_sd = np.sqrt(
            (scalar_weight * efficacy_sd) ** 2
            + ((1.0 - scalar_weight) * environment_sd) ** 2
        )
        incumbent_values = (
            scalar_weight * observations.efficacy[evaluated]
            + (1.0 - scalar_weight) * (1.0 - observations.environmental_burden[evaluated])
        )

    observed_feasible = observations.crop_injury[evaluated] <= config.injury_limit
    if np.any(observed_feasible):
        incumbent = float(np.max(incumbent_values[observed_feasible]))
    else:
        incumbent = float(np.max(incumbent_values))
    ei = _expected_improvement(scalar_mean, scalar_sd, incumbent)
    acquisition = ei * feasibility_probability**config.feasibility_exponent
    acquisition[evaluated] = -np.inf
    return pd.DataFrame(
        {
            "candidate": np.arange(grid.n_candidates, dtype=np.int64),
            "efficacy_mean": efficacy_mean,
            "environment_mean": environment_mean,
            "injury_mean": injury_mean,
            "feasibility_probability": feasibility_probability,
            "scalar_weight_efficacy": scalar_weight,
            "expected_improvement": ei,
            "acquisition": acquisition,
        }
    )


def run_policy(
    grid: CandidateGrid,
    observations: ObservationStreams,
    config: BOConfig,
    *,
    policy: Policy,
    rng: np.random.Generator,
) -> dict[str, float | int | str]:
    """Run one equal-budget sequential optimisation policy and score discovered true outcomes."""
    features = response_features(grid.x)
    initial = _initial_design(grid, config)
    evaluated = initial.tolist()
    available = np.ones(grid.n_candidates, dtype=bool)
    available[initial] = False

    for step in range(config.n_sequential):
        if policy == "random":
            candidates = np.flatnonzero(available)
            next_candidate = int(rng.choice(candidates))
        else:
            # Deterministic cycling weights approximate Pareto-front exploration without injecting
            # extra acquisition noise into paired policy comparisons.
            scalar_weight = (
                1.0
                if policy == "efficacy_only"
                else (step + 1.0) / (config.n_sequential + 1.0)
            )
            table = acquisition_values(
                grid,
                features,
                np.asarray(evaluated, dtype=np.int64),
                observations,
                config,
                policy=policy,
                scalar_weight=scalar_weight,
            )
            next_candidate = int(table["acquisition"].idxmax())
        evaluated.append(next_candidate)
        available[next_candidate] = False

    evaluated_array = np.asarray(evaluated, dtype=np.int64)
    true_feasible = grid.crop_injury[evaluated_array] <= config.injury_limit
    feasible_indices = evaluated_array[true_feasible]
    feasible_objectives = np.column_stack(
        [grid.efficacy[feasible_indices], 1.0 - grid.environmental_burden[feasible_indices]]
    )
    discovered_hv = hypervolume_2d(feasible_objectives)
    frontier_indices, oracle_hv = oracle_frontier(grid, config)
    discovered_frontier = np.intersect1d(evaluated_array, frontier_indices)

    unsafe_rate = float(np.mean(~true_feasible))
    high_value = true_feasible & (grid.efficacy[evaluated_array] >= 0.80) & (
        grid.environmental_burden[evaluated_array] <= 0.48
    )
    return {
        "policy": policy,
        "n_evaluations": int(evaluated_array.size),
        "n_true_feasible": int(true_feasible.sum()),
        "unsafe_evaluation_rate": unsafe_rate,
        "discovered_hypervolume": discovered_hv,
        "oracle_hypervolume": oracle_hv,
        "hypervolume_ratio": discovered_hv / oracle_hv if oracle_hv > 0.0 else 0.0,
        "oracle_frontier_recall": float(discovered_frontier.size / frontier_indices.size),
        "n_balanced_high_value_evaluated": int(high_value.sum()),
        "best_feasible_efficacy": (
            float(np.max(grid.efficacy[feasible_indices])) if feasible_indices.size else 0.0
        ),
        "best_feasible_environmental_burden": (
            float(np.min(grid.environmental_burden[feasible_indices]))
            if feasible_indices.size
            else 1.0
        ),
    }


def simulate_policies(config: BOConfig) -> pd.DataFrame:
    """Run paired optimisation policies under common latent truth and observation noise."""
    grid = build_candidate_grid(config)
    seed_sequence = np.random.SeedSequence(config.seed)
    rollout_seeds = seed_sequence.spawn(config.n_rollouts)
    records: list[dict[str, float | int | str]] = []
    policies: tuple[Policy, ...] = ("random", "efficacy_only", "constrained_pareto")
    for rollout, rollout_seed in enumerate(rollout_seeds):
        observation_seed, random_seed = rollout_seed.spawn(2)
        observations = simulate_observations(
            grid, config, rng=np.random.default_rng(observation_seed)
        )
        random_rng = np.random.default_rng(random_seed)
        for policy in policies:
            result = run_policy(
                grid,
                observations,
                config,
                policy=policy,
                rng=random_rng if policy == "random" else np.random.default_rng(0),
            )
            result["rollout"] = rollout
            records.append(result)
    return pd.DataFrame.from_records(records)


def summarise_policies(results: pd.DataFrame) -> pd.DataFrame:
    """Aggregate paired optimisation metrics by policy."""
    required = {
        "policy",
        "rollout",
        "hypervolume_ratio",
        "unsafe_evaluation_rate",
        "oracle_frontier_recall",
        "n_balanced_high_value_evaluated",
    }
    missing = required.difference(results.columns)
    if missing:
        raise ValueError(f"Missing policy result columns: {sorted(missing)}")
    metrics = [
        "hypervolume_ratio",
        "unsafe_evaluation_rate",
        "oracle_frontier_recall",
        "n_balanced_high_value_evaluated",
        "best_feasible_efficacy",
        "best_feasible_environmental_burden",
    ]
    grouped = results.groupby("policy", sort=False)[metrics].agg(["mean", "std"])
    grouped.columns = [f"{stat}_{metric}" for metric, stat in grouped.columns]
    return grouped.reset_index()


def paired_difference(
    results: pd.DataFrame,
    *,
    metric: str,
    policy_a: Policy,
    policy_b: Policy,
) -> dict[str, float]:
    """Return paired Monte Carlo difference A-minus-B with a normal 95% MC interval."""
    pivot = results.pivot(index="rollout", columns="policy", values=metric)
    difference = (pivot[policy_a] - pivot[policy_b]).to_numpy(dtype=np.float64)
    mean = float(np.mean(difference))
    se = float(np.std(difference, ddof=1) / np.sqrt(difference.size))
    return {"mean": mean, "mc95_low": mean - 1.96 * se, "mc95_high": mean + 1.96 * se}
