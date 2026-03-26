"""Core pass-through calculations.

The theoretical maximum consumer price reduction from the VAT cut
(12% -> 6%) is: (1.12 - 1.06) / 1.12 = 5.36%.

Pass-through percentage = observed_avg_change / -5.36 * 100
  100% = full pass-through
  0%   = no pass-through
  >100% = retailers cut prices beyond the VAT effect
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from statistics import median, quantiles

from sqlalchemy.orm import Session

from matmoms.db.queries import get_baseline_prices, get_current_prices

# Theoretical max consumer price drop from 12% -> 6% VAT
THEORETICAL_CHANGE_PCT = -5.36

# Dead zone: changes within ±0.5% are classified as "unchanged"
UNCHANGED_THRESHOLD = 0.5


@dataclass
class ProductChange:
    product_id: int
    store_id: str
    baseline_price: float
    current_price: float
    change_pct: float
    classification: str  # "lowered", "unchanged", "increased"


@dataclass
class PassthroughResult:
    """Result of a pass-through calculation for a given scope."""

    scope_type: str  # "national", "chain", "store", "category"
    scope_id: str | None
    baseline_date: str
    comparison_date: str

    n_products: int
    n_lowered: int
    n_unchanged: int
    n_increased: int

    avg_change_pct: float
    median_change_pct: float
    p25_change_pct: float | None
    p75_change_pct: float | None

    passthrough_pct: float  # avg_change / THEORETICAL * 100
    campaign_excluded: int

    changes: list[ProductChange] = field(default_factory=list)


def compute_passthrough(
    db: Session,
    baseline_end: date = date(2026, 3, 31),
    baseline_window_days: int = 7,
    comparison_date: date | None = None,
    scope_type: str = "national",
    scope_id: str | None = None,
    exclude_campaigns: bool = True,
    store_ids: list[str] | None = None,
) -> PassthroughResult:
    """Compute VAT pass-through metrics.

    Args:
        db: Database session
        baseline_end: Last date of baseline window (default: March 31)
        baseline_window_days: Number of days in baseline window
        comparison_date: Date to compare against baseline (default: today)
        scope_type: One of "national", "chain", "store", "category", "format"
        scope_id: Filter value for scope (chain_id, store_id, or category_id)
        exclude_campaigns: Whether to exclude promotional prices
        store_ids: Optional list of store IDs to restrict to (for format-level analysis)
    """
    if comparison_date is None:
        comparison_date = date.today()

    # Build filter kwargs based on scope
    filters: dict = {}
    if scope_type == "chain":
        filters["chain_id"] = scope_id
    elif scope_type == "store":
        filters["store_id"] = scope_id
    elif scope_type == "category":
        filters["category_id"] = scope_id

    if store_ids:
        filters["store_ids"] = store_ids

    # Get baseline and current prices
    baselines = get_baseline_prices(
        db,
        baseline_end=baseline_end,
        window_days=baseline_window_days,
        exclude_campaigns=exclude_campaigns,
        **filters,
    )

    current = get_current_prices(
        db,
        target_date=comparison_date,
        exclude_campaigns=exclude_campaigns,
        **filters,
    )

    # Compute changes for products present in both sets
    changes: list[ProductChange] = []
    campaign_excluded_count = 0

    # Count products in current that were excluded by campaign filter
    if exclude_campaigns:
        current_with_campaigns = get_current_prices(
            db,
            target_date=comparison_date,
            exclude_campaigns=False,
            **filters,
        )
        campaign_excluded_count = len(current_with_campaigns) - len(current)

    common_keys = set(baselines.keys()) & set(current.keys())

    for key in common_keys:
        baseline_price = baselines[key]
        current_price = current[key]

        if baseline_price == 0:
            continue

        change_pct = (current_price - baseline_price) / baseline_price * 100

        if change_pct < -UNCHANGED_THRESHOLD:
            classification = "lowered"
        elif change_pct > UNCHANGED_THRESHOLD:
            classification = "increased"
        else:
            classification = "unchanged"

        changes.append(ProductChange(
            product_id=key[0],
            store_id=key[1],
            baseline_price=baseline_price,
            current_price=current_price,
            change_pct=round(change_pct, 2),
            classification=classification,
        ))

    if not changes:
        return PassthroughResult(
            scope_type=scope_type,
            scope_id=scope_id,
            baseline_date=baseline_end.isoformat(),
            comparison_date=comparison_date.isoformat(),
            n_products=0,
            n_lowered=0,
            n_unchanged=0,
            n_increased=0,
            avg_change_pct=0.0,
            median_change_pct=0.0,
            p25_change_pct=None,
            p75_change_pct=None,
            passthrough_pct=0.0,
            campaign_excluded=campaign_excluded_count,
            changes=[],
        )

    # Aggregate
    pcts = [c.change_pct for c in changes]
    n_lowered = sum(1 for c in changes if c.classification == "lowered")
    n_unchanged = sum(1 for c in changes if c.classification == "unchanged")
    n_increased = sum(1 for c in changes if c.classification == "increased")

    avg_change = sum(pcts) / len(pcts)
    med_change = median(pcts)

    p25 = None
    p75 = None
    if len(pcts) >= 4:
        q = quantiles(pcts, n=4)
        p25 = round(q[0], 2)
        p75 = round(q[2], 2)

    passthrough = round(avg_change / THEORETICAL_CHANGE_PCT * 100, 1)

    return PassthroughResult(
        scope_type=scope_type,
        scope_id=scope_id,
        baseline_date=baseline_end.isoformat(),
        comparison_date=comparison_date.isoformat(),
        n_products=len(changes),
        n_lowered=n_lowered,
        n_unchanged=n_unchanged,
        n_increased=n_increased,
        avg_change_pct=round(avg_change, 2),
        median_change_pct=round(med_change, 2),
        p25_change_pct=p25,
        p75_change_pct=p75,
        passthrough_pct=passthrough,
        campaign_excluded=campaign_excluded_count,
        changes=changes,
    )
