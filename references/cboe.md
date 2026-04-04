# CBOE

Use CBOE as a general direct-source provider when the user already has a CSV endpoint or when the requested dataset clearly maps to the public CDN CSV patterns.

## Direct CSV pattern

- Base pattern:
  - `https://cdn.cboe.com/api/global/us_indices/daily_prices/{symbol}_History.csv`

## Confirmed examples

- `https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv`
- `https://cdn.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv`
- `https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv`

## Native payloads

- `VIX_History.csv` and similar OHLC series use headers such as:
  - `DATE,OPEN,HIGH,LOW,CLOSE`
- Some index series are single-value histories instead, for example:
  - `DATE,VVIX`

## Guidance

- Prefer the direct CSV endpoint over HTML pages when the user already has the CBOE data URL.
- Raw mode should preserve the native CSV unchanged.
- Parsed mode should keep the provider-native columns and row order instead of forcing a cross-source schema.
