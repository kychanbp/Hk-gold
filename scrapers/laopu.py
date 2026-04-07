"""Lao Pu Gold (老鋪黃金) gold price scraper.

Website: https://www.lphj.com/

Note: 老鋪黃金 is a luxury ancient-style gold jewellery brand (古法黃金).
Unlike traditional gold retailers, they price products at a significant premium
over spot gold price (克均價 ~2000-3000+ RMB/gram in 2026).

They do NOT publish a standard daily gold buy/sell price table like the other
HK retailers. Their pricing is product-specific with high craftsmanship premiums.

This scraper attempts to extract any gold price info from their website,
but may return limited data compared to other retailers.
"""

import requests
from bs4 import BeautifulSoup

from .base import GoldPrice, GoldPriceScraper, ScraperResult


class LaoPuScraper(GoldPriceScraper):
    name = "Lao Pu Gold"
    name_zh = "老鋪黃金"
    url = "https://www.lphj.com/"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def scrape_with_requests(self) -> ScraperResult:
        result = self._make_result()
        result.error = (
            "老鋪黃金 does not publish standard daily gold prices. "
            "They are a luxury brand with product-specific pricing (古法黃金). "
            "Visit https://www.lphj.com/ for product prices."
        )
        try:
            resp = requests.get(self.url, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            parsed = self._parse_html(resp.text, result)
            if parsed.prices:
                parsed.error = None
            return parsed
        except Exception:
            pass
        return result

    def scrape_with_playwright(self, page) -> ScraperResult:
        result = self._make_result()
        result.error = (
            "老鋪黃金 does not publish standard daily gold prices. "
            "They are a luxury brand with product-specific pricing (古法黃金). "
            "Visit https://www.lphj.com/ for product prices."
        )
        try:
            page.goto(self.url, timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            parsed = self._parse_html(html, result)
            if parsed.prices:
                parsed.error = None
            return parsed
        except Exception:
            pass
        return result

    def _parse_html(self, html: str, result: ScraperResult) -> ScraperResult:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        for line in lines:
            if any(kw in line for kw in ["金價", "克", "gold price"]):
                numbers = []
                val = self._parse_price(line)
                if val is not None:
                    numbers.append(val)

                if numbers:
                    gp = GoldPrice(
                        type="古法黃金 (參考價)",
                        sell_per_gram=numbers[0],
                    )
                    result.prices.append(gp)

        return result
