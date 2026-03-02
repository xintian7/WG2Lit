"""Shared utility functions and constants for the IPCC Literature app."""

from typing import Any

# ---- Constants ----
MAX_RESULTS_LIMIT: int = 5000
DISPLAY_CONTAINER_HEIGHT: int = 420
OPENALEX_PAGE_SIZE: int = 200
MAX_WORK_TYPES: int = 3
DEFAULT_YEAR_START: int = 2000
DEFAULT_YEAR_END: int = 2026
YEAR_SLIDER_MIN: int = 1900
YEAR_SLIDER_MAX: int = 2027


def record_identifier(rec: dict[str, Any] | None) -> str:
    """Generate a unique identifier for a publication record.

    Uses OpenAlex URL if available, otherwise falls back to title.
    Both are normalized to lowercase for case-insensitive matching.

    Parameters
    ----------
    rec : dict or None
        A publication record dictionary with optional "OpenAlex URL" and "Title" keys.

    Returns
    -------
    str
        A prefixed identifier string (e.g., "url::..." or "title::...").
    """
    rec_url = str((rec or {}).get("OpenAlex URL") or "").strip().lower()
    if rec_url:
        return f"url::{rec_url}"
    rec_title = str((rec or {}).get("Title") or "").strip().lower()
    return f"title::{rec_title}"
