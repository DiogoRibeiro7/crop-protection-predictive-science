"""Verify row-level parity between the two original potato late-blight formats.

The Zenodo RData and TSV are independently hash-pinned. This non-inferential
audit compares every ordered source cell and identifies extra R factor levels,
without inferring randomized experiments or authorizing treatment models.

The CLI requires the development dependency ``rdata==1.1.0``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import warnings
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rdata

from crop_protection_ps.potato_source_audit import (
    SOURCE_COLUMNS,
    SOURCE_DOI,
    SOURCE_SHA256,
    audit_potato_source,
)

BINARY_URL = "https://zenodo.org/records/6352735/files/corteva-potato-late-blight.Rdata?download=1"
BINARY_ZENODO_MD5 = "a592e55691af3f08ef6928c51fa03a93"
BINARY_SHA256 = "7f7844a868ae10a621679a832a7de10b348a96684c8e948ad1700f808b084940"
_SERIALIZED_HEADER = b"RDX3\nX\n"
_NUMERIC = frozenset(("Latitude", "Longitude", "Value"))
_RDATE_COLUMN = "Date"
_R_FACTOR_COLUMNS = frozenset(SOURCE_COLUMNS) - _NUMERIC - {_RDATE_COLUMN}


def _check_original_binary(path: Path) -> None:
    """Reject unrecognized R workspace bytes before attempting deserialization."""
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    md5 = hashlib.md5(payload, usedforsecurity=False).hexdigest()
    if digest != BINARY_SHA256 or md5 != BINARY_ZENODO_MD5:
        raise ValueError("potato original RData checksum differs from Zenodo source identity")
    with gzip.open(path, "rb") as stream:
        if stream.read(len(_SERIALIZED_HEADER)) != _SERIALIZED_HEADER:
            raise ValueError("potato RData has unexpected serialization format")


def _first_mismatch(left: np.ndarray[Any, Any], right: np.ndarray[Any, Any]) -> int | None:
    """Report the first ordered source line that disagrees, counting the header."""
    positions = np.flatnonzero(left != right)
    return int(positions[0]) + 2 if len(positions) else None


def compare_potato_observation_frames(binary: pd.DataFrame, tsv: pd.DataFrame) -> dict[str, Any]:
    """Compare all fields and original row positions without dropping duplicates.

    R factor labels are compared literally, numeric doubles exactly and
    R's integer epoch-day Date values against the TSV's ISO dates. Numeric
    rounding tolerance is deliberately zero for this pinned source revision.
    """
    original_columns = tuple(str(column) for column in binary.columns)
    text_columns = tuple(str(column) for column in tsv.columns)
    if original_columns != SOURCE_COLUMNS or text_columns != SOURCE_COLUMNS:
        raise ValueError("potato RData/TSV columns or column order changed")
    if len(binary) == 0 or len(binary) != len(tsv):
        raise ValueError("potato RData/TSV row counts differ or are empty")

    inspections: list[dict[str, Any]] = []
    factor_vocabulary: list[dict[str, Any]] = []
    for name in SOURCE_COLUMNS:
        original = binary[name].reset_index(drop=True)
        published = tsv[name].reset_index(drop=True)
        if original.isna().any() or published.isna().any() or (published == "").any():
            raise ValueError(f"potato source missingness or empty field in {name}")

        if name == _RDATE_COLUMN:
            if not pd.api.types.is_numeric_dtype(original):
                raise ValueError("R Date must be stored as numeric epoch days")
            epoch_days = original.to_numpy(dtype=float)
            if (
                not np.isfinite(epoch_days).all()
                or not np.equal(epoch_days, np.floor(epoch_days)).all()
            ):
                raise ValueError("R Date contains nonfinite or fractional epoch days")
            converted = pd.to_datetime(original, unit="D", origin="unix").dt.strftime("%Y-%m-%d")
            left = converted.to_numpy(dtype=str)
            right = published.to_numpy(dtype=str)
            method = "r_epoch_day_to_iso_date_exact"
        elif name in _NUMERIC:
            if not pd.api.types.is_numeric_dtype(original):
                raise ValueError(f"RData field {name} is not numeric")
            left = original.to_numpy(dtype=float)
            right = pd.to_numeric(published, errors="raise").to_numpy(dtype=float)
            if not np.isfinite(left).all() or not np.isfinite(right).all():
                raise ValueError(f"nonfinite numeric source field {name}")
            method = "ieee754_double_exact"
        else:
            if name not in _R_FACTOR_COLUMNS or not isinstance(original.dtype, pd.CategoricalDtype):
                raise ValueError(f"RData field {name} does not preserve R factor labels")
            left = original.astype(str).to_numpy(dtype=str)
            right = published.to_numpy(dtype=str)
            method = "r_factor_label_exact"
            declared = {str(value) for value in original.cat.categories}
            observed = set(left)
            factor_vocabulary.append(
                {
                    "column": name,
                    "declared_factor_levels": len(declared),
                    "observed_factor_levels": len(observed),
                    "unused_factor_labels": sorted(declared - observed),
                }
            )

        mismatch_line = _first_mismatch(left, right)
        if mismatch_line is not None:
            raise ValueError(
                f"RData/TSV disagreement in {name} at original source line {mismatch_line}"
            )
        inspections.append(
            {
                "column": name,
                "binary_dtype": str(original.dtype),
                "comparison": method,
                "rows_compared": len(original),
                "mismatches": 0,
            }
        )

    return {
        "rows_compared": len(binary),
        "columns_compared": len(SOURCE_COLUMNS),
        "cells_compared": len(binary) * len(SOURCE_COLUMNS),
        "column_results": inspections,
        "factor_vocabulary": factor_vocabulary,
        "unexplained_mismatches": 0,
        "row_order_preserved": True,
        "exact_numeric_parity": True,
    }


def audit_potato_binary_parity(binary_path: Path, tsv_path: Path) -> dict[str, Any]:
    """Run a checksum-pinned comparison of both upstream serialized formats."""
    _check_original_binary(binary_path)
    previous = audit_potato_source(tsv_path)
    with warnings.catch_warnings():
        # rdata 1.1.0 gives the R Date class as numeric epoch-day values.
        warnings.filterwarnings("ignore", message='Missing constructor for R class "Date"')
        objects: Mapping[str, Any] = rdata.read_rda(binary_path)
    if set(objects) != {"obs"} or not isinstance(objects["obs"], pd.DataFrame):
        raise ValueError("original potato RData object inventory differs from obs data.frame")
    text_frame = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    compared = compare_potato_observation_frames(objects["obs"], text_frame)
    if compared["rows_compared"] != previous.summary["original_source_rows"]:
        raise ValueError("binary source row count diverges from earlier source intake")
    if compared["columns_compared"] != len(SOURCE_COLUMNS):
        raise ValueError("binary source introduces an unexpected field")

    return {
        "schema_version": 1,
        "analysis": "source_format_parity_without_protocol_identification",
        "source_doi": SOURCE_DOI,
        "binary_url": BINARY_URL,
        "binary_original_md5": BINARY_ZENODO_MD5,
        "binary_sha256": BINARY_SHA256,
        "binary_size_bytes": binary_path.stat().st_size,
        "text_sha256": SOURCE_SHA256,
        "r_objects": sorted(objects),
        "comparison": compared,
        "source_duplicate_excess_rows_reproduced_in_both_formats": (
            previous.summary["exact_repeat_excess_rows"]
        ),
        "source_signatures_repeated_100x_reproduced_in_both_formats": (
            previous.summary["signatures_repeated_100_times"]
        ),
        "unrepresented_endpoint_columns_found": False,
        "experiment_identifiers_reconciled": False,
        "model_permission": "requires_protocol",
        "interpretation_limits": [
            "RData contains only obs with the same 127034 ordered rows and 10 TSV fields.",
            "Both formats preserve the 2016 exact-record multiplicity; its cause is unknown.",
            "Unused R factor levels are vocabulary metadata, not additional observations.",
            "Neither format identifies yield as a distinct outcome column.",
            "Parity alone cannot identify independent trials, plots or subsamples.",
            "No treatment effects, model selection or data correction are authorized.",
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Write or verify the deterministic derived report from both original files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rdata", type=Path, required=True, help="Original Zenodo RData")
    parser.add_argument("--tsv", type=Path, required=True, help="Original Zenodo TSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/real_potato_late_blight/binary_parity.json"),
    )
    parser.add_argument("--check", action="store_true", help="Verify a saved report unchanged")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = audit_potato_binary_parity(args.rdata, args.tsv)
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"potato binary parity audit failed: {exc}\n")
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            parser.exit(1, f"potato binary parity report missing or stale: {args.output}\n")
        print(f"potato binary parity report verified: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"potato binary parity report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
