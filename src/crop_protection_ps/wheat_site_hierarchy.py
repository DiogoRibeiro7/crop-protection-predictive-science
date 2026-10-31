"""Describe wheat TrialId nesting within published, coarsened geocodes.

Matching coordinates do not prove that two trials share a physical location,
experimental plot, randomization unit, or trial protocol. This module only
counts identifier collisions at the recorded 0.1-degree spatial resolution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from crop_protection_ps.external_data import verify_external_data
from crop_protection_ps.wheat_pairability import _read_wheat_rows

_SOURCE_PATH = "zenodo_wheat_fungicide_6521175/basf-wheat-diseases.txt"
_SOURCE_DOI = "10.5281/zenodo.6521175"
_SPATIAL_STEP = Decimal("0.1")
_FIELDS = ("TrialId", "Country", "Latitude", "Longitude", "Date")


def _coordinate(raw: str, field: str, lower: int, upper: int) -> str:
    """Validate published coordinate precision without rounding it again."""
    try:
        value = Decimal(raw)
        if (
            not value.is_finite()
            or value < lower
            or value > upper
            or value != value.quantize(_SPATIAL_STEP)
        ):
            raise ValueError(f"invalid or finer-than-0.1-degree {field}: {raw!r}")
    except InvalidOperation as exc:
        raise ValueError(f"invalid {field}: {raw!r}") from exc
    return f"{value:.1f}"


def _trial_sort(code: str) -> tuple[int, str]:
    """Sort numeric trial labels deterministically without changing the labels."""
    return int(code), code


def _site_sort(site: tuple[str, str, str]) -> tuple[str, Decimal, Decimal]:
    """Sort recorded locations numerically within countries."""
    return site[0], Decimal(site[1]), Decimal(site[2])


def audit_wheat_site_rows(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    """Report geocode/year aliases without inferring physical trial identity.

    An ID must have one country, one coordinate pair and one observation year.
    Co-occurrence at the same geocode/year is *not* evidence of replication.
    """
    if not rows:
        raise ValueError("no wheat field observations")

    trial_to_siteyear: dict[str, tuple[str, str, str, int]] = {}
    siteyear_to_trials: dict[tuple[str, str, str, int], set[str]] = defaultdict(set)
    site_to_year_trials: dict[tuple[str, str, str], dict[int, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for row_number, row in enumerate(rows, start=2):
        if any(field not in row or not isinstance(row[field], str) for field in _FIELDS):
            raise ValueError(f"missing site metadata on source line {row_number}")
        trial = row["TrialId"]
        country = row["Country"]
        if not re.fullmatch(r"[0-9]+", trial) or not country.strip():
            raise ValueError(f"invalid TrialId or country on source line {row_number}")
        try:
            year = date.fromisoformat(row["Date"]).year
        except ValueError as exc:
            raise ValueError(f"invalid observation date on source line {row_number}") from exc
        latitude = _coordinate(row["Latitude"], "Latitude", -90, 90)
        longitude = _coordinate(row["Longitude"], "Longitude", -180, 180)
        location_year = (country, latitude, longitude, year)
        if trial in trial_to_siteyear and trial_to_siteyear[trial] != location_year:
            raise ValueError(f"TrialId {trial} is reused across geocodes or years")
        trial_to_siteyear[trial] = location_year
        siteyear_to_trials[location_year].add(trial)
        site_to_year_trials[location_year[:3]][year].add(trial)

    site_rows: list[dict[str, Any]] = []
    shared_siteyears: list[dict[str, Any]] = []
    reused_geocodes: list[dict[str, Any]] = []
    for site in sorted(site_to_year_trials, key=_site_sort):
        country, latitude, longitude = site
        by_year = site_to_year_trials[site]
        years: list[dict[str, Any]] = []
        for year in sorted(by_year):
            trial_ids = sorted(by_year[year], key=_trial_sort)
            years.append({"year": year, "trial_ids": trial_ids})
            if len(trial_ids) > 1:
                shared_siteyears.append(
                    {
                        "country": country,
                        "latitude": latitude,
                        "longitude": longitude,
                        "year": year,
                        "trial_ids": trial_ids,
                    }
                )
        description: dict[str, Any] = {
            "country": country,
            "latitude": latitude,
            "longitude": longitude,
            "trial_ids_by_year": years,
        }
        site_rows.append(description)
        if len(by_year) > 1:
            reused_geocodes.append(description)

    country_ids: dict[str, set[str]] = defaultdict(set)
    country_geocodes: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    country_siteyears: dict[str, set[tuple[str, str, str, int]]] = defaultdict(set)
    for trial, siteyear in trial_to_siteyear.items():
        country_ids[siteyear[0]].add(trial)
        country_geocodes[siteyear[0]].add(siteyear[:3])
        country_siteyears[siteyear[0]].add(siteyear)

    multiplicity = Counter(len(trials) for trials in siteyear_to_trials.values())
    years_per_site = Counter(len(years) for years in site_to_year_trials.values())
    return {
        "schema_version": 1,
        "source_rows": len(rows),
        "trial_id_count": len(trial_to_siteyear),
        "geocode_count": len(site_to_year_trials),
        "geocode_year_count": len(siteyear_to_trials),
        "geocode_precision_degrees": str(_SPATIAL_STEP),
        "geocode_year_trial_multiplicity": {
            str(size): count for size, count in sorted(multiplicity.items())
        },
        "geocode_years_per_geocode": {
            str(size): count for size, count in sorted(years_per_site.items())
        },
        "geocode_years_with_multiple_trial_ids": len(shared_siteyears),
        "trial_ids_at_shared_geocode_years": sum(
            len(item["trial_ids"]) for item in shared_siteyears
        ),
        "geocodes_reused_across_years": len(reused_geocodes),
        "country_summary": [
            {
                "country": country,
                "trial_ids": len(country_ids[country]),
                "geocodes": len(country_geocodes[country]),
                "geocode_years": len(country_siteyears[country]),
            }
            for country in sorted(country_ids)
        ],
        "shared_geocode_years": shared_siteyears,
        "reused_geocodes": reused_geocodes,
        "all_geocodes": site_rows,
    }


def audit_wheat_site_data(data_dir: Path) -> dict[str, Any]:
    """Verify vendor snapshots before examining geographic trial-ID nesting."""
    problems = verify_external_data(data_dir)
    if problems:
        raise ValueError("external source integrity failed: " + "; ".join(problems))
    source = data_dir / "external" / _SOURCE_PATH
    return {
        "source_doi": _SOURCE_DOI,
        "source_path": _SOURCE_PATH,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        **audit_wheat_site_rows(_read_wheat_rows(source)),
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Regenerate/check the evidence report offline, without changing source data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/external_wheat_site_hierarchy.json")
    )
    parser.add_argument("--check", action="store_true", help="Check the saved report, no writes")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        content = json.dumps(audit_wheat_site_data(args.data_dir), indent=2) + "\n"
    except (ValueError, OSError) as exc:
        parser.exit(1, f"wheat geocode audit failed: {exc}\n")
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != content:
            parser.exit(1, f"wheat geocode audit missing or stale: {args.output}\n")
        print(f"wheat geocode audit matches source: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"wrote wheat geocode audit: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
