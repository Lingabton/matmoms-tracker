"""Reusable database query functions."""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from matmoms.db.models import PriceObservation, Product, ScrapeRun, Store


def get_baseline_prices(
    db: Session,
    baseline_end: date,
    window_days: int = 7,
    exclude_campaigns: bool = True,
    store_id: str | None = None,
    chain_id: str | None = None,
    category_id: str | None = None,
    store_ids: list[str] | None = None,
) -> dict[tuple[int, str], float]:
    """Get median baseline price per (product_id, store_id) over a window.

    Returns dict mapping (product_id, store_id) -> median_price.
    """
    start = datetime.combine(baseline_end - timedelta(days=window_days), datetime.min.time())
    end = datetime.combine(baseline_end, datetime.max.time())

    stmt = (
        select(
            PriceObservation.product_id,
            PriceObservation.store_id,
            PriceObservation.price,
        )
        .where(PriceObservation.observed_at.between(start, end))
    )

    if exclude_campaigns:
        stmt = stmt.where(PriceObservation.is_campaign == False)  # noqa: E712
    if store_id:
        stmt = stmt.where(PriceObservation.store_id == store_id)
    if store_ids:
        stmt = stmt.where(PriceObservation.store_id.in_(store_ids))
    if chain_id:
        stmt = stmt.join(Store, PriceObservation.store_id == Store.id).where(
            Store.chain_id == chain_id
        )
    if category_id:
        stmt = stmt.join(Product, PriceObservation.product_id == Product.id).where(
            Product.category_id == category_id
        )

    rows = db.execute(stmt).all()

    # Group prices by (product_id, store_id) and compute median
    from statistics import median

    grouped: dict[tuple[int, str], list[float]] = {}
    for product_id, sid, price in rows:
        grouped.setdefault((product_id, sid), []).append(price)

    return {key: median(prices) for key, prices in grouped.items()}


def get_current_prices(
    db: Session,
    target_date: date,
    exclude_campaigns: bool = True,
    store_id: str | None = None,
    chain_id: str | None = None,
    category_id: str | None = None,
    store_ids: list[str] | None = None,
) -> dict[tuple[int, str], float]:
    """Get latest price per (product_id, store_id) on a given date.

    Uses the most recent observation on that date.
    """
    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())

    # Subquery to get max observation id per product-store on the date
    sub = (
        select(
            PriceObservation.product_id,
            PriceObservation.store_id,
            func.max(PriceObservation.id).label("max_id"),
        )
        .where(PriceObservation.observed_at.between(start, end))
    )

    if exclude_campaigns:
        sub = sub.where(PriceObservation.is_campaign == False)  # noqa: E712
    if store_id:
        sub = sub.where(PriceObservation.store_id == store_id)
    if store_ids:
        sub = sub.where(PriceObservation.store_id.in_(store_ids))

    sub = sub.group_by(PriceObservation.product_id, PriceObservation.store_id).subquery()

    stmt = select(
        PriceObservation.product_id,
        PriceObservation.store_id,
        PriceObservation.price,
    ).join(sub, PriceObservation.id == sub.c.max_id)

    if chain_id:
        stmt = stmt.join(Store, PriceObservation.store_id == Store.id).where(
            Store.chain_id == chain_id
        )
    if category_id:
        stmt = stmt.join(Product, PriceObservation.product_id == Product.id).where(
            Product.category_id == category_id
        )

    rows = db.execute(stmt).all()
    return {(pid, sid): price for pid, sid, price in rows}


def get_latest_scrape_runs(db: Session) -> list[ScrapeRun]:
    """Get the most recent scrape run per chain."""
    sub = (
        select(
            ScrapeRun.chain_id,
            func.max(ScrapeRun.id).label("max_id"),
        )
        .where(ScrapeRun.status == "completed")
        .group_by(ScrapeRun.chain_id)
        .subquery()
    )
    stmt = select(ScrapeRun).join(sub, ScrapeRun.id == sub.c.max_id)
    return list(db.scalars(stmt).all())
