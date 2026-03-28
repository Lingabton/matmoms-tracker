"""Abstract base scraper and shared data classes."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from playwright.async_api import Browser, BrowserContext, Page
from sqlalchemy.orm import Session

from matmoms.db.models import PriceObservation, Product, ScrapeRun, Store
from matmoms.tz import now as _now

logger = logging.getLogger(__name__)

# Price validation bounds (SEK)
MIN_VALID_PRICE = 0.50
MAX_VALID_PRICE = 5000.0

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1.0, 3.0, 9.0]  # Exponential backoff

# Rate limiting
DEFAULT_DELAY_BETWEEN_PRODUCTS = 1.5  # seconds


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
    is_available: bool = True
    raw_data: dict = field(default_factory=dict)
    error: str | None = None


def validate_price(price: float | None) -> float | None:
    """Return price if within valid bounds, else None."""
    if price is None:
        return None
    if price < MIN_VALID_PRICE or price > MAX_VALID_PRICE:
        logger.warning(f"Price out of bounds ({price} SEK), rejecting")
        return None
    return round(price, 2)


def normalize_volume(text: str | None) -> float | None:
    """Parse a volume/weight string to a standard unit (ml or g).

    Returns milliliters for liquids, grams for weights, or None.
    Examples: '1.5L' -> 1500, '1,5l' -> 1500, '3dl' -> 300, '500g' -> 500
    """
    if not text:
        return None
    text = text.strip().lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(l|dl|cl|ml|kg|g)\b", text)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2)
    multipliers = {"l": 1000, "dl": 100, "cl": 10, "ml": 1, "kg": 1000, "g": 1}
    return value * multipliers[unit]


def best_match(
    items: list[dict],
    product: "Product",
    name_key: str = "name",
    brand_key: str | None = None,
    size_key: str | None = None,
) -> dict | None:
    """Pick the best API result for a product based on size, brand, and name.

    Args:
        items: List of API result dicts.
        product: The target Product.
        name_key: Key for product name in the API item.
        brand_key: Key for brand/manufacturer (optional).
        size_key: Key for pack size description (optional).

    Returns the best matching item, or None if no acceptable match.
    """
    if not items:
        return None

    # Parse target size from canonical name
    target_vol = normalize_volume(product.canonical_name)

    # Extract brand from canonical name (first word, typically)
    canonical_lower = product.canonical_name.lower()
    canonical_words = set(canonical_lower.split())

    # Flags from canonical name
    target_is_eko = "eko" in canonical_words or "ekologisk" in canonical_words
    target_is_laktosfri = "laktosfri" in canonical_lower

    scored: list[tuple[float, int, dict]] = []

    for idx, item in enumerate(items):
        score = 0.0
        item_name = (item.get(name_key) or "").lower()

        # --- Size match (most important) ---
        if size_key and target_vol:
            item_size = item.get(size_key)
            item_vol = normalize_volume(item_size)
            if item_vol and target_vol:
                ratio = item_vol / target_vol
                if 0.9 <= ratio <= 1.1:
                    score += 50  # Size matches
                elif 0.5 <= ratio <= 2.0:
                    score -= 20  # Close but wrong size
                else:
                    score -= 100  # Way off

        # --- Brand match ---
        if brand_key:
            item_brand = (item.get(brand_key) or "").lower()
            # Check if target brand appears in API brand
            # Extract brand from canonical: first word(s) before product type
            brand_words = []
            for w in product.canonical_name.split():
                if w.lower() in ("mjölk", "smör", "ost", "ägg", "bröd", "socker",
                                  "standardmjölk", "mellanmjölk", "lättmjölk",
                                  "filmjölk", "yoghurt", "grädde", "gräddfil"):
                    break
                brand_words.append(w.lower())

            if brand_words:
                brand_str = " ".join(brand_words)
                if brand_str in item_brand or any(w in item_brand for w in brand_words):
                    score += 30

        # --- Eko/Laktosfri penalty ---
        item_is_eko = "eko" in item_name or "ekologisk" in item_name
        item_is_laktosfri = "laktosfri" in item_name

        if item_is_eko != target_is_eko:
            score -= 40  # Organic mismatch
        if item_is_laktosfri != target_is_laktosfri:
            score -= 40  # Lactose-free mismatch

        # --- Name keyword overlap ---
        item_words = set(item_name.split())
        overlap = len(canonical_words & item_words)
        score += overlap * 5

        # --- Position penalty (prefer earlier results) ---
        score -= idx * 0.5

        scored.append((score, idx, item))

    if not scored:
        return None

    # Sort by score descending
    scored.sort(key=lambda x: (-x[0], x[1]))
    best_score, best_idx, best_item = scored[0]

    # Reject if score is very negative (terrible match)
    if best_score < -50:
        best_name = best_item.get(name_key, "?")
        logger.debug(
            f"Rejected best match '{best_name}' (score={best_score:.0f}) "
            f"for '{product.canonical_name}'"
        )
        return None

    return best_item


class BaseScraper(ABC):
    """Abstract scraper — one instance per store per scrape run.

    Subclasses must implement:
        - select_store: Set the active store context in the browser
        - search_product: Search for a product and extract price data
        - detect_campaign: Chain-specific logic to detect promotional prices
    """

    chain_id: str
    delay_between_products: float = DEFAULT_DELAY_BETWEEN_PRODUCTS

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

    async def _search_with_retry(self, page: Page, product: Product) -> RawPriceResult:
        """Search for a product with retry logic and exponential backoff."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                result = await self.search_product(page, product)
                if result.found:
                    return result
                # Not found is not an error — don't retry
                if not result.error:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)

            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.debug(
                    f"Retry {attempt + 1}/{MAX_RETRIES} for "
                    f"{product.canonical_name} after {delay}s"
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        return RawPriceResult(
            product_id=product.id,
            store_id=self.store.id,
            found=False,
            error=f"Failed after {MAX_RETRIES} attempts: {last_error}",
        )

    async def run(self, db: Session) -> ScrapeRun:
        """Execute a full scrape of all products for this store.

        Template method:
        1. Create browser context
        2. Navigate and select store
        3. Search each product with retry logic
        4. Validate and persist results
        """
        scrape_run = ScrapeRun(
            started_at=_now(),
            chain_id=self.store.chain_id,
            store_id=self.store.id,
            status="running",
        )
        db.add(scrape_run)
        db.commit()

        found = 0
        missed = 0
        start_time = _now()

        try:
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="sv-SE",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            self.page = await self.context.new_page()
            await self.page.add_init_script(
                'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            )

            logger.info(f"Selecting store: {self.store.name} ({self.store.id})")
            await self.select_store(self.page)

            for i, product in enumerate(self.products):
                try:
                    result = await self._search_with_retry(self.page, product)

                    # Validate price
                    if result.found and result.price is not None:
                        result.price = validate_price(result.price)
                        result.unit_price = validate_price(result.unit_price)
                        result.member_price = validate_price(result.member_price)
                        result.original_price = validate_price(result.original_price)

                    if result.found and result.price is not None:
                        result.is_campaign = self.detect_campaign(result)

                        obs = PriceObservation(
                            product_id=result.product_id,
                            store_id=result.store_id,
                            scrape_run_id=scrape_run.id,
                            price=result.price,
                            unit_price=result.unit_price,
                            is_available=True,
                            is_campaign=result.is_campaign,
                            campaign_label=result.campaign_label,
                            member_price=result.member_price,
                            original_price=result.original_price,
                            observed_at=_now(),
                            raw_payload=json.dumps(result.raw_data, ensure_ascii=False),
                        )
                        db.add(obs)
                        found += 1
                    else:
                        # Record unavailability for traceability
                        obs = PriceObservation(
                            product_id=product.id,
                            store_id=self.store.id,
                            scrape_run_id=scrape_run.id,
                            price=None,
                            is_available=False,
                            observed_at=_now(),
                            raw_payload=json.dumps(
                                {"error": result.error, "raw": result.raw_data},
                                ensure_ascii=False,
                            ),
                        )
                        db.add(obs)
                        missed += 1
                        logger.warning(
                            f"Not found: {product.canonical_name} "
                            f"in {self.store.name}"
                        )

                except Exception as e:
                    missed += 1
                    logger.error(
                        f"Error scraping {product.canonical_name} "
                        f"in {self.store.name}: {e}"
                    )

                # Rate limiting between products
                if i < len(self.products) - 1:
                    await asyncio.sleep(self.delay_between_products)

            scrape_run.status = "completed"

        except Exception as e:
            scrape_run.status = "failed"
            scrape_run.error_message = str(e)
            logger.error(f"Scrape run failed for {self.store.name}: {e}")

        finally:
            if self.context:
                await self.context.close()

            elapsed = (_now() - start_time).total_seconds()
            scrape_run.finished_at = _now()
            scrape_run.products_found = found
            scrape_run.products_missed = missed
            scrape_run.duration_s = elapsed
            db.commit()

            total = found + missed
            hitrate = (found / total * 100) if total > 0 else 0
            level = logging.ERROR if hitrate < 50 and total > 0 else logging.INFO
            logger.log(
                level,
                f"{self.store.chain_id} {self.store.name}: "
                f"{found}/{total} products ({hitrate:.0f}% hitrate), "
                f"{elapsed:.1f}s",
            )

        return scrape_run
