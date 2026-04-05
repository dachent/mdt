# Agent Market Data Terminal (aMDT) — Claude Code Project Context

Agent Market Data Terminal (aMDT) is a lightweight, no-auth LLM skill that provides direct access to market and macro data from BEA, Treasury FiscalData, Treasury rates feeds, BLS, World Bank, OECD, Kenneth French Data Library, FRED, VIXCentral, Macrotrends, Yahoo Finance via yfinance, Westmetall, EIA DNAV, Multpl, CBOE, and dougransom/vix_utils. All providers use public endpoints that require no API keys.

## Skill invocation

The skill definition lives in `SKILL.md` with frontmatter `name: "agent-market-data-terminal"`.

**Claude Code** — invoke with:
```
/agent-market-data-terminal
```

**Codex** — invoke with:
```
$agent-market-data-terminal
```

## Repository layout

| Path | Purpose |
|------|---------|
| `SKILL.md` | Skill trigger metadata and workflow — shared by Codex and Claude Code |
| `agents/openai.yaml` | Codex UI metadata only |
| `agents/claude.md` | Claude Code metadata only |
| `references/` | Provider-specific reference docs (16 files) |
| `scripts/` | Python fetch helpers, one per provider (16 files) |

## Provider routing summary

| Provider | Reference | Script |
|----------|-----------|--------|
| BEA | `references/bea.md` | `scripts/fetch_bea.py` |
| Treasury FiscalData | `references/fiscaldata.md` | `scripts/fetch_fiscaldata.py` |
| Treasury Rates | `references/treasury_rates.md` | `scripts/fetch_treasury_rates.py` |
| BLS | `references/bls.md` | `scripts/fetch_bls.py` |
| World Bank | `references/worldbank.md` | `scripts/fetch_worldbank.py` |
| OECD | `references/oecd.md` | `scripts/fetch_oecd.py` |
| Fama/French | `references/famafrench.md` | `scripts/fetch_famafrench.py` |
| FRED | `references/fred.md` | `scripts/fetch_fred.py` |
| Macrotrends | `references/macrotrends.md` | `scripts/fetch_macrotrends.py` |
| VIXCentral | `references/vixcentral.md` | `scripts/fetch_vixcentral.py` |
| Westmetall | `references/westmetall.md` | `scripts/fetch_westmetall.py` |
| EIA | `references/eia.md` | `scripts/fetch_eia.py` |
| Multpl | `references/multpl.md` | `scripts/fetch_multpl.py` |
| CBOE | `references/cboe.md` | `scripts/fetch_cboe.py` |
| vix_utils | `references/vix_utils.md` | `scripts/fetch_vix_utils.py` |
| Yahoo Finance | `references/yahoo.md` | `scripts/fetch_yfinance.py` |

Open the relevant `references/*.md` file before running a script. See `SKILL.md` for full provider routing rules and guardrails.

## Workspace conventions

- All output files go inside the current workspace directory.
- Every script invocation must include an explicit `--output` path.
- Never write files outside the workspace.
- Cross-source normalization (`references/normalization.md`) is only for tasks that explicitly require merging providers.

## Optional Python dependencies

Some helpers require optional packages. Install as needed:

```
pip install openpyxl      # BEA .xlsx workbook parsing
pip install pandas        # Yahoo Finance and some dataframe-backed providers
pip install yfinance      # Yahoo Finance direct access
pip install xlrd          # EIA history workbook parsing
pip install curl_cffi     # VIXCentral TLS-impersonation fallback (optional)
pip install vix_utils     # Standalone historical VIX term-structure provider
```

Scripts guard optional imports so syntax validation passes even when packages are absent.
