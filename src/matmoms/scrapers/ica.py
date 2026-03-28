"""ICA scraper — handlaprivatkund.ica.se

Strategy: API-first via ICA's internal product search API.
The shopping SPA lives on handlaprivatkund.ica.se (not handla.ica.se).
Each store has an accountId used in the URL path.
We first resolve external_id -> accountId via the store API on handla.ica.se,
then call the search API on handlaprivatkund.ica.se directly.
Falls back to DOM scraping with data-test="fop-*" selectors.
"""

from __future__ import annotations

import json
import logging
import re

from playwright.async_api import Browser, Page, Response

from matmoms.db.models import Product, Store
from matmoms.scrapers.base import BaseScraper, RawPriceResult, best_match

logger = logging.getLogger(__name__)

ICA_LANDING_URL = "https://handla.ica.se"
ICA_STORE_API = "https://handla.ica.se/api/store/v1"
ICA_SHOP_BASE = "https://handlaprivatkund.ica.se"


class IcaScraper(BaseScraper):
    chain_id = "ica"

    def __init__(self, store: Store, products: list[Product], browser: Browser):
        super().__init__(store, products, browser)
        self._account_id: str | None = None

    async def select_store(self, page: Page) -> None:
        """Resolve store accountId and navigate to the store page."""
        # First go to landing page to get cookies
        await page.goto(ICA_LANDING_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1000)

        # Accept cookies
        try:
            cookie_btn = page.locator("#onetrust-accept-btn-handler")
            if await cookie_btn.is_visible(timeout=3000):
                await cookie_btn.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

        # Resolve external_id -> accountId via store API
        zip_code = self.store.zip_code or "11247"
        await self._resolve_account_id(page, zip_code)

        if not self._account_id:
            logger.warning(
                f"ICA: could not resolve accountId for {self.store.name} "
                f"(ext_id={self.store.external_id}), will try external_id as accountId"
            )
            self._account_id = self.store.external_id

        # Navigate to the store page on handlaprivatkund
        store_url = f"{ICA_SHOP_BASE}/stores/{self._account_id}"
        await page.goto(store_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        logger.info(f"ICA store selected: {self.store.name} (accountId={self._account_id})")

    async def _resolve_account_id(self, page: Page, zip_code: str) -> None:
        """Call ICA's store API to map store name to accountId."""
        try:
            api_url = f"{ICA_STORE_API}?zip={zip_code}&customerType=B2C"
            data = await page.evaluate(
                """async (url) => {
                    try {
                        const resp = await fetch(url);
                        if (resp.ok) return await resp.json();
                    } catch(e) {}
                    return null;
                }""",
                api_url,
            )

            if not data:
                return

            # Search in both delivery and pickup stores
            all_stores = (
                (data.get("forHomeDelivery") or [])
                + (data.get("forPickup") or [])
            )

            # Try exact ID match first
            ext_id = self.store.external_id
            for store in all_stores:
                if store.get("id") == ext_id or str(store.get("id")) == str(ext_id):
                    self._account_id = str(store["accountId"])
                    logger.debug(
                        f"ICA store resolved by ID: {ext_id} -> accountId {self._account_id}"
                    )
                    return

            # Fallback: match by name (our DB name may not match ICA's exactly)
            store_name_lower = self.store.name.lower()
            # Extract key words: strip "ICA", "Maxi", "Nära", "Kvantum", "Supermarket"
            name_keywords = [
                w for w in store_name_lower.split()
                if w not in ("ica", "maxi", "nära", "kvantum", "supermarket", "stormarknad")
            ]

            best_match = None
            best_score = 0
            for store in all_stores:
                api_name = store.get("name", "").lower()
                score = sum(1 for kw in name_keywords if kw in api_name)
                if score > best_score:
                    best_score = score
                    best_match = store

            if best_match and best_score >= 1:
                self._account_id = str(best_match["accountId"])
                logger.debug(
                    f"ICA store resolved by name: '{self.store.name}' -> "
                    f"'{best_match['name']}' (accountId={self._account_id})"
                )
                return

            logger.debug(f"ICA store '{self.store.name}' not found in API response for zip {zip_code}")

        except Exception as e:
            logger.debug(f"ICA store API call failed: {e}")

    def get_search_term(self, product: Product) -> str:
        """Get search term, stripping pack size suffixes that break ICA search."""
        term = super().get_search_term(product)
        # ICA's search chokes on pack sizes like "1.5L", "1L", "500g" at end
        term = re.sub(r"\s+\d+(?:[.,]\d+)?\s*(?:L|l|dl|cl|ml|kg|g)\s*$", "", term)
        return term

    async def search_product(self, page: Page, product: Product) -> RawPriceResult:
        """Search for a product — API first, DOM fallback."""
        result = RawPriceResult(
            product_id=product.id,
            store_id=self.store.id,
        )

        search_term = self.get_search_term(product)

        # Try direct API call
        api_result = await self._search_via_api(page, search_term, result, product)
        if api_result and api_result.found:
            return api_result

        # Fallback: navigate to search page and parse DOM
        search_url = (
            f"{ICA_SHOP_BASE}/stores/{self._account_id}"
            f"/search?q={search_term.replace(' ', '+')}"
        )
        await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(2000)

        return await self._search_dom(page, result, search_term)

    async def _search_via_api(
        self, page: Page, search_term: str, result: RawPriceResult, product: Product
    ) -> RawPriceResult | None:
        """Call ICA's product search API directly."""
        try:
            from urllib.parse import quote
            encoded_term = quote(search_term, safe="")

            api_url = (
                f"{ICA_SHOP_BASE}/stores/{self._account_id}"
                f"/api/webproductpagews/v6/product-pages/search"
                f"?includeAdditionalPageInfo=true"
                f"&maxPageSize=10"
                f"&maxProductsToDecorate=5"
                f"&q={encoded_term}"
                f"&tag=web"
            )

            data = await page.evaluate(
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

            if data and "error" not in data:
                return self._parse_api_response(data, result, api_url, product)

        except Exception as e:
            logger.debug(f"ICA API call failed: {e}")

        return None

    def _parse_api_response(
        self, data: dict, result: RawPriceResult, source_url: str, product: Product
    ) -> RawPriceResult | None:
        """Parse ICA API response — products in productGroups[].decoratedProducts[]."""
        try:
            product_groups = data.get("productGroups", [])
            if not product_groups:
                return None

            # Collect all products from all groups
            all_items = []
            for group in product_groups:
                all_items.extend(group.get("decoratedProducts", []))

            if not all_items:
                return None

            item = best_match(
                all_items, product,
                name_key="name",
                brand_key="brand",
                size_key="packSizeDescription",
            )
            if not item:
                return None

            # Price at price.amount (string)
            price_obj = item.get("price", {})
            price_str = price_obj.get("amount")
            if price_str is None:
                return None

            result.price = float(price_str)
            result.found = True
            result.raw_data = {"api_url": source_url, "api_item": item}

            # Unit/comparison price
            unit_price_obj = item.get("unitPrice", {})
            unit_price_inner = unit_price_obj.get("price", {})
            unit_amount = unit_price_inner.get("amount")
            if unit_amount is not None:
                result.unit_price = float(unit_amount)

            # Promotions
            promos = item.get("promotions", [])
            if promos:
                result.is_campaign = True
                promo = promos[0]
                result.campaign_label = promo.get("description", "")

            # Availability
            result.is_available = item.get("available", True)

            return result

        except (KeyError, TypeError, ValueError) as e:
            logger.debug(f"ICA API parse failed: {e}")

        return None

    async def _search_dom(
        self, page: Page, result: RawPriceResult, search_term: str
    ) -> RawPriceResult:
        """Fallback: Extract price from DOM using data-test='fop-*' selectors."""
        try:
            # ICA uses data-test="fop-wrapper:{productId}" for product cards
            product_cards = page.locator("[data-test^='fop-wrapper:']")

            count = await product_cards.count()
            if count == 0:
                result.found = False
                return result

            card = product_cards.first

            # Price from data-test="fop-price"
            price_el = card.locator("[data-test='fop-price']")
            if await price_el.count() > 0:
                price_text = await price_el.first.text_content(timeout=3000)
                result.raw_data["price_text"] = price_text
                price = self._parse_price(price_text)
                if price is not None:
                    result.price = price
                    result.found = True

            # Campaign detection via data-ica-class attribute
            ica_class = await card.get_attribute("data-ica-class")
            if ica_class and ica_class in ("offer-single", "offer-multi"):
                result.is_campaign = True

            # Campaign text
            offer_text_el = card.locator("[data-test='fop-offer-text']")
            if await offer_text_el.count() > 0:
                result.campaign_label = await offer_text_el.first.text_content(timeout=2000)
                result.is_campaign = True

            # Reference/original price
            ref_price_el = card.locator("[data-test='fop-reference-price']")
            if await ref_price_el.count() > 0:
                ref_text = await ref_price_el.first.text_content(timeout=2000)
                result.original_price = self._parse_price(ref_text)
                result.is_campaign = True

            # Unit price from fop-size or fop-price-per-unit
            unit_el = card.locator("[data-test='fop-price-per-unit'], [data-test='fop-size']")
            if await unit_el.count() > 0:
                unit_text = await unit_el.first.text_content(timeout=2000)
                result.raw_data["unit_price_text"] = unit_text
                # Extract price from text like "0.7kg (71,24 kr/kg)"
                match = re.search(r"(\d+[,:]\d+)\s*kr", unit_text)
                if match:
                    result.unit_price = self._parse_price(match.group(1))

            # Product name for traceability
            title_el = card.locator("[data-test='fop-title']")
            if await title_el.count() > 0:
                result.raw_data["product_name"] = await title_el.first.text_content(timeout=2000)

        except Exception as e:
            logger.debug(f"ICA DOM parse failed for {search_term}: {e}")
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
        if raw.member_price and raw.price and raw.member_price < raw.price:
            return True
        return False

    @staticmethod
    def _parse_price(text: str | None) -> float | None:
        """Parse price from Swedish format: '23:90 kr', '23,90', '24 kr'."""
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
