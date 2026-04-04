# fetch-cross-market-data

`fetch-cross-market-data` is a Codex skill for pulling market and macro data from:

- FRED
- VIXCentral
- CBOE
- `dougransom/vix_utils`
- Macrotrends
- Westmetall
- EIA DNAV
- Multpl
- Yahoo Finance via [`dachent/yf_marketdata`](https://github.com/dachent/yf_marketdata)

The skill is native-first. It prefers direct machine-readable provider sources such as FRED CSV, Macrotrends JSON, Westmetall chart XML, linked EIA XLS workbooks for history pages, VIXCentral XHR-style routes, CBOE CSV endpoints, `vix_utils`' CBOE-backed history loaders, and Multpl's inline chart payload.

## Install

Clone or copy this repository into your Codex skills directory as:

```text
$CODEX_HOME/skills/fetch-cross-market-data
```

After installation, Codex can use the skill as `$fetch-cross-market-data`.

## Layout

- [SKILL.md](./SKILL.md): trigger metadata and workflow
- [agents/openai.yaml](./agents/openai.yaml): Codex UI metadata
- [references/](./references/): provider-specific guidance and source contracts
- [scripts/](./scripts/): fetch helpers for each provider
- [assets/yf_marketdata.template.yaml](./assets/yf_marketdata.template.yaml): starter config for Yahoo exports

## Notes

- EIA history parsing prefers linked `.xls` workbooks and uses Python-native `xlrd` for structured history extraction instead of Windows-only COM automation.
- VIXCentral no longer depends on Playwright. The helper uses direct requests first, then a homepage-primed `requests.Session()`, then optional `curl_cffi` impersonation if needed.
- Westmetall chart parsing is XML-first. Raw chart fetches remain XML-only, while parsed chart mode can fall back to the daily HTML table if the XML endpoint is temporarily unavailable.
- `vix_utils` is exposed as a separate historical provider and keeps its cache inside a workspace-local directory when used through the bundled helper.
- The Yahoo path reuses the upstream `yf_marketdata` CLI instead of reimplementing Yahoo logic inside this repo.

## Optional Python dependencies

Some helpers depend on lightweight optional packages:

- `xlrd` for EIA history workbook parsing
- `curl_cffi` for the optional VIXCentral TLS-impersonation fallback
- `vix_utils` for the standalone historical VIX term-structure provider

The repo keeps imports lazy or guarded so syntax validation still passes even when these packages are not installed.

## Validation

This repository includes a lightweight GitHub Actions workflow that runs Python syntax checks over the bundled scripts.
