"""Campaign / promotional price detection.

Uses multiple signals:
1. Explicit labels from scraper (campaign_label, member_price, original_price)
2. Statistical outlier detection — prices that drop >15% from rolling median
   and bounce back within 14 days are retroactively flagged as campaigns.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from matmoms.db.models import PriceObservation

logger = logging.getLogger(__name__)


def detect_statistical_campaigns(
    db: Session,
    lookback_days: int = 30,
    drop_threshold_pct: float = 15.0,
    bounce_back_days: int = 14,
) -> int:
    """Retroactively flag campaign prices using statistical outlier detection.

    A price is flagged as a statistical campaign if:
    - It dropped more than `drop_threshold_pct` from the 7-day rolling median
    - The price bounced back within `bounce_back_days`

    Returns the number of newly flagged observations.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    # Get all non-campaign observations in the lookback window
    stmt = (
        select(PriceObservation)
        .where(
            PriceObservation.observed_at >= cutoff,
            PriceObservation.is_campaign == False,  # noqa: E712
        )
        .order_by(
            PriceObservation.product_id,
            PriceObservation.store_id,
            PriceObservation.observed_at,
        )
    )

    observations = list(db.scalars(stmt).all())

    # Group by (product_id, store_id)
    grouped: dict[tuple[int, str], list[PriceObservation]] = {}
    for obs in observations:
        key = (obs.product_id, obs.store_id)
        grouped.setdefault(key, []).append(obs)

    flagged_count = 0

    for key, obs_list in grouped.items():
        if len(obs_list) < 5:
            continue

        prices = [o.price for o in obs_list]

        for i, obs in enumerate(obs_list):
            # Compute rolling median of preceding 7 observations
            start = max(0, i - 7)
            window = prices[start:i]
            if len(window) < 3:
                continue

            from statistics import median
            rolling_med = median(window)

            if rolling_med == 0:
                continue

            drop_pct = (obs.price - rolling_med) / rolling_med * 100

            # Check if this is a suspiciously large drop
            if drop_pct < -drop_threshold_pct:
                # Check if price bounces back
                future_obs = obs_list[i + 1 : i + 1 + bounce_back_days]
                bounced_back = any(
                    abs(fo.price - rolling_med) / rolling_med * 100 < 5
                    for fo in future_obs
                )

                if bounced_back:
                    obs.is_campaign = True
                    obs.campaign_label = (
                        obs.campaign_label or "statistiskt identifierad kampanj"
                    )
                    flagged_count += 1

    if flagged_count > 0:
        db.commit()
        logger.info(f"Flagged {flagged_count} observations as statistical campaigns")

    return flagged_count


def get_campaign_summary(
    db: Session,
    chain_id: str | None = None,
) -> dict:
    """Get summary of campaign observations."""
    from matmoms.db.models import Store

    stmt = select(
        func.count(PriceObservation.id).label("total"),
        func.sum(
            func.cast(PriceObservation.is_campaign, type_=None)
        ).label("campaigns"),
    ).where(PriceObservation.is_campaign.isnot(None))

    if chain_id:
        stmt = stmt.join(Store, PriceObservation.store_id == Store.id).where(
            Store.chain_id == chain_id
        )

    row = db.execute(stmt).one()
    total = row.total or 0
    campaigns = int(row.campaigns or 0)

    return {
        "total_observations": total,
        "campaign_observations": campaigns,
        "regular_observations": total - campaigns,
        "campaign_share_pct": round(campaigns / total * 100, 1) if total else 0,
    }
