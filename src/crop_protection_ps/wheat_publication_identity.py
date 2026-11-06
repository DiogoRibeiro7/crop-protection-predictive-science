"""Audit published wheat-trial counts against explicitly recorded grouping keys.

This module separates three *descriptive* groupings of a checksum-pinned
source. Neither matching geocodes nor matching publisher counts identify
physical experiments, randomized plots, or independent statistical units.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

from crop_protection_ps.analysis_eligibility import (
    analysis_decision,
    validate_analysis_contract,
)
from crop_protection_ps.wheat_site_hierarchy import (
    _SOURCE_DOI,
    _SOURCE_PATH,
    audit_wheat_site_data,
)

_EVIDENCE_PATH = Path("external/wheat_publication_evidence.json")
_SOURCE_RECORD = "https://zenodo.org/records/6521175"
_PUBLISHED_FILE_MD5 = {
    "basf-wheat-diseases.txt": "107ba039c535832223bf484acf1e5602",
    "basf-wheat-diseases.R": "b45c3c26f9e8d9cffff23f64c905b4f9",
    "setup.R": "2a90dfca4960ec49dd5eea14321d1e75",
    "basf-wheat-diseases.Rdata": "943b8cd7276896dc2753c46bb6ed0c51",
    "basf-wheat-diseases-map.png": "659c05fe78ac8fa01191ac48b6e0edf3",
}
_PUBLISHED_STATUSES = frozenset(
    {"locally_imported_and_checksum_verified", "publisher_text_read", "publisher_inventory_only"}
)
_REQUIRED_PROTOCOL = frozenset(
    {
        "reconcile_56_published_trials_vs_76_trial_ids",
        "plot_replicate_identity",
        "treatment_dictionary",
        "endpoint_protocol",
    }
)


def _sha256(path: Path) -> str:
    """Hash source bytes, without normalizing whitespace or line endings."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Prevent JSON duplicate keys from silently changing evidence claims."""
    values: dict[str, Any] = {}
    for key, value in pairs:
        if key in values:
            raise ValueError(f"duplicate publication-evidence key: {key}")
        values[key] = value
    return values


def _publication_evidence(path: Path, source_path: Path) -> dict[str, Any]:
    """Validate a manually reviewed record against pinned publisher file MD5s.

    Non-imported file digests are *transcribed from Zenodo*, not represented as
    locally verified file bytes. Their presence cannot establish plot design.
    """
    raw: Any = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "record_url",
        "record_doi",
        "record_version",
        "publisher_title",
        "publisher_trial_count",
        "publication_date",
        "reviewed_on",
        "review_scope",
        "publisher_files",
        "source_script_findings",
    }:
        raise ValueError("unexpected wheat publication evidence schema")
    if (
        type(raw["schema_version"]) is not int
        or raw["schema_version"] != 1
        or raw["record_url"] != _SOURCE_RECORD
        or raw["record_doi"] != _SOURCE_DOI
        or raw["record_version"] != "1.0"
        or type(raw["publisher_trial_count"]) is not int
        or raw["publisher_trial_count"] < 1
        or not isinstance(raw["publisher_title"], str)
        or str(raw["publisher_trial_count"]) not in raw["publisher_title"]
        or not isinstance(raw["review_scope"], str)
        or len(raw["review_scope"]) < 40
    ):
        raise ValueError("invalid publisher record identity or reported trial count")
    for date_field in ("publication_date", "reviewed_on"):
        if not isinstance(raw[date_field], str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw[date_field]
        ):
            raise ValueError(f"invalid publication evidence date: {date_field}")
        try:
            date.fromisoformat(raw[date_field])
        except ValueError as exc:
            raise ValueError(f"invalid calendar date: {date_field}") from exc
    if raw["reviewed_on"] < raw["publication_date"]:
        raise ValueError("source cannot be reviewed before publication")

    file_rows = raw["publisher_files"]
    if not isinstance(file_rows, list) or len(file_rows) != len(_PUBLISHED_FILE_MD5):
        raise ValueError("incomplete Zenodo release-file inventory")
    found: dict[str, str] = {}
    for item in file_rows:
        if not isinstance(item, dict) or set(item) != {"name", "md5", "review_status"}:
            raise ValueError("invalid Zenodo file inventory entry")
        name, md5, status = item["name"], item["md5"], item["review_status"]
        if (
            not isinstance(name, str)
            or name in found
            or not isinstance(md5, str)
            or _PUBLISHED_FILE_MD5.get(name) != md5
            or status not in _PUBLISHED_STATUSES
        ):
            raise ValueError(f"unverified published file identity: {name!r}")
        found[name] = status
    if set(found) != set(_PUBLISHED_FILE_MD5) or found["basf-wheat-diseases.txt"] != (
        "locally_imported_and_checksum_verified"
    ):
        raise ValueError("publisher inventory does not match local source snapshot")
    for script in ("basf-wheat-diseases.R", "setup.R"):
        if found[script] != "publisher_text_read":
            raise ValueError(f"unreviewed original source script: {script}")
    for binary in ("basf-wheat-diseases.Rdata", "basf-wheat-diseases-map.png"):
        if found[binary] != "publisher_inventory_only":
            raise ValueError(f"unsupported review claim for source file: {binary}")
    if (
        hashlib.md5(source_path.read_bytes()).hexdigest()
        != _PUBLISHED_FILE_MD5["basf-wheat-diseases.txt"]
    ):
        raise ValueError("local wheat TSV differs from the original Zenodo MD5")

    findings = raw["source_script_findings"]
    if not isinstance(findings, list) or len(findings) != 2:
        raise ValueError("source-script reading scope is incomplete")
    covered: set[str] = set()
    for item in findings:
        if not isinstance(item, dict) or set(item) != {
            "file",
            "source_url",
            "observed_purpose",
            "trial_dictionary_defined_in_reviewed_script",
        }:
            raise ValueError("malformed reviewed source-script finding")
        name = item["file"]
        if (
            name not in {"basf-wheat-diseases.R", "setup.R"}
            or name in covered
            or item["source_url"] != f"{_SOURCE_RECORD}/files/{name}?download=1"
            or not isinstance(item["observed_purpose"], str)
            or len(item["observed_purpose"]) < 25
            or item["trial_dictionary_defined_in_reviewed_script"] is not False
        ):
            raise ValueError(f"unsubstantiated source-script finding: {name!r}")
        covered.add(name)
    if covered != {"basf-wheat-diseases.R", "setup.R"}:
        raise ValueError("missing source-script review")
    return raw


def summarize_wheat_identity_scenarios(
    hierarchy: Mapping[str, Any], publisher_count: int
) -> dict[str, Any]:
    """Decompose only code/grouping-count gaps, never assign trial identity."""
    if type(publisher_count) is not int or publisher_count < 1:
        raise ValueError("publisher count must be a positive integer")
    trial_ids = hierarchy["trial_id_count"]
    site_years = hierarchy["geocode_year_count"]
    geocodes = hierarchy["geocode_count"]
    if not all(type(item) is int for item in (trial_ids, site_years, geocodes)) or not (
        trial_ids >= site_years >= geocodes >= 1
    ):
        raise ValueError("invalid trial-code/geocode hierarchy counts")
    if trial_ids - site_years != sum(
        len(group["trial_ids"]) - 1 for group in hierarchy["shared_geocode_years"]
    ):
        raise ValueError("shared-year grouping gaps disagree with source hierarchy")
    if site_years - geocodes != sum(
        len(site["trial_ids_by_year"]) - 1 for site in hierarchy["reused_geocodes"]
    ):
        raise ValueError("cross-year grouping gaps disagree with source hierarchy")
    return {
        "source_trial_id_codes": trial_ids,
        "distinct_recorded_geocode_years": site_years,
        "distinct_recorded_geocodes": geocodes,
        "published_trial_count": publisher_count,
        "trial_ids_above_geocode_year_count": trial_ids - site_years,
        "geocode_years_above_geocode_count": site_years - geocodes,
        "trial_ids_above_geocode_count": trial_ids - geocodes,
        "published_count_equals_geocode_count": publisher_count == geocodes,
        "published_count_equals_geocode_year_count": publisher_count == site_years,
        "published_count_equals_trial_id_count": publisher_count == trial_ids,
        "geocode_years_with_multiple_trial_ids": hierarchy["geocode_years_with_multiple_trial_ids"],
        "geocodes_reused_across_years": hierarchy["geocodes_reused_across_years"],
    }


def audit_wheat_publication_identity(
    data_dir: Path, evidence_path: Path | None = None
) -> dict[str, Any]:
    """Cross-check original publisher metadata, observed keys and model gate."""
    hierarchy = audit_wheat_site_data(data_dir)
    source_path = data_dir / "external" / _SOURCE_PATH
    reviewed_path = evidence_path or data_dir / _EVIDENCE_PATH
    publication = _publication_evidence(reviewed_path, source_path)
    manifest = json.loads((data_dir / "external/manifest.json").read_text(encoding="utf-8"))
    source_entries = [
        entry for entry in manifest["sources"] if entry["id"] == "zenodo_wheat_fungicide_6521175"
    ]
    if (
        len(source_entries) != 1
        or publication["publisher_title"] != source_entries[0]["title"]
        or publication["record_url"] != source_entries[0]["url"]
        or publication["record_doi"] != source_entries[0]["doi"]
    ):
        raise ValueError("publisher release description disagrees with pinned source manifest")
    contract = validate_analysis_contract(data_dir, data_dir / "external/analysis_eligibility.json")
    decision = analysis_decision(contract, "wheat_field", "trial_level_treatment_effect")
    requirements = decision.get("requirements")
    if (
        decision["status"] != "requires_protocol"
        or not isinstance(requirements, list)
        or not _REQUIRED_PROTOCOL.issubset(set(requirements))
    ):
        raise ValueError("original wheat protocol gate was changed or incompletely reviewed")

    scenarios = summarize_wheat_identity_scenarios(hierarchy, publication["publisher_trial_count"])
    return {
        "schema_version": 1,
        "analysis": "descriptive_wheat_publication_identity_evidence_only",
        "source_doi": _SOURCE_DOI,
        "source_record_url": _SOURCE_RECORD,
        "source_path": _SOURCE_PATH,
        "source_sha256": hierarchy["source_sha256"],
        "publication_evidence_path": reviewed_path.relative_to(data_dir.parent).as_posix()
        if reviewed_path.is_relative_to(data_dir.parent)
        else str(reviewed_path),
        "publication_evidence_sha256": _sha256(reviewed_path),
        "published_record_version": publication["record_version"],
        "publisher_source_file_count": len(publication["publisher_files"]),
        "source_scripts_reviewed": [item["file"] for item in publication["source_script_findings"]],
        "uninspected_publisher_files": [
            item["name"]
            for item in publication["publisher_files"]
            if item["review_status"] == "publisher_inventory_only"
        ],
        "counts": scenarios,
        "maximum_shared_geocode_year": max(
            hierarchy["shared_geocode_years"],
            key=lambda group: len(group["trial_ids"]),
            default=None,
        ),
        "cross_year_geocode_example": max(
            hierarchy["reused_geocodes"],
            key=lambda site: len(site["trial_ids_by_year"]),
            default=None,
        ),
        "model_permission": decision["status"],
        "remaining_protocol_requirements": requirements,
        "experimental_unit_identity_established": False,
        "inference_permitted": False,
        "limitations": [
            "Equal counts do not prove that 56 published trials are 56 rounded geocodes.",
            "0.1-degree geocodes cannot identify physical experiments, plots or replicates.",
            "Publisher R scripts were read for mapping and loading logic only, not study design.",
            "The publisher binary Rdata and map image were inventoried but not examined.",
            "No 76-to-56 mapping, treatment assignment or treatment effects are asserted.",
        ],
    }


def wheat_author_evidence_request(report: Mapping[str, Any]) -> str:
    """Build a source-specific, reviewable request from the verified hierarchy."""
    counts = report["counts"]
    largest = report["maximum_shared_geocode_year"]
    cross_year = report["cross_year_geocode_example"]
    if largest is None or cross_year is None:
        raise ValueError("cannot show collision examples without source cases")
    values = ", ".join(f"`{item}`" for item in largest["trial_ids"])
    year_values = ", ".join(
        f"{item['year']} ({', '.join(item['trial_ids'])})"
        for item in cross_year["trial_ids_by_year"]
    )
    return (
        "# Original-source request: wheat trial and plot identities\n\n"
        f"Source: [{report['source_doi']}]({report['source_record_url']}); "
        f"checksum-verified local TSV: `{report['source_path']}`.\n\n"
        "## Verified discrepancies (not reconciliations)\n\n"
        f"- Publisher title: **{counts['published_trial_count']} trials**.\n"
        f"- Raw file: **{counts['source_trial_id_codes']} `TrialId` codes**, "
        f"**{counts['distinct_recorded_geocode_years']} recorded geocode-years**, "
        f"**{counts['distinct_recorded_geocodes']} recorded geocodes**.\n"
        f"- Codes above geocode-year groups: **{counts['trial_ids_above_geocode_year_count']}**; "
        f"geocode-years above geocodes: **{counts['geocode_years_above_geocode_count']}**. "
        "These counts do not establish physical trial identities.\n"
        f"- Shared geocode-year example: {largest['country']} "
        f"({largest['latitude']}, {largest['longitude']}) in {largest['year']} "
        f"contains codes {values}.\n"
        f"- Across-year example: {cross_year['country']} "
        f"({cross_year['latitude']}, {cross_year['longitude']}) "
        f"has {year_values}.\n\n"
        "## Documents to request from BASF / the Zenodo depositor\n\n"
        "1. The authoritative definition of a published *trial* and a "
        "machine-readable `TrialId` to physical trial/site/field/plot "
        "crosswalk, covering all 76 codes and explaining the advertised 56.\n"
        "2. Trial layouts, randomized treatment allocation, experimental "
        "units, block and plot replicate IDs; specifically explain codes "
        "sharing a rounded geocode and year.\n"
        "3. Whether experiments at the same rounded geocode in different "
        "years are physically and statistically distinct; provide the "
        "unrounded location or site identifiers if releasable.\n"
        "4. Full fungicide product/active-substance, dose and application "
        "dictionary, with `Treatment` code mapping and control definition.\n"
        "5. Assessment protocol by `Organism`/`Parameter`: timing, unit, "
        "missing-value coding, repeated measurement links and yield basis.\n"
        "6. The original protocol/data dictionary and, if available, "
        "documentation of the published `obs` R object. The public R "
        "scripts inspected so far only load, summarize and map the data.\n\n"
        "## Decision boundary\n\n"
        "The current `trial_level_treatment_effect` decision remains "
        "`requires_protocol`; no treatment-effect analysis is authorized by "
        "a numerical 56/56 match. No researchers have been contacted.\n"
    )


def main(argv: Iterable[str] | None = None) -> int:
    """Generate or check the publication audit and investigator request offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/external_wheat_publication_identity.json")
    )
    parser.add_argument(
        "--request-output",
        type=Path,
        default=Path("results/external_wheat_protocol_identity_request.md"),
    )
    parser.add_argument("--check", action="store_true", help="Check committed files only")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = audit_wheat_publication_identity(args.data_dir)
        content = json.dumps(report, indent=2) + "\n"
        request = wheat_author_evidence_request(report)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"wheat publication audit failed: {exc}\n")
    artifacts: Sequence[tuple[Path, str]] = (
        (args.output, content),
        (args.request_output, request),
    )
    for path, expected in artifacts:
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                parser.exit(1, f"wheat publication artifact missing or stale: {path}\n")
            print(f"wheat publication artifact matches source: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
            print(f"wrote wheat publication artifact: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
