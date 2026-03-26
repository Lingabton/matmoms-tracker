"""Category endpoints — category-level metrics."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from matmoms.api.deps import get_db
from matmoms.db.models import Category
from matmoms.metrics.passthrough import compute_passthrough

router = APIRouter()


@router.get("/categories")
def list_categories(
    comparison_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    comp_date = comparison_date or date.today()
    categories = list(
        db.scalars(select(Category).where(Category.parent_id.is_(None))).all()
    )

    items = []
    for cat in categories:
        result = compute_passthrough(
            db,
            comparison_date=comp_date,
            scope_type="category",
            scope_id=cat.id,
        )
        items.append({
            "id": cat.id,
            "name_sv": cat.name_sv,
            "name_en": cat.name_en,
            "n_products": result.n_products,
            "avg_change_pct": result.avg_change_pct,
            "median_change_pct": result.median_change_pct,
            "passthrough_pct": result.passthrough_pct,
            "n_lowered": result.n_lowered,
            "n_unchanged": result.n_unchanged,
            "n_increased": result.n_increased,
        })

    return {"categories": items}


@router.get("/categories/{category_id}/metrics")
def category_metrics(
    category_id: str,
    comparison_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    cat = db.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    comp_date = comparison_date or date.today()

    result = compute_passthrough(
        db,
        comparison_date=comp_date,
        scope_type="category",
        scope_id=category_id,
    )

    # Per-chain breakdown for this category
    chain_metrics = {}
    for chain_id in ("ica", "coop", "willys"):
        # We need a combined scope here — compute with both filters
        # For now, compute at category level (includes all chains)
        chain_metrics[chain_id] = {
            "note": "per-chain category breakdown requires combined filter",
        }

    return {
        "category": {
            "id": cat.id,
            "name_sv": cat.name_sv,
            "name_en": cat.name_en,
        },
        "metrics": {
            "n_products": result.n_products,
            "avg_change_pct": result.avg_change_pct,
            "median_change_pct": result.median_change_pct,
            "p25_change_pct": result.p25_change_pct,
            "p75_change_pct": result.p75_change_pct,
            "passthrough_pct": result.passthrough_pct,
            "n_lowered": result.n_lowered,
            "n_unchanged": result.n_unchanged,
            "n_increased": result.n_increased,
            "campaign_excluded": result.campaign_excluded,
        },
        "product_changes": [
            {
                "product_id": c.product_id,
                "store_id": c.store_id,
                "baseline_price": c.baseline_price,
                "current_price": c.current_price,
                "change_pct": c.change_pct,
                "classification": c.classification,
            }
            for c in result.changes[:100]  # Cap at 100 for API response size
        ],
    }
