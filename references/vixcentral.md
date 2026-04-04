# VIXCentral

Treat VIXCentral as HTTP-only.

## Confirmed routes

- `http://vixcentral.com/ajax_update`
- `http://vixcentral.com/ajax_historical?n1=YYYY-MM-DD`
- `http://vixcentral.com/historical/?days=30`

The homepage help text also links to `http://vixcentral.com/historical/?days=30` for bulk historical downloads.

## Direct-call behavior

Direct HTTP calls can return placeholders such as:

- `"hello"`
- `"hello historical"`

In practice, the working direct path is to mimic the site's same-origin jQuery request headers, especially:

- `X-Requested-With: XMLHttpRequest`
- `Accept: application/json, text/javascript, */*; q=0.01`
- `Referer: http://vixcentral.com/`
- `Origin: http://vixcentral.com`

If the endpoint still returns placeholders or non-JSON after that, use browser automation instead of trusting the response.

## `ajax_historical` shape

The page JS treats historical data as a month-indexed array used to build a single curve:

- index `0`: start month number
- index `1..n`: historical contract values in display order

The client maps the values to calendar month labels using the start month.

## `ajax_update` shape

The live bundle is a positional array. Important indexes from the client code:

- `2`: last
- `3`: open
- `4`: bid
- `5`: high
- `6`: ask
- `7`: low
- `8`: VIX
- `9`: VXV
- `10`: VXST
- `11`: VXMT
- `12`: `[VXST, VIX, VXV, VXMT]`
- `13`: VIXMO
- `14`: weeklies

The page also stores `1` as quote-time data.

## Browser fallback

If the direct response is placeholder text or non-JSON:

1. Open `http://vixcentral.com/` in a real browser context.
2. Fetch the same-origin route from the loaded page.
3. Preserve the raw payload and attach a decoded summary in the output artifact.

Use the installed Playwright workflow for this path. The bundled helper script handles the switch automatically.
