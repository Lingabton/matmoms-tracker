"""Product endpoints — list products and price history."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from matmoms.api.deps import get_db
from matmoms.db.models import PriceObservation, Product, Store

router = APIRouter()


@router.get("/products")
def list_products(
    chain: str | None = Query(None),
    category: str | None = Query(None),
    campaign: str = Query("exclude", pattern="^(include|exclude|only)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Product).order_by(Product.canonical_name)

    if category:
        stmt = stmt.where(Product.category_id == category)

    total = db.scalar(
        select(func.count()).select_from(stmt.subquery())
    )

    products = list(db.scalars(stmt.offset(offset).limit(limit)).all())

    items = []
    for p in products:
        # Get latest observation
        obs_stmt = (
            select(PriceObservation)
            .where(PriceObservation.product_id == p.id)
            .order_by(PriceObservation.observed_at.desc())
        )
        if campaign == "exclude":
            obs_stmt = obs_stmt.where(PriceObservation.is_campaign == False)  # noqa: E712
        elif campaign == "only":
            obs_stmt = obs_stmt.where(PriceObservation.is_campaign == True)  # noqa: E712

        if chain:
            obs_stmt = obs_stmt.join(Store).where(Store.chain_id == chain)

        obs_stmt = obs_stmt.limit(1)
        latest = db.scalar(obs_stmt)

        items.append({
            "id": p.id,
            "canonical_name": p.canonical_name,
            "brand": p.brand,
            "category_id": p.category_id,
            "ean": p.ean,
            "unit_quantity": p.unit_quantity,
            "unit_type": p.unit_type,
            "latest_price": latest.price if latest else None,
            "latest_store": latest.store_id if latest else None,
            "latest_date": latest.observed_at.isoformat() if latest else None,
            "is_campaign": latest.is_campaign if latest else None,
        })

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


@router.get("/products/{product_id}/history")
def product_history(
    product_id: int,
    store_id: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    from datetime import datetime

    stmt = (
        select(PriceObservation)
        .where(PriceObservation.product_id == product_id)
        .order_by(PriceObservation.observed_at)
    )

    if store_id:
        stmt = stmt.where(PriceObservation.store_id == store_id)
    if from_date:
        stmt = stmt.where(
            PriceObservation.observed_at >= datetime.combine(from_date, datetime.min.time())
        )
    if to_date:
        stmt = stmt.where(
            PriceObservation.observed_at <= datetime.combine(to_date, datetime.max.time())
        )

    observations = list(db.scalars(stmt).all())

    product = db.get(Product, product_id)

    return {
        "product": {
            "id": product.id,
            "canonical_name": product.canonical_name,
            "brand": product.brand,
            "category_id": product.category_id,
        } if product else None,
        "observations": [
            {
                "date": obs.observed_at.isoformat(),
                "store_id": obs.store_id,
                "price": obs.price,
                "unit_price": obs.unit_price,
                "is_campaign": obs.is_campaign,
                "campaign_label": obs.campaign_label,
                "member_price": obs.member_price,
                "original_price": obs.original_price,
            }
            for obs in observations
        ],
    }
