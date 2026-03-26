"""Export endpoints — CSV and raw data for journalistic transparency."""

import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from matmoms.api.deps import get_db
from matmoms.db.models import PriceObservation, Product, Store

router = APIRouter()


@router.get("/export/csv")
def export_csv(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    chain: str | None = Query(None),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Export price observations as CSV."""
    stmt = (
        select(PriceObservation)
        .join(Product, PriceObservation.product_id == Product.id)
        .join(Store, PriceObservation.store_id == Store.id)
        .order_by(PriceObservation.observed_at)
    )

    if from_date:
        stmt = stmt.where(
            PriceObservation.observed_at >= datetime.combine(from_date, datetime.min.time())
        )
    if to_date:
        stmt = stmt.where(
            PriceObservation.observed_at <= datetime.combine(to_date, datetime.max.time())
        )
    if chain:
        stmt = stmt.where(Store.chain_id == chain)
    if category:
        stmt = stmt.where(Product.category_id == category)

    observations = list(db.scalars(stmt).all())

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "observed_at",
        "product_id",
        "product_name",
        "brand",
        "category",
        "ean",
        "store_id",
        "chain_id",
        "store_name",
        "city",
        "price",
        "unit_price",
        "is_campaign",
        "campaign_label",
        "member_price",
        "original_price",
    ])

    for obs in observations:
        writer.writerow([
            obs.observed_at.isoformat(),
            obs.product_id,
            obs.product.canonical_name,
            obs.product.brand,
            obs.product.category_id,
            obs.product.ean,
            obs.store_id,
            obs.store.chain_id,
            obs.store.name,
            obs.store.city,
            obs.price,
            obs.unit_price,
            obs.is_campaign,
            obs.campaign_label,
            obs.member_price,
            obs.original_price,
        ])

    output.seek(0)
    filename = f"matmoms_export_{date.today().isoformat()}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/observations")
def export_observations(
    limit: int = Query(1000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Export raw observations as JSON for programmatic access."""
    stmt = (
        select(PriceObservation)
        .order_by(PriceObservation.observed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    observations = list(db.scalars(stmt).all())

    return {
        "count": len(observations),
        "offset": offset,
        "observations": [
            {
                "id": obs.id,
                "product_id": obs.product_id,
                "store_id": obs.store_id,
                "price": obs.price,
                "unit_price": obs.unit_price,
                "is_campaign": obs.is_campaign,
                "campaign_label": obs.campaign_label,
                "member_price": obs.member_price,
                "original_price": obs.original_price,
                "observed_at": obs.observed_at.isoformat(),
                "raw_payload": obs.raw_payload,
            }
            for obs in observations
        ],
    }
