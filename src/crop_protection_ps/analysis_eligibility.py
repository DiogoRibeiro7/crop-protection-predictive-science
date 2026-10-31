"""Fail-closed analysis permissions for independently audited external datasets.

The checked-in contract is a statement of *current evidence*, not an inference
that experimental units are independent. Protocol-gated analyses are never
automatically approved by passing a command-line flag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from crop_protection_ps.aphid_dryad_units import audit_aphid_dryad
from crop_protection_ps.external_profile import profile_external_data
from crop_protection_ps.wheat_pairability import audit_wheat_data

_CONTRACT_RELATIVE = Path("external/analysis_eligibility.json")
_EVIDENCE_PATHS = frozenset(
    {
        "data/external/manifest.json",
        "data/external/profile.json",
        "results/external_wheat_pairability.json",
        "results/external_aphid_dryad_units.json",
    }
)
_DESCRIPTIVE_ACTIONS = frozenset(
    {
        "structural_inventory",
        "matched_endpoint_coverage",
        "condition_mortality_description",
        "within_series_mortality_description",
        "assay_count_description",
        "colony_count_description",
        "disease_status_frequencies",
        "death_case_tally",
        "within_plant_status_description",
        "aggregate_flowering_description",
        "source_weather_quality_review",
    }
)
_POLICY_ALLOWED = {
    "wheat_field": {"structural_inventory", "matched_endpoint_coverage"},
    "aphid_cohort": {"structural_inventory", "condition_mortality_description"},
    "aphid_field": {"structural_inventory", "within_series_mortality_description"},
    "dryad_binomial_lab": {"structural_inventory", "assay_count_description"},
    "dryad_growth": {"structural_inventory", "colony_count_description"},
    "dryad_greenhouse_infection": {"structural_inventory", "disease_status_frequencies"},
    "dryad_greenhouse_death": {"structural_inventory", "death_case_tally"},
    "dryad_field": {"structural_inventory", "within_plant_status_description"},
    "dryad_summary": {"structural_inventory", "aggregate_flowering_description"},
    "dryad_weather": {"structural_inventory", "source_weather_quality_review"},
}
_WHEAT = "zenodo_wheat_fungicide_6521175"
_APHID = "zenodo_aphid_pesticide_19805135"
_DRYAD = "dryad_pathogen_temperature_4mw6m90jv"


def _object(value: Any, context: str) -> dict[str, Any]:
    """Require an object whose keys are strings, with useful error context."""
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{context} must be a JSON object with string keys")
    return value


def _array(value: Any, context: str) -> list[Any]:
    """Require an array, explicitly rejecting strings and other iterables."""
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a JSON array")
    return value


def _names(value: Any, context: str) -> set[str]:
    """Reject duplicate, empty, and non-string action or requirement names."""
    values = _array(value, context)
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{context} needs nonempty strings")
    names = set(values)
    if len(names) != len(values):
        raise ValueError(f"{context} has duplicate names")
    return names


def _observations(profile: Mapping[str, Any]) -> dict[tuple[str, str], tuple[str, int]]:
    """Index observation sheets from the verified structural source profile."""
    result: dict[tuple[str, str], tuple[str, int]] = {}
    for raw_source in _array(profile["sources"], "profile.sources"):
        source = _object(raw_source, "profile.source")
        for raw_file in _array(source["files"], "profile.source.files"):
            source_file = _object(raw_file, "profile.source.file")
            for raw_table in _array(source_file["tables"], "profile.source.file.tables"):
                table = _object(raw_table, "profile.source.file.table")
                if table["role"] != "observations":
                    continue
                key = (source_file["path"], table["name"])
                if key in result:
                    raise ValueError(f"duplicate observation sheet: {key}")
                result[key] = (source["id"], table["rows"])
    return result


def _audited_group(
    asset: Mapping[str, Any], wheat: Mapping[str, Any], other: Mapping[str, Any]
) -> tuple[str, str, int]:
    """Resolve policy and grouping evidence without trusting the contract claim."""
    source = asset["source"]
    filename = Path(asset["file"]).name
    table = asset["table"]
    if source == _WHEAT and asset["file"] == wheat["source_path"]:
        return "wheat_field", "trial_id_codes", wheat["trial_id_count"]
    if source == _APHID and filename == "Experiment.xlsx":
        aphid = _object(other["aphid"], "aphid audit")
        controlled = _object(aphid["controlled"], "aphid controlled audit")
        if table in controlled:
            study = _object(controlled[table], "aphid experiment audit")
            return "aphid_cohort", "condition_cells", study["condition_cells"]
        if table == "Experiment5":
            field = _object(aphid["field"], "aphid field audit")
            return "aphid_field", "provisional_field_series", field["provisional_series_count"]
    if source == _DRYAD:
        dryad = _object(other["dryad"], "Dryad audit")
        laboratory = _object(dryad["laboratory"], "Dryad laboratory audit")
        if filename in laboratory:
            lab = _object(laboratory[filename], "Dryad assay audit")
            policy = "dryad_growth" if lab["assay"] == "growth" else "dryad_binomial_lab"
            return policy, "temperature_run_groups", lab["temperature_run_groups"]
        greenhouse = _object(dryad["greenhouse"], "Dryad greenhouse audit")
        field = _object(dryad["field"], "Dryad field audit")
        weather = _object(dryad["weather"], "Dryad weather audit")
        summaries = {
            "seedling_inoculation-_infection_data.xlsx": (
                "dryad_greenhouse_infection",
                "recorded_design_cells",
                greenhouse["infection_design_cells"],
            ),
            "seedling_inoculation-_death_data.xlsx": (
                "dryad_greenhouse_death",
                "recorded_design_cells",
                greenhouse["death_design_cells"],
            ),
            "Raw_field_data.xlsx": (
                "dryad_field",
                "unique_row_position_pairs",
                field["unique_row_position_pairs"],
            ),
            "flower_summary_data.xlsx": (
                "dryad_summary",
                "summary_dates",
                field["flower_summary_dates"],
            ),
            "daily_high_temps.txt": ("dryad_weather", "weather_dates", weather["weather_rows"]),
        }
        if filename in summaries:
            return summaries[filename]
    raise ValueError(f"unmapped observation sheet: {source}/{filename}:{table}")


def _validate_policies(raw: Any) -> dict[str, Any]:
    """Ensure no policy can promote inferential work into descriptive permissions."""
    policies = _object(raw, "policies")
    if set(policies) != set(_POLICY_ALLOWED):
        raise ValueError("the contract has missing or unexpected policies")
    for name, raw_policy in policies.items():
        policy = _object(raw_policy, f"policy {name}")
        if set(policy) != {"allowed", "requires_protocol", "blocked"}:
            raise ValueError(f"policy {name} has missing or unexpected fields")
        allowed = _names(policy["allowed"], f"{name}.allowed")
        blocked = _names(policy["blocked"], f"{name}.blocked")
        deferred = _object(policy["requires_protocol"], f"{name}.requires_protocol")
        if not allowed or "structural_inventory" not in allowed or not blocked or not deferred:
            raise ValueError(f"policy {name} needs descriptive, deferred and blocked actions")
        if not allowed <= _DESCRIPTIVE_ACTIONS:
            raise ValueError(f"policy {name} attempts to allow non-descriptive analysis")
        if allowed != _POLICY_ALLOWED[name]:
            raise ValueError(f"policy {name} has altered its safe descriptive actions")
        if allowed & (blocked | set(deferred)) or blocked & set(deferred):
            raise ValueError(f"policy {name} assigns conflicting analysis statuses")
        for action, requirements in deferred.items():
            if not action.strip() or not _names(requirements, f"{name}.{action}.requirements"):
                raise ValueError(f"policy {name} has a deferred action without prerequisites")
    return policies


def _verified_report(root: Path, relative: str, regenerate: Mapping[str, Any]) -> dict[str, Any]:
    """Reject checked-in audit reports that disagree with the unmodified inputs."""
    report = _object(json.loads((root / relative).read_text(encoding="utf-8")), relative)
    if report != regenerate:
        raise ValueError(f"stale external audit report: {relative}")
    return report


def validate_analysis_contract(data_dir: Path, contract_path: Path) -> dict[str, Any]:
    """Validate provenance, complete sheet coverage, and conservative permissions.

    Reads original public source snapshots but does not modify files or connect
    to the network. A stale source snapshot or unreviewed observation sheet
    invalidates the entire contract instead of silently enabling analysis.
    """
    root = data_dir.resolve().parent
    contract = _object(json.loads(contract_path.read_text(encoding="utf-8")), "contract")
    if set(contract) != {
        "schema_version",
        "contract_status",
        "evidence_sha256",
        "policies",
        "assets",
    }:
        raise ValueError("analysis contract has missing or unexpected top-level fields")
    if contract["schema_version"] != 1 or contract["contract_status"] != "protocol_review_pending":
        raise ValueError("unsupported analysis contract version or status")

    expected_hashes = _object(contract["evidence_sha256"], "evidence_sha256")
    if set(expected_hashes) != _EVIDENCE_PATHS:
        raise ValueError("evidence_sha256 must pin all and only the four audited reports")
    for relative in sorted(_EVIDENCE_PATHS):
        expected = expected_hashes[relative]
        actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if not isinstance(expected, str) or len(expected) != 64 or expected != actual:
            raise ValueError(f"outdated or invalid evidence checksum: {relative}")

    profile = _verified_report(root, "data/external/profile.json", profile_external_data(data_dir))
    wheat = _verified_report(
        root, "results/external_wheat_pairability.json", audit_wheat_data(data_dir)
    )
    other = _verified_report(
        root, "results/external_aphid_dryad_units.json", audit_aphid_dryad(data_dir)
    )
    observations = _observations(profile)
    policies = _validate_policies(contract["policies"])
    seen_ids: set[str] = set()
    seen_tables: set[tuple[str, str]] = set()
    seen_policies: set[str] = set()
    for raw_asset in _array(contract["assets"], "assets"):
        asset = _object(raw_asset, "asset")
        required = {"id", "source", "file", "table", "policy", "rows", "group_basis", "group_count"}
        if set(asset) != required:
            raise ValueError(f"asset has missing or unexpected fields: {asset.get('id')}")
        identifier = asset["id"]
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen_ids:
            raise ValueError(f"duplicate or invalid asset ID: {identifier}")
        seen_ids.add(identifier)
        key = (asset["file"], asset["table"])
        if key not in observations or key in seen_tables:
            raise ValueError(f"unprofiled or duplicate observation table: {key}")
        seen_tables.add(key)
        source, rows = observations[key]
        if asset["source"] != source or type(asset["rows"]) is not int or asset["rows"] != rows:
            raise ValueError(f"source or row-count mismatch for {identifier}")
        policy, basis, count = _audited_group(asset, wheat, other)
        if (
            asset["policy"] != policy
            or asset["group_basis"] != basis
            or type(asset["group_count"]) is not int
            or asset["group_count"] != count
        ):
            raise ValueError(f"audited group or policy mismatch for {identifier}")
        if policy not in policies:
            raise ValueError(f"asset {identifier} refers to undefined policy: {policy}")
        seen_policies.add(policy)
    if seen_tables != set(observations):
        missing = set(observations) - seen_tables
        raise ValueError(f"contract does not cover all observation tables: {missing}")
    if seen_policies != set(policies):
        raise ValueError(f"contract has unused policies: {set(policies) - seen_policies}")
    return contract


def analysis_decision(
    contract: Mapping[str, Any], dataset_id: str, analysis: str
) -> dict[str, Any]:
    """Return an explicit decision; unknown datasets and actions are blocked."""
    for raw_asset in contract["assets"]:
        if raw_asset["id"] != dataset_id:
            continue
        policy = contract["policies"][raw_asset["policy"]]
        decision: dict[str, Any] = {"dataset": dataset_id, "analysis": analysis}
        if analysis in policy["allowed"]:
            return {**decision, "status": "allowed", "reason": "descriptive_only"}
        if analysis in policy["requires_protocol"]:
            return {
                **decision,
                "status": "requires_protocol",
                "requirements": policy["requires_protocol"][analysis],
            }
        if analysis in policy["blocked"]:
            return {**decision, "status": "blocked", "reason": "explicitly_prohibited"}
        return {**decision, "status": "blocked", "reason": "unrecognized_analysis"}
    return {
        "dataset": dataset_id,
        "analysis": analysis,
        "status": "blocked",
        "reason": "unknown_dataset",
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Check evidence freshness or query permission; never approve gated analyses."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--contract", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="Validate evidence and contract")
    parser.add_argument("--dataset", help="Audited asset identifier")
    parser.add_argument("--analysis", help="Requested action identifier")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.check and (not args.dataset or not args.analysis):
        parser.error("provide --check or both --dataset and --analysis")
    if args.check and (args.dataset or args.analysis):
        parser.error("--check cannot be combined with a decision query")
    contract_path = args.contract or args.data_dir / _CONTRACT_RELATIVE
    try:
        contract = validate_analysis_contract(args.data_dir, contract_path)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"analysis eligibility evidence invalid: {exc}\n")
    if args.check:
        print(f"validated {len(contract['assets'])} observation tables")
        return 0
    decision = analysis_decision(contract, args.dataset, args.analysis)
    print(json.dumps(decision, indent=2))
    return 0 if decision["status"] == "allowed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
