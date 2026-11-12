"""Integrity-first intake of the independent Corteva potato late-blight release.

The original Zenodo TSV contains repeated plot assessments and unusual exact
row multiplicities. This audit deliberately does not deduplicate observations,
infer a trial protocol, estimate treatment effects or fit disease models.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

SOURCE_URL = (
    "https://zenodo.org/records/6352735/files/"
    "corteva-potato-late-blight.txt?download=1"
)
SOURCE_DOI = "10.5281/zenodo.6352735"
SOURCE_SHA256 = "e89e391b32915df358f66ccd95e20c3d2d922c8ccfb5d1c6efb8b5ccdf198096"
SOURCE_ZENODO_MD5 = "4bd9fa37126cf6f6842bb3491a1779e7"
SOURCE_COLUMNS = (
    "Country", "Latitude", "Longitude", "Date", "CropStage", "Trial",
    "Plot", "Treatment", "Untreated", "Value",
)

YEAR_COLUMNS = (
    "year", "source_rows", "distinct_full_records", "exact_repeat_excess",
    "repeated_100x_signatures", "site_year_cells", "trial_code_cells",
    "candidate_plot_ids", "event_keys_with_different_values",
)
SITE_COLUMNS = (
    "year", "country", "latitude", "longitude", "source_rows",
    "distinct_full_records", "exact_repeat_excess", "repeated_100x_signatures",
    "trial_codes", "candidate_plot_ids", "untreated_plot_ids", "treated_plot_ids",
    "event_keys_with_different_values",
)
TRIAL_COLUMNS = (
    "year", "country", "latitude", "longitude", "trial_code",
    "source_rows", "distinct_full_records", "exact_repeat_excess",
    "candidate_plot_ids", "untreated_plot_ids", "treated_plot_ids",
    "event_keys_with_different_values",
)
CONFLICT_COLUMNS = (
    "year", "country", "latitude", "longitude", "trial_code", "plot_code",
    "assessment_date", "crop_stage", "distinct_recorded_values",
)

SiteKey = tuple[str, Decimal, Decimal, int]
TrialKey = tuple[SiteKey, int]
PlotKey = tuple[TrialKey, int]
EventKey = tuple[PlotKey, date, str]
Signature = tuple[str, ...]


@dataclass(frozen=True)
class PotatoIntakeAudit:
    """Non-inferential source-profile tables and hash-pinned provenance."""

    years: list[dict[str, Any]]
    sites: list[dict[str, Any]]
    trial_aliases: list[dict[str, Any]]
    conflicting_events: list[dict[str, Any]]
    summary: dict[str, Any]


def _decimal(value: str, name: str, lower: int, upper: int) -> Decimal:
    """Validate finite numeric input without changing coordinate precision."""
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name} is not numeric: {value!r}") from exc
    if not result.is_finite() or not lower <= result <= upper:
        raise ValueError(f"{name} outside finite range {lower}..{upper}")
    return result


def _positive_int(value: str, name: str) -> int:
    """Require a literal positive source identifier, never silently truncate."""
    if not value.isascii() or not value.isdecimal() or int(value) == 0:
        raise ValueError(f"{name} must be a positive integer: {value!r}")
    return int(value)


def _site(site: SiteKey) -> dict[str, str | int]:
    return {
        "year": site[3],
        "country": site[0],
        "latitude": str(site[1]),
        "longitude": str(site[2]),
    }


def _sort_site(site: SiteKey) -> tuple[int, str, Decimal, Decimal]:
    return (site[3], site[0], site[1], site[2])


def audit_potato_source(path: Path, *, verify_source: bool = True) -> PotatoIntakeAudit:
    """Audit the original TSV at source row, site-year, trial-code and plot levels.

    Exact repeated rows are counted, never dropped from a response analysis
    because no response analysis is authorized here. A plot is a *candidate*
    experimental unit, pending the author's source protocol and data dictionary.
    """
    source_bytes = path.read_bytes()
    digest = hashlib.sha256(source_bytes).hexdigest()
    md5 = hashlib.md5(source_bytes, usedforsecurity=False).hexdigest()
    if verify_source and (digest != SOURCE_SHA256 or md5 != SOURCE_ZENODO_MD5):
        raise ValueError("potato TSV source checksum mismatch")

    signatures: Counter[Signature] = Counter()
    signature_groups: dict[Signature, tuple[SiteKey, TrialKey]] = {}
    source_rows: Counter[SiteKey] = Counter()
    alias_rows: Counter[TrialKey] = Counter()
    assignments: dict[PlotKey, tuple[int, bool]] = {}
    event_values: dict[EventKey, set[Decimal]] = defaultdict(set)

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != SOURCE_COLUMNS:
            raise ValueError("potato TSV source column contract changed")
        for line_no, row in enumerate(reader, start=2):
            if None in row or any(value is None or not value.strip() for value in row.values()):
                raise ValueError(f"missing or malformed source field at line {line_no}")
            try:
                assessment = date.fromisoformat(row["Date"])
            except ValueError as exc:
                raise ValueError(f"invalid Date at line {line_no}") from exc
            lat = _decimal(row["Latitude"], "Latitude", -90, 90)
            lon = _decimal(row["Longitude"], "Longitude", -180, 180)
            response = _decimal(row["Value"], "Value", 0, 100)
            trial = _positive_int(row["Trial"], "Trial")
            plot = _positive_int(row["Plot"], "Plot")
            treatment = _positive_int(row["Treatment"], "Treatment")
            if row["Untreated"] not in ("0", "1"):
                raise ValueError(f"invalid Untreated flag at line {line_no}")
            if not row["Country"].strip():
                raise ValueError(f"missing source Country at line {line_no}")

            site: SiteKey = (row["Country"], lat, lon, assessment.year)
            alias: TrialKey = (site, trial)
            plot_key: PlotKey = (alias, plot)
            assignment = (treatment, row["Untreated"] == "1")
            previous = assignments.setdefault(plot_key, assignment)
            if previous != assignment:
                raise ValueError(
                    "plot changes treatment or untreated status within source trial: "
                    f"line {line_no}"
                )
            signature = tuple(row[column] for column in SOURCE_COLUMNS)
            signatures[signature] += 1
            signature_groups[signature] = (site, alias)
            source_rows[site] += 1
            alias_rows[alias] += 1
            event_values[(plot_key, assessment, row["CropStage"])].add(response)

    if not signatures:
        raise ValueError("potato TSV source contains no records")

    unique_site: Counter[SiteKey] = Counter()
    unique_alias: Counter[TrialKey] = Counter()
    excess_site: Counter[SiteKey] = Counter()
    excess_alias: Counter[TrialKey] = Counter()
    hundred_site: Counter[SiteKey] = Counter()
    multiplicity: Counter[int] = Counter()
    for signature, count in signatures.items():
        site, alias = signature_groups[signature]
        unique_site[site] += 1
        unique_alias[alias] += 1
        excess_site[site] += count - 1
        excess_alias[alias] += count - 1
        multiplicity[count] += 1
        if count == 100:
            hundred_site[site] += 1

    plots_by_site: dict[SiteKey, list[PlotKey]] = defaultdict(list)
    plots_by_alias: dict[TrialKey, list[PlotKey]] = defaultdict(list)
    for key in assignments:
        plots_by_site[key[0][0]].append(key)
        plots_by_alias[key[0]].append(key)

    conflicts_by_site: Counter[SiteKey] = Counter()
    conflicts_by_alias: Counter[TrialKey] = Counter()
    conflicts: list[dict[str, Any]] = []
    for (plot_key, assessed, stage), values in event_values.items():
        if len(values) <= 1:
            continue
        alias, plot = plot_key
        site, trial = alias
        conflicts_by_site[site] += 1
        conflicts_by_alias[alias] += 1
        conflicts.append(
            {
                **_site(site),
                "trial_code": trial,
                "plot_code": plot,
                "assessment_date": assessed.isoformat(),
                "crop_stage": stage,
                "distinct_recorded_values": len(values),
            }
        )
    conflicts.sort(
        key=lambda row: (
            row["year"], row["country"], Decimal(row["latitude"]),
            Decimal(row["longitude"]), row["trial_code"], row["plot_code"],
            row["assessment_date"], row["crop_stage"],
        )
    )

    def plot_counts(keys: list[PlotKey]) -> dict[str, int]:
        """Count candidate plot labels without calling them randomized replicates."""
        return {
            "candidate_plot_ids": len(keys),
            "untreated_plot_ids": sum(assignments[key][1] for key in keys),
            "treated_plot_ids": sum(not assignments[key][1] for key in keys),
        }

    sites: list[dict[str, Any]] = []
    for site in sorted(source_rows, key=_sort_site):
        sites.append(
            {
                **_site(site),
                "source_rows": source_rows[site],
                "distinct_full_records": unique_site[site],
                "exact_repeat_excess": excess_site[site],
                "repeated_100x_signatures": hundred_site[site],
                "trial_codes": sum(alias[0] == site for alias in alias_rows),
                **plot_counts(plots_by_site[site]),
                "event_keys_with_different_values": conflicts_by_site[site],
            }
        )

    aliases: list[dict[str, Any]] = []
    for alias in sorted(alias_rows, key=lambda a: (*_sort_site(a[0]), a[1])):
        site, trial = alias
        aliases.append(
            {
                **_site(site),
                "trial_code": trial,
                "source_rows": alias_rows[alias],
                "distinct_full_records": unique_alias[alias],
                "exact_repeat_excess": excess_alias[alias],
                **plot_counts(plots_by_alias[alias]),
                "event_keys_with_different_values": conflicts_by_alias[alias],
            }
        )

    years: list[dict[str, Any]] = []
    for year in sorted({site[3] for site in source_rows}):
        year_sites = [site for site in source_rows if site[3] == year]
        year_aliases = [alias for alias in alias_rows if alias[0][3] == year]
        years.append(
            {
                "year": year,
                "source_rows": sum(source_rows[site] for site in year_sites),
                "distinct_full_records": sum(unique_site[site] for site in year_sites),
                "exact_repeat_excess": sum(excess_site[site] for site in year_sites),
                "repeated_100x_signatures": sum(hundred_site[site] for site in year_sites),
                "site_year_cells": len(year_sites),
                "trial_code_cells": len(year_aliases),
                "candidate_plot_ids": sum(len(plots_by_site[site]) for site in year_sites),
                "event_keys_with_different_values": sum(
                    conflicts_by_site[site] for site in year_sites
                ),
            }
        )

    summary: dict[str, Any] = {
        "source_doi": SOURCE_DOI,
        "source_url": SOURCE_URL,
        "source_sha256": digest,
        "source_md5_matches_zenodo": md5 == SOURCE_ZENODO_MD5,
        "source_md5": md5,
        "original_source_rows": sum(source_rows.values()),
        "distinct_complete_row_signatures": len(signatures),
        "exact_repeat_excess_rows": sum(count - 1 for count in signatures.values()),
        "exact_repeat_multiplicity_distribution": {
            str(k): multiplicity[k] for k in sorted(multiplicity)
        },
        "signatures_repeated_100_times": multiplicity[100],
        "site_year_geocode_cells": len(source_rows),
        "distinct_trial_code_labels": len({alias[1] for alias in alias_rows}),
        "site_year_trial_code_cells": len(alias_rows),
        "candidate_plot_keys": len(assignments),
        "distinct_assessment_event_keys": len(event_values),
        "event_keys_with_different_recorded_values": len(conflicts),
        "source_years": sorted({site[3] for site in source_rows}),
        "source_trial_count_in_title": 18,
        "interpretation_limits": [
            "Rows repeated verbatim are signatures, not independent field observations.",
            "The 18 geocoded site-years do not resolve 34 source trial-code cells.",
            "Plot keys are provisional; a randomization and trial dictionary is still needed.",
            "The Value column has no explicit endpoint-type field identifying tuber yield.",
            "Same event keys with different values are retained and not averaged.",
            "No source rows are deleted, corrected, imputed, or used for treatment inference.",
        ],
        "permitted_actions": ["source_integrity_audit", "design_identity_inventory"],
        "requires_protocol": [
            "trial_and_plot_allocation_reconciliation",
            "value_endpoint_unit_dictionary",
            "repeat_assessment_and_multiplicity_explanation",
            "treatment_dictionary_across_site_years",
        ],
    }
    return PotatoIntakeAudit(years, sites, aliases, conflicts, summary)


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_potato_audit(audit: PotatoIntakeAudit, output_dir: Path) -> None:
    """Persist only aggregated evidence and ambiguity flags, not original rows."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "years.csv", YEAR_COLUMNS, audit.years)
    _write_csv(output_dir / "site_years.csv", SITE_COLUMNS, audit.sites)
    _write_csv(output_dir / "trial_aliases.csv", TRIAL_COLUMNS, audit.trial_aliases)
    _write_csv(output_dir / "conflicting_events.csv", CONFLICT_COLUMNS, audit.conflicting_events)
    (output_dir / "summary.json").write_text(
        json.dumps(audit.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    """Audit a locally downloaded original source against its published identity."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Original Zenodo TSV")
    parser.add_argument("--output", type=Path, required=True, help="Derived result directory")
    args = parser.parse_args()
    result = audit_potato_source(args.source)
    write_potato_audit(result, args.output)
    print(json.dumps(result.summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
