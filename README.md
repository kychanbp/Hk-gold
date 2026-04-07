# HK Gold Price Monitor 香港金價監察

Monitor gold prices from major Hong Kong gold retailers in real-time.

## Supported Retailers 支持商戶

| Retailer | Chinese | Gold Price Page |
|----------|---------|-----------------|
| Chow Tai Fook | 周大福 | [chowtaifook.com](https://www.chowtaifook.com/zh-hk/eshop/realtime-gold-price.html) |
| Chow Sang Sang | 周生生 | [chowsangsang.com](https://www.chowsangsang.com/zh-hk/gold-price) |
| Luk Fook | 六福珠寶 | [goldprice.lukfook.com](https://goldprice.lukfook.com/tc.html) |
| TSL Jewellery | 謝瑞麟 | [tslj.com](https://www.tslj.com/zh-hk/) |
| Lao Pu Gold | 老鋪黃金 | [lphj.com](https://www.lphj.com/) |

## Price Types 價格類型

- **飾金 (Jewellery Gold 999.9)**: Gold used for jewellery, includes craftsmanship premium
- **金粒 (Gold Granules / Investment Gold)**: Pure gold pellets for investment, closer to spot price

Prices are shown in HKD per **兩 (tael)** and per **克 (gram)**.
- 1 tael (兩) = 37.429 grams

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# For playwright mode (headless browser), also install browsers:
playwright install chromium
```

## Usage

```bash
# Fetch once and display as table
python monitor.py

# Use headless browser (better for JS-rendered pages)
python monitor.py --mode playwright

# Auto-refresh every 5 minutes
python monitor.py --loop 300

# Output as JSON
python monitor.py --json

# Save to CSV (appends each fetch)
python monitor.py --csv

# Combine options
python monitor.py --mode playwright --loop 300 --csv
```

## Output Example

```
================================================================================
  香港金價監察 | HK Gold Price Monitor
  查詢時間: 2026-04-07 09:30:00
================================================================================

  📊 飾金價格 (Jewellery Gold 999.9)
  ──────────────────────────────────────────────────────────────────────────
  商戶 Retailer          賣出/兩 Sell    買入/兩 Buy    賣出/克 Sell    買入/克 Buy
  周大福 (Chow Tai Fook)      52,310        41,850     1,397.58     1,118.12
  周生生 (Chow Sang Sang)     51,010        40,810            -            -
  六福珠寶 (Luk Fook)         52,310        41,850     1,397.58     1,118.12
  謝瑞麟 (TSL Jewellery)      51,010        40,810            -            -

  📊 金粒價格 (Gold Granules / Investment Gold)
  ──────────────────────────────────────────────────────────────────────────
  商戶 Retailer          賣出/兩 Sell    買入/兩 Buy    賣出/克 Sell    買入/克 Buy
  周大福 (Chow Tai Fook)      46,890        42,750     1,252.77     1,142.16
  ...
```

## Project Structure

```
Hk-gold/
├── monitor.py              # Main entry point
├── requirements.txt        # Python dependencies
├── README.md
└── scrapers/
    ├── __init__.py         # Package exports
    ├── base.py             # Base classes (GoldPrice, GoldPriceScraper)
    ├── chowtaifook.py      # 周大福 scraper
    ├── chowsangsang.py     # 周生生 scraper
    ├── lukfook.py          # 六福珠寶 scraper
    ├── tsl.py              # 謝瑞麟 scraper
    └── laopu.py            # 老鋪黃金 scraper
```

## Notes

- **老鋪黃金 (Lao Pu Gold)** is a luxury ancient-craft gold brand (古法黃金) that does not publish standard daily gold prices like traditional retailers. Their products are priced at significant premiums over spot gold.
- Gold prices update during market hours (typically 9:00 AM - 5:00 PM HKT on business days).
- Use `--mode playwright` if `requests` mode returns errors — some sites require JavaScript rendering.
- The `--csv` option is useful for tracking price history over time.
