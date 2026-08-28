from crop_protection_ps.design import make_candidate_grid, select_d_optimal_candidates


def test_d_optimal_design_returns_unique_candidates() -> None:
    candidates = make_candidate_grid()
    selected = select_d_optimal_candidates(candidates, ed50=10.0, hill=1.5, n_select=6)
    assert len(selected) == 6
    unique = selected.drop_duplicates(
        subset=["dose_g_ai_ha", "temperature_c", "spray_coverage_pct"]
    )
    assert len(unique) == 6
