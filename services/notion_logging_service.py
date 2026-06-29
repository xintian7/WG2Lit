"""Application-level Notion logging services for feedback and search events."""

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from services.notion_client import create_notion_page


PARIS_TZ = "Europe/Paris"
SEARCH_LOG_QUEUE_PATH = Path(__file__).resolve().parent.parent / ".notion_search_log_queue.jsonl"


def _is_transient_notion_error(detail: object) -> bool:
    """Return True when a Notion write failed due to network/proxy/SSL issues."""
    text = str(detail)
    transient_markers = (
        "Request error",
        "proxy",
        "ssl",
        "HTTPSConnectionPool",
        "Max retries exceeded",
        "Connection aborted",
        "EOF occurred in violation of protocol",
        "timed out",
        "Temporary failure",
    )
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in transient_markers)


def _append_search_log_queue(entry: dict[str, object]) -> tuple[bool, str]:
    """Append one failed Notion search-log payload to a local JSONL queue."""
    try:
        SEARCH_LOG_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SEARCH_LOG_QUEUE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True, f"Search log queued locally at {SEARCH_LOG_QUEUE_PATH.name}."
    except Exception as exc:
        return False, f"Also failed to queue search log locally: {exc}"


def write_feedback_to_notion(
    name: str,
    chapter: str,
    email: str,
    message: str,
    contact_ok: bool,
) -> tuple[bool, str]:
    """Write one feedback event to the Notion feedback database."""
    token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("DATABASE_ID")
    if not token or not database_id:
        return False, "Notion credentials are missing in the environment."

    title_value = name.strip() or "Feedback"
    email_value = email.strip() if email.strip() else None
    cet_now = datetime.now(ZoneInfo(PARIS_TZ)).isoformat()
    properties = {
        "Title": {"title": [{"text": {"content": title_value}}]},
        "App name": {"rich_text": [{"text": {"content": "Literature"}}]},
        "Name": {"rich_text": [{"text": {"content": name}}]},
        "Chapter": {"rich_text": [{"text": {"content": chapter}}]},
        "Email": {"email": email_value},
        "Question or Suggestion": {"rich_text": [{"text": {"content": message}}]},
        "Further Contact": {"rich_text": [{"text": {"content": "Yes" if contact_ok else "No"}}]},
        "Datetime": {"date": {"start": cet_now}},
    }

    ok, detail = create_notion_page(
        token=token,
        database_id=database_id,
        properties=properties,
    )
    if not ok:
        return False, f"Failed to submit feedback to Notion. Response detail: {detail}"

    return True, "Thank you! Your feedback has been submitted."


def write_search_log_to_notion(
    original_keyword: str,
    used_keyword: str,
    year_range: tuple[int, int],
    work_types: list[str],
    language: str,
    member_state: str | None,
    max_number: int,
    returned_results: int,
) -> tuple[bool, str]:
    """Write one search event to the literature Notion database."""
    token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("literature_database_id")
    if not token or not database_id:
        return False, "Notion search-log credentials are missing in the environment."

    original_keyword_clean = (original_keyword or "").strip()
    used_keyword_clean = (used_keyword or "").strip()

    title_keyword = original_keyword_clean or "No keyword"
    title_keyword = title_keyword[:120]
    title_value = f"Search: {title_keyword}"

    publication_year_text = f"{year_range[0]}-{year_range[1]}"
    type_text = ", ".join(work_types) if work_types else "Any"
    language_text = language or "Any"
    member_state_text = member_state or "All"
    cet_now = datetime.now(ZoneInfo(PARIS_TZ)).isoformat()

    properties = {
        "Name": {"title": [{"text": {"content": title_value}}]},
        "Keyword": {"rich_text": [{"text": {"content": used_keyword_clean}}]},
        "Publication year": {"rich_text": [{"text": {"content": publication_year_text}}]},
        "Type": {"rich_text": [{"text": {"content": type_text}}]},
        "Language": {"rich_text": [{"text": {"content": language_text}}]},
        "UN member states": {"rich_text": [{"text": {"content": member_state_text}}]},
        "Max Number": {"number": int(max_number)},
        "Returned results": {"number": int(returned_results)},
        "Datetime": {"date": {"start": cet_now}},
    }

    ok, detail = create_notion_page(
        token=token,
        database_id=database_id,
        properties=properties,
    )
    if not ok:
        if _is_transient_notion_error(detail):
            queued_ok, queued_msg = _append_search_log_queue(
                {
                    "database_id": database_id,
                    "properties": properties,
                    "queued_at": cet_now,
                    "original_error": str(detail),
                }
            )
            if queued_ok:
                return True, queued_msg
            return False, (
                "Failed to write search log to Notion due to a transient network error. "
                f"{queued_msg}"
            )
        return False, f"Failed to write search log to Notion. Response detail: {detail}"

    return True, "Search log saved to Notion."
