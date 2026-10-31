"""Audit source-level experimental units in the aphid and fungal-pathogen data.

All counts describe the original, checksum-verified records. Treatment
replication and biological independence require the source protocol; neither
is inferred from identical rows, spreadsheet columns, or outcome denominators.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import posixpath
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from crop_protection_ps.external_data import verify_external_data
from crop_protection_ps.external_profile import (
    _MAIN,
    _PACKAGE_REL,
    _REL,
    _shared_strings,
    _sheet_rows,
)

_APHID = "zenodo_aphid_pesticide_19805135"
_DRYAD = "dryad_pathogen_temperature_4mw6m90jv"
_APHID_FACTORS: dict[str, tuple[str, ...]] = {
    "Experiment1": ("Temperature", "CONC"),
    "Experiment2": ("Temperature", "CONC", "Treatment_Time"),
    "Experiment3": ("Temperature", "CONC", "Treatment_Time", "Interval", "Order"),
    "Experiment4": ("Temperature", "CONC", "Treatment_Time", "Interval"),
}
_FIELD_UNIT = ("Site", "Treat", "Replicate", "Date", "Interval")
_LAB_FILES: dict[str, str] = {
    "Germination_data.xlsx": "germination",
    "Conjugation_Data_strain_2.xlsx": "conjugation",
    "Conjugation_Data_strain_3.xlsx": "conjugation",
    "Conjugation_Data_strain_4.xlsx": "conjugation",
    "Growth_data_strain_2.xlsx": "growth",
    "Growth_data_strain_3.xlsx": "growth",
    "Growth_data_strain_4.xlsx": "growth",
}


def _read_workbook(path: Path) -> dict[str, list[dict[str, str]]]:
    """Read source cells from OOXML without modifying or calculating the XLSX."""
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall(f"{{{_PACKAGE_REL}}}Relationship")
        }
        shared = _shared_strings(archive)
        tables: dict[str, list[dict[str, str]]] = {}
        for sheet in workbook.iter(f"{{{_MAIN}}}sheet"):
            name = sheet.attrib["name"]
            relation_id = sheet.get(f"{{{_REL}}}id")
            if relation_id is None or relation_id not in targets:
                raise ValueError(f"missing XLSX worksheet relationship in {path.name}")
            target = targets[relation_id]
            part = posixpath.normpath(
                target.lstrip("/") if target.startswith("/") else posixpath.join("xl", target)
            )
            if not part.startswith("xl/worksheets/") or part not in archive.namelist():
                raise ValueError(f"unsafe or missing XLSX part: {part}")
            rows, formulas = _sheet_rows(archive, part, shared)
            if name.casefold().replace(" ", "").startswith("readme"):
                continue
            if formulas:
                raise ValueError(f"unexpected formulas in observational worksheet: {name}")
            if not rows:
                raise ValueError(f"missing header in worksheet: {name}")
            header = rows[0]
            if set(header) != set(range(len(header))) or len(set(header.values())) != len(header):
                raise ValueError(f"invalid header in worksheet: {name}")
            tables[name] = [
                {field: original.get(index, "") for index, field in header.items()}
                for original in rows[1:]
            ]
        return tables


def _required(row: Mapping[str, str], fields: Sequence[str], source: str) -> None:
    """Reject schema drift or missing categorical identifiers."""
    if any(not isinstance(row.get(field), str) or not row[field].strip() for field in fields):
        raise ValueError(f"missing field in {source}: {', '.join(fields)}")


def _number(raw: str, field: str, *, integer: bool = False) -> float:
    """Parse a finite source number; integer counts must remain integer counts."""
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}: {raw!r}") from exc
    if not math.isfinite(value) or (integer and not value.is_integer()):
        raise ValueError(f"invalid {field}: {raw!r}")
    return value


def _multiplicity(counts: Iterable[int]) -> dict[str, int]:
    """Count groups of each size in a deterministic, JSON-compatible order."""
    return {str(size): amount for size, amount in sorted(Counter(counts).items())}


def _unique_rows(rows: Sequence[Mapping[str, str]]) -> int:
    """Count excess fully identical rows without dropping plausible individuals."""
    duplicates = Counter(tuple(sorted(record.items())) for record in rows)
    return sum(count - 1 for count in duplicates.values())


def _aphid_controlled(
    name: str, rows: Sequence[Mapping[str, str]], factors: Sequence[str]
) -> dict[str, Any]:
    """Summarize binomial cohorts by treatment-cell design, not aphid count."""
    groups: Counter[tuple[str, ...]] = Counter()
    aphids = 0
    deaths = 0
    for row in rows:
        _required(row, (*factors, "TOTAL", "DEAD"), name)
        total = int(_number(row["TOTAL"], "TOTAL", integer=True))
        dead = int(_number(row["DEAD"], "DEAD", integer=True))
        if total <= 0 or not 0 <= dead <= total:
            raise ValueError(f"invalid DEAD/TOTAL cohort in {name}")
        groups[tuple(row[key] for key in factors)] += 1
        aphids += total
        deaths += dead
    if not rows:
        raise ValueError(f"empty controlled experiment: {name}")
    return {
        "rows": len(rows),
        "condition_fields": list(factors),
        "condition_cells": len(groups),
        "records_per_condition": _multiplicity(groups.values()),
        "counted_aphids": aphids,
        "recorded_deaths": deaths,
        "explicit_replicate_id": False,
    }


def _aphid_field(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Find repeated field follow-ups using a composite *provisional* series key."""
    groups: dict[tuple[str, ...], list[Mapping[str, str]]] = defaultdict(list)
    sites: Counter[str] = Counter()
    dates: dict[str, set[str]] = defaultdict(set)
    fractional_baselines = 0
    fractional_populations = 0
    for row in rows:
        _required(
            row,
            (
                *_FIELD_UNIT,
                "SamplingDay",
                "PopSize",
                "Base_number",
                "Mortality",
                "DH_above26",
                "Order",
                "Type",
                "CONC",
            ),
            "Experiment5",
        )
        baseline = _number(row["Base_number"], "Base_number")
        population = _number(row["PopSize"], "PopSize")
        mortality = _number(row["Mortality"], "Mortality")
        if baseline <= 0 or population < 0 or not 0 <= mortality <= 1:
            raise ValueError("invalid aphid field population or mortality")
        if not math.isclose(mortality, 1 - population / baseline, abs_tol=1e-7):
            raise ValueError("field mortality disagrees with 1 - PopSize / Base_number")
        fractional_baselines += not baseline.is_integer()
        fractional_populations += not population.is_integer()
        groups[tuple(row[field] for field in _FIELD_UNIT)].append(row)
        sites[row["Site"]] += 1
        dates[row["Site"]].add(row["Date"])
    if not rows:
        raise ValueError("empty aphid field experiment")

    repeated_sampling = 0
    complete_pairs = 0
    changed_baselines = 0
    changed_exposures = 0
    for series in groups.values():
        sampling = Counter(record["SamplingDay"] for record in series)
        repeated_sampling += sum(count - 1 for count in sampling.values())
        complete_pairs += set(sampling) == {
            "Day3_postpesticide",
            "Day7_postpesticide",
        } and all(count == 1 for count in sampling.values())
        changed_baselines += len({record["Base_number"] for record in series}) > 1
        changed_exposures += len(
            {(record["Order"], record["Type"], record["CONC"], record["DH_above26"])
             for record in series}
        ) > 1
    return {
        "rows": len(rows),
        "provisional_series_fields": list(_FIELD_UNIT),
        "provisional_series_count": len(groups),
        "observations_per_series": _multiplicity(map(len, groups.values())),
        "complete_day3_day7_series": complete_pairs,
        "repeated_sampling_keys": repeated_sampling,
        "changed_baseline_series": changed_baselines,
        "changed_exposure_series": changed_exposures,
        "site_rows": dict(sorted(sites.items())),
        "source_date_serials_by_site": {
            site: sorted(serials, key=float) for site, serials in sorted(dates.items())
        },
        "fractional_base_number_rows": fractional_baselines,
        "fractional_popsize_rows": fractional_populations,
        "mortality_is_derived_rate": True,
    }


def _dryad_lab(
    rows: Sequence[Mapping[str, str]], kind: str, filename: str
) -> dict[str, Any]:
    """Distinguish assay subsamples, temperature replicates, and run codes."""
    growth = kind == "growth"
    keys = ("Temperature", "Temp.Rep", "Run.Num")
    sample_keys = ("Strain", *keys, "Mating.Type", "Replicate") if growth else (*keys, "Rep")
    groups: Counter[tuple[str, ...]] = Counter()
    samples: Counter[tuple[str, ...]] = Counter()
    temperatures: set[str] = set()
    runs: set[str] = set()
    photo_ids: Counter[str] = Counter()

    for row in rows:
        _required(row, sample_keys, filename)
        _number(row["Temperature"], "Temperature")
        _number(row["Temp.Rep"], "Temp.Rep", integer=True)
        _number(row["Run.Num"], "Run.Num", integer=True)
        groups[tuple(row[key] for key in keys)] += 1
        samples[tuple(row[key] for key in sample_keys)] += 1
        temperatures.add(row["Temperature"])
        runs.add(row["Run.Num"])
        if growth:
            _required(row, ("Picture ID", "Colonly.Count"), filename)
            if _number(row["Colonly.Count"], "Colonly.Count", integer=True) < 0:
                raise ValueError(f"negative colony count in {filename}")
            photo_ids[row["Picture ID"]] += 1
        else:
            numerator = "Sum.Germ" if kind == "germination" else "Sum.Mating"
            _required(row, (numerator, "Sum.Total", "Sum.Prop"), filename)
            successes = _number(row[numerator], numerator, integer=True)
            total = _number(row["Sum.Total"], "Sum.Total", integer=True)
            fraction = _number(row["Sum.Prop"], "Sum.Prop")
            if total <= 0 or not 0 <= successes <= total or not 0 <= fraction <= 1:
                raise ValueError(f"invalid assay count or proportion in {filename}")
            if not math.isclose(fraction, successes / total, abs_tol=1e-7):
                raise ValueError(f"published assay proportion disagrees with count in {filename}")

    if not rows:
        raise ValueError(f"empty Dryad lab worksheet: {filename}")
    return {
        "assay": kind,
        "rows": len(rows),
        "temperatures": len(temperatures),
        "temperature_run_groups": len(groups),
        "records_per_temperature_run": _multiplicity(groups.values()),
        "distinct_run_codes": len(runs),
        "unique_nested_record_keys": len(samples),
        "duplicate_nested_record_keys": sum(n - 1 for n in samples.values()),
        **(
            {
                "distinct_picture_ids": len(photo_ids),
                "repeated_picture_id_rows": sum(n - 1 for n in photo_ids.values()),
            }
            if growth
            else {}
        ),
    }


def _dryad_greenhouse(
    infection: Sequence[Mapping[str, str]], death: Sequence[Mapping[str, str]]
) -> dict[str, Any]:
    """Report plant rows and case-only death rows without inventing plant IDs."""
    infection_fields = (
        "year", "Date", "Temperature", "Smut Exposure", "Time", "Rep", "Family"
    )
    death_fields = (
        "year", "date", "temperature", "smut exposure", "time", "replicate", "family"
    )
    groups: Counter[tuple[str, ...]] = Counter()
    status: Counter[str] = Counter()
    years: Counter[str] = Counter()
    for row in infection:
        _required(row, (*infection_fields, "Disease Status"), "Dryad greenhouse infection")
        groups[tuple(row[field] for field in infection_fields)] += 1
        status[row["Disease Status"]] += 1
        years[row["year"]] += 1
    if not infection:
        raise ValueError("empty greenhouse infection records")

    death_groups: Counter[tuple[str, ...]] = Counter()
    for row in death:
        _required(row, (*death_fields, "dead"), "Dryad greenhouse death")
        if _number(row["dead"], "dead", integer=True) != 1:
            raise ValueError("death file does not contain one death case per row")
        death_groups[tuple(row[field] for field in death_fields)] += 1
    if not death:
        raise ValueError("empty greenhouse death records")

    return {
        "infection_rows": len(infection),
        "infection_design_cells": len(groups),
        "infection_rows_per_design_cell": _multiplicity(groups.values()),
        "infection_exact_repeated_rows": _unique_rows(infection),
        "infection_year_codes": dict(sorted(years.items())),
        "disease_status_codes": dict(sorted(status.items())),
        "death_case_rows": len(death),
        "death_design_cells": len(death_groups),
        "death_exact_repeated_rows": _unique_rows(death),
        "death_case_value": 1,
        "unique_plant_identifier_present": False,
    }


def _dryad_field(
    plants: Sequence[Mapping[str, str]], flower: Sequence[Mapping[str, str]]
) -> dict[str, Any]:
    """Count unique plant positions and repeated columns separately from plants."""
    if not flower or not plants:
        raise ValueError("empty Dryad field series")
    positions: Counter[tuple[str, str]] = Counter()
    statuses = [name for name in plants[0] if name.casefold().startswith("status.")]
    infections = [
        name for name in plants[0] if name.casefold().startswith("infect.status.")
    ]
    observed_statuses = 0
    for row in plants:
        _required(row, ("Row", "Position"), "Dryad raw field plants")
        positions[(row["Row"], row["Position"])] += 1
        observed_statuses += sum(bool(row[name].strip()) for name in statuses)
    dates = [row.get("Date", "") for row in flower]
    if not all(dates):
        raise ValueError("blank flower-summary date")
    return {
        "plant_rows": len(plants),
        "unique_row_position_pairs": len(positions),
        "reused_row_position_pairs": sum(n - 1 for n in positions.values()),
        "raw_status_date_columns": len(statuses),
        "infection_status_date_columns": len(infections),
        "populated_raw_status_cells": observed_statuses,
        "flower_summary_dates": len(set(dates)),
        "flower_summary_rows": len(flower),
        "field_is_longitudinal": True,
    }


def _dryad_weather(path: Path) -> dict[str, int]:
    """Check source weather rows without imputing missing or reversed values."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t", strict=True)
        if set(reader.fieldnames or ()) != {"Date", "High", "Low"}:
            raise ValueError("unexpected Dryad weather schema")
        rows = list(reader)
    missing = 0
    reversed_temperatures = 0
    for row in rows:
        date_raw = row.get("Date")
        high_raw = row.get("High")
        low_raw = row.get("Low")
        if not isinstance(date_raw, str) or not date_raw.strip():
            raise ValueError("missing Dryad weather date")
        if not isinstance(high_raw, str) or not isinstance(low_raw, str):
            raise ValueError("malformed Dryad weather row")
        if not high_raw.strip() or not low_raw.strip():
            missing += 1
            continue
        high = _number(high_raw, "High")
        low = _number(low_raw, "Low")
        reversed_temperatures += low > high
    return {
        "weather_rows": len(rows),
        "rows_with_missing_temperature": missing,
        "rows_with_low_above_high": reversed_temperatures,
    }


def audit_aphid_dryad(data_dir: Path) -> dict[str, Any]:
    """Audit both original studies after checking the full external manifest."""
    errors = verify_external_data(data_dir)
    if errors:
        raise ValueError("external source integrity failed: " + "; ".join(errors))
    root = data_dir / "external"
    aphid_tables = _read_workbook(root / _APHID / "Experiment.xlsx")
    if set(aphid_tables) != {*_APHID_FACTORS, "Experiment5"}:
        raise ValueError("unexpected aphid experiment sheets")
    aphid = {
        "doi": "10.5281/zenodo.19805135",
        "controlled": {
            name: _aphid_controlled(name, aphid_tables[name], factors)
            for name, factors in _APHID_FACTORS.items()
        },
        "field": _aphid_field(aphid_tables["Experiment5"]),
    }

    lab: dict[str, dict[str, Any]] = {}
    for filename, kind in _LAB_FILES.items():
        tables = _read_workbook(root / _DRYAD / filename)
        if len(tables) != 1:
            raise ValueError(f"unexpected Dryad assay worksheets: {filename}")
        lab[filename] = _dryad_lab(next(iter(tables.values())), kind, filename)

    infection_tables = _read_workbook(root / _DRYAD / "seedling_inoculation-_infection_data.xlsx")
    death_tables = _read_workbook(root / _DRYAD / "seedling_inoculation-_death_data.xlsx")
    field_tables = _read_workbook(root / _DRYAD / "Raw_field_data.xlsx")
    flower_tables = _read_workbook(root / _DRYAD / "flower_summary_data.xlsx")
    field_workbooks = (infection_tables, death_tables, field_tables, flower_tables)
    if any(len(tables) != 1 for tables in field_workbooks):
        raise ValueError("unexpected Dryad greenhouse or field worksheets")

    dryad = {
        "doi": "10.5061/dryad.4mw6m90jv",
        "laboratory": dict(sorted(lab.items())),
        "greenhouse": _dryad_greenhouse(
            next(iter(infection_tables.values())), next(iter(death_tables.values()))
        ),
        "field": _dryad_field(
            next(iter(field_tables.values())), next(iter(flower_tables.values()))
        ),
        "weather": _dryad_weather(root / _DRYAD / "daily_high_temps.txt"),
    }
    return {
        "schema_version": 1,
        "manifest_sha256": hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "aphid": aphid,
        "dryad": dryad,
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Generate or check the stable observational-unit report, without source edits."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/external_aphid_dryad_units.json")
    )
    parser.add_argument("--check", action="store_true", help="Check saved report without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = json.dumps(audit_aphid_dryad(args.data_dir), indent=2) + "\n"
    except (ValueError, KeyError, OSError, ET.ParseError, BadZipFile, csv.Error) as exc:
        parser.exit(1, f"experimental-unit audit failed: {exc}\n")
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != report:
            parser.exit(1, f"experimental-unit audit missing or stale: {args.output}\n")
        print(f"experimental-unit audit matches source: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"wrote experimental-unit audit: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
