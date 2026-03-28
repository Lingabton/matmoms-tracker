"""Willys scraper — willys.se

Willys is part of the Axfood group.
Strategy: Navigate to search page, intercept the /search?q= API response.
Fallback to DOM scraping with data-testid selectors.
Store selection via POST /axfood/rest/store/activate.
"""

from __future__ import annotations

import json
import logging
import re

from playwright.async_api import Browser, Page

from matmoms.db.models import Product, Store
from matmoms.scrapers.base import BaseScraper, RawPriceResult, best_match

logger = logging.getLogger(__name__)

WILLYS_BASE_URL = "https://www.willys.se"


class WillysScraper(BaseScraper):
    chain_id = "willys"

    async def select_store(self, page: Page) -> None:
        """Navigate to Willys and activate the store via API."""
        await page.goto(WILLYS_BASE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Accept cookies
        try:
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            if await cookie_btn.is_visible(timeout=3000):
                await cookie_btn.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

        # Activate store via API
        if self.store.external_id:
            try:
                result = await page.evaluate(
                    """async (storeId) => {
                        try {
                            const resp = await fetch(
                                '/axfood/rest/store/activate?storeId=' + storeId
                                + '&activelySelected=true&forceAsPickingStore=false',
                                { method: 'POST', credentials: 'include' }
                            );
                            if (resp.ok) return await resp.json();
                        } catch(e) {}
                        return null;
                    }""",
                    self.store.external_id,
                )
                if result and result.get("storeId"):
                    logger.info(f"Willys store activated: {result.get('name', self.store.name)}")
                else:
                    logger.warning(f"Willys store activation returned unexpected result for {self.store.name}")
            except Exception as e:
                logger.warning(f"Willys store activation failed: {e}")

    async def search_product(self, page: Page, product: Product) -> RawPriceResult:
        """Search for a product on Willys."""
        result = RawPriceResult(
            product_id=product.id,
            store_id=self.store.id,
        )

        search_term = self.get_search_term(product)

        # Try direct API call first (most reliable)
        api_result = await self._search_via_api(page, search_term, result, product)
        if api_result and api_result.found:
            return api_result

        # Fallback: navigate to search page and parse DOM
        search_url = f"{WILLYS_BASE_URL}/sok?q={search_term.replace(' ', '+')}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)

        return await self._search_dom(page, result, search_term)

    async def _search_via_api(
        self, page: Page, search_term: str, result: RawPriceResult, product: Product
    ) -> RawPriceResult | None:
        """Call Willys search API directly."""
        try:
            from urllib.parse import quote
            encoded = quote(search_term, safe="")
            api_url = f"{WILLYS_BASE_URL}/search?q={encoded}&size=10"

            response = await page.evaluate(
                """async (url) => {
                    try {
                        const resp = await fetch(url, { credentials: 'include' });
                        if (resp.ok) return await resp.json();
                        return { error: resp.status };
                    } catch(e) {
                        return { error: e.message };
                    }
                }""",
                api_url,
            )

            if response and "error" not in response:
                return self._parse_api_data(response, result, api_url, product)

        except Exception as e:
            logger.debug(f"Willys direct API call failed: {e}")

        return None

    def _parse_api_data(
        self, data: dict, result: RawPriceResult, source_url: str, product: Product
    ) -> RawPriceResult | None:
        """Parse Willys search API response with smart matching."""
        try:
            products = data.get("results", [])
            if not products or not isinstance(products, list):
                return None

            item = best_match(
                products, product,
                name_key="name",
                brand_key="manufacturer",
                size_key="displayVolume",
            )
            if not item:
                return None

            price = item.get("priceValue")
            if price is None:
                price_str = item.get("priceNoUnit")
                if price_str:
                    price = float(price_str.replace(",", "."))

            if price is not None:
                result.price = float(price)
                result.found = True
                result.raw_data = {"api_url": source_url, "api_item": item}

                # Comparison price
                comp = item.get("comparePrice")
                if comp and isinstance(comp, str):
                    result.unit_price = self._parse_price(comp)

                # Campaign via potentialPromotions
                promos = item.get("potentialPromotions", [])
                if promos:
                    result.is_campaign = True
                    promo = promos[0]
                    result.campaign_label = (
                        promo.get("conditionLabel")
                        or promo.get("rewardLabel")
                        or promo.get("splashTitleText")
                        or ""
                    )
                    savings = item.get("savingsAmount")
                    if savings and result.price:
                        result.original_price = round(result.price + float(savings), 2)

                if item.get("bargainProduct"):
                    result.is_campaign = True

                return result

        except (KeyError, TypeError, ValueError) as e:
            logger.debug(f"Could not parse Willys API response: {e}")

        return None

    async def _search_dom(
        self, page: Page, result: RawPriceResult, search_term: str
    ) -> RawPriceResult:
        """Fallback: Extract price from DOM using data-testid selectors."""
        try:
            product_cards = page.locator("[data-testid='product']")

            count = await product_cards.count()
            if count == 0:
                result.found = False
                return result

            card = product_cards.first

            # Price — try both DEFAULT (regular) and GENERAL (campaign)
            price_el = card.locator(
                "[data-testid='product-price-DEFAULT'], "
                "[data-testid='product-price-GENERAL']"
            ).first

            price_text = await price_el.text_content(timeout=3000)
            result.raw_data["price_text"] = price_text

            # Willys splits price into separate spans: "1850/st" means 18 kr 50 öre
            # The two spans contain kr digits and öre digits with no separator
            price = self._parse_willys_price(price_text)
            if price is not None:
                result.price = price
                result.found = True

            # Campaign: GENERAL price testid means it's a campaign
            campaign_price = card.locator("[data-testid='product-price-GENERAL']")
            if await campaign_price.count() > 0:
                result.is_campaign = True

            # Product name
            try:
                name_el = card.locator("[itemprop='name']")
                if await name_el.count() > 0:
                    result.raw_data["product_name"] = await name_el.first.text_content(timeout=2000)
            except Exception:
                pass

            # Full card text for traceability
            try:
                result.raw_data["card_text"] = await card.text_content(timeout=2000)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error parsing Willys result for {search_term}: {e}")
            result.found = False
            result.error = str(e)

        return result

    def detect_campaign(self, raw: RawPriceResult) -> bool:
        if raw.is_campaign:
            return True
        if raw.original_price and raw.price and raw.original_price > raw.price:
            return True
        if raw.campaign_label:
            return True
        return False

    @staticmethod
    def _parse_willys_price(text: str | None) -> float | None:
        """Parse Willys DOM price: spans concatenate to e.g. '1850/st' = 18.50 kr."""
        if not text:
            return None
        # Strip unit suffix like "/st", "/kg"
        cleaned = re.sub(r"/\w+", "", text).strip()
        # Remove non-digits
        digits = re.sub(r"[^\d]", "", cleaned)
        if not digits:
            return None
        if len(digits) <= 2:
            # Just öre or just kr
            return float(digits)
        # Last 2 digits are öre, rest is kr
        kr = int(digits[:-2])
        ore = int(digits[-2:])
        return kr + ore / 100.0

    @staticmethod
    def _parse_price(text: str | None) -> float | None:
        if not text:
            return None
        cleaned = re.sub(r"[^\d:,.]", "", text.strip())
        if not cleaned:
            return None
        cleaned = cleaned.replace(":", ".").replace(",", ".")
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = parts[0] + "." + parts[1]
        try:
            return float(cleaned)
        except ValueError:
            return None
