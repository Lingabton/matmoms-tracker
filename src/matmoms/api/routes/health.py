"""Health check endpoint."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from matmoms.api.deps import get_db
from matmoms.db.queries import get_latest_scrape_runs

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    runs = get_latest_scrape_runs(db)
    chain_status = {}
    for run in runs:
        chain_status[run.chain_id] = {
            "last_scrape": run.finished_at.isoformat() if run.finished_at else None,
            "status": run.status,
            "products_found": run.products_found,
            "products_missed": run.products_missed,
        }

    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "chains": chain_status,
    }
