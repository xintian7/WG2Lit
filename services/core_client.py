"""CORE HTTP client helpers with retry, rate limiting, and pagination behavior."""

import logging
import os
import threading
import time
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()

CORE_SEARCH_WORKS_URL = "https://api.core.ac.uk/v3/search/works"
CORE_MIN_SECONDS_BETWEEN_REQUESTS = 10.0
logger = logging.getLogger(__name__)

_last_request_time: float | None = None
_rate_limit_lock = threading.Lock()


def _compute_retry_delay(
    response: requests.Response | None,
    *,
    attempt: int,
    fallback_seconds: float = 10.0,
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
    return fallback_seconds * attempt


def _validate_pagination(limit: int, page_size: int) -> None:
    """Ensure pagination parameters are valid positive integers."""
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if page_size <= 0:
        raise ValueError("page_size must be > 0")


def _respect_rate_limit() -> None:
    """Sleep so consecutive CORE requests respect the recommended pacing."""
    global _last_request_time
    if _last_request_time is None:
        return
    elapsed = time.monotonic() - _last_request_time
    wait = CORE_MIN_SECONDS_BETWEEN_REQUESTS - elapsed
    if wait > 0:
        time.sleep(wait)


def request_core(body: dict[str, Any], *, timeout: int = 60) -> requests.Response:
    """Send a CORE request with retries for transient failures."""
    global _last_request_time

    api_key = os.getenv("CORE_API_KEY")
    if not api_key:
        raise RuntimeError("CORE_API_KEY is not set in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    max_attempts = 5
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            with _rate_limit_lock:
                _respect_rate_limit()
                response = requests.post(
                    CORE_SEARCH_WORKS_URL,
                    headers=headers,
                    json=body,
                    timeout=timeout,
                )
                _last_request_time = time.monotonic()

            if response.status_code in (429, 500, 502, 503, 504) and attempt < max_attempts:
                time.sleep(_compute_retry_delay(response, attempt=attempt))
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            _last_request_time = time.monotonic()
            if attempt < max_attempts:
                response = getattr(exc, "response", None)
                time.sleep(_compute_retry_delay(response, attempt=attempt))
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("CORE request failed without exception detail.")


def extract_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from a requests exception when available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    status_code = getattr(response, "status_code", None)
    return int(status_code) if isinstance(status_code, int) else None


def build_core_body(
    *,
    query: str,
    limit: int,
    offset: int,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, Any]:
    """Build CORE request body with optional year filtering in query syntax."""
    q = query.strip()
    if year_from is not None:
        q = f"({q}) AND yearPublished>={year_from}"
    if year_to is not None:
        q = f"({q}) AND yearPublished<={year_to}"

    return {
        "q": q,
        "limit": limit,
        "offset": offset,
    }


def fetch_paginated(
    *,
    query: str,
    limit: int,
    page_size: int,
    year_from: int | None = None,
    year_to: int | None = None,
    timeout: int = 60,
) -> list[dict[str, Any]]:
    """Fetch up to limit CORE works across paginated requests."""
    _validate_pagination(limit, page_size)

    offset = 0
    collected: list[dict[str, Any]] = []

    while len(collected) < limit:
        remaining = limit - len(collected)
        current_page_size = min(page_size, remaining)
        body = build_core_body(
            query=query,
            limit=current_page_size,
            offset=offset,
            year_from=year_from,
            year_to=year_to,
        )
        data = request_core(body, timeout=timeout).json() or {}
        batch = data.get("results") or []
        if not batch:
            break
        collected.extend(batch)
        if len(batch) < current_page_size:
            break
        offset += len(batch)

    return collected[:limit]


def fetch_results_with_count(
    *,
    query: str,
    limit: int,
    page_size: int,
    year_from: int | None = None,
    year_to: int | None = None,
    timeout: int = 60,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch CORE works and total hit count."""
    _validate_pagination(limit, page_size)

    count_body = build_core_body(
        query=query,
        limit=1,
        offset=0,
        year_from=year_from,
        year_to=year_to,
    )
    try:
        count_data = request_core(count_body, timeout=timeout).json() or {}
        total = int(count_data.get("totalHits") or 0)
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("CORE total-count request failed; falling back to 0 total.", exc_info=exc)
        total = 0

    results = fetch_paginated(
        query=query,
        limit=limit,
        page_size=page_size,
        year_from=year_from,
        year_to=year_to,
        timeout=timeout,
    )
    return results, total
