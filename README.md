# Climate Literature Navigator (IPCCWG2_Litereature)

Climate Literature Navigator is a Streamlit application for searching, reviewing, analyzing, and exporting literature relevant to IPCC WG2 workflows.

## Current Capabilities

- Literature search across OpenAlex, ReliefWeb, UN Digital Library, and World Bank.
- Search controls for keyword logic, publication year, OpenAlex type, OpenAlex language, UN member state, and per-source result limits.
- Literature review with source, topic, type, keyword, and publication-year filters.
- Literature review with compact pagination, optional abstract hiding, and skip-based curation.
- Literature analysis with one-source-at-a-time charts from cached search results.
- Literature export with separate downloads for the full cached result set and the review-filtered remaining set.
- Literature network tab scaffold for upcoming graph/network workflows.
- Notion-based feedback and search-log integration.
- Source retrieval client scripts for:
	- OpenAlex
	- ReliefWeb
	- UN Digital Library
	- World Bank
	- Additional standalone institutional service adapters under `services/` for future integration

## Project Structure

- `app_lit_wg2.py`: Main Streamlit app/router and sidebar orchestration.
- `pages/`: Page-level UI modules.
- `features/`: Reusable feature logic (search/analyze/preview/graph).
- `services/`: External service clients and integration logic.
- `docs/`: Changelog and development/guide documentation.

## Key Retrieval Clients

- `services/openalex_client.py`
- `services/reliefweb_client.py`
- `services/un_digital_library_client.py`
- `services/world_bank_client.py`

These integrated clients follow a consistent pattern:
- Request helper with retry behavior.
- `extract_status_code(...)` utility.
- Paginated fetch helper.
- `fetch_results_with_count(...)` helper.

Additional development-bank and institution clients have also been added under `services/` as standalone adapters for future validation and integration.

## Environment Variables

Depending on enabled features, configure the following in your environment:

- `RELIEFWEB_APPNAME`
- `openalex_api` or another supported OpenAlex API key variable name
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

Core search, review, analysis, and export workflows are implemented. Current follow-up work is mainly around validating additional source adapters, strengthening integrations, and expanding future network/database workflows.
