"""Worst-case partial identification of missing hop cone-disease counts.

Each source plant records infections among ten assessed cones, or the literal
missing marker ``.``. Ten plant slots form a plot; missing plants can each
contribute anywhere from zero to ten diseased cones. These bounds make no
missing-at-random assumption and never replace a missing plant with zero.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crop_protection_ps.hop_cone_quality import (
    CASCADE_GIT_BLOB,
    MILDEW_GIT_BLOB,
    ConeObservation,
    ConeQualityAnalysis,
    ConeQualitySources,
    analyse_late_season_cones,
    load_late_season_cone_sources,
)

PLOT_COLUMNS = (
    "year", "farm", "block", "treatment", "ending_strategy", "mildew_source_status",
    "observed_plants", "missing_plants", "infected_observed_cones",
    "incidence_lower_percent", "incidence_upper_percent", "bound_width_percentage_points",
)
PAIR_COLUMNS = (
    "year", "farm", "block", "additional_after_bloom", "ending_strategy",
    "identification_status", "delta_lower_percentage_points", "delta_upper_percentage_points",
    "bound_width_percentage_points", "identified_direction",
)
YEAR_COLUMNS = (
    "year", "farm", "additional_after_bloom", "ending_strategy", "source_pairs",
    "point_identified_pairs", "partially_identified_pairs", "mean_lower_percentage_points",
    "mean_upper_percentage_points", "bound_width_percentage_points", "identified_direction",
)


@dataclass(frozen=True)
class DiseaseInterval:
    """Identified infection-rate range for a 100-cone source plot."""

    observed_plants: int
    missing_plants: int
    infected_observed_cones: int
    lower_percent: float
    upper_percent: float


@dataclass(frozen=True)
class ConeBoundsAnalysis:
    """Auditable plot, pair and annual worst-case bounds with provenance."""

    plot_bounds: list[dict[str, Any]]
    paired_bounds: list[dict[str, Any]]
    year_bounds: list[dict[str, Any]]
    summary: dict[str, Any]


def _direction(lower: float | None, upper: float | None) -> str:
    """Report an algebraic sign only when the entire interval identifies it."""
    if lower is None or upper is None:
        return "not_in_source"
    if lower > 0:
        return "positive"
    if upper < 0:
        return "negative"
    if lower == upper == 0:
        return "exact_zero"
    return "not_sign_identified"


def _mean(values: list[float]) -> float:
    """Average complete block bounds; callers enforce positive denominators."""
    if not values:
        raise ValueError("cannot average an empty identified sample")
    return round(sum(values) / len(values), 10)


def analyse_cone_disease_bounds(
    sources: ConeQualitySources, quality: ConeQualityAnalysis
) -> ConeBoundsAnalysis:
    """Bound prespecified paired contrasts without assumptions about missing PM.

    The quality audit has already checked years, farm attribution, ten plant
    slots per mildew plot and four treatments per quality block. The bounds
    are derived from those same source observations and experimental units.
    """
    groups: dict[tuple[int, str, int], list[ConeObservation]] = defaultdict(list)
    for row in sources.mildew:
        groups[(row.year, row.block, row.treatment)].append(row)

    intervals: dict[tuple[int, str, int], DiseaseInterval] = {}
    for key, plants in groups.items():
        # 10 cones per plant × 10 recorded plant slots = 100 cones per plot.
        if len(plants) != 10 or len({row.plant for row in plants}) != 10:
            raise ValueError("disease bounds require ten unique plant slots per plot")
        observed: list[int] = []
        for plant in plants:
            if plant.diseased_cones is not None:
                observed.append(plant.diseased_cones)
        if any(value < 0 or value > 10 for value in observed):
            raise ValueError("each observed plant has a 0..10 diseased-cone count")
        missing = 10 - len(observed)
        infected = sum(observed)
        intervals[key] = DiseaseInterval(
            observed_plants=len(observed),
            missing_plants=missing,
            infected_observed_cones=infected,
            lower_percent=float(infected),
            upper_percent=float(infected + 10 * missing),
        )

    plot_bounds: list[dict[str, Any]] = []
    plot_lookup: dict[tuple[int, str, int], dict[str, Any]] = {}
    for row in quality.linked_plots:
        key = (row["year"], row["block"], row["treatment"])
        interval = intervals.get(key)
        status = row["mildew_status"]
        if (interval is None) != (status == "not_in_source"):
            raise ValueError("mildew bounds and source coverage disagree")
        if interval is not None:
            if (interval.missing_plants == 0) != (status == "complete"):
                raise ValueError("missing-plant counts and source completeness disagree")
            if status == "complete" and (
                interval.lower_percent != row["mildew_incidence_percent"]
            ):
                raise ValueError("complete-plot incidence disagrees with source audit")
        plot = {
            "year": row["year"],
            "farm": row["farm"],
            "block": row["block"],
            "treatment": row["treatment"],
            "ending_strategy": row["ending_strategy"],
            "mildew_source_status": status,
            "observed_plants": interval.observed_plants if interval else None,
            "missing_plants": interval.missing_plants if interval else None,
            "infected_observed_cones": (
                interval.infected_observed_cones if interval else None
            ),
            "incidence_lower_percent": interval.lower_percent if interval else None,
            "incidence_upper_percent": interval.upper_percent if interval else None,
            "bound_width_percentage_points": (
                interval.upper_percent - interval.lower_percent if interval else None
            ),
        }
        plot_bounds.append(plot)
        plot_lookup[key] = plot
    if not set(intervals).issubset(plot_lookup):
        raise ValueError("the original mildew data contain plots without quality records")

    paired_bounds: list[dict[str, Any]] = []
    for original in quality.paired_blocks:
        year, block, extra = (
            original["year"], original["block"], original["additional_after_bloom"]
        )
        baseline = plot_lookup[(year, block, 1)]
        treated = plot_lookup[(year, block, extra + 1)]
        lower: float | None = None
        upper: float | None = None
        if (
            baseline["incidence_lower_percent"] is not None
            and treated["incidence_lower_percent"] is not None
        ):
            # Independent unknown missing outcomes attain their extrema at
            # opposite ends of the two plot-level intervals.
            lower = round(
                treated["incidence_lower_percent"]
                - baseline["incidence_upper_percent"],
                10,
            )
            upper = round(
                treated["incidence_upper_percent"]
                - baseline["incidence_lower_percent"],
                10,
            )
            if original["mildew_pair_status"] == "complete" and (
                lower != upper or lower != original["mildew_delta_percentage_points"]
            ):
                raise ValueError("point-identified contrast disagrees with source audit")
        status = (
            "not_in_source" if lower is None else
            "point_identified" if lower == upper else "partially_identified"
        )
        paired_bounds.append(
            {
                "year": year,
                "farm": original["farm"],
                "block": block,
                "additional_after_bloom": extra,
                "ending_strategy": original["ending_strategy"],
                "identification_status": status,
                "delta_lower_percentage_points": lower,
                "delta_upper_percentage_points": upper,
                "bound_width_percentage_points": (
                    round(upper - lower, 10) if lower is not None and upper is not None
                    else None
                ),
                "identified_direction": _direction(lower, upper),
            }
        )

    years: list[dict[str, Any]] = []
    for original in quality.year_comparisons:
        matching = [
            row for row in paired_bounds
            if row["year"] == original["year"]
            and row["additional_after_bloom"] == original["additional_after_bloom"]
        ]
        available = [
            row for row in matching if row["identification_status"] != "not_in_source"
        ]
        # Never publish a seven-block average as though an absent plot were
        # a missing-at-random sample from those that happened to be present.
        lower = (
            _mean([row["delta_lower_percentage_points"] for row in available])
            if available and len(available) == len(matching) else None
        )
        upper = (
            _mean([row["delta_upper_percentage_points"] for row in available])
            if available and len(available) == len(matching) else None
        )
        years.append(
            {
                "year": original["year"],
                "farm": original["farm"],
                "additional_after_bloom": original["additional_after_bloom"],
                "ending_strategy": original["ending_strategy"],
                "source_pairs": len(available),
                "point_identified_pairs": sum(
                    row["identification_status"] == "point_identified" for row in matching
                ),
                "partially_identified_pairs": sum(
                    row["identification_status"] == "partially_identified" for row in matching
                ),
                "mean_lower_percentage_points": lower,
                "mean_upper_percentage_points": upper,
                "bound_width_percentage_points": (
                    round(upper - lower, 10) if lower is not None and upper is not None
                    else None
                ),
                "identified_direction": _direction(lower, upper),
            }
        )

    summary: dict[str, Any] = {
        "source_mildew_canonical_sha256": sources.mildew_sha,
        "source_cascade_canonical_sha256": sources.cascade_sha,
        "source_mildew_git_blob": MILDEW_GIT_BLOB,
        "source_cascade_git_blob": CASCADE_GIT_BLOB,
        "observed_infected_cones": sum(
            row["infected_observed_cones"] or 0 for row in plot_bounds
        ),
        "missing_plant_assessments": sum(row["missing_plants"] or 0 for row in plot_bounds),
        "source_plots": len(intervals),
        "point_identified_plots": sum(
            row["mildew_source_status"] == "complete" for row in plot_bounds
        ),
        "partially_identified_plots": sum(
            row["mildew_source_status"] == "incomplete" for row in plot_bounds
        ),
        "plots_without_disease_source": sum(
            row["mildew_source_status"] == "not_in_source" for row in plot_bounds
        ),
        "paired_quality_comparisons": len(paired_bounds),
        "bounded_disease_pairs": sum(
            row["identification_status"] != "not_in_source" for row in paired_bounds
        ),
        "point_identified_disease_pairs": sum(
            row["identification_status"] == "point_identified" for row in paired_bounds
        ),
        "partially_identified_disease_pairs": sum(
            row["identification_status"] == "partially_identified" for row in paired_bounds
        ),
        "disease_pairs_without_source": sum(
            row["identification_status"] == "not_in_source" for row in paired_bounds
        ),
        "year_comparisons": len(years),
        "year_comparisons_with_full_source_coverage": sum(
            row["mean_lower_percentage_points"] is not None for row in years
        ),
        "year_comparisons_with_identified_sign": sum(
            row["identified_direction"] in ("positive", "negative") for row in years
        ),
        "identification_contract": [
            "Ten source plant slots per plot, each with ten cones at risk.",
            "Missing plant cone counts may independently range from zero to ten.",
            "No missing-at-random assumption, imputation or cross-year pooling.",
            "2021 disease is absent from the source, not a plot bound of zero.",
            "Block-paired and year-level intervals are deterministic worst-case bounds.",
            "Bounds are descriptive, not treatment-effect inference or efficacy recommendations.",
        ],
    }
    return ConeBoundsAnalysis(plot_bounds, paired_bounds, years, summary)


def write_cone_disease_bounds(result: ConeBoundsAnalysis, output_dir: Path) -> None:
    """Write the new sensitivity outputs without changing the prior evidence bundle."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, columns, rows in (
        ("plot_bounds.csv", PLOT_COLUMNS, result.plot_bounds),
        ("paired_bounds.csv", PAIR_COLUMNS, result.paired_bounds),
        ("year_bounds.csv", YEAR_COLUMNS, result.year_bounds),
    ):
        with (output_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    (output_dir / "summary.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_late_season_cone_bounds(
    mildew_path: Path, cascade_path: Path, output_dir: Path, *, verify_source: bool = True
) -> ConeBoundsAnalysis:
    """Validate original data and reproduce exact, no-imputation disease bounds."""
    sources = load_late_season_cone_sources(
        mildew_path, cascade_path, verify_source=verify_source
    )
    quality = analyse_late_season_cones(
        sources.mildew,
        sources.qualities,
        mildew_sha=sources.mildew_sha,
        cascade_sha=sources.cascade_sha,
    )
    result = analyse_cone_disease_bounds(sources, quality)
    write_cone_disease_bounds(result, output_dir)
    return result


def main() -> None:
    """Expose the deterministic missing-disease sensitivity as a local CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mildew", type=Path, required=True, help="Original Mildew.csv")
    parser.add_argument("--cascade", type=Path, required=True, help="Original Cascade.csv")
    parser.add_argument("--output", type=Path, required=True, help="Derived output directory")
    args = parser.parse_args()
    result = run_late_season_cone_bounds(args.mildew, args.cascade, args.output)
    print(json.dumps(result.summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
