"""Islamic Development Bank document-search helpers."""

import html
import re
import time
from typing import Any

import requests


ISDB_SEARCH_URL = "https://www.isdb.org/search"
ISDB_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _validate_pagination(limit: int, page_size: int) -> None:
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if page_size <= 0:
        raise ValueError("page_size must be > 0")


def request_islamic_development_bank(params: dict[str, Any], *, timeout: int = 30) -> requests.Response:
    max_attempts = 3
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(ISDB_SEARCH_URL, params=params, headers=ISDB_REQUEST_HEADERS, timeout=timeout)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < max_attempts:
                time.sleep(0.6 * attempt)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_attempts:
                time.sleep(0.6 * attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("IsDB request failed without exception detail.")


def extract_status_code(exc: Exception) -> int | None:
    response = getattr(exc, "response", None)
    if response is None:
        return None
    status_code = getattr(response, "status_code", None)
    return int(status_code) if isinstance(status_code, int) else None


def build_islamic_development_bank_params(*, search: str | None, page: int) -> dict[str, Any]:
    params: dict[str, Any] = {"page": max(page, 1)}
    if search and search.strip():
        params["keys"] = search.strip()
    return params


def parse_islamic_development_bank_results(html_text: str) -> tuple[list[dict[str, Any]], int]:
    total_match = re.search(r"([\d,]+)\s+results", html_text, flags=re.IGNORECASE)
    total = int(total_match.group(1).replace(",", "")) if total_match else 0
    pattern = re.compile(
        r'<a[^>]+href="(?P<url>https://www\.isdb\.org/[^"]+)"[^>]*>(?P<title>.*?)</a>(?P<body>.*?)(?=<a[^>]+href="https://www\.isdb\.org/|$)',
        flags=re.IGNORECASE | re.DOTALL,
    )
    records: list[dict[str, Any]] = []
    for match in pattern.finditer(html_text):
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", match.group("title") or ""))).strip()
        if not title:
            continue
        body_text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", match.group("body") or ""))).strip()
        records.append({
            "title": title,
            "url": match.group("url") or "",
            "publication_date": "",
            "type": "",
            "summary": body_text,
            "source": "Islamic Development Bank",
        })
    return records, total


def fetch_results_with_count(*, search: str | None, limit: int, page_size: int, timeout: int = 30) -> tuple[list[dict[str, Any]], int]:
    _validate_pagination(limit, page_size)
    page = 1
    collected: list[dict[str, Any]] = []
    total = 0
    while len(collected) < limit:
        response = request_islamic_development_bank(build_islamic_development_bank_params(search=search, page=page), timeout=timeout)
        batch, page_total = parse_islamic_development_bank_results(response.text)
        if page == 1:
            total = page_total
        if not batch:
            break
        collected.extend(batch[: limit - len(collected)])
        if len(batch) < page_size:
            break
        page += 1
    return collected[:limit], total
