"""Review literal Dryad station-weather readings without estimating exposure.

The 214 station dates are calendar observations, not independent plants or
biological treatment replicates. Flag source defects without repairing values,
constructing lags, or claiming a temperature–disease relationship.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

from crop_protection_ps.analysis_eligibility import (
    analysis_decision,
    validate_analysis_contract,
)
from crop_protection_ps.dryad_field_panel import _weather_dates, audit_dryad_field_panel

_SOURCE = "dryad_pathogen_temperature_4mw6m90jv"
_SOURCE_FILE = "daily_high_temps.txt"
_ASSET = "dryad_daily_weather"
_ACTION = "source_weather_quality_review"
_SOURCE_FIELDS = ("Date", "High", "Low")
_RECORD_FIELDS = (
    "record_order",
    "calendar_date",
    *_SOURCE_FIELDS,
    "quality_flag",
    "high_missing",
    "low_missing",
    "low_above_high",
    "aligned_field_visit",
)
_EVENT_FIELDS = (
    "record_order",
    "calendar_date",
    "issue",
    "Date",
    "High",
    "Low",
    "aligned_field_visit",
)


def _temperature(raw: str, field: str, observed: date) -> float | None:
    """Validate each present recorded component, even if its pair is absent."""
    if not isinstance(raw, str):
        raise ValueError(f"non-string Dryad {field} temperature on {observed}")
    if not raw.strip():
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid Dryad {field} temperature on {observed}") from exc
    if not math.isfinite(value):
        raise ValueError(f"nonfinite Dryad {field} temperature on {observed}")
    return value


def describe_weather_records(
    rows: Sequence[Mapping[str, str]], field_visits: Sequence[date]
) -> dict[str, Any]:
    """Summarize source quality, retaining every original High/Low string.

    ``field_visits`` identifies matching calendar dates only. Alignment does
    not validate weather-station measurements as plant-level exposures.
    """
    if not field_visits or any(type(day) is not date for day in field_visits):
        raise ValueError("missing or invalid independently audited Dryad field dates")
    if list(field_visits) != sorted(set(field_visits)):
        raise ValueError("duplicate or unordered Dryad field-visit dates")

    # This existing validator protects the weather schema, date identities,
    # and high/low anomaly semantics used by the predecessor field audit.
    source_dates = _weather_dates(rows)
    visit_dates = set(field_visits)
    records: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    quality_counts: Counter[str] = Counter()
    observed_order: list[date] = []

    for order, row in enumerate(rows, start=1):
        if set(row) != set(_SOURCE_FIELDS) or any(
            not isinstance(row[field], str) for field in _SOURCE_FIELDS
        ):
            raise ValueError("unexpected Dryad weather source columns or value types")
        observed = datetime.strptime(row["Date"], "%m/%d/%y").date()
        observed_order.append(observed)
        high = _temperature(row["High"], "High", observed)
        low = _temperature(row["Low"], "Low", observed)
        missing_high = high is None
        missing_low = low is None
        reversed_pair = high is not None and low is not None and low > high
        if source_dates[observed] != {
            "missing_temperature": missing_high or missing_low,
            "low_above_high": reversed_pair,
        }:
            raise ValueError("Dryad weather review disagrees with field-panel validation")

        issues: list[str] = []
        if missing_high:
            issues.append("missing_high")
        if missing_low:
            issues.append("missing_low")
        if reversed_pair:
            issues.append("low_above_high")
        quality_flag = "+".join(issues) if issues else "ok"
        quality_counts[quality_flag] += 1
        matched = observed in visit_dates
        record = {
            "record_order": order,
            "calendar_date": observed.isoformat(),
            **row,
            "quality_flag": quality_flag,
            "high_missing": missing_high,
            "low_missing": missing_low,
            "low_above_high": reversed_pair,
            "aligned_field_visit": matched,
        }
        records.append(record)
        for issue in issues:
            events.append(
                {
                    "record_order": order,
                    "calendar_date": observed.isoformat(),
                    "issue": issue,
                    "Date": row["Date"],
                    "High": row["High"],
                    "Low": row["Low"],
                    "aligned_field_visit": matched,
                }
            )

    dates = sorted(source_dates)
    gaps = [
        {
            "before": first.isoformat(),
            "after": second.isoformat(),
            "missing_calendar_days": (second - first).days - 1,
        }
        for first, second in pairwise(dates)
        if (second - first).days > 1
    ]
    matched_dates = visit_dates.intersection(source_dates)
    flagged_days = {date.fromisoformat(item["calendar_date"]) for item in events}
    return {
        "source_weather_rows": len(rows),
        "distinct_dates": len(source_dates),
        "first_weather_date": dates[0].isoformat(),
        "last_weather_date": dates[-1].isoformat(),
        "out_of_order_source_rows": sum(
            current < previous for previous, current in pairwise(observed_order)
        ),
        "missing_calendar_days_between_records": sum(
            item["missing_calendar_days"] for item in gaps
        ),
        "calendar_gaps": gaps,
        "quality_flag_counts": dict(sorted(quality_counts.items())),
        "records_missing_high": sum(record["high_missing"] for record in records),
        "records_missing_low": sum(record["low_missing"] for record in records),
        "records_low_above_high": sum(record["low_above_high"] for record in records),
        "source_anomaly_dates": [day.isoformat() for day in sorted(flagged_days)],
        "weather_dates_matching_field_visits": len(matched_dates),
        "field_visit_date_count": len(visit_dates),
        "field_visits_without_weather": [
            day.isoformat() for day in sorted(visit_dates - set(source_dates))
        ],
        "field_visits_on_source_anomaly_dates": [
            day.isoformat() for day in sorted(visit_dates & flagged_days)
        ],
        "source_records": records,
        "quality_events": events,
    }


def audit_dryad_weather_quality(data_dir: Path) -> dict[str, Any]:
    """Check source hashes, descriptive permission, units and field-date audit."""
    root = data_dir.resolve().parent
    contract_path = data_dir / "external/analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    if analysis_decision(contract, _ASSET, _ACTION)["status"] != "allowed":
        raise ValueError("Dryad source weather-quality review not permitted")
    asset = next(item for item in contract["assets"] if item["id"] == _ASSET)

    previous_path = root / "results/external_dryad_field_panel.json"
    previous_bytes = previous_path.read_bytes()
    previous = audit_dryad_field_panel(data_dir)
    if json.loads(previous_bytes) != previous:
        raise ValueError("predecessor Dryad field-panel audit is missing or stale")
    panel = previous["field_panel"]
    visit_dates = [date.fromisoformat(item["date"]) for item in panel["visits"]]

    source_file = data_dir / "external" / _SOURCE / _SOURCE_FILE
    with source_file.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t", strict=True)
        if reader.fieldnames != list(_SOURCE_FIELDS):
            raise ValueError("unexpected Dryad daily-weather source header")
        rows = list(reader)

    report = describe_weather_records(rows, visit_dates)
    if (
        report["source_weather_rows"] != asset["rows"]
        or report["distinct_dates"] != asset["group_count"]
        or asset["table"] != _SOURCE_FILE
        or Path(asset["file"]).name != _SOURCE_FILE
    ):
        raise ValueError("Dryad weather rows/dates disagree with eligibility contract")
    if (
        report["weather_dates_matching_field_visits"] != panel["visits_with_matching_weather_date"]
        or report["field_visit_date_count"] != panel["field_visits"]
        or [
            item["calendar_date"]
            for item in report["source_records"]
            if item["high_missing"] or item["low_missing"]
        ]
        != panel["weather_missing_temperature_dates"]
        or [item["calendar_date"] for item in report["source_records"] if item["low_above_high"]]
        != panel["weather_low_above_high_dates"]
    ):
        raise ValueError("Dryad weather quality disagrees with predecessor field audit")

    return {
        "schema_version": 1,
        "source_doi": "10.5061/dryad.4mw6m90jv",
        "source_file": _SOURCE_FILE,
        "source_table": asset["table"],
        "manifest_sha256": hashlib.sha256(
            (data_dir / "external/manifest.json").read_bytes()
        ).hexdigest(),
        "analysis_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "predecessor_field_panel_sha256": hashlib.sha256(previous_bytes).hexdigest(),
        "analysis": _ACTION,
        "observational_unit": "weather_station_calendar_day_not_individual_plant",
        **report,
        "limitations": [
            "Source High and Low strings and blanks are retained without correction.",
            "A missing component or Low above High requires source-level resolution.",
            "The source README names the Beltsville weather station; site exposure is unverified.",
            "Matching a weather date to a field visit is not exposure validation.",
            "No weather interpolation, reordering, unit conversion or lag building occurs.",
            "No temperature association, causal effect or disease model is fitted.",
        ],
    }


def _csv(records: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    """Serialize source-value observations and anomaly events deterministically."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Keep 214 literal daily observations in CSV, not duplicated in metadata."""
    metadata = {
        key: value
        for key, value in report.items()
        if key not in {"source_records", "quality_events"}
    }
    return {
        "summary.json": json.dumps(metadata, indent=2) + "\n",
        "source_daily_weather.csv": _csv(report["source_records"], _RECORD_FIELDS),
        "quality_events.csv": _csv(report["quality_events"], _EVENT_FIELDS),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Regenerate or verify the permitted Dryad daily-weather quality audit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/external_dryad_weather_quality")
    )
    parser.add_argument("--check", action="store_true", help="Verify files without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        files = render_reports(audit_dryad_weather_quality(args.data_dir))
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError, csv.Error) as exc:
        parser.exit(1, f"Dryad daily-weather quality review failed: {exc}\n")
    if args.check:
        stale = [
            name
            for name, content in files.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"Dryad weather-quality files missing or stale: {', '.join(stale)}\n")
        print(f"verified {len(files)} Dryad daily-weather files in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {len(files)} Dryad daily-weather files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
