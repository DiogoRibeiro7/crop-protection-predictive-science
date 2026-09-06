"""Independent multi-environment southern corn leaf blight data utilities.

The source dataset accompanies Del Ponte (2026), "From Scalar Summaries to
Functional Comparisons: A Framework for Analyzing Plant Disease Progress
Curves". Raw data remain in the upstream repository; acquisition is pinned to
an exact Git commit and Git blob identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd

_PUBLICATION_DOI = "10.1094/PHYTO-01-26-0009-LE"


@dataclass(frozen=True)
class BipolarisSourceContract:
    """Pinned identity and schema for the public maize disease-progress dataset."""

    repository_url: str = "https://github.com/emdelponte/paper-hgam-curves"
    source_commit: str = "d793d54c17ad404df2f6618d2681c993fcf144cf"
    source_path: str = "maize_bipolaris.csv"
    source_git_blob_sha1: str = "433a2d1c37ba4f6069d04d8ffc9f7916f0a8adc3"
    source_size_bytes: int = 53_293
    publication_doi: str = _PUBLICATION_DOI
    expected_columns: tuple[str, ...] = (
        "Ambiente",
        "Hibrido",
        "DAE",
        "Fenologia",
        "Bipolaris",
    )

    @property
    def raw_url(self) -> str:
        """Return a commit-pinned URL for the canonical CSV bytes."""
        return (
            "https://raw.githubusercontent.com/emdelponte/paper-hgam-curves/"
            f"{self.source_commit}/{self.source_path}"
        )


def git_blob_sha1(payload: bytes) -> str:
    """Return the Git blob SHA-1 for *payload*.

    SHA-1 is used here only because Git object identity is defined by it, not
    as a general-purpose security hash.
    """
    header = f"blob {len(payload)}\0".encode("ascii")
    return sha1(header + payload, usedforsecurity=False).hexdigest()


def validate_source_bytes(
    payload: bytes,
    contract: BipolarisSourceContract | None = None,
) -> None:
    """Validate downloaded bytes against the pinned upstream Git object."""
    source = contract or BipolarisSourceContract()
    if len(payload) != source.source_size_bytes:
        raise ValueError(
            "Bipolaris source byte length changed: "
            f"expected {source.source_size_bytes}, got {len(payload)}."
        )
    observed_blob = git_blob_sha1(payload)
    if observed_blob != source.source_git_blob_sha1:
        raise ValueError(
            "Bipolaris source Git blob identity changed: "
            f"expected {source.source_git_blob_sha1}, got {observed_blob}."
        )


def download_bipolaris(
    destination: str | Path,
    *,
    timeout_seconds: float = 30.0,
    contract: BipolarisSourceContract | None = None,
) -> Path:
    """Download the pinned public CSV and verify its exact Git object identity."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    source = contract or BipolarisSourceContract()
    with urlopen(source.raw_url, timeout=timeout_seconds) as response:
        payload = response.read()

    validate_source_bytes(payload, source)
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return output


def validate_bipolaris_frame(
    frame: pd.DataFrame,
    contract: BipolarisSourceContract | None = None,
) -> None:
    """Validate the canonical source schema and basic scientific ranges."""
    source = contract or BipolarisSourceContract()
    columns = tuple(map(str, frame.columns))
    if columns != source.expected_columns:
        raise ValueError(
            "Unexpected Bipolaris columns: "
            f"expected {source.expected_columns}, got {columns}."
        )
    if frame.empty:
        raise ValueError("Bipolaris source data must not be empty.")

    required = ["Ambiente", "Hibrido", "DAE", "Bipolaris"]
    if frame[required].isna().any().any():
        raise ValueError("Bipolaris source data contain missing required values.")

    dae = pd.to_numeric(frame["DAE"], errors="raise")
    severity = pd.to_numeric(frame["Bipolaris"], errors="raise")

    if bool((dae < 0).any()):
        raise ValueError("DAE values must be non-negative.")
    if bool(((severity < 0) | (severity > 100)).any()):
        raise ValueError("Bipolaris severity must lie between 0 and 100 percent.")

    duplicate_key = frame.duplicated(subset=["Ambiente", "Hibrido", "DAE"])
    if bool(duplicate_key.any()):
        raise ValueError(
            "Each environment-hybrid-day combination must identify one assessment."
        )


def load_bipolaris(path: str | Path) -> pd.DataFrame:
    """Load and normalize the canonical CSV into English analysis columns."""
    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    raw = pd.read_csv(source_path)
    validate_bipolaris_frame(raw)

    normalized = raw.rename(
        columns={
            "Ambiente": "environment",
            "Hibrido": "hybrid",
            "DAE": "days_after_emergence",
            "Fenologia": "phenology",
            "Bipolaris": "severity_pct",
        }
    ).copy()
    normalized["days_after_emergence"] = pd.to_numeric(
        normalized["days_after_emergence"], errors="raise"
    )
    normalized["severity_pct"] = pd.to_numeric(
        normalized["severity_pct"], errors="raise"
    )
    return normalized


def _t50(days: np.ndarray, severity: np.ndarray) -> float:
    """Return first interpolated day reaching half the observed maximum severity."""
    maximum = float(np.max(severity))
    threshold = 0.5 * maximum
    first = int(np.flatnonzero(severity >= threshold)[0])
    if first == 0:
        return float(days[0])

    t1 = float(days[first - 1])
    t2 = float(days[first])
    y1 = float(severity[first - 1])
    y2 = float(severity[first])
    if np.isclose(y1, y2):
        return t2
    return t1 + (threshold - y1) * (t2 - t1) / (y2 - y1)


def curve_metrics(
    frame: pd.DataFrame,
    *,
    dae_min_exclusive: float = 20.0,
    dae_max_exclusive: float = 116.0,
    min_assessments: int = 5,
) -> pd.DataFrame:
    """Compute transparent scalar summaries for each environment-hybrid curve.

    The default time window and minimum-assessment rule match the upstream
    analysis. AUDPC remains on the original percent-severity × day scale.
    """
    required = {
        "environment",
        "hybrid",
        "days_after_emergence",
        "severity_pct",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing normalized Bipolaris columns: {sorted(missing)}.")
    if dae_min_exclusive >= dae_max_exclusive:
        raise ValueError("dae_min_exclusive must be smaller than dae_max_exclusive.")
    if min_assessments < 2:
        raise ValueError("min_assessments must be at least 2.")

    window = frame.loc[
        (frame["days_after_emergence"] > dae_min_exclusive)
        & (frame["days_after_emergence"] < dae_max_exclusive)
    ].copy()

    records: list[dict[str, str | int | float]] = []
    grouped = window.groupby(["environment", "hybrid"], sort=True, observed=True)
    for (environment, hybrid), group in grouped:
        ordered = group.sort_values("days_after_emergence")
        if len(ordered) < min_assessments:
            continue
        days = ordered["days_after_emergence"].to_numpy(dtype=float)
        severity = ordered["severity_pct"].to_numpy(dtype=float)

        records.append(
            {
                "environment": str(environment),
                "hybrid": str(hybrid),
                "n_assessments": len(ordered),
                "first_dae": float(days[0]),
                "last_dae": float(days[-1]),
                "audpc_pct_days": float(np.trapezoid(severity, days)),
                "final_severity_pct": float(severity[-1]),
                "maximum_severity_pct": float(np.max(severity)),
                "t50_dae": _t50(days, severity),
            }
        )

    metrics = pd.DataFrame.from_records(records)
    if metrics.empty:
        raise ValueError("No Bipolaris curves satisfy the requested analysis window.")
    return metrics.sort_values(["environment", "hybrid"]).reset_index(drop=True)


def environment_rank_stability(metrics: pd.DataFrame) -> pd.DataFrame:
    """Return pairwise Spearman correlations of hybrid AUDPC rankings by environment."""
    required = {"environment", "hybrid", "audpc_pct_days"}
    missing = required.difference(metrics.columns)
    if missing:
        raise ValueError(f"Missing curve-metric columns: {sorted(missing)}.")

    matrix = metrics.pivot(
        index="hybrid",
        columns="environment",
        values="audpc_pct_days",
    )
    return matrix.corr(method="spearman", min_periods=3)


def empirical_case_summary(
    frame: pd.DataFrame,
    metrics: pd.DataFrame,
) -> dict[str, int | float]:
    """Summarize dataset breadth and cross-environment rank stability."""
    correlations = environment_rank_stability(metrics)
    upper = correlations.where(
        np.triu(np.ones(correlations.shape, dtype=bool), k=1)
    ).stack()
    median_rank_correlation = (
        float(upper.median()) if not upper.empty else float("nan")
    )
    return {
        "rows": len(frame),
        "environments": int(frame["environment"].nunique()),
        "hybrids": int(frame["hybrid"].nunique()),
        "eligible_curves": len(metrics),
        "median_pairwise_spearman_audpc": median_rank_correlation,
    }
