# Notion Logging Reliability Guide

## Context
This project writes two kinds of records to Notion:
1. Search logs (literature searches)
2. Feedback submissions

These writes can fail due to external network conditions even when credentials are valid.

Status note (2026-06-30):
- The Notion reliability approach remains active and unchanged.
- Service modularization remains the preferred pattern for all external integrations.

## What Made It Work
The Notion integration became reliable after combining architecture refactor + resilience strategies:

1. Moved Notion API code out of `app_lit_wg2.py` into service modules.
2. Centralized low-level Notion HTTP behavior in `services/notion_client.py`.
3. Added retry path for proxy-related failures:
   - First attempt uses default `requests` behavior.
   - If a proxy error occurs, retry once with `requests.Session(trust_env=False)`.
4. Added transient-failure fallback queue for search logs in `services/notion_logging_service.py`:
   - On SSL/proxy/network failures, write failed search log payloads to `.notion_search_log_queue.jsonl`.
   - Return success to app flow for transient failures to avoid blocking user searches.
5. Kept UI layer thin by calling service methods from `app_lit_wg2.py` only.

## Current Module Responsibilities

### `services/notion_client.py`
Low-level Notion page creation:
- Notion endpoint call (`/v1/pages`)
- HTTP headers and payload submission
- proxy-bypass retry
- response formatting

### `services/notion_logging_service.py`
Application-level logging workflows:
- Build Notion properties for feedback/search logs
- Read environment configuration (`NOTION_TOKEN`, `DATABASE_ID`, `literature_database_id`)
- Classify transient network errors
- Queue failed search logs locally

### `app_lit_wg2.py`
UI orchestration only:
- Trigger logging services
- Display success/warning/error messages

## Known Failure Modes and Meaning

### ProxyError with tunnel 503
Example:
- `ProxyError(... Tunnel connection failed: 503 Service Unavailable)`

Meaning:
- Request is going through a proxy path that cannot reach Notion.

Handling:
- Retry once with `trust_env=False`.

### SSL EOF (`UNEXPECTED_EOF_WHILE_READING`)
Example:
- `SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] ...')`

Meaning:
- TLS handshake/network path issue before application-level Notion auth checks.

Handling:
- Treat as transient network failure; queue search log locally.

## Operational Keep Points (Future Development Checklist)

1. Keep Notion HTTP calls in `services/notion_client.py` only.
2. Keep payload/business logic in `services/notion_logging_service.py`.
3. Do not add raw Notion `requests.post(...)` calls back into `app_lit_wg2.py`.
4. Preserve proxy-bypass retry (`trust_env=False`) behavior.
5. Preserve transient-failure queue fallback for search logs.
6. Preserve environment variable contract:
   - `NOTION_TOKEN`
   - `DATABASE_ID`
   - `literature_database_id`
7. Keep queue file in project root:
   - `.notion_search_log_queue.jsonl`
8. Keep user flow non-blocking for transient Notion outages (search should still finish).
9. Validate by testing both modes:
   - Normal Notion reachable path
   - Simulated network/proxy failure path
10. Avoid logging secret values (token/database IDs) in plain text.

## Suggested Next Improvements

1. Add automatic queue replay when Notion becomes reachable.
2. Add a manual "flush queued logs" action for operators.
3. Add lightweight health diagnostics for Notion connectivity.
4. Add tests for:
   - transient error classification
   - queue write behavior
   - success/failure message contracts

## Alignment With Current Service Standards

To stay consistent with current `services/` conventions:

1. Keep retry/fallback behavior explicit and centralized.
2. Keep UI handlers free of direct external API request code.
3. Keep warning-level logs for graceful fallback paths.
4. Prefer narrow exception handling where practical.

## Quick Troubleshooting Steps

1. Confirm env vars are present.
2. Check whether shell/macOS proxy settings are active.
3. Test direct connectivity to `api.notion.com`.
4. If Notion remains unreachable, verify queue growth:
   - `.notion_search_log_queue.jsonl`
5. Recover queued logs after network is restored (future replay feature).

## Files to Reference

- `app_lit_wg2.py`
- `services/notion_client.py`
- `services/notion_logging_service.py`
- `.notion_search_log_queue.jsonl`

Last reviewed: 2026-06-30
