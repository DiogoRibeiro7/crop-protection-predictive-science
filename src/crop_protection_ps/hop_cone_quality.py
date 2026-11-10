"""Link source-pinned hop cone infection and quality at field-plot level.

Gent et al. (2025) released distinct late-season Mildew and Cascade tables.
The join is by year, block and fungicide-ending strategy, never by plant.
Quality is observed in 2018–2022, while infection is absent in 2021 and
incomplete in many 2018–2019 plots. This module preserves that distinction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from crop_protection_ps.hop_powdery_field import BLOCKS, SOURCE_REPOSITORY

MILDEW_SHA256 = "2e26ce77ea392fee7e177b3b8f05a1411ebdde204af2c8d3da91758a272b5f75"
CASCADE_SHA256 = "d8dbca537d19cd1c6894a442c0b7e9f1eecb74d2ee1c2ba8b0971c3892de0be4"
MILDEW_GIT_BLOB = "bba8fffb6bfc77d57040ef568d50d5f4cde8e432"
CASCADE_GIT_BLOB = "aaa91ec59ec21b36d16289b79f165d51e813421b"
MILDEW_COLUMNS = ("YEAR", "DATE", "SU", "REP", "TRT", "PLANT", "PM")
CASCADE_COLUMNS = (
    "Year",
    "Date",
    "Field",
    "Block",
    "Treatment",
    "Dry_Matter",
    "A_acid",
    "B_acid",
    "_HSI",
    "Color",
)
TREATMENTS = {
    1: "cease_at_bloom",
    2: "bloom_plus_one",
    3: "bloom_plus_two",
    4: "bloom_plus_three",
}
METRICS = (
    "dry_matter_percent",
    "alpha_acids_percent",
    "beta_acids_percent",
    "hsi",
    "cone_color",
)
LINK_COLUMNS = (
    "year", "farm", "block", "treatment", "ending_strategy", "quality_date",
    "mildew_date", "mildew_vs_quality_date_offset_days", "mildew_status",
    "mildew_plants_observed", "mildew_incidence_percent", *METRICS,
)
PAIRED_COLUMNS = (
    "year", "farm", "block", "additional_after_bloom", "ending_strategy",
    "mildew_pair_status", "mildew_delta_percentage_points",
    *(f"delta_{metric}" for metric in METRICS),
)
YEAR_COLUMNS = (
    "year", "farm", "additional_after_bloom", "ending_strategy", "paired_quality_blocks",
    "paired_complete_mildew_blocks", "mean_mildew_delta_percentage_points",
    *(f"mean_delta_{metric}" for metric in METRICS),
)
INFLUENCE_COLUMNS = (
    "year", "farm", "additional_after_bloom", "ending_strategy", "metric",
    "omitted_block", "all_block_mean_delta", "without_block_mean_delta",
    "full_minus_without", "absolute_influence",
)


@dataclass(frozen=True)
class ConeObservation:
    """An original plant assessment among ten cones on that plant."""

    year: int
    assessment: date
    block: str
    treatment: int
    plant: int
    diseased_cones: int | None


@dataclass(frozen=True)
class ConeQuality:
    """An original plot-level harvest quality record."""

    year: int
    harvest: date
    farm: str
    block: str
    treatment: int
    metrics: dict[str, float]


@dataclass(frozen=True)
class ConeQualityAnalysis:
    """Verified, source-aligned derived evidence tables and study caveats."""

    linked_plots: list[dict[str, Any]]
    paired_blocks: list[dict[str, Any]]
    year_comparisons: list[dict[str, Any]]
    block_influence: list[dict[str, Any]]
    summary: dict[str, Any]


def _strict_int(value: str, field: str, lower: int, upper: int) -> int:
    """Validate numeric identifiers and source-scale response counts."""
    if not value.isascii() or not value.isdecimal():
        raise ValueError(f"{field} must be a decimal integer: {value!r}")
    number = int(value)
    if not lower <= number <= upper:
        raise ValueError(f"{field} outside {lower}..{upper}: {value!r}")
    return number


def _finite_float(value: str, field: str, lower: float, upper: float) -> float:
    """Accept the original extreme observations, but reject invalid values."""
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{field} is not numeric: {value!r}") from exc
    if not math.isfinite(number) or not lower <= number <= upper:
        raise ValueError(f"{field} is not a finite in-range value: {value!r}")
    return number


def _date(value: str, year: int, field: str) -> date:
    try:
        result = datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if result.year != year:
        raise ValueError(f"{field} year does not match trial year")
    return result


def _source_rows(
    path: Path, columns: tuple[str, ...], expected_sha: str, *, verify_source: bool
) -> tuple[list[dict[str, str]], str]:
    """Read a canonical-newline source and validate its published identity."""
    canonical = path.read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha256(canonical).hexdigest()
    if verify_source and digest != expected_sha:
        raise ValueError(f"{path.name} source checksum mismatch: {digest}")
    reader = csv.DictReader(io.StringIO(canonical.decode("utf-8-sig")))
    if tuple(reader.fieldnames or ()) != columns:
        raise ValueError(f"{path.name} source schema differs from the original")
    rows: list[dict[str, str]] = []
    for row in reader:
        if None in row or any(value is None or not value.strip() for value in row.values()):
            raise ValueError(f"{path.name} contains an empty or malformed source record")
        rows.append(row)
    if not rows:
        raise ValueError(f"{path.name} contains no source observations")
    return rows, digest


def _mildew_rows(path: Path, *, verify_source: bool) -> tuple[list[ConeObservation], str]:
    raw, digest = _source_rows(path, MILDEW_COLUMNS, MILDEW_SHA256, verify_source=verify_source)
    observations: list[ConeObservation] = []
    unique: set[tuple[int, str, int, int]] = set()
    for row in raw:
        year = _strict_int(row["YEAR"], "YEAR", 2000, 2100)
        if row["SU"] != "Cone":
            raise ValueError("Mildew.csv SU must be Cone")
        block = row["REP"]
        if block not in BLOCKS:
            raise ValueError(f"invalid mildew block: {block!r}")
        treatment = _strict_int(row["TRT"], "TRT", 1, 4)
        plant = _strict_int(row["PLANT"], "PLANT", 1, 10)
        assessment = _date(row["DATE"], year, "DATE")
        key = (year, block, treatment, plant)
        if key in unique:
            raise ValueError("duplicate year-block-treatment-plant cone observation")
        unique.add(key)
        disease = (
            None
            if row["PM"] == "."
            else _strict_int(row["PM"], "PM", 0, 10)
        )
        observations.append(ConeObservation(year, assessment, block, treatment, plant, disease))
    return observations, digest


def _quality_rows(path: Path, *, verify_source: bool) -> tuple[list[ConeQuality], str]:
    raw, digest = _source_rows(
        path, CASCADE_COLUMNS, CASCADE_SHA256, verify_source=verify_source
    )
    qualities: list[ConeQuality] = []
    seen: set[tuple[int, str, int]] = set()
    for row in raw:
        year = _strict_int(row["Year"], "Year", 2000, 2100)
        block = row["Block"]
        if block not in BLOCKS:
            raise ValueError(f"invalid quality block: {block!r}")
        treatment = _strict_int(row["Treatment"], "Treatment", 1, 4)
        farm = row["Field"]
        if not farm:
            raise ValueError("Field must identify a source farm")
        key = (year, block, treatment)
        if key in seen:
            raise ValueError("duplicate year-block-treatment quality plot")
        seen.add(key)
        metrics = {
            "dry_matter_percent": _finite_float(row["Dry_Matter"], "Dry_Matter", 0, 100),
            "alpha_acids_percent": _finite_float(row["A_acid"], "A_acid", 0, 100),
            "beta_acids_percent": _finite_float(row["B_acid"], "B_acid", 0, 100),
            "hsi": _finite_float(row["_HSI"], "_HSI", 0, 1),
            "cone_color": float(_strict_int(row["Color"], "Color", 1, 10)),
        }
        qualities.append(
            ConeQuality(year, _date(row["Date"], year, "Date"), farm, block, treatment, metrics)
        )
    return qualities, digest


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 10) if values else None


def analyse_late_season_cones(
    mildew: list[ConeObservation],
    qualities: list[ConeQuality],
    *,
    mildew_sha: str,
    cascade_sha: str,
) -> ConeQualityAnalysis:
    """Join only uniquely identified field plots; never impute disease status."""
    infected: dict[tuple[int, str, int], list[ConeObservation]] = defaultdict(list)
    for row in mildew:
        infected[(row.year, row.block, row.treatment)].append(row)
    mildew_plots: dict[tuple[int, str, int], dict[str, Any]] = {}
    for key, rows in infected.items():
        if len(rows) != 10 or {r.plant for r in rows} != set(range(1, 11)):
            raise ValueError("each mildew plot must contain exactly ten plant slots")
        dates = {r.assessment for r in rows}
        if len(dates) != 1:
            raise ValueError("mildew plot contains inconsistent harvest dates")
        observed = [r.diseased_cones for r in rows if r.diseased_cones is not None]
        count = len(observed)
        mildew_plots[key] = {
            "date": next(iter(dates)),
            "observed": count,
            "status": "complete" if count == 10 else "incomplete",
            "incidence_percent": round(float(sum(observed)), 10) if count == 10 else None,
        }
        # Each original PM is the number infected among ten assessed cones.
        # Ten complete plants therefore represent a 100-cone plot denominator.

    quality_lookup = {(r.year, r.block, r.treatment): r for r in qualities}
    if len(quality_lookup) != len(qualities):
        raise ValueError("quality plot identifiers must be unique")
    years = sorted({r.year for r in qualities})
    for year in years:
        farms = {r.farm for r in qualities if r.year == year}
        if len(farms) != 1:
            raise ValueError("mildew lacks a field ID; multiple farms make the join ambiguous")
        for block in {r.block for r in qualities if r.year == year}:
            if {t for t in TREATMENTS if (year, block, t) in quality_lookup} != set(TREATMENTS):
                raise ValueError("each quality year-block must represent all four treatments")
    if not set(mildew_plots).issubset(quality_lookup):
        raise ValueError("mildew plots have no uniquely matching quality record")

    linked: list[dict[str, Any]] = []
    for key, record in sorted(quality_lookup.items()):
        source = mildew_plots.get(key)
        linked.append(
            {
                "year": record.year,
                "farm": record.farm,
                "block": record.block,
                "treatment": record.treatment,
                "ending_strategy": TREATMENTS[record.treatment],
                "quality_date": record.harvest.isoformat(),
                "mildew_date": source["date"].isoformat() if source else None,
                "mildew_vs_quality_date_offset_days": (
                    (source["date"] - record.harvest).days if source else None
                ),
                "mildew_status": source["status"] if source else "not_in_source",
                "mildew_plants_observed": source["observed"] if source else None,
                "mildew_incidence_percent": source["incidence_percent"] if source else None,
                **record.metrics,
            }
        )
    plot_lookup = {(r["year"], r["block"], r["treatment"]): r for r in linked}
    pairs: list[dict[str, Any]] = []
    for year in years:
        blocks = sorted({r.block for r in qualities if r.year == year}, key=BLOCKS.index)
        for block in blocks:
            baseline = plot_lookup[(year, block, 1)]
            for treatment in (2, 3, 4):
                treated = plot_lookup[(year, block, treatment)]
                complete = (
                    baseline["mildew_status"] == treated["mildew_status"] == "complete"
                )
                pairs.append(
                    {
                        "year": year,
                        "farm": baseline["farm"],
                        "block": block,
                        "additional_after_bloom": treatment - 1,
                        "ending_strategy": TREATMENTS[treatment],
                        "mildew_pair_status": (
                            "complete"
                            if complete
                            else (
                                "not_in_source"
                                if baseline["mildew_status"] == "not_in_source"
                                else "incomplete"
                            )
                        ),
                        "mildew_delta_percentage_points": (
                            round(
                                float(
                                    treated["mildew_incidence_percent"]
                                    - baseline["mildew_incidence_percent"]
                                ),
                                10,
                            )
                            if complete
                            else None
                        ),
                        **{
                            f"delta_{metric}": round(
                                float(treated[metric] - baseline[metric]), 10
                            )
                            for metric in METRICS
                        },
                    }
                )
    summaries: list[dict[str, Any]] = []
    influence: list[dict[str, Any]] = []
    for year in years:
        for treatment in (2, 3, 4):
            selected = [
                p
                for p in pairs
                if p["year"] == year and p["additional_after_bloom"] == treatment - 1
            ]
            disease = [
                float(p["mildew_delta_percentage_points"])
                for p in selected
                if p["mildew_pair_status"] == "complete"
            ]
            summaries.append(
                {
                    "year": year,
                    "farm": selected[0]["farm"],
                    "additional_after_bloom": treatment - 1,
                    "ending_strategy": TREATMENTS[treatment],
                    "paired_quality_blocks": len(selected),
                    "paired_complete_mildew_blocks": len(disease),
                    "mean_mildew_delta_percentage_points": _mean(disease),
                    **{
                        f"mean_delta_{metric}": _mean(
                            [float(p[f"delta_{metric}"]) for p in selected]
                        )
                        for metric in METRICS
                    },
                }
            )
            for metric in METRICS:
                values = [float(p[f"delta_{metric}"]) for p in selected]
                full = _mean(values)
                if full is None:
                    continue
                for idx, pair in enumerate(selected):
                    leave_out = _mean(values[:idx] + values[idx + 1 :])
                    if leave_out is None:
                        continue
                    effect = round(full - leave_out, 10)
                    influence.append(
                        {
                            "year": year,
                            "farm": pair["farm"],
                            "additional_after_bloom": treatment - 1,
                            "ending_strategy": TREATMENTS[treatment],
                            "metric": metric,
                            "omitted_block": pair["block"],
                            "all_block_mean_delta": full,
                            "without_block_mean_delta": leave_out,
                            "full_minus_without": effect,
                            "absolute_influence": round(abs(effect), 10),
                        }
                    )

    # The five quality metrics have different units and cannot be ranked by
    # a common numerical influence magnitude.
    largest_by_metric = {
        metric: max(
            (row for row in influence if row["metric"] == metric),
            key=lambda row: row["absolute_influence"],
        )
        for metric in METRICS
    }
    alphas = sorted(
        (r.metrics["alpha_acids_percent"], r.year, r.block, r.treatment)
        for r in qualities
    )
    source_years = sorted({r.year for r in mildew})
    summary: dict[str, Any] = {
        "study": "Gent et al. (2025) late-season hop cone disease and quality",
        "doi": "10.1094/PHYTOFR-10-24-0117-R",
        "source_repository": SOURCE_REPOSITORY,
        "source_mildew_git_blob": MILDEW_GIT_BLOB,
        "source_cascade_git_blob": CASCADE_GIT_BLOB,
        "mildew_canonical_sha256": mildew_sha,
        "cascade_canonical_sha256": cascade_sha,
        "mildew_plant_rows": len(mildew),
        "mildew_source_years": source_years,
        "quality_plot_rows": len(qualities),
        "quality_source_years": years,
        "quality_only_years": sorted(set(years) - set(source_years)),
        "mildew_missing_plant_rows": sum(r.diseased_cones is None for r in mildew),
        "mildew_complete_plots": sum(r["mildew_status"] == "complete" for r in linked),
        "mildew_incomplete_plots": sum(r["mildew_status"] == "incomplete" for r in linked),
        "quality_only_plots": sum(r["mildew_status"] == "not_in_source" for r in linked),
        "paired_quality_block_comparisons": len(pairs),
        "paired_complete_mildew_block_comparisons": sum(
            p["mildew_pair_status"] == "complete" for p in pairs
        ),
        "alpha_acid_largest_original_value": {
            "value_percent": alphas[-1][0],
            "year": alphas[-1][1],
            "block": alphas[-1][2],
            "treatment": alphas[-1][3],
            "next_largest_percent": alphas[-2][0],
        },
        "largest_block_influence_by_metric": largest_by_metric,
        "contrast_direction": "bloom-plus-N minus cease-at-bloom within same year and block",
        "scientific_limits": [
            "Years are distinct environments, but Farm3 is reused across 2020-2022.",
            "2021 has quality data and no Mildew.csv source rows; missing is not zero infection.",
            "Mildew.csv has no farm label; joining requires one Cascade farm per year.",
            "Mildew and quality dates can differ; the offset is recorded, not harmonised.",
            "All treatments received fungicide; there is no untreated comparison or cost evidence.",
            "Plant subsamples do not increase the seven field-block replicates per year.",
            "Source-provided extreme alpha acid value is retained, with full block influence.",
            "This is descriptive, not a predictive model or treatment recommendation.",
        ],
    }
    return ConeQualityAnalysis(linked, pairs, summaries, influence, summary)


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_late_season_cones(result: ConeQualityAnalysis, output_dir: Path) -> None:
    """Persist all primary and sensitivity tables deterministically."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "linked_plots.csv", LINK_COLUMNS, result.linked_plots)
    _write_csv(output_dir / "paired_blocks.csv", PAIRED_COLUMNS, result.paired_blocks)
    _write_csv(output_dir / "year_comparisons.csv", YEAR_COLUMNS, result.year_comparisons)
    _write_csv(output_dir / "block_influence.csv", INFLUENCE_COLUMNS, result.block_influence)
    (output_dir / "summary.json").write_text(
        json.dumps(result.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def run_late_season_cones(
    mildew_path: Path, cascade_path: Path, output_dir: Path, *, verify_source: bool = True
) -> ConeQualityAnalysis:
    """Reproduce a sourced plot link without copying the original CSV files."""
    mildew, mildew_sha = _mildew_rows(mildew_path, verify_source=verify_source)
    quality, cascade_sha = _quality_rows(cascade_path, verify_source=verify_source)
    result = analyse_late_season_cones(
        mildew, quality, mildew_sha=mildew_sha, cascade_sha=cascade_sha
    )
    write_late_season_cones(result, output_dir)
    return result


def main() -> None:
    """Analyze original, checksum-pinned late-season data from the authors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mildew", type=Path, required=True, help="Original Mildew.csv")
    parser.add_argument("--cascade", type=Path, required=True, help="Original Cascade.csv")
    parser.add_argument("--output", type=Path, required=True, help="Derived output directory")
    args = parser.parse_args()
    result = run_late_season_cones(args.mildew, args.cascade, args.output)
    print(json.dumps(result.summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
