"""Test fixtures."""

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from matmoms.db.models import (
    Base,
    Category,
    Chain,
    PriceObservation,
    Product,
    ScrapeRun,
    Store,
)


def _seed_db(db: Session) -> None:
    """Populate a database session with test data."""
    # Chains
    for cid, name, url in [
        ("ica", "ICA", "https://handla.ica.se"),
        ("coop", "Coop", "https://www.coop.se/handla"),
        ("willys", "Willys", "https://www.willys.se"),
    ]:
        db.add(Chain(id=cid, name=name, base_url=url))

    # Categories
    db.add(Category(id="dairy", name_sv="Mejeri", name_en="Dairy"))
    db.add(Category(id="dairy-milk", name_sv="Mjölk", name_en="Milk", parent_id="dairy"))
    db.add(Category(id="meat", name_sv="Kött", name_en="Meat"))

    # Stores
    db.add(Store(id="ica-test", chain_id="ica", name="ICA Test", city="Stockholm", store_type="maxi"))
    db.add(Store(id="coop-test", chain_id="coop", name="Coop Test", city="Stockholm", store_type="stor"))

    # Products
    p1 = Product(canonical_name="Arla Mjölk 3% 1.5L", ean="7310865001726", category_id="dairy-milk", brand="Arla", unit_quantity=1.5, unit_type="L")
    p2 = Product(canonical_name="Scan Köttfärs 500g", ean="7300156001234", category_id="meat", brand="Scan", unit_quantity=500, unit_type="g")
    db.add(p1)
    db.add(p2)
    db.commit()

    # Scrape runs and observations — baseline period (March 25-31)
    for day_offset in range(7):
        dt = datetime(2026, 3, 25, 10, 0, 0) + timedelta(days=day_offset)

        for store_id in ["ica-test", "coop-test"]:
            chain_id = store_id.split("-")[0]
            run = ScrapeRun(
                started_at=dt,
                finished_at=dt,
                chain_id=chain_id,
                store_id=store_id,
                status="completed",
                products_found=2,
            )
            db.add(run)
            db.commit()

            # Milk: 18.90 baseline
            db.add(PriceObservation(
                product_id=p1.id, store_id=store_id, scrape_run_id=run.id,
                price=18.90, observed_at=dt, is_campaign=False,
            ))
            # Meat: 49.90 baseline
            db.add(PriceObservation(
                product_id=p2.id, store_id=store_id, scrape_run_id=run.id,
                price=49.90, observed_at=dt, is_campaign=False,
            ))

    # Post-cut observations (April 2) — prices lowered by ~5%
    post_dt = datetime(2026, 4, 2, 10, 0, 0)
    for store_id in ["ica-test", "coop-test"]:
        chain_id = store_id.split("-")[0]
        run = ScrapeRun(
            started_at=post_dt, finished_at=post_dt,
            chain_id=chain_id, store_id=store_id,
            status="completed", products_found=2,
        )
        db.add(run)
        db.commit()

        # Milk: 17.90 (-5.29%)
        db.add(PriceObservation(
            product_id=p1.id, store_id=store_id, scrape_run_id=run.id,
            price=17.90, observed_at=post_dt, is_campaign=False,
        ))
        # Meat: 49.90 (unchanged)
        db.add(PriceObservation(
            product_id=p2.id, store_id=store_id, scrape_run_id=run.id,
            price=49.90, observed_at=post_dt, is_campaign=False,
        ))

    db.commit()


@pytest.fixture
def db():
    """In-memory SQLite database with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def seeded_db(db):
    """Database with sample data."""
    _seed_db(db)
    return db
