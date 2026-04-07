"""Aggregator site scrapers for HK gold prices.

These serve as fallback data sources when direct retailer scraping fails.
Aggregator sites collect gold prices from multiple HK retailers.

Supported aggregators:
- hkgoldprice.com: Individual shop pages at /shop/周大福, /shop/周生生, etc.
- goldpricehk.com: All retailers on one page
"""

import requests
from bs4 import BeautifulSoup

from .base import GoldPrice, GoldPriceScraper, ScraperResult


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
}

# Mapping of retailer Chinese names to hkgoldprice.com shop URL slugs
HKGOLDPRICE_SHOPS = {
    "周大福": "周大福",
    "周生生": "周生生",
    "六福珠寶": "六福",
    "謝瑞麟": "謝瑞麟",
}


def fetch_from_hkgoldprice(retailer_zh: str) -> ScraperResult:
    """Fetch gold price for a specific retailer from hkgoldprice.com.

    URL pattern: https://hkgoldprice.com/shop/{retailer_name}
    """
    result = ScraperResult(retailer=retailer_zh)
    slug = HKGOLDPRICE_SHOPS.get(retailer_zh, retailer_zh)
    url = f"https://hkgoldprice.com/shop/{slug}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        result = _parse_aggregator_text(lines, result)
    except Exception as e:
        result.error = f"hkgoldprice.com fallback failed: {e}"

    return result


def fetch_all_from_goldpricehk() -> dict[str, ScraperResult]:
    """Fetch gold prices for all retailers from goldpricehk.com.

    Returns a dict mapping retailer Chinese names to ScraperResults.
    """
    results = {}
    url = "https://goldpricehk.com/"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # goldpricehk.com shows all retailers; try to split by retailer name
        current_retailer = None
        retailer_lines: dict[str, list[str]] = {}

        for line in lines:
            for name in ["周大福", "周生生", "六福", "謝瑞麟"]:
                if name in line:
                    current_retailer = name
                    retailer_lines.setdefault(current_retailer, [])
                    break
            if current_retailer:
                retailer_lines.setdefault(current_retailer, []).append(line)

        for name, rlines in retailer_lines.items():
            r = ScraperResult(retailer=name)
            r = _parse_aggregator_text(rlines, r)
            results[name] = r

    except Exception as e:
        for name in ["周大福", "周生生", "六福", "謝瑞麟"]:
            results[name] = ScraperResult(retailer=name, error=f"goldpricehk.com failed: {e}")

    return results


def fetch_from_aggregator_playwright(page, retailer_zh: str) -> ScraperResult:
    """Fetch gold price using Playwright from hkgoldprice.com."""
    result = ScraperResult(retailer=retailer_zh)
    slug = HKGOLDPRICE_SHOPS.get(retailer_zh, retailer_zh)
    url = f"https://hkgoldprice.com/shop/{slug}"

    try:
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        result = _parse_aggregator_text(lines, result)
    except Exception as e:
        result.error = f"hkgoldprice.com playwright fallback failed: {e}"

    return result


def _parse_price(text: str) -> float | None:
    if not text or text.strip() in ("-", "--", "N/A", ""):
        return None
    cleaned = text.strip().replace(",", "").replace("$", "").replace("HK", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_aggregator_text(lines: list[str], result: ScraperResult) -> ScraperResult:
    """Parse gold price from aggregator text lines.

    Aggregators typically show: 飾金 price per tael, possibly 金粒 price.
    """
    price_types = {
        "飾金": "飾金 999.9",
        "足金": "飾金 999.9",
        "999.9": "飾金 999.9",
        "金粒": "金粒",
        "金條": "金粒",
    }

    seen = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        matched = None
        for key, label in price_types.items():
            if key in line and "換" not in line and "鉑" not in line and label not in seen:
                matched = label
                seen.add(label)
                break

        if matched:
            numbers = []
            for j in range(max(0, i - 1), min(len(lines), i + 6)):
                val = _parse_price(lines[j])
                if val is not None:
                    numbers.append(val)

            if numbers:
                gp = GoldPrice(type=matched)
                nums_sorted = sorted(numbers[:4], reverse=True)
                gp.sell_per_tael = nums_sorted[0]
                if len(nums_sorted) > 1:
                    gp.buy_per_tael = nums_sorted[1]
                result.prices.append(gp)

        i += 1

    for line in lines:
        if "更新" in line or "update" in line.lower():
            result.last_updated = line.strip()
            break

    if not result.prices:
        result.error = "Could not parse gold prices from aggregator"
    return result
