"""Materialized metric snapshots — precomputed aggregates stored in DB."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from matmoms.db.models import Category, Chain, MetricSnapshot, Store
from matmoms.metrics.passthrough import PassthroughResult, compute_passthrough

logger = logging.getLogger(__name__)


def materialize_snapshots(
    db: Session,
    comparison_date: date | None = None,
    baseline_end: date = date(2026, 3, 31),
) -> list[MetricSnapshot]:
    """Compute and store metric snapshots at all scope levels.

    Creates snapshots for:
    - National aggregate
    - Per-chain (ica, coop, willys)
    - Per-store (all stores)
    - Per-category (all categories)
    """
    if comparison_date is None:
        comparison_date = date.today()

    snapshots: list[MetricSnapshot] = []
    period_label = comparison_date.isoformat()

    # 1. National
    result = compute_passthrough(
        db,
        baseline_end=baseline_end,
        comparison_date=comparison_date,
        scope_type="national",
    )
    snap = _result_to_snapshot(result, period_label)
    if snap:
        snapshots.append(snap)

    # 2. Per chain
    chains = list(db.scalars(select(Chain)).all())
    for chain in chains:
        result = compute_passthrough(
            db,
            baseline_end=baseline_end,
            comparison_date=comparison_date,
            scope_type="chain",
            scope_id=chain.id,
        )
        snap = _result_to_snapshot(result, period_label)
        if snap:
            snapshots.append(snap)

    # 3. Per store
    stores = list(db.scalars(select(Store)).all())
    for store in stores:
        result = compute_passthrough(
            db,
            baseline_end=baseline_end,
            comparison_date=comparison_date,
            scope_type="store",
            scope_id=store.id,
        )
        snap = _result_to_snapshot(result, period_label)
        if snap:
            snapshots.append(snap)

    # 4. Per category
    categories = list(db.scalars(select(Category)).all())
    for cat in categories:
        result = compute_passthrough(
            db,
            baseline_end=baseline_end,
            comparison_date=comparison_date,
            scope_type="category",
            scope_id=cat.id,
        )
        snap = _result_to_snapshot(result, period_label)
        if snap:
            snapshots.append(snap)

    # Persist all snapshots
    for snap in snapshots:
        db.add(snap)
    db.commit()

    logger.info(f"Materialized {len(snapshots)} metric snapshots for {period_label}")
    return snapshots


def _result_to_snapshot(
    result: PassthroughResult, period_label: str
) -> MetricSnapshot | None:
    """Convert a PassthroughResult into a MetricSnapshot ORM object."""
    if result.n_products == 0:
        return None

    # Build detail JSON with distribution data
    detail = {
        "share_lowered_pct": round(result.n_lowered / result.n_products * 100, 1),
        "share_unchanged_pct": round(result.n_unchanged / result.n_products * 100, 1),
        "share_increased_pct": round(result.n_increased / result.n_products * 100, 1),
    }

    return MetricSnapshot(
        computed_at=datetime.utcnow(),
        scope_type=result.scope_type,
        scope_id=result.scope_id,
        period_label=period_label,
        baseline_date=result.baseline_date,
        comparison_date=result.comparison_date,
        n_products=result.n_products,
        n_lowered=result.n_lowered,
        n_unchanged=result.n_unchanged,
        n_increased=result.n_increased,
        avg_change_pct=result.avg_change_pct,
        median_change_pct=result.median_change_pct,
        p25_change_pct=result.p25_change_pct,
        p75_change_pct=result.p75_change_pct,
        passthrough_pct=result.passthrough_pct,
        campaign_excluded=result.campaign_excluded,
        detail_json=json.dumps(detail),
    )
