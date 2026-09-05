import hashlib
import json
from pathlib import Path

import pandas as pd

from crop_protection_ps.hop_trial import load_hop_trial

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _provenance(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_hop_trial_bytes_match_committed_provenance() -> None:
    data_path = RAW_DIR / "richardson_gent_hop_downy_mildew.csv"
    provenance_path = RAW_DIR / "richardson_gent_hop_downy_mildew.provenance.json"
    provenance = _provenance(provenance_path)
    frame = load_hop_trial(data_path)

    assert _sha256(data_path) == provenance["local_sha256"]
    assert len(frame) == provenance["raw_rows"]
    assert sorted(frame["year"].unique().tolist()) == provenance["years"]
    assert int(frame["audpc"].isna().sum()) == provenance["missing_audpc"]
    assert provenance["local_file"] == str(data_path.relative_to(ROOT)).replace("\\", "/")


def test_weather_bytes_match_committed_provenance() -> None:
    data_path = RAW_DIR / "corvallis_monthly_weather_2009_2025.csv"
    provenance_path = RAW_DIR / "corvallis_monthly_weather_2009_2025.provenance.json"
    provenance = _provenance(provenance_path)
    frame = pd.read_csv(data_path)

    assert _sha256(data_path) == provenance["local_sha256"]
    assert len(frame) == provenance["rows"]
