"""Read-only CLI for auditing authorized linked-discovery CSV observations."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from crop_protection_ps.discovery_csv import DiscoveryCSVError, audit_discovery_csv


def main(argv: Sequence[str] | None = None) -> int:
    """Print a deterministic structural audit as JSON; return 0 on success.

    Candidate IDs are omitted by default because an audit may describe private
    experiment identities. The explicit flag opts into exposing them on stdout.
    All errors go to stderr and return exit code 2, without a traceback.
    """
    parser = argparse.ArgumentParser(
        description="Audit an authorized local lab–glasshouse–field CSV (no network or writes)."
    )
    parser.add_argument("csv_path", type=Path, help="Path to the local discovery CSV")
    parser.add_argument(
        "--include-candidate-ids",
        action="store_true",
        help="Include linked candidate IDs in JSON (may expose confidential metadata)",
    )
    args = parser.parse_args(argv)

    try:
        result = audit_discovery_csv(args.csv_path)
    except (DiscoveryCSVError, ValueError, OSError) as error:
        print(f"discovery CSV audit failed: {error}", file=sys.stderr)
        return 2

    report: dict[str, object] = {
        "n_observations": result.n_observations,
        "n_candidates": result.n_candidates,
        "n_fully_linked_candidates": len(result.fully_linked_candidate_ids),
        "stage_counts": {
            stage.value: result.stage_counts[stage] for stage in sorted(result.stage_counts)
        },
        "audit_scope": "structural_only_not_biological_validation",
    }
    if args.include_candidate_ids:
        report["fully_linked_candidate_ids"] = list(result.fully_linked_candidate_ids)
    print(json.dumps(report, sort_keys=True))
    return 0


def run() -> None:
    """Console-script entry point with conventional process exit status."""
    raise SystemExit(main())


if __name__ == "__main__":
    run()
