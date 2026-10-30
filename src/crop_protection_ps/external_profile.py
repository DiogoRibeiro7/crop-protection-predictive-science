"""Reproducible structural profiles of the original external research files.

The profiler uses only the Python standard library to read tab-separated files
and the cached values in XLSX Open Packaging Convention archives. It never
modifies the source files, interprets treatments, or joins different studies.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import posixpath
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from crop_protection_ps.external_data import verify_external_data

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NA_TOKENS = frozenset({"NA", "N/A"})


def _column_index(reference: str) -> int:
    """Translate an XLSX cell reference such as ``AB12`` to a zero-based column."""
    letters = reference.rstrip("0123456789").upper()
    if not letters or any(letter < "A" or letter > "Z" for letter in letters):
        raise ValueError(f"invalid XLSX cell reference: {reference!r}")
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def _shared_strings(archive: ZipFile) -> list[str]:
    """Read plain and rich-text shared strings in workbook order."""
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(f"{{{_MAIN}}}t"))
        for item in root.iter(f"{{{_MAIN}}}si")
    ]


def _cell_text(cell: ET.Element, shared: Sequence[str]) -> str:
    """Read a cell's stored value without evaluating formulas or coercing dates."""
    if cell.get("t") == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{_MAIN}}}t"))
    value = cell.findtext(f"{{{_MAIN}}}v")
    if value is None:
        return ""
    if cell.get("t") == "s":
        index = int(value)
        if not 0 <= index < len(shared):
            raise ValueError(f"invalid shared-string index: {index}")
        return shared[index]
    return value


def _sheet_rows(
    archive: ZipFile, filename: str, shared: Sequence[str]
) -> tuple[list[dict[int, str]], int]:
    """Read populated XLSX rows, retaining sparse column positions."""
    root = ET.fromstring(archive.read(filename))
    rows: list[dict[int, str]] = []
    formula_cells = 0
    for row in root.iter(f"{{{_MAIN}}}row"):
        values: dict[int, str] = {}
        for cell in row.findall(f"{{{_MAIN}}}c"):
            reference = cell.get("r")
            if reference is None:
                raise ValueError("XLSX cell without an address")
            if cell.find(f"{{{_MAIN}}}f") is not None:
                formula_cells += 1
            value = _cell_text(cell, shared)
            if value.strip():
                values[_column_index(reference)] = value
        if values:
            rows.append(values)
    return rows, formula_cells


def _summarise_table(
    name: str, rows: Sequence[Mapping[int, str]], formula_cells: int = 0
) -> dict[str, Any]:
    """Count observations and per-column missingness without changing values."""
    if not rows:
        raise ValueError(f"tabular source {name!r} has no header")
    header = rows[0]
    column_count = len(header)
    if set(header) != set(range(column_count)):
        raise ValueError(f"tabular source {name!r} has missing header names")
    if len(set(header.values())) != column_count:
        raise ValueError(f"tabular source {name!r} has duplicate header names")

    records = rows[1:]
    columns: list[dict[str, Any]] = []
    for index in range(column_count):
        values = [record.get(index, "") for record in records]
        populated = [value for value in values if value.strip()]
        columns.append(
            {
                "name": header[index],
                "missing_cells": len(records) - len(populated),
                "literal_na_cells": sum(value.strip().upper() in _NA_TOKENS for value in populated),
                "distinct_nonblank": len(set(populated)),
            }
        )

    normalised_name = name.casefold().replace(" ", "").replace("_", "")
    role = "documentation" if normalised_name.startswith("readme") else "observations"
    return {
        "name": name,
        "role": role,
        "rows": len(records),
        "columns": column_count,
        "formula_cells": formula_cells,
        "fields": columns,
    }


def _profile_workbook(path: Path) -> list[dict[str, Any]]:
    """Profile every worksheet, including embedded readme sheets."""
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in relationships.findall(f"{{{_PACKAGE_REL}}}Relationship")
        }
        shared = _shared_strings(archive)
        tables: list[dict[str, Any]] = []
        for sheet in workbook.iter(f"{{{_MAIN}}}sheet"):
            relationship_id = sheet.get(f"{{{_REL}}}id")
            if relationship_id is None or relationship_id not in targets:
                raise ValueError(f"missing XLSX worksheet relationship in {path.name}")
            target = targets[relationship_id]
            filename = posixpath.normpath(
                target.lstrip("/") if target.startswith("/") else posixpath.join("xl", target)
            )
            if not filename.startswith("xl/worksheets/") or filename not in archive.namelist():
                raise ValueError(f"unsafe or missing worksheet path: {filename}")
            rows, formula_cells = _sheet_rows(archive, filename, shared)
            tables.append(_summarise_table(sheet.attrib["name"], rows, formula_cells))
        return tables


def _profile_tsv(path: Path) -> list[dict[str, Any]]:
    """Read a UTF-8, tab-separated data file, retaining source NA tokens."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t", strict=True)
        rows = [
            {index: value for index, value in enumerate(row) if value.strip()}
            for row in reader
            if any(value.strip() for value in row)
        ]
    if rows and any(max(row, default=-1) >= len(rows[0]) for row in rows[1:]):
        raise ValueError(f"TSV rows exceed header width: {path.name}")
    return [_summarise_table(path.name, rows)]


def profile_external_data(data_dir: Path) -> dict[str, Any]:
    """Profile all verified public source files; return metadata, never raw values.

    The manifest is authoritative. Failed source integrity checks stop profiling
    before any table is parsed. ``NA`` is a literal token, not a blank cell.
    """
    errors = verify_external_data(data_dir)
    if errors:
        raise ValueError("external source integrity failed: " + "; ".join(errors))

    manifest_path = data_dir / "external" / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    sources: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        files: list[dict[str, Any]] = []
        for item in source["files"]:
            relative = item["path"]
            path = data_dir / "external" / relative
            suffix = path.suffix.casefold()
            if suffix == ".xlsx":
                tables = _profile_workbook(path)
            elif suffix == ".txt" and not path.name.casefold().startswith("readme"):
                tables = _profile_tsv(path)
            else:
                tables = []
            files.append({"path": relative, "tables": tables})
        sources.append({"id": source["id"], "doi": source["doi"], "files": files})

    return {
        "schema_version": 1,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "sources": sources,
    }


def _json_text(profile: Mapping[str, Any]) -> str:
    return json.dumps(profile, indent=2, ensure_ascii=False) + "\n"


def main(argv: Iterable[str] | None = None) -> int:
    """Generate or verify a checked-in structural profile without network access."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("data/external/profile.json"))
    parser.add_argument("--check", action="store_true", help="Check the profile without writing")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        result = _json_text(profile_external_data(args.data_dir))
    except (ValueError, OSError, KeyError, ET.ParseError, BadZipFile) as exc:
        parser.exit(1, f"cannot profile external data: {exc}\n")

    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != result:
            parser.exit(1, f"profile is missing or stale: {args.output}\n")
        print(f"profile matches verified external data: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
        print(f"wrote external data profile: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
