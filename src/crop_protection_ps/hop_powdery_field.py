"""Source-pinned, design-preserving audit of Gent et al. (2025) field validation.

The original data have repeated leaf assessments within field plots. This
module retains the year/site/replicate/treatment plot as the experimental unit;
plants and repeated assessment dates are subsamples, not replicates.

This is a descriptive re-analysis of four fungicide scheduling strategies,
not a new predictive-model search or a comparison against no fungicide.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

SOURCE_REPOSITORY = (
    "https://github.com/DavidGent-Lab/"
    "Gent-et-al-2025-A-Modified-Disease-Risk-Index-for-Hop-Powdery-Mildew-PhytoFrontiers-"
)
SOURCE_FILE_URL = f"{SOURCE_REPOSITORY}/raw/refs/heads/main/Interval.csv"
SOURCE_GIT_BLOB_SHA = "f88b19a34592ab23990bae4509eacdeb2876761e"
# The checksum applies to original UTF-8 text after CRLF -> LF normalization.
SOURCE_CANONICAL_SHA256 = "55feee5674bede0357a8eb404a149f10cf3dc9db4845783f800a52315688eb3b"
SOURCE_DOI = "10.1094/PHYTOFR-10-24-0117-R"
SOURCE_COLUMNS = ("YEAR", "Site", "DATE", "SU", "REP", "TRT", "PLANT", "PM")
BLOCKS = ("I", "II", "III", "IV", "V", "VI", "VII")
TREATMENTS = {1: "10-day", 2: "14-day", 3: "21-day", 4: "risk-index"}
PLOT_OUTPUT_COLUMNS = (
    "year",
    "site",
    "date",
    "block",
    "treatment",
    "strategy",
    "plants_recorded",
    "plants_observed",
    "leaves_observed",
    "missing_plants",
    "plot_integrity",
    "incidence_percent",
)
PAIR_OUTPUT_COLUMNS = (
    "year",
    "site",
    "block",
    "fixed_treatment",
    "fixed_strategy",
    "risk_index_incidence_percent",
    "fixed_incidence_percent",
    "risk_minus_fixed_percentage_points",
)
ENV_OUTPUT_COLUMNS = (
    "year",
    "site",
    "assessment_dates",
    "last_assessment",
    "plant_rows",
    "missing_plant_outcomes",
    "end_season_plots",
    "complete_end_season_plots",
    "end_season_mean_incidence_percent",
)
CONTRAST_OUTPUT_COLUMNS = (
    "year",
    "site",
    "fixed_treatment",
    "fixed_strategy",
    "paired_blocks",
    "mean_risk_minus_fixed_percentage_points",
)


@dataclass(frozen=True)
class LeafObservation:
    """One source plant assessment: up to ten examined leaves per plant."""

    year: int
    site: str
    assessment: date
    block: str
    treatment: int
    plant: int
    diseased_leaves: int | None


@dataclass(frozen=True)
class SourceObservations:
    """Validated source observations and explicit file-level provenance."""

    rows: tuple[LeafObservation, ...]
    canonical_sha256: str
    empty_source_rows: int
    duplicated_plant_identifiers: int


@dataclass(frozen=True)
class FieldIntervalAnalysis:
    """Ready-to-export tables and structured study-design audit."""

    plot_visits: list[dict[str, Any]]
    end_season_plots: list[dict[str, Any]]
    paired_comparisons: list[dict[str, Any]]
    environments: list[dict[str, Any]]
    environment_contrasts: list[dict[str, Any]]
    summary: dict[str, Any]


def _integer(value: str, label: str, *, minimum: int, maximum: int) -> int:
    """Reject decimal, non-numeric and out-of-range original identifiers."""
    if not value.isdecimal():
        raise ValueError(f"{label} must be a whole number: {value!r}")
    parsed = int(value)
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{label} outside {minimum}..{maximum}: {parsed}")
    return parsed


def _parse_row(row: dict[str, str]) -> LeafObservation:
    year = _integer(row["YEAR"], "YEAR", minimum=2000, maximum=2100)
    site = row["Site"].strip()
    if site not in {"Toppenish", "Prosser"}:
        raise ValueError(f"unexpected trial site: {site!r}")
    try:
        assessment = datetime.strptime(row["DATE"], "%m/%d/%Y").date()
    except ValueError as exc:
        raise ValueError(f"invalid assessment DATE: {row['DATE']!r}") from exc
    if assessment.year != year:
        raise ValueError("DATE and YEAR must identify the same trial year")
    if row["SU"] != "Leaf":
        raise ValueError("only the original Leaf sampling unit is supported")
    block = row["REP"].strip()
    if block not in BLOCKS:
        raise ValueError(f"unexpected field replicate block: {block!r}")
    treatment = _integer(row["TRT"], "TRT", minimum=1, maximum=4)
    plant = _integer(row["PLANT"], "PLANT", minimum=1, maximum=10)
    # A literal period is missing, not zero disease and not an absent plant.
    pm = (
        None
        if row["PM"] == "."
        else _integer(row["PM"], "PM", minimum=0, maximum=10)
    )
    return LeafObservation(year, site, assessment, block, treatment, plant, pm)


def load_gent_interval_csv(path: Path, *, verify_source: bool = True) -> SourceObservations:
    """Parse source CSV, optionally requiring the pinned original content hash.

    A source-provided all-empty CSV record is counted and excluded. Any partial
    empty record or malformed observation fails closed. Header and plot-level
    identification collisions are retained for a subsequent plot-level audit.
    """
    canonical_bytes = path.read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha256(canonical_bytes).hexdigest()
    if verify_source and digest != SOURCE_CANONICAL_SHA256:
        raise ValueError(
            f"source checksum mismatch: expected {SOURCE_CANONICAL_SHA256}, got {digest}"
        )
    reader = csv.DictReader(io.StringIO(canonical_bytes.decode("utf-8-sig")))
    if tuple(reader.fieldnames or ()) != SOURCE_COLUMNS:
        raise ValueError("original Interval.csv column names or order changed")
    observations: list[LeafObservation] = []
    empty_rows = 0
    duplicate_keys = 0
    seen: set[tuple[int, str, date, str, int, int]] = set()
    for source_row in reader:
        if None in source_row or any(value is None for value in source_row.values()):
            raise ValueError("malformed source CSV row")
        if all(not value.strip() for value in source_row.values()):
            empty_rows += 1
            continue
        if any(not value.strip() for value in source_row.values()):
            raise ValueError("partially empty source CSV row")
        record = _parse_row(source_row)
        key = (
            record.year,
            record.site,
            record.assessment,
            record.block,
            record.treatment,
            record.plant,
        )
        if key in seen:
            # The published 2020 Prosser file repeats plant 2 in one visit.
            # Do not silently relabel it as plant 1 or count it as replication.
            duplicate_keys += 1
        seen.add(key)
        observations.append(record)
    if not observations:
        raise ValueError("source CSV contains no measured plant records")
    return SourceObservations(tuple(observations), digest, empty_rows, duplicate_keys)


def _plot_visit(records: list[LeafObservation]) -> dict[str, Any]:
    """Aggregate the ten plant subsamples within one field-plot visit."""
    first = records[0]
    plants = {record.plant for record in records}
    integrity = "ok" if len(records) == 10 and plants == set(range(1, 11)) else "invalid_plant_ids"
    measured = [record.diseased_leaves for record in records if record.diseased_leaves is not None]
    n_measured = len(measured)
    leaves = n_measured * 10
    return {
        "year": first.year,
        "site": first.site,
        "date": first.assessment.isoformat(),
        "block": first.block,
        "treatment": first.treatment,
        "strategy": TREATMENTS[first.treatment],
        "plants_recorded": len(records),
        "plants_observed": n_measured,
        "leaves_observed": leaves,
        "missing_plants": len(records) - n_measured,
        "plot_integrity": integrity,
        "incidence_percent": (
            round(100 * sum(measured) / leaves, 10)
            if leaves and integrity == "ok"
            else None
        ),
    }


def _mean(values: list[float]) -> float | None:
    """Use explicit missingness instead of NaN in serialized tables."""
    return round(sum(values) / len(values), 10) if values else None


def analyse_field_intervals(source: SourceObservations) -> FieldIntervalAnalysis:
    """Audit study coverage and matched block-level end-of-season contrasts.

    Every environment (year x site) is reported separately. Contrasts pair
    the risk-index schedule against each fixed fungicide schedule within the
    same year, location, and field block, using only complete plot visits.
    """
    visits: dict[tuple[int, str, date, str, int], list[LeafObservation]] = defaultdict(list)
    by_environment: dict[tuple[int, str], list[LeafObservation]] = defaultdict(list)
    for record in source.rows:
        visits[
            (record.year, record.site, record.assessment, record.block, record.treatment)
        ].append(record)
        by_environment[(record.year, record.site)].append(record)
    plot_visits = [_plot_visit(records) for _, records in sorted(visits.items())]
    latest_dates = {
        env: max(record.assessment for record in rows)
        for env, rows in by_environment.items()
    }
    final_plots = [
        row
        for row in plot_visits
        if row["date"] == latest_dates[(row["year"], row["site"])].isoformat()
    ]
    plot_lookup = {
        (row["year"], row["site"], row["block"], row["treatment"]): row
        for row in final_plots
    }
    pairs: list[dict[str, Any]] = []
    for year, site in sorted(by_environment):
        blocks = sorted(
            {row["block"] for row in final_plots if row["year"] == year and row["site"] == site},
            key=BLOCKS.index,
        )
        for block in blocks:
            risk = plot_lookup.get((year, site, block, 4))
            if risk is None or risk["plants_observed"] != 10 or risk["plot_integrity"] != "ok":
                continue
            for fixed in (1, 2, 3):
                comparator = plot_lookup.get((year, site, block, fixed))
                if (
                    comparator is None
                    or comparator["plants_observed"] != 10
                    or comparator["plot_integrity"] != "ok"
                ):
                    continue
                delta = float(risk["incidence_percent"] - comparator["incidence_percent"])
                pairs.append(
                    {
                        "year": year,
                        "site": site,
                        "block": block,
                        "fixed_treatment": fixed,
                        "fixed_strategy": TREATMENTS[fixed],
                        "risk_index_incidence_percent": risk["incidence_percent"],
                        "fixed_incidence_percent": comparator["incidence_percent"],
                        "risk_minus_fixed_percentage_points": round(delta, 10),
                    }
                )
    environments: list[dict[str, Any]] = []
    contrasts: list[dict[str, Any]] = []
    for year, site in sorted(by_environment):
        records = by_environment[(year, site)]
        plots = [row for row in final_plots if row["year"] == year and row["site"] == site]
        complete = [
            row for row in plots if row["plants_observed"] == 10 and row["plot_integrity"] == "ok"
        ]
        environments.append(
            {
                "year": year,
                "site": site,
                "assessment_dates": len({row.assessment for row in records}),
                "last_assessment": latest_dates[(year, site)].isoformat(),
                "plant_rows": len(records),
                "missing_plant_outcomes": sum(r.diseased_leaves is None for r in records),
                "end_season_plots": len(plots),
                "complete_end_season_plots": len(complete),
                "end_season_mean_incidence_percent": _mean(
                    [float(row["incidence_percent"]) for row in complete]
                ),
            }
        )
        for fixed in (1, 2, 3):
            deltas = [
                float(pair["risk_minus_fixed_percentage_points"])
                for pair in pairs
                if pair["year"] == year
                and pair["site"] == site
                and pair["fixed_treatment"] == fixed
            ]
            contrasts.append(
                {
                    "year": year,
                    "site": site,
                    "fixed_treatment": fixed,
                    "fixed_strategy": TREATMENTS[fixed],
                    "paired_blocks": len(deltas),
                    "mean_risk_minus_fixed_percentage_points": _mean(deltas),
                }
            )
    summary: dict[str, Any] = {
        "study": "Gent et al. (2025) hop powdery mildew field-validation intervals",
        "doi": SOURCE_DOI,
        "source_repository": SOURCE_REPOSITORY,
        "source_file": "Interval.csv",
        "source_git_blob_sha": SOURCE_GIT_BLOB_SHA,
        "source_canonical_sha256": source.canonical_sha256,
        "original_all_empty_csv_rows": source.empty_source_rows,
        "duplicate_plant_identifier_rows": source.duplicated_plant_identifiers,
        "plant_assessment_rows": len(source.rows),
        "missing_pm_plant_rows": sum(row.diseased_leaves is None for row in source.rows),
        "plot_visit_units": len(plot_visits),
        "plot_visits_with_invalid_plant_ids": sum(
            row["plot_integrity"] != "ok" for row in plot_visits
        ),
        "site_year_environments": len(by_environment),
        "end_season_plot_units": len(final_plots),
        "complete_end_season_plots": sum(
            row["plants_observed"] == 10 and row["plot_integrity"] == "ok"
            for row in final_plots
        ),
        "excluded_incomplete_end_season_plots": sum(
            row["plants_observed"] != 10 or row["plot_integrity"] != "ok"
            for row in final_plots
        ),
        "within_block_risk_vs_fixed_pairs": len(pairs),
        "primary_endpoint": "incidence percentage at each site-year's last leaf assessment",
        "experimental_unit": "site-year x replicate block x fungicide scheduling treatment",
        "pair_sign": "risk index minus fixed schedule, in percentage points",
        "design_cautions": [
            "No untreated control exists in Interval.csv: this is not efficacy versus no spray.",
            "Repeated plants and dates are subsamples, not independent field replicates.",
            "Missing PM values are not zeros; only complete plot visits enter paired contrasts.",
            "A repeated plant ID invalidates one early visit; no replacement ID is invented.",
            "Site-year descriptives do not establish causal superiority or select new models.",
            "Spray counts, pesticide identity and application costs are absent from this file.",
        ],
    }
    return FieldIntervalAnalysis(plot_visits, final_plots, pairs, environments, contrasts, summary)


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    """Write deterministically ordered, schema-stable CSV evidence."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_field_interval_analysis(analysis: FieldIntervalAnalysis, output_dir: Path) -> None:
    """Export already-validated study evidence with stable filenames and ordering."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "plot_visits.csv", PLOT_OUTPUT_COLUMNS, analysis.plot_visits)
    _write_csv(
        output_dir / "end_season_plots.csv", PLOT_OUTPUT_COLUMNS, analysis.end_season_plots
    )
    _write_csv(
        output_dir / "paired_risk_vs_fixed.csv", PAIR_OUTPUT_COLUMNS, analysis.paired_comparisons
    )
    _write_csv(output_dir / "environment_quality.csv", ENV_OUTPUT_COLUMNS, analysis.environments)
    _write_csv(
        output_dir / "environment_contrasts.csv",
        CONTRAST_OUTPUT_COLUMNS,
        analysis.environment_contrasts,
    )
    (output_dir / "summary.json").write_text(
        json.dumps(analysis.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_field_interval_analysis(input_path: Path, output_dir: Path) -> FieldIntervalAnalysis:
    """Verify upstream identity and persist reproducible descriptive results."""
    analysis = analyse_field_intervals(load_gent_interval_csv(input_path))
    write_field_interval_analysis(analysis, output_dir)
    return analysis


def main() -> None:
    """Offline, verified execution against a downloaded original Interval.csv."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, required=True, help="Unmodified upstream Interval.csv"
    )
    parser.add_argument("--output", type=Path, required=True, help="Directory for derived evidence")
    args = parser.parse_args()
    analysis = run_field_interval_analysis(args.input, args.output)
    print(json.dumps(analysis.summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
