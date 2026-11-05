"""Export literal aggregate flowering observations from the Dryad field study.

The source records visit-level plant and flower counts, not additional plants.
Arithmetic cross-checks are descriptive provenance tests: they do not turn
recorded proportions into independent disease risks or weather effects.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from crop_protection_ps.analysis_eligibility import (
    analysis_decision,
    validate_analysis_contract,
)
from crop_protection_ps.aphid_dryad_units import _read_workbook
from crop_protection_ps.dryad_field_panel import _flower_dates, audit_dryad_field_panel

_SOURCE = "dryad_pathogen_temperature_4mw6m90jv"
_WORKBOOK = "flower_summary_data.xlsx"
_ASSET = "dryad_flowering_summary"
_ACTION = "aggregate_flowering_description"
_SOURCE_FIELDS = (
    "days",
    "Date",
    "high",
    "low",
    "Data.collection.pt",
    "high.7",
    "low.7",
    "liquid.in",
    "Degree.days",
    "Evap.in",
    "high.14",
    "low.14",
    "high.10",
    "low.10",
    "high.12",
    "low.12",
    "high.16",
    "low.16",
    "Flwer.data",
    "total.D.flwr",
    "total.H.flwr",
    "total",
    "proportion",
    "Flwr.plants",
    "Fully.Smutty.plants",
    "Partial.dis",
    "any.disease",
    "Prop.any.dis",
    "prop.flwr",
)
_RAW_CSV_FIELDS = ("visit_order", "calendar_date", *_SOURCE_FIELDS)
_CHECK_FIELDS = (
    "visit_order",
    "calendar_date",
    "recorded_flower_data_flag",
    "flower_count_availability",
    "source_flower_total_sum",
    "source_flower_fraction",
    "source_any_disease_count_sum",
    "source_any_disease_fraction",
    "source_flowering_fraction_vs_plant_rows",
)
_SOURCE_PLANT_COUNTS = ("Flwr.plants", "Fully.Smutty.plants", "Partial.dis", "any.disease")
_SOURCE_FLOWER_COUNTS = ("total.D.flwr", "total.H.flwr", "total")
_SOURCE_RATIOS = ("proportion", "Prop.any.dis", "prop.flwr")
_TOLERANCE_TWO_DECIMALS = Decimal("0.00501")
_TOLERANCE_THREE_DECIMALS = Decimal("0.00051")


def _nonnegative_count(raw: str, field: str, *, optional: bool = False) -> int | None:
    """Validate a literal integral source count without filling absent cells."""
    if not isinstance(raw, str):
        raise ValueError(f"non-string source field: {field}")
    if raw == "" and optional:
        return None
    if not raw.isascii() or not raw.isdigit():
        raise ValueError(f"invalid nonnegative source count: {field}={raw!r}")
    return int(raw)


def _source_ratio(raw: str, field: str) -> Decimal | None:
    """Validate a recorded fraction without altering its Excel literal."""
    if not isinstance(raw, str):
        raise ValueError(f"non-string source field: {field}")
    if raw == "":
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"invalid source fraction: {field}={raw!r}") from exc
    if not value.is_finite() or not Decimal(0) <= value <= Decimal(1):
        raise ValueError(f"invalid source fraction: {field}={raw!r}")
    return value


def _sum_check(a: int | None, b: int | None, recorded: int | None) -> str:
    """Compare a source total with components, preserving unavailable cases."""
    if a is None or b is None or recorded is None:
        return "not_recorded"
    return "agrees" if a + b == recorded else "disagrees"


def _ratio_check(
    numerator: int | None,
    denominator: int | None,
    recorded: Decimal | None,
    tolerance: Decimal,
) -> str:
    """Check source rounding with a declared absolute tolerance, not a model."""
    if numerator is None or denominator is None or denominator == 0 or recorded is None:
        return "not_recorded"
    difference = abs(Decimal(numerator) / Decimal(denominator) - recorded)
    return "agrees" if difference <= tolerance else "disagrees"


def describe_flowering_visits(
    rows: Sequence[Mapping[str, str]], source_plant_rows: int
) -> dict[str, Any]:
    """Preserve source strings and check within-row arithmetic only.

    ``source_plant_rows`` is an independently audited source-table count.
    Matching `prop.flwr` to that denominator is an arithmetic observation,
    not evidence that all plants form an independent or stable risk set.
    """
    if type(source_plant_rows) is not int or source_plant_rows <= 0:
        raise ValueError("invalid independently audited source plant count")
    if not rows:
        raise ValueError("empty Dryad flowering summary")
    dates = _flower_dates(rows)
    raw_visits: list[dict[str, str | int]] = []
    checks: list[dict[str, str | int]] = []
    availability: Counter[str] = Counter()
    flags: Counter[str] = Counter()
    for order, (row, observed) in enumerate(zip(rows, dates, strict=True), start=1):
        if set(row) != set(_SOURCE_FIELDS):
            raise ValueError("unexpected Dryad flower-summary source columns")
        if any(not isinstance(row[field], str) for field in _SOURCE_FIELDS):
            raise ValueError("non-string Dryad flower-summary source value")
        flag = row["Flwer.data"]
        if flag not in {"0", "1"}:
            raise ValueError(f"unexpected Dryad Flwer.data source flag: {flag!r}")
        flags[flag] += 1
        plant_counts = {
            field: _nonnegative_count(row[field], field) for field in _SOURCE_PLANT_COUNTS
        }
        if any(value is None or value > source_plant_rows for value in plant_counts.values()):
            raise ValueError("recorded flowering plant count exceeds source plant rows")
        flower_counts = {
            field: _nonnegative_count(row[field], field, optional=True)
            for field in _SOURCE_FLOWER_COUNTS
        }
        ratios = {field: _source_ratio(row[field], field) for field in _SOURCE_RATIOS}
        if flag == "0":
            # A zero collection flag accompanied by nonzero detailed counts
            # or a recorded proportion is a source inconsistency, not proof
            # that the unexpected measurements should be thrown away.
            has_detail_values = (
                flower_counts["total.D.flwr"] is not None
                or flower_counts["total.H.flwr"] is not None
                or flower_counts["total"] not in (None, 0)
                or ratios["proportion"] is not None
            )
            current_availability = (
                "flag_off_with_detail_values" if has_detail_values else "not_collected"
            )
        elif (
            all(value is not None for value in flower_counts.values())
            and ratios["proportion"] is not None
        ):
            current_availability = "complete"
        else:
            current_availability = "incomplete"
        availability[current_availability] += 1
        raw_visits.append({"visit_order": order, "calendar_date": observed.isoformat(), **row})
        checks.append(
            {
                "visit_order": order,
                "calendar_date": observed.isoformat(),
                "recorded_flower_data_flag": flag,
                "flower_count_availability": current_availability,
                "source_flower_total_sum": _sum_check(
                    flower_counts["total.D.flwr"],
                    flower_counts["total.H.flwr"],
                    flower_counts["total"],
                ),
                "source_flower_fraction": _ratio_check(
                    flower_counts["total.D.flwr"],
                    flower_counts["total"],
                    ratios["proportion"],
                    _TOLERANCE_TWO_DECIMALS,
                ),
                "source_any_disease_count_sum": _sum_check(
                    plant_counts["Fully.Smutty.plants"],
                    plant_counts["Partial.dis"],
                    plant_counts["any.disease"],
                ),
                "source_any_disease_fraction": _ratio_check(
                    plant_counts["any.disease"],
                    plant_counts["Flwr.plants"],
                    ratios["Prop.any.dis"],
                    _TOLERANCE_THREE_DECIMALS,
                ),
                "source_flowering_fraction_vs_plant_rows": _ratio_check(
                    plant_counts["Flwr.plants"],
                    source_plant_rows,
                    ratios["prop.flwr"],
                    _TOLERANCE_THREE_DECIMALS,
                ),
            }
        )

    fields_to_count = (*_SOURCE_FLOWER_COUNTS, *_SOURCE_PLANT_COUNTS, *_SOURCE_RATIOS)
    return {
        "source_visit_rows": len(rows),
        "source_plant_rows_used_only_for_arithmetic_check": source_plant_rows,
        "first_visit_date": dates[0].isoformat(),
        "last_visit_date": dates[-1].isoformat(),
        "original_source_columns": list(_SOURCE_FIELDS),
        "recorded_flower_data_flag_counts": dict(sorted(flags.items())),
        "flower_count_availability": dict(sorted(availability.items())),
        "nonblank_cells_by_count_or_fraction_field": {
            field: sum(row[field] != "" for row in rows) for field in fields_to_count
        },
        "arithmetic_check_counts": {
            field: dict(sorted(Counter(str(row[field]) for row in checks).items()))
            for field in _CHECK_FIELDS[4:]
        },
        "source_visits": raw_visits,
        "arithmetic_checks": checks,
    }


def audit_dryad_flowering_summary(data_dir: Path) -> dict[str, Any]:
    """Enforce allowed scope, original-source provenance, dates and unit counts."""
    root = data_dir.resolve().parent
    contract_path = data_dir / "external/analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    if analysis_decision(contract, _ASSET, _ACTION)["status"] != "allowed":
        raise ValueError("Dryad aggregate flowering description not permitted")
    asset = next(item for item in contract["assets"] if item["id"] == _ASSET)
    plants_asset = next(item for item in contract["assets"] if item["id"] == "dryad_field_plants")
    sheets = _read_workbook(data_dir / "external" / _SOURCE / _WORKBOOK)
    if set(sheets) != {asset["table"]}:
        raise ValueError("unexpected Dryad flowering-summary workbook sheet")
    report = describe_flowering_visits(sheets[asset["table"]], plants_asset["rows"])
    if report["source_visit_rows"] != asset["rows"] or asset["group_count"] != asset["rows"]:
        raise ValueError("flower-summary row count disagrees with eligibility contract")

    previous_path = root / "results/external_dryad_field_panel.json"
    previous_bytes = previous_path.read_bytes()
    previous = audit_dryad_field_panel(data_dir)
    if json.loads(previous_bytes) != previous:
        raise ValueError("predecessor Dryad field-panel audit is missing or stale")
    panel = previous["field_panel"]
    if (
        panel["plant_rows"] != plants_asset["rows"]
        or panel["field_visits"] != report["source_visit_rows"]
        or [item["date"] for item in panel["visits"]]
        != [item["calendar_date"] for item in report["source_visits"]]
    ):
        raise ValueError("flowering-summary dates disagree with source field-panel audit")
    return {
        "schema_version": 1,
        "source_doi": "10.5061/dryad.4mw6m90jv",
        "source_workbook": _WORKBOOK,
        "source_sheet": asset["table"],
        "manifest_sha256": hashlib.sha256(
            (data_dir / "external/manifest.json").read_bytes()
        ).hexdigest(),
        "analysis_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "predecessor_field_panel_sha256": hashlib.sha256(previous_bytes).hexdigest(),
        "analysis": _ACTION,
        "observational_unit": "aggregate_visit_row_not_individual_plant",
        **report,
        "limitations": [
            "Source flowering fractions are retained, not interpreted as independent risks.",
            "Twenty-seven aggregate visits are not twenty-seven new individual plants.",
            "The 178 field rows are used only to inspect recorded fraction arithmetic.",
            "Flower totals are recorded for fewer visits than flowering-plant totals.",
            "Summary weather fields are raw source strings, not validated exposures.",
            "No weather association, causal effect, or disease transition model is fitted.",
        ],
    }


def _csv(records: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    """Emit original source strings with stable newlines and header order."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Keep original visit values in CSV, not duplicated inside JSON."""
    metadata = {
        key: value
        for key, value in report.items()
        if key not in {"source_visits", "arithmetic_checks"}
    }
    return {
        "summary.json": json.dumps(metadata, indent=2) + "\n",
        "source_flowering_visits.csv": _csv(report["source_visits"], _RAW_CSV_FIELDS),
        "source_arithmetic_checks.csv": _csv(report["arithmetic_checks"], _CHECK_FIELDS),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Regenerate or check source-grounded aggregate flowering descriptions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/external_dryad_flowering_summary")
    )
    parser.add_argument("--check", action="store_true", help="Verify files without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        files = render_reports(audit_dryad_flowering_summary(args.data_dir))
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        json.JSONDecodeError,
        csv.Error,
    ) as exc:
        parser.exit(1, f"Dryad flowering-summary description failed: {exc}\n")
    if args.check:
        stale = [
            name
            for name, content in files.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"Dryad flowering summary files missing or stale: {', '.join(stale)}\n")
        print(f"verified {len(files)} Dryad flowering-summary files in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {len(files)} Dryad flowering-summary files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
