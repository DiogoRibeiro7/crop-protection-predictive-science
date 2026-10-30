"""Offline integrity checks for independently published research datasets.

Checksums and byte sizes are recorded from the source repositories. This
module never downloads data and does not claim cross-stage comparability.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def verify_external_data(data_dir: Path) -> list[str]:
    """Return deterministic errors for missing or modified original source files.

    Args:
        data_dir: Directory containing ``external/manifest.json`` and raw files.

    Returns:
        An empty list if every listed file has the expected size and checksum.

    Raises:
        ValueError: The manifest itself is malformed or includes unsafe paths.
    """
    root = (data_dir / "external").resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("invalid external data manifest schema")
    sources: Any = manifest.get("sources")
    if not isinstance(sources, list):
        raise ValueError("external data manifest requires a sources list")

    errors: list[str] = []
    seen: set[Path] = set()
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("files"), list):
            raise ValueError("invalid source files declaration")
        for record in source["files"]:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                raise ValueError("invalid external file declaration")
            relative = Path(record["path"])
            path = (root / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(root) or path in seen:
                raise ValueError(f"unsafe or duplicate external file path: {relative}")
            seen.add(path)

            if not isinstance(record.get("size"), int) or record["size"] < 0:
                raise ValueError(f"invalid byte size for {relative}")
            checksum_kind = "sha256" if "sha256" in record else "md5"
            expected_digest = record.get(checksum_kind)
            valid_length = 64 if checksum_kind == "sha256" else 32
            if (
                not isinstance(expected_digest, str)
                or len(expected_digest) != valid_length
                or any(c not in "0123456789abcdef" for c in expected_digest)
            ):
                raise ValueError(f"invalid checksum for {relative}")

            if not path.is_file():
                errors.append(f"missing: {relative}")
                continue
            if path.stat().st_size != record["size"]:
                errors.append(f"size mismatch: {relative}")
                continue
            digest = hashlib.new(checksum_kind)
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
            if digest.hexdigest() != expected_digest:
                errors.append(f"checksum mismatch: {relative}")
    return errors
