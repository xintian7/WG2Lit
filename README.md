# Climate Literature Navigator (IPCCWG2_Litereature)

Climate Literature Navigator is a Streamlit application for searching, reviewing, analyzing, and exporting literature relevant to IPCC WG2 workflows.

## Current Capabilities

- Literature search with keyword, filters, and mode options.
- Literature review with compact pagination and optional abstract hiding.
- Literature analysis and export utilities.
- Literature network tab scaffold for upcoming graph/network workflows.
- Notion-based feedback and search-log integration.
- Source retrieval client scripts for:
	- OpenAlex
	- ReliefWeb
	- CORE
	- UN Digital Library

## Project Structure

- `app_lit_wg2.py`: Main Streamlit app/router and sidebar orchestration.
- `pages/`: Page-level UI modules.
- `features/`: Reusable feature logic (search/analyze/preview/graph).
- `services/`: External service clients and integration logic.
- `docs/`: Changelog and development/guide documentation.

## Key Retrieval Clients

- `services/openalex_client.py`
- `services/reliefweb_client.py`
- `services/core_client.py`
- `services/un_digital_library_client.py`

All four clients follow a consistent pattern:
- Request helper with retry behavior.
- `extract_status_code(...)` utility.
- Paginated fetch helper.
- `fetch_results_with_count(...)` helper.

## Environment Variables

Depending on enabled features, configure the following in your environment:

- `RELIEFWEB_APPNAME`
- `CORE_API_KEY`
- `NOTION_TOKEN`
- `DATABASE_ID`
- `literature_database_id`

## Run Locally

Run commands from the repository root so Streamlit loads the shared `.streamlit/config.toml` settings.

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the app:

```bash
streamlit run app_lit_wg2.py
```

## Documentation

- Changelog: `docs/changelogs.md`
- Development standards: `docs/guides/design_and_development_standard.md`
- Notion reliability guide: `docs/guides/notion_logging_reliability_guide.md`
- Internship/reference note: `docs/student_intern_2026.md`

## Status

Most core UI and retrieval extension tasks are complete. Current focus is strengthening integrations and expanding network/database workflows.
