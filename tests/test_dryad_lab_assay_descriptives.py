"""Tests for permission-gated, count-based Dryad laboratory descriptions."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

import crop_protection_ps.dryad_lab_assay_descriptives as module
from crop_protection_ps.dryad_lab_assay_descriptives import (
    audit_dryad_lab_assays,
    main,
    render_reports,
    summarise_lab_assay,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_dryad_lab_assays"


def _row(
    rep: str,
    successes: str,
    total: str,
    *,
    kind: str = "germination",
    temp: str = "10",
    temp_rep: str = "1",
    run: str = "3",
    fraction: str | None = None,
) -> dict[str, str]:
    """Make a minimal source-shaped count row with a recorded proportion."""
    success_name = "Sum.Germ" if kind == "germination" else "Sum.Mating"
    return {
        "Temperature": temp,
        "Temp.Rep": temp_rep,
        "Run.Num": run,
        "Rep": rep,
        success_name: successes,
        "Sum.Total": total,
        "Sum.Prop": fraction if fraction is not None else str(int(successes) / int(total)),
    }


def test_all_real_exports_reproduce_original_workbook_audit() -> None:
    report = audit_dryad_lab_assays(_ROOT / "data")
    expected = render_reports(report)
    assert set(expected) == {
        "summary.json",
        "germination_temperature_runs.csv",
        "conjugation_strain_2_temperature_runs.csv",
        "conjugation_strain_3_temperature_runs.csv",
        "conjugation_strain_4_temperature_runs.csv",
    }
    for name, text in expected.items():
        assert (_OUTPUT / name).read_text(encoding="utf-8") == text
    assert json.loads((_OUTPUT / "summary.json").read_text(encoding="utf-8")) == report
    assert report["schema_version"] == 1
    assert report["analysis"] == "assay_count_description"
    assert report["aggregation_group"] == ["Temperature", "Temp.Rep", "Run.Num"]


def test_counts_and_replicate_labels_reconcile_without_pseudoreplication() -> None:
    assays = audit_dryad_lab_assays(_ROOT / "data")["assays"]
    expected_counts = {
        "germination": (11174, 6774),
        "conjugation_strain_2": (30908, 9101),
        "conjugation_strain_3": (30145, 8264),
        "conjugation_strain_4": (26479, 7010),
    }
    assert set(assays) == set(expected_counts)
    for name, assay in assays.items():
        assert assay["source_record_count"] == 84
        assert assay["temperature_run_groups"] == 28
        assert assay["source_rows_per_temperature_run"] == {"3": 28}
        assert assay["temperature_labels"] == [str(value) for value in range(4, 32, 2)]
        assert (
            assay["source_total_count"],
            assay["source_success_count"],
        ) == expected_counts[name]
        assert len(assay["groups"]) == 28
        assert all(group["source_rep_labels"] == ["1", "2", "3"] for group in assay["groups"])
        assert all(group["source_assay_rows"] == 3 for group in assay["groups"])
        assert (
            len(
                {
                    (group["Temperature"], group["Temp.Rep"], group["Run.Num"])
                    for group in assay["groups"]
                }
            )
            == 28
        )


def test_csvs_contain_one_group_per_temperature_run_and_count_weighted_rates() -> None:
    report = audit_dryad_lab_assays(_ROOT / "data")
    for name, assay in report["assays"].items():
        filename = f"{name}_temperature_runs.csv"
        records = list(csv.DictReader(io.StringIO(render_reports(report)[filename])))
        assert len(records) == 28
        assert sum(int(group["source_assay_rows"]) for group in records) == 84
        assert (
            sum(int(group["source_total_count"]) for group in records)
            == assay["source_total_count"]
        )
        assert (
            sum(int(group["source_success_count"]) for group in records)
            == assay["source_success_count"]
        )
        for group in records:
            assert group["source_rep_labels"] == "1|2|3"
            assert float(group["pooled_recorded_success_fraction"]) == pytest.approx(
                int(group["source_success_count"]) / int(group["source_total_count"]),
                abs=1e-10,
            )
            assert float(group["min_source_assay_fraction"]) <= (
                float(group["pooled_recorded_success_fraction"]) + 1e-9
            )
            assert float(group["max_source_assay_fraction"]) >= (
                float(group["pooled_recorded_success_fraction"]) - 1e-9
            )


@pytest.mark.parametrize("kind", ["germination", "conjugation"])
def test_synthetic_grouping_is_count_weighted_and_never_strain_pooled(kind: str) -> None:
    rows = [
        _row("1", "1", "2", kind=kind),
        _row("2", "9", "10", kind=kind),
        _row("3", "2", "8", kind=kind),
    ]
    report = summarise_lab_assay(rows, kind=kind, filename="synthetic.xlsx")
    assert report["temperature_run_groups"] == 1
    group = report["groups"][0]
    assert group["source_assay_rows"] == 3
    assert group["source_rep_labels"] == ["1", "2", "3"]
    assert group["source_total_count"] == 20
    assert group["source_success_count"] == 12
    assert group["pooled_recorded_success_fraction"] == 0.6
    assert group["min_source_assay_fraction"] == 0.25
    assert group["max_source_assay_fraction"] == 0.9
    assert report["source_success_field"] == ("Sum.Germ" if kind == "germination" else "Sum.Mating")


def test_run_codes_reused_across_temperatures_are_not_collapsed() -> None:
    rows = [_row("1", "1", "2"), _row("1", "2", "4", temp="12")]
    report = summarise_lab_assay(rows, kind="germination", filename="synthetic.xlsx")
    assert report["temperature_run_groups"] == 2
    assert [group["Temperature"] for group in report["groups"]] == ["10", "12"]
    assert [group["source_rep_labels"] for group in report["groups"]] == [["1"], ["1"]]


@pytest.mark.parametrize(
    "rows,reason",
    [
        ([], "empty Dryad lab worksheet"),
        ([_row("1", "1", "2"), _row("1", "1", "2")], "repeated assay Rep"),
        ([_row("1", "1", "2") | {"Sum.Total": "0"}], "invalid assay counts"),
        ([_row("1", "1", "2") | {"Sum.Germ": "3"}], "invalid assay counts"),
        ([_row("1", "1", "2") | {"Sum.Germ": "1.5"}], "invalid Sum.Germ count"),
        ([_row("1", "1", "2") | {"Sum.Total": "-1"}], "invalid Sum.Total count"),
        ([_row("1", "1", "2") | {"Sum.Prop": "0.1"}], "fraction disagrees"),
        ([_row("1", "1", "2") | {"Sum.Prop": "NaN"}], "invalid assay counts"),
        ([_row("1", "1", "2") | {"Temperature": "nan"}], "invalid assay counts"),
        ([_row("1", "1", "2") | {"Temp.Rep": "1.2"}], "invalid assay counts"),
        ([_row("1", "1", "2") | {"Rep": "A"}], "invalid source Rep label"),
        ([_row("1", "1", "2") | {"Extra": "value"}], "unexpected assay source columns"),
    ],
)
def test_unsafe_source_rows_fail_closed(rows: list[dict[str, str]], reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        summarise_lab_assay(rows, kind="germination", filename="synthetic.xlsx")


def test_unknown_assay_kind_is_not_reinterpreted() -> None:
    with pytest.raises(ValueError, match="unsupported assay kind"):
        summarise_lab_assay([_row("1", "1", "2")], kind="growth", filename="synthetic.xlsx")


def test_explicit_eligibility_denial_blocks_all_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "analysis_decision", lambda *args: {"status": "requires_protocol"})
    with pytest.raises(ValueError, match="not permitted"):
        audit_dryad_lab_assays(_ROOT / "data")


def test_cli_check_detects_stale_files_without_modifying_them(tmp_path: Path) -> None:
    destination = tmp_path / "dryad-lab"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(destination)]
    with pytest.raises(SystemExit) as missing:
        main([*args, "--check"])
    assert missing.value.code == 1
    assert not destination.exists()

    assert main(args) == 0
    before = {path.name: path.read_bytes() for path in destination.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {path.name: path.read_bytes() for path in destination.iterdir()} == before

    (destination / "conjugation_strain_3_temperature_runs.csv").write_text(
        "stale\n", encoding="utf-8"
    )
    with pytest.raises(SystemExit) as stale:
        main([*args, "--check"])
    assert stale.value.code == 1
