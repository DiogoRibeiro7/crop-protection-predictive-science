"""Audit cross-fold overlap under candidate wheat observation grouping rules.

Recorded trial IDs and 0.1-degree geocodes are *proxy grouping labels*, not
verified experimental units. This module makes no model-performance claim and
does not estimate fungicide effects or infer physical plot identities.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

from crop_protection_ps.wheat_collision_fingerprints import audit_wheat_collision_data
from crop_protection_ps.wheat_pairability import _FIELDS, _read_wheat_rows
from crop_protection_ps.wheat_site_hierarchy import (
    _SOURCE_DOI,
    _SOURCE_PATH,
    _coordinate,
    audit_wheat_site_data,
    audit_wheat_site_rows,
)

GroupKey = tuple[str, ...]
_SEED = 20261106
_FOLD_COUNT = 5
_GROUPING_LEVELS = ("trial_id", "geocode_year", "geocode")
_SPLIT_SCHEMES = ("row", *_GROUPING_LEVELS)
_RECORD_FIELDS = tuple(field for field in _FIELDS if field != "TrialId")


def _recorded_keys(rows: Sequence[Mapping[str, str]]) -> dict[str, list[GroupKey]]:
    """Build source-recorded grouping keys using exact 0.1-degree geocodes."""
    result: dict[str, list[GroupKey]] = {level: [] for level in _GROUPING_LEVELS}
    for line_number, row in enumerate(rows, start=2):
        if any(field not in row or not isinstance(row[field], str) for field in _FIELDS):
            raise ValueError(f"missing observation metadata on source line {line_number}")
        country = row["Country"]
        latitude = _coordinate(row["Latitude"], "Latitude", -90, 90)
        longitude = _coordinate(row["Longitude"], "Longitude", -180, 180)
        year = str(date.fromisoformat(row["Date"]).year)
        geocode = (country, latitude, longitude)
        result["trial_id"].append((row["TrialId"],))
        result["geocode_year"].append((*geocode, year))
        result["geocode"].append(geocode)
    return result


def _fold_assignment(
    keys: Sequence[GroupKey], *, fold_count: int, seed: int, group_aware: bool
) -> list[int]:
    """Assign balanced row folds or greedily row-balanced whole-key folds.

    The same seed and ordered source always give identical assignments. The
    grouped algorithm shuffles sorted keys before size-based allocation, so
    input row order cannot alter which fold receives a given group.
    """
    if not keys or isinstance(fold_count, bool) or not isinstance(fold_count, int):
        raise ValueError("fold_count must be an integer with sufficient observations")
    if fold_count < 2 or fold_count > len(keys):
        raise ValueError("fold_count must be between 2 and the number of rows")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    assignment = [-1] * len(keys)
    if not group_aware:
        indices = list(range(len(keys)))
        rng.shuffle(indices)
        for position, row_index in enumerate(indices):
            assignment[row_index] = position % fold_count
        return assignment

    groups: dict[GroupKey, list[int]] = defaultdict(list)
    for index, key in enumerate(keys):
        groups[key].append(index)
    if len(groups) < fold_count:
        raise ValueError("fewer distinct recorded groups than requested folds")

    shuffled = sorted(groups)
    rng.shuffle(shuffled)
    tie_order = {key: index for index, key in enumerate(shuffled)}
    # Keep large groups intact, then distribute them to the least-filled fold.
    shuffled.sort(key=lambda key: (-len(groups[key]), tie_order[key]))
    fold_rows = [0] * fold_count
    fold_groups = [0] * fold_count
    for key in shuffled:
        target = min(
            range(fold_count),
            key=lambda fold: (fold_rows[fold], fold_groups[fold], fold),
        )
        for index in groups[key]:
            assignment[index] = target
        fold_rows[target] += len(groups[key])
        fold_groups[target] += 1
    return assignment


def _overlap_summary(keys: Sequence[GroupKey], assignment: Sequence[int]) -> dict[str, int]:
    """Count observed labels spanning held-out folds without inferring trials."""
    memberships: dict[GroupKey, set[int]] = defaultdict(set)
    sizes: dict[GroupKey, int] = defaultdict(int)
    for key, fold in zip(keys, assignment, strict=True):
        memberships[key].add(fold)
        sizes[key] += 1
    overlapping = {key for key, folds in memberships.items() if len(folds) > 1}
    return {
        "distinct_recorded_groups": len(memberships),
        "groups_spanning_folds": len(overlapping),
        "rows_in_groups_spanning_folds": sum(sizes[key] for key in overlapping),
        "max_folds_per_group": max(map(len, memberships.values())),
    }


def audit_wheat_split_rows(
    rows: Sequence[Mapping[str, str]], *, fold_count: int = _FOLD_COUNT, seed: int = _SEED
) -> dict[str, Any]:
    """Compare candidate split rules without fitting a model or assigning plots."""
    hierarchy = audit_wheat_site_rows(rows)
    grouping = _recorded_keys(rows)

    # Exact non-ID matches across different TrialId values are *record* matches.
    # They are not evidence that two rows came from the same experimental plot.
    fingerprints: dict[GroupKey, set[str]] = defaultdict(set)
    record_keys: list[GroupKey] = []
    for row in rows:
        signature = tuple(row[field] for field in _RECORD_FIELDS)
        fingerprints[signature].add(row["TrialId"])
        record_keys.append(signature)
    cross_id_signatures = {key for key, ids in fingerprints.items() if len(ids) > 1}

    schemes: list[dict[str, Any]] = []
    for scheme in _SPLIT_SCHEMES:
        unit_keys = (
            [(str(index),) for index in range(len(rows))] if scheme == "row" else grouping[scheme]
        )
        assignment = _fold_assignment(
            unit_keys, fold_count=fold_count, seed=seed, group_aware=scheme != "row"
        )
        record_memberships: dict[GroupKey, set[int]] = defaultdict(set)
        record_sizes: dict[GroupKey, int] = defaultdict(int)
        for signature, fold in zip(record_keys, assignment, strict=True):
            if signature in cross_id_signatures:
                record_memberships[signature].add(fold)
                record_sizes[signature] += 1
        spanning = {key for key, folds in record_memberships.items() if len(folds) > 1}

        schemes.append(
            {
                "scheme": scheme,
                "fold_row_counts": [assignment.count(i) for i in range(fold_count)],
                "fold_assignment_unit_counts": [
                    len({key for key, fold in zip(unit_keys, assignment, strict=True) if fold == i})
                    for i in range(fold_count)
                ],
                "recorded_group_overlap": {
                    level: _overlap_summary(keys, assignment) for level, keys in grouping.items()
                },
                "cross_id_exact_record_signatures_spanning_folds": len(spanning),
                "rows_in_cross_id_exact_signatures_spanning_folds": sum(
                    record_sizes[key] for key in spanning
                ),
            }
        )

    return {
        "schema_version": 1,
        "source_rows": len(rows),
        "fold_count": fold_count,
        "random_seed": seed,
        "grouping_counts": {level: len(set(keys)) for level, keys in grouping.items()},
        "cross_id_exact_record_signatures": len(cross_id_signatures),
        "scientific_scope": "descriptive_validation_partition_structure_only",
        "physical_trial_identity_verified": False,
        "trial_level_treatment_effect_permitted": False,
        "schemes": schemes,
        "site_hierarchy_source_rows": hierarchy["source_rows"],
    }


def audit_wheat_split_data(data_dir: Path) -> dict[str, Any]:
    """Check original source integrity and predecessor reports before auditing."""
    site = audit_wheat_site_data(data_dir)
    collisions = audit_wheat_collision_data(data_dir)
    root = data_dir.parent
    report_paths = {
        "site": root / "results/external_wheat_site_hierarchy.json",
        "collisions": root / "results/external_wheat_collision_fingerprints.json",
    }
    for name, predecessor in (("site", site), ("collisions", collisions)):
        try:
            saved = json.loads(report_paths[name].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"missing or unreadable {name} predecessor audit") from exc
        if saved != predecessor:
            raise ValueError(f"stale {name} predecessor audit")

    source = data_dir / "external" / _SOURCE_PATH
    result = audit_wheat_split_rows(_read_wheat_rows(source))
    if result["grouping_counts"] != {
        "trial_id": site["trial_id_count"],
        "geocode_year": site["geocode_year_count"],
        "geocode": site["geocode_count"],
    }:
        raise ValueError("recorded split groups disagree with site hierarchy")
    if result["source_rows"] != collisions["source_rows"]:
        raise ValueError("recorded split rows disagree with collision audit")

    return {
        "source_doi": _SOURCE_DOI,
        "source_path": _SOURCE_PATH,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        **result,
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Regenerate or verify deterministic descriptive split-overlap evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/external_wheat_split_contamination.json")
    )
    parser.add_argument("--check", action="store_true", help="Compare without writes")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        content = json.dumps(audit_wheat_split_data(args.data_dir), indent=2) + "\n"
    except (ValueError, OSError) as exc:
        parser.exit(1, f"wheat split-overlap audit failed: {exc}\n")
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != content:
            parser.exit(1, f"wheat split-overlap report missing or stale: {args.output}\n")
        print(f"wheat split-overlap report verified: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"wrote wheat split-overlap report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
