"""Scientific unit-of-analysis and source-pairability regression tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from crop_protection_ps.wheat_pairability import audit_wheat_data, audit_wheat_rows, main

_ROOT = Path(__file__).resolve().parents[1]


def _record(treatment: str, **changes: str) -> dict[str, str]:
    """Construct a synthetic endpoint record without any research measurements."""
    record = {
        "TrialId": "1",
        "Country": "TEST COUNTRY",
        "Latitude": "48.0",
        "Longitude": "12.0",
        "Date": "2019-05-25",
        "Daft": "10",
        "GsFrom": "37",
        "GsTo": "39",
        "NumSprays": "0" if treatment == "Untreated" else "1",
        "Treatment": treatment,
        "Organism": "TESTORG",
        "Parameter": "INFECT",
        "Clarifier": "NA",
        "Method": "P%INF",
        "SampleUnit": "TPLOT",
        "PlantPart": "LEAF, 4TH",
        "Value": "10.0",
    }
    record.update(changes)
    return record


def test_report_is_deterministic_and_matches_source_digest() -> None:
    actual = audit_wheat_data(_ROOT / "data")
    saved = json.loads((_ROOT / "results/external_wheat_pairability.json").read_text())
    assert actual == saved
    original = _ROOT / "data/external/zenodo_wheat_fungicide_6521175/basf-wheat-diseases.txt"
    assert actual["source_sha256"] == hashlib.sha256(original.read_bytes()).hexdigest()


def test_source_trial_groups_and_endpoint_coverage_are_not_row_sample_size() -> None:
    audit = audit_wheat_data(_ROOT / "data")
    assert (audit["source_rows"], audit["trial_id_count"]) == (2276, 76)
    assert (audit["endpoint_groups"], audit["paired_endpoint_groups"]) == (1164, 921)
    assert (audit["paired_untreated_records"], audit["paired_treated_records"]) == (921, 1112)
    assert (audit["unpaired_untreated_records"], audit["unpaired_treated_records"]) == (239, 4)
    assert audit["ambiguous_endpoint_groups"] == 0
    assert audit["paired_arm_multiplicity"] == {"1": 760, "2": 131, "3": 30}
    assert len(audit["trial_summary"]) == 76
    assert all("Untreated" in trial["treatment_labels"] for trial in audit["trial_summary"])
    assert all(len(trial["treatment_labels"]) > 1 for trial in audit["trial_summary"])
    assert {item["TrialId"] for item in audit["unpaired_treated_endpoints"]} == {"17", "70"}


def test_comparison_requires_exactly_one_record_per_arm() -> None:
    audit = audit_wheat_rows([_record("Untreated"), _record("TreatmentA")])
    assert audit["paired_endpoint_groups"] == 1
    assert audit["paired_treated_records"] == 1
    assert audit["unpaired_treated_records"] == 0

    repeated = audit_wheat_rows(
        [_record("Untreated"), _record("TreatmentA"), _record("TreatmentA", Value="7")]
    )
    assert repeated["paired_endpoint_groups"] == 0
    assert repeated["ambiguous_endpoint_groups"] == 1
    assert repeated["ambiguous_records"] == 3


def test_growth_stage_is_part_of_the_matching_key() -> None:
    audit = audit_wheat_rows([_record("Untreated"), _record("TreatmentA", GsTo="75")])
    assert audit["paired_endpoint_groups"] == 0
    assert audit["unpaired_untreated_records"] == 1
    assert audit["unpaired_treated_records"] == 1


def test_reused_trial_ids_and_nonfinite_measurements_fail_closed() -> None:
    with pytest.raises(ValueError, match="reused across sites or years"):
        audit_wheat_rows([_record("Untreated"), _record("TreatmentA", Date="2018-05-25")])
    with pytest.raises(ValueError, match="nonfinite measurement"):
        audit_wheat_rows([_record("Untreated", Value="NaN")])


def test_cli_check_detects_a_stale_report_without_overwriting_it(tmp_path: Path) -> None:
    destination = tmp_path / "report.json"
    args = ["--data-dir", str(_ROOT / "data"), "--output", str(destination)]
    assert main(args) == 0
    original = destination.read_bytes()
    assert main([*args, "--check"]) == 0
    assert destination.read_bytes() == original
    destination.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main([*args, "--check"])
    assert exc.value.code == 1
