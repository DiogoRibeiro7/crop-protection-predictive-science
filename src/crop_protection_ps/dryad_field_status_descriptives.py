"""Export literal within-plant status records from the Dryad field workbook.

Each source row represents one plant observed on multiple calendar dates.
These exports are inventories, not disease transitions, infection risks,
temperature responses, or independent plant-by-visit experimental units.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

from crop_protection_ps.analysis_eligibility import (
    analysis_decision,
    validate_analysis_contract,
)
from crop_protection_ps.aphid_dryad_units import _read_workbook
from crop_protection_ps.dryad_field_panel import (
    _flower_dates,
    _indexed_columns,
    audit_dryad_field_panel,
)

_SOURCE = "dryad_pathogen_temperature_4mw6m90jv"
_WORKBOOK = "Raw_field_data.xlsx"
_FLOWER_WORKBOOK = "flower_summary_data.xlsx"
_ASSET = "dryad_field_plants"
_ACTION = "within_plant_status_description"
_PLANT_FIELDS = (
    "source_plant_row",
    "Row",
    "Position",
    "visit_order",
    "date",
    "raw_status_header",
    "raw_status",
    "infection_status_header",
    "infection_status",
)
_FREQUENCY_FIELDS = (
    "visit_order",
    "date",
    "status_field",
    "source_header",
    "literal_label",
    "plant_rows_with_label",
    "plant_rows_observed",
)


def describe_field_statuses(
    plants: Sequence[Mapping[str, str]], flower: Sequence[Mapping[str, str]]
) -> dict[str, Any]:
    """Retain each source plant/visit and tally exact, unrecoded labels.

    The ``(Row, Position)`` pair is a plant identifier within this workbook.
    Source row numbers and all 27 measurement dates remain attached to each
    literal status value, including blanks and unlisted/compound codes.
    """
    if not plants:
        raise ValueError("empty Dryad field plant table")
    headers = list(plants[0])
    dates = _flower_dates(flower)
    raw, aliases = _indexed_columns(
        (header for header in headers if header.casefold().startswith("status.")),
        "Status.",
        dates,
    )
    infection, infection_aliases = _indexed_columns(
        (header for header in headers if header.casefold().startswith("infect.status.")),
        "Infect.status.",
        dates,
    )

    plant_keys: set[tuple[str, str]] = set()
    plant_visits: list[dict[str, str | int]] = []
    frequencies: Counter[tuple[int, str, str, str, str]] = Counter()
    for source_row, plant in enumerate(plants, start=1):
        if set(plant) != set(headers):
            raise ValueError("inconsistent Dryad field plant columns")
        row_label, position = plant.get("Row"), plant.get("Position")
        if not isinstance(row_label, str) or not isinstance(position, str):
            raise ValueError("invalid Dryad field plant position")
        key = (row_label.strip(), position.strip())
        if not all(key):
            raise ValueError("missing Dryad field plant position")
        if key in plant_keys:
            raise ValueError(f"duplicate Dryad field plant identity: {key}")
        plant_keys.add(key)

        for visit_order, day in enumerate(dates, start=1):
            day_str = day.isoformat()
            raw_header, infection_header = raw[day], infection[day]
            raw_label = plant[raw_header]
            infection_label = plant[infection_header]
            if not isinstance(raw_label, str) or not isinstance(infection_label, str):
                raise ValueError("non-string Dryad field status label")
            plant_visits.append(
                {
                    "source_plant_row": source_row,
                    "Row": row_label,
                    "Position": position,
                    "visit_order": visit_order,
                    "date": day_str,
                    "raw_status_header": raw_header,
                    "raw_status": raw_label,
                    "infection_status_header": infection_header,
                    "infection_status": infection_label,
                }
            )
            for field, header, label in (
                ("raw_status", raw_header, raw_label),
                ("infection_status", infection_header, infection_label),
            ):
                frequencies[(visit_order, day_str, field, header, label)] += 1

    # Each row in this table describes one literal label on a single visit;
    # the denominator is source plant rows, never independent status cells.
    by_visit = [
        {
            "visit_order": visit_order,
            "date": day_str,
            "status_field": field,
            "source_header": header,
            "literal_label": label,
            "plant_rows_with_label": count,
            "plant_rows_observed": len(plants),
        }
        for (visit_order, day_str, field, header, label), count in sorted(frequencies.items())
    ]
    raw_counts = Counter(record["raw_status"] for record in plant_visits)
    infection_counts = Counter(record["infection_status"] for record in plant_visits)
    return {
        "plant_rows": len(plants),
        "unique_plant_keys": len(plant_keys),
        "field_visits": len(dates),
        "plant_visit_rows": len(plant_visits),
        "raw_status_populated": len(plant_visits) - raw_counts[""],
        "raw_status_blank": raw_counts[""],
        "infection_status_populated": len(plant_visits) - infection_counts[""],
        "infection_status_blank": infection_counts[""],
        "raw_status_distinct_nonblank_labels": len(raw_counts) - ("" in raw_counts),
        "infection_status_distinct_nonblank_labels": len(infection_counts)
        - ("" in infection_counts),
        "source_header_aliases": sorted(
            aliases + infection_aliases, key=lambda item: item["source_header"]
        ),
        "raw_status_counts": dict(sorted(raw_counts.items())),
        "infection_status_counts": dict(sorted(infection_counts.items())),
        "plant_visits": plant_visits,
        "visit_label_counts": by_visit,
    }


def audit_dryad_field_statuses(data_dir: Path) -> dict[str, Any]:
    """Enforce pinned source evidence and permission before exporting rows."""
    contract_path = data_dir / "external" / "analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    if analysis_decision(contract, _ASSET, _ACTION)["status"] != "allowed":
        raise ValueError("within-plant status description not permitted")
    asset = next(item for item in contract["assets"] if item["id"] == _ASSET)
    source = data_dir / "external" / _SOURCE
    plants_sheets = _read_workbook(source / _WORKBOOK)
    flower_sheets = _read_workbook(source / _FLOWER_WORKBOOK)
    if set(plants_sheets) != {asset["table"]} or len(flower_sheets) != 1:
        raise ValueError("unexpected Dryad field or flower summary worksheet")
    result = describe_field_statuses(
        plants_sheets[asset["table"]], next(iter(flower_sheets.values()))
    )

    # The existing panel audit validates date/weather alignment and source
    # labels; its checked-in report is also verified against original bytes.
    panel_path = data_dir.resolve().parent / "results/external_dryad_field_panel.json"
    panel_bytes = panel_path.read_bytes()
    panel_report = audit_dryad_field_panel(data_dir)
    if json.loads(panel_bytes) != panel_report:
        raise ValueError("preceding Dryad field-panel audit is missing or stale")
    panel = panel_report["field_panel"]
    if (
        result["plant_rows"] != asset["rows"]
        or result["unique_plant_keys"] != asset["group_count"]
        or result["field_visits"] != panel["field_visits"]
        or result["raw_status_counts"] != panel["raw_status_codes"]
        or result["infection_status_counts"] != panel["infection_status_codes"]
        or result["plant_visit_rows"] != panel["raw_status_cells"]
    ):
        raise ValueError("Dryad within-plant export disagrees with audited source units")
    for index, visit in enumerate(panel["visits"], start=1):
        records = [row for row in result["plant_visits"] if row["visit_order"] == index]
        if (
            len(records) != result["plant_rows"]
            or records[0]["date"] != visit["date"]
            or records[0]["raw_status_header"] != visit["raw_header"]
            or records[0]["infection_status_header"] != visit["infection_header"]
            or sum(row["raw_status"] == "" for row in records) != visit["raw_blank"]
            or sum(row["infection_status"] == "" for row in records) != visit["infection_blank"]
        ):
            raise ValueError("Dryad within-plant visit disagrees with prior panel audit")

    return {
        "schema_version": 1,
        "source_doi": "10.5061/dryad.4mw6m90jv",
        "source_workbook": _WORKBOOK,
        "source_sheet": asset["table"],
        "manifest_sha256": hashlib.sha256(
            (data_dir / "external/manifest.json").read_bytes()
        ).hexdigest(),
        "analysis_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "predecessor_field_panel_sha256": hashlib.sha256(panel_bytes).hexdigest(),
        "analysis": _ACTION,
        "observational_unit": "source_plant_with_repeated_dated_visits",
        **result,
        "limitations": [
            "The 27 visits for each source plant are not independent plant samples.",
            "Every raw label, compound code, annotation, and blank is retained literally.",
            "The one source Status.Spet.24 typo is dated without altering its header.",
            "No codebook-based disease endpoint, transition, or absorbing X state is assumed.",
            "No imputation, weather exposure, causal effect, or longitudinal model is fitted.",
            "Ever.dis is incomplete and is not used to construct an outcome.",
        ],
    }


def _csv(records: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    """Serialise records reproducibly without changing source label values."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Keep row-level observations in CSV and audit metadata in compact JSON."""
    metadata = {
        key: value
        for key, value in report.items()
        if key not in {"plant_visits", "visit_label_counts"}
    }
    return {
        "summary.json": json.dumps(metadata, indent=2) + "\n",
        "plant_visit_status.csv": _csv(report["plant_visits"], _PLANT_FIELDS),
        "status_labels_by_visit.csv": _csv(report["visit_label_counts"], _FREQUENCY_FIELDS),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Write or verify offline status exports without editing source files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/external_dryad_field_statuses")
    )
    parser.add_argument("--check", action="store_true", help="Verify files without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        files = render_reports(audit_dryad_field_statuses(args.data_dir))
    except (
        ValueError,
        KeyError,
        OSError,
        StopIteration,
        ET.ParseError,
        BadZipFile,
        csv.Error,
        TypeError,
    ) as exc:
        parser.exit(1, f"Dryad field status export failed: {exc}\n")
    if args.check:
        stale = [
            name
            for name, content in files.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"Dryad field status files missing or stale: {', '.join(stale)}\n")
        print(f"verified {len(files)} Dryad field status files in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {len(files)} Dryad field status files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
