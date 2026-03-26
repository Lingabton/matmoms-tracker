"""Coop scraper — coop.se/handla

Coop runs a Hybris-based SPA. We attempt to use their internal API
first (via intercepted requests), falling back to DOM scraping.
"""

from __future__ import annotations

import logging
import re

from playwright.async_api import Browser, Page

from matmoms.db.models import Product, Store
from matmoms.scrapers.base import BaseScraper, RawPriceResult

logger = logging.getLogger(__name__)

COOP_BASE_URL = "https://www.coop.se/handla"
COOP_API_BASE = "https://external.api.coop.se"


class CoopScraper(BaseScraper):
    chain_id = "coop"

    def __init__(self, store: Store, products: list[Product], browser: Browser):
        super().__init__(store, products, browser)
        self._api_token: str | None = None

    async def select_store(self, page: Page) -> None:
        """Navigate to Coop and select store via postal code."""
        await page.goto(COOP_BASE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Accept cookies
        try:
            cookie_btn = page.locator(
                "button:has-text('Acceptera'), "
                "button:has-text('Godkänn')"
            )
            if await cookie_btn.first.is_visible(timeout=3000):
                await cookie_btn.first.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

        # Try to intercept API token from network requests
        async def capture_token(response):
            if "external.api.coop.se" in response.url:
                try:
                    headers = response.request.headers
                    if "authorization" in headers:
                        self._api_token = headers["authorization"]
                except Exception:
                    pass

        page.on("response", capture_token)

        # Set store via postal code
        try:
            # Look for postal code / store selector
            zip_input = page.locator(
                "input[placeholder*='postnummer'], "
                "input[placeholder*='Postnummer'], "
                "input[name*='zip'], "
                "input[aria-label*='postnummer']"
            )
            if await zip_input.first.is_visible(timeout=5000):
                await zip_input.first.fill(self.store.zip_code or "")
                await page.wait_for_timeout(1500)

                # Click search/confirm
                confirm_btn = page.locator(
                    "button:has-text('Välj'), "
                    "button:has-text('Sök'), "
                    "button[type='submit']"
                )
                await confirm_btn.first.click(timeout=3000)
                await page.wait_for_timeout(2000)

                # Select the specific store from results
                store_result = page.locator(
                    f"text=/{re.escape(self.store.name)}/i"
                )
                if await store_result.first.is_visible(timeout=3000):
                    await store_result.first.click()
                    await page.wait_for_timeout(2000)

        except Exception as e:
            logger.warning(f"Coop store selection failed: {e}")

    async def search_product(self, page: Page, product: Product) -> RawPriceResult:
        """Search for a product on Coop and extract price."""
        result = RawPriceResult(
            product_id=product.id,
            store_id=self.store.id,
        )

        search_term = self.get_search_term(product)

        # Try API-based search if we have a token
        if self._api_token:
            api_result = await self._search_via_api(page, search_term, result)
            if api_result and api_result.found:
                return api_result

        # Fallback to DOM-based search
        search_url = f"{COOP_BASE_URL}/sok?q={search_term.replace(' ', '+')}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        try:
            product_cards = page.locator(
                "[data-testid='product-card'], "
                ".product-card, "
                "[class*='ProductCard'], "
                "[class*='productCard']"
            )

            count = await product_cards.count()
            if count == 0:
                result.found = False
                return result

            card = product_cards.first

            # Extract price
            price_el = card.locator(
                "[class*='price'], [class*='Price'], "
                "[data-testid='price']"
            ).first

            price_text = await price_el.text_content(timeout=3000)
            result.raw_data["price_text"] = price_text

            price = self._parse_price(price_text)
            if price is not None:
                result.price = price
                result.found = True

            # Campaign detection
            try:
                campaign_el = card.locator(
                    "[class*='campaign'], [class*='Campaign'], "
                    "[class*='offer'], [class*='splash'], "
                    "[class*='badge'], .promotion"
                )
                if await campaign_el.count() > 0:
                    result.is_campaign = True
                    result.campaign_label = await campaign_el.first.text_content(timeout=2000)
            except Exception:
                pass

            # Original price (struck through)
            try:
                orig_el = card.locator("s, del, [class*='original'], [class*='was']")
                if await orig_el.count() > 0:
                    orig_text = await orig_el.first.text_content(timeout=2000)
                    result.original_price = self._parse_price(orig_text)
                    result.is_campaign = True
            except Exception:
                pass

            # Unit price
            try:
                unit_el = card.locator(
                    "[class*='unit'], [class*='comparison'], [class*='jmf']"
                )
                if await unit_el.count() > 0:
                    unit_text = await unit_el.first.text_content(timeout=2000)
                    result.unit_price = self._parse_price(unit_text)
                    result.raw_data["unit_price_text"] = unit_text
            except Exception:
                pass

            # Member price
            try:
                member_el = card.locator("[class*='member'], [class*='Member']")
                if await member_el.count() > 0:
                    member_text = await member_el.first.text_content(timeout=2000)
                    result.member_price = self._parse_price(member_text)
            except Exception:
                pass

            # Full card text for traceability
            try:
                result.raw_data["card_text"] = await card.text_content(timeout=2000)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error parsing Coop result for {search_term}: {e}")
            result.found = False
            result.error = str(e)

        return result

    async def _search_via_api(
        self, page: Page, search_term: str, result: RawPriceResult
    ) -> RawPriceResult | None:
        """Attempt to use Coop's internal API for product search."""
        try:
            import json

            api_url = (
                f"{COOP_API_BASE}/personalization/search/entities/by-attribute"
                f"?q={search_term}&size=1&storeId={self.store.external_id}"
            )

            response = await page.evaluate(
                """async (url) => {
                    const resp = await fetch(url, { credentials: 'include' });
                    if (resp.ok) return await resp.json();
                    return null;
                }""",
                api_url,
            )

            if response and isinstance(response, dict):
                products = response.get("results", response.get("products", []))
                if products:
                    item = products[0]
                    result.price = item.get("price", item.get("currentPrice"))
                    result.original_price = item.get("originalPrice", item.get("wasPrice"))
                    result.unit_price = item.get("comparisonPrice", item.get("unitPrice"))
                    result.raw_data = {"api_response": item}
                    result.found = result.price is not None

                    # Campaign detection from API data
                    if item.get("campaign") or item.get("promotion"):
                        result.is_campaign = True
                        result.campaign_label = item.get("campaignText", "")

                    return result

        except Exception as e:
            logger.debug(f"Coop API search failed, will use DOM: {e}")

        return None

    def detect_campaign(self, raw: RawPriceResult) -> bool:
        """Detect if a Coop price is a campaign/promo."""
        if raw.is_campaign:
            return True
        if raw.original_price and raw.price and raw.original_price > raw.price:
            return True
        if raw.campaign_label:
            return True
        return False

    @staticmethod
    def _parse_price(text: str | None) -> float | None:
        if not text:
            return None
        cleaned = re.sub(r"[^\d:,.]", "", text.strip())
        if not cleaned:
            return None
        cleaned = cleaned.replace(":", ".").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
