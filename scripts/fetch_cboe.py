#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USER_AGENT = "Codex fetch-cross-market-data/1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch direct CBOE CSV datasets.")
    parser.add_argument("--url", required=True, help="Direct CBOE CSV endpoint URL.")
    parser.add_argument("--format", required=True, choices=["raw", "parsed"])
    parser.add_argument("--output", required=True, help="Output path.")
    return parser.parse_args()


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return response.read()


def infer_dataset_name(url: str) -> str:
    stem = Path(urlparse(url).path).stem
    return stem or "cboe_dataset"


def parse_scalar(value: str) -> object:
    cleaned = value.strip()
    if cleaned == "":
        return None
    if re.fullmatch(r"-?\d+", cleaned):
        return int(cleaned)
    if re.fullmatch(r"-?\d+\.\d+", cleaned):
        return float(cleaned)
    return cleaned


def parse_csv_payload(raw_bytes: bytes, source_url: str) -> dict[str, object]:
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = [{key: parse_scalar(value) for key, value in row.items()} for row in reader]
    return {
        "provider": "cboe",
        "source_url": source_url,
        "dataset": infer_dataset_name(source_url),
        "columns": reader.fieldnames or [],
        "rows": rows,
    }


def main() -> int:
    args = parse_args()
    try:
        raw_bytes = fetch_bytes(args.url)
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if args.format == "raw":
            output_path.write_bytes(raw_bytes)
            print(f"Saved raw CBOE payload to {output_path}")
            return 0

        parsed = parse_csv_payload(raw_bytes, args.url)
        output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved parsed CBOE artifact to {output_path}")
        print(f"rows={len(parsed['rows'])}")
        return 0
    except (HTTPError, URLError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
