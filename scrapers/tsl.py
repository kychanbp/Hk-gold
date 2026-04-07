"""TSL Jewellery (謝瑞麟) gold price scraper.

Gold price page: https://www.tslj.com/zh-hk/
The TSL website shows gold bar/jewellery prices on their homepage or a dedicated gold price section.

TSL displays:
- 飾金價 (Gold Jewellery): per tael
- 金條價 (Gold Bar): per tael
- 鉑金價 (Platinum): per tael
"""

import requests
from bs4 import BeautifulSoup

from .base import GoldPrice, GoldPriceScraper, ScraperResult


class TSLScraper(GoldPriceScraper):
    name = "TSL Jewellery"
    name_zh = "謝瑞麟"
    url = "https://www.tslj.com/zh-hk/"
    url_en = "https://www.tslj.com/en-hk/"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
    }

    def scrape_with_requests(self) -> ScraperResult:
        result = self._make_result()
        for url in [self.url, self.url_en]:
            try:
                resp = requests.get(url, headers=self.HEADERS, timeout=15)
                resp.raise_for_status()
                result = self._parse_html(resp.text, result)
                if result.prices:
                    return result
            except Exception as e:
                result.error = str(e)
        return result

    def scrape_with_playwright(self, page) -> ScraperResult:
        result = self._make_result()
        for url in [self.url, self.url_en]:
            try:
                page.goto(url, timeout=30000)
                page.wait_for_timeout(3000)
                try:
                    page.wait_for_selector("table, .gold-price, .price-table, .gold-bar", timeout=10000)
                except Exception:
                    pass
                html = page.content()
                result = self._parse_html(html, result)
                if result.prices:
                    return result
            except Exception as e:
                result.error = str(e)
        return result

    def _parse_html(self, html: str, result: ScraperResult) -> ScraperResult:
        soup = BeautifulSoup(html, "html.parser")

        tables = soup.find_all("table")
        for table in tables:
            prices = self._parse_table(table)
            if prices:
                result.prices = prices
                break

        if not result.prices:
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

    def _parse_table(self, table) -> list[GoldPrice]:
        prices = []
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            cell_texts = [c.get_text(strip=True) for c in cells]
            if not cell_texts:
                continue

            label = cell_texts[0]
            gold_type = None
            if any(kw in label for kw in ["飾金", "足金", "Gold Jewellery", "999"]) and "換" not in label and "鉑" not in label:
                gold_type = "飾金 999.9"
            elif any(kw in label for kw in ["金條", "金粒", "Gold Bar", "投資"]) and "換" not in label:
                gold_type = "金粒"

            if gold_type:
                nums = []
                for ct in cell_texts[1:]:
                    val = self._parse_price(ct)
                    if val is not None:
                        nums.append(val)

                if nums:
                    gp = GoldPrice(type=gold_type)
                    if len(nums) >= 2:
                        gp.sell_per_tael = nums[0]
                        gp.buy_per_tael = nums[1]
                    elif len(nums) == 1:
                        gp.sell_per_tael = nums[0]
                    prices.append(gp)
        return prices

    def _parse_from_text(self, lines: list[str]) -> list[GoldPrice]:
        prices = []
        price_types = {
            "飾金": "飾金 999.9",
            "足金": "飾金 999.9",
            "999": "飾金 999.9",
            "金條": "金粒",
            "金粒": "金粒",
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
                    nums_sorted = sorted(numbers[:4], reverse=True)
                    gp.sell_per_tael = nums_sorted[0]
                    gp.buy_per_tael = nums_sorted[1] if len(nums_sorted) > 1 else None
                    prices.append(gp)

            i += 1
        return prices
