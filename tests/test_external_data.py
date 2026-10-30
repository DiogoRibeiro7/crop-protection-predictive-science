"""Offline integrity tests for vendored, licence-verified public datasets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from crop_protection_ps.external_data import verify_external_data


def test_external_sources_match_published_checksums() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    assert verify_external_data(data_dir) == []


def test_verifier_detects_missing_or_corrupted_file(tmp_path: Path) -> None:
    root = tmp_path / "external"
    root.mkdir()
    sample = root / "sample.txt"
    sample.write_bytes(b"original")
    manifest = {
        "schema_version": 1,
        "sources": [{"files": [{
            "path": "sample.txt",
            "size": 8,
            "sha256": hashlib.sha256(b"original").hexdigest(),
        }]}],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_external_data(tmp_path) == []
    sample.write_bytes(b"replaced")
    assert verify_external_data(tmp_path) == ["checksum mismatch: sample.txt"]
    sample.unlink()
    assert verify_external_data(tmp_path) == ["missing: sample.txt"]


def test_verifier_refuses_path_escape(tmp_path: Path) -> None:
    root = tmp_path / "external"
    root.mkdir()
    manifest = {
        "schema_version": 1,
        "sources": [{"files": [{
            "path": "../outside.txt",
            "size": 0,
            "md5": hashlib.md5(b"").hexdigest(),
        }]}],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe"):
        verify_external_data(tmp_path)
