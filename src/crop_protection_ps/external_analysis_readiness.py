"""Inventory audited descriptive exports and unresolved analysis gates.

This report is a roadmap, not an approval mechanism. All decisions come from
the checksum-verified analysis eligibility contract. A published descriptive
artifact cannot authorize a disease, treatment, or causal model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from crop_protection_ps.analysis_eligibility import (
    analysis_decision,
    validate_analysis_contract,
)

# The paths are a deliberately reviewed list of existing descriptive outputs.
# No report for the aggregate flower summary or the weather quality review is
# committed yet. Their descriptive permissions are nevertheless in force.
_EXPORTS: dict[str, str | None] = {
    "wheat_field": "results/external_wheat_pairability.json",
    "aphid_cohort": "results/external_aphid_controlled/summary.json",
    "aphid_field": "results/external_aphid_field/summary.json",
    "dryad_binomial_lab": "results/external_dryad_lab_assays/summary.json",
    "dryad_growth": "results/external_dryad_growth/summary.json",
    "dryad_greenhouse_infection": "results/external_dryad_greenhouse_status/summary.json",
    "dryad_greenhouse_death": "results/external_dryad_greenhouse_deaths/summary.json",
    "dryad_field": "results/external_dryad_field_statuses/summary.json",
    "dryad_summary": None,
    "dryad_weather": None,
}
_ALLOWED_FIELDS = (
    "asset_id",
    "policy",
    "source",
    "source_file",
    "source_table",
    "recorded_rows",
    "recorded_group_basis",
    "recorded_groups",
    "action",
    "permission",
    "export_state",
    "evidence_path",
)
_GATE_FIELDS = (
    "asset_id",
    "policy",
    "analysis",
    "permission",
    "requirement",
    "clearance",
)
_BLOCKED_FIELDS = ("asset_id", "policy", "analysis", "permission")


def _sha256(path: Path) -> str:
    """Hash bytes instead of the decoded/normalised file representation."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _integer_field(report: Mapping[str, Any], field: str, expected: int) -> None:
    """Check committed descriptive counts against the audited contract units."""
    if type(report.get(field)) is not int or report[field] != expected:
        raise ValueError(f"descriptive source-unit disagreement: {field}")


def _verify_export(
    root: Path,
    asset: Mapping[str, Any],
    action: str,
    evidence_path: str,
    manifest_sha: str,
    contract_sha: str,
) -> None:
    """Cross-check each committed export's action, provenance and units.

    This is a metadata consistency check, not a substitute for each exporting
    module's original-source regeneration test in the repository suite.
    """
    report_path = root / evidence_path
    if not report_path.is_file():
        raise ValueError(f"missing reviewed descriptive report: {evidence_path}")
    raw = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"invalid descriptive report: {evidence_path}")
    report: dict[str, Any] = raw
    policy = asset["policy"]
    rows, groups = asset["rows"], asset["group_count"]
    source_file = Path(asset["file"]).name

    if policy == "wheat_field":
        # The eligibility validator independently regenerates this evidence.
        if report.get("source_path") != asset["file"]:
            raise ValueError("wheat pairability source-path disagreement")
        _integer_field(report, "source_rows", rows)
        _integer_field(report, "trial_id_count", groups)
        return

    if (
        report.get("schema_version") != 1
        or report.get("analysis") != action
        or report.get("manifest_sha256") != manifest_sha
        or report.get("analysis_contract_sha256") != contract_sha
    ):
        raise ValueError(f"stale or mismatched descriptive provenance: {evidence_path}")

    if policy == "aphid_cohort":
        experiment = report["experiments"][asset["table"]]
        if experiment.get("source_sheet") != asset["table"]:
            raise ValueError("aphid cohort source-sheet disagreement")
        _integer_field(experiment, "source_records", rows)
        _integer_field(experiment, "condition_cells", groups)
    elif policy == "aphid_field":
        if report.get("source_sheet") != asset["table"]:
            raise ValueError("aphid field source-sheet disagreement")
        _integer_field(report["summary"], "source_record_count", rows)
        _integer_field(report["summary"], "provisional_series_count", groups)
    elif policy in {"dryad_binomial_lab", "dryad_growth"}:
        if policy == "dryad_binomial_lab":
            key = (
                "germination"
                if asset["id"] == "dryad_germination"
                else (f"conjugation_strain_{asset['id'].rsplit('_', 1)[-1]}")
            )
            detail = report["assays"][key]
        else:
            key = f"strain_{asset['id'].rsplit('_', 1)[-1]}"
            detail = report["strains"][key]
        if detail.get("source_file") != source_file:
            raise ValueError("Dryad assay source-file disagreement")
        _integer_field(detail, "source_record_count", rows)
        _integer_field(detail, "temperature_run_groups", groups)
    elif policy in {"dryad_greenhouse_infection", "dryad_greenhouse_death", "dryad_field"}:
        if (
            report.get("source_workbook") != source_file
            or report.get("source_sheet") != asset["table"]
        ):
            raise ValueError("Dryad plant source-table disagreement")
        row_field, group_field = {
            "dryad_greenhouse_infection": ("source_scored_rows", "recorded_visit_cells"),
            "dryad_greenhouse_death": ("source_death_case_rows", "recorded_case_cells"),
            "dryad_field": ("plant_rows", "unique_plant_keys"),
        }[policy]
        _integer_field(report, row_field, rows)
        _integer_field(report, group_field, groups)
    else:
        raise ValueError(f"unrecognised descriptive export policy: {policy}")


def inventory_analysis_readiness(data_dir: Path) -> dict[str, Any]:
    """Derive a non-promoting analysis checklist from validated source evidence."""
    root = data_dir.resolve().parent
    contract_path = data_dir / "external/analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    if set(contract["policies"]) != set(_EXPORTS):
        raise ValueError("unreviewed policy added to the descriptive export inventory")

    manifest_sha = _sha256(data_dir / "external/manifest.json")
    contract_sha = _sha256(contract_path)
    allowed: list[dict[str, Any]] = []
    gates: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []
    for asset in sorted(contract["assets"], key=lambda item: item["id"]):
        policy_name = asset["policy"]
        policy = contract["policies"][policy_name]
        if len(policy["allowed"]) != 2 or "structural_inventory" not in policy["allowed"]:
            raise ValueError("expected one scoped descriptive action per dataset policy")

        for action in sorted(policy["allowed"]):
            if analysis_decision(contract, asset["id"], action)["status"] != "allowed":
                raise ValueError("unexpected denied descriptive permission")
            path: str | None
            if action == "structural_inventory":
                path, state = "data/external/profile.json", "crosschecked_committed_report"
            else:
                path = _EXPORTS[policy_name]
                state = "crosschecked_committed_report" if path is not None else "not_exported"
                if path is not None:
                    # A shared report may cover several source sheets. Always
                    # verify each asset's own row and grouping counts.
                    _verify_export(root, asset, action, path, manifest_sha, contract_sha)
            allowed.append(
                {
                    "asset_id": asset["id"],
                    "policy": policy_name,
                    "source": asset["source"],
                    "source_file": asset["file"],
                    "source_table": asset["table"],
                    "recorded_rows": asset["rows"],
                    "recorded_group_basis": asset["group_basis"],
                    "recorded_groups": asset["group_count"],
                    "action": action,
                    "permission": "allowed_descriptive_only",
                    "export_state": state,
                    "evidence_path": path or "",
                }
            )

        for analysis, requirements in sorted(policy["requires_protocol"].items()):
            decision = analysis_decision(contract, asset["id"], analysis)
            if (
                decision["status"] != "requires_protocol"
                or decision["requirements"] != requirements
            ):
                raise ValueError("protocol-gated action was promoted or changed")
            for requirement in requirements:
                gates.append(
                    {
                        "asset_id": asset["id"],
                        "policy": policy_name,
                        "analysis": analysis,
                        "permission": "requires_protocol",
                        "requirement": requirement,
                        "clearance": "not_cleared_by_contract",
                    }
                )
        for analysis in sorted(policy["blocked"]):
            if analysis_decision(contract, asset["id"], analysis)["status"] != "blocked":
                raise ValueError("explicitly blocked action was promoted")
            blocked.append(
                {
                    "asset_id": asset["id"],
                    "policy": policy_name,
                    "analysis": analysis,
                    "permission": "blocked",
                }
            )

    states = Counter(item["export_state"] for item in allowed)
    return {
        "schema_version": 1,
        "contract_status": contract["contract_status"],
        "manifest_sha256": manifest_sha,
        "analysis_contract_sha256": contract_sha,
        "source_profile_sha256": _sha256(root / "data/external/profile.json"),
        "source_assets": len(contract["assets"]),
        "policy_families": len(contract["policies"]),
        "allowed_descriptive_rows": len(allowed),
        "crosschecked_descriptive_rows": states["crosschecked_committed_report"],
        "descriptive_rows_not_yet_exported": states["not_exported"],
        "protocol_requirement_rows": len(gates),
        "protocol_gated_question_rows": len({(row["asset_id"], row["analysis"]) for row in gates}),
        "explicitly_blocked_rows": len(blocked),
        "allowed_descriptions": allowed,
        "protocol_requirements": gates,
        "blocked_actions": blocked,
        "limitations": [
            "A committed descriptive report is metadata-crosschecked, not a model approval.",
            "A requirements checklist is not proof that a protocol element is absent.",
            "An aligned calendar date may still need protocol-level review.",
            "Recorded groups are not verified independent experimental units.",
            "No inferential action has permission in the current contract.",
            "No cross-publication candidate linkage or causal estimation is attempted.",
        ],
    }


def _csv(records: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    """Render a deterministic, spreadsheet-readable evidence checklist."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Avoid duplicating the full checklist in the JSON metadata summary."""
    details = {"allowed_descriptions", "protocol_requirements", "blocked_actions"}
    metadata = {key: value for key, value in report.items() if key not in details}
    return {
        "summary.json": json.dumps(metadata, indent=2) + "\n",
        "allowed_descriptives.csv": _csv(report["allowed_descriptions"], _ALLOWED_FIELDS),
        "protocol_requirements.csv": _csv(report["protocol_requirements"], _GATE_FIELDS),
        "blocked_analyses.csv": _csv(report["blocked_actions"], _BLOCKED_FIELDS),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Regenerate or check the offline research-readiness inventory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/external_analysis_readiness")
    )
    parser.add_argument("--check", action="store_true", help="Verify files without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        files = render_reports(inventory_analysis_readiness(args.data_dir))
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError, csv.Error) as exc:
        parser.exit(1, f"analysis readiness inventory failed: {exc}\n")
    if args.check:
        stale = [
            name
            for name, content in files.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"analysis readiness files missing or stale: {', '.join(stale)}\n")
        print(f"verified {len(files)} analysis readiness files in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {len(files)} analysis readiness files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
