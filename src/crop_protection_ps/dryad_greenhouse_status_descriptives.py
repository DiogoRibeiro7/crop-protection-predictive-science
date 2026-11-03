"""Describe original Dryad greenhouse infection-status codes without recoding disease.

The infection workbook has one row per recorded score but no stable individual
plant identifier. Repeated, even fully identical, source rows remain counted.
The separate death-case workbook is not joined or used as a risk denominator.
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
from crop_protection_ps.aphid_dryad_units import _read_workbook

_SOURCE = "dryad_pathogen_temperature_4mw6m90jv"
_FILE = "seedling_inoculation-_infection_data.xlsx"
_ASSET = "dryad_greenhouse_infection"
_ACTION = "disease_status_frequencies"
_VISIT_FIELDS = ("year", "Date", "Temperature", "Smut Exposure", "Time", "Rep", "Family")
_STRATUM_FIELDS = ("year", "Temperature", "Smut Exposure", "Time")
_STATUS_CODES = ("D", "HF", "HM", "LD")
_SOURCE_FIELDS = {*_VISIT_FIELDS, "Disease Status", "Observer", "Comments"}
_MEASURE_FIELDS = ("source_scored_rows", *(f"status_{code}" for code in _STATUS_CODES))
_VISIT_CSV_FIELDS = (
    *_VISIT_FIELDS,
    *_MEASURE_FIELDS,
    "observer_labels",
    "nonblank_comment_rows",
)
_STRATUM_CSV_FIELDS = (*_STRATUM_FIELDS, "recorded_visit_cells", *_MEASURE_FIELDS)


def _source_label(raw: str, field: str) -> str:
    """Require a nonblank literal label; never interpret the source's `NA`."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"blank greenhouse source field: {field}")
    return raw


def _source_integer(raw: str, field: str) -> int:
    """Validate a recorded numeric code without changing its string value."""
    value = _source_label(raw, field)
    if not value.isascii() or not value.isdigit():
        raise ValueError(f"invalid greenhouse {field} code: {value!r}")
    return int(value)


def _sort_visit(key: tuple[str, ...]) -> tuple[int, int, float, str, str, int, str]:
    """Order recorded visit cells deterministically, retaining original labels."""
    return (int(key[0]), int(key[1]), float(key[2]), key[3], key[4], int(key[5]), key[6])


def _sort_stratum(key: tuple[str, ...]) -> tuple[int, float, str, str]:
    """Order descriptive strata by numerical year/temperature source codes."""
    return (int(key[0]), float(key[1]), key[2], key[3])


def summarise_infection_status(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Count literal status codes within source visit cells and broad strata.

    ``Date`` is the literal Excel serial value, and ``year`` is the source
    experimental-year code. Neither is recast as a calendar date or exposure.
    """
    if not rows:
        raise ValueError("empty Dryad greenhouse infection worksheet")

    visit_status: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    visit_observers: dict[tuple[str, ...], set[str]] = defaultdict(set)
    visit_comments: Counter[tuple[str, ...]] = Counter()
    exact_rows: Counter[tuple[tuple[str, str], ...]] = Counter()
    observers: Counter[str] = Counter()
    years: Counter[str] = Counter()
    statuses: Counter[str] = Counter()

    for row in rows:
        if set(row) != _SOURCE_FIELDS:
            raise ValueError("unexpected greenhouse infection source columns")
        for field in (*_VISIT_FIELDS, "Disease Status", "Observer"):
            _source_label(row[field], field)
        for field in ("year", "Date", "Rep"):
            _source_integer(row[field], field)
        try:
            temperature = float(row["Temperature"])
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid greenhouse Temperature") from exc
        if not math.isfinite(temperature):
            raise ValueError("invalid greenhouse Temperature")
        status = row["Disease Status"]
        if status not in _STATUS_CODES:
            raise ValueError(f"unmapped greenhouse Disease Status: {status!r}")
        if not isinstance(row["Comments"], str):
            raise ValueError("non-string greenhouse Comments")

        key = tuple(row[field] for field in _VISIT_FIELDS)
        visit_status[key][status] += 1
        visit_observers[key].add(row["Observer"])
        visit_comments[key] += bool(row["Comments"].strip())
        exact_rows[tuple(sorted(row.items()))] += 1
        observers[row["Observer"]] += 1
        years[row["year"]] += 1
        statuses[status] += 1

    visits: list[dict[str, Any]] = []
    stratum_status: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    stratum_visits: Counter[tuple[str, ...]] = Counter()
    for key in sorted(visit_status, key=_sort_visit):
        counts = visit_status[key]
        visit = {
            **dict(zip(_VISIT_FIELDS, key, strict=True)),
            "source_scored_rows": sum(counts.values()),
            **{f"status_{code}": counts[code] for code in _STATUS_CODES},
            "observer_labels": sorted(visit_observers[key]),
            "nonblank_comment_rows": visit_comments[key],
        }
        visits.append(visit)
        stratum = tuple(key[_VISIT_FIELDS.index(field)] for field in _STRATUM_FIELDS)
        stratum_status[stratum].update(counts)
        stratum_visits[stratum] += 1

    strata = [
        {
            **dict(zip(_STRATUM_FIELDS, key, strict=True)),
            "recorded_visit_cells": stratum_visits[key],
            "source_scored_rows": sum(stratum_status[key].values()),
            **{f"status_{code}": stratum_status[key][code] for code in _STATUS_CODES},
        }
        for key in sorted(stratum_status, key=_sort_stratum)
    ]
    return {
        "source_scored_rows": len(rows),
        "recorded_visit_cells": len(visits),
        "source_exact_repeated_row_excess": sum(n - 1 for n in exact_rows.values()),
        "source_year_code_counts": dict(sorted(years.items())),
        "source_observer_code_counts": dict(sorted(observers.items())),
        "source_status_code_counts": {code: statuses[code] for code in _STATUS_CODES},
        "source_nonblank_comment_rows": sum(visit_comments.values()),
        "source_records_per_visit_cell": {
            str(n): count
            for n, count in sorted(Counter(v["source_scored_rows"] for v in visits).items())
        },
        "visit_fields": list(_VISIT_FIELDS),
        "stratum_fields": list(_STRATUM_FIELDS),
        "visit_cells": visits,
        "strata": strata,
    }


def audit_dryad_greenhouse_status(data_dir: Path) -> dict[str, Any]:
    """Verify original source bytes, analysis policy, and unit-audit counts."""
    contract_path = data_dir / "external" / "analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    if analysis_decision(contract, _ASSET, _ACTION)["status"] != "allowed":
        raise ValueError("greenhouse disease-status description not permitted")

    asset = next(item for item in contract["assets"] if item["id"] == _ASSET)
    root = data_dir / "external"
    tables = _read_workbook(root / _SOURCE / _FILE)
    if set(tables) != {asset["table"]}:
        raise ValueError("unexpected Dryad greenhouse infection worksheet")
    report = summarise_infection_status(tables[asset["table"]])

    # The contract validator already compared this report to its regenerated
    # source-level unit audit, so the checked-in counts are safe to reconcile.
    unit_path = data_dir.parent / "results/external_aphid_dryad_units.json"
    audited = json.loads(unit_path.read_text(encoding="utf-8"))["dryad"]["greenhouse"]
    comparisons = {
        "source_scored_rows": (asset["rows"], audited["infection_rows"]),
        "recorded_visit_cells": (asset["group_count"], audited["infection_design_cells"]),
        "source_exact_repeated_row_excess": (audited["infection_exact_repeated_rows"],),
        "source_year_code_counts": (audited["infection_year_codes"],),
        "source_status_code_counts": (audited["disease_status_codes"],),
        "source_records_per_visit_cell": (audited["infection_rows_per_design_cell"],),
    }
    for field, expected in comparisons.items():
        if any(report[field] != value for value in expected):
            raise ValueError(f"greenhouse status description disagrees with unit audit: {field}")

    return {
        "schema_version": 1,
        "source_doi": "10.5061/dryad.4mw6m90jv",
        "source_workbook": _FILE,
        "source_sheet": asset["table"],
        "manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "analysis_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "analysis": _ACTION,
        "observational_unit": "recorded_plant_score_row_not_verified_unique_plant",
        **report,
        "limitations": [
            "D, LD, HF and HM are literal source codes; no binary disease endpoint is constructed.",
            "Year and Excel Date serial values are labels, not validated calendar dates.",
            "Identical records remain counted; equal scores need not be duplicate plants.",
            "Visit cells, family and Rep labels do not establish independent plants.",
            "The separate death-case file has no linkable plant IDs or at-risk denominator.",
            "No infection risk, mortality rate, temperature effect or causal estimate is made.",
        ],
    }


def _render_csv(records: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    """Render stable labelled counts without ratios or disease recoding."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for record in records:
        row = dict(record)
        if "observer_labels" in row:
            row["observer_labels"] = json.dumps(row["observer_labels"], separators=(",", ":"))
        writer.writerow(row)
    return output.getvalue()


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Store source-level audit metadata once; detailed records live in CSVs."""
    metadata = {key: value for key, value in report.items() if key not in {"visit_cells", "strata"}}
    return {
        "summary.json": json.dumps(metadata, indent=2) + "\n",
        "status_by_visit_cell.csv": _render_csv(report["visit_cells"], _VISIT_CSV_FIELDS),
        "status_by_stratum.csv": _render_csv(report["strata"], _STRATUM_CSV_FIELDS),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Write or verify permitted descriptive status counts entirely offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/external_dryad_greenhouse_status")
    )
    parser.add_argument("--check", action="store_true", help="Verify existing files, no writes")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        files = render_reports(audit_dryad_greenhouse_status(args.data_dir))
    except (
        ValueError,
        KeyError,
        OSError,
        StopIteration,
        ET.ParseError,
        BadZipFile,
        csv.Error,
    ) as exc:
        parser.exit(1, f"Dryad greenhouse status description failed: {exc}\n")

    if args.check:
        stale = [
            name
            for name, contents in files.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != contents
        ]
        if stale:
            parser.exit(1, f"Dryad greenhouse status reports missing/stale: {', '.join(stale)}\n")
        print(f"verified {len(files)} Dryad greenhouse status files in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, contents in files.items():
            (args.output_dir / name).write_text(contents, encoding="utf-8")
        print(f"wrote {len(files)} Dryad greenhouse status files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
