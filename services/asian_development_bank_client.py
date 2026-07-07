"""Asian Development Bank document-search helpers.

This client mirrors the World Bank client structure, but ADB currently exposes
search results through HTML pages rather than a stable public JSON endpoint.
"""

import html
import re
import time
from typing import Any

import requests


ADB_DOCUMENTS_SEARCH_URL = "https://www.adb.org/projects/documents"
ADB_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _validate_pagination(limit: int, page_size: int) -> None:
    """Ensure pagination parameters are valid positive integers."""
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if page_size <= 0:
        raise ValueError("page_size must be > 0")


def request_asian_development_bank(params: dict[str, Any], *, timeout: int = 30) -> requests.Response:
    """Send an ADB search request with retries for transient failures."""
    max_attempts = 3
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                ADB_DOCUMENTS_SEARCH_URL,
                params=params,
                headers=ADB_REQUEST_HEADERS,
                timeout=timeout,
            )
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
    raise RuntimeError("ADB request failed without exception detail.")


def extract_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from a requests exception when available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    status_code = getattr(response, "status_code", None)
    return int(status_code) if isinstance(status_code, int) else None


def build_asian_development_bank_params(
    *,
    search: str | None,
    page: int,
) -> dict[str, Any]:
    """Build query parameters for one ADB search request."""
    params: dict[str, Any] = {
        "page": max(page, 0),
    }
    if search and search.strip():
        params["searchstax[query]"] = search.strip()
    return params


def parse_asian_development_bank_results(html_text: str) -> tuple[list[dict[str, Any]], int]:
    """Parse ADB search HTML into simplified record dictionaries."""
    total_match = re.search(r"Showing\s+\d+\s*-\s*\d+\s+of\s+([\d,]+)\s+results", html_text, flags=re.IGNORECASE)
    total = int(total_match.group(1).replace(",", "")) if total_match else 0

    pattern = re.compile(
        r"Document\s+Date:\s*(?P<date>[^<]+)"
        r"\s*<a[^>]+href=\"(?P<url>[^\"]+)\"[^>]*>(?P<title>.*?)</a>"
        r"(?P<body>.*?)(?:Country/Economy:\s*(?P<country>[^|<]+)\s*\|\s*Type:\s*(?P<type>[^<]+))",
        flags=re.IGNORECASE | re.DOTALL,
    )

    records: list[dict[str, Any]] = []
    for match in pattern.finditer(html_text):
        body_text = re.sub(r"<[^>]+>", " ", match.group("body") or "")
        body_text = re.sub(r"\s+", " ", html.unescape(body_text)).strip()
        title = re.sub(r"\s+", " ", html.unescape(match.group("title") or "")).strip()
        records.append({
            "title": title,
            "url": match.group("url") or "",
            "publication_date": (match.group("date") or "").strip(),
            "country": (match.group("country") or "").strip(),
            "type": (match.group("type") or "").strip(),
            "summary": body_text,
            "source": "Asian Development Bank",
        })

    return records, total


def fetch_results_with_count(
    *,
    search: str | None,
    limit: int,
    page_size: int,
    timeout: int = 30,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch ADB search results using HTML pagination.

    Note: the upstream endpoint may return bot-protection responses depending on
    runtime environment.
    """
    _validate_pagination(limit, page_size)

    page = 0
    collected: list[dict[str, Any]] = []
    total = 0

    while len(collected) < limit:
        params = build_asian_development_bank_params(search=search, page=page)
        response = request_asian_development_bank(params, timeout=timeout)
        batch, page_total = parse_asian_development_bank_results(response.text)
        if page == 0:
            total = page_total
        if not batch:
            break

        remaining = limit - len(collected)
        collected.extend(batch[:remaining])
        if len(batch) < page_size:
            break
        page += 1

    return collected[:limit], total