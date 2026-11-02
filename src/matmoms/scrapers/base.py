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

from sqlalchemy import func, select

from matmoms.db.models import PriceObservation, Product, ScrapeRun, Store
from matmoms.tz import now as _now

logger = logging.getLogger(__name__)

# Price validation bounds (SEK)
MIN_VALID_PRICE = 0.50
MAX_VALID_PRICE = 500.0  # No tracked grocery item should exceed 500 SEK

# Price volatility threshold — reject if price deviates more than this
# fraction from the historical median for the same product+store.
PRICE_DEVIATION_THRESHOLD = 0.60  # 60%

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


def _extract_brand(canonical_name: str) -> str:
    """Extract brand from canonical product name (first word(s) before product type or size)."""
    product_type_words = {
        "mjölk", "smör", "ost", "ägg", "bröd", "socker", "pasta", "ris",
        "standardmjölk", "mellanmjölk", "lättmjölk", "minimjölk",
        "filmjölk", "yoghurt", "grädde", "gräddfil", "crème", "cream",
        "sill", "sardiner", "korv", "skinka", "färs", "filé", "bitar",
        "fläskkarré", "fläskkotletter", "kotletter", "kassler", "julskinka",
        "nötfärs", "högrev", "falukorv",
        "knäckebröd", "müsli", "havrefrön", "flingor", "limpa",
        "ketchup", "senap", "majonäs", "tacokrydda", "tacosås",
        "lingonsylt", "senap",
        "chips", "naturchips", "dip", "godis", "choklad", "glass",
        "digestive", "schweizernöt", "japp", "sandwich",
        "juice", "läsk", "vatten", "dryck", "havredryck",
        "apelsinjuice", "äppeljuice",
        "blöjor", "kikärtor", "kidneybönor", "tomater", "potatis",
        "äpplen", "bananer", "apelsiner", "vitlök", "tomat",
        "paprika", "rödlök", "zucchini", "broccoli", "majs",
        "haricots", "granatäpple",
        "riven", "skivad", "kokt", "rökt", "strimlad", "gravad",
        "gratäng", "fiskgratäng", "nuggets", "stroganoff",
        "sesamolja", "vaniljsocker",
        "pastasås", "olivolja", "rapsolja",
    }
    words = []
    for w in canonical_name.split():
        wl = w.lower()
        if wl in product_type_words:
            break
        # Stop at size patterns like "1.5L", "500g", "200ml", "3%"
        if re.match(r"^\d+(?:[.,]\d+)?(?:l|dl|cl|ml|kg|g|%)$", wl):
            break
        # Stop at pack patterns like "6-pack", "8-pack"
        if re.match(r"^\d+-?pack$", wl):
            break
        words.append(w)
    return " ".join(words).lower() if words else ""


def _normalize_brand(text: str) -> str:
    """Normalize brand text for comparison: strip ®, ™, trailing suffixes."""
    text = text.lower().strip()
    text = re.sub(r"[®™©]", "", text)
    # Strip common suffixes: "Arla Ko" -> "Arla", "Arla Köket" -> "Arla"
    text = re.sub(r"\s+(ko|köket|foods?)$", "", text)
    return text.strip()


def best_match(
    items: list[dict],
    product: "Product",
    name_key: str = "name",
    brand_key: str | None = None,
    size_key: str | None = None,
) -> dict | None:
    """Pick the best API result with triple-check validation and size fallback.

    Hard gates (any failure = reject):
    1. BRAND: Must match (mandatory for branded products)
    2. VARIANT: Eko/Laktosfri must match exactly

    Size matching is tiered:
    - Strict: ±25% → full score bonus
    - Flexible: any size with strong brand+name match → reduced score
    """
    if not items:
        return None

    # Parse target attributes from canonical name
    canonical = product.canonical_name
    canonical_lower = canonical.lower()
    target_vol = normalize_volume(canonical)
    target_brand = _normalize_brand(_extract_brand(canonical))

    # Strip size/percentage from canonical for keyword matching
    canonical_clean = re.sub(r"\s+\d+(?:[.,]\d+)?\s*(?:L|l|dl|cl|ml|kg|g)\s*$", "", canonical_lower)
    canonical_clean = re.sub(r"\s+\d+(?:[.,]\d+)?%", "", canonical_clean)
    # Also strip pack counts like "6-pack"
    canonical_clean = re.sub(r"\s+\d+-?pack\s*$", "", canonical_clean)
    canonical_keywords = {w for w in canonical_clean.split() if len(w) > 1}

    # Variant flags
    target_is_eko = any(w in canonical_lower.split() for w in ("eko", "ekologisk", "ekologiska"))
    target_is_laktosfri = "laktosfri" in canonical_lower
    target_is_light = any(w in canonical_lower for w in ("lätt", "light", "0.5%", "0.1%"))

    candidates: list[tuple[float, int, dict, str, bool]] = []

    for idx, item in enumerate(items):
        item_name = (item.get(name_key) or "").lower()
        item_brand_raw = (item.get(brand_key) or "") if brand_key else ""
        item_brand = _normalize_brand(item_brand_raw)
        item_size_raw = item.get(size_key) if size_key else None

        reject_reason = ""

        # === CHECK 1: BRAND ===
        if target_brand:
            brand_found = False
            target_brand_words = {bw for bw in target_brand.split() if len(bw) > 2}
            item_brand_words = {bw for bw in item_brand.split() if len(bw) > 2}
            if item_brand_words and target_brand_words:
                # Word-level overlap between brand fields
                brand_found = bool(target_brand_words & item_brand_words)
            # Reverse check: API brand words appear in our canonical name
            if not brand_found and item_brand_words:
                brand_found = any(bw in canonical_lower for bw in item_brand_words)
            # Check if our brand words appear in API product name
            if not brand_found and target_brand_words:
                brand_found = any(bw in item_name for bw in target_brand_words)
            if not brand_found:
                reject_reason = f"brand mismatch: target='{target_brand}', got='{item_brand}' / '{item_name[:40]}'"

        # === CHECK 2: VARIANT (eko, laktosfri, light must match exactly) ===
        if not reject_reason:
            item_is_eko = any(w in item_name.split() for w in ("eko", "ekologisk", "ekologiska"))
            item_is_laktosfri = "laktosfri" in item_name
            item_is_light = any(w in item_name for w in ("lätt", "light"))

            if item_is_eko != target_is_eko:
                reject_reason = f"eko mismatch: target={target_is_eko}, got={item_is_eko}"
            elif item_is_laktosfri != target_is_laktosfri:
                reject_reason = f"laktosfri mismatch: target={target_is_laktosfri}, got={item_is_laktosfri}"
            # Only check light for dairy products
            elif target_is_light != item_is_light and any(
                w in canonical_lower for w in ("mjölk", "fil", "yoghurt", "grädde")
            ):
                reject_reason = f"light mismatch: target={target_is_light}, got={item_is_light}"

        if reject_reason:
            logger.debug(
                f"Rejected '{item_name[:50]}' for '{canonical}': {reject_reason}"
            )
            continue

        # === SCORING (candidates passed brand + variant checks) ===
        score = 0.0
        size_verified = False

        # Size scoring (tiered, not a hard gate)
        if target_vol and size_key:
            item_vol = normalize_volume(item_size_raw)
            if item_vol:
                ratio = item_vol / target_vol
                if 0.75 <= ratio <= 1.25:
                    # Strict match — strong bonus
                    size_verified = True
                    score += 50
                elif 0.40 <= ratio <= 2.5:
                    # Flexible match — nearby size, penalized
                    score -= 30
                else:
                    # Too far — heavy penalty
                    score -= 100

        # Name keyword overlap
        item_keywords = {w for w in item_name.split() if len(w) > 1}
        overlap = len(canonical_keywords & item_keywords)
        # Non-brand overlap: keywords that match beyond just the brand name
        non_brand_overlap = len(
            (canonical_keywords - {target_brand} - set(target_brand.split()))
            & item_keywords
        )
        score += overlap * 10

        # Require minimum confidence:
        # - Size verified: need non-brand keyword overlap OR strong total overlap
        # - Size not verified: need at least 1 keyword overlap total
        if size_verified and non_brand_overlap < 1 and overlap < 2:
            logger.debug(
                f"Rejected '{item_name[:50]}' for '{canonical}': "
                f"only brand overlap, no product match"
            )
            continue
        if not size_verified and overlap < 1:
            logger.debug(
                f"Rejected '{item_name[:50]}' for '{canonical}': "
                f"weak match (size_verified={size_verified}, overlap={overlap})"
            )
            continue

        # Position preference (earlier results are usually more relevant)
        score -= idx * 0.5

        candidates.append((score, idx, item, item_name, size_verified))

    if not candidates:
        logger.debug(f"No valid match for '{canonical}' among {len(items)} results")
        return None

    # Sort by score descending
    candidates.sort(key=lambda x: (-x[0], x[1]))
    best_score, _, best_item, best_name, best_size_verified = candidates[0]

    # Reject if best score is too low (weak match)
    if best_score < -20:
        logger.debug(
            f"Rejected best match '{best_name}' (score={best_score:.0f}) for '{canonical}'"
        )
        return None

    tag = "verified" if best_size_verified else "FLEX-SIZE"
    logger.debug(
        f"Matched '{canonical}' -> '{best_name}' (score={best_score:.0f}, "
        f"{len(candidates)}/{len(items)} passed, {tag})"
    )

    return best_item


def _trim_payload(raw_data: dict) -> dict:
    """Keep only essential fields from raw_data to save storage.

    Full API responses are ~5KB each; we only need ~150 bytes for traceability.
    """
    trimmed: dict = {}
    if "api_item" in raw_data:
        item = raw_data["api_item"]
        trimmed["api_item"] = {
            k: item[k] for k in ("name", "ean") if k in item
        }
        # Keep brand from whichever key exists
        for bk in ("brand", "manufacturerName"):
            if bk in item:
                trimmed["api_item"][bk] = item[bk]
                break
        # Keep size info
        for sk in ("packSizeDescription", "packageSizeInformation", "packageSize"):
            if sk in item:
                trimmed["api_item"][sk] = item[sk]
                break
        # Keep country of origin
        for ok in ("countryOfOriginCodes", "fromSweden", "countryOfOrigin"):
            if ok in item:
                trimmed["api_item"][ok] = item[ok]
    # Keep non-item keys (api_url, vat_percent, etc.) as-is — they're small
    for k, v in raw_data.items():
        if k != "api_item":
            trimmed[k] = v
    return trimmed


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
        self._median_prices: dict[int, float] = {}  # product_id -> median price

    def _load_median_prices(self, db: Session) -> None:
        """Load historical median prices for this store to detect anomalies."""
        product_ids = [p.id for p in self.products]
        if not product_ids:
            return

        # Use SQL to compute median via percentile approximation (average of
        # middle values). SQLite doesn't have a native MEDIAN, so we use a
        # subquery approach grouped by product.
        rows = db.execute(
            select(
                PriceObservation.product_id,
                func.avg(PriceObservation.price),
                func.count(PriceObservation.price),
            )
            .where(
                PriceObservation.store_id == self.store.id,
                PriceObservation.product_id.in_(product_ids),
                PriceObservation.price.isnot(None),
            )
            .group_by(PriceObservation.product_id)
        ).all()

        self._median_prices = {
            row[0]: row[1] for row in rows if row[2] >= 5  # need ≥5 obs
        }
        logger.debug(
            f"Loaded median prices for {len(self._median_prices)} products "
            f"at {self.store.id}"
        )

    def _check_price_deviation(
        self, product: Product, price: float
    ) -> bool:
        """Return True if price is within acceptable range of historical median.

        Returns True (accept) if no historical data exists yet.
        """
        median = self._median_prices.get(product.id)
        if median is None:
            return True  # No history, accept

        deviation = abs(price - median) / median
        if deviation > PRICE_DEVIATION_THRESHOLD:
            logger.warning(
                f"Price anomaly for {product.canonical_name} at {self.store.id}: "
                f"{price} SEK vs median {median:.2f} SEK "
                f"({deviation:.0%} deviation) — skipping"
            )
            return False
        return True

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
            self._load_median_prices(db)
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
                        if not self._check_price_deviation(product, result.price):
                            missed += 1
                            continue

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
                            raw_payload=json.dumps(
                                _trim_payload(result.raw_data), ensure_ascii=False
                            ),
                        )
                        db.add(obs)
                        found += 1
                    else:
                        # Log but don't store missed observations
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
