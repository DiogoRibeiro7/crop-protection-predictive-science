"""Deterministic, stdout-only known-truth transport inverse demonstration."""

from __future__ import annotations

import json
from dataclasses import asdict

import numpy as np

from .transport_reaction import TransportReactionConfig, cosine_mode_initial
from .transport_reaction_inverse import (
    InverseCalibrationConfig,
    calibrate_transport_reaction,
    simulate_transport_observations,
    validate_inverse_holdout,
)


def run_transport_inverse_demo() -> dict[str, object]:
    """Return reproducible calibration and disjoint held-out metrics as JSON-ready data.

    All observations are synthetic, with independent Gaussian measurement noise
    and fixed, separate training and holdout seeds. Nothing is written to disk.
    """
    truth = TransportReactionConfig(
        diffusion=0.035,
        decay_rate=0.18,
        n_cells=48,
        dt=0.002,
        final_time=0.2,
    )
    initial = cosine_mode_initial(truth, mean=0.8, amplitude=0.45, mode=1)
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
            "training_seed": training_seed,
            "holdout_seed": holdout_seed,
            "training_time_indices": sorted(set(training.time_index.tolist())),
            "holdout_time_indices": sorted(set(holdout.time_index.tolist())),
            "cell_indices": cells.tolist(),
            "training_observations": int(training.observed.size),
            "holdout_observations": int(holdout.observed.size),
        },
        "fit": asdict(fit),
        "holdout": asdict(prediction),
        "scope_warning": (
            "Synthetic known-truth validation only; local predictive intervals and scores do "
            "not establish crop-field calibration or account for structural model error."
        ),
    }


def main() -> None:
    """Print a deterministic JSON report without creating any files."""
    print(json.dumps(run_transport_inverse_demo(), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
