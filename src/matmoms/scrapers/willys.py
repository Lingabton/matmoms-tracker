"""Willys scraper — willys.se

Willys is part of the Axfood group (same platform as Hemköp).
The SPA often has an underlying API at /search/... or /api/...
We attempt to intercept that, falling back to DOM scraping.
"""

from __future__ import annotations

import json
import logging
import re

from playwright.async_api import Browser, Page, Response

from matmoms.db.models import Product, Store
from matmoms.scrapers.base import BaseScraper, RawPriceResult

logger = logging.getLogger(__name__)

WILLYS_BASE_URL = "https://www.willys.se"


class WillysScraper(BaseScraper):
    chain_id = "willys"

    def __init__(self, store: Store, products: list[Product], browser: Browser):
        super().__init__(store, products, browser)
        self._api_responses: dict[str, dict] = {}

    async def select_store(self, page: Page) -> None:
        """Navigate to Willys and select the store."""
        # Intercept API responses
        async def capture_api(response: Response):
            if "/search/" in response.url or "/api/" in response.url:
                try:
                    if "application/json" in (response.headers.get("content-type", "")):
                        data = await response.json()
                        self._api_responses[response.url] = data
                except Exception:
                    pass

        page.on("response", capture_api)

        await page.goto(WILLYS_BASE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Accept cookies
        try:
            cookie_btn = page.locator(
                "button:has-text('Acceptera'), "
                "button:has-text('Godkänn'), "
                "#onetrust-accept-btn-handler"
            )
            if await cookie_btn.first.is_visible(timeout=3000):
                await cookie_btn.first.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

        # Select store
        try:
            store_btn = page.locator(
                "button:has-text('Välj butik'), "
                "button:has-text('Byt butik'), "
                "[data-testid='store-selector'], "
                "[class*='store-selector']"
            )
            await store_btn.first.click(timeout=5000)
            await page.wait_for_timeout(1000)

            # Search for store
            search_input = page.locator(
                "input[placeholder*='butik'], input[placeholder*='Sök']"
            )
            await search_input.first.fill(self.store.name.replace("Willys ", ""))
            await page.wait_for_timeout(1500)

            # Click the matching store
            store_result = page.locator(
                f"text=/{re.escape(self.store.name)}/i"
            )
            if await store_result.first.is_visible(timeout=5000):
                await store_result.first.click()
                await page.wait_for_timeout(2000)

        except Exception as e:
            logger.warning(f"Willys store selection failed: {e}")
            # Try setting via cookie/URL
            if self.store.external_id:
                await page.goto(
                    f"{WILLYS_BASE_URL}/sok?q=&avd=&store={self.store.external_id}",
                    wait_until="domcontentloaded",
                )
                await page.wait_for_timeout(2000)

    async def search_product(self, page: Page, product: Product) -> RawPriceResult:
        """Search for a product on Willys."""
        result = RawPriceResult(
            product_id=product.id,
            store_id=self.store.id,
        )

        search_term = self.get_search_term(product)

        # Clear previous API responses to capture fresh ones
        self._api_responses.clear()

        search_url = f"{WILLYS_BASE_URL}/sok?q={search_term.replace(' ', '+')}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        # Try to use captured API response first
        api_result = self._try_parse_api_response(result)
        if api_result and api_result.found:
            return api_result

        # DOM-based fallback
        try:
            product_cards = page.locator(
                "[data-testid='product'], "
                ".product-card, "
                "[class*='ProductCard'], "
                "[class*='productCard'], "
                "article[class*='product']"
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

            # Campaign indicators
            try:
                campaign_el = card.locator(
                    "[class*='campaign'], [class*='Campaign'], "
                    "[class*='offer'], [class*='splash'], "
                    "[class*='badge'], [class*='Promotion'], "
                    ".promotion"
                )
                if await campaign_el.count() > 0:
                    result.is_campaign = True
                    result.campaign_label = await campaign_el.first.text_content(timeout=2000)
            except Exception:
                pass

            # Original price
            try:
                orig_el = card.locator(
                    "s, del, [class*='original'], [class*='was'], "
                    "[class*='strikethrough']"
                )
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

            # Full card text
            try:
                result.raw_data["card_text"] = await card.text_content(timeout=2000)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error parsing Willys result for {search_term}: {e}")
            result.found = False
            result.error = str(e)

        return result

    def _try_parse_api_response(self, result: RawPriceResult) -> RawPriceResult | None:
        """Try to extract product data from intercepted API responses."""
        for url, data in self._api_responses.items():
            if "/search/" not in url:
                continue

            try:
                products = data.get("results", data.get("products", []))
                if not products:
                    continue

                item = products[0]
                price = item.get("price", item.get("currentPrice"))
                if price is not None:
                    result.price = float(price)
                    result.found = True
                    result.raw_data = {"api_url": url, "api_item": item}

                    # Original price from API
                    orig = item.get("originalPrice", item.get("savingsPrice"))
                    if orig:
                        result.original_price = float(orig)

                    # Unit price
                    unit = item.get("comparisonPrice", item.get("pricePerUnit"))
                    if unit:
                        result.unit_price = float(unit)

                    # Campaign from API
                    if item.get("potpiece") or item.get("promotion") or item.get("campaign"):
                        result.is_campaign = True
                        result.campaign_label = (
                            item.get("promotionText", "")
                            or item.get("campaignText", "")
                        )

                    return result

            except (KeyError, TypeError, ValueError) as e:
                logger.debug(f"Could not parse Willys API response: {e}")

        return None

    def detect_campaign(self, raw: RawPriceResult) -> bool:
        """Detect if a Willys price is a campaign/promo."""
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
