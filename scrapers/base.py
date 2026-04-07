"""Base classes for gold price scrapers."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class GoldPrice:
    """A single gold price entry."""

    type: str  # e.g. "飾金 999.9", "金粒 (投資金)"
    sell_per_gram: Optional[float] = None  # HKD per gram
    sell_per_tael: Optional[float] = None  # HKD per tael (兩)
    buy_per_gram: Optional[float] = None   # HKD per gram
    buy_per_tael: Optional[float] = None   # HKD per tael (兩)


@dataclass
class ScraperResult:
    """Result from a scraper."""

    retailer: str
    prices: list[GoldPrice] = field(default_factory=list)
    last_updated: Optional[str] = None
    error: Optional[str] = None
    fetched_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class GoldPriceScraper:
    """Base class for gold price scrapers."""

    name: str = "Unknown"
    name_zh: str = "未知"
    url: str = ""

    def scrape_with_requests(self) -> ScraperResult:
        """Scrape using requests + BeautifulSoup (faster, but may not work for JS-rendered pages)."""
        raise NotImplementedError

    def scrape_with_playwright(self, page) -> ScraperResult:
        """Scrape using Playwright (slower, but handles JS-rendered pages)."""
        raise NotImplementedError

    def _make_result(self, error: Optional[str] = None) -> ScraperResult:
        return ScraperResult(retailer=f"{self.name_zh} ({self.name})", error=error)

    def _parse_price(self, text: str) -> Optional[float]:
        """Parse a price string like '1,397.58' or '52,310' into a float."""
        if not text or text.strip() in ("-", "--", "N/A", ""):
            return None
        cleaned = text.strip().replace(",", "").replace("$", "").replace("HK", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
