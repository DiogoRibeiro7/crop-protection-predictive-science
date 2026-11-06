"""Prepare traceable source-protocol questions without clearing model gates.

The compiled review repeats the eligibility contract's actual outstanding
requirements for every observation table. Original README anchors are only
partial *context*, not experimental-design evidence or model permissions.
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
from crop_protection_ps.external_analysis_readiness import inventory_analysis_readiness

_ORIGINAL_DOCS = {
    "aphid_readme": "data/external/zenodo_aphid_pesticide_19805135/README.txt",
    "dryad_readme": "data/external/dryad_pathogen_temperature_4mw6m90jv/README.md",
}
_QUESTION_FIELDS = {"question", "evidence_needed", "context"}
_ANCHOR_FIELDS = {"document", "anchor"}
_REQUIREMENT_FIELDS = (
    "asset_id",
    "policy",
    "analysis",
    "requirement",
    "permission",
    "clearance",
    "local_context",
    "context_refs",
    "evidence_needed",
    "author_question",
)
_ANCHOR_OUTPUT_FIELDS = ("ref_id", "source_document", "source_line", "literal_anchor")


def _sha256(path: Path) -> str:
    """Hash immutable source bytes, not decoded or normalised content."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(raw: Any, label: str) -> dict[str, Any]:
    """Require JSON objects rather than silently accepting other shapes."""
    if not isinstance(raw, dict) or any(not isinstance(key, str) for key in raw):
        raise ValueError(f"invalid protocol review object: {label}")
    return raw


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys that would otherwise shadow review decisions."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate protocol-review configuration key: {key}")
        result[key] = value
    return result


def _source_anchors(
    root: Path, configured: Any
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Resolve exact README phrases to line numbers under checksum-pinned files."""
    source_anchors = _mapping(configured, "source_anchors")
    contents: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for doc, relative in _ORIGINAL_DOCS.items():
        path = root / relative
        contents[doc] = path.read_text(encoding="utf-8-sig")
        hashes[relative] = _sha256(path)

    found: dict[str, dict[str, Any]] = {}
    for name, raw in sorted(source_anchors.items()):
        anchor = _mapping(raw, f"source_anchors.{name}")
        if set(anchor) != _ANCHOR_FIELDS or anchor["document"] not in _ORIGINAL_DOCS:
            raise ValueError(f"unrecognised original-source anchor: {name}")
        phrase = anchor["anchor"]
        if not isinstance(phrase, str) or len(phrase) < 12:
            raise ValueError(f"invalid literal source anchor: {name}")
        content = contents[anchor["document"]]
        if content.count(phrase) != 1:
            raise ValueError(f"original-source anchor missing or ambiguous: {name}")
        line = content[: content.index(phrase)].count("\n") + 1
        found[name] = {
            "ref_id": name,
            "source_document": _ORIGINAL_DOCS[anchor["document"]],
            "source_line": line,
            "literal_anchor": phrase,
        }
    if not found:
        raise ValueError("protocol-review plan has no independently located source context")
    return found, hashes


def audit_external_protocol_review(
    data_dir: Path, questions_path: Path | None = None
) -> dict[str, Any]:
    """Match every outstanding model prerequisite to a targeted author request.

    The resulting questions remain *requests*: source README phrases are
    cited with exact line provenance, but cannot satisfy experimental-unit,
    randomization, missing-value or causal-identification requirements.
    """
    root = data_dir.resolve().parent
    contract_path = data_dir / "external/analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    readiness = inventory_analysis_readiness(data_dir)
    plan_path = questions_path or data_dir / "external/protocol_review_questions.json"
    plan = _mapping(
        json.loads(plan_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs),
        "root",
    )
    if (
        set(plan) != {"schema_version", "source_anchors", "requests"}
        or type(plan["schema_version"]) is not int
        or plan["schema_version"] != 1
    ):
        raise ValueError("unexpected protocol-review configuration schema")

    anchors, original_hashes = _source_anchors(root, plan["source_anchors"])
    requests = _mapping(plan["requests"], "requests")
    policies = contract["policies"]
    if set(requests) != set(policies):
        raise ValueError("unreviewed or missing protocol request policy")

    used_anchors: set[str] = set()
    reviewed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for policy_name, policy in sorted(policies.items()):
        policy_requests = _mapping(requests[policy_name], policy_name)
        if set(policy_requests) != set(policy["requires_protocol"]):
            raise ValueError(f"missing or unreviewed protocol question: {policy_name}")
        for analysis, requirements in sorted(policy["requires_protocol"].items()):
            question_group = _mapping(policy_requests[analysis], f"{policy_name}.{analysis}")
            if set(question_group) != set(requirements):
                raise ValueError(f"incomplete requirement coverage: {policy_name}.{analysis}")
            for requirement in requirements:
                item = _mapping(question_group[requirement], requirement)
                if set(item) != _QUESTION_FIELDS:
                    raise ValueError(f"invalid requirement request fields: {requirement}")
                question, evidence, refs = (
                    item["question"],
                    item["evidence_needed"],
                    item["context"],
                )
                if (
                    not isinstance(question, str)
                    or len(question) < 24
                    or not question.endswith("?")
                ):
                    raise ValueError(f"invalid source-specific author question: {requirement}")
                if not isinstance(evidence, str) or len(evidence) < 16:
                    raise ValueError(f"missing required evidence type: {requirement}")
                if (
                    not isinstance(refs, list)
                    or any(not isinstance(ref, str) for ref in refs)
                    or len(refs) != len(set(refs))
                    or any(ref not in anchors for ref in refs)
                ):
                    raise ValueError(f"invalid original-source context refs: {requirement}")
                used_anchors.update(refs)
                reviewed[(policy_name, analysis, requirement)] = {
                    "question": question,
                    "evidence_needed": evidence,
                    "context": refs,
                }
    if used_anchors != set(anchors):
        raise ValueError("unused or unreviewed original-source anchor")

    # The readiness ledger has itself crosschecked every existing descriptive
    # report and preserved all original gates; verify the same prerequisite keys.
    expected_gates = {
        (row["asset_id"], row["analysis"], row["requirement"])
        for row in readiness["protocol_requirements"]
    }
    rows: list[dict[str, str]] = []
    for asset in sorted(contract["assets"], key=lambda item: item["id"]):
        policy_name = asset["policy"]
        for analysis, requirements in sorted(policies[policy_name]["requires_protocol"].items()):
            if analysis_decision(contract, asset["id"], analysis)["status"] != "requires_protocol":
                raise ValueError("protocol question was incorrectly promoted to allowed")
            for requirement in requirements:
                item = reviewed[(policy_name, analysis, requirement)]
                refs = item["context"]
                rows.append(
                    {
                        "asset_id": asset["id"],
                        "policy": policy_name,
                        "analysis": analysis,
                        "requirement": requirement,
                        "permission": "requires_protocol",
                        "clearance": "not_cleared_by_contract",
                        "local_context": (
                            "original_readme_hint_only" if refs else "no_curated_readme_hint"
                        ),
                        "context_refs": ";".join(refs),
                        "evidence_needed": item["evidence_needed"],
                        "author_question": item["question"],
                    }
                )
    if {
        (row["asset_id"], row["analysis"], row["requirement"]) for row in rows
    } != expected_gates or len(rows) != readiness["protocol_requirement_rows"]:
        raise ValueError("source protocol requests disagree with research-readiness ledger")

    states = Counter(row["local_context"] for row in rows)
    return {
        "schema_version": 1,
        "analysis": "protocol_evidence_request_review_only",
        "contract_status": contract["contract_status"],
        "manifest_sha256": _sha256(data_dir / "external/manifest.json"),
        "analysis_contract_sha256": _sha256(contract_path),
        "research_readiness_sha256": _sha256(
            root / "results/external_analysis_readiness/summary.json"
        ),
        "protocol_questions_config_sha256": _sha256(plan_path),
        "original_readme_sha256": original_hashes,
        "source_assets": len(contract["assets"]),
        "policy_families": len(policies),
        "protocol_gated_question_rows": readiness["protocol_gated_question_rows"],
        "protocol_requirement_rows": len(rows),
        "unique_requirement_templates": len(reviewed),
        "source_anchor_count": len(anchors),
        "requirement_rows_with_source_context": states["original_readme_hint_only"],
        "requirement_rows_without_curated_context": states["no_curated_readme_hint"],
        "requirements_cleared": 0,
        "source_anchors": list(anchors.values()),
        "requirement_requests": rows,
        "review_templates": reviewed,
        "limitations": [
            "Original README context is only a source hint, not a reviewed protocol clearance.",
            "A missing curated README anchor does not prove the source paper lacks information.",
            "All 59 prerequisite entries retain their not_cleared_by_contract status.",
            "Duplicate policy questions across source assets are not independent evidence.",
            "No eligibility contract changes, inferential models or causal estimates are made.",
        ],
    }


def _csv(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    """Serialize checklists in stable source and contract order."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _markdown(report: Mapping[str, Any]) -> str:
    """Build one concise investigator evidence request per unique prerequisite."""
    anchors = {item["ref_id"]: item for item in report["source_anchors"]}
    templates = report["review_templates"]
    lines = [
        "# Protocol evidence requests for external source studies",
        "",
        "These questions are **not** a grant to fit treatment, temperature or causal models.",
        f"The 19 gated source-table questions require {report['protocol_requirement_rows']} "
        f"prerequisite entries, condensed here into {len(templates)} distinct requests.",
        "An archived README phrase provides context only; it never clears a gate.",
        "",
    ]
    previous: tuple[str, str] | None = None
    for (policy, analysis, requirement), item in sorted(templates.items()):
        group = (policy, analysis)
        if group != previous:
            lines.extend([f"## {policy}: {analysis}", ""])
            previous = group
        lines.append(f"### {requirement}")
        lines.append("")
        lines.append(f"- **Question:** {item['question']}")
        lines.append(f"- **Evidence requested:** {item['evidence_needed']}")
        refs = item["context"]
        if refs:
            parts = []
            for ref_id in refs:
                anchor = anchors[ref_id]
                path = anchor["source_document"]
                line = anchor["source_line"]
                parts.append(f"[{ref_id}](../../{path}#L{line}) (line {line})")
            lines.append(f"- **Existing original-source context only:** {', '.join(parts)}.")
        else:
            lines.append(
                "- **Original-source context:** No curated local README anchor; "
                "the full protocol may still contain this information."
            )
        lines.append("")
    lines.extend(
        [
            "## Review boundary",
            "",
            "The question list does not assert that the original authors omitted any "
            "requested details. Source papers, experimental logs and original analysis "
            "scripts may supply additional evidence, but each applicable prerequisite "
            "requires a separate scientific review and an explicit eligibility-contract "
            "revision before modelling.",
            "",
        ]
    )
    return "\n".join(lines)


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Separate provenance, repeatable per-asset rows and unique question prompts."""
    metadata = {
        key: value
        for key, value in report.items()
        if key not in {"source_anchors", "requirement_requests", "review_templates"}
    }
    return {
        "summary.json": json.dumps(metadata, indent=2) + "\n",
        "requirement_requests.csv": _csv(report["requirement_requests"], _REQUIREMENT_FIELDS),
        "original_source_anchors.csv": _csv(report["source_anchors"], _ANCHOR_OUTPUT_FIELDS),
        "author_evidence_requests.md": _markdown(report),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Regenerate or read-only check the source protocol review and author pack."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--questions", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("results/external_protocol_review"))
    parser.add_argument("--check", action="store_true", help="Verify files without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        files = render_reports(audit_external_protocol_review(args.data_dir, args.questions))
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError, csv.Error) as exc:
        parser.exit(1, f"external protocol evidence review failed: {exc}\n")
    if args.check:
        stale = [
            name
            for name, content in files.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"protocol review files missing or stale: {', '.join(stale)}\n")
        print(f"verified {len(files)} protocol review files in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {len(files)} protocol review files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
