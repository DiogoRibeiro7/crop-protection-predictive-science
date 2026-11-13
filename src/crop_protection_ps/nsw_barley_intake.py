"""Checksum-pinned, non-inferential intake for NSW barley Ramularia trials.

Requires ``openpyxl`` for local XLSX decoding. Original files are not bundled.
The audit never computes treatment effects or changes source observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SOURCE_SHA256: dict[str, str] = {
    "trials": "c5e09475329664a99ee9b1c4f3b5efe8030690a84c46632b064dcfc58047de05",
    "measurements": "b67fc91e33be73a342beb0c46de563ec113a1a5a6962dfc885bbe1233fa57a21",
    "methods": "57b6f427ba45a6cb0f3c99db3c8b2dac028ac3bcf28cb82fda71f1f32f19f4b0",
}
EXPECTED_TRIALS = {"FPB245WIR", "FPB255WIR", "FPC245WIR", "FPC255WIR"}
REQUIRED_MEASUREMENT_COLUMNS = {
    "TrialAcronym", "SiteYear", "TrialUnitId", "ReplicateNumber", "Block",
    "Mainplot", "Subplot", "GenotypeName", "FungicideTreatment",
}


def verify_sha256(path: Path, expected: str) -> str:
    """Read an original file in chunks and reject any content revision."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path.name}: {actual}")
    return actual


def load_export(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """Decode exactly one XLSX Export sheet, preserving missing cells."""
    try:
        from openpyxl import load_workbook  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("Install openpyxl to audit original XLSX files") from exc

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if workbook.sheetnames != ["Export"]:
            raise ValueError(f"unexpected worksheets: {workbook.sheetnames}")
        values = workbook["Export"].values
        header = list(next(values))
        if any(not isinstance(name, str) or not name for name in header):
            raise ValueError("blank or non-text column name")
        if len(set(header)) != len(header):
            raise ValueError("duplicate column names")
        rows = [dict(zip(header, row, strict=True)) for row in values]
        return header, rows
    finally:
        workbook.close()


def audit_rows(
    trial_rows: list[dict[str, Any]], measurement_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Check published plot structure; never assume rows are independent trials."""
    trial_by_code = {row["TrialAcronym"]: row for row in trial_rows}
    if len(trial_rows) != 4 or set(trial_by_code) != EXPECTED_TRIALS:
        raise ValueError("trial roster does not match the four published experiments")
    if any(row["DesignTypeName"] != "Split Plot using DiGGer" for row in trial_rows):
        raise ValueError("unexpected trial design")
    if len(measurement_rows) != 240:
        raise ValueError("expected exactly 240 source plot rows")
    if any(not row.keys() >= REQUIRED_MEASUREMENT_COLUMNS for row in measurement_rows):
        raise ValueError("missing design field")
    plot_ids = [row["TrialUnitId"] for row in measurement_rows]
    if any(value is None for value in plot_ids) or len(set(plot_ids)) != len(plot_ids):
        raise ValueError("missing or repeated global TrialUnitId")

    trial_counts: Counter[str] = Counter()
    treatment_counts: Counter[str] = Counter()
    genotype_counts: Counter[str] = Counter()
    block_counts: Counter[tuple[str, str]] = Counter()
    mainplot_genotypes: dict[tuple[str, str, str], set[str]] = {}
    mainplot_treatments: dict[tuple[str, str, str], set[str]] = {}
    for row in measurement_rows:
        code = row["TrialAcronym"]
        if code not in trial_by_code or row["SiteYear"] != trial_by_code[code]["SiteYear"]:
            raise ValueError("unmatched trial or contradictory year")
        if any(row[key] is None for key in REQUIRED_MEASUREMENT_COLUMNS):
            raise ValueError("missing required plot design value")
        treatment = str(row["FungicideTreatment"])
        genotype = str(row["GenotypeName"])
        block = str(row["Block"])
        mainplot = str(row["Mainplot"])
        trial_counts[code] += 1
        treatment_counts[treatment] += 1
        genotype_counts[genotype] += 1
        block_counts[code, block] += 1
        key = (code, block, mainplot)
        mainplot_genotypes.setdefault(key, set()).add(genotype)
        mainplot_treatments.setdefault(key, set()).add(treatment)

    if set(trial_counts.values()) != {60}:
        raise ValueError("expected 60 plots per trial")
    if len(treatment_counts) != 6 or set(treatment_counts.values()) != {40}:
        raise ValueError("expected six equally represented treatment labels")
    if len(genotype_counts) != 2 or set(genotype_counts.values()) != {120}:
        raise ValueError("expected two equally represented genotypes")
    if len(block_counts) != 20 or set(block_counts.values()) != {12}:
        raise ValueError("expected five twelve-plot blocks per trial")
    # The exported Mainplot/Subplot hierarchy differs between 2024 and 2025.
    # Do not silently force the methods document's stated fungicide main factor.
    by_trial: dict[str, dict[str, int]] = {}
    for code in sorted(EXPECTED_TRIALS):
        keys = [key for key in mainplot_treatments if key[0] == code]
        treatment_sizes = {len(mainplot_treatments[key]) for key in keys}
        genotype_sizes = {len(mainplot_genotypes[key]) for key in keys}
        if len(treatment_sizes) != 1 or len(genotype_sizes) != 1:
            raise ValueError(f"inconsistent mainplot design within {code}")
        by_trial[code] = {
            "block_mainplot_groups": len(keys),
            "treatment_labels_per_group": next(iter(treatment_sizes)),
            "genotype_labels_per_group": next(iter(genotype_sizes)),
        }

    return {
        "status": "source_integrity_only",
        "model_permission": "requires_protocol",
        "trial_count": len(trial_by_code),
        "measurement_rows": len(measurement_rows),
        "distinct_plot_ids": len(set(plot_ids)),
        "block_mainplot_groups": by_trial,
        "block_count": len(block_counts),
        "plots_by_trial": dict(sorted(trial_counts.items())),
        "treatments": dict(sorted(treatment_counts.items())),
        "genotypes": dict(sorted(genotype_counts.items())),
        "limitations": [
            "Four trials share one research site over two seasons and irrigation regimes.",
            "Plot rows are not independent treatment-randomization units.",
            "Mainplot/Subplot coding differs between 2024 and 2025; "
            "reconcile with methods before estimating effects.",
            "No treatment effects, endpoint statistics or out-of-trial models were estimated.",
        ],
    }


def main() -> int:
    """Validate immutable originals and write a deterministic derived report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=Path, required=True)
    parser.add_argument("--measurements", type=Path, required=True)
    parser.add_argument("--methods", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    hashes = {
        key: verify_sha256(getattr(args, key), expected)
        for key, expected in SOURCE_SHA256.items()
    }
    trial_header, trial_rows = load_export(args.trials)
    measurement_header, measurement_rows = load_export(args.measurements)
    report = audit_rows(trial_rows, measurement_rows)
    report["sha256"] = hashes
    report["source_columns"] = {
        "trials": len(trial_header),
        "measurements": len(measurement_header),
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != encoded:
            raise ValueError("committed intake report differs from current audited sources")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
