"""Abstract base scraper and shared data classes."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime

from playwright.async_api import Browser, BrowserContext, Page
from sqlalchemy.orm import Session

from matmoms.db.models import PriceObservation, Product, ScrapeRun, Store

logger = logging.getLogger(__name__)


@dataclass
class RawPriceResult:
    """Raw scraped price data for a single product in a single store."""

    product_id: int
    store_id: str
    price: float | None = None
    unit_price: float | None = None
    is_campaign: bool = False
    campaign_label: str | None = None
    member_price: float | None = None
    original_price: float | None = None
    found: bool = False
    raw_data: dict = field(default_factory=dict)
    error: str | None = None


class BaseScraper(ABC):
    """Abstract scraper — one instance per store per scrape run.

    Subclasses must implement:
        - select_store: Set the active store context in the browser
        - search_product: Search for a product and extract price data
        - detect_campaign: Chain-specific logic to detect promotional prices
    """

    chain_id: str

    def __init__(self, store: Store, products: list[Product], browser: Browser):
        self.store = store
        self.products = products
        self.browser = browser
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    @abstractmethod
    async def select_store(self, page: Page) -> None:
        """Navigate to the chain site and set the active store context."""

    @abstractmethod
    async def search_product(self, page: Page, product: Product) -> RawPriceResult:
        """Search for a product and extract price data from the page."""

    @abstractmethod
    def detect_campaign(self, raw: RawPriceResult) -> bool:
        """Return True if the price observation looks like a campaign/promo."""

    def get_search_term(self, product: Product) -> str:
        """Get chain-specific search term, falling back to canonical name."""
        if product.search_terms_json:
            terms = json.loads(product.search_terms_json)
            if self.chain_id in terms:
                return terms[self.chain_id]
        return product.canonical_name

    async def run(self, db: Session) -> ScrapeRun:
        """Execute a full scrape of all products for this store.

        Template method pattern:
        1. Create browser context
        2. Navigate and select store
        3. Search each product and record observations
        4. Persist results and scrape run metadata
        """
        scrape_run = ScrapeRun(
            started_at=datetime.utcnow(),
            chain_id=self.store.chain_id,
            store_id=self.store.id,
            status="running",
        )
        db.add(scrape_run)
        db.commit()

        found = 0
        missed = 0
        start_time = datetime.utcnow()

        try:
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="sv-SE",
            )
            self.page = await self.context.new_page()

            logger.info(f"Selecting store: {self.store.name} ({self.store.id})")
            await self.select_store(self.page)

            for product in self.products:
                try:
                    result = await self.search_product(self.page, product)

                    if result.found and result.price is not None:
                        # Apply campaign detection
                        result.is_campaign = self.detect_campaign(result)

                        obs = PriceObservation(
                            product_id=result.product_id,
                            store_id=result.store_id,
                            scrape_run_id=scrape_run.id,
                            price=result.price,
                            unit_price=result.unit_price,
                            is_campaign=result.is_campaign,
                            campaign_label=result.campaign_label,
                            member_price=result.member_price,
                            original_price=result.original_price,
                            observed_at=datetime.utcnow(),
                            raw_payload=json.dumps(result.raw_data, ensure_ascii=False),
                        )
                        db.add(obs)
                        found += 1
                    else:
                        missed += 1
                        logger.warning(
                            f"Product not found: {product.canonical_name} "
                            f"in {self.store.name}"
                        )

                except Exception as e:
                    missed += 1
                    logger.error(
                        f"Error scraping {product.canonical_name} "
                        f"in {self.store.name}: {e}"
                    )

            scrape_run.status = "completed"

        except Exception as e:
            scrape_run.status = "failed"
            scrape_run.error_message = str(e)
            logger.error(f"Scrape run failed for {self.store.name}: {e}")

        finally:
            if self.context:
                await self.context.close()

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            scrape_run.finished_at = datetime.utcnow()
            scrape_run.products_found = found
            scrape_run.products_missed = missed
            scrape_run.duration_s = elapsed
            db.commit()

            logger.info(
                f"Scrape run for {self.store.name}: "
                f"{found} found, {missed} missed, {elapsed:.1f}s"
            )

        return scrape_run
