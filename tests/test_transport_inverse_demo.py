"""Regression checks for the stdout-only inverse evidence example."""

from __future__ import annotations

import json

import pytest

from crop_protection_ps.transport_inverse_demo import main, run_transport_inverse_demo


def test_inverse_demo_is_reproducible_and_uses_disjoint_times() -> None:
    first = run_transport_inverse_demo()
    second = run_transport_inverse_demo()
    assert first == second
    assert first["schema_version"] == 1
    assert first["evidence_status"] == "controlled synthetic methods evidence"

    experiment = first["experiment"]
    assert isinstance(experiment, dict)
    train_times = set(experiment["training_time_indices"])
    holdout_times = set(experiment["holdout_time_indices"])
    assert train_times.isdisjoint(holdout_times)
    assert experiment["training_observations"] == 21
    assert experiment["holdout_observations"] == 14

    fit = first["fit"]
    validation = first["holdout"]
    assert isinstance(fit, dict)
    assert isinstance(validation, dict)
    assert fit["success"] is True
    assert fit["identifiable"] is True
    assert fit["diffusion"] == pytest.approx(0.035, rel=0.15)
    assert fit["decay_rate"] == pytest.approx(0.18, rel=0.15)
    assert validation["n_observations"] == 14
    assert validation["normalized_rmse"] < 2.0
    assert validation["local_parameter_mean_negative_log_likelihood"] is not None

    # The report contains no non-standard NaN/Infinity JSON values.
    json.dumps(first, allow_nan=False)


def test_inverse_demo_cli_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    main([])
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload == json.loads(json.dumps(run_transport_inverse_demo(), allow_nan=False))


def test_uniform_negative_control_is_reproducible_and_unidentifiable() -> None:
    first = run_transport_inverse_demo("uniform")
    assert first == run_transport_inverse_demo("uniform")
    experiment = first["experiment"]
    fit = first["fit"]
    holdout = first["holdout"]
    assert isinstance(experiment, dict)
    assert isinstance(fit, dict)
    assert isinstance(holdout, dict)
    assert experiment["scenario"] == "uniform"
    assert experiment["expected_identifiable"] is False
    assert fit["success"] is True
    assert fit["identifiable"] is False
    assert holdout["local_parameter_90_coverage"] is None
    assert holdout["local_parameter_mean_negative_log_likelihood"] is None
    json.dumps(first, allow_nan=False)


def test_negative_control_cli_and_invalid_scenario(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--scenario", "uniform"])
    assert json.loads(capsys.readouterr().out) == json.loads(
        json.dumps(run_transport_inverse_demo("uniform"), allow_nan=False)
    )
    with pytest.raises(ValueError, match="scenario"):
        run_transport_inverse_demo("invalid")  # type: ignore[arg-type]
    with pytest.raises(SystemExit, match="2"):
        main(["--scenario", "unknown"])
