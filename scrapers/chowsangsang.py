"""Chow Sang Sang (周生生) gold price scraper.

Gold price page: https://www.chowsangsang.com/zh-hk/gold-price
Also available: https://www.chowsangsang.com/en/gold-price
Possible API: https://ws.chowsangsang.com/goldrate

The page displays gold prices in a table format:
- 足金飾品 (999.9 Gold Jewellery): sell/buy per tael
- 金粒 (Gold Granules): sell/buy per tael
- 足鉑金飾品 (Platinum Jewellery): sell/buy per tael

Prices are typically per tael (兩) in HKD.
"""

import json

import requests
from bs4 import BeautifulSoup

from .base import GoldPrice, GoldPriceScraper, ScraperResult


class ChowSangSangScraper(GoldPriceScraper):
    name = "Chow Sang Sang"
    name_zh = "周生生"
    url = "https://www.chowsangsang.com/zh-hk/gold-price"
    url_en = "https://www.chowsangsang.com/en/gold-price"
    api_url = "https://ws.chowsangsang.com/goldrate"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
    }

    API_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.chowsangsang.com/",
        "Origin": "https://www.chowsangsang.com",
    }

    def scrape_with_requests(self) -> ScraperResult:
        result = self._make_result()

        # Try API endpoint first (faster, more reliable if it works)
        try:
            resp = requests.get(self.api_url, headers=self.API_HEADERS, timeout=10)
            if resp.status_code == 200:
                parsed = self._parse_api_response(resp.text, result)
                if parsed.prices:
                    return parsed
        except Exception:
            pass

        # Fallback to HTML scraping
        try:
            resp = requests.get(self.url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            result = self._parse_html(resp.text, result)
        except Exception as e:
            result.error = str(e)
        return result

    def _parse_api_response(self, text: str, result: ScraperResult) -> ScraperResult:
        """Parse JSON response from ws.chowsangsang.com/goldrate API."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return result

        # The API structure is not fully known; try common patterns
        if isinstance(data, dict):
            # Look for gold rate fields
            for key_pattern, gold_type in [
                (["goldJewellery", "gold_jewellery", "ornament", "足金", "飾金"], "飾金 999.9"),
                (["goldGranule", "gold_granule", "goldBar", "gold_bar", "金粒"], "金粒"),
            ]:
                for key in key_pattern:
                    if key in data:
                        item = data[key]
                        gp = GoldPrice(type=gold_type)
                        if isinstance(item, dict):
                            gp.sell_per_tael = self._parse_price(str(item.get("sell", item.get("selling", ""))))
                            gp.buy_per_tael = self._parse_price(str(item.get("buy", item.get("buying", ""))))
                            gp.sell_per_gram = self._parse_price(str(item.get("sellPerGram", item.get("sell_gram", ""))))
                            gp.buy_per_gram = self._parse_price(str(item.get("buyPerGram", item.get("buy_gram", ""))))
                        if gp.sell_per_tael or gp.buy_per_tael:
                            result.prices.append(gp)
                        break

            # Try extracting update time
            for time_key in ["lastUpdate", "last_update", "updateTime", "timestamp"]:
                if time_key in data:
                    result.last_updated = str(data[time_key])
                    break

        return result

    def scrape_with_playwright(self, page) -> ScraperResult:
        result = self._make_result()
        try:
            page.goto(self.url, timeout=30000)
            page.wait_for_timeout(3000)
            # Try waiting for gold price content to load
            try:
                page.wait_for_selector("table, .gold-price, .price-table", timeout=10000)
            except Exception:
                pass
            html = page.content()
            result = self._parse_html(html, result)
        except Exception as e:
            result.error = str(e)
        return result

    def _parse_html(self, html: str, result: ScraperResult) -> ScraperResult:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        prices = self._parse_from_text(lines)
        if prices:
            result.prices = prices

        for line in lines:
            if "更新" in line or "update" in line.lower():
                result.last_updated = line.strip()
                break

        if not result.prices:
            result.error = "Could not parse gold prices from page"
        return result

    def _parse_from_text(self, lines: list[str]) -> list[GoldPrice]:
        prices = []
        price_types = {
            "足金飾品": "飾金 999.9",
            "飾金": "飾金 999.9",
            "Gold Jewellery": "飾金 999.9",
            "999.9": "飾金 999.9",
            "金粒": "金粒",
            "Gold Granule": "金粒",
        }

        i = 0
        seen_types = set()
        while i < len(lines):
            line = lines[i]
            matched_type = None
            for key, label in price_types.items():
                if key in line and "換" not in line and "鉑" not in line and label not in seen_types:
                    matched_type = label
                    seen_types.add(label)
                    break

            if matched_type:
                numbers = []
                for j in range(max(0, i - 2), min(len(lines), i + 8)):
                    val = self._parse_price(lines[j])
                    if val is not None:
                        numbers.append(val)

                if len(numbers) >= 2:
                    gp = GoldPrice(type=matched_type)
                    # Chow Sang Sang typically shows per tael prices
                    # Larger number is sell, smaller is buy
                    nums_sorted = sorted(numbers[:4], reverse=True)
                    gp.sell_per_tael = nums_sorted[0]
                    gp.buy_per_tael = nums_sorted[1] if len(nums_sorted) > 1 else None
                    if len(nums_sorted) > 2:
                        gp.sell_per_gram = nums_sorted[2] if nums_sorted[2] < 5000 else None
                        gp.buy_per_gram = nums_sorted[3] if len(nums_sorted) > 3 and nums_sorted[3] < 5000 else None
                    prices.append(gp)

            i += 1
        return prices
