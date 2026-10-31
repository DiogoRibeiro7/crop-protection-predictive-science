"""Evidence-bound, fail-closed analysis permission checks for external data."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from crop_protection_ps.analysis_eligibility import (
    analysis_decision,
    main,
    validate_analysis_contract,
)

_ROOT = Path(__file__).resolve().parents[1]
_DATA = _ROOT / "data"
_CONTRACT = _DATA / "external/analysis_eligibility.json"


@pytest.fixture(scope="module")
def verified_contract() -> dict[str, Any]:
    """Read and validate original source snapshots once for decision-only tests."""
    return validate_analysis_contract(_DATA, _CONTRACT)


def _changed_contract(tmp_path: Path, contract: dict[str, Any]) -> Path:
    """Write a modified policy in isolation; never alter committed source files."""
    output = tmp_path / "tampered.json"
    output.write_text(json.dumps(contract), encoding="utf-8")
    return output


def test_contract_covers_all_original_observation_tables(
    verified_contract: dict[str, Any],
) -> None:
    assets = verified_contract["assets"]
    assert verified_contract["schema_version"] == 1
    assert verified_contract["contract_status"] == "protocol_review_pending"
    assert len(assets) == 18
    assert len({(asset["file"], asset["table"]) for asset in assets}) == 18
    assert len({asset["policy"] for asset in assets}) == 10
    assert sum(asset["rows"] for asset in assets) == 5150


def test_allowed_actions_are_descriptive_only(verified_contract: dict[str, Any]) -> None:
    for dataset, analysis in (
        ("wheat_field", "matched_endpoint_coverage"),
        ("aphid_experiment_5_field", "within_series_mortality_description"),
        ("dryad_greenhouse_infection", "disease_status_frequencies"),
        ("dryad_field_plants", "within_plant_status_description"),
        ("dryad_daily_weather", "source_weather_quality_review"),
    ):
        assert analysis_decision(verified_contract, dataset, analysis)["status"] == "allowed"


def test_inferential_actions_require_protocol_not_automatic_release(
    verified_contract: dict[str, Any],
) -> None:
    for dataset, action in (
        ("wheat_field", "trial_level_treatment_effect"),
        ("aphid_experiment_1", "binomial_temperature_interaction"),
        ("aphid_experiment_5_field", "field_treatment_effect"),
        ("dryad_growth_3", "temperature_response_model"),
        ("dryad_greenhouse_death", "plant_death_risk_model"),
        ("dryad_field_plants", "temperature_causal_effect"),
    ):
        decision = analysis_decision(verified_contract, dataset, action)
        assert decision["status"] == "requires_protocol"
        assert decision["requirements"]


def test_unsafe_and_unknown_actions_fail_closed(verified_contract: dict[str, Any]) -> None:
    prohibited = analysis_decision(
        verified_contract, "dryad_greenhouse_death", "mortality_rate_from_death_cases_only"
    )
    assert prohibited["status"] == "blocked"
    assert prohibited["reason"] == "explicitly_prohibited"
    assert (
        analysis_decision(verified_contract, "dryad_greenhouse_death", "automated_effect_fit")[
            "reason"
        ]
        == "unrecognized_analysis"
    )
    assert (
        analysis_decision(verified_contract, "invented_dataset", "structural_inventory")["reason"]
        == "unknown_dataset"
    )


@pytest.mark.parametrize(
    "path",
    [
        "data/external/manifest.json",
        "data/external/profile.json",
        "results/external_wheat_pairability.json",
        "results/external_aphid_dryad_units.json",
    ],
)
def test_stale_evidence_checksum_is_rejected(
    tmp_path: Path, verified_contract: dict[str, Any], path: str
) -> None:
    changed = copy.deepcopy(verified_contract)
    changed["evidence_sha256"][path] = "0" * 64
    with pytest.raises(ValueError, match="evidence checksum"):
        validate_analysis_contract(_DATA, _changed_contract(tmp_path, changed))


def test_missing_observation_table_is_rejected(
    tmp_path: Path, verified_contract: dict[str, Any]
) -> None:
    changed = copy.deepcopy(verified_contract)
    changed["assets"].pop()
    with pytest.raises(ValueError, match="does not cover all observation tables"):
        validate_analysis_contract(_DATA, _changed_contract(tmp_path, changed))


def test_incorrect_group_count_is_rejected(
    tmp_path: Path, verified_contract: dict[str, Any]
) -> None:
    changed = copy.deepcopy(verified_contract)
    changed["assets"][0]["group_count"] = 2276
    with pytest.raises(ValueError, match="audited group or policy mismatch"):
        validate_analysis_contract(_DATA, _changed_contract(tmp_path, changed))


def test_unsafe_promotion_to_allowed_is_rejected(
    tmp_path: Path, verified_contract: dict[str, Any]
) -> None:
    changed = copy.deepcopy(verified_contract)
    policy = changed["policies"]["dryad_greenhouse_death"]
    policy["blocked"].remove("mortality_rate_from_death_cases_only")
    policy["allowed"].append("mortality_rate_from_death_cases_only")
    with pytest.raises(ValueError, match="non-descriptive analysis"):
        validate_analysis_contract(_DATA, _changed_contract(tmp_path, changed))


def test_wrong_descriptive_action_for_policy_is_rejected(
    tmp_path: Path, verified_contract: dict[str, Any]
) -> None:
    changed = copy.deepcopy(verified_contract)
    changed["policies"]["wheat_field"]["allowed"].append("assay_count_description")
    with pytest.raises(ValueError, match="altered its safe descriptive actions"):
        validate_analysis_contract(_DATA, _changed_contract(tmp_path, changed))


def test_cli_reports_decisions_and_exit_codes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--data-dir", str(_DATA), "--check"]) == 0
    assert "18 observation tables" in capsys.readouterr().out

    allowed_args = ["--data-dir", str(_DATA), "--dataset", "dryad_field_plants"]
    assert main([*allowed_args, "--analysis", "within_plant_status_description"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "allowed"

    assert main([*allowed_args, "--analysis", "temperature_causal_effect"]) == 2
    decision = json.loads(capsys.readouterr().out)
    assert decision["status"] == "requires_protocol"


def test_cli_refuses_stale_contract(tmp_path: Path, verified_contract: dict[str, Any]) -> None:
    changed = copy.deepcopy(verified_contract)
    changed["evidence_sha256"]["data/external/manifest.json"] = "a" * 64
    with pytest.raises(SystemExit) as error:
        main(
            [
                "--data-dir",
                str(_DATA),
                "--contract",
                str(_changed_contract(tmp_path, changed)),
                "--check",
            ]
        )
    assert error.value.code == 1
