"""Deterministic, stdout-only known-truth transport inverse demonstration."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from typing import Literal

import numpy as np

from .transport_reaction import TransportReactionConfig, cosine_mode_initial
from .transport_reaction_inverse import (
    InverseCalibrationConfig,
    calibrate_transport_reaction,
    simulate_transport_observations,
    validate_inverse_holdout,
)

InverseScenario = Literal["informative", "uniform"]


def run_transport_inverse_demo(
    scenario: InverseScenario = "informative",
) -> dict[str, object]:
    """Return reproducible calibration and disjoint held-out metrics as JSON-ready data.

    The uniform negative control contains no diffusion information. All noise
    is independent Gaussian, with fixed disjoint seeds and no disk writes.
    """
    if scenario not in ("informative", "uniform"):
        raise ValueError("scenario must be 'informative' or 'uniform'.")
    truth = TransportReactionConfig(
        diffusion=0.035,
        decay_rate=0.18,
        n_cells=48,
        dt=0.002,
        final_time=0.2,
    )
    initial = (
        cosine_mode_initial(truth, mean=0.8, amplitude=0.45, mode=1)
        if scenario == "informative"
        else np.full(truth.n_cells, 0.8, dtype=np.float64)
    )
    cells = np.asarray([3, 9, 15, 23, 31, 39, 45], dtype=np.int64)
    noise_sigma = 0.003
    training_seed = 1729
    holdout_seed = 1730
    training = simulate_transport_observations(
        truth,
        initial,
        observation_times=np.asarray([0.02, 0.05, 0.10], dtype=np.float64),
        cell_indices=cells,
        noise_sigma=noise_sigma,
        seed=training_seed,
    )
    holdout = simulate_transport_observations(
        truth,
        initial,
        observation_times=np.asarray([0.15, 0.20], dtype=np.float64),
        cell_indices=cells,
        noise_sigma=noise_sigma,
        seed=holdout_seed,
    )
    fit = calibrate_transport_reaction(
        truth,
        initial,
        training,
        calibration=InverseCalibrationConfig(
            initial_diffusion=0.02,
            initial_decay_rate=0.10,
            diffusion_bounds=(0.005, 0.10),
            decay_rate_bounds=(0.05, 0.40),
        ),
    )
    prediction = validate_inverse_holdout(truth, initial, training, holdout, fit)
    fit_payload = asdict(fit)
    # An unidentifiable Jacobian legitimately has an infinite condition number;
    # JSON should encode that explicitly as null, never as non-standard Infinity.
    if not np.isfinite(fit.jacobian_condition_number):
        fit_payload["jacobian_condition_number"] = None
    return {
        "schema_version": 1,
        "evidence_status": "controlled synthetic methods evidence",
        "truth": {
            "diffusion": truth.diffusion,
            "decay_rate": truth.decay_rate,
            "n_cells": truth.n_cells,
            "dt": truth.dt,
            "final_time": truth.final_time,
            "noise_sigma": noise_sigma,
        },
        "experiment": {
            "scenario": scenario,
            "expected_identifiable": scenario == "informative",
            "training_seed": training_seed,
            "holdout_seed": holdout_seed,
            "training_time_indices": sorted(set(training.time_index.tolist())),
            "holdout_time_indices": sorted(set(holdout.time_index.tolist())),
            "cell_indices": cells.tolist(),
            "training_observations": int(training.observed.size),
            "holdout_observations": int(holdout.observed.size),
        },
        "fit": fit_payload,
        "holdout": asdict(prediction),
        "scope_warning": (
            "Synthetic known-truth validation only; local predictive intervals and scores do "
            "not establish crop-field calibration or account for structural model error."
        ),
    }


def main(argv: Sequence[str] | None = None) -> None:
    """Print one selected known-truth scenario as strict JSON to stdout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=("informative", "uniform"),
        default="informative",
        help="Use a spatial cosine profile or the uniform unidentifiable negative control.",
    )
    args = parser.parse_args(argv)
    scenario: InverseScenario = args.scenario
    print(json.dumps(run_transport_inverse_demo(scenario), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
