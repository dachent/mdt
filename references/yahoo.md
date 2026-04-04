# Yahoo Finance via `yf_marketdata`

Reuse the existing `dachent/yf_marketdata` project instead of re-implementing Yahoo logic in this skill.

## Run command

```powershell
python -m yf_marketdata .\yf_marketdata_live.yaml
```

## Confirmed config sections

- `source`
- `history`
- `lookup`
- `fetch`
- `outputs`

## Confirmed datasets

- `history_yf`
- `history_raw`
- `history_adjusted`
- `history_summary`
- `ticker_search`
- `current_snapshot`

## Useful repo facts

- The module entrypoint is `yf_marketdata/__main__.py`.
- `outputs.root_dir`, dataset layout, and `outputs.format` control the written artifacts.
- `lookup.full_quote_results` must be true when `ticker_search` is enabled.
- `current_snapshot` is the wide one-row-per-ticker dataset for current quote, fundamentals, targets, and EPS trend.

## Expected wrapper behavior

The helper script should:

1. Validate the repo path and config path.
2. Confirm the repo looks like `yf_marketdata`.
3. Run `python -m yf_marketdata <config.yaml>` with the repo as the working directory.
