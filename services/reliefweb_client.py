"""ReliefWeb HTTP client helpers with retry and pagination behavior."""

import logging
import os
import time
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

RELIEFWEB_REPORTS_URL = "https://api.reliefweb.int/v2/reports"
logger = logging.getLogger(__name__)

# Fields requested from ReliefWeb for each report.
RELIEFWEB_INCLUDE_FIELDS = [
    "title",
    "headline.title",
    "headline.summary",
    "source.name",
    "country.name",
    "country.iso3",
    "primary_country.name",
    "primary_country.iso3",
    "language.name",
    "language.code",
    "format.name",
    "theme.name",
    "date.original",
    "url",
    "url_alias",
]


def _compute_retry_delay(
    response: requests.Response | None,
    *,
    attempt: int,
    fallback_base_seconds: float = 0.7,
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


def request_reliefweb(payload: dict[str, Any], *, timeout: int = 30) -> requests.Response:
    """Send a ReliefWeb request with retries for transient failures."""
    appname = os.getenv("RELIEFWEB_APPNAME")
    if not appname:
        raise RuntimeError("RELIEFWEB_APPNAME is not set in environment variables.")

    max_attempts = 3
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                f"{RELIEFWEB_REPORTS_URL}?appname={appname}",
                json=payload,
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
    raise RuntimeError("ReliefWeb request failed without exception detail.")


def extract_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from a requests exception when available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    status_code = getattr(response, "status_code", None)
    return int(status_code) if isinstance(status_code, int) else None


def build_reliefweb_payload(
    *,
    search: str | None,
    from_year: int | None,
    to_year: int | None,
    offset: int,
    limit: int,
) -> dict[str, Any]:
    """Build POST payload for one ReliefWeb page request."""
    payload: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "preset": "latest",
        "fields": {"include": RELIEFWEB_INCLUDE_FIELDS},
    }

    if search and search.strip():
        payload["query"] = {
            "value": search.strip(),
        }

    date_value: dict[str, str] = {}
    if from_year is not None:
        date_value["from"] = f"{from_year}-01-01T00:00:00+00:00"
    if to_year is not None:
        date_value["to"] = f"{to_year}-12-31T23:59:59+00:00"
    if date_value:
        payload["filter"] = {"field": "date.original", "value": date_value}

    return payload


def fetch_paginated(
    *,
    search: str | None,
    from_year: int | None,
    to_year: int | None,
    limit: int,
    page_size: int,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Fetch up to limit ReliefWeb reports using offset pagination."""
    _validate_pagination(limit, page_size)

    offset = 0
    collected: list[dict[str, Any]] = []

    while len(collected) < limit:
        remaining = limit - len(collected)
        current_page_size = min(page_size, remaining)
        payload = build_reliefweb_payload(
            search=search,
            from_year=from_year,
            to_year=to_year,
            offset=offset,
            limit=current_page_size,
        )
        response = request_reliefweb(payload, timeout=timeout)
        batch = (response.json() or {}).get("data") or []
        if not batch:
            break
        collected.extend(batch)
        if len(batch) < current_page_size:
            break
        offset += len(batch)

    return collected[:limit]


def fetch_results_with_count(
    *,
    search: str | None,
    from_year: int | None,
    to_year: int | None,
    limit: int,
    page_size: int,
    timeout: int = 30,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch ReliefWeb reports with a best-effort total count."""
    _validate_pagination(limit, page_size)

    count_payload = build_reliefweb_payload(
        search=search,
        from_year=from_year,
        to_year=to_year,
        offset=0,
        limit=1,
    )
    try:
        count_data = request_reliefweb(count_payload, timeout=timeout).json() or {}
        total = int(
            count_data.get("totalCount")
            or count_data.get("total")
            or count_data.get("count")
            or 0
        )
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("ReliefWeb total-count request failed; falling back to 0 total.", exc_info=exc)
        total = 0

    results = fetch_paginated(
        search=search,
        from_year=from_year,
        to_year=to_year,
        limit=limit,
        page_size=page_size,
        timeout=timeout,
    )
    return results, total
