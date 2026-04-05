---
name: "agent-market-data-terminal"
description: "Use when tasks require a lightweight, no-auth market-data skill for BEA, Treasury FiscalData, Treasury rates feeds, BLS, World Bank, OECD, FRED, VIXCentral, Macrotrends, Yahoo Finance, Westmetall, EIA DNAV pages, Multpl, CBOE, or dougransom/vix_utils. Prefer BEA public files and `Data.json`, Treasury FiscalData JSON, Treasury TextView-linked XML/CSV feeds, BLS public v1, World Bank indicator JSON, OECD SDMX-JSON, direct FRED CSV URLs, Macrotrends `/economic-data/{page_id}/{chart_frequency}` JSON, Westmetall chart XML from `/api/marketdata/{lang}/{field}/`, EIA linked XLS/history pages, Multpl inline `pi` chart payloads and table views, VIXCentral term-structure routes with lightweight session-based retries, direct and archive-discovered CBOE CSV endpoints, direct `yfinance` for Yahoo history and current snapshots, and `vix_utils` for historical VIX term structure."
---

# Agent Market Data Terminal (aMDT)

Use this skill when a task needs lightweight, no-auth raw downloads, parsed tables, or provider-aware analysis from BEA, Treasury FiscalData, Treasury rates feeds, BLS, World Bank, OECD, FRED, VIXCentral, Macrotrends, Yahoo Finance, Westmetall, EIA DNAV pages, Multpl, CBOE, or `vix_utils`.

## Workflow

1. Identify the requested provider or providers and whether the user wants a raw export, parsed table, or combined analysis.
2. Prefer direct source endpoints and the bundled helper scripts before scraping visible tables.
3. Preserve each provider's native schema by default.
4. Only use the optional long-form schema in `references/normalization.md` when the user explicitly asks to combine sources.
5. Keep all writes inside the current workspace and make output paths explicit.

## Provider routing

- BEA
  Open `references/bea.md`, then use `scripts/fetch_bea.py`.
  Prefer direct public BEA files, then release-page discovery, then `Data.json` catalog matches.
- Treasury FiscalData
  Open `references/fiscaldata.md`, then use `scripts/fetch_fiscaldata.py`.
  Use this for Treasury JSON service endpoints such as debt or average-interest-rate datasets.
- Treasury Rates
  Open `references/treasury_rates.md`, then use `scripts/fetch_treasury_rates.py`.
  Use this for Treasury yield-curve, bill-rate, and real-yield feed data exposed through TextView-linked CSV/XML downloads.
- BLS
  Open `references/bls.md`, then use `scripts/fetch_bls.py`.
  Use the public v1 API without registration.
- World Bank
  Open `references/worldbank.md`, then use `scripts/fetch_worldbank.py`.
  Use this for no-auth indicator data and country/panel pulls.
- OECD
  Open `references/oecd.md`, then use `scripts/fetch_oecd.py`.
  Use this for SDMX-JSON datasets and keep series/observation dimensions provider-native.
- FRED
  Open `references/fred.md`, then use `scripts/fetch_fred.py`.
- Macrotrends
  Open `references/macrotrends.md`, then use `scripts/fetch_macrotrends.py`.
- VIXCentral
  Open `references/vixcentral.md`, then use `scripts/fetch_vixcentral.py`.
  The script tries direct HTTP first, then retries with homepage-primed `requests.Session()`, then optional `curl_cffi` impersonation when VIXCentral returns placeholders or non-JSON.
- Westmetall
  Open `references/westmetall.md`, then use `scripts/fetch_westmetall.py`.
  Prefer the chart XML endpoint first, then use `table` and `averages` HTML views when the user explicitly wants those views.
  The helper keeps raw chart fetches strict, but parsed chart requests can fall back to the table view if the XML endpoint is temporarily unavailable.
- EIA
  Open `references/eia.md`, then use `scripts/fetch_eia.py`.
  Prefer linked XLS files for raw downloads and for history-page parsing.
  Use HTML parsing for summary pages, metadata extraction, and explicit history fallback only.
- Multpl
  Open `references/multpl.md`, then use `scripts/fetch_multpl.py`.
  Prefer the inline `pi` chart payload for chart data, then use `/table/by-year`, `/table/by-month`, or `/atom` when the task asks for those native views.
- CBOE
  Open `references/cboe.md`, then use `scripts/fetch_cboe.py`.
  Prefer direct `cdn.cboe.com` CSV endpoints when the URL is known, or use futures-archive mode for the public settlement-archive page.
- vix_utils
  Open `references/vix_utils.md`, then use `scripts/fetch_vix_utils.py`.
  Use this provider for historical VIX futures/cash term structure when the user wants CBOE-backed research data instead of VIXCentral's live site routes.
- Yahoo Finance
  Open `references/yahoo.md`, then use `scripts/fetch_yfinance.py`.
  Keep Yahoo requests direct through `yfinance` and limit the helper surface to `history` and `current_snapshot`.

## Commands

```powershell
python .\scripts\fetch_bea.py --mode direct --url "https://www.bea.gov/sites/default/files/2026-03/pi0126.xlsx" --format parsed --output .\outputs\bea_pi0126.json
python .\scripts\fetch_fiscaldata.py --endpoint /accounting/od/avg_interest_rates --fields record_date,security_desc,avg_interest_rate_amt --filter record_date:gte:2020-01-01 --sort=-record_date --page-size 2 --format parsed --output .\outputs\fiscaldata_avg_interest_rates.json
python .\scripts\fetch_treasury_rates.py --dataset daily_treasury_yield_curve --year 2024 --view xml --format parsed --output .\outputs\treasury_yield_curve_2024.json
python .\scripts\fetch_bls.py --series-id CUSR0000SA0 --series-id LNS14000000 --start-year 2020 --end-year 2024 --format parsed --output .\outputs\bls_2020_2024.json
python .\scripts\fetch_worldbank.py --country US --indicator NY.GDP.MKTP.CD --date 2000:2024 --format parsed --output .\outputs\worldbank_us_gdp.json
python .\scripts\fetch_oecd.py --dataset MEI_CLI --series-key LOLITONO.USA.M --start-time 2000-01 --end-time 2001-12 --format parsed --output .\outputs\oecd_mei_cli.json
python .\scripts\fetch_fred.py --series-id GS10 --start 2020-01-01 --end 2026-04-01 --output .\outputs\gs10.csv
python .\scripts\fetch_macrotrends.py --page-url "https://www.macrotrends.net/datasets/1476/copper-prices-historical-chart-data" --chart-frequency D --output .\outputs\macrotrends_copper_daily.json
python .\scripts\fetch_vixcentral.py --mode historical --date 2026-04-02 --output .\outputs\vixcentral_2026-04-02.json
python .\scripts\fetch_westmetall.py --field LME_Cu_cash --view chart --format parsed --output .\outputs\westmetall_lme_cu_chart.json
python .\scripts\fetch_eia.py --page-url "https://www.eia.gov/dnav/pet/hist/RWTCD.htm" --format parsed --source auto --output .\outputs\eia_rwtc_daily.json
python .\scripts\fetch_multpl.py --page-url "https://www.multpl.com/s-p-500-pe-ratio" --view chart --format parsed --output .\outputs\multpl_sp500_pe.json
python .\scripts\fetch_cboe.py --url "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv" --format parsed --output .\outputs\cboe_vix_history.json
python .\scripts\fetch_cboe.py --mode futures-archive --product VX --year 2013 --format parsed --output .\outputs\cboe_vx_archive_2013.json
python .\scripts\fetch_vix_utils.py --dataset spot-wide --format parsed --output .\outputs\vix_utils_spot_wide.json
python .\scripts\fetch_yfinance.py --dataset history --ticker SPY --ticker TLT --start 2020-01-01 --end today --interval 1d --format parsed --output .\outputs\yfinance_history.json
python .\scripts\fetch_yfinance.py --dataset current_snapshot --ticker ^VIX --ticker SPY --format parsed --output .\outputs\yfinance_snapshot.json
```

## When to load references

- Open `references/bea.md` for direct BEA files, release-page discovery, and `Data.json` catalog usage.
- Open `references/fiscaldata.md` for Treasury FiscalData endpoint/query handling.
- Open `references/treasury_rates.md` for TextView-linked CSV/XML feed discovery and supported datasets.
- Open `references/bls.md` for BLS public v1 request shapes.
- Open `references/worldbank.md` for indicator endpoint behavior and pagination notes.
- Open `references/oecd.md` for SDMX-JSON route structure and flattening expectations.
- Open `references/fred.md` for valid FRED parameters and the clean CSV contract.
- Open `references/macrotrends.md` for page-id extraction and valid `chart_frequency` codes.
- Open `references/vixcentral.md` for route behavior, array shapes, and the lightweight retry order.
- Open `references/westmetall.md` for field discovery, chart XML, and table/averages fallbacks.
- Open `references/eia.md` for DNAV summary pages, static and `LeafHandler` history pages, linked XLS files, and parsed-history source policy.
- Open `references/multpl.md` for the inline `pi` array, table-by-year/month views, estimate markers, and Atom feed usage.
- Open `references/cboe.md` for direct CSV endpoint patterns and parsed/raw guidance.
- Open `references/vix_utils.md` for dataset routing and cache-directory handling.
- Open `references/yahoo.md` for the direct `yfinance` helper contract, supported datasets, and snapshot-output notes.
- Open `references/normalization.md` only when a task explicitly needs cross-source merging.

## Guardrails

- Do not use the key-based BEA API in this skill; use public files, release pages, or `Data.json` instead.
- Use FiscalData for Treasury JSON service endpoints, but use `treasury_rates` for yield-curve and bill-rate feeds.
- Use BLS public v1 only; v2 registration features are out of scope here.
- World Bank raw mode should keep the native two-element JSON page response. Parsed mode may paginate to complete the requested panel.
- For OECD, flatten SDMX dimensions and attributes into rows without inventing a cross-source schema.
- Do not scrape visible HTML tables from Macrotrends when the JSON endpoint is available.
- Prefer Westmetall `/api/marketdata/{lang}/{field}/` chart XML over HTML tables when the task is a chart-series request.
- For EIA DNAV pages, prefer linked XLS files for raw downloads and for history parsing. Use HTML only for summary parsing, metadata extraction, or explicit history fallback.
- For Multpl chart pages, parse the inline `pi` array instead of scraping the rendered canvas.
- Treat VIXCentral as HTTP-only unless the site changes.
- If VIXCentral direct calls return `"hello"` or `"hello historical"`, let the helper script retry with session priming and optional `curl_cffi` instead of inventing data.
- For CBOE futures archive requests, use the public settlement-archive page or known direct CSVs instead of scraping rendered tables.
- For `vix_utils`, keep cache and downloaded data inside the workspace-local cache directory.
- For Yahoo Finance, use direct `yfinance` through `fetch_yfinance.py`; do not require a separate repo checkout or YAML export config.
- Do not normalize providers into one schema unless the user asked for that.
