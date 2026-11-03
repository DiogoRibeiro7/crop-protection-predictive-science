"""Tests for non-inferential Dryad colony-growth descriptions."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

import crop_protection_ps.dryad_growth_descriptives as module
from crop_protection_ps.dryad_growth_descriptives import (
    audit_dryad_growth,
    main,
    render_reports,
    summarise_growth_strain,
)

_ROOT = Path(__file__).resolve().parents[1]
_OUTPUT = _ROOT / "results/external_dryad_growth"


def _row(
    replicate: str,
    count: str,
    *,
    strain: str = "2",
    temperature: str = "10",
    temp_rep: str = "1",
    run: str = "4",
    mating: str = "A1",
    picture_id: str | None = None,
) -> dict[str, str]:
    """Create one source-shaped colony count observation."""
    return {
        "Picture ID": (
            picture_id if picture_id is not None else f"{strain} {mating} {temperature}.{replicate}"
        ),
        "Strain": strain,
        "Temp.Rep": temp_rep,
        "Temperature": temperature,
        "Mating.Type": mating,
        "Replicate": replicate,
        "Colonly.Count": count,
        "Run.Num": run,
    }


def test_original_growth_reports_match_all_committed_outputs() -> None:
    report = audit_dryad_growth(_ROOT / "data")
    expected = render_reports(report)
    assert set(expected) == {
        "summary.json",
        "strain_2_mating_type_runs.csv",
        "strain_3_mating_type_runs.csv",
        "strain_4_mating_type_runs.csv",
    }
    for filename, content in expected.items():
        assert (_OUTPUT / filename).read_text(encoding="utf-8") == content
    assert report == json.loads((_OUTPUT / "summary.json").read_text(encoding="utf-8"))
    assert report["analysis"] == "colony_count_description"
    assert report["source_count_unit"] == "recorded_colonies_per_assay_row"
    assert report["group_fields"] == ["Strain", "Temperature", "Temp.Rep", "Run.Num", "Mating.Type"]


def test_growth_unit_and_picture_id_collisions_are_not_hidden() -> None:
    report = audit_dryad_growth(_ROOT / "data")
    expected = {
        "strain_2": (28, {"6": 28}, 5729),
        "strain_3": (30, {"3": 4, "6": 26}, 4437),
        "strain_4": (28, {"6": 28}, 4940),
    }
    assert set(report["strains"]) == set(expected)
    for name, source in report["strains"].items():
        run_count, multiplicity, total = expected[name]
        assert source["source_record_count"] == 168
        assert source["temperature_run_groups"] == run_count
        assert source["records_per_temperature_run"] == multiplicity
        assert source["strain_run_mating_cells"] == 56
        assert source["records_per_strain_run_mating_cell"] == {"3": 56}
        assert source["source_total_recorded_colonies"] == total
        assert source["source_distinct_picture_id_labels"] == 84
        assert source["source_repeated_picture_id_rows"] == 84
        assert source["source_colony_field"] == "Colonly.Count"
        assert source["temperature_labels"] == [str(i) for i in range(4, 32, 2)]
        assert {group["Strain"] for group in source["groups"]} == {name[-1]}
        assert {group["Mating.Type"] for group in source["groups"]} == {"A1", "A2"}


def test_csv_retains_original_picture_labels_and_nonnegative_colony_counts() -> None:
    report = audit_dryad_growth(_ROOT / "data")
    for name, strain in report["strains"].items():
        records = list(
            csv.DictReader(io.StringIO(render_reports(report)[f"{name}_mating_type_runs.csv"]))
        )
        assert len(records) == 56
        assert sum(int(row["source_assay_rows"]) for row in records) == 168
        assert (
            sum(int(row["total_recorded_colonies"]) for row in records)
            == (strain["source_total_recorded_colonies"])
        )
        assert all(row["source_replicate_labels"] == "1|2|3" for row in records)
        assert all(len(row["source_picture_ids"].split("|")) == 3 for row in records)
        for record in records:
            assert int(record["min_source_colony_count"]) >= 0
            assert float(record["mean_colonies_per_source_row"]) == pytest.approx(
                int(record["total_recorded_colonies"]) / int(record["source_assay_rows"]),
                abs=1e-10,
            )
            assert (
                int(record["min_source_colony_count"])
                <= float(record["mean_colonies_per_source_row"])
                <= int(record["max_source_colony_count"])
            )


def test_synthetic_counts_are_grouped_without_mating_type_pooling() -> None:
    rows = [
        _row("1", "0"),
        _row("2", "4"),
        _row("3", "8"),
        _row("1", "10", mating="A2"),
    ]
    result = summarise_growth_strain(rows, expected_strain="2", filename="synthetic.xlsx")
    assert result["source_record_count"] == 4
    assert result["temperature_run_groups"] == 1
    assert result["strain_run_mating_cells"] == 2
    assert result["source_total_recorded_colonies"] == 22
    first, second = result["groups"]
    assert first["Mating.Type"] == "A1"
    assert first["source_replicate_labels"] == ["1", "2", "3"]
    assert first["total_recorded_colonies"] == 12
    assert first["mean_colonies_per_source_row"] == 4
    assert (first["min_source_colony_count"], first["max_source_colony_count"]) == (0, 8)
    assert second["Mating.Type"] == "A2"
    assert second["total_recorded_colonies"] == 10


def test_repeated_picture_ids_across_temperature_replicates_are_preserved() -> None:
    rows = [
        _row("1", "2", picture_id="shared label", temp_rep="1"),
        _row("1", "3", picture_id="shared label", temp_rep="2"),
    ]
    report = summarise_growth_strain(rows, expected_strain="2", filename="synthetic.xlsx")
    assert report["source_record_count"] == 2
    assert report["source_distinct_picture_id_labels"] == 1
    assert report["source_repeated_picture_id_rows"] == 1
    assert report["strain_run_mating_cells"] == 2
    assert sum(group["total_recorded_colonies"] for group in report["groups"]) == 5


@pytest.mark.parametrize(
    "rows,expected_message",
    [
        ([], "empty Dryad lab"),
        ([_row("1", "1"), _row("1", "2")], "duplicate nested growth replicate"),
        ([_row("1", "1", strain="3")], "unexpected Dryad growth strain"),
        ([_row("1", "-1")], "invalid Colonly.Count"),
        ([_row("1", "1.5")], "invalid Colonly.Count"),
        ([_row("1", "NaN")], "invalid Colonly.Count"),
        ([_row("1", "1", temperature="NaN")], "invalid Dryad growth Temperature"),
        ([_row("1", "1", run="2.5")], "invalid Dryad growth Run.Num"),
        ([_row("1", "1", temp_rep="N/A")], "invalid Dryad growth Temp.Rep"),
        ([_row("A", "1")], "invalid Dryad growth Replicate"),
        ([_row("1", "1", picture_id="")], "blank Dryad growth"),
        ([_row("1", "1") | {"extra": "value"}], "unexpected Dryad growth columns"),
    ],
)
def test_invalid_source_records_fail_closed(
    rows: list[dict[str, str]], expected_message: str
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        summarise_growth_strain(rows, expected_strain="2", filename="synthetic.xlsx")


def test_invalid_expected_strain_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid requested strain"):
        summarise_growth_strain([_row("1", "1")], expected_strain="two", filename="test")


def test_explicit_permission_denial_blocks_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "analysis_decision", lambda *args: {"status": "requires_protocol"})
    with pytest.raises(ValueError, match="not permitted"):
        audit_dryad_growth(_ROOT / "data")


def test_cli_check_is_read_only_and_fails_on_missing_or_stale_files(tmp_path: Path) -> None:
    destination = tmp_path / "growth"
    args = ["--data-dir", str(_ROOT / "data"), "--output-dir", str(destination)]
    with pytest.raises(SystemExit) as missing:
        main([*args, "--check"])
    assert missing.value.code == 1
    assert not destination.exists()

    assert main(args) == 0
    before = {path.name: path.read_bytes() for path in destination.iterdir()}
    assert main([*args, "--check"]) == 0
    assert {path.name: path.read_bytes() for path in destination.iterdir()} == before

    (destination / "strain_3_mating_type_runs.csv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stale:
        main([*args, "--check"])
    assert stale.value.code == 1
