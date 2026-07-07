"""African Development Bank document-search helpers.

This client mirrors the World Bank client structure, but AfDB currently serves
search results through HTML pages and may apply bot protection to direct HTTP
requests from some runtimes.
"""

import html
import re
import time
from typing import Any
from urllib.parse import quote

import requests


AFDB_SEARCH_URL_TEMPLATE = "https://www.afdb.org/en/search/node/{query}"
AFDB_REQUEST_HEADERS = {
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


def request_african_development_bank(
    search: str,
    *,
    page: int,
    timeout: int = 30,
) -> requests.Response:
    """Send an AfDB search request with retries for transient failures."""
    max_attempts = 3
    last_exc: Exception | None = None
    url = AFDB_SEARCH_URL_TEMPLATE.format(query=quote(search.strip()))

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                url,
                params={"page": max(page, 0)},
                headers=AFDB_REQUEST_HEADERS,
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
    raise RuntimeError("AfDB request failed without exception detail.")


def extract_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from a requests exception when available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    status_code = getattr(response, "status_code", None)
    return int(status_code) if isinstance(status_code, int) else None


def parse_african_development_bank_results(html_text: str) -> tuple[list[dict[str, Any]], int]:
    """Parse AfDB search HTML into simplified record dictionaries."""
    total_match = re.search(r"Displaying\s+\d+\s*-\s*\d+\s+of\s+([\d,]+)", html_text, flags=re.IGNORECASE)
    total = int(total_match.group(1).replace(",", "")) if total_match else 0

    pattern = re.compile(
        r"\[(?P<title>[^\]]+)\]\((?P<url>https://www\.afdb\.org/en/[^)]+)\)"
        r"\s+(?P<type>[A-Z\s]+)\s+Updated:\s+(?P<date>\d{2}-[A-Za-z]{3}-\d{4})"
        r"\s*(?P<summary>.*?)(?=\[[^\]]+\]\(https://www\.afdb\.org/en/|[«‹] first|## SECTORS|$)",
        flags=re.DOTALL,
    )

    records: list[dict[str, Any]] = []
    for match in pattern.finditer(html_text):
        summary = re.sub(r"\s+", " ", html.unescape(match.group("summary") or "")).strip()
        records.append({
            "title": re.sub(r"\s+", " ", html.unescape(match.group("title") or "")).strip(),
            "url": match.group("url") or "",
            "publication_date": (match.group("date") or "").strip(),
            "type": re.sub(r"\s+", " ", match.group("type") or "").strip(),
            "summary": summary,
            "source": "African Development Bank",
        })

    return records, total


def fetch_results_with_count(
    *,
    search: str | None,
    limit: int,
    page_size: int,
    timeout: int = 30,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch AfDB search results using HTML pagination.

    Note: the upstream endpoint may return bot-protection responses depending on
    runtime environment.
    """
    _validate_pagination(limit, page_size)
    if not search or not search.strip():
        return [], 0

    page = 0
    collected: list[dict[str, Any]] = []
    total = 0

    while len(collected) < limit:
        response = request_african_development_bank(search.strip(), page=page, timeout=timeout)
        batch, page_total = parse_african_development_bank_results(response.text)
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