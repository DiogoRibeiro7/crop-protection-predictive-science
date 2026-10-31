"""Compare observations of trial IDs sharing a rounded wheat geocode/year.

Agreement on dates, endpoints, or opaque treatment labels is descriptive
evidence only. It cannot establish shared physical plots, replicates,
randomization, or the meaning of the publisher's 56-trial count.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any

from crop_protection_ps.wheat_pairability import _FIELDS, ENDPOINT_FIELDS, _read_wheat_rows
from crop_protection_ps.wheat_site_hierarchy import (
    _SOURCE_DOI,
    _SOURCE_PATH,
    audit_wheat_site_data,
    audit_wheat_site_rows,
)

_SIGNATURE_FIELDS = tuple(field for field in ENDPOINT_FIELDS if field != "TrialId")
_ARM_FIELDS = (*_SIGNATURE_FIELDS, "Treatment")
_RAW_RECORD_FIELDS = tuple(field for field in _FIELDS if field != "TrialId")
_ROW_FIELDS = frozenset(_FIELDS)


def _fingerprint(trial_id: str, rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Collect non-inferential observation characteristics for one trial code."""
    dates = sorted({row["Date"] for row in rows})
    signatures = {tuple(row[field] for field in _SIGNATURE_FIELDS) for row in rows}
    return {
        "trial_id": trial_id,
        "rows": len(rows),
        "observation_dates": dates,
        "distinct_assessment_signatures": len(signatures),
        "treatment_labels": sorted({row["Treatment"] for row in rows}),
        "organisms": sorted({row["Organism"] for row in rows}),
        "parameters": sorted({row["Parameter"] for row in rows}),
    }


def _pairwise_comparison(
    left_id: str,
    left: Sequence[Mapping[str, str]],
    right_id: str,
    right: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Count overlaps, with treatment and TrialId excluded from endpoint keys."""
    left_signatures = {tuple(row[field] for field in _SIGNATURE_FIELDS) for row in left}
    right_signatures = {tuple(row[field] for field in _SIGNATURE_FIELDS) for row in right}
    left_arms = {tuple(row[field] for field in _ARM_FIELDS) for row in left}
    right_arms = {tuple(row[field] for field in _ARM_FIELDS) for row in right}
    left_records = Counter(tuple(row[field] for field in _RAW_RECORD_FIELDS) for row in left)
    right_records = Counter(tuple(row[field] for field in _RAW_RECORD_FIELDS) for row in right)
    return {
        "trial_ids": [left_id, right_id],
        "shared_dates": sorted({row["Date"] for row in left} & {row["Date"] for row in right}),
        "shared_assessment_signatures": len(left_signatures & right_signatures),
        "shared_arm_assessment_signatures": len(left_arms & right_arms),
        "identical_records_except_trial_id": sum((left_records & right_records).values()),
        "shared_treatment_labels": sorted(
            {row["Treatment"] for row in left} & {row["Treatment"] for row in right}
        ),
        "shared_organisms": sorted(
            {row["Organism"] for row in left} & {row["Organism"] for row in right}
        ),
        "shared_parameters": sorted(
            {row["Parameter"] for row in left} & {row["Parameter"] for row in right}
        ),
    }


def summarize_wheat_collisions(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Characterize every shared geocode-year while preserving every trial ID."""
    hierarchy = audit_wheat_site_rows(rows)
    trials: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for index, row in enumerate(rows, start=2):
        if not row.keys() >= _ROW_FIELDS or any(
            not isinstance(row[field], str) for field in _ROW_FIELDS
        ):
            raise ValueError(f"missing endpoint metadata on source line {index}")
        trials[row["TrialId"]].append(row)

    comparisons: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for cluster in hierarchy["shared_geocode_years"]:
        ids = cluster["trial_ids"]
        pairs = [
            _pairwise_comparison(left, trials[left], right, trials[right])
            for left, right in combinations(ids, 2)
        ]
        comparisons.extend(pairs)
        groups.append(
            {
                **cluster,
                "trials": [_fingerprint(trial, trials[trial]) for trial in ids],
                "pairwise_comparisons": pairs,
            }
        )

    return {
        "schema_version": 1,
        "source_rows": len(rows),
        "trial_id_count": hierarchy["trial_id_count"],
        "geocode_count": hierarchy["geocode_count"],
        "geocode_year_count": hierarchy["geocode_year_count"],
        "shared_geocode_year_count": len(groups),
        "trial_ids_in_shared_geocode_years": len(
            {trial for group in groups for trial in group["trial_ids"]}
        ),
        "pairwise_comparison_count": len(comparisons),
        "pairs_with_common_date": sum(bool(pair["shared_dates"]) for pair in comparisons),
        "pairs_with_common_assessment_signature": sum(
            pair["shared_assessment_signatures"] > 0 for pair in comparisons
        ),
        "pairs_with_identical_records_except_trial_id": sum(
            pair["identical_records_except_trial_id"] > 0 for pair in comparisons
        ),
        "pairwise_identical_record_matches": sum(
            pair["identical_records_except_trial_id"] for pair in comparisons
        ),
        "pairs_with_common_nonuntreated_treatment_label": sum(
            any(label != "Untreated" for label in pair["shared_treatment_labels"])
            for pair in comparisons
        ),
        "assessment_signature_fields_without_trial_id": list(_SIGNATURE_FIELDS),
        "exact_record_comparison_fields_without_trial_id": list(_RAW_RECORD_FIELDS),
        "shared_geocode_years": groups,
    }


def audit_wheat_collision_data(data_dir: Path) -> dict[str, Any]:
    """Verify both the source and prior site audit before generating the report."""
    hierarchy = audit_wheat_site_data(data_dir)
    saved_hierarchy = data_dir.parent / "results/external_wheat_site_hierarchy.json"
    if not saved_hierarchy.exists() or json.loads(saved_hierarchy.read_text()) != hierarchy:
        raise ValueError("wheat site hierarchy report missing or stale")
    path = data_dir / "external" / _SOURCE_PATH
    report = summarize_wheat_collisions(_read_wheat_rows(path))
    for field in ("source_rows", "trial_id_count", "geocode_count", "geocode_year_count"):
        if report[field] != hierarchy[field]:
            raise ValueError(f"source audit disagreement: {field}")
    return {
        "source_doi": _SOURCE_DOI,
        "source_path": _SOURCE_PATH,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        **report,
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Generate or verify the fixed, descriptive collision fingerprint report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/external_wheat_collision_fingerprints.json")
    )
    parser.add_argument("--check", action="store_true", help="Check report without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        content = json.dumps(audit_wheat_collision_data(args.data_dir), indent=2) + "\n"
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"wheat collision fingerprint audit failed: {exc}\n")
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != content:
            parser.exit(1, f"wheat collision report missing or stale: {args.output}\n")
        print(f"wheat collision report matches source: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"wrote wheat collision report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
