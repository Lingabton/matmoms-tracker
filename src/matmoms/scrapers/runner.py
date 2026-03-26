"""Scrape runner — orchestrates full scrape sessions across chains and stores."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import yaml
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session

from matmoms.db.models import Product, ScrapeRun, Store
from matmoms.scrapers.coop import CoopScraper
from matmoms.scrapers.ica import IcaScraper
from matmoms.scrapers.willys import WillysScraper

logger = logging.getLogger(__name__)

CHAIN_SCRAPERS = {
    "ica": IcaScraper,
    "coop": CoopScraper,
    "willys": WillysScraper,
}


class ScrapeRunner:
    """Orchestrates scraping across chains and stores."""

    def __init__(self, db: Session, headless: bool = True):
        self.db = db
        self.headless = headless

    def _load_stores(self, chain_filter: str | None = None) -> dict[str, list[Store]]:
        """Load stores from database, grouped by chain."""
        from sqlalchemy import select

        stmt = select(Store)
        if chain_filter:
            stmt = stmt.where(Store.chain_id == chain_filter)

        stores = list(self.db.scalars(stmt).all())
        grouped: dict[str, list[Store]] = {}
        for store in stores:
            grouped.setdefault(store.chain_id, []).append(store)
        return grouped

    def _load_products(self) -> list[Product]:
        """Load all trackable products from database."""
        from sqlalchemy import select

        stmt = select(Product).where(Product.vat_applicable == True)  # noqa: E712
        return list(self.db.scalars(stmt).all())

    async def run(
        self,
        chain: str | None = None,
        store_id: str | None = None,
        dry_run: bool = False,
    ) -> list[ScrapeRun]:
        """Execute a full scrape session.

        Args:
            chain: Optional chain filter (e.g. "ica"). None = all chains.
            store_id: Optional single store to scrape.
            dry_run: If True, launch browser and select store but don't scrape products.
        """
        stores_by_chain = self._load_stores(chain)
        products = self._load_products()

        if not products:
            logger.error("No products found in database. Run 'matmoms db seed' first.")
            return []

        if store_id:
            # Filter to single store
            stores_by_chain = {
                c: [s for s in ss if s.id == store_id]
                for c, ss in stores_by_chain.items()
            }
            stores_by_chain = {c: ss for c, ss in stores_by_chain.items() if ss}

        logger.info(
            f"Starting scrape: {sum(len(v) for v in stores_by_chain.values())} stores, "
            f"{len(products)} products"
        )

        if dry_run:
            logger.info("DRY RUN — will select stores but not scrape products")
            products = products[:3]  # Only try a few products in dry run

        # Run chains in parallel, stores within a chain sequentially
        tasks = []
        for chain_id, stores in stores_by_chain.items():
            if chain_id in CHAIN_SCRAPERS:
                tasks.append(
                    self._scrape_chain(chain_id, stores, products)
                )
            else:
                logger.warning(f"No scraper for chain: {chain_id}")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_runs: list[ScrapeRun] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Chain scrape failed: {result}")
            elif isinstance(result, list):
                all_runs.extend(result)

        logger.info(
            f"Scrape complete: {len(all_runs)} store runs, "
            f"{sum(r.products_found for r in all_runs)} total observations"
        )

        return all_runs

    async def _scrape_chain(
        self,
        chain_id: str,
        stores: list[Store],
        products: list[Product],
    ) -> list[ScrapeRun]:
        """Scrape all stores for a single chain using one browser instance."""
        runs: list[ScrapeRun] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            try:
                scraper_cls = CHAIN_SCRAPERS[chain_id]

                for store in stores:
                    logger.info(f"Scraping {chain_id}: {store.name}")
                    scraper = scraper_cls(store, products, browser)

                    try:
                        run = await scraper.run(self.db)
                        runs.append(run)
                    except Exception as e:
                        logger.error(
                            f"Store scrape failed: {store.name}: {e}"
                        )

            finally:
                await browser.close()

        return runs
