#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import Request, urlopen


TAG_PATTERN = re.compile(r"<[^>]+>")
HISTORY_LINK_PATTERN = re.compile(
    r"href\s*=\s*(?:\"(?P<double>[^\"]*LeafHandler\.ashx[^\"]*)\"|'(?P<single>[^']*LeafHandler\.ashx[^']*)'|(?P<bare>[^\"'\s>]*LeafHandler\.ashx[^\"'\s>]*))",
    re.IGNORECASE,
)
DOWNLOAD_LINK_PATTERN = re.compile(
    r"href\s*=\s*(?:\"(?P<double>[^\"]*\.xls)\"|'(?P<single>[^']*\.xls)'|(?P<bare>[^\"'\s>]*\.xls))",
    re.IGNORECASE,
)
TITLE_PATTERN = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_REFRESH_PATTERN = re.compile(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\'][^"\']*url=(?P<target>[^"\']+)["\']', re.IGNORECASE)
SUMMARY_SECTION_PATTERN = re.compile(
    r"<!--Start of Inner Data Table -->(.*?)<!--End of Inner Data Table -->",
    re.IGNORECASE | re.DOTALL,
)
HISTORY_FILE_PATTERN = re.compile(r"(?P<series>.+?)(?P<freq>[DWMA])\.(?:htm|xls)$", re.IGNORECASE)
MISSING_MARKERS = {"", "-", "--", "NA", "W"}
FREQUENCY_NAME_TO_CODE = {
    "daily": "D",
    "weekly": "W",
    "monthly": "M",
    "annual": "A",
}
POWERSHELL_EXTRACT_SCRIPT = r"""
param(
    [string]$InputPath,
    [string]$DataSheetPath
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$excel = $null
$workbook = $null
$contents = $null
$dataSheet = $null

try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false

    $workbook = $excel.Workbooks.Open($InputPath, 0, $false)
    $contents = $workbook.Worksheets.Item('Contents')
    $dataSheet = $workbook.Worksheets.Item('Data 1')

    $dataSheet.Activate() | Out-Null
    $workbook.SaveAs($DataSheetPath, 42)

    $payload = [ordered]@{
        frequency = [string]$contents.Cells.Item(7, 5).Text
        release_date = [string]$contents.Cells.Item(9, 3).Text
        next_release_date = [string]$contents.Cells.Item(10, 3).Text
        excel_file_name = [string]$contents.Cells.Item(11, 3).Text
        available_from_web_page = [string]$contents.Cells.Item(12, 3).Text
        sourcekey = [string]$dataSheet.Cells.Item(2, 2).Text
        value_label = [string]$dataSheet.Cells.Item(3, 2).Text
    }

    $payload | ConvertTo-Json -Compress
}
finally {
    if ($workbook) {
        $workbook.Close($false)
    }
    if ($excel) {
        $excel.Quit()
    }

    foreach ($com in @($dataSheet, $contents, $workbook, $excel)) {
        if ($com) {
            [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($com)
        }
    }

    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch raw or parsed EIA DNAV summary/history pages.")
    parser.add_argument(
        "--page-url",
        required=True,
        help="EIA DNAV summary page, static history page, or LeafHandler history URL.",
    )
    parser.add_argument("--format", required=True, choices=["raw", "parsed"])
    parser.add_argument("--output", required=True, help="Output path.")
    parser.add_argument("--prefer", choices=["xls", "html"], default="xls", help="Raw-mode preference, defaults to xls.")
    parser.add_argument(
        "--source",
        choices=["auto", "xls", "html"],
        default="auto",
        help="Parsed history source policy: auto prefers XLS, xls requires XLS, html forces HTML parsing.",
    )
    return parser.parse_args()


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Codex fetch-cross-market-data/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8", errors="replace")


def clean_text(value: str) -> str:
    text = TAG_PATTERN.sub(" ", value)
    text = html.unescape(text).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_number(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def parse_number(value: str) -> int | float | None:
    cleaned = clean_text(value).replace("†", "").strip()
    if cleaned in MISSING_MARKERS:
        return None
    try:
        return normalize_number(float(cleaned.replace(",", "")))
    except ValueError:
        return None


def parse_short_date(value: str) -> str:
    return datetime.strptime(value, "%m/%d/%y").date().isoformat()


def parse_release_date(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = clean_text(value)
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None


def extract_title(html_text: str) -> str:
    match = TITLE_PATTERN.search(html_text)
    return clean_text(match.group(1)) if match else "EIA DNAV"


def extract_meta_refresh_url(html_text: str, source_url: str) -> str | None:
    match = META_REFRESH_PATTERN.search(html_text)
    if not match:
        return None
    return urljoin(source_url, html.unescape(match.group("target").strip()))


def extract_href(match: re.Match[str]) -> str | None:
    for key in ("double", "single", "bare"):
        value = match.group(key)
        if value:
            return value
    return None


def extract_download_url(html_text: str, source_url: str) -> str | None:
    match = DOWNLOAD_LINK_PATTERN.search(html_text)
    href = extract_href(match) if match else None
    return urljoin(source_url, html.unescape(href)) if href else None


def extract_release_dates(html_text: str) -> tuple[str | None, str | None]:
    release_match = re.search(r"Release Date:\s*([^<]+)", html_text, re.IGNORECASE)
    next_release_match = re.search(r"Next Release Date:\s*([^<]+)", html_text, re.IGNORECASE)
    return (
        parse_release_date(release_match.group(1)) if release_match else None,
        parse_release_date(next_release_match.group(1)) if next_release_match else None,
    )


class TopLevelTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.table_depth = 0
        self.target_table_depth: int | None = None
        self.in_row = False
        self.current_row_class = ""
        self.current_row: list[dict[str, object]] = []
        self.rows: list[dict[str, object]] = []
        self.capture_cell = False
        self.current_cell_parts: list[str] = []
        self.current_cell_attrs: dict[str, str] = {}
        self.current_cell_tag = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if tag == "table":
            self.table_depth += 1
            if self.target_table_depth is None:
                self.target_table_depth = self.table_depth

        if tag == "tr" and self.table_depth == self.target_table_depth and not self.in_row:
            self.in_row = True
            self.current_row_class = attr_map.get("class", "")
            self.current_row = []
            return

        if tag in {"td", "th"} and self.in_row and self.table_depth == self.target_table_depth and not self.capture_cell:
            self.capture_cell = True
            self.current_cell_parts = [self.get_starttag_text()]
            self.current_cell_attrs = attr_map
            self.current_cell_tag = tag
            return

        if self.capture_cell:
            self.current_cell_parts.append(self.get_starttag_text())

    def handle_endtag(self, tag: str) -> None:
        if self.capture_cell:
            self.current_cell_parts.append(f"</{tag}>")

        if tag == self.current_cell_tag and self.capture_cell and self.in_row and self.table_depth == self.target_table_depth:
            cell_html = "".join(self.current_cell_parts)
            self.current_row.append(
                {
                    "tag": self.current_cell_tag,
                    "attrs": self.current_cell_attrs,
                    "html": cell_html,
                    "text": clean_text(cell_html),
                }
            )
            self.capture_cell = False
            self.current_cell_parts = []
            self.current_cell_attrs = {}
            self.current_cell_tag = ""
            return

        if tag == "tr" and self.in_row and self.table_depth == self.target_table_depth:
            self.rows.append({"class": self.current_row_class, "cells": self.current_row})
            self.in_row = False
            self.current_row_class = ""
            self.current_row = []
            return

        if tag == "table":
            self.table_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.capture_cell:
            self.current_cell_parts.append(data)


def page_type_for(page_url: str) -> str:
    path = urlparse(page_url).path.lower()
    return "history" if "/hist/" in path else "summary"


def parse_summary_page(page_url: str, html_text: str, download_url: str | None) -> dict[str, object]:
    section_match = SUMMARY_SECTION_PATTERN.search(html_text)
    summary_section = section_match.group(1) if section_match else html_text
    parser = TopLevelTableParser()
    parser.feed(summary_section)
    parser.close()

    header_dates: list[str] = []
    release_date, next_release_date = extract_release_dates(html_text)
    current_category: str | None = None
    rows: list[dict[str, object]] = []

    for parsed_row in parser.rows:
        cells = parsed_row.get("cells", [])
        if not cells:
            continue

        first_cell = cells[0]
        label = str(first_cell.get("text", ""))
        if not label:
            continue

        cell_class = str(first_cell.get("attrs", {}).get("class", ""))
        if label == "Product by Area":
            header_dates = [parse_short_date(str(cell.get("text", ""))) for cell in cells[1:-1] if str(cell.get("text", "")).strip()]
            continue

        if cell_class == "DataStub2":
            current_category = label
            continue

        if cell_class == "DataStub":
            history_cell_html = str(cells[-1].get("html", "")) if cells else ""
            history_match = HISTORY_LINK_PATTERN.search(history_cell_html)
            history_href = extract_href(history_match) if history_match else None
            history_range = str(cells[-1].get("text", "")) if cells else None
            values = []
            for header_date, value_cell in zip(header_dates, cells[1:-1]):
                values.append({"date": header_date, "value": parse_number(str(value_cell.get("text", "")))})
            rows.append(
                {
                    "category": current_category,
                    "label": label,
                    "values": values,
                    "history_url": urljoin(page_url, html.unescape(history_href)) if history_href else None,
                    "history_range": history_range or None,
                }
            )

    return {
        "provider": "eia",
        "page_type": "summary",
        "source_url": page_url,
        "download_url": download_url,
        "title": extract_title(html_text),
        "release_date": release_date,
        "next_release_date": next_release_date,
        "parsed_from": "html",
        "rows": rows,
    }


def infer_history_details(page_url: str, download_url: str | None = None) -> tuple[str | None, str]:
    parsed_url = urlparse(page_url)
    query = parse_qs(parsed_url.query)
    series_id = query.get("s", [None])[0]
    frequency = query.get("f", [None])[0]

    for candidate_url in (page_url, download_url):
        if not candidate_url:
            continue
        basename = Path(urlparse(candidate_url).path).name
        match = HISTORY_FILE_PATTERN.match(basename)
        if match:
            if not series_id:
                series_id = match.group("series").upper()
            if not frequency:
                frequency = match.group("freq").upper()

    if not frequency:
        raise RuntimeError("Could not determine EIA history frequency from the URL or linked XLS.")
    return series_id.upper() if series_id else None, frequency.upper()


def parse_daily_week_label(value: str) -> date | None:
    match = re.match(r"^(\d{4})\s+([A-Za-z]{3})-\s*(\d{1,2})\s+to\s+[A-Za-z]{3}-\s*\d{1,2}$", value)
    if not match:
        return None
    year_value, month_name, day_value = match.groups()
    month_number = datetime.strptime(month_name, "%b").month
    return date(int(year_value), month_number, int(day_value))


def parse_daily_history_rows(row_cells: list[str]) -> list[dict[str, object]]:
    week_start = parse_daily_week_label(row_cells[0])
    if week_start is None:
        return []
    rows = []
    for index, cell in enumerate(row_cells[1:6]):
        parsed_value = parse_number(cell)
        if parsed_value is None:
            continue
        rows.append({"date": (week_start + timedelta(days=index)).isoformat(), "value": parsed_value})
    return rows


def parse_weekly_history_rows(row_cells: list[str]) -> list[dict[str, object]]:
    match = re.match(r"^(\d{4})-([A-Za-z]{3})$", row_cells[0])
    if not match:
        return []
    year_value = int(match.group(1))
    rows = []
    for index in range(1, len(row_cells), 2):
        if index + 1 >= len(row_cells):
            break
        end_date_text = row_cells[index]
        parsed_value = parse_number(row_cells[index + 1])
        if parsed_value is None or not end_date_text:
            continue
        month_value, day_value = [int(part) for part in end_date_text.split("/")]
        rows.append({"date": date(year_value, month_value, day_value).isoformat(), "value": parsed_value})
    return rows


def parse_monthly_history_rows(row_cells: list[str]) -> list[dict[str, object]]:
    if not re.match(r"^\d{4}$", row_cells[0]):
        return []
    year_value = int(row_cells[0])
    rows = []
    for month_number, cell in enumerate(row_cells[1:13], start=1):
        parsed_value = parse_number(cell)
        if parsed_value is None:
            continue
        rows.append({"date": f"{year_value}-{month_number:02d}-01", "value": parsed_value})
    return rows


def parse_annual_history_rows(row_cells: list[str]) -> list[dict[str, object]]:
    match = re.match(r"^(\d{4})'s$", row_cells[0])
    if not match:
        return []
    start_year = int(match.group(1))
    rows = []
    for offset, cell in enumerate(row_cells[1:11]):
        parsed_value = parse_number(cell)
        if parsed_value is None:
            continue
        rows.append({"date": f"{start_year + offset}-01-01", "value": parsed_value})
    return rows


def parse_history_page_html(page_url: str, html_text: str, download_url: str | None) -> dict[str, object]:
    series_id, frequency = infer_history_details(page_url, download_url)
    release_date, next_release_date = extract_release_dates(html_text)
    rows: list[dict[str, object]] = []
    table_match = re.search(r"<table[^>]*class=['\"]FloatTitle['\"][^>]*>.*?</table>", html_text, re.IGNORECASE | re.DOTALL)
    if not table_match:
        table_match = re.search(r"<table\s+SUMMARY=(?:['\"].*?['\"]|[^>]+)>.*?</table>", html_text, re.IGNORECASE | re.DOTALL)
    if not table_match:
        raise RuntimeError("Could not find the EIA history data table.")

    parser = TopLevelTableParser()
    parser.feed(table_match.group(0))
    parser.close()

    for parsed_row in parser.rows:
        cells = [str(cell.get("text", "")) for cell in parsed_row.get("cells", [])]
        if not cells or len(cells) < 2:
            continue

        if frequency == "D":
            rows.extend(parse_daily_history_rows(cells))
        elif frequency == "W":
            rows.extend(parse_weekly_history_rows(cells))
        elif frequency == "M":
            rows.extend(parse_monthly_history_rows(cells))
        elif frequency == "A":
            rows.extend(parse_annual_history_rows(cells))

    return {
        "provider": "eia",
        "page_type": "history",
        "source_url": page_url,
        "download_url": download_url,
        "title": extract_title(html_text),
        "series_id": series_id,
        "frequency": frequency,
        "release_date": release_date,
        "next_release_date": next_release_date,
        "parsed_from": "html_fallback",
        "rows": rows,
    }


def resolve_powershell() -> str:
    executable = shutil.which("powershell") or shutil.which("pwsh")
    if not executable:
        raise RuntimeError("PowerShell is required for EIA XLS parsing on this Windows environment.")
    return executable


def read_data1_rows(data_sheet_path: Path, frequency: str) -> tuple[str | None, str, list[dict[str, object]]]:
    with data_sheet_path.open("r", encoding="utf-16", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        raw_rows = list(reader)

    if len(raw_rows) < 4:
        raise RuntimeError("EIA XLS export did not contain the expected Data 1 rows.")

    sourcekey = clean_text(raw_rows[1][1]) if len(raw_rows[1]) > 1 else None
    value_label = clean_text(raw_rows[2][1]) if len(raw_rows[2]) > 1 else "EIA Series"
    rows: list[dict[str, object]] = []

    for raw_row in raw_rows[3:]:
        if len(raw_row) < 2:
            continue
        date_text = clean_text(raw_row[0])
        value_text = clean_text(raw_row[1])
        if not date_text or not value_text:
            continue
        parsed_value = parse_number(value_text)
        if parsed_value is None:
            continue
        rows.append({"date": parse_xls_date(date_text, frequency), "value": parsed_value})

    return sourcekey or None, value_label, rows


def parse_xls_date(value: str, frequency: str) -> str:
    if frequency in {"D", "W"}:
        return datetime.strptime(value, "%b %d, %Y").date().isoformat()
    if frequency == "M":
        return datetime.strptime(value, "%b-%Y").date().isoformat()
    if frequency == "A":
        year_match = re.match(r"^\d{4}$", value)
        if not year_match:
            raise RuntimeError(f"Unexpected annual EIA XLS date value: {value}")
        return f"{value}-01-01"
    raise RuntimeError(f"Unsupported EIA history frequency: {frequency}")


def normalize_frequency_code(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = clean_text(value).lower()
    return FREQUENCY_NAME_TO_CODE.get(cleaned, cleaned.upper())


def parse_history_page_xls(page_url: str, download_url: str, html_text: str) -> dict[str, object]:
    release_date, next_release_date = extract_release_dates(html_text)

    with tempfile.TemporaryDirectory(prefix="eia_xls_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        xls_path = temp_dir / Path(urlparse(download_url).path).name
        xls_path.write_bytes(fetch_bytes(download_url))

        data_sheet_path = temp_dir / "data1.txt"
        script_path = temp_dir / "extract_eia_history.ps1"
        script_path.write_text(POWERSHELL_EXTRACT_SCRIPT, encoding="utf-8")

        powershell = resolve_powershell()
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                str(xls_path),
                str(data_sheet_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=True,
        )

        metadata = json.loads(result.stdout.strip() or "{}")

        inferred_series_id, inferred_frequency = infer_history_details(page_url, download_url)
        sourcekey, value_label, rows = read_data1_rows(
            data_sheet_path,
            normalize_frequency_code(metadata.get("frequency")) or inferred_frequency,
        )

    return {
        "provider": "eia",
        "page_type": "history",
        "source_url": page_url,
        "download_url": download_url,
        "title": value_label,
        "series_id": sourcekey or inferred_series_id,
        "frequency": normalize_frequency_code(metadata.get("frequency")) or inferred_frequency,
        "release_date": parse_release_date(metadata.get("release_date")) or release_date,
        "next_release_date": parse_release_date(metadata.get("next_release_date")) or next_release_date,
        "parsed_from": "xls",
        "rows": rows,
    }


def parse_history_page(page_url: str, html_text: str, download_url: str | None, source: str) -> dict[str, object]:
    if source == "html":
        return parse_history_page_html(page_url, html_text, download_url)

    if not download_url:
        if source == "xls":
            raise RuntimeError("EIA history page does not expose a linked XLS download.")
        return parse_history_page_html(page_url, html_text, download_url)

    try:
        return parse_history_page_xls(page_url, download_url, html_text)
    except (json.JSONDecodeError, subprocess.SubprocessError, RuntimeError) as exc:
        if source == "xls":
            raise RuntimeError(f"EIA XLS parsing failed: {exc}") from exc
        parsed_output = parse_history_page_html(page_url, html_text, download_url)
        parsed_output["xls_fallback_reason"] = str(exc)
        return parsed_output


def save_raw_output(source_url: str, preferred_url: str | None, prefer: str, output_path: Path) -> str:
    if prefer == "xls" and preferred_url:
        output_path.write_bytes(fetch_bytes(preferred_url))
        return preferred_url
    output_path.write_text(fetch_text(source_url), encoding="utf-8")
    return source_url


def main() -> int:
    args = parse_args()
    try:
        source_url = args.page_url
        page_kind = page_type_for(source_url)
        html_text = fetch_text(source_url)
        effective_url = source_url
        redirect_url = extract_meta_refresh_url(html_text, source_url) if page_kind == "history" else None
        if redirect_url:
            effective_url = redirect_url
            html_text = fetch_text(effective_url)
        download_url = extract_download_url(html_text, effective_url)
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if args.format == "raw":
            saved_url = save_raw_output(effective_url, download_url, args.prefer, output_path)
            print(f"Saved raw EIA payload to {output_path}")
            print(f"URL: {saved_url}")
            return 0

        if page_kind == "summary":
            if args.source == "xls":
                raise ValueError("Parsed summary pages support HTML output only. Use --format raw for the linked XLS.")
            parsed_output = parse_summary_page(source_url, html_text, download_url)
        else:
            parsed_output = parse_history_page(source_url, html_text, download_url, args.source)

        output_path.write_text(json.dumps(parsed_output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved parsed EIA artifact to {output_path}")
        print(f"page_type={page_kind} rows={len(parsed_output.get('rows', []))}")
        return 0
    except (HTTPError, URLError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
