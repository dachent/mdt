#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
from datetime import date
from pathlib import Path
from shutil import which
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "http://vixcentral.com"
PLACEHOLDER_RESPONSES = {"hello", "hello historical"}
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
IMPORTANT_LIVE_INDEXES = {
    "time_data": 1,
    "last": 2,
    "open": 3,
    "bid": 4,
    "high": 5,
    "ask": 6,
    "low": 7,
    "vix": 8,
    "vxv": 9,
    "vxst": 10,
    "vxmt": 11,
    "vcurve": 12,
    "vixmo": 13,
    "weeklies": 14,
}
XHR_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": f"{BASE_URL}/",
    "Origin": BASE_URL,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch VIXCentral live or historical data.")
    parser.add_argument("--mode", required=True, choices=["live", "historical"], help="Fetch live term structure or a historical curve.")
    parser.add_argument("--date", help="Historical date in YYYY-MM-DD.")
    parser.add_argument("--days", type=int, help="Bulk historical days for /historical/?days=N.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.mode == "historical":
        if args.date and args.days:
            raise ValueError("Use either --date or --days for historical mode, not both.")
        if not args.date and not args.days:
            raise ValueError("Historical mode requires --date or --days.")
        if args.date:
            date.fromisoformat(args.date)
        if args.days is not None and args.days < 1:
            raise ValueError("--days must be >= 1.")
    elif args.date or args.days:
        raise ValueError("--date and --days are only valid with --mode historical.")


def fetch_text(url: str, *, headers: dict[str, str] | None = None) -> str:
    request_headers = {"User-Agent": "Codex fetch-cross-market-data/1.0"}
    if headers:
        request_headers.update(headers)
    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def direct_route_for(args: argparse.Namespace) -> str:
    if args.mode == "live":
        return f"{BASE_URL}/ajax_update"
    if args.days is not None:
        return f"{BASE_URL}/historical/?{urlencode({'days': args.days})}"
    return f"{BASE_URL}/ajax_historical?{urlencode({'n1': args.date})}"


def parse_json_text(raw_text: str) -> Any | None:
    stripped = raw_text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def is_placeholder_or_html(raw_text: str, parsed: Any | None) -> bool:
    stripped = raw_text.strip().strip('"').strip().lower()
    if stripped in PLACEHOLDER_RESPONSES:
        return True
    if raw_text.lstrip().startswith("<!DOCTYPE") or raw_text.lstrip().startswith("<html"):
        return True
    if parsed is None:
        return True
    if isinstance(parsed, str) and parsed.strip().lower() in PLACEHOLDER_RESPONSES:
        return True
    return False


def decode_live_bundle(bundle: Any) -> dict[str, Any]:
    if not isinstance(bundle, list):
        return {}
    decoded: dict[str, Any] = {}
    for label, index in IMPORTANT_LIVE_INDEXES.items():
        decoded[label] = bundle[index] if index < len(bundle) else None
    return decoded


def decode_historical_curve(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not payload:
        return []
    try:
        start_month = int(payload[0])
    except (TypeError, ValueError):
        return []

    curve: list[dict[str, Any]] = []
    for offset, value in enumerate(payload[1:]):
        month_index = (start_month + offset - 1) % 12
        curve.append(
            {
                "month": MONTH_NAMES[month_index],
                "value": value,
                "is_active": isinstance(value, (int, float)) and value > 0,
            }
        )
    return curve


def resolve_npx() -> str:
    npx_path = which("npx") or which("npx.cmd")
    if not npx_path:
        raise RuntimeError("npx is required for the VIXCentral browser fallback.")
    return npx_path


def run_playwright(npx_path: str, session: str, cache_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NPM_CONFIG_CACHE"] = str(cache_dir)
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(cache_dir / "ms-playwright")
    env["PLAYWRIGHT_DAEMON_SESSION_DIR"] = str(cache_dir / "ms-playwright" / "daemon")
    command = [
        npx_path,
        "--yes",
        "--package",
        "@playwright/cli",
        "playwright-cli",
        "--session",
        session,
        *args,
    ]
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=180,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Playwright command failed: {' '.join(command)}\n{details}") from exc


def fetch_with_playwright(args: argparse.Namespace, output_path: Path) -> tuple[Any, str]:
    npx_path = resolve_npx()
    cache_dir = output_path.parent / ".npm-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    session = f"vixcentral-{secrets.token_hex(4)}"
    base_page = f"{BASE_URL}/"

    if args.mode == "live":
        route = "/ajax_update"
    elif args.days is not None:
        route = f"/historical/?days={args.days}"
    else:
        route = f"/ajax_historical?n1={args.date}"

    eval_code = (
        "async () => {"
        f"  const response = await fetch({json.dumps(route)});"
        "  return await response.text();"
        "}"
    )

    try:
        run_playwright(npx_path, session, cache_dir, "open", "--browser", "msedge", base_page)
        result = run_playwright(npx_path, session, cache_dir, "--raw", "eval", eval_code)
        raw_text = result.stdout.strip()
        parsed = parse_json_text(raw_text)
        if parsed is None:
            return raw_text, raw_text
        return parsed, raw_text
    finally:
        try:
            run_playwright(npx_path, session, cache_dir, "close")
        except Exception:
            pass


def build_output(args: argparse.Namespace, endpoint: str, raw_text: str, payload: Any, used_browser_fallback: bool) -> dict[str, Any]:
    output: dict[str, Any] = {
        "source": "vixcentral",
        "mode": args.mode,
        "endpoint": endpoint,
        "used_browser_fallback": used_browser_fallback,
        "raw": payload,
    }
    if args.date:
        output["date"] = args.date
    if args.days is not None:
        output["days"] = args.days

    if args.mode == "live" and isinstance(payload, list):
        output["decoded"] = decode_live_bundle(payload)
    elif args.mode == "historical" and isinstance(payload, list):
        output["decoded"] = {
            "start_month": payload[0] if payload else None,
            "curve": decode_historical_curve(payload),
        }
    else:
        output["raw_text"] = raw_text

    return output


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        endpoint = direct_route_for(args)
        raw_text = fetch_text(endpoint, headers=XHR_HEADERS)
        parsed = parse_json_text(raw_text)
        used_browser_fallback = False

        if is_placeholder_or_html(raw_text, parsed):
            payload, raw_text = fetch_with_playwright(args, Path(args.output).expanduser().resolve())
            used_browser_fallback = True
        else:
            payload = parsed

        artifact = build_output(args, endpoint, raw_text, payload, used_browser_fallback)
    except (HTTPError, URLError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved VIXCentral artifact to {output_path}")
    if artifact.get("used_browser_fallback"):
        print("Browser fallback used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
