"""OpenAlex HTTP client helpers with retry and pagination behavior."""

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv


OPENALEX_WORKS_URL = "https://api.openalex.org/works"


load_dotenv()


def _with_openalex_auth(params: dict[str, Any]) -> dict[str, Any]:
    """Attach the configured OpenAlex API key when one is available."""
    api_key = (
        os.getenv("OPENALEX_API_KEY")
        or os.getenv("OPENALEX_APIKEY")
        or os.getenv("openalex_api_key")
        or os.getenv("openalex_apiKey")
        or os.getenv("openalex_api")
    )
    if not api_key:
        return dict(params)

    authenticated_params = dict(params)
    authenticated_params.setdefault("api_key", api_key)
    return authenticated_params


def request_openalex(params: dict[str, Any], *, timeout: int = 30) -> requests.Response:
    """Send an OpenAlex request with retries for transient failures."""
    max_attempts = 3
    last_exc: Exception | None = None
    request_params = _with_openalex_auth(params)

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                OPENALEX_WORKS_URL,
                params=request_params,
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
    raise RuntimeError("OpenAlex request failed without exception detail.")


def extract_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from a requests exception when available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    status_code = getattr(response, "status_code", None)
    return int(status_code) if isinstance(status_code, int) else None


def fetch_paginated(
    params: dict[str, Any],
    *,
    limit: int | None,
    page_size: int,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Fetch up to limit records across multiple OpenAlex pages."""
    page = 1
    collected: list[dict[str, Any]] = []

    while limit is None or len(collected) < limit:
        response = request_openalex(
            {**params, "per_page": page_size, "page": page},
            timeout=timeout,
        )
        batch = (response.json() or {}).get("results") or []
        if not batch:
            break
        collected.extend(batch)
        if len(batch) < page_size:
            break
        page += 1

    return collected if limit is None else collected[:limit]


def fetch_results_with_count(
    params: dict[str, Any],
    *,
    limit: int | None,
    use_semantic_search: bool,
    page_size: int,
    timeout: int = 30,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch results and total count, respecting semantic-search request limits."""
    total = 0
    results_list: list[dict[str, Any]] = []

    if use_semantic_search:
        response = request_openalex(
            {**params, "per_page": min(limit, 50)},
            timeout=timeout,
        )
        data = response.json() or {}
        total = int(data.get("meta", {}).get("count") or 0)
        results_list = data.get("results") or []
        return results_list, total

    try:
        count_response = request_openalex(
            {**params, "per_page": 1},
            timeout=timeout,
        )
        total = int((count_response.json() or {}).get("meta", {}).get("count") or 0)
    except Exception:
        total = 0

    results_list = fetch_paginated(
        params,
        limit=limit,
        page_size=page_size,
        timeout=timeout,
    )
    return results_list, total
