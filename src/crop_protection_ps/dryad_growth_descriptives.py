"""Export source-verified descriptive colony counts for three Dryad strains.

The workbook's literal ``Colonly.Count`` values are nonnegative integer
colony observations, not a binomial denominator or independent temperature
assignments. Repeated Picture ID labels are retained, never deduplicated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

from crop_protection_ps.analysis_eligibility import (
    analysis_decision,
    validate_analysis_contract,
)
from crop_protection_ps.aphid_dryad_units import _dryad_lab, _read_workbook

_SOURCE = "dryad_pathogen_temperature_4mw6m90jv"
_ACTION = "colony_count_description"
_SOURCE_STRAINS = {
    "strain_2": ("Growth_data_strain_2.xlsx", "dryad_growth_2", "2"),
    "strain_3": ("Growth_data_strain_3.xlsx", "dryad_growth_3", "3"),
    "strain_4": ("Growth_data_strain_4.xlsx", "dryad_growth_4", "4"),
}
_RUN_FIELDS = ("Temperature", "Temp.Rep", "Run.Num")
_GROUP_FIELDS = ("Strain", *_RUN_FIELDS, "Mating.Type")
_REQUIRED_COLUMNS = {
    *_GROUP_FIELDS,
    "Replicate",
    "Picture ID",
    "Colonly.Count",
}
_CSV_FIELDS = (
    *_GROUP_FIELDS,
    "source_assay_rows",
    "source_replicate_labels",
    "source_picture_ids",
    "total_recorded_colonies",
    "mean_colonies_per_source_row",
    "min_source_colony_count",
    "max_source_colony_count",
)


def _nonnegative_count(raw: str, field: str) -> int:
    """Require a literal unsigned integer source count without coercion."""
    if not isinstance(raw, str) or not raw.strip().isascii() or not raw.strip().isdigit():
        raise ValueError(f"invalid {field} source count: {raw!r}")
    return int(raw.strip())


def summarise_growth_strain(
    rows: Sequence[Mapping[str, str]], *, expected_strain: str, filename: str
) -> dict[str, Any]:
    """Summarize colony rows by original strain, run and mating-type labels."""
    if not expected_strain.isascii() or not expected_strain.isdigit():
        raise ValueError(f"invalid requested strain label: {expected_strain!r}")
    groups: dict[tuple[str, ...], list[tuple[str, str, int]]] = defaultdict(list)
    run_groups: Counter[tuple[str, ...]] = Counter()
    picture_labels: Counter[str] = Counter()
    for row in rows:
        if set(row) != _REQUIRED_COLUMNS:
            raise ValueError(f"unexpected Dryad growth columns: {filename}")
        if any(not isinstance(row[field], str) or not row[field].strip() for field in row):
            raise ValueError(f"blank Dryad growth source field: {filename}")
        if row["Strain"] != expected_strain:
            raise ValueError(f"mixed or unexpected Dryad growth strain: {filename}")
        for field in ("Temperature", "Temp.Rep", "Run.Num"):
            try:
                value = float(row[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid Dryad growth {field}: {filename}") from exc
            if not math.isfinite(value) or (field != "Temperature" and not value.is_integer()):
                raise ValueError(f"invalid Dryad growth {field}: {filename}")
        if not row["Replicate"].isascii() or not row["Replicate"].isdigit():
            raise ValueError(f"invalid Dryad growth Replicate: {filename}")
        count = _nonnegative_count(row["Colonly.Count"], "Colonly.Count")
        group_key = tuple(row[field] for field in _GROUP_FIELDS)
        run_groups[tuple(row[field] for field in _RUN_FIELDS)] += 1
        picture_labels[row["Picture ID"]] += 1
        groups[group_key].append((row["Replicate"], row["Picture ID"], count))

    unit_report = _dryad_lab(rows, "growth", filename)
    records: list[dict[str, Any]] = []
    for key, observations in sorted(
        groups.items(),
        key=lambda entry: (
            int(entry[0][0]),
            *(float(value) for value in entry[0][1:4]),
            entry[0][4],
        ),
    ):
        replicates = [record[0] for record in observations]
        if len(set(replicates)) != len(replicates):
            raise ValueError(f"duplicate nested growth replicate: {filename} {key}")
        counts = [record[2] for record in observations]
        records.append(
            {
                **dict(zip(_GROUP_FIELDS, key, strict=True)),
                "source_assay_rows": len(observations),
                "source_replicate_labels": sorted(replicates, key=int),
                "source_picture_ids": [
                    record[1] for record in sorted(observations, key=lambda x: int(x[0]))
                ],
                "total_recorded_colonies": sum(counts),
                "mean_colonies_per_source_row": round(sum(counts) / len(counts), 10),
                "min_source_colony_count": min(counts),
                "max_source_colony_count": max(counts),
            }
        )

    if len(run_groups) != unit_report["temperature_run_groups"]:
        raise ValueError(f"temperature/run count conflicts with source unit audit: {filename}")
    if unit_report["duplicate_nested_record_keys"]:
        raise ValueError(f"duplicated nested growth source keys: {filename}")
    if len(picture_labels) != unit_report["distinct_picture_ids"]:
        raise ValueError(f"picture ID count conflicts with source unit audit: {filename}")
    if sum(n - 1 for n in picture_labels.values()) != unit_report["repeated_picture_id_rows"]:
        raise ValueError(f"picture ID collision count conflicts with source audit: {filename}")
    return {
        "source_file": filename,
        "source_strain_label": expected_strain,
        "source_colony_field": "Colonly.Count",
        "group_fields": list(_GROUP_FIELDS),
        "source_record_count": len(rows),
        "temperature_labels": sorted({row["Temperature"] for row in rows}, key=float),
        "temperature_run_groups": len(run_groups),
        "records_per_temperature_run": {
            str(size): count for size, count in sorted(Counter(run_groups.values()).items())
        },
        "strain_run_mating_cells": len(records),
        "records_per_strain_run_mating_cell": {
            str(size): count for size, count in sorted(Counter(map(len, groups.values())).items())
        },
        "source_total_recorded_colonies": sum(
            record["total_recorded_colonies"] for record in records
        ),
        "source_distinct_picture_id_labels": len(picture_labels),
        "source_repeated_picture_id_rows": sum(n - 1 for n in picture_labels.values()),
        "groups": records,
    }


def audit_dryad_growth(data_dir: Path) -> dict[str, Any]:
    """Enforce source integrity, per-table permissions, and unit reconciliation."""
    contract_path = data_dir / "external" / "analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    asset_by_id = {item["id"]: item for item in contract["assets"]}
    root = data_dir / "external"
    strains: dict[str, dict[str, Any]] = {}
    for name, (filename, asset_id, strain_label) in _SOURCE_STRAINS.items():
        if analysis_decision(contract, asset_id, _ACTION)["status"] != "allowed":
            raise ValueError(f"colony count description not permitted: {asset_id}")
        tables = _read_workbook(root / _SOURCE / filename)
        if len(tables) != 1:
            raise ValueError(f"unexpected Dryad growth worksheets: {filename}")
        sheet, rows = next(iter(tables.items()))
        asset = asset_by_id[asset_id]
        if sheet != asset["table"]:
            raise ValueError(f"source growth sheet disagrees with eligibility: {filename}")
        report = summarise_growth_strain(rows, expected_strain=strain_label, filename=filename)
        if (
            report["source_record_count"] != asset["rows"]
            or report["temperature_run_groups"] != asset["group_count"]
        ):
            raise ValueError(f"growth totals disagree with eligibility: {filename}")
        strains[name] = report
    return {
        "schema_version": 1,
        "source_doi": "10.5061/dryad.4mw6m90jv",
        "manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "analysis_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "analysis": _ACTION,
        "source_count_unit": "recorded_colonies_per_assay_row",
        "group_fields": list(_GROUP_FIELDS),
        "strains": strains,
        "limitations": [
            "Counts describe original assay rows, not independent randomized temperature units.",
            "Picture ID labels may recur across temperature replicates; no rows are removed.",
            "Mating types and strains are kept separate; their counts are not pooled into effects.",
            "Run.Num and Temp.Rep are source codes, not verified independent growth chambers.",
            "Strain 3 splits some recorded temperature/run groups by mating-type run codes.",
            "No growth rate, temperature model, significance test or causal effect is estimated.",
        ],
    }


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Render reproducible per-strain CSV files and the full audited JSON."""
    files = {"summary.json": json.dumps(report, indent=2) + "\n"}
    for name, strain in report["strains"].items():
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for group in strain["groups"]:
            writer.writerow(
                {
                    **group,
                    "source_replicate_labels": "|".join(group["source_replicate_labels"]),
                    "source_picture_ids": "|".join(group["source_picture_ids"]),
                }
            )
        files[f"{name}_mating_type_runs.csv"] = output.getvalue()
    return files


def main(argv: Iterable[str] | None = None) -> int:
    """Write or verify the three permitted growth exports without network calls."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/external_dryad_growth"))
    parser.add_argument("--check", action="store_true", help="Check without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        expected = render_reports(audit_dryad_growth(args.data_dir))
    except (
        ValueError,
        KeyError,
        OSError,
        StopIteration,
        ET.ParseError,
        BadZipFile,
        csv.Error,
    ) as exc:
        parser.exit(1, f"Dryad growth description failed: {exc}\n")
    if args.check:
        stale = [
            name
            for name, content in expected.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"Dryad growth reports missing or stale: {', '.join(stale)}\n")
        print(f"verified {len(expected)} Dryad growth files in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in expected.items():
            (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {len(expected)} Dryad growth files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
