"""Export permitted count summaries for four Dryad germination/conjugation assays.

The source identifies assay rows nested in recorded temperature/run labels.
Grouped proportions here are descriptive ratios of source counts, not
independent treatment responses or an estimand for a temperature effect.
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
_ACTION = "assay_count_description"
_GROUP_FIELDS = ("Temperature", "Temp.Rep", "Run.Num")
_SOURCE_ASSAYS = {
    "germination": ("Germination_data.xlsx", "germination", "dryad_germination"),
    "conjugation_strain_2": (
        "Conjugation_Data_strain_2.xlsx",
        "conjugation",
        "dryad_conjugation_2",
    ),
    "conjugation_strain_3": (
        "Conjugation_Data_strain_3.xlsx",
        "conjugation",
        "dryad_conjugation_3",
    ),
    "conjugation_strain_4": (
        "Conjugation_Data_strain_4.xlsx",
        "conjugation",
        "dryad_conjugation_4",
    ),
}
_CSV_FIELDS = (
    *_GROUP_FIELDS,
    "source_assay_rows",
    "source_rep_labels",
    "source_total_count",
    "source_success_count",
    "pooled_recorded_success_fraction",
    "min_source_assay_fraction",
    "max_source_assay_fraction",
)


def _source_count(raw: str, name: str) -> int:
    """Parse literal unsigned integer counts without rounding or imputation."""
    if not isinstance(raw, str) or not raw.strip().isascii() or not raw.strip().isdigit():
        raise ValueError(f"invalid {name} count: {raw!r}")
    return int(raw.strip())


def summarise_lab_assay(
    rows: Sequence[Mapping[str, str]], *, kind: str, filename: str
) -> dict[str, Any]:
    """Summarise recorded assay rows inside temperature/replicate/run labels."""
    if kind not in {"germination", "conjugation"}:
        raise ValueError(f"unsupported assay kind: {kind}")
    success_field = "Sum.Germ" if kind == "germination" else "Sum.Mating"
    required = {*_GROUP_FIELDS, "Rep", success_field, "Sum.Total", "Sum.Prop"}
    groups: dict[tuple[str, ...], list[tuple[str, int, int, float]]] = defaultdict(list)
    for row in rows:
        if set(row) != required:
            raise ValueError(f"unexpected assay source columns: {filename}")
        if any(not isinstance(row[name], str) or not row[name].strip() for name in required):
            raise ValueError(f"blank assay source value: {filename}")
        count = _source_count(row["Sum.Total"], "Sum.Total")
        successes = _source_count(row[success_field], success_field)
        try:
            proportion = float(row["Sum.Prop"])
            temperature = float(row["Temperature"])
            temperature_replicate = float(row["Temp.Rep"])
            run_code = float(row["Run.Num"])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"invalid numeric assay field: {filename}") from exc
        if (
            count <= 0
            or successes > count
            or not math.isfinite(proportion)
            or not 0 <= proportion <= 1
            or not all(math.isfinite(x) for x in (temperature, temperature_replicate, run_code))
            or not temperature_replicate.is_integer()
            or not run_code.is_integer()
        ):
            raise ValueError(f"invalid assay counts or recorded design labels: {filename}")
        if not math.isclose(proportion, successes / count, abs_tol=1e-7):
            raise ValueError(f"assay fraction disagrees with counts: {filename}")
        if not row["Rep"].isascii() or not row["Rep"].isdigit():
            raise ValueError(f"invalid source Rep label: {filename}")
        groups[tuple(row[field] for field in _GROUP_FIELDS)].append(
            (row["Rep"], count, successes, proportion)
        )

    unit_audit = _dryad_lab(rows, kind, filename)
    records: list[dict[str, Any]] = []
    for key, source_rows in sorted(
        groups.items(), key=lambda item: tuple(float(x) for x in item[0])
    ):
        rep_labels = [record[0] for record in source_rows]
        if len(set(rep_labels)) != len(rep_labels):
            raise ValueError(f"repeated assay Rep within temperature/run: {filename} {key}")
        totals = sum(record[1] for record in source_rows)
        successes = sum(record[2] for record in source_rows)
        proportions = [record[3] for record in source_rows]
        records.append(
            {
                **dict(zip(_GROUP_FIELDS, key, strict=True)),
                "source_assay_rows": len(source_rows),
                "source_rep_labels": sorted(rep_labels, key=int),
                "source_total_count": totals,
                "source_success_count": successes,
                "pooled_recorded_success_fraction": round(successes / totals, 10),
                "min_source_assay_fraction": round(min(proportions), 10),
                "max_source_assay_fraction": round(max(proportions), 10),
            }
        )
    if unit_audit["temperature_run_groups"] != len(records):
        raise ValueError(f"group counts disagree with source unit audit: {filename}")
    if unit_audit["duplicate_nested_record_keys"]:
        raise ValueError(f"repeated source nested assay key: {filename}")
    return {
        "source_file": filename,
        "assay_type": kind,
        "source_success_field": success_field,
        "group_fields": list(_GROUP_FIELDS),
        "source_record_count": len(rows),
        "temperature_labels": sorted({row["Temperature"] for row in rows}, key=float),
        "temperature_run_groups": len(records),
        "source_rows_per_temperature_run": {
            str(size): n for size, n in sorted(Counter(len(x) for x in groups.values()).items())
        },
        "source_total_count": sum(item["source_total_count"] for item in records),
        "source_success_count": sum(item["source_success_count"] for item in records),
        "groups": records,
    }


def audit_dryad_lab_assays(data_dir: Path) -> dict[str, Any]:
    """Validate source integrity and explicit permission for each assay table."""
    contract_path = data_dir / "external" / "analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    asset_by_id = {asset["id"]: asset for asset in contract["assets"]}
    root = data_dir / "external"
    assays: dict[str, dict[str, Any]] = {}
    for name, (filename, kind, asset_id) in _SOURCE_ASSAYS.items():
        if analysis_decision(contract, asset_id, _ACTION)["status"] != "allowed":
            raise ValueError(f"assay description not permitted: {asset_id}")
        source_tables = _read_workbook(root / _SOURCE / filename)
        if len(source_tables) != 1:
            raise ValueError(f"unexpected assay worksheets: {filename}")
        sheet, rows = next(iter(source_tables.items()))
        asset = asset_by_id[asset_id]
        if sheet != asset["table"]:
            raise ValueError(f"source assay sheet name disagrees with eligibility: {filename}")
        report = summarise_lab_assay(rows, kind=kind, filename=filename)
        if (
            report["source_record_count"] != asset["rows"]
            or report["temperature_run_groups"] != asset["group_count"]
        ):
            raise ValueError(f"assay row/group counts disagree with eligibility: {filename}")
        assays[name] = report
    return {
        "schema_version": 1,
        "source_doi": "10.5061/dryad.4mw6m90jv",
        "manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "analysis_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "analysis": _ACTION,
        "assay_unit": "recorded_assay_row",
        "aggregation_group": list(_GROUP_FIELDS),
        "assays": assays,
        "limitations": [
            "Germination and each conjugation strain are separate assays; no pooling across them.",
            "Pooled fractions within recorded temperature/run groups describe counts only.",
            "Rep labels describe nested source rows, not independent exposure chambers.",
            "Temp.Rep and Run.Num labels do not establish randomized treatment units.",
            "Repeated run codes are preserved, not treated as unique global batch IDs.",
            "No temperature-response model, causal contrast, p-value, or interval is estimated.",
        ],
    }


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Render stable CSVs plus a source-audited JSON summary."""
    files = {"summary.json": json.dumps(report, indent=2) + "\n"}
    for name, assay in report["assays"].items():
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for record in assay["groups"]:
            writer.writerow(
                {
                    **record,
                    "source_rep_labels": "|".join(record["source_rep_labels"]),
                }
            )
        files[f"{name}_temperature_runs.csv"] = output.getvalue()
    return files


def main(argv: Iterable[str] | None = None) -> int:
    """Write or read-only verify the four permitted laboratory assay exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/external_dryad_lab_assays")
    )
    parser.add_argument("--check", action="store_true", help="Verify without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        expected = render_reports(audit_dryad_lab_assays(args.data_dir))
    except (
        ValueError,
        KeyError,
        OSError,
        StopIteration,
        ET.ParseError,
        BadZipFile,
        csv.Error,
    ) as exc:
        parser.exit(1, f"Dryad assay description failed: {exc}\n")
    if args.check:
        stale = [
            name
            for name, content in expected.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"Dryad assay reports missing or stale: {', '.join(stale)}\n")
        print(f"verified {len(expected)} Dryad assay files in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in expected.items():
            (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {len(expected)} Dryad assay files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
