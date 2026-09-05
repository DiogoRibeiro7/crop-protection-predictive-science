"""Contracts for adapting public Fundecitrus crop-protection trial files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

FUNDECITRUS_PROJECT_URL = (
    "https://rdp.fundecitrus.com.br/project/"
    "measures-for-reducing-primary-infections-in-t-9"
)


@dataclass(frozen=True)
class FundecitrusFileContract:
    """Expected public files for the real-data extension."""

    mortality_filename: str = "field trial 2 – Psyllid mortality.xlsx"
    coverage_filename: str = "field trial 2 – Spray coverage.xlsx"
    climate_filename: str = "field trial 2 - Climatic condition.xlsx"


def inspect_workbook(path: str | Path) -> dict[str, tuple[str, ...]]:
    """Return sheet names and column names without imposing undocumented semantics."""
    workbook_path = Path(path)
    if not workbook_path.exists():
        raise FileNotFoundError(workbook_path)
    excel = pd.ExcelFile(workbook_path)
    structure: dict[str, tuple[str, ...]] = {}
    for sheet_name in excel.sheet_names:
        frame = pd.read_excel(workbook_path, sheet_name=sheet_name, nrows=5)
        structure[sheet_name] = tuple(map(str, frame.columns))
    return structure


def validate_expected_files(directory: str | Path) -> dict[str, bool]:
    """Check whether the three public field-trial workbooks are present locally."""
    base = Path(directory)
    contract = FundecitrusFileContract()
    filenames = {
        "mortality": contract.mortality_filename,
        "coverage": contract.coverage_filename,
        "climate": contract.climate_filename,
    }
    return {name: (base / filename).exists() for name, filename in filenames.items()}
