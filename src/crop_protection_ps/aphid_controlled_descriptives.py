"""Export permission-gated descriptive condition tables for aphid assays.

The four controlled-experiment worksheets count aphids within recorded cohort
rows. Aggregates here describe those counts only: they are not treatment
effects, replicated-binomial likelihoods, or independent experimental units.
Experiment 5 has a different field design and is never included.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
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
from crop_protection_ps.aphid_dryad_units import _APHID_FACTORS, _read_workbook

_SOURCE = "zenodo_aphid_pesticide_19805135"
_ACTION = "condition_mortality_description"
_RESULT_COLUMNS = (
    "source_records",
    "counted_aphids",
    "recorded_deaths",
    "pooled_recorded_mortality",
    "min_source_cohort_fraction",
    "max_source_cohort_fraction",
)


def _count(raw: str, field: str) -> int:
    """Require an exact nonnegative integer, with no missing-value coercion."""
    if not isinstance(raw, str) or not raw.strip().isascii() or not raw.strip().isdigit():
        raise ValueError(f"invalid {field} source count: {raw!r}")
    return int(raw.strip())


def _rate(numerator: int, denominator: int) -> float:
    """Round a descriptive observed fraction for deterministic publication."""
    return round(numerator / denominator, 10)


def summarise_experiment(
    rows: Sequence[Mapping[str, str]],
    factors: Sequence[str],
    name: str,
) -> dict[str, Any]:
    """Count source cohorts inside literal condition labels, without pooling studies."""
    if not rows:
        raise ValueError(f"empty controlled aphid experiment: {name}")
    if not factors or len(set(factors)) != len(factors):
        raise ValueError(f"invalid factor fields for {name}")
    required = {*factors, "TOTAL", "DEAD"}
    groups: dict[tuple[str, ...], list[tuple[int, int]]] = defaultdict(list)
    exact_records: Counter[tuple[tuple[str, str], ...]] = Counter()
    factor_levels: dict[str, set[str]] = {field: set() for field in factors}
    for row in rows:
        if set(row) != required:
            raise ValueError(f"unexpected source columns in {name}")
        if any(not isinstance(row[field], str) or not row[field].strip() for field in factors):
            raise ValueError(f"blank factor value in {name}")
        total = _count(row["TOTAL"], "TOTAL")
        dead = _count(row["DEAD"], "DEAD")
        if total == 0 or dead > total:
            raise ValueError(f"invalid DEAD/TOTAL record in {name}")
        key = tuple(row[field] for field in factors)
        groups[key].append((total, dead))
        exact_records[tuple(sorted(row.items()))] += 1
        for field in factors:
            factor_levels[field].add(row[field])

    conditions: list[dict[str, Any]] = []
    for key, cohorts in sorted(groups.items()):
        total = sum(value[0] for value in cohorts)
        dead = sum(value[1] for value in cohorts)
        cohort_rates = [deaths / denominator for denominator, deaths in cohorts]
        conditions.append(
            {
                "factors": dict(zip(factors, key, strict=True)),
                "source_records": len(cohorts),
                "counted_aphids": total,
                "recorded_deaths": dead,
                "pooled_recorded_mortality": _rate(dead, total),
                "min_source_cohort_fraction": round(min(cohort_rates), 10),
                "max_source_cohort_fraction": round(max(cohort_rates), 10),
            }
        )

    return {
        "source_sheet": name,
        "factor_fields": list(factors),
        "factor_levels_as_recorded": {
            factor: sorted(levels) for factor, levels in factor_levels.items()
        },
        "source_records": len(rows),
        "condition_cells": len(conditions),
        "source_records_per_condition": {
            str(size): count for size, count in sorted(Counter(map(len, groups.values())).items())
        },
        "exact_source_row_match_excess": sum(n - 1 for n in exact_records.values()),
        "counted_aphids": sum(record["counted_aphids"] for record in conditions),
        "recorded_deaths": sum(record["recorded_deaths"] for record in conditions),
        "conditions": conditions,
    }


def audit_aphid_conditions(data_dir: Path) -> dict[str, Any]:
    """Verify source/eligibility evidence and return four separate descriptions."""
    contract_path = data_dir / "external" / "analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    for name in _APHID_FACTORS:
        identifier = f"aphid_experiment_{name.removeprefix('Experiment')}"
        decision = analysis_decision(contract, identifier, _ACTION)
        if decision["status"] != "allowed":
            raise ValueError(f"condition description is not permitted: {identifier}")

    root = data_dir / "external"
    tables = _read_workbook(root / _SOURCE / "Experiment.xlsx")
    if set(tables) != {*_APHID_FACTORS, "Experiment5"}:
        raise ValueError("unexpected controlled-aphid workbook sheets")
    experiments = {
        name: summarise_experiment(tables[name], factors, name)
        for name, factors in _APHID_FACTORS.items()
    }
    for name, report in experiments.items():
        asset = next(
            item
            for item in contract["assets"]
            if item["id"] == f"aphid_experiment_{name.removeprefix('Experiment')}"
        )
        if (
            report["source_records"] != asset["rows"]
            or report["condition_cells"] != asset["group_count"]
        ):
            raise ValueError(f"condition aggregation does not match audited unit counts: {name}")
    return {
        "schema_version": 1,
        "source_doi": "10.5281/zenodo.19805135",
        "manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "analysis_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "analysis": _ACTION,
        "excluded_source_sheet": "Experiment5",
        "observational_unit": "recorded_cohort_row",
        "rate_denominator": "sum_of_recorded_TOTAL_within_condition",
        "experiments": experiments,
        "limitations": [
            "Experiments are separate study designs; no across-experiment effect is estimated.",
            "Condition fractions are descriptive ratios of counted aphids, not effect sizes.",
            "Individual aphids and repeated cohort rows are not verified randomized units.",
            "Source time and concentration labels are retained without unit conversion.",
            "Matching source rows are preserved; equal values do not prove duplicate units.",
            "Protocol-gated interaction and causal models remain ineligible.",
        ],
    }


def _csv_report(experiment: Mapping[str, Any]) -> str:
    """Render one experiment with only factors that its source actually records."""
    output = io.StringIO(newline="")
    fields = [*experiment["factor_fields"], *_RESULT_COLUMNS]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for condition in experiment["conditions"]:
        writer.writerow(
            {
                **condition["factors"],
                **{
                    name: (
                        f"{condition[name]:.10f}"
                        if "fraction" in name or name == "pooled_recorded_mortality"
                        else condition[name]
                    )
                    for name in _RESULT_COLUMNS
                },
            }
        )
    return output.getvalue()


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Produce stable filename-to-text mappings for write and freshness checks."""
    files = {"summary.json": json.dumps(report, indent=2) + "\n"}
    for name, experiment in report["experiments"].items():
        files[f"{name.lower()}_conditions.csv"] = _csv_report(experiment)
    return files


def main(argv: Iterable[str] | None = None) -> int:
    """Export or verify the four approved condition-level tables, offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/external_aphid_controlled")
    )
    parser.add_argument("--check", action="store_true", help="Check all outputs without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        expected = render_reports(audit_aphid_conditions(args.data_dir))
    except (
        ValueError,
        OSError,
        KeyError,
        StopIteration,
        ET.ParseError,
        BadZipFile,
        csv.Error,
    ) as exc:
        parser.exit(1, f"controlled aphid description failed: {exc}\n")
    if args.check:
        stale = [
            name
            for name, content in expected.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"missing or stale controlled-aphid reports: {', '.join(stale)}\n")
        print(f"verified {len(expected)} controlled-aphid reports in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in expected.items():
            (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {len(expected)} controlled-aphid reports to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
