# Agent Market Data Terminal (aMDT)

Agent Market Data Terminal (aMDT) is a lightweight LLM skill built to give both autonomous agents and cloud chatbots direct access to market and macro data for research and backtesting rule-based trading theories. The repo is intentionally designed around public endpoints that do not require API keys or authentication, so the skill stays easy to run and easy to distribute.

`agent-market-data-terminal` is the Codex skill packaged by this repository, and it pulls market and macro data from:

- BEA public files and `Data.json`
- Treasury FiscalData
- Treasury daily rates feeds
- BLS public v1
- World Bank
- OECD
- Kenneth French Data Library via direct Fama/French CSV zips
- FRED
- VIXCentral
- CBOE
- `dougransom/vix_utils`
- Macrotrends
- Westmetall
- EIA DNAV
- Multpl
- Yahoo Finance via direct `yfinance`

The skill is native-first. It prefers direct machine-readable provider sources such as BEA public files, Treasury FiscalData JSON, Treasury rate feeds, BLS v1 JSON, World Bank indicator JSON, OECD SDMX-JSON, Kenneth French `_CSV.zip` feeds, FRED CSV, Macrotrends JSON, Westmetall chart XML, linked EIA XLS workbooks for history pages, VIXCentral XHR-style routes, CBOE CSV endpoints, `vix_utils`' CBOE-backed history loaders, and Multpl's inline chart payload.

## Install

### Codex

Clone or copy this repository into your Codex skills directory as:

```text
$CODEX_HOME/skills/agent-market-data-terminal
```

After installation, Codex can use the skill as `$agent-market-data-terminal`.

### Claude Code

Clone or copy this repository into your Claude Code skills directory.

For a user-global install (available in all projects):

```text
~/.claude/skills/agent-market-data-terminal/
```

For a project-local install (available only in a specific project):

```text
.claude/skills/agent-market-data-terminal/
```

After installation, Claude Code can use the skill as `/agent-market-data-terminal`.

Claude Code also reads `CLAUDE.md` automatically when you open this repository as a project directory, providing layout and routing context without an explicit invocation.

## Layout

- [SKILL.md](./SKILL.md): trigger metadata and workflow (shared by Codex and Claude Code)
- [agents/openai.yaml](./agents/openai.yaml): Codex UI metadata
- [agents/claude.md](./agents/claude.md): Claude Code metadata
- [CLAUDE.md](./CLAUDE.md): Claude Code auto-loaded project context
- [references/](./references/): provider-specific guidance and source contracts
- [scripts/](./scripts/): fetch helpers for each provider

## Notes

- EIA history parsing prefers linked `.xls` workbooks and uses Python-native `xlrd` for structured history extraction instead of Windows-only COM automation.
- VIXCentral no longer depends on Playwright. The helper uses direct requests first, then a homepage-primed `requests.Session()`, then optional `curl_cffi` impersonation if needed.
- BEA is implemented as a no-auth file/catalog source. It uses direct public files, BEA release pages, and `https://apps.bea.gov/Data.json` instead of the key-based API.
- Treasury yield-curve and bill-rate data come from Treasury's official TextView-linked CSV/XML feeds, not FiscalData.
- Fama/French support is structured-feed only. The helper accepts direct Kenneth French `_CSV.zip` feeds and direct archive zip URLs, and rejects HTML page scraping.
- Westmetall chart parsing is XML-first. Raw chart fetches remain XML-only, while parsed chart mode can fall back to the daily HTML table if the XML endpoint is temporarily unavailable.
- `vix_utils` is exposed as a separate historical provider and keeps its cache inside a workspace-local directory when used through the bundled helper.
- The Yahoo path uses direct `yfinance` inside this repo and keeps only the lightweight `history` and `current_snapshot` datasets.

## Optional Python dependencies

Some helpers depend on lightweight optional packages:

- `openpyxl` for parsed BEA `.xlsx` workbooks
- `pandas` for the direct Yahoo helper and some dataframe-backed providers
- `yfinance` for direct Yahoo Finance access
- `xlrd` for EIA history workbook parsing
- `curl_cffi` for the optional VIXCentral TLS-impersonation fallback
- `vix_utils` for the standalone historical VIX term-structure provider

The repo keeps imports lazy or guarded so syntax validation still passes even when these packages are not installed.

## Validation

This repository includes a lightweight GitHub Actions workflow that runs Python syntax checks over the bundled scripts.
