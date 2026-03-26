"""Store endpoints — list stores and per-store metrics."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from matmoms.api.deps import get_db
from matmoms.db.models import Store
from matmoms.metrics.passthrough import compute_passthrough

router = APIRouter()


@router.get("/stores")
def list_stores(
    chain: str | None = Query(None),
    comparison_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    stmt = select(Store).order_by(Store.chain_id, Store.name)
    if chain:
        stmt = stmt.where(Store.chain_id == chain)

    stores = list(db.scalars(stmt).all())
    comp_date = comparison_date or date.today()

    items = []
    for store in stores:
        result = compute_passthrough(
            db,
            comparison_date=comp_date,
            scope_type="store",
            scope_id=store.id,
        )
        items.append({
            "id": store.id,
            "name": store.name,
            "chain_id": store.chain_id,
            "city": store.city,
            "store_type": store.store_type,
            "n_products": result.n_products,
            "avg_change_pct": result.avg_change_pct,
            "median_change_pct": result.median_change_pct,
            "passthrough_pct": result.passthrough_pct,
            "n_lowered": result.n_lowered,
            "n_unchanged": result.n_unchanged,
            "n_increased": result.n_increased,
        })

    return {"stores": items}


@router.get("/stores/{store_id}/metrics")
def store_metrics(
    store_id: str,
    comparison_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    store = db.get(Store, store_id)
    if not store:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Store not found")

    comp_date = comparison_date or date.today()

    overall = compute_passthrough(
        db,
        comparison_date=comp_date,
        scope_type="store",
        scope_id=store_id,
    )

    # Per-category breakdown for this store
    from matmoms.db.models import Category
    categories = list(db.scalars(select(Category).where(Category.parent_id.is_(None))).all())

    cat_metrics = []
    for cat in categories:
        result = compute_passthrough(
            db,
            comparison_date=comp_date,
            scope_type="category",
            scope_id=cat.id,
        )
        if result.n_products > 0:
            cat_metrics.append({
                "category_id": cat.id,
                "category_name": cat.name_en,
                "n_products": result.n_products,
                "avg_change_pct": result.avg_change_pct,
                "passthrough_pct": result.passthrough_pct,
            })

    return {
        "store": {
            "id": store.id,
            "name": store.name,
            "chain_id": store.chain_id,
            "city": store.city,
        },
        "overall": {
            "n_products": overall.n_products,
            "avg_change_pct": overall.avg_change_pct,
            "median_change_pct": overall.median_change_pct,
            "passthrough_pct": overall.passthrough_pct,
            "n_lowered": overall.n_lowered,
            "n_unchanged": overall.n_unchanged,
            "n_increased": overall.n_increased,
        },
        "categories": cat_metrics,
    }
