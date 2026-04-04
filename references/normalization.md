# Optional Cross-Source Normalization

Only use this schema when the user explicitly asks to combine providers.

## Long-form schema

- `source`
- `dataset`
- `series_id`
- `symbol`
- `date`
- `value`
- `frequency`
- `units`
- `metadata_json`

## Notes

- `source` should be one of `fred`, `macrotrends`, `vixcentral`, `vix_utils`, `cboe`, `yahoo`, `westmetall`, `eia`, or `multpl`.
- `dataset` should preserve the provider-specific dataset or route identity.
- `series_id` is the provider-native id when available, such as a FRED series code or Macrotrends page id.
- `symbol` is optional and should only be filled when the source exposes a natural ticker or contract symbol.
- `metadata_json` should preserve provider-native metadata that does not fit the shared columns.

## Examples

- Westmetall
  - `source=westmetall`, `dataset=chart`, `series_id=LME_Cu_cash`
- EIA
  - `source=eia`, `dataset=LeafHandler.ashx`, `series_id=RWTC`
- Multpl
  - `source=multpl`, `dataset=table/by-year`, `series_id=s-p-500-pe-ratio`
- CBOE
  - `source=cboe`, `dataset=VIX_History`, `series_id=VIX`
- vix_utils
  - `source=vix_utils`, `dataset=spot-wide`, `series_id=` blank unless the downstream task wants a symbol-level split
