#!/usr/bin/env python3
"""
HK Gold Price Monitor
=====================
Monitors gold prices from major Hong Kong gold retailers:
- 周大福 (Chow Tai Fook)
- 周生生 (Chow Sang Sang)
- 六福珠寶 (Luk Fook)
- 謝瑞麟 (TSL Jewellery)
- 老鋪黃金 (Lao Pu Gold)

Usage:
    python monitor.py                    # Fetch once and display
    python monitor.py --mode playwright  # Use headless browser (for JS-heavy sites)
    python monitor.py --loop 300         # Fetch every 300 seconds (5 min)
    python monitor.py --json             # Output as JSON
    python monitor.py --csv              # Append to CSV file
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional

from tabulate import tabulate

from scrapers import ALL_SCRAPERS
from scrapers.base import GoldPriceScraper, ScraperResult


def fetch_all_prices(mode: str = "requests") -> list[ScraperResult]:
    """Fetch gold prices from all retailers."""
    results = []

    if mode == "playwright":
        results = _fetch_with_playwright()
    else:
        results = _fetch_with_requests()

    return results


def _fetch_with_requests() -> list[ScraperResult]:
    results = []
    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        print(f"  Fetching {scraper.name_zh} ({scraper.name})...", end=" ", flush=True)
        try:
            result = scraper.scrape_with_requests()
            if result.error:
                print(f"⚠ {result.error[:60]}")
            else:
                print(f"✓ {len(result.prices)} price(s)")
        except Exception as e:
            result = scraper._make_result(error=str(e))
            print(f"✗ {e}")
        results.append(result)
    return results


def _fetch_with_playwright() -> list[ScraperResult]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: playwright not installed. Run: pip install playwright && playwright install")
        sys.exit(1)

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu"],
        )
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        for scraper_cls in ALL_SCRAPERS:
            scraper = scraper_cls()
            print(f"  Fetching {scraper.name_zh} ({scraper.name})...", end=" ", flush=True)
            try:
                result = scraper.scrape_with_playwright(page)
                if result.error:
                    print(f"⚠ {result.error[:60]}")
                else:
                    print(f"✓ {len(result.prices)} price(s)")
            except Exception as e:
                result = scraper._make_result(error=str(e))
                print(f"✗ {e}")
            results.append(result)

        browser.close()
    return results


def format_price(value: Optional[float]) -> str:
    if value is None:
        return "-"
    if value >= 10000:
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def display_results(results: list[ScraperResult]):
    """Display results as a formatted table."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*80}")
    print(f"  香港金價監察 | HK Gold Price Monitor")
    print(f"  查詢時間: {now}")
    print(f"{'='*80}")

    # Jewellery Gold (飾金) table
    print(f"\n  📊 飾金價格 (Jewellery Gold 999.9)")
    print(f"  {'─'*70}")

    jewellery_rows = []
    for r in results:
        for p in r.prices:
            if "飾金" in p.type:
                jewellery_rows.append([
                    r.retailer,
                    format_price(p.sell_per_tael),
                    format_price(p.buy_per_tael),
                    format_price(p.sell_per_gram),
                    format_price(p.buy_per_gram),
                ])
                break
        else:
            if not r.error or "老鋪" in r.retailer:
                continue
            jewellery_rows.append([r.retailer, "-", "-", "-", "-"])

    if jewellery_rows:
        print(tabulate(
            jewellery_rows,
            headers=["商戶 Retailer", "賣出/兩 Sell", "買入/兩 Buy", "賣出/克 Sell", "買入/克 Buy"],
            tablefmt="simple",
            stralign="right",
            numalign="right",
        ))
    else:
        print("  No jewellery gold data available.")

    # Gold Granules (金粒) table
    print(f"\n  📊 金粒價格 (Gold Granules / Investment Gold)")
    print(f"  {'─'*70}")

    granule_rows = []
    for r in results:
        for p in r.prices:
            if "金粒" in p.type:
                granule_rows.append([
                    r.retailer,
                    format_price(p.sell_per_tael),
                    format_price(p.buy_per_tael),
                    format_price(p.sell_per_gram),
                    format_price(p.buy_per_gram),
                ])
                break
        else:
            if not r.error or "老鋪" in r.retailer:
                continue
            granule_rows.append([r.retailer, "-", "-", "-", "-"])

    if granule_rows:
        print(tabulate(
            granule_rows,
            headers=["商戶 Retailer", "賣出/兩 Sell", "買入/兩 Buy", "賣出/克 Sell", "買入/克 Buy"],
            tablefmt="simple",
            stralign="right",
            numalign="right",
        ))
    else:
        print("  No gold granule data available.")

    # Errors / Notes
    errors = [(r.retailer, r.error) for r in results if r.error]
    if errors:
        print(f"\n  ⚠ 備註 Notes:")
        for retailer, error in errors:
            print(f"    • {retailer}: {error}")

    # Last updated times
    updates = [(r.retailer, r.last_updated) for r in results if r.last_updated]
    if updates:
        print(f"\n  🕐 數據更新時間:")
        for retailer, updated in updates:
            print(f"    • {retailer}: {updated}")

    print(f"\n{'='*80}\n")


def output_json(results: list[ScraperResult]):
    """Output results as JSON."""
    data = {
        "fetched_at": datetime.now().isoformat(),
        "retailers": [],
    }
    for r in results:
        retailer_data = {
            "name": r.retailer,
            "last_updated": r.last_updated,
            "error": r.error,
            "prices": [],
        }
        for p in r.prices:
            retailer_data["prices"].append({
                "type": p.type,
                "sell_per_gram": p.sell_per_gram,
                "sell_per_tael": p.sell_per_tael,
                "buy_per_gram": p.buy_per_gram,
                "buy_per_tael": p.buy_per_tael,
            })
        data["retailers"].append(retailer_data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def append_csv(results: list[ScraperResult], filepath: str = "gold_prices.csv"):
    """Append results to a CSV file."""
    file_exists = os.path.exists(filepath)
    now = datetime.now().isoformat()

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "retailer", "type",
                "sell_per_gram", "sell_per_tael",
                "buy_per_gram", "buy_per_tael",
            ])
        for r in results:
            for p in r.prices:
                writer.writerow([
                    now, r.retailer, p.type,
                    p.sell_per_gram, p.sell_per_tael,
                    p.buy_per_gram, p.buy_per_tael,
                ])

    print(f"  Data appended to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="HK Gold Price Monitor")
    parser.add_argument(
        "--mode", choices=["requests", "playwright"], default="requests",
        help="Scraping mode: 'requests' (fast) or 'playwright' (headless browser, for JS pages)"
    )
    parser.add_argument(
        "--loop", type=int, default=0,
        help="Loop interval in seconds (0 = fetch once and exit)"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--csv", action="store_true", help="Append results to CSV file")
    parser.add_argument("--csv-file", default="gold_prices.csv", help="CSV output file path")
    args = parser.parse_args()

    while True:
        print(f"\n🔍 Fetching gold prices (mode: {args.mode})...")
        results = fetch_all_prices(mode=args.mode)

        if args.json:
            output_json(results)
        else:
            display_results(results)

        if args.csv:
            append_csv(results, filepath=args.csv_file)

        if args.loop <= 0:
            break

        print(f"⏳ Next update in {args.loop} seconds... (Ctrl+C to stop)")
        try:
            time.sleep(args.loop)
        except KeyboardInterrupt:
            print("\n👋 Monitor stopped.")
            break


if __name__ == "__main__":
    main()
