"""Chow Tai Fook (周大福) gold price scraper.

Gold price page: https://www.chowtaifook.com/zh-hk/eshop/realtime-gold-price.html

The page displays a table with:
- 999.9飾金: sell/buy per gram and per tael
- 飾金換金價: buy only per gram and per tael
- 飾金換珠寶價: buy only per gram and per tael
- 金粒 (投資金): sell/buy per gram and per tael
- 金粒換貨價: buy only per gram and per tael
- 足鉑金: buy only per gram and per tael
- 足鉑金換貨價: buy only per gram and per tael

Data is rendered server-side in HTML table. Last updated time shown at bottom.
"""

import requests
from bs4 import BeautifulSoup

from .base import GoldPrice, GoldPriceScraper, ScraperResult


class ChowTaiFookScraper(GoldPriceScraper):
    name = "Chow Tai Fook"
    name_zh = "周大福"
    url = "https://www.chowtaifook.com/zh-hk/eshop/realtime-gold-price.html"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
    }

    def scrape_with_requests(self) -> ScraperResult:
        result = self._make_result()
        try:
            resp = requests.get(self.url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            result = self._parse_html(resp.text, result)
        except Exception as e:
            result.error = str(e)
        return result

    def scrape_with_playwright(self, page) -> ScraperResult:
        result = self._make_result()
        try:
            page.goto(self.url, timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            result = self._parse_html(html, result)
        except Exception as e:
            result.error = str(e)
        return result

    def _parse_html(self, html: str, result: ScraperResult) -> ScraperResult:
        soup = BeautifulSoup(html, "html.parser")

        # Try to find gold price table rows
        # The page uses a table structure with rows for each gold type
        rows = soup.select("table tr, .gold-price-row, .price-row")
        if not rows:
            # Try finding by text content - look for divs/sections containing gold price data
            rows = soup.find_all(["tr", "div", "li"], string=lambda s: s and "999" in s)

        # Try parsing the page text as a fallback
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        prices = self._parse_from_text(lines)
        if prices:
            result.prices = prices

        # Look for last updated time
        for line in lines:
            if "更新" in line:
                result.last_updated = line.replace("最後更新時間:", "").replace("最後更新時間：", "").strip()
                break

        if not result.prices:
            result.error = "Could not parse gold prices from page"
        return result

    def _parse_from_text(self, lines: list[str]) -> list[GoldPrice]:
        """Parse gold prices from page text lines.

        Based on the screenshot, the structure is:
        - Row label: "999.9飾金"
        - Units: 克 / 兩
        - Sell prices: per gram / per tael
        - Buy prices: per gram / per tael
        """
        prices = []
        price_map = {
            "999.9飾金": "飾金 999.9",
            "金粒": "金粒 (投資金)",
        }

        i = 0
        while i < len(lines):
            line = lines[i]
            matched_type = None
            for key, label in price_map.items():
                if key in line and "換" not in line:
                    matched_type = label
                    break

            if matched_type:
                # Collect nearby numbers
                numbers = []
                for j in range(max(0, i - 2), min(len(lines), i + 8)):
                    val = self._parse_price(lines[j])
                    if val is not None:
                        numbers.append(val)

                if len(numbers) >= 4:
                    # Expected order: sell_gram, sell_tael, buy_gram, buy_tael
                    gp = GoldPrice(
                        type=matched_type,
                        sell_per_gram=numbers[0],
                        sell_per_tael=numbers[1],
                        buy_per_gram=numbers[2],
                        buy_per_tael=numbers[3],
                    )
                    prices.append(gp)
                elif len(numbers) >= 2:
                    gp = GoldPrice(
                        type=matched_type,
                        sell_per_tael=numbers[0],
                        buy_per_tael=numbers[1],
                    )
                    prices.append(gp)

            i += 1
        return prices
