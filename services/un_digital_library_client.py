"""UN Digital Library HTTP client helpers with retry and pagination behavior."""

import logging
import re
import time
from typing import Any
from xml.etree import ElementTree as ET

import requests


UN_DIGITAL_LIBRARY_SEARCH_URL = "https://digitallibrary.un.org/search"
MARC_NS = "http://www.loc.gov/MARC21/slim"
REQUEST_DELAY_SECONDS = 1.0
logger = logging.getLogger(__name__)


def _compute_retry_delay(
    response: requests.Response | None,
    *,
    attempt: int,
    fallback_base_seconds: float = 0.8,
) -> float:
    """Compute retry delay, preferring Retry-After when present."""
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                parsed = float(retry_after)
                if parsed > 0:
                    return parsed
            except ValueError:
                pass
    return fallback_base_seconds * attempt


def _validate_pagination(limit: int, page_size: int) -> None:
    """Ensure pagination parameters are valid positive integers."""
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if page_size <= 0:
        raise ValueError("page_size must be > 0")


def request_un_digital_library(
    params: dict[str, Any],
    *,
    timeout: int = 30,
) -> requests.Response:
    """Send a UN Digital Library request with retries for transient failures."""
    max_attempts = 3
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                UN_DIGITAL_LIBRARY_SEARCH_URL,
                params=params,
                timeout=timeout,
            )
            if response.status_code in (429, 500, 502, 503, 504) and attempt < max_attempts:
                time.sleep(_compute_retry_delay(response, attempt=attempt))
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_attempts:
                response = getattr(exc, "response", None)
                time.sleep(_compute_retry_delay(response, attempt=attempt))
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("UN Digital Library request failed without exception detail.")


def extract_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from a requests exception when available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    status_code = getattr(response, "status_code", None)
    return int(status_code) if isinstance(status_code, int) else None


def build_query(
    *,
    search: str | None,
    from_year: int | None,
    to_year: int | None,
) -> str:
    """Build a website-aligned free-text query string for UN Digital Library."""
    del from_year, to_year
    return str(search or "").strip()


def _record_id(record: ET.Element) -> str:
    """Extract the MARC record identifier used for deduplication."""
    return record.findtext(f"{{{MARC_NS}}}controlfield[@tag='001']") or ""


def _extract_total_count_from_html(html_text: str) -> int | None:
    """Parse the search-result count from the UN Digital Library HTML page."""
    match = re.search(r"<strong>([0-9,]+)</strong>\s+records found", html_text, flags=re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def fetch_total_count(
    *,
    search: str | None,
    timeout: int = 30,
) -> int:
    """Fetch the website-style total count for a UN Digital Library query."""
    query = build_query(search=search, from_year=None, to_year=None)
    if not query:
        raise ValueError("Provide search text to fetch a UN Digital Library total count.")

    params = {
        "ln": "en",
        "p": query,
        "rg": 1,
        "so": "d",
        "fti": 0,
    }
    response = request_un_digital_library(params, timeout=timeout)
    total_count = _extract_total_count_from_html(response.text)
    return total_count if total_count is not None else 0


def fetch_paginated(
    *,
    search: str | None,
    from_year: int | None,
    to_year: int | None,
    limit: int,
    page_size: int = 200,
    timeout: int = 30,
) -> list[ET.Element]:
    """Fetch up to limit UN Digital Library MARCXML records."""
    _validate_pagination(limit, page_size)

    query = build_query(search=search, from_year=from_year, to_year=to_year)
    if not query:
        raise ValueError("Provide search text or a year bound to avoid unconstrained pagination.")

    jrec = 1
    collected: list[ET.Element] = []
    seen_record_ids: set[str] = set()
    first_page = True

    while len(collected) < limit:
        remaining = limit - len(collected)
        current_page_size = min(page_size, remaining)

        if not first_page:
            time.sleep(REQUEST_DELAY_SECONDS)
        first_page = False

        params = {
            "ln": "en",
            "p": query,
            "of": "xm",
            "jrec": jrec,
            "rg": current_page_size,
            "so": "d",
        }
        response = request_un_digital_library(params, timeout=timeout)
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            summary_params = {"p": query, "of": "xm", "jrec": jrec, "rg": current_page_size}
            raise RuntimeError(
                f"Failed to parse UN Digital Library XML response for params={summary_params}"
            ) from exc
        batch = root.findall(f"{{{MARC_NS}}}record")
        if not batch:
            break

        new_records: list[ET.Element] = []
        for record in batch:
            record_id = _record_id(record)
            dedupe_key = record_id or str(len(collected) + len(new_records))
            if dedupe_key in seen_record_ids:
                continue
            seen_record_ids.add(dedupe_key)
            new_records.append(record)

        if not new_records:
            break

        collected.extend(new_records)
        if len(batch) < current_page_size:
            break

        jrec += len(batch)

    return collected[:limit]


def fetch_results_with_count(
    *,
    search: str | None,
    from_year: int | None,
    to_year: int | None,
    limit: int,
    page_size: int = 200,
    timeout: int = 30,
) -> tuple[list[ET.Element], int]:
    """Fetch UN Digital Library records with website-aligned total count."""
    _validate_pagination(limit, page_size)

    try:
        total_count = fetch_total_count(search=search, timeout=timeout)
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("UN Digital Library total-count request failed; falling back to 0 total.", exc_info=exc)
        total_count = 0

    records = fetch_paginated(
        search=search,
        from_year=from_year,
        to_year=to_year,
        limit=limit,
        page_size=page_size,
        timeout=timeout,
    )
    return records, total_count
