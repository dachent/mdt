---
name: "fetch-cross-market-data"
description: "Use when tasks require fetching market data from FRED, VIXCentral, Macrotrends, Yahoo Finance, Westmetall, EIA DNAV pages, Multpl, CBOE CSV endpoints, or dougransom/vix_utils. Prefer direct FRED CSV URLs, Macrotrends `/economic-data/{page_id}/{chart_frequency}` JSON, Westmetall chart XML from `/api/marketdata/{lang}/{field}/`, EIA linked XLS/history pages, Multpl inline `pi` chart payloads and table views, VIXCentral term-structure routes with lightweight session-based retries, direct CBOE CSV endpoints, `vix_utils` for historical VIX term structure, and the `dachent/yf_marketdata` CLI for Yahoo Finance exports."
---

# Fetch Cross-Market Data

Use this skill when a task needs raw downloads, parsed tables, or provider-aware analysis from FRED, VIXCentral, Macrotrends, Yahoo Finance, Westmetall, EIA DNAV pages, Multpl, CBOE, or `vix_utils`.

## Workflow

1. Identify the requested provider or providers and whether the user wants a raw export, parsed table, or combined analysis.
2. Prefer direct source endpoints and the bundled helper scripts before scraping visible tables.
3. Preserve each provider's native schema by default.
4. Only use the optional long-form schema in `references/normalization.md` when the user explicitly asks to combine sources.
5. Keep all writes inside the current workspace and make output paths explicit.

## Provider routing

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
  Prefer direct `cdn.cboe.com` CSV endpoints and preserve the native CSV in raw mode.
- vix_utils
  Open `references/vix_utils.md`, then use `scripts/fetch_vix_utils.py`.
  Use this provider for historical VIX futures/cash term structure when the user wants CBOE-backed research data instead of VIXCentral's live site routes.
- Yahoo Finance
  Open `references/yahoo.md`, use `assets/yf_marketdata.template.yaml` as a starting point, and run `scripts/run_yf_marketdata.py` against an existing `dachent/yf_marketdata` checkout.

## Commands

```powershell
python .\scripts\fetch_fred.py --series-id GS10 --start 2020-01-01 --end 2026-04-01 --output .\outputs\gs10.csv
python .\scripts\fetch_macrotrends.py --page-url "https://www.macrotrends.net/datasets/1476/copper-prices-historical-chart-data" --chart-frequency D --output .\outputs\macrotrends_copper_daily.json
python .\scripts\fetch_vixcentral.py --mode historical --date 2026-04-02 --output .\outputs\vixcentral_2026-04-02.json
python .\scripts\fetch_westmetall.py --field LME_Cu_cash --view chart --format parsed --output .\outputs\westmetall_lme_cu_chart.json
python .\scripts\fetch_eia.py --page-url "https://www.eia.gov/dnav/pet/hist/RWTCD.htm" --format parsed --source auto --output .\outputs\eia_rwtc_daily.json
python .\scripts\fetch_multpl.py --page-url "https://www.multpl.com/s-p-500-pe-ratio" --view chart --format parsed --output .\outputs\multpl_sp500_pe.json
python .\scripts\fetch_cboe.py --url "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv" --format parsed --output .\outputs\cboe_vix_history.json
python .\scripts\fetch_vix_utils.py --dataset spot-wide --format parsed --output .\outputs\vix_utils_spot_wide.json
python .\scripts\run_yf_marketdata.py --repo-path ..\yf_marketdata --config-path .\assets\yf_marketdata.template.yaml
```

## When to load references

- Open `references/fred.md` for valid FRED parameters and the clean CSV contract.
- Open `references/macrotrends.md` for page-id extraction and valid `chart_frequency` codes.
- Open `references/vixcentral.md` for route behavior, array shapes, and the lightweight retry order.
- Open `references/westmetall.md` for field discovery, chart XML, and table/averages fallbacks.
- Open `references/eia.md` for DNAV summary pages, static and `LeafHandler` history pages, linked XLS files, and parsed-history source policy.
- Open `references/multpl.md` for the inline `pi` array, table-by-year/month views, estimate markers, and Atom feed usage.
- Open `references/cboe.md` for direct CSV endpoint patterns and parsed/raw guidance.
- Open `references/vix_utils.md` for dataset routing and cache-directory handling.
- Open `references/yahoo.md` for the confirmed `yf_marketdata` config structure and datasets.
- Open `references/normalization.md` only when a task explicitly needs cross-source merging.

## Guardrails

- Do not scrape visible HTML tables from Macrotrends when the JSON endpoint is available.
- Prefer Westmetall `/api/marketdata/{lang}/{field}/` chart XML over HTML tables when the task is a chart-series request.
- For EIA DNAV pages, prefer linked XLS files for raw downloads and for history parsing. Use HTML only for summary parsing, metadata extraction, or explicit history fallback.
- For Multpl chart pages, parse the inline `pi` array instead of scraping the rendered canvas.
- Treat VIXCentral as HTTP-only unless the site changes.
- If VIXCentral direct calls return `"hello"` or `"hello historical"`, let the helper script retry with session priming and optional `curl_cffi` instead of inventing data.
- For `vix_utils`, keep cache and downloaded data inside the workspace-local cache directory.
- Do not normalize providers into one schema unless the user asked for that.
