"""Audit within-trial endpoint comparability in the original wheat field data.

The source has repeated disease and yield measurements but no plot replicate
identifier. A matching endpoint is a *possible descriptive comparison*, not
an independent experimental unit or a treatment-effect estimate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

from crop_protection_ps.external_data import verify_external_data

_SOURCE_PATH = "zenodo_wheat_fungicide_6521175/basf-wheat-diseases.txt"
_SOURCE_DOI = "10.5281/zenodo.6521175"
_FIELDS = (
    "TrialId",
    "Country",
    "Latitude",
    "Longitude",
    "Date",
    "Daft",
    "GsFrom",
    "GsTo",
    "NumSprays",
    "Treatment",
    "Organism",
    "Parameter",
    "Clarifier",
    "Method",
    "SampleUnit",
    "PlantPart",
    "Value",
)
# Hold the assessment conditions fixed while allowing treatment and spray count
# to differ. This deliberately does not average across dates or plant parts.
ENDPOINT_FIELDS = (
    "TrialId",
    "Date",
    "Daft",
    "GsFrom",
    "GsTo",
    "Organism",
    "Parameter",
    "Clarifier",
    "Method",
    "SampleUnit",
    "PlantPart",
)


def _trial_sort(identifier: str) -> int:
    """Sort the numeric trial identifiers without conflating them with counts."""
    return int(identifier)


def _read_wheat_rows(path: Path) -> list[dict[str, str]]:
    """Load a fixed-schema TSV without replacing literal NA codes or values."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t", strict=True)
        if reader.fieldnames is None or (
            len(reader.fieldnames) != len(_FIELDS)
            or set(reader.fieldnames) != set(_FIELDS)
        ):
            raise ValueError("unexpected wheat field-trial columns")

        rows: list[dict[str, str]] = []
        for line_number, original in enumerate(reader, start=2):
            parsed: dict[str, str] = {}
            for field in _FIELDS:
                value = original.get(field)
                if not isinstance(value, str):
                    raise ValueError(f"missing or malformed {field} on source line {line_number}")
                parsed[field] = value
            if None in original:
                raise ValueError(f"extra fields on source line {line_number}")
            rows.append(parsed)
    return rows


def audit_wheat_rows(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Summarise *potential* endpoint pairs and their experimental-unit limits.

    A pair requires exactly one untreated record and one record per treated
    label for the same assessment signature. Repeated records for the same arm
    are marked ambiguous, rather than silently aggregated or pseudoreplicated.
    """
    if not rows:
        raise ValueError("no wheat field observations")

    grouped: dict[tuple[str, ...], list[Mapping[str, str]]] = defaultdict(list)
    by_trial: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    trial_metadata: dict[str, tuple[str, str, str, int]] = {}

    for row_number, row in enumerate(rows, start=2):
        if any(field not in row for field in _FIELDS):
            raise ValueError(f"missing required field on source line {row_number}")
        trial = row["TrialId"]
        if not trial.isdecimal() or not trial:
            raise ValueError(f"invalid TrialId on source line {row_number}")
        try:
            year = date.fromisoformat(row["Date"]).year
            measurement = float(row["Value"])
        except ValueError as exc:
            raise ValueError(f"invalid date or measurement on source line {row_number}") from exc
        if not math.isfinite(measurement):
            raise ValueError(f"nonfinite measurement on source line {row_number}")
        if not row["Treatment"].strip():
            raise ValueError(f"missing treatment on source line {row_number}")

        metadata = (row["Country"], row["Latitude"], row["Longitude"], year)
        if trial in trial_metadata and trial_metadata[trial] != metadata:
            raise ValueError(f"TrialId {trial} is reused across sites or years")
        trial_metadata[trial] = metadata
        grouped[tuple(row[field] for field in ENDPOINT_FIELDS)].append(row)
        by_trial[trial].append(row)

    trial_summary: dict[str, dict[str, Any]] = {
        trial: {
            "trial_id": trial,
            "country": trial_metadata[trial][0],
            "year": trial_metadata[trial][3],
            "source_rows": len(records),
            "treatment_labels": sorted({record["Treatment"] for record in records}),
            "paired_endpoint_groups": 0,
            "paired_treated_records": 0,
            "unpaired_treated_records": 0,
            "unpaired_untreated_records": 0,
            "ambiguous_records": 0,
        }
        for trial, records in by_trial.items()
    }
    paired_groups = 0
    paired_controls = 0
    paired_treated = 0
    unpaired_controls = 0
    unpaired_treated: list[dict[str, str]] = []
    ambiguous_groups: list[dict[str, Any]] = []
    ambiguous_records = 0
    by_parameter: dict[str, dict[str, int]] = defaultdict(lambda: {"groups": 0, "treated": 0})
    by_treatment: Counter[str] = Counter()
    arm_multiplicity: Counter[int] = Counter()

    for key, records in grouped.items():
        descriptor = dict(zip(ENDPOINT_FIELDS, key, strict=True))
        trial = descriptor["TrialId"]
        arms = Counter(record["Treatment"] for record in records)

        if max(arms.values()) > 1:
            ambiguous_groups.append(
                {"endpoint": descriptor, "arm_counts": dict(sorted(arms.items()))}
            )
            ambiguous_records += len(records)
            trial_summary[trial]["ambiguous_records"] += len(records)
            continue

        if "Untreated" in arms and len(arms) > 1:
            treated_here = len(records) - 1
            paired_groups += 1
            paired_controls += 1
            paired_treated += treated_here
            trial_summary[trial]["paired_endpoint_groups"] += 1
            trial_summary[trial]["paired_treated_records"] += treated_here
            parameter = descriptor["Parameter"]
            by_parameter[parameter]["groups"] += 1
            by_parameter[parameter]["treated"] += treated_here
            arm_multiplicity[treated_here] += 1
            by_treatment.update(arm for arm in arms if arm != "Untreated")
            continue

        if "Untreated" in arms:
            unpaired_controls += 1
            trial_summary[trial]["unpaired_untreated_records"] += 1
        else:
            for record in records:
                unpaired_treated.append({**descriptor, "Treatment": record["Treatment"]})
                trial_summary[trial]["unpaired_treated_records"] += 1

    unpaired_treated.sort(
        key=lambda record: (
            _trial_sort(record["TrialId"]),
            record["Date"],
            record["Organism"],
            record["PlantPart"],
            record["Treatment"],
        )
    )
    ambiguous_groups.sort(
        key=lambda item: (
            _trial_sort(item["endpoint"]["TrialId"]),
            item["endpoint"]["Date"],
        )
    )
    return {
        "schema_version": 1,
        "pairing_fields": list(ENDPOINT_FIELDS),
        "source_rows": len(rows),
        "trial_id_count": len(by_trial),
        "endpoint_groups": len(grouped),
        "paired_endpoint_groups": paired_groups,
        "paired_untreated_records": paired_controls,
        "paired_treated_records": paired_treated,
        "unpaired_untreated_records": unpaired_controls,
        "unpaired_treated_records": len(unpaired_treated),
        "ambiguous_endpoint_groups": len(ambiguous_groups),
        "ambiguous_records": ambiguous_records,
        "paired_by_parameter": dict(sorted(by_parameter.items())),
        "paired_by_treatment": dict(sorted(by_treatment.items())),
        "paired_arm_multiplicity": {
            str(arms): count for arms, count in sorted(arm_multiplicity.items())
        },
        "unpaired_treated_endpoints": unpaired_treated,
        "ambiguous_endpoints": ambiguous_groups,
        "trial_summary": [trial_summary[trial] for trial in sorted(by_trial, key=_trial_sort)],
    }


def audit_wheat_data(data_dir: Path) -> dict[str, Any]:
    """Verify the source checksum, then audit endpoint coverage offline."""
    errors = verify_external_data(data_dir)
    if errors:
        raise ValueError("external source integrity failed: " + "; ".join(errors))
    source = data_dir / "external" / _SOURCE_PATH
    result = audit_wheat_rows(_read_wheat_rows(source))
    return {
        "source_doi": _SOURCE_DOI,
        "source_path": _SOURCE_PATH,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        **result,
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Generate or verify a repeatable audit report without changing the data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/external_wheat_pairability.json")
    )
    parser.add_argument("--check", action="store_true", help="Check saved report without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        content = json.dumps(audit_wheat_data(args.data_dir), indent=2, ensure_ascii=False) + "\n"
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(1, f"wheat audit failed: {exc}\n")
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != content:
            parser.exit(1, f"wheat audit missing or stale: {args.output}\n")
        print(f"wheat endpoint audit matches source: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"wrote wheat endpoint audit: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
