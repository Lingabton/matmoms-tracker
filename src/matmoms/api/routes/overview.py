"""Overview endpoint — headline pass-through numbers."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from matmoms.api.deps import get_db
from matmoms.metrics.passthrough import compute_passthrough, THEORETICAL_CHANGE_PCT

router = APIRouter()

VAT_CUT_DATE = date(2026, 4, 1)


@router.get("/overview")
def overview(
    comparison_date: date | None = Query(None, description="Date to compare (default: today)"),
    exclude_campaigns: bool = Query(True, description="Exclude campaign prices"),
    db: Session = Depends(get_db),
):
    from matmoms.tz import today as _today
    comp_date = comparison_date or _today()
    days_since_cut = (comp_date - VAT_CUT_DATE).days

    # National aggregate
    national = compute_passthrough(
        db, comparison_date=comp_date, exclude_campaigns=exclude_campaigns
    )

    # Per-chain
    chains = {}
    for chain_id in ("ica", "coop", "willys"):
        result = compute_passthrough(
            db,
            comparison_date=comp_date,
            scope_type="chain",
            scope_id=chain_id,
            exclude_campaigns=exclude_campaigns,
        )
        chains[chain_id] = {
            "n_products": result.n_products,
            "avg_change_pct": result.avg_change_pct,
            "median_change_pct": result.median_change_pct,
            "passthrough_pct": result.passthrough_pct,
            "n_lowered": result.n_lowered,
            "n_unchanged": result.n_unchanged,
            "n_increased": result.n_increased,
        }

    # Per-format (stor vs liten across all chains)
    from matmoms.db.models import Store
    from sqlalchemy import select

    LARGE_FORMATS = {"maxi", "stor", "willys", "kvantum"}
    SMALL_FORMATS = {"nara", "liten", "hemma"}

    all_stores = list(db.scalars(select(Store)).all())
    large_ids = [s.id for s in all_stores if s.store_type in LARGE_FORMATS]
    small_ids = [s.id for s in all_stores if s.store_type in SMALL_FORMATS]

    formats = {}
    for label, store_ids in [("large", large_ids), ("small", small_ids)]:
        if not store_ids:
            continue
        result = compute_passthrough(
            db,
            comparison_date=comp_date,
            scope_type="format",
            scope_id=label,
            exclude_campaigns=exclude_campaigns,
            store_ids=store_ids,
        )
        formats[label] = {
            "store_types": list(LARGE_FORMATS if label == "large" else SMALL_FORMATS),
            "n_stores": len(store_ids),
            "n_products": result.n_products,
            "avg_change_pct": result.avg_change_pct,
            "median_change_pct": result.median_change_pct,
            "passthrough_pct": result.passthrough_pct,
            "n_lowered": result.n_lowered,
            "n_unchanged": result.n_unchanged,
            "n_increased": result.n_increased,
        }

    return {
        "comparison_date": comp_date.isoformat(),
        "baseline_date": national.baseline_date,
        "days_since_vat_cut": days_since_cut,
        "theoretical_change_pct": THEORETICAL_CHANGE_PCT,
        "national": {
            "n_products": national.n_products,
            "avg_change_pct": national.avg_change_pct,
            "median_change_pct": national.median_change_pct,
            "p25_change_pct": national.p25_change_pct,
            "p75_change_pct": national.p75_change_pct,
            "passthrough_pct": national.passthrough_pct,
            "n_lowered": national.n_lowered,
            "n_unchanged": national.n_unchanged,
            "n_increased": national.n_increased,
            "share_lowered_pct": round(
                national.n_lowered / national.n_products * 100, 1
            ) if national.n_products else 0,
            "campaign_excluded": national.campaign_excluded,
        },
        "chains": chains,
        "formats": formats,
    }
