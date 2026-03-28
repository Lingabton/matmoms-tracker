"""Coop scraper — coop.se

Strategy: Direct API calls to external.api.coop.se using the static
ocp-apim-subscription-key. The search endpoint is POST-based.
Store ID is passed as a query parameter. Falls back to DOM scraping.
"""

from __future__ import annotations

import json
import logging
import re

from playwright.async_api import Browser, Page, Response

from matmoms.db.models import Product, Store
from matmoms.scrapers.base import BaseScraper, RawPriceResult, best_match

logger = logging.getLogger(__name__)

COOP_BASE_URL = "https://www.coop.se/handla"
COOP_API_BASE = "https://external.api.coop.se"

# Static subscription key embedded in Coop's SPA
COOP_API_KEY = "3becf0ce306f41a1ae94077c16798187"


class CoopScraper(BaseScraper):
    chain_id = "coop"

    def __init__(self, store: Store, products: list[Product], browser: Browser):
        super().__init__(store, products, browser)
        self._api_key: str = COOP_API_KEY

    async def select_store(self, page: Page) -> None:
        """Navigate to Coop — store is set via API query param, no UI needed."""
        await page.goto(COOP_BASE_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1000)

        # Accept cookies
        try:
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            if await cookie_btn.is_visible(timeout=3000):
                await cookie_btn.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

        logger.info(f"Coop store set: {self.store.name} (ext_id={self.store.external_id})")

    async def search_product(self, page: Page, product: Product) -> RawPriceResult:
        """Search via POST API call, DOM fallback."""
        result = RawPriceResult(
            product_id=product.id,
            store_id=self.store.id,
        )

        search_term = self.get_search_term(product)

        # Direct API call via page.evaluate (uses browser's fetch)
        api_result = await self._search_via_api(page, search_term, result, product)
        if api_result and api_result.found:
            return api_result

        # Fallback: navigate to search page and parse DOM
        search_url = f"{COOP_BASE_URL}/sok?q={search_term.replace(' ', '+')}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        return await self._search_dom(page, result, search_term)

    async def _search_via_api(
        self, page: Page, search_term: str, result: RawPriceResult, product: Product
    ) -> RawPriceResult | None:
        """Call Coop's search API directly via POST."""
        try:
            store_id = self.store.external_id or ""
            api_url = (
                f"{COOP_API_BASE}/personalization/search/products"
                f"?api-version=v1&store={store_id}"
                f"&groups=CUSTOMER_PRIVATE&device=desktop&direct=false"
            )

            response = await page.evaluate(
                """async ([url, apiKey, query]) => {
                    try {
                        const resp = await fetch(url, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Accept': 'application/json',
                                'ocp-apim-subscription-key': apiKey
                            },
                            body: JSON.stringify({
                                query: query,
                                resultsOptions: {
                                    skip: 0,
                                    take: 10,
                                    sortBy: [],
                                    facets: []
                                },
                                relatedResultsOptions: { skip: 0, take: 0 },
                                customData: { consent: false }
                            })
                        });
                        if (resp.ok) return await resp.json();
                        return { error: resp.status };
                    } catch(e) {
                        return { error: e.message };
                    }
                }""",
                [api_url, self._api_key, search_term],
            )

            if response and "error" not in response:
                return self._parse_api_response(response, result, api_url, product)

        except Exception as e:
            logger.debug(f"Coop API call failed: {e}")

        return None

    def _parse_api_response(
        self, data: dict, result: RawPriceResult, source_url: str, product: Product
    ) -> RawPriceResult | None:
        """Parse Coop API response — products at data['results']['items']."""
        try:
            results = data.get("results", {})
            items = results.get("items", [])
            if not items:
                return None

            item = best_match(
                items, product,
                name_key="name",
                brand_key="manufacturerName",
                size_key="packageSizeInformation",
            )
            if not item:
                return None

            # Price at salesPriceData.b2cPrice
            sales_data = item.get("salesPriceData", {})
            price = sales_data.get("b2cPrice")

            if price is not None:
                result.price = float(price)
                result.found = True
                result.raw_data = {"api_url": source_url, "api_item": item}

                # Comparison price
                comp_data = item.get("comparativePriceData", {})
                comp_price = comp_data.get("b2cPrice")
                if comp_price is not None:
                    result.unit_price = float(comp_price)

                # VAT rate (useful for the VAT pass-through analysis)
                vat = item.get("vat", {})
                if vat:
                    result.raw_data["vat_percent"] = vat.get("value")

                # Campaign via onlinePromotions
                promos = item.get("onlinePromotions", [])
                if promos:
                    result.is_campaign = True
                    promo = promos[0]
                    promo_price = promo.get("priceData", {}).get("b2cPrice")
                    if promo_price is not None:
                        # The promotion price is the current effective price
                        result.original_price = result.price
                        result.price = float(promo_price)
                    result.campaign_label = promo.get("description", "")

                return result

        except (KeyError, TypeError, ValueError) as e:
            logger.debug(f"Coop API parse failed: {e}")

        return None

    async def _search_dom(
        self, page: Page, result: RawPriceResult, search_term: str
    ) -> RawPriceResult:
        """Fallback: Extract price from DOM."""
        try:
            # Coop product cards are <article> elements
            product_cards = page.locator("article")

            if await product_cards.count() == 0:
                result.found = False
                return result

            card = product_cards.first

            # Best approach: parse the product link's aria-label which contains
            # full product info including price
            link = card.locator("a[href*='/handla/varor/']")
            if await link.count() > 0:
                aria = await link.first.get_attribute("aria-label")
                if aria:
                    result.raw_data["aria_label"] = aria
                    # aria-label format: "Name, Brand, Size, Pris X kronor och Y öre styck, ..."
                    price_match = re.search(
                        r"Pris\s+(\d+)\s+kronor\s+och\s+(\d+)\s+öre",
                        aria,
                        re.IGNORECASE,
                    )
                    if price_match:
                        kr = int(price_match.group(1))
                        ore = int(price_match.group(2))
                        result.price = kr + ore / 100.0
                        result.found = True

                    # Comparison price
                    comp_match = re.search(
                        r"Jämförpris\s+(\d+)\s+kronor\s+och\s+(\d+)\s+öre",
                        aria,
                        re.IGNORECASE,
                    )
                    if comp_match:
                        kr = int(comp_match.group(1))
                        ore = int(comp_match.group(2))
                        result.unit_price = kr + ore / 100.0

            # Full card text for traceability
            try:
                result.raw_data["card_text"] = await card.text_content(timeout=2000)
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"Coop DOM parse failed for {search_term}: {e}")
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
