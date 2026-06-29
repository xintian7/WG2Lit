"""Low-level Notion API client helpers."""

from typing import Any

import requests


NOTION_PAGES_URL = "https://api.notion.com/v1/pages"
NOTION_API_VERSION = "2022-06-28"


def create_notion_page(
    token: str,
    database_id: str,
    properties: dict[str, Any],
) -> tuple[bool, object]:
    """Create a Notion page in the target database and return raw response detail on failure."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"database_id": database_id.strip()},
        "properties": properties,
    }

    def _post_page(*, bypass_env_proxy: bool) -> requests.Response:
        if bypass_env_proxy:
            # Some environments expose broken HTTP(S)_PROXY settings.
            # For Notion writes, retry once with trust_env disabled.
            with requests.Session() as session:
                session.trust_env = False
                return session.post(
                    NOTION_PAGES_URL,
                    headers=headers,
                    json=payload,
                    timeout=20,
                )
        return requests.post(
            NOTION_PAGES_URL,
            headers=headers,
            json=payload,
            timeout=20,
        )

    try:
        response = _post_page(bypass_env_proxy=False)
    except requests.exceptions.ProxyError:
        try:
            response = _post_page(bypass_env_proxy=True)
        except requests.RequestException as exc:
            return False, f"Request error after proxy bypass retry: {exc}"
    except requests.RequestException as exc:
        return False, f"Request error: {exc}"
    except Exception as exc:
        return False, f"Unexpected error: {exc}"

    if response.status_code >= 300:
        try:
            return False, response.json()
        except ValueError:
            return False, response.text

    return True, "ok"
