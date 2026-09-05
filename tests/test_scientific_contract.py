import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_real_field_transportability_conclusion_remains_true() -> None:
    summary = _load_json(RESULTS / "real_hop_trial" / "summary.json")
    paired = summary["paired_timing"]
    transport = summary["transportability"]
    assert isinstance(paired, dict)
    assert isinstance(transport, dict)

    ci95 = paired["ci95_audpc"]
    assert isinstance(ci95, list)
    assert float(ci95[0]) > 0.0
    assert float(transport["raw_sqrt_audpc_leave_one_year_out_rmse"]) > 2.0 * float(
        transport["raw_sqrt_audpc_random_rmse"]
    )


def test_environment_complexity_is_not_promoted() -> None:
    summary = _load_json(RESULTS / "real_hop_trial" / "environment" / "summary.json")
    metrics = summary["leave_one_year_out"]
    gate = summary["gxe_promotion_gate"]
    assert isinstance(metrics, dict)
    assert isinstance(gate, dict)

    assert float(metrics["sentinel_rmse"]) < float(metrics["baseline_rmse"])
    assert float(metrics["coarse_weather_rmse"]) > float(metrics["baseline_rmse"])
    assert gate["promoted"] is False
    assert int(gate["fold_wins"]) == 0


def test_multifidelity_progression_keeps_decision_advantage() -> None:
    summary = _load_json(RESULTS / "multifidelity" / "summary.json")
    gate = summary["calibration_gate"]
    result = summary["equal_budget_policy_result"]
    assert isinstance(gate, dict)
    assert isinstance(result, dict)

    assert gate["glasshouse_stage_promoted"] is True
    assert float(gate["rmse_improvement_percent"]) >= float(gate["promotion_threshold_percent"])
    assert float(result["multifidelity_regret"]) < float(result["lab_field_regret"])
    paired = result["paired_regret_difference_multifidelity_minus_lab_field"]
    assert isinstance(paired, dict)
    assert float(paired["mc95_high"]) < 0.0


def test_portfolio_voi_keeps_decision_advantage() -> None:
    summary = _load_json(RESULTS / "portfolio_decision" / "summary.json")
    policies = summary["equal_followup_budget_result"]
    gate = summary["promotion_gate"]
    assert isinstance(policies, dict)
    assert isinstance(gate, dict)

    for policy in ("uniform", "uncertainty", "portfolio_voi"):
        row = policies[policy]
        assert isinstance(row, dict)
        assert float(row["mean_followup_cost_units"]) == 24.0

    assert gate["promoted"] is True
    assert float(gate["observed_regret_reduction_vs_uncertainty_percent"]) >= float(
        gate["minimum_regret_reduction_vs_uncertainty_percent"]
    )
    paired = gate["paired_regret_difference_portfolio_voi_minus_uncertainty"]
    assert isinstance(paired, dict)
    assert float(paired["mc95_high"]) < 0.0


def test_model_risk_controls_keep_promotion_gate() -> None:
    summary = _load_json(RESULTS / "model_risk" / "summary.json")
    metrics = summary["metrics"]
    gate = summary["promotion_gate"]
    assert isinstance(metrics, dict)
    assert isinstance(gate, dict)

    assert gate["promoted"] is True
    assert float(gate["observed_distance_scaled_coverage"]) >= float(
        gate["minimum_distance_scaled_coverage"]
    )
    assert float(gate["observed_selective_coverage"]) >= float(
        gate["minimum_selective_coverage"]
    )
    assert float(gate["observed_ood_rejection_rate"]) >= float(
        gate["minimum_ood_rejection_rate"]
    )
    assert float(gate["observed_selective_mae_reduction_percent"]) >= float(
        gate["minimum_selective_mae_reduction_percent"]
    )

    naive = metrics["naive_id_interval_coverage"]
    scaled = metrics["distance_scaled_interval_coverage"]
    assert isinstance(naive, dict)
    assert isinstance(scaled, dict)
    assert float(scaled["mean"]) > float(naive["mean"])
