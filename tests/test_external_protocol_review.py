"""Fail-closed tests for traceable but still uncleared source-protocol requests."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest

import crop_protection_ps.external_protocol_review as module
from crop_protection_ps.external_analysis_readiness import inventory_analysis_readiness
from crop_protection_ps.external_protocol_review import (
    audit_external_protocol_review,
    main,
    render_reports,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_protocol_review"
_QUESTIONS = _ROOT / "data/external/protocol_review_questions.json"


def _rows(content: str) -> list[dict[str, str]]:
    """Parse source-review CSVs without coercing protocol labels."""
    return list(csv.DictReader(io.StringIO(content)))


def _plan() -> dict[str, Any]:
    """Copy reviewed request data for mutation tests."""
    return json.loads(_QUESTIONS.read_text(encoding="utf-8"))


def _candidate(tmp_path: Path, plan: dict[str, Any]) -> Path:
    """Write an alternative request plan, never changing original sources."""
    path = tmp_path / "candidate_questions.json"
    path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    return path


def test_source_contract_and_readmes_reproduce_all_checked_in_outputs() -> None:
    report = audit_external_protocol_review(_ROOT / "data")
    files = render_reports(report)
    assert set(files) == {
        "summary.json",
        "requirement_requests.csv",
        "original_source_anchors.csv",
        "author_evidence_requests.md",
    }
    for filename, content in files.items():
        assert (_OUTPUT / filename).read_text(encoding="utf-8") == content
    summary = json.loads(files["summary.json"])
    assert summary["contract_status"] == "protocol_review_pending"
    assert summary["analysis"] == "protocol_evidence_request_review_only"
    assert summary["source_assets"] == 18
    assert summary["policy_families"] == 10
    assert summary["protocol_gated_question_rows"] == 19
    assert summary["protocol_requirement_rows"] == 59
    assert summary["unique_requirement_templates"] == 35
    assert summary["source_anchor_count"] == 14
    assert summary["requirement_rows_with_source_context"] == 41
    assert summary["requirement_rows_without_curated_context"] == 18
    assert summary["requirements_cleared"] == 0
    assert len(summary["original_readme_sha256"]) == 2
    assert "requirement_requests" not in summary
    assert "review_templates" not in summary


def test_all_contract_prerequisites_remain_uncleared_and_source_grounded() -> None:
    report = audit_external_protocol_review(_ROOT / "data")
    rows = _rows(render_reports(report)["requirement_requests.csv"])
    previous = inventory_analysis_readiness(_ROOT / "data")["protocol_requirements"]
    assert len(rows) == len(previous) == 59
    assert {
        (row["asset_id"], row["analysis"], row["requirement"], row["permission"], row["clearance"])
        for row in rows
    } == {
        (row["asset_id"], row["analysis"], row["requirement"], row["permission"], row["clearance"])
        for row in previous
    }
    assert all(row["author_question"].endswith("?") for row in rows)
    assert all(row["evidence_needed"] for row in rows)
    assert all(row["permission"] == "requires_protocol" for row in rows)
    assert all(row["clearance"] == "not_cleared_by_contract" for row in rows)
    assert {row["local_context"] for row in rows} == {
        "original_readme_hint_only",
        "no_curated_readme_hint",
    }
    assert sum(row["policy"] == "aphid_cohort" for row in rows) == 12
    assert sum(row["policy"] == "dryad_growth" for row in rows) == 9
    assert sum(row["policy"] == "wheat_field" for row in rows) == 4
    assert all(
        row["local_context"] == "no_curated_readme_hint"
        for row in rows
        if row["policy"] == "wheat_field"
    )


def test_source_anchor_lines_point_to_actual_unchanged_original_text() -> None:
    report = audit_external_protocol_review(_ROOT / "data")
    anchors = _rows(render_reports(report)["original_source_anchors.csv"])
    assert len(anchors) == 14
    assert {anchor["ref_id"] for anchor in anchors} == {
        ref for item in report["review_templates"].values() for ref in item["context"]
    }
    for anchor in anchors:
        text = (_ROOT / anchor["source_document"]).read_text(encoding="utf-8-sig")
        line_index = int(anchor["source_line"]) - 1
        assert anchor["literal_anchor"] in text.splitlines()[line_index]
        assert text.count(anchor["literal_anchor"]) == 1
    station = next(anchor for anchor in anchors if anchor["ref_id"] == "dryad_station")
    assert station["source_line"] == "107"
    replicate = next(anchor for anchor in anchors if anchor["ref_id"] == "aphid_field_replicate")
    assert replicate["source_line"] == "63"


def test_author_request_markdown_does_not_claim_to_clear_permission() -> None:
    content = render_reports(audit_external_protocol_review(_ROOT / "data"))[
        "author_evidence_requests.md"
    ]
    assert content.count("\n## ") == 12  # Eleven analyses and the final review boundary.
    assert content.count("\n### ") == 35
    assert "An archived README phrase provides context only" in content
    assert "../../data/external/dryad_pathogen_temperature_4mw6m90jv/README.md#L107" in content
    assert "the full protocol may still contain this information" in content
    assert "before modelling" in content


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("missing_policy", "unreviewed or missing protocol request policy"),
        ("missing_requirement", "incomplete requirement coverage"),
        ("extra_requirement", "incomplete requirement coverage"),
        ("unknown_ref", "invalid original-source context refs"),
        ("duplicate_ref", "invalid original-source context refs"),
        ("missing_anchor", "original-source anchor missing or ambiguous"),
        ("unknown_document", "unrecognised original-source anchor"),
        ("missing_question", "invalid requirement request fields"),
        ("non_question", "invalid source-specific author question"),
    ],
)
def test_invalid_or_unsupported_review_plan_fails_closed(
    tmp_path: Path, mutation: str, error: str
) -> None:
    plan = _plan()
    requests = plan["requests"]["dryad_weather"]["weather_exposure_model"]
    item = requests["resolve_missing_temperature"]
    if mutation == "missing_policy":
        plan["requests"].pop("wheat_field")
    elif mutation == "missing_requirement":
        requests.pop("resolve_low_above_high")
    elif mutation == "extra_requirement":
        requests["new_model_permission"] = item
    elif mutation == "unknown_ref":
        item["context"] = ["nonexistent_method_document"]
    elif mutation == "duplicate_ref":
        item["context"] *= 2
    elif mutation == "missing_anchor":
        plan["source_anchors"]["dryad_station"]["anchor"] = "no such station documented here"
    elif mutation == "unknown_document":
        plan["source_anchors"]["dryad_station"]["document"] = "../outside"
    elif mutation == "missing_question":
        item.pop("question")
    else:
        item["question"] = "No question"
    with pytest.raises(ValueError, match=error):
        audit_external_protocol_review(_ROOT / "data", _candidate(tmp_path, plan))


def test_repeated_json_key_fails_without_silent_override(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate protocol-review configuration key"):
        audit_external_protocol_review(_ROOT / "data", path)


def test_model_permission_cannot_be_promoted_by_review(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module.analysis_decision

    def invalid_decision(contract: dict[str, Any], asset: str, analysis: str) -> dict[str, Any]:
        """Simulate a downstream attempt to promote a protocol-gated action."""
        if asset == "dryad_daily_weather" and analysis == "weather_exposure_model":
            return {"status": "allowed"}
        return original(contract, asset, analysis)

    monkeypatch.setattr(module, "analysis_decision", invalid_decision)
    with pytest.raises(ValueError, match="incorrectly promoted"):
        audit_external_protocol_review(_ROOT / "data")


def test_check_mode_is_read_only_and_rejects_stale_outputs(tmp_path: Path) -> None:
    target = tmp_path / "protocol_review"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(target)]
    with pytest.raises(SystemExit) as missing:
        main([*args, "--check"])
    assert missing.value.code == 1
    assert not target.exists()
    assert main(args) == 0
    original = {path.name: path.read_bytes() for path in target.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {path.name: path.read_bytes() for path in target.iterdir()} == original
    (target / "author_evidence_requests.md").write_text("outdated\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stale:
        main([*args, "--check"])
    assert stale.value.code == 1
