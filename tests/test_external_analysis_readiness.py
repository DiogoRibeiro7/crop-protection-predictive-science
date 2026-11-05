"""Regression tests for the research-readiness and protocol-gap ledger."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest

import crop_protection_ps.external_analysis_readiness as module
from crop_protection_ps.external_analysis_readiness import (
    _verify_export,
    inventory_analysis_readiness,
    main,
    render_reports,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_analysis_readiness"


def _csv_rows(content: str) -> list[dict[str, str]]:
    """Parse one generated checklist without treating labels as numerics."""
    return list(csv.DictReader(io.StringIO(content)))


def test_original_reports_and_contract_reproduce_checked_in_readiness() -> None:
    report = inventory_analysis_readiness(_ROOT / "data")
    outputs = render_reports(report)
    assert set(outputs) == {
        "summary.json",
        "allowed_descriptives.csv",
        "protocol_requirements.csv",
        "blocked_analyses.csv",
    }
    for filename, content in outputs.items():
        assert (_OUTPUT / filename).read_text(encoding="utf-8") == content
    metadata = json.loads(outputs["summary.json"])
    assert metadata["schema_version"] == 1
    assert metadata["contract_status"] == "protocol_review_pending"
    assert metadata["source_assets"] == 18
    assert metadata["policy_families"] == 10
    assert metadata["allowed_descriptive_rows"] == 36
    assert metadata["crosschecked_descriptive_rows"] == 36
    assert metadata["descriptive_rows_not_yet_exported"] == 0
    assert metadata["protocol_gated_question_rows"] == 19
    assert metadata["protocol_requirement_rows"] == 59
    assert metadata["explicitly_blocked_rows"] == 34
    assert "allowed_descriptions" not in metadata
    assert "protocol_requirements" not in metadata
    assert "blocked_actions" not in metadata


def test_allowed_export_state_is_separate_from_scientific_permission() -> None:
    exports = _csv_rows(
        render_reports(inventory_analysis_readiness(_ROOT / "data"))["allowed_descriptives.csv"]
    )
    assert len(exports) == 36
    assert len({row["asset_id"] for row in exports}) == 18
    assert all(row["permission"] == "allowed_descriptive_only" for row in exports)
    assert all(row["recorded_group_basis"] for row in exports)
    assert all(int(row["recorded_groups"]) >= 1 for row in exports)
    assert all(row["evidence_path"] for row in exports if row["export_state"] != "not_exported")
    pending = [row for row in exports if row["export_state"] == "not_exported"]
    assert pending == []
    weather = next(row for row in exports if row["action"] == "source_weather_quality_review")
    assert weather["evidence_path"] == "results/external_dryad_weather_quality/summary.json"
    assert sum(r["action"] == "structural_inventory" for r in exports) == 18
    assert sum(r["export_state"] == "crosschecked_committed_report" for r in exports) == 36


def test_protocol_requirements_never_become_allowed_inferential_analyses() -> None:
    rendered = render_reports(inventory_analysis_readiness(_ROOT / "data"))
    gates = _csv_rows(rendered["protocol_requirements.csv"])
    blocked = _csv_rows(rendered["blocked_analyses.csv"])
    assert len(gates) == 59
    assert len(blocked) == 34
    assert all(r["permission"] == "requires_protocol" for r in gates)
    assert all(r["clearance"] == "not_cleared_by_contract" for r in gates)
    assert all(r["permission"] == "blocked" for r in blocked)
    assert any(
        r["asset_id"] == "dryad_field_plants"
        and r["analysis"] == "longitudinal_disease_model"
        and r["requirement"] == "state_transition_codebook"
        for r in gates
    )
    assert any(
        r["asset_id"] == "wheat_field"
        and r["requirement"] == "reconcile_56_published_trials_vs_76_trial_ids"
        for r in gates
    )
    assert any(
        r["asset_id"] == "dryad_greenhouse_death"
        and r["analysis"] == "mortality_rate_from_death_cases_only"
        for r in blocked
    )
    assert {r["analysis"] for r in gates}.isdisjoint(
        {r["action"] for r in _csv_rows(rendered["allowed_descriptives.csv"])}
    )


def test_unreviewed_or_missing_report_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(module._EXPORTS, "dryad_field", "results/absent_field_report.json")
    with pytest.raises(ValueError, match="missing reviewed descriptive report"):
        inventory_analysis_readiness(_ROOT / "data")


def test_cross_dataset_substitution_does_not_pass_source_unit_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(module._EXPORTS, "dryad_field", "results/external_aphid_field/summary.json")
    with pytest.raises(ValueError, match="stale or mismatched descriptive provenance"):
        inventory_analysis_readiness(_ROOT / "data")


def test_explicit_source_count_regression_is_detected(tmp_path: Path) -> None:
    existing = json.loads(
        (_ROOT / "results/external_dryad_field_statuses/summary.json").read_text(encoding="utf-8")
    )
    existing["plant_rows"] = 4806  # Accidental plant–visit pseudo-replication.
    report_path = tmp_path / "tampered.json"
    report_path.write_text(json.dumps(existing), encoding="utf-8")
    asset: dict[str, Any] = {
        "id": "dryad_field_plants",
        "policy": "dryad_field",
        "file": "dryad_pathogen_temperature_4mw6m90jv/Raw_field_data.xlsx",
        "table": "Sheet1",
        "rows": 178,
        "group_count": 178,
    }
    with pytest.raises(ValueError, match="source-unit disagreement"):
        _verify_export(
            tmp_path,
            asset,
            "within_plant_status_description",
            "tampered.json",
            existing["manifest_sha256"],
            existing["analysis_contract_sha256"],
        )


def test_weather_summary_count_regression_is_detected(tmp_path: Path) -> None:
    existing = json.loads(
        (_ROOT / "results/external_dryad_weather_quality/summary.json").read_text(encoding="utf-8")
    )
    existing["distinct_dates"] = 213
    report_path = tmp_path / "tampered_weather.json"
    report_path.write_text(json.dumps(existing), encoding="utf-8")
    asset: dict[str, Any] = {
        "id": "dryad_daily_weather",
        "policy": "dryad_weather",
        "file": "dryad_pathogen_temperature_4mw6m90jv/daily_high_temps.txt",
        "table": "daily_high_temps.txt",
        "rows": 214,
        "group_count": 214,
    }
    with pytest.raises(ValueError, match="source-unit disagreement"):
        _verify_export(
            tmp_path,
            asset,
            "source_weather_quality_review",
            "tampered_weather.json",
            existing["manifest_sha256"],
            existing["analysis_contract_sha256"],
        )


def test_misclassified_protocol_action_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module.analysis_decision

    def wrongly_approved(contract: dict[str, Any], dataset: str, action: str) -> dict[str, Any]:
        """Simulate a non-reviewed downstream permission override."""
        if dataset == "dryad_field_plants" and action == "temperature_causal_effect":
            return {"status": "allowed"}
        return original(contract, dataset, action)

    monkeypatch.setattr(module, "analysis_decision", wrongly_approved)
    with pytest.raises(ValueError, match="protocol-gated action was promoted"):
        inventory_analysis_readiness(_ROOT / "data")


def test_policy_inventory_requires_explicit_review_of_new_families(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(module._EXPORTS, "dryad_weather")
    with pytest.raises(ValueError, match="unreviewed policy"):
        inventory_analysis_readiness(_ROOT / "data")


def test_cli_check_is_read_only_and_rejects_stale_files(tmp_path: Path) -> None:
    target = tmp_path / "readiness"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(target)]
    with pytest.raises(SystemExit) as missing:
        main([*args, "--check"])
    assert missing.value.code == 1
    assert not target.exists()

    assert main(args) == 0
    before = {path.name: path.read_bytes() for path in target.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {path.name: path.read_bytes() for path in target.iterdir()} == before
    (target / "protocol_requirements.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stale:
        main([*args, "--check"])
    assert stale.value.code == 1
