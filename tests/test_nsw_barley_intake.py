"""Synthetic source-integrity tests for the NSW barley intake."""

from copy import deepcopy

import pytest

from crop_protection_ps.nsw_barley_intake import audit_rows


def _synthetic_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Construct the expected two-year export hierarchy without source data."""
    codes = ("FPB245WIR", "FPC245WIR", "FPB255WIR", "FPC255WIR")
    trials: list[dict[str, object]] = []
    plots: list[dict[str, object]] = []
    plot_id = 1
    for code in codes:
        year = 2024 if "24" in code else 2025
        trials.append(
            {"TrialAcronym": code, "SiteYear": year, "DesignTypeName": "Split Plot using DiGGer"}
        )
        for block in range(1, 6):
            for treatment in range(1, 7):
                for genotype in ("A", "B"):
                    plots.append(
                        {
                            "TrialAcronym": code,
                            "SiteYear": year,
                            "TrialUnitId": plot_id,
                            "ReplicateNumber": block,
                            "Block": block,
                            "Mainplot": (1 if genotype == "A" else 2)
                            if year == 2024
                            else treatment,
                            "Subplot": treatment
                            if year == 2024
                            else (1 if genotype == "A" else 2),
                            "GenotypeName": genotype,
                            "FungicideTreatment": f"T{treatment}",
                        }
                    )
                    plot_id += 1
    return trials, plots


def test_reconciles_all_240_plots_and_reports_hierarchy_change() -> None:
    """Both observed mainplot layouts must be reported, not silently harmonized."""
    trials, plots = _synthetic_rows()
    summary = audit_rows(trials, plots)
    assert summary["distinct_plot_ids"] == 240
    assert summary["block_mainplot_groups"]["FPB245WIR"]["treatment_labels_per_group"] == 6
    assert summary["block_mainplot_groups"]["FPB255WIR"]["treatment_labels_per_group"] == 1


@pytest.mark.parametrize("mutation", ["duplicate_id", "year_mismatch", "missing_design"])
def test_rejects_corrupted_plot_identity(mutation: str) -> None:
    """A real-source discrepancy must fail before derived evidence is committed."""
    trials, original = _synthetic_rows()
    plots = deepcopy(original)
    if mutation == "duplicate_id":
        plots[1]["TrialUnitId"] = plots[0]["TrialUnitId"]
    elif mutation == "year_mismatch":
        plots[0]["SiteYear"] = 2030
    else:
        plots[0]["Block"] = None
    with pytest.raises(ValueError):
        audit_rows(trials, plots)
