"""Export source-preserving day-3/day-7 pairs from the aphid field worksheet.

The source has two observations per provisional sampling series. This module
describes the within-series change in the *recorded mortality rate* only; it
does not infer an independent field plot, a sampling calendar, or a pesticide
treatment effect. It never combines the field rates with controlled cohorts.
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
from crop_protection_ps.aphid_dryad_units import (
    _FIELD_UNIT,
    _aphid_field,
    _read_workbook,
)

_SOURCE = "zenodo_aphid_pesticide_19805135"
_DATASET = "aphid_experiment_5_field"
_ACTION = "within_series_mortality_description"
_DAYS = ("Day3_postpesticide", "Day7_postpesticide")
_FIXED_EXPOSURE_FIELDS = ("Base_number", "Order", "Type", "CONC", "DH_above26")
_CSV_FIELDS = (
    *_FIELD_UNIT,
    "Order",
    "Type",
    "CONC",
    "DH_above26",
    "Base_number",
    "Day3_PopSize",
    "Day7_PopSize",
    "Day3_Mortality",
    "Day7_Mortality",
    "Day7_minus_Day3_Mortality",
)


def _source_rate(value: str, field: str) -> float:
    """Parse a finite source rate without treating it as a binomial count."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError(f"invalid {field}: {value!r}")
    return number


def pair_source_field_rows(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Construct paired records without treating the provisional key as plot ID."""
    unit_report = _aphid_field(rows)
    groups: dict[tuple[str, ...], dict[str, Mapping[str, str]]] = defaultdict(dict)
    for row in rows:
        series = tuple(row[field] for field in _FIELD_UNIT)
        sampling = row["SamplingDay"]
        if sampling not in _DAYS or sampling in groups[series]:
            raise ValueError(f"invalid or repeated sampling-day label for field series: {sampling}")
        groups[series][sampling] = row

    pairs: list[dict[str, str]] = []
    by_site: Counter[str] = Counter()
    by_treat: Counter[str] = Counter()
    changes: Counter[str] = Counter()
    same_source_date_pairs = 0
    fractional_baselines = 0
    for key, sample in sorted(groups.items()):
        if set(sample) != set(_DAYS):
            raise ValueError(f"incomplete source field series: {key}")
        early, late = (sample[name] for name in _DAYS)
        if any(early[field] != late[field] for field in _FIXED_EXPOSURE_FIELDS):
            raise ValueError(f"changing baseline or exposure within field series: {key}")
        early_rate = _source_rate(early["Mortality"], "day-3 mortality")
        late_rate = _source_rate(late["Mortality"], "day-7 mortality")
        delta = late_rate - early_rate
        classification = "positive" if delta > 1e-10 else "negative" if delta < -1e-10 else "zero"
        changes[classification] += 1
        by_site[early["Site"]] += 1
        by_treat[early["Treat"]] += 1
        same_source_date_pairs += early["Date"] == late["Date"]
        fractional_baselines += not float(early["Base_number"]).is_integer()
        pairs.append(
            {
                **dict(zip(_FIELD_UNIT, key, strict=True)),
                **{
                    field: early[field]
                    for field in _FIXED_EXPOSURE_FIELDS
                    if field != "Base_number"
                },
                "Base_number": early["Base_number"],
                "Day3_PopSize": early["PopSize"],
                "Day7_PopSize": late["PopSize"],
                "Day3_Mortality": early["Mortality"],
                "Day7_Mortality": late["Mortality"],
                "Day7_minus_Day3_Mortality": f"{delta:.10f}",
            }
        )

    if len(pairs) != unit_report["provisional_series_count"]:
        raise ValueError("pair count disagrees with audited field series")
    if unit_report["complete_day3_day7_series"] != len(pairs):
        raise ValueError("field source audit contains incomplete pairs")
    if any(
        unit_report[field]
        for field in (
            "repeated_sampling_keys",
            "changed_baseline_series",
            "changed_exposure_series",
        )
    ):
        raise ValueError("field source audit has conflicting series metadata")

    return {
        "series": pairs,
        "source_record_count": len(rows),
        "provisional_series_count": len(pairs),
        "pairs_with_same_source_date_serial": same_source_date_pairs,
        "series_by_site": dict(sorted(by_site.items())),
        "series_by_treatment_label": dict(sorted(by_treat.items())),
        "fractional_baseline_series": fractional_baselines,
        "recorded_day7_minus_day3_signs": {
            name: changes[name] for name in ("negative", "zero", "positive")
        },
        "source_date_serials_by_site": unit_report["source_date_serials_by_site"],
    }


def audit_aphid_field_pairs(data_dir: Path) -> dict[str, Any]:
    """Require verified source integrity and an allowed descriptive contract."""
    contract_path = data_dir / "external" / "analysis_eligibility.json"
    contract = validate_analysis_contract(data_dir, contract_path)
    if analysis_decision(contract, _DATASET, _ACTION)["status"] != "allowed":
        raise ValueError("aphid within-series description is not permitted")
    root = data_dir / "external"
    sheets = _read_workbook(root / _SOURCE / "Experiment.xlsx")
    if set(sheets) != {"Experiment1", "Experiment2", "Experiment3", "Experiment4", "Experiment5"}:
        raise ValueError("unexpected aphid workbook sheets")
    paired = pair_source_field_rows(sheets["Experiment5"])
    return {
        "schema_version": 1,
        "source_doi": "10.5281/zenodo.19805135",
        "manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "analysis_contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "analysis": _ACTION,
        "source_sheet": "Experiment5",
        "provisional_series_fields": list(_FIELD_UNIT),
        "source_date_interpretation": "published_excel_serial_unverified_as_sampling_date",
        "summary": {key: value for key, value in paired.items() if key != "series"},
        "series": paired["series"],
        "limitations": [
            "The composite series key is provisional; independent field plots are not established.",
            "Two nominal sampling days use the same Date value within every recorded pair.",
            "Date is preserved as a source serial; follow-up calendar dates are not inferred.",
            "Mortality is a derived population rate, not an integer DEAD/TOTAL observation.",
            "Day-7 minus day-3 change is within-series description, not treatment efficacy.",
            "No experimental control contrast, uncertainty interval or causal model is fitted.",
        ],
    }


def render_reports(report: Mapping[str, Any]) -> dict[str, str]:
    """Render the two source-derived artifacts with stable row and field order."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for series in report["series"]:
        writer.writerow(series)
    return {
        "summary.json": json.dumps(report, indent=2) + "\n",
        "paired_series.csv": output.getvalue(),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Write or read-only verify the descriptively eligible source field pairs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/external_aphid_field"))
    parser.add_argument("--check", action="store_true", help="Check outputs without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        expected = render_reports(audit_aphid_field_pairs(args.data_dir))
    except (
        ValueError,
        OSError,
        KeyError,
        StopIteration,
        ET.ParseError,
        BadZipFile,
        csv.Error,
    ) as exc:
        parser.exit(1, f"aphid field pairing failed: {exc}\n")
    if args.check:
        stale = [
            filename
            for filename, content in expected.items()
            if not (args.output_dir / filename).exists()
            or (args.output_dir / filename).read_text(encoding="utf-8") != content
        ]
        if stale:
            parser.exit(1, f"aphid field pair reports missing or stale: {', '.join(stale)}\n")
        print(f"verified {len(expected)} aphid field reports in {args.output_dir}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in expected.items():
            (args.output_dir / filename).write_text(content, encoding="utf-8")
        print(f"wrote {len(expected)} aphid field reports to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
