"""Export source-verified greenhouse death-case tallies from the Dryad archive.

The source contains case-only rows, each labelled ``dead=1``. It provides no
at-risk population, event-time/censoring definition, or stable plant key for
linking to infection records. Counts are not mortality probabilities.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
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

_SOURCE = "dryad_pathogen_temperature_4mw6m90jv"
_FILE = "seedling_inoculation-_death_data.xlsx"
_ASSET = "dryad_greenhouse_death"
_ACTION = "death_case_tally"
_CELL_FIELDS = ("year", "date", "temperature", "smut exposure", "time", "replicate", "family")
_STRATUM_FIELDS = ("year", "temperature", "smut exposure", "time")
_REQUIRED_COLUMNS = {*_CELL_FIELDS, "dead"}
_CELL_CSV_FIELDS = (*_CELL_FIELDS, "source_death_case_rows")
_STRATUM_CSV_FIELDS = (*_STRATUM_FIELDS, "recorded_case_cells", "source_death_case_rows")


def _require_label(raw: str, field: str) -> str:
    """Verify a nonblank source label without recoding ``NA`` values."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"blank greenhouse death source field: {field}")
    return raw


def _require_integer_label(raw: str, field: str) -> None:
    """Reject invalid source codes while preserving their original strings."""
    value = _require_label(raw, field)
    if not value.isascii() or not value.isdigit():
        raise ValueError(f"invalid greenhouse death {field} code: {value!r}")


def _sort_cell(key: tuple[str, ...]) -> tuple[int, int, float, str, str, int, str]:
    """Deterministically sort original seven-field case cells."""
    return (int(key[0]), int(key[1]), float(key[2]), key[3], key[4], int(key[5]), key[6])


def _sort_stratum(key: tuple[str, ...]) -> tuple[int, float, str, str]:
    """Sort broad source-code strata without interpreting study years."""
    return (int(key[0]), float(key[1]), key[2], key[3])


def summarise_death_cases(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Count original death-case records within labelled cells and strata.

    Each row contributes exactly one recorded case. Identical rows are kept;
    they are not evidence of duplicate plants, and no non-case denominator is
    available in this workbook.
    """
    if not rows:
        raise ValueError("empty Dryad greenhouse death worksheet")

    cells: Counter[tuple[str, ...]] = Counter()
    exact_rows: Counter[tuple[tuple[str, str], ...]] = Counter()
    year_codes: Counter[str] = Counter()
    date_codes: Counter[str] = Counter()
    temperatures: Counter[str] = Counter()

    for row in rows:
        if set(row) != _REQUIRED_COLUMNS:
            raise ValueError("unexpected greenhouse death source columns")
        for field in _REQUIRED_COLUMNS:
            _require_label(row[field], field)
        for field in ("year", "date", "replicate"):
            _require_integer_label(row[field], field)
        try:
            temperature = float(row["temperature"])
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid greenhouse death temperature") from exc
        if not math.isfinite(temperature):
            raise ValueError("invalid greenhouse death temperature")
        if row["dead"] != "1":
            raise ValueError("greenhouse death file requires literal dead=1 cases")

        key = tuple(row[field] for field in _CELL_FIELDS)
        cells[key] += 1
        exact_rows[tuple(sorted(row.items()))] += 1
        year_codes[row["year"]] += 1
        date_codes[row["date"]] += 1
        temperatures[row["temperature"]] += 1

    records = [
        {
            **dict(zip(_CELL_FIELDS, key, strict=True)),
            "source_death_case_rows": cells[key],
        }
        for key in sorted(cells, key=_sort_cell)
    ]
    by_stratum: Counter[tuple[str, ...]] = Counter()
    stratum_cell_counts: Counter[tuple[str, ...]] = Counter()
    for cell_key, case_count in cells.items():
        stratum_key = tuple(cell_key[_CELL_FIELDS.index(field)] for field in _STRATUM_FIELDS)
        by_stratum[stratum_key] += case_count
        stratum_cell_counts[stratum_key] += 1
    strata = [
        {
            **dict(zip(_STRATUM_FIELDS, key, strict=True)),
            "recorded_case_cells": stratum_cell_counts[key],
            "source_death_case_rows": by_stratum[key],
        }
        for key in sorted(by_stratum, key=_sort_stratum)
    ]

    return {
        "source_death_case_rows": len(rows),
        "recorded_case_cells": len(cells),
        "source_exact_repeated_row_excess": sum(n - 1 for n in exact_rows.values()),
        "source_year_code_counts": dict(sorted(year_codes.items())),
        "source_date_serial_counts": dict(sorted(date_codes.items(), key=lambda x: int(x[0]))),
        "source_temperature_code_counts": dict(
            sorted(temperatures.items(), key=lambda x: float(x[0]))
        ),
        "source_case_value": "1",
        "source_records_per_case_cell": {
            str(n): count for n, count in sorted(Counter(cells.values()).items())
        },
        "cell_fields": list(_CELL_FIELDS),
        "stratum_fields": list(_STRATUM_FIELDS),
        "case_cells": records,
        "strata": strata,
    }


def audit_dryad_greenhouse_deaths(data_dir: Path) -> dict[str, Any]:
    """Check source integrity, permission, worksheet schema, and audited units."""
    contract_path = data_dir / "external" / "analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    if analysis_decision(contract, _ASSET, _ACTION)["status"] != "allowed":
        raise ValueError("greenhouse death-case tally not permitted")

    asset = next(item for item in contract["assets"] if item["id"] == _ASSET)
    root = data_dir / "external"
    sheets = _read_workbook(root / _SOURCE / _FILE)
    if set(sheets) != {asset["table"]}:
        raise ValueError("unexpected Dryad greenhouse death worksheet")
    report = summarise_death_cases(sheets[asset["table"]])

    # Validation above has already regenerated and verified the committed
    # experimental-unit audit against checksum-pinned original source bytes.
    audited_path = data_dir.parent / "results/external_aphid_dryad_units.json"
    audited = json.loads(audited_path.read_text(encoding="utf-8"))["dryad"]["greenhouse"]
    expected = {
        "source_death_case_rows": (asset["rows"], audited["death_case_rows"]),
        "recorded_case_cells": (asset["group_count"], audited["death_design_cells"]),
        "source_exact_repeated_row_excess": (audited["death_exact_repeated_rows"],),
    }
    for field, accepted in expected.items():
        if any(report[field] != value for value in accepted):
            raise ValueError(f"greenhouse death tally disagrees with unit audit: {field}")
    if audited["death_case_value"] != 1 or audited["unique_plant_identifier_present"]:
        raise ValueError("greenhouse death-case source assumption disagrees with audit")

    return {
        "schema_version": 1,
        "source_doi": "10.5061/dryad.4mw6m90jv",
        "source_workbook": _FILE,
        "source_sheet": asset["table"],
        "manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "analysis_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "analysis": _ACTION,
        "observational_unit": "recorded_death_case_row_not_verified_unique_plant",
        **report,
        "limitations": [
            "The source is case-only: no at-risk population or noncase records are supplied.",
            "All dead values are literal 1 labels; case rows are never an infection risk.",
            "Fully identical death-case records are retained, not deduplicated as plants.",
            "Date serials and year codes are retained without calendar reinterpretation.",
            "Shared factor labels do not link death cases to greenhouse infection rows.",
            "No mortality rate, survival curve, hazard ratio or temperature effect is estimated.",
        ],
    }


def _csv(records: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> str:
    """Write stable case counts, intentionally without probability columns."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Export concise audit metadata and detailed case counts only once."""
    metadata = {key: value for key, value in report.items() if key not in {"case_cells", "strata"}}
    return {
        "summary.json": json.dumps(metadata, indent=2) + "\n",
        "cases_by_recorded_cell.csv": _csv(report["case_cells"], _CELL_CSV_FIELDS),
        "cases_by_stratum.csv": _csv(report["strata"], _STRATUM_CSV_FIELDS),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Generate or check death-case artifacts offline without source changes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/external_dryad_greenhouse_deaths")
    )
    parser.add_argument("--check", action="store_true", help="Verify files without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        files = render_reports(audit_dryad_greenhouse_deaths(args.data_dir))
    except (
        ValueError,
        KeyError,
        OSError,
        StopIteration,
        ET.ParseError,
        BadZipFile,
        csv.Error,
    ) as exc:
        parser.exit(1, f"Dryad greenhouse death tally failed: {exc}\n")

    if args.check:
        stale = [
            name
            for name, content in files.items()
            if not (args.output_dir / name).exists()
            or (args.output_dir / name).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"Dryad death-case files missing or stale: {', '.join(stale)}\n")
        print(f"verified {len(files)} Dryad death-case files in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (args.output_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {len(files)} Dryad death-case files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
