"""ICA scraper — handla.ica.se"""

from __future__ import annotations

import logging
import re

from playwright.async_api import Browser, Page

from matmoms.db.models import Product, Store
from matmoms.scrapers.base import BaseScraper, RawPriceResult

logger = logging.getLogger(__name__)

ICA_BASE_URL = "https://handla.ica.se"


class IcaScraper(BaseScraper):
    chain_id = "ica"

    def __init__(self, store: Store, products: list[Product], browser: Browser):
        super().__init__(store, products, browser)

    async def select_store(self, page: Page) -> None:
        """Navigate to ICA and select the store via the store picker."""
        await page.goto(ICA_BASE_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # Accept cookies if dialog appears
        try:
            cookie_btn = page.locator("button:has-text('Acceptera')")
            if await cookie_btn.is_visible(timeout=3000):
                await cookie_btn.click()
                await page.wait_for_timeout(500)
        except Exception:
            pass

        # Click on store selector / "Välj butik" button
        try:
            store_btn = page.locator(
                "[data-testid='store-selector'], "
                "button:has-text('Välj butik'), "
                "button:has-text('Byt butik')"
            )
            await store_btn.first.click(timeout=5000)
            await page.wait_for_timeout(1000)

            # Search for our store by name
            search_input = page.locator(
                "input[placeholder*='butik'], input[placeholder*='Sök']"
            )
            await search_input.first.fill(self.store.name)
            await page.wait_for_timeout(1500)

            # Click the matching store result
            store_result = page.locator(
                f"text=/{re.escape(self.store.name)}/i"
            )
            await store_result.first.click(timeout=5000)
            await page.wait_for_timeout(2000)

        except Exception as e:
            # Fallback: try setting store via URL parameter or zip code
            logger.warning(f"Store selection UI failed, trying zip fallback: {e}")
            if self.store.zip_code:
                await page.goto(
                    f"{ICA_BASE_URL}/sok?q=&s={self.store.external_id}",
                    wait_until="domcontentloaded",
                )
                await page.wait_for_timeout(2000)

    async def search_product(self, page: Page, product: Product) -> RawPriceResult:
        """Search for a product on ICA and extract price data."""
        result = RawPriceResult(
            product_id=product.id,
            store_id=self.store.id,
        )

        search_term = self.get_search_term(product)
        search_url = f"{ICA_BASE_URL}/sok?q={search_term.replace(' ', '+')}"
        await page.goto(search_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        try:
            # Look for product cards in search results
            product_cards = page.locator(
                "[data-testid='product-card'], "
                ".product-card, "
                "[class*='ProductCard'], "
                "article[class*='product']"
            )

            count = await product_cards.count()
            if count == 0:
                result.found = False
                return result

            # Take the first matching result
            card = product_cards.first

            # Extract price — ICA typically shows "XX:XX kr" or "XX kr"
            price_el = card.locator(
                "[data-testid='price'], "
                "[class*='price'], [class*='Price'], "
                ".product-price"
            ).first

            price_text = await price_el.text_content(timeout=3000)
            result.raw_data["price_text"] = price_text

            price = self._parse_price(price_text)
            if price is not None:
                result.price = price
                result.found = True

            # Check for campaign/offer indicators
            try:
                campaign_el = card.locator(
                    "[class*='campaign'], [class*='Campaign'], "
                    "[class*='offer'], [class*='Offer'], "
                    "[class*='splash'], [class*='badge'], "
                    ".promotion, .erbjudande"
                )
                if await campaign_el.count() > 0:
                    result.is_campaign = True
                    result.campaign_label = await campaign_el.first.text_content(timeout=2000)
            except Exception:
                pass

            # Check for original/struck-through price
            try:
                orig_price_el = card.locator(
                    "[class*='original'], [class*='strikethrough'], "
                    "[class*='was-price'], s, del"
                )
                if await orig_price_el.count() > 0:
                    orig_text = await orig_price_el.first.text_content(timeout=2000)
                    result.original_price = self._parse_price(orig_text)
                    result.is_campaign = True
            except Exception:
                pass

            # Check for comparison/unit price
            try:
                unit_price_el = card.locator(
                    "[class*='unit-price'], [class*='UnitPrice'], "
                    "[class*='comparison-price'], [class*='jmfpris']"
                )
                if await unit_price_el.count() > 0:
                    unit_text = await unit_price_el.first.text_content(timeout=2000)
                    result.unit_price = self._parse_price(unit_text)
                    result.raw_data["unit_price_text"] = unit_text
            except Exception:
                pass

            # Check for member price
            try:
                member_el = card.locator(
                    "[class*='member'], [class*='Member'], "
                    "[class*='stammis'], [class*='Stammis']"
                )
                if await member_el.count() > 0:
                    member_text = await member_el.first.text_content(timeout=2000)
                    result.member_price = self._parse_price(member_text)
            except Exception:
                pass

            # Store full card text for traceability
            try:
                result.raw_data["card_text"] = await card.text_content(timeout=2000)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error parsing ICA result for {search_term}: {e}")
            result.found = False
            result.error = str(e)

        return result

    def detect_campaign(self, raw: RawPriceResult) -> bool:
        """Detect if an ICA price is a campaign/promo."""
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
        """Parse price from Swedish formatted text like '23:90 kr' or '23,90'."""
        if not text:
            return None
        # Remove non-numeric except : , .
        cleaned = re.sub(r"[^\d:,.]", "", text.strip())
        if not cleaned:
            return None
        # Swedish format: 23:90 or 23,90
        cleaned = cleaned.replace(":", ".").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return None
