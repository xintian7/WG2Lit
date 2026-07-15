# Design and Development Standard

## Purpose
This guide records the current design system, page structure, and implementation conventions used in Climate Literature Navigator so future changes stay consistent.

## Core Architecture
1. Keep `app_lit_wg2.py` as the app orchestrator only.
2. Keep page-specific UI in `pages/*.py`.
3. Keep reusable business logic in `features/*`, `services/*`, `core/*`, and `utils.py`.
4. Prefer session-state driven UI flow over global variables.
5. Keep query-parameter routing and sidebar state as the main navigation mechanism.
6. Keep source retrieval clients in `services/` modular and independently testable.
7. Keep shared Streamlit runtime settings in `.streamlit/config.toml`; never commit `.streamlit/secrets.toml`.
8. Preserve the app bootstrap reload guard that clears cached local modules before importing page/feature/service modules so saved code changes are reflected during Streamlit reruns.

## Current App Structure
- Main app bootstrap: `app_lit_wg2.py`
- Page modules: `pages/*.py`
- Search logic: `features/search/search.py`
- Analysis logic: `features/analyze/analyze.py`
- Network/export logic: `features/graph/neo4j_export.py`
- Preview rendering: `features/preview/html_preview.py`
- Logging/services: `services/*`

### Service Client Convention (Current Standard)
For external literature source clients under `services/`:

1. Implement a dedicated request helper with retry behavior.
2. Provide `extract_status_code(exc)` for uniform error inspection.
3. Provide a pagination helper for bounded fetches.
4. Provide `fetch_results_with_count(...)` for UI and pipeline readiness.
5. Validate pagination inputs (`limit`, `page_size`) before loop execution.
6. Prefer `Retry-After` header when handling transient API throttling.
7. Use scoped logging warnings for fallback paths (for example count fallback to zero).

## Navigation Rules
1. Sidebar uses two groups:
   - Information pages
   - Literature workflow pages
2. Only one sidebar group should be active at a time.
3. Use `st.session_state["active_panel"]` to control the visible page.
4. Use query parameters for direct linking to pages.
5. Use deferred navigation state when a page must jump to another tab.

## Default Visual Style
### Color Tokens
- Accent cyan: `#00a9cf`
- Primary button blue: `#1f77b4`
- Secondary button gray: `#a3a3a3`
- Sidebar selected background: cyan-tinted highlight with good contrast in light and dark themes

### Layout Tokens
- Main content gutters: `20%` left and right
- Main title size: `42px`
- Main title alignment: centered
- Title color: accent cyan
- Rounded corners are used for buttons, cards, banners, and small UI blocks

### Button Defaults
- Primary buttons use a blue background and white text.
- Secondary buttons use a gray background and white text.
- Buttons should be center-aligned vertically and horizontally.
- Keep button labels short and clear.
- Use `use_container_width=True` for main action buttons when a full-width layout is desired.

### Card and Preview Defaults
- Preview cards use a light border and a white background.
- Metadata rows should be short, labeled, and easy to scan.
- Keep preview content compact and readable.
- Abstracts can be hidden when needed, but should be shown by default unless the UI explicitly provides a toggle.

## Typography Rules
1. Use a simple heading hierarchy.
2. Prefer `#` for top-level page titles.
3. Use `##` and `###` for sub-sections.
4. Avoid inconsistent heading levels within the same page.
5. Keep long explanatory text in short paragraphs or captions.

## Page Behavior Standards
### Literature Search
- Search should focus on discovery and request creation.
- Keep the page free from unrelated export/review controls.
- Search results should be cached in session state.

### Literature Review
- Review should handle source, topic, type, keyword, and publication-year filtering plus page-based browsing.
- Data-source filtering should be shown as direct checkboxes when only a small fixed set of sources is available.
- Use compact pagination.
- Keep the preview and filtering flow readable on one page.

### Literature Network
- This tab is reserved for future network visualization.
- Keep placeholder text explicit about development status until the feature is ready.

### Literature Analysis
- Keep analysis actions separate from search actions.
- Avoid duplicate chart rendering within one render pass.

### Literature Export
- Keep export actions grouped together.
- Export controls should remain clear and stable.
- Keep a clear distinction between full cached-search exports and review-refined exports when both are offered.

## Interaction Rules
1. Do not open a new page when an in-app tab switch is intended.
2. Preserve existing sidebar grouping and order unless there is a strong reason to change it.
3. Keep page-specific controls close to the content they affect.
4. Prefer compact controls for dense pages.
5. Make pagination and filters visually aligned and predictable.

## Current Literature Review Defaults
- Displayed works per page: `10`
- Default page progression: compact numbered controls with first/last anchors and ellipses for gaps
- Optional hide-abstracts checkbox: unchecked by default
- Review filters currently include source, topic, type, keyword text, and publication year

## Do / Don’t
### Do
- Keep design changes consistent with the current blue/cyan language.
- Use small, focused page modules.
- Validate changes with an error check after edits.
- Preserve current naming and navigation patterns.
- Keep source-client retry and pagination behavior explicit and predictable.

### Don’t
- Don’t move feature logic back into `app_lit_wg2.py` unless it is routing or orchestration.
- Don’t introduce unrelated style systems.
- Don’t rework layout broadly when a small, local change is enough.
- Don’t break existing session-state keys without updating all call sites.
- Don’t swallow broad exceptions in service clients when a narrower exception type is available.

## Useful Files to Reference
- `app_lit_wg2.py`
- `pages/about_page.py`
- `pages/literature_search_page.py`
- `pages/literature_review_page.py`
- `pages/literature_network_page.py`
- `pages/literature_analysis_page.py`
- `pages/literature_export_page.py`
- `features/preview/html_preview.py`
- `features/analyze/analyze.py`

## Maintenance Note
Update this guide whenever the default style, navigation model, or page responsibilities change so future work stays aligned with the current standard.

Last reviewed: 2026-07-07
