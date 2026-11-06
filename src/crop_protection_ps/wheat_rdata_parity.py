"""Compare the publisher's R workspace with its independently pinned wheat TSV.

The original binary is verified against Zenodo's advertised MD5 before
deserialization. This is a row-preserving *source-format parity* audit only:
it does not assert physical trial identities or permit treatment-effect models.

The command requires the development-only ``rdata`` reader (version 1.1.0).
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

from crop_protection_ps.wheat_publication_identity import audit_wheat_publication_identity
from crop_protection_ps.wheat_site_hierarchy import _SOURCE_PATH, audit_wheat_site_data

_RDATA_PATH = "zenodo_wheat_fungicide_6521175/basf-wheat-diseases.Rdata"
_RDATA_FILE = "basf-wheat-diseases.Rdata"
_SERIALIZED_HEADER = b"RDX3\nX\n"
_MISSING_TOKEN = "NA"


def _sha256(path: Path) -> str:
    """Calculate a full-file SHA-256 fingerprint of the original bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _original_rdata_md5(data_dir: Path) -> str:
    """Use the earlier publisher inventory as the reference, not a new guess."""
    inventory_path = data_dir / "external/wheat_publication_evidence.json"
    inventory: dict[str, Any] = json.loads(inventory_path.read_text(encoding="utf-8"))
    records = [item for item in inventory["publisher_files"] if item["name"] == _RDATA_FILE]
    if len(records) != 1 or records[0]["review_status"] != "publisher_inventory_only":
        raise ValueError("publisher RData provenance was not independently documented")
    md5 = records[0]["md5"]
    if not isinstance(md5, str) or len(md5) != 32:
        raise ValueError("invalid original publisher RData MD5")
    return md5


def compare_wheat_observation_frames(binary: pd.DataFrame, tsv: pd.DataFrame) -> dict[str, Any]:
    """Compare every cell at its original row and column position.

    Serialized R numeric values are IEEE 754 doubles; exporting them to TSV
    can change the last representable bit when a decimal is printed and
    reparsed. At most one unit in the last place (ULP) is allowed *only* for
    those numeric conversions. Category
    labels, missingness, dates, row order and column order require equality.
    """
    columns = [str(column) for column in binary.columns]
    if len(columns) != len(set(columns)) or columns != [str(column) for column in tsv.columns]:
        raise ValueError("binary and TSV column names/order differ")
    if len(binary) != len(tsv) or len(binary) == 0:
        raise ValueError("binary and TSV row counts differ or are empty")
    if columns.count("TrialId") != 1 or columns.count("Date") != 1:
        raise ValueError("published observation keys are missing")

    discrepancies: list[dict[str, Any]] = []
    inspected: list[dict[str, Any]] = []
    for column in columns:
        original = binary[column].reset_index(drop=True)
        exported = tsv[column].reset_index(drop=True)
        binary_nulls = int(original.isna().sum())
        tsv_nulls = int((exported == _MISSING_TOKEN).sum())
        if binary_nulls != tsv_nulls:
            raise ValueError(f"missingness differs in column {column}")

        if column == "Date":
            if not pd.api.types.is_numeric_dtype(original) or binary_nulls:
                raise ValueError("R Date must contain nonmissing epoch-day values")
            normalized = pd.to_datetime(original, unit="D", origin="unix").dt.strftime("%Y-%m-%d")
            equal = normalized.to_numpy(dtype=str) == exported.to_numpy(dtype=str)
            comparison = "iso_date_from_r_epoch_days"
        elif pd.api.types.is_numeric_dtype(original):
            numeric = pd.to_numeric(exported.replace(_MISSING_TOKEN, np.nan), errors="raise")
            left = original.to_numpy(dtype=float)
            right = numeric.to_numpy(dtype=float)
            finite = np.isfinite(left) & np.isfinite(right)
            equal = np.isnan(left) & np.isnan(right)
            # Only operate on finite pairs: np.spacing(NaN) itself raises a
            # runtime warning and would obscure the intended missingness check.
            rounding_limit = np.maximum(
                np.abs(np.spacing(left[finite])), np.abs(np.spacing(right[finite]))
            )
            equal[finite] = np.abs(left[finite] - right[finite]) <= rounding_limit
            exact = (left == right) | (np.isnan(left) & np.isnan(right))
            for index in np.flatnonzero(~exact & equal):
                discrepancies.append(
                    {
                        "source_line": int(index) + 2,
                        "column": column,
                        "rdata_value": float(left[index]),
                        "tsv_value": float(right[index]),
                        "absolute_difference": float(abs(left[index] - right[index])),
                    }
                )
            comparison = "numeric_ieee754_at_most_one_ulp"
        else:
            normalized = original.astype("string").fillna(_MISSING_TOKEN)
            equal = normalized.to_numpy(dtype=str) == exported.to_numpy(dtype=str)
            comparison = "exact_factor_or_text_label"

        mismatch_count = int(np.count_nonzero(~equal))
        if mismatch_count:
            first = int(np.flatnonzero(~equal)[0]) + 2
            raise ValueError(
                f"binary/TSV disagreement in {column}, source line {first}: "
                f"{mismatch_count} mismatches"
            )
        inspected.append(
            {
                "column": column,
                "binary_dtype": str(original.dtype),
                "comparison": comparison,
                "missing_in_both": binary_nulls,
                "rows_compared": len(original),
                "unexplained_mismatches": mismatch_count,
            }
        )

    return {
        "rows_compared": len(binary),
        "columns_compared": len(columns),
        "column_names": columns,
        "cells_compared": len(binary) * len(columns),
        "column_results": inspected,
        "rounding_only_differences": discrepancies,
        "rounding_only_difference_count": len(discrepancies),
        "unexplained_mismatches": 0,
        "row_order_preserved": True,
    }


def audit_wheat_rdata_parity(data_dir: Path) -> dict[str, Any]:
    """Verify the original binary snapshot and source-level row parity offline."""
    earlier = audit_wheat_publication_identity(data_dir)
    binary_path = data_dir / "external" / _RDATA_PATH
    if not binary_path.is_file():
        raise ValueError(f"missing original RData file: {binary_path}")
    published_md5 = _original_rdata_md5(data_dir)
    observed_md5 = hashlib.md5(binary_path.read_bytes()).hexdigest()
    if observed_md5 != published_md5:
        raise ValueError("original RData checksum differs from Zenodo MD5")
    with gzip.open(binary_path, "rb") as compressed:
        if compressed.read(len(_SERIALIZED_HEADER)) != _SERIALIZED_HEADER:
            raise ValueError("RData is not the expected RDX3/XDR serialisation")

    # rdata currently returns numeric R Date epoch-days while emitting a
    # warning for that unsupported R class. The explicit comparison below
    # interprets these values without dropping their underlying precision.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message='Missing constructor for R class "Date"')
        objects: Mapping[str, Any] = rdata.read_rda(binary_path)
    if set(objects) != {"obs"} or not isinstance(objects["obs"], pd.DataFrame):
        raise ValueError("unexpected original RData object inventory")
    obs = objects["obs"]
    tsv_path = data_dir / "external" / _SOURCE_PATH
    textframe = pd.read_csv(tsv_path, sep="\t", dtype=str, keep_default_na=False)
    frame_report = compare_wheat_observation_frames(obs, textframe)
    if frame_report["rows_compared"] != audit_wheat_site_data(data_dir)["source_rows"]:
        raise ValueError("binary observations disagree with previous source-row count")
    if textframe["TrialId"].nunique(dropna=False) != earlier["counts"]["source_trial_id_codes"]:
        raise ValueError("binary comparison does not cover the prior 76 trial-ID count")
    if earlier["model_permission"] != "requires_protocol":
        raise ValueError("wheat model permission unexpectedly changed")

    return {
        "schema_version": 1,
        "analysis": "format_parity_without_experimental_unit_identification",
        "source_record": earlier["source_record_url"],
        "source_doi": earlier["source_doi"],
        "binary_file": _RDATA_PATH,
        "binary_size_bytes": binary_path.stat().st_size,
        "binary_original_md5": published_md5,
        "binary_sha256": _sha256(binary_path),
        "tsv_file": _SOURCE_PATH,
        "tsv_sha256": earlier["source_sha256"],
        "published_trial_count": earlier["counts"]["published_trial_count"],
        "source_trial_id_codes": earlier["counts"]["source_trial_id_codes"],
        "original_r_objects": sorted(objects),
        "comparison": frame_report,
        "additional_plot_or_trial_keys_found": False,
        "trial_identity_established": False,
        "model_permission": earlier["model_permission"],
        "limitations": [
            "RData contains one obs data.frame with the same 17 fields and 2276 ordered rows.",
            "One floating-point double differs by one ULP after decimal text export.",
            "Row-level format parity does not identify independent trials, plots or replicates.",
            "Source binary is integrity-checked separately from the original TSV manifest.",
            "No treatment-effect analysis or permission change follows from this parity result.",
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    """Regenerate or verify a deterministic comparison of two original formats."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/external_wheat_rdata_parity.json")
    )
    parser.add_argument("--check", action="store_true", help="Verify without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        content = json.dumps(audit_wheat_rdata_parity(args.data_dir), indent=2) + "\n"
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f"wheat RData parity audit failed: {exc}\n")
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != content:
            parser.exit(1, f"wheat RData parity report missing or stale: {args.output}\n")
        print(f"wheat RData parity report verified: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
        print(f"wrote wheat RData parity report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
