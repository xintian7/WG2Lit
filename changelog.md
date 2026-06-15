# Changelog

This file uses an entry format of:

- Date: YYYY-MM-DD
- Version: vX.Y (see `.env` for version value)
- Main activities: bullet list

---

Date: 2026-05-08
Version: v0.1a

Main activities:
- Renamed app title to "Climate Literature Navigator" and added a magnifying-glass emoji in the main UI header. (file: `app_lit_wg2.py`)
- Added query-parameter document rendering for Terms of Use and Privacy Policy (`?doc=terms`, `?doc=privacy`) and implemented `render_text_document_page()` with duplicate-heading fix. (file: `app_lit_wg2.py`, `assets/`)
- Updated the sidebar disclaimer and added a User Guide link plus a "Give feedback" link to open the feedback page. (file: `app_lit_wg2.py`, `guidance.md`, `guidance.html`)
- Implemented feedback page (`?page=feedback`) with Notion integration; fields: Name (optional), Chapter (optional), Email (conditionally required), Message, Further Contact. Submissions write `App name` set to "Literature" and `Datetime` in CET. Email is validated when contact is requested. (file: `app_lit_wg2.py`)
- Adjusted Notion payload property mappings and improved API error reporting for easier debugging. (file: `app_lit_wg2.py`)
- Removed the on-screen "Showing the first N results..." caption and the inline JSON preview in search results; downloads (CSV/JSON) remain available. (file: `button_search.py`)
- Restricted UI controls: limited Languages to six UN languages and restricted Publication `Type` options to a curated set mapped to OpenAlex keys. (file: `app_lit_wg2.py`)
- Commented out Global South filter UI and set the related flag to `False`. (file: `app_lit_wg2.py`)
- Restored Load CSV button with an informational message indicating the feature is under development. (file: `app_lit_wg2.py`)
- Updated guidance content to reflect the new app name and UI changes. (files: `guidance.md`, `guidance.html`)

Notes & next steps:
- Verify a real Notion submission in the deployed app and share any API error responses if adjustments are needed.
- Optionally update the `Version` field by reading the version string from `.env` and applying it here.
- Consider converting `assets/Privacy Policy.txt` and `assets/Terms of Use.txt` into Markdown/HTML for richer rendering.

---

Date: 2026-05-08
Version: v0.1b

Main activities:
- Updated section header icons for clearer UI navigation: moved 🔎 from the app title to Literature searching, changed Settings icon to 🛠️, and added 📑 to Literature Review & Export. (file: `app_lit_wg2.py`)
- Renamed section title from "Grey Literature Review & Export" to "Literature Review & Export". (file: `app_lit_wg2.py`)
- Added a new "Semantic search" checkbox under Keyword to switch between semantic and regular Boolean modes. (file: `app_lit_wg2.py`)
- Extended `perform_search(...)` with `use_semantic_search` and implemented mode-aware query construction:
- Boolean mode behavior: `;` separated terms are joined with explicit `AND`. (file: `button_search.py`)
- Semantic mode behavior: terms are sent as a broader natural-language query string. (file: `button_search.py`)
- Enforced strict AND behavior in Boolean mode by post-filtering results so all `;` separated keyword phrases must match each returned record. (file: `button_search.py`)
- Performed release-readiness validation: workspace error scan, repository compile check, dependency sync via `requirements.txt`, and Streamlit startup smoke test. No blocking code/runtime issues were found. (files: `requirements.txt`, `app_lit_wg2.py`)

Notes & next steps:
- Consider showing active search mode (Semantic/Boolean) in the search summary message for transparency.
- If guidance files are intentionally removed from this release, update documentation references accordingly.

---

Date: 2026-05-13
Version: v0.1c

Main activities:
- Center-aligned button labels for primary, download, and form submit buttons for consistent readability. (file: `app_lit_wg2.py`)
- Moved Topic filter section (title, help text, select/deselect toggles, and dropdown) above the Read Publications / Load CSV action row. (file: `app_lit_wg2.py`)
- Refined topic multiselect selected-item display to avoid overlap and improve visibility while keeping one topic per line in the Topic filter. (file: `app_lit_wg2.py`)
- Scoped Topic-filter-specific multiselect styling so the Type selector keeps its original compact display behavior. (file: `app_lit_wg2.py`)
- Updated placeholder actions (Load CSV, Similar works, Citing works, Cited works) to grey button style with consistent sizing, while preserving click feedback messages for under-construction features. (files: `app_lit_wg2.py`, `button_html.py`)
- Added Topic-filter support for records without generated topics by introducing a `No Generated Topics` option. (file: `app_lit_wg2.py`)
- Updated Select all topics behavior to include records with empty/missing topic values through the `No Generated Topics` bucket. (file: `app_lit_wg2.py`)

Notes & next steps:
- When placeholder features are implemented, switch these buttons back to active primary styling and replace informational messages with workflows.

---

Date: 2026-05-19
Version: v0.1d

Main activities:
- Reworked keyword query behavior to support explicit Boolean expressions in the UI and aligned backend retrieval with OpenAlex field-based search semantics for improved count parity with OpenAlex Web. (files: `app_lit_wg2.py`, `button_search.py`)
- Updated keyword guidance copy with line-by-line formatting, highlighted operator labels, and OpenAlex searching references; added clearer notes on supported operators and semantic search reference text. (file: `app_lit_wg2.py`)
- Added parallel load-test utility `test_para.py` to simulate concurrent search users and report latency/error metrics for stress testing. (file: `test_para.py`)
- Increased maximum selectable publication types from 3 to 5 and synchronized the limit across UI and backend filtering logic. (files: `utils.py`, `app_lit_wg2.py`, `button_search.py`)
- Changed default search settings to better match expected workflow: default language set to English and default publication type set to report. (file: `app_lit_wg2.py`)
- Improved analysis figure layout/readability for the yearly stacked chart by reducing x-axis tick clutter and repositioning legend/title spacing. (file: `button_analyze.py`)
- Moved `Sort by` control from the search section to the Literature Review & Export section and positioned it after Topic filter controls. (file: `app_lit_wg2.py`)
- Refined UN member state helper text emphasis (bold/blue styling updates) and updated placeholder/help wording for member-state filtering. (file: `app_lit_wg2.py`)

Notes & next steps:
- Consider pinning one canonical search mode/field in documentation (Boolean vs semantic) and documenting expected count differences when additional filters (language/type/year) are applied.
- Consider adding an optional "Match OpenAlex Web defaults" toggle that pre-fills year/language/type settings for easier parity checks.

---

Date: 2026-05-19
Version: v0.1e

Main activities:
- Finalized caption emphasis styling so highlighted helper terms and links use the app cyan consistently and render in bold for readability across themes. (file: `app_lit_wg2.py`)
- Fine-tuned yearly stacked chart presentation by moving the legend further right to reduce visual crowding near plot content. (file: `button_analyze.py`)

Notes & next steps:
- Recheck chart spacing on smaller screens to ensure the right-shifted legend remains fully visible.

---

Date: 2026-05-20
Version: v0.1f

Main activities:
- Added search logging to Notion after each OpenAlex search, writing query/filter metadata and returned result count to the literature database configured in `.env`. (file: `app_lit_wg2.py`)
- Refactored Notion writes so feedback and search logging use the same shared page-creation flow with consistent request headers/payload handling. (file: `app_lit_wg2.py`)
- Added `Datetime` support for search logs and now write CET/Paris timestamp into the Notion date property. (file: `app_lit_wg2.py`)
- Hardened search flow so failed Notion logging (API/network/exception) does not block or break search result return; failures are surfaced as warnings only. (file: `app_lit_wg2.py`)
- Added a standalone Notion connectivity utility to validate env credentials/database reachability and optionally create a test page. (file: `test_notion_connection.py`)

Notes & next steps:
- If logging appears inconsistent during local dev, restart Streamlit after `.env` edits to avoid stale environment values in the running process.

---

Date: 2026-06-15
Version: v0.2a

Main activities:
- Added BibTeX export generation from cached search results and enabled direct `.bib` download for Zotero import. (file: `app_lit_wg2.py`)
- Added a new download action button labeled "Download BibTex (for Zotero)" in row 2, column 3 of the export controls. (file: `app_lit_wg2.py`)
- Reorganized export action layout so Neo4j download is placed on row 3, column 1. (file: `app_lit_wg2.py`)
- Updated button styling for long labels to improve readability: adjusted height/padding/font and enabled line wrapping for button text. (file: `app_lit_wg2.py`)
- Widened the central action-button container to give each button more horizontal space and reduce text clipping. (file: `app_lit_wg2.py`)

Notes & next steps:
- Verify BibTeX import on Zotero with a mixed sample (article/report/book-chapter) and confirm field mapping quality (author, journal/booktitle, DOI, URL).
- If desired, align all visible version strings/placeholders in the UI with `v0.2a` for release consistency.

---

Last updated: 2026-06-15
