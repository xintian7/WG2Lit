"""World Bank Documents API helpers with retry and pagination behavior."""

import time
from typing import Any

import requests


WORLD_BANK_WDS_URL = "https://search.worldbank.org/api/v2/wds"


def _validate_pagination(limit: int, page_size: int) -> None:
    """Ensure pagination parameters are valid positive integers."""
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if page_size <= 0:
        raise ValueError("page_size must be > 0")


def request_world_bank(params: dict[str, Any], *, timeout: int = 30) -> requests.Response:
    """Send a World Bank Documents API request with retries for transient failures."""
    max_attempts = 3
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                WORLD_BANK_WDS_URL,
                params=params,
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
    raise RuntimeError("World Bank request failed without exception detail.")


def extract_status_code(exc: Exception) -> int | None:
    """Extract HTTP status code from a requests exception when available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    status_code = getattr(response, "status_code", None)
    return int(status_code) if isinstance(status_code, int) else None


def build_world_bank_params(
    *,
    search: str | None,
    offset: int,
    limit: int,
) -> dict[str, Any]:
    """Build query parameters for one World Bank Documents API request."""
    params: dict[str, Any] = {
        "format": "json",
        "rows": limit,
        "os": offset,
    }
    if search and search.strip():
        params["qterm"] = search.strip()
    return params


def fetch_results_with_count(
    *,
    search: str | None,
    limit: int,
    page_size: int,
    timeout: int = 30,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch World Bank documents with total count using offset pagination."""
    _validate_pagination(limit, page_size)

    offset = 0
    collected: list[dict[str, Any]] = []
    total = 0

    while len(collected) < limit:
        remaining = limit - len(collected)
        current_page_size = min(page_size, remaining)
        params = build_world_bank_params(
            search=search,
            offset=offset,
            limit=current_page_size,
        )
        response = request_world_bank(params, timeout=timeout)
        data = response.json() or {}
        if offset == 0:
            total = int(data.get("total") or 0)

        documents = data.get("documents") or {}
        if isinstance(documents, dict):
            batch = [item for item in documents.values() if isinstance(item, dict)]
        else:
            batch = []

        if not batch:
            break
        collected.extend(batch)
        if len(batch) < current_page_size:
            break
        offset += len(batch)

    return collected[:limit], total