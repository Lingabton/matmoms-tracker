"""Tests for the pass-through calculation engine."""

from datetime import date

from matmoms.metrics.passthrough import (
    THEORETICAL_CHANGE_PCT,
    compute_passthrough,
)


def test_passthrough_with_seeded_data(seeded_db):
    """Verify pass-through calculation with known test data.

    Baseline: milk=18.90, meat=49.90
    Post-cut: milk=17.90 (-5.29%), meat=49.90 (0%)
    Expected avg change: ~-2.65%
    """
    result = compute_passthrough(
        seeded_db,
        baseline_end=date(2026, 3, 31),
        comparison_date=date(2026, 4, 2),
    )

    assert result.n_products == 4  # 2 products x 2 stores
    assert result.n_lowered == 2   # milk in both stores
    assert result.n_unchanged == 2  # meat in both stores
    assert result.n_increased == 0

    # Milk changed -5.29%, meat 0% => avg ~-2.65%
    assert -3.0 < result.avg_change_pct < -2.0

    # Pass-through should be around 49% (2.65/5.36*100)
    assert 40 < result.passthrough_pct < 60


def test_passthrough_chain_scope(seeded_db):
    """Test filtering by chain."""
    result = compute_passthrough(
        seeded_db,
        baseline_end=date(2026, 3, 31),
        comparison_date=date(2026, 4, 2),
        scope_type="chain",
        scope_id="ica",
    )

    assert result.n_products == 2  # 2 products in 1 ICA store
    assert result.scope_type == "chain"
    assert result.scope_id == "ica"


def test_passthrough_empty_data(seeded_db):
    """Test with a date that has no observations."""
    result = compute_passthrough(
        seeded_db,
        baseline_end=date(2026, 3, 31),
        comparison_date=date(2026, 5, 1),  # No data for May
    )

    assert result.n_products == 0
    assert result.passthrough_pct == 0.0


def test_theoretical_constant():
    """Verify the theoretical VAT change calculation: (1.12-1.06)/1.12"""
    expected = -((1.12 - 1.06) / 1.12) * 100
    assert abs(THEORETICAL_CHANGE_PCT - expected) < 0.01
