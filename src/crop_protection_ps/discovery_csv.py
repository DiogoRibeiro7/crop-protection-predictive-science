"""Read externally supplied discovery observations from CSV without modifying them.

The loader enforces the observation contract and gives source row numbers for
validation failures. It does not infer units, impute values or fetch data.
"""

from __future__ import annotations

import csv
from pathlib import Path

from pydantic import ValidationError

from crop_protection_ps.discovery_evidence import (
    DiscoveryObservation,
    LinkedEvidenceAudit,
    audit_linked_discovery_evidence,
)

_COLUMNS = frozenset(DiscoveryObservation.model_fields)
_OPTIONAL_COLUMNS = frozenset({"site_id", "season"})


class DiscoveryCSVError(ValueError):
    """A CSV schema, parsing or observation-validation error."""


def load_discovery_csv(path: str | Path) -> list[DiscoveryObservation]:
    """Validate an authorized UTF-8 CSV, preserving record order.

    The header must contain every required model field exactly once. Optional
    site and season columns can be absent or blank for non-field observations.
    A blank required value is rejected by the Pydantic observation contract.

    Args:
        path: CSV path; no network access or writes are performed.

    Raises:
        DiscoveryCSVError: Missing, duplicate or unexpected columns, malformed
            records, non-UTF-8 text or an invalid observation (with CSV row).
        OSError: The input path cannot be read.
    """
    observations: list[DiscoveryObservation] = []
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, restkey="__extra_fields__", restval=None)
            header = reader.fieldnames
            if not header:
                raise DiscoveryCSVError("CSV must contain a header")
            duplicate = sorted(name for name in set(header) if header.count(name) > 1)
            if duplicate:
                raise DiscoveryCSVError(f"duplicate CSV columns: {duplicate}")
            missing = sorted(_COLUMNS - _OPTIONAL_COLUMNS - set(header))
            unexpected = sorted(set(header) - _COLUMNS)
            if missing or unexpected:
                raise DiscoveryCSVError(
                    f"invalid CSV header: missing={missing}, unexpected={unexpected}"
                )

            for row in reader:
                # Physical line numbers remain useful with quoted multiline fields.
                line_number = reader.line_num
                if "__extra_fields__" in row or any(value is None for value in row.values()):
                    raise DiscoveryCSVError(
                        f"CSV row ending at line {line_number}: malformed columns"
                    )
                cleaned = {
                    key: (None if key in _OPTIONAL_COLUMNS and value == "" else value)
                    for key, value in row.items()
                }
                try:
                    observations.append(DiscoveryObservation.model_validate(cleaned))
                except ValidationError as error:
                    raise DiscoveryCSVError(
                        f"CSV row ending at line {line_number}: {error}"
                    ) from error
    except (UnicodeError, csv.Error) as error:
        raise DiscoveryCSVError(f"invalid CSV encoding or syntax: {error}") from error

    if not observations:
        raise DiscoveryCSVError("CSV contains no observations")
    return observations


def audit_discovery_csv(path: str | Path) -> LinkedEvidenceAudit:
    """Read a CSV and apply the cross-record structural-linkage audit."""
    return audit_linked_discovery_evidence(load_discovery_csv(path))
