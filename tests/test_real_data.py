from pathlib import Path

import pandas as pd
import pytest

import crop_protection_ps.real_data as real_data


def test_validate_expected_files_tracks_each_workbook(tmp_path: Path) -> None:
    contract = real_data.FundecitrusFileContract()
    (tmp_path / contract.mortality_filename).touch()
    (tmp_path / contract.climate_filename).touch()

    status = real_data.validate_expected_files(tmp_path)

    assert status == {"mortality": True, "coverage": False, "climate": True}


def test_inspect_workbook_requires_existing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        real_data.inspect_workbook(tmp_path / "missing.xlsx")


def test_inspect_workbook_returns_sheet_columns(monkeypatch, tmp_path: Path) -> None:
    workbook = tmp_path / "trial.xlsx"
    workbook.touch()

    class _FakeExcelFile:
        sheet_names = ("Mortality", "Metadata")

    monkeypatch.setattr(pd, "ExcelFile", lambda path: _FakeExcelFile())

    def fake_read_excel(path, *, sheet_name, nrows):
        assert path == workbook
        assert nrows == 5
        if sheet_name == "Mortality":
            return pd.DataFrame(columns=["Treatment", "Mortality (%)"])
        return pd.DataFrame(columns=["Site", "Year"])

    monkeypatch.setattr(pd, "read_excel", fake_read_excel)

    assert real_data.inspect_workbook(workbook) == {
        "Mortality": ("Treatment", "Mortality (%)"),
        "Metadata": ("Site", "Year"),
    }
