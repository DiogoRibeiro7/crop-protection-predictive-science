"""Regressions for original-source wheat trial-count evidence and safeguards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from crop_protection_ps.wheat_publication_identity import (
    audit_wheat_publication_identity,
    main,
    summarize_wheat_identity_scenarios,
    wheat_author_evidence_request,
)
from crop_protection_ps.wheat_site_hierarchy import audit_wheat_site_rows

_ROOT = Path(__file__).resolve().parents[1]
_EVIDENCE = _ROOT / "data/external/wheat_publication_evidence.json"


def _row(trial_id: str, *, year: int, longitude: str = "1.0") -> dict[str, str]:
    """Make a minimal row with controlled site/year collisions."""
    return {
        "TrialId": trial_id,
        "Country": "TEST",
        "Latitude": "40.0",
        "Longitude": longitude,
        "Date": f"{year}-05-01",
    }


def test_published_title_count_does_not_reconcile_trial_ids() -> None:
    report = audit_wheat_publication_identity(_ROOT / "data")
    saved = json.loads((_ROOT / "results/external_wheat_publication_identity.json").read_text())
    assert report == saved
    assert report["source_scripts_reviewed"] == ["basf-wheat-diseases.R", "setup.R"]
    assert report["uninspected_publisher_files"] == [
        "basf-wheat-diseases.Rdata",
        "basf-wheat-diseases-map.png",
    ]
    assert report["publisher_source_file_count"] == 5
    assert report["counts"] == {
        "source_trial_id_codes": 76,
        "distinct_recorded_geocode_years": 65,
        "distinct_recorded_geocodes": 56,
        "published_trial_count": 56,
        "trial_ids_above_geocode_year_count": 11,
        "geocode_years_above_geocode_count": 9,
        "trial_ids_above_geocode_count": 20,
        "published_count_equals_geocode_count": True,
        "published_count_equals_geocode_year_count": False,
        "published_count_equals_trial_id_count": False,
        "geocode_years_with_multiple_trial_ids": 9,
        "geocodes_reused_across_years": 8,
    }
    assert report["maximum_shared_geocode_year"] == {
        "country": "BULGARIA",
        "latitude": "43.3",
        "longitude": "25.0",
        "year": 2019,
        "trial_ids": ["31", "32", "33", "34"],
    }
    assert report["model_permission"] == "requires_protocol"
    assert report["experimental_unit_identity_established"] is False
    assert report["inference_permitted"] is False
    assert len(report["remaining_protocol_requirements"]) == 4


def test_small_synthetic_grouping_decomposition_is_exact_and_noncausal() -> None:
    hierarchy = audit_wheat_site_rows(
        [
            _row("1", year=2018),
            _row("2", year=2018),
            _row("3", year=2019),
            _row("4", year=2019, longitude="2.0"),
        ]
    )
    scenarios = summarize_wheat_identity_scenarios(hierarchy, publisher_count=2)
    assert scenarios["source_trial_id_codes"] == 4
    assert scenarios["distinct_recorded_geocode_years"] == 3
    assert scenarios["distinct_recorded_geocodes"] == 2
    assert scenarios["trial_ids_above_geocode_year_count"] == 1
    assert scenarios["geocode_years_above_geocode_count"] == 1
    assert scenarios["trial_ids_above_geocode_count"] == 2
    assert scenarios["published_count_equals_geocode_count"] is True


def test_count_gaps_must_agree_with_underlying_groups() -> None:
    hierarchy = audit_wheat_site_rows(
        [_row("1", year=2018), _row("2", year=2018), _row("3", year=2019)]
    )
    with pytest.raises(ValueError, match="shared-year grouping gaps"):
        summarize_wheat_identity_scenarios(
            {**hierarchy, "shared_geocode_years": []}, publisher_count=1
        )
    with pytest.raises(ValueError, match="cross-year grouping gaps"):
        summarize_wheat_identity_scenarios({**hierarchy, "reused_geocodes": []}, publisher_count=1)
    for invalid in (0, True, "56"):
        with pytest.raises(ValueError, match="positive integer"):
            summarize_wheat_identity_scenarios(hierarchy, publisher_count=invalid)  # type: ignore[arg-type]


def test_author_request_is_source_specific_and_keeps_inferential_gate() -> None:
    report = audit_wheat_publication_identity(_ROOT / "data")
    request = wheat_author_evidence_request(report)
    assert request == (_ROOT / "results/external_wheat_protocol_identity_request.md").read_text()
    assert "BULGARIA" in request
    assert "`31`, `32`, `33`, `34`" in request
    assert "76 `TrialId` codes" in request
    assert "requires_protocol" in request
    assert "No researchers have been contacted" in request


@pytest.mark.parametrize(
    "change", ["md5", "script", "title_count", "title_mismatch", "invalid_date", "duplicate"]
)
def test_unverified_publisher_evidence_fails_closed(tmp_path: Path, change: str) -> None:
    raw: dict[str, Any] = json.loads(_EVIDENCE.read_text(encoding="utf-8"))
    output = tmp_path / "publication.json"
    if change == "md5":
        raw["publisher_files"][1]["md5"] = "0" * 32
    elif change == "script":
        raw["source_script_findings"][1]["trial_dictionary_defined_in_reviewed_script"] = True
    elif change == "title_count":
        raw["publisher_trial_count"] = 55
    elif change == "title_mismatch":
        raw["publisher_title"] = "A different 56-trial study"
    elif change == "invalid_date":
        raw["reviewed_on"] = "2026-13-33"
    elif change == "duplicate":
        # This is deliberately invalid JSON *semantics*, though JSON parsers
        # commonly accept it and silently overwrite one of the field values.
        output.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    if change != "duplicate":
        output.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        audit_wheat_publication_identity(_ROOT / "data", evidence_path=output)


def test_cli_generates_and_checks_both_artifacts(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    request = tmp_path / "request.md"
    args = [
        "--data-dir",
        str(_ROOT / "data"),
        "--output",
        str(output),
        "--request-output",
        str(request),
    ]
    assert main(args) == 0
    baseline = (output.read_bytes(), request.read_bytes())
    assert main([*args, "--check"]) == 0
    assert (output.read_bytes(), request.read_bytes()) == baseline
    request.write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        main([*args, "--check"])
    assert error.value.code == 1
