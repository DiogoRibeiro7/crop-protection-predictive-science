"""Audit the date axis and recorded status lexicon of the Dryad field panel.

The source has one row per plant and multiple status columns per observation
date. This module never converts the recorded labels into disease outcomes,
imputes missing values, or assumes that successive visits are independent.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

from crop_protection_ps.aphid_dryad_units import _read_workbook, audit_aphid_dryad

_DRYAD = "dryad_pathogen_temperature_4mw6m90jv"
_EXCEL_EPOCH = date(1899, 12, 30)
_MONTHS = {
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "sept": 9,
    "sep": 9,
    "spet": 9,  # The literal misspelling in the source workbook.
    "oct": 10,
    "nov": 11,
}
_RAW_CODES = frozenset({"V", "B", "D", "PD", "LD", "X", "PO", "ST"})
_INFECTION_CODES = frozenset({"D", "H", "PD", "ST"})


def _excel_date(serial: str) -> date:
    """Decode an integral 1900-system Excel serial without changing the source."""
    try:
        number = float(serial)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid Excel date serial: {serial!r}") from exc
    if not math.isfinite(number) or not number.is_integer() or number < 61:
        raise ValueError(f"invalid Excel date serial: {serial!r}")
    try:
        return _EXCEL_EPOCH + timedelta(days=int(number))
    except OverflowError as exc:
        raise ValueError(f"out-of-range Excel date serial: {serial!r}") from exc


def _field_date(header: str, prefix: str, year: int) -> tuple[date, bool]:
    """Parse observed header dates, explicitly flagging the source's typo."""
    if not header.casefold().startswith(prefix.casefold()):
        raise ValueError(f"unexpected field column: {header!r}")
    parts = header[len(prefix) :].casefold().split(".")
    if len(parts) != 2 or parts[0] not in _MONTHS or not parts[1].isdigit():
        raise ValueError(f"unrecognized field date header: {header!r}")
    try:
        observed = date(year, _MONTHS[parts[0]], int(parts[1]))
    except ValueError as exc:
        raise ValueError(f"invalid field date header: {header!r}") from exc
    return observed, parts[0] == "spet"


def _indexed_columns(
    headers: Iterable[str], prefix: str, summary_dates: Sequence[date]
) -> tuple[dict[date, str], list[dict[str, str]]]:
    """Index dated status columns and reject ambiguous or duplicated dates."""
    years = {item.year for item in summary_dates}
    if len(years) != 1:
        raise ValueError("field header dates are ambiguous across summary years")
    year = next(iter(years))
    columns: dict[date, str] = {}
    aliases: list[dict[str, str]] = []
    for header in headers:
        observed, typo = _field_date(header, prefix, year)
        if observed in columns:
            raise ValueError(f"duplicate field date columns: {observed.isoformat()}")
        columns[observed] = header
        if typo:
            aliases.append({"source_header": header, "parsed_date": observed.isoformat()})
    if set(columns) != set(summary_dates):
        missing = sorted(item.isoformat() for item in set(summary_dates) - set(columns))
        extra = sorted(item.isoformat() for item in set(columns) - set(summary_dates))
        raise ValueError(f"field/flower date mismatch: missing={missing}, extra={extra}")
    return columns, aliases


def _flower_dates(rows: Sequence[Mapping[str, str]]) -> list[date]:
    """Validate visit order and elapsed days as recorded in the summary."""
    if not rows:
        raise ValueError("empty Dryad flower summary")
    dates = [_excel_date(row.get("Date", "")) for row in rows]
    if dates != sorted(set(dates)):
        raise ValueError("Dryad flower summary has duplicated or unordered dates")
    for observed, row in zip(dates, rows, strict=True):
        try:
            days = int(row.get("days", ""))
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid Dryad elapsed-day label") from exc
        if days != (observed - dates[0]).days:
            raise ValueError("Dryad flower summary date disagrees with elapsed days")
    return dates


def _weather_dates(rows: Sequence[Mapping[str, str]]) -> dict[date, dict[str, Any]]:
    """Retain recorded weather anomalies without filling or repairing values."""
    if not rows:
        raise ValueError("empty Dryad weather history")
    readings: dict[date, dict[str, Any]] = {}
    for row in rows:
        if set(row) != {"Date", "High", "Low"}:
            raise ValueError("unexpected Dryad weather columns")
        if not isinstance(row["Date"], str):
            raise ValueError("missing Dryad weather date")
        try:
            observed = datetime.strptime(row["Date"], "%m/%d/%y").date()
        except ValueError as exc:
            raise ValueError(f"invalid Dryad weather date: {row['Date']!r}") from exc
        if observed in readings:
            raise ValueError(f"duplicate Dryad weather date: {observed}")
        if not isinstance(row["High"], str) or not isinstance(row["Low"], str):
            raise ValueError(f"malformed Dryad weather row on {observed}")
        raw_high, raw_low = row["High"].strip(), row["Low"].strip()
        missing = not raw_high or not raw_low
        reversed_pair = False
        if not missing:
            try:
                high, low = float(raw_high), float(raw_low)
            except ValueError as exc:
                raise ValueError(f"invalid Dryad weather temperature on {observed}") from exc
            if not all(map(math.isfinite, (high, low))):
                raise ValueError(f"nonfinite Dryad weather temperature on {observed}")
            reversed_pair = low > high
        readings[observed] = {
            "missing_temperature": missing,
            "low_above_high": reversed_pair,
        }
    return readings


def audit_field_panel(
    plants: Sequence[Mapping[str, str]],
    flower: Sequence[Mapping[str, str]],
    weather: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Describe plant-level repeated measurements and exact source labels.

    ``H`` in the raw-status field and mixed forms such as ``D/H`` are retained
    literally. The upstream README does not enumerate every observed code; an
    unlisted label is a codebook question, not an invalid or diseased outcome.
    """
    if not plants:
        raise ValueError("empty Dryad field plant table")
    dates = _flower_dates(flower)
    headers = list(plants[0])
    raw, aliases = _indexed_columns(
        (name for name in headers if name.casefold().startswith("status.")),
        "Status.",
        dates,
    )
    infection, infection_aliases = _indexed_columns(
        (name for name in headers if name.casefold().startswith("infect.status.")),
        "Infect.status.",
        dates,
    )
    weather_dates = _weather_dates(weather)
    positions: Counter[tuple[str, str]] = Counter()
    raw_codes: Counter[str] = Counter()
    infection_codes: Counter[str] = Counter()
    ever_disease: Counter[str] = Counter()
    visits: list[dict[str, Any]] = []
    for plant in plants:
        if set(plant) != set(headers):
            raise ValueError("inconsistent Dryad field plant columns")
        row, position = plant.get("Row", "").strip(), plant.get("Position", "").strip()
        if not row or not position:
            raise ValueError("missing Dryad field plant position")
        positions[(row, position)] += 1
        ever_disease[plant.get("Ever.dis", "").strip()] += 1

    for day in dates:
        raw_count = Counter(plant[raw[day]].strip() for plant in plants)
        infection_count = Counter(plant[infection[day]].strip() for plant in plants)
        raw_codes.update(raw_count)
        infection_codes.update(infection_count)
        weather_record = weather_dates.get(day)
        visits.append(
            {
                "date": day.isoformat(),
                "raw_header": raw[day],
                "infection_header": infection[day],
                "raw_populated": len(plants) - raw_count[""],
                "raw_blank": raw_count[""],
                "raw_recorded_x": raw_count["X"],
                "infection_populated": len(plants) - infection_count[""],
                "infection_blank": infection_count[""],
                "weather_available": weather_record is not None,
                "weather_missing_temperature": (
                    weather_record["missing_temperature"] if weather_record else None
                ),
                "weather_low_above_high": (
                    weather_record["low_above_high"] if weather_record else None
                ),
            }
        )

    def _sort_counts(counts: Counter[str]) -> dict[str, int]:
        return dict(sorted(counts.items()))

    return {
        "plant_rows": len(plants),
        "unique_row_position_pairs": len(positions),
        "repeated_row_position_pairs": sum(n - 1 for n in positions.values()),
        "field_visits": len(dates),
        "raw_status_cells": len(plants) * len(dates),
        "raw_status_codes": _sort_counts(raw_codes),
        "raw_unlisted_readme_codes": _sort_counts(
            Counter({code: n for code, n in raw_codes.items() if code and code not in _RAW_CODES})
        ),
        "infection_status_codes": _sort_counts(infection_codes),
        "infection_unlisted_readme_codes": _sort_counts(
            Counter(
                {
                    code: n
                    for code, n in infection_codes.items()
                    if code and code not in _INFECTION_CODES
                }
            )
        ),
        "ever_disease_field_codes": _sort_counts(ever_disease),
        "source_header_aliases": sorted(
            aliases + infection_aliases, key=lambda item: item["source_header"]
        ),
        "summary_dates_matched_to_raw_status": len(raw),
        "summary_dates_matched_to_infection_status": len(infection),
        "visits_with_matching_weather_date": sum(day in weather_dates for day in dates),
        "weather_missing_temperature_dates": [
            day.isoformat()
            for day, record in sorted(weather_dates.items())
            if record["missing_temperature"]
        ],
        "weather_low_above_high_dates": [
            day.isoformat()
            for day, record in sorted(weather_dates.items())
            if record["low_above_high"]
        ],
        "visits": visits,
        "limitations": [
            "Source status strings are preserved verbatim; no binary outcomes are assigned.",
            "Unlisted source labels require the study codebook, not silent correction.",
            "Recorded X statuses are not verified absorbing death events.",
            "Repeated visits on one plant are not independent experimental units.",
            "Date alignment does not establish causal weather exposure.",
        ],
    }


def audit_dryad_field_panel(data_dir: Path) -> dict[str, Any]:
    """Verify all source files and previously reported units before this audit."""
    precedent = audit_aphid_dryad(data_dir)
    root = data_dir / "external"
    previous = Path("results/external_aphid_dryad_units.json")
    if not previous.exists() or json.loads(previous.read_text(encoding="utf-8")) != precedent:
        raise ValueError("predecessor experimental-unit audit is missing or stale")
    source = root / _DRYAD
    field = _read_workbook(source / "Raw_field_data.xlsx")
    summary = _read_workbook(source / "flower_summary_data.xlsx")
    if len(field) != 1 or len(summary) != 1:
        raise ValueError("unexpected Dryad field workbook worksheets")
    with (source / "daily_high_temps.txt").open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t", strict=True)
        if set(reader.fieldnames or ()) != {"Date", "High", "Low"}:
            raise ValueError("unexpected Dryad weather schema")
        weather = list(reader)
    result = audit_field_panel(next(iter(field.values())), next(iter(summary.values())), weather)
    if result["plant_rows"] != precedent["dryad"]["field"]["plant_rows"]:
        raise ValueError("field plant-count disagreement with source-unit audit")
    if result["field_visits"] != precedent["dryad"]["field"]["raw_status_date_columns"]:
        raise ValueError("field visit-count disagreement with source-unit audit")
    return {
        "schema_version": 1,
        "doi": "10.5061/dryad.4mw6m90jv",
        "manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "predecessor_report_sha256": hashlib.sha256(previous.read_bytes()).hexdigest(),
        "field_panel": result,
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Generate or check the original Dryad field-panel audit offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/external_dryad_field_panel.json")
    )
    parser.add_argument("--check", action="store_true", help="Verify report without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        content = json.dumps(audit_dryad_field_panel(args.data_dir), indent=2) + "\n"
    except (ValueError, KeyError, OSError, ET.ParseError, BadZipFile, csv.Error) as exc:
        parser.exit(1, f"Dryad field-panel audit failed: {exc}\n")
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != content:
            parser.exit(1, f"Dryad field-panel report missing or stale: {args.output}\n")
        print(f"Dryad field-panel audit matches source: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"wrote Dryad field-panel audit: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
