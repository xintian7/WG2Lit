import html
import hashlib
import json
import re
from typing import Any

import streamlit as st

from utils import record_identifier


def _safe_text(value: Any) -> str:
    """Escape a value for safe HTML rendering."""
    return html.escape(str(value or "").strip())


def _display_cell_text(value: Any) -> str:
    """Return escaped text or a non-breaking placeholder for empty values."""
    text = _safe_text(value)
    return text if text else "&nbsp;"


def _clean_publication_date(value: Any) -> str:
    """Return a clean YYYY-MM-DD style date string when available."""
    if isinstance(value, dict):
        candidates = [
            value.get("original"),
            value.get("created"),
            value.get("changed"),
        ]
    else:
        candidates = [value]

    for candidate in candidates:
        text = str(candidate or "").strip()
        if not text:
            continue
        if "T" in text:
            text = text.split("T", maxsplit=1)[0]
        return text
    return ""


def _display_publication_datetime(rec: dict[str, Any]) -> str:
    """Prefer a clean YYYY-MM-DD date; fall back to year when needed."""
    clean_date = _clean_publication_date(rec.get("Publication Date"))
    if clean_date:
        date_match = re.search(r"(19|20)\d{2}-\d{2}-\d{2}", clean_date)
        if date_match:
            return date_match.group(0)
        year_month_match = re.search(r"(19|20)\d{2}-\d{2}", clean_date)
        if year_month_match:
            return year_month_match.group(0)
        year_match = re.search(r"(19|20)\d{2}", clean_date)
        if year_match:
            return year_match.group(0)
        return clean_date

    raw_year = str(rec.get("Publication Year") or "").strip()
    if raw_year:
        date_match = re.search(r"(19|20)\d{2}-\d{2}-\d{2}", raw_year)
        if date_match:
            return date_match.group(0)
        year_month_match = re.search(r"(19|20)\d{2}-\d{2}", raw_year)
        if year_month_match:
            return year_month_match.group(0)
        year_match = re.search(r"(19|20)\d{2}", raw_year)
        if year_match:
            return year_match.group(0)

    return ""


def _display_record_source(rec: dict[str, Any]) -> str:
    """Build a human-readable source label by provider."""
    provider = str(rec.get("Source") or "").strip()
    journal_or_source = str(rec.get("Journal") or "").strip()

    if provider.lower() == "reliefweb":
        return f"{journal_or_source} (via ReliefWeb)" if journal_or_source else "ReliefWeb"

    if provider.lower() == "un digital library":
        return "UN Digital Library"

    if provider.lower() == "world bank":
        return "World Bank"

    # OpenAlex records usually omit `Source`; infer from schema fallback.
    if journal_or_source:
        return f"{journal_or_source} (via OpenAlex)"

    if provider:
        return provider

    return "OpenAlex"


def _display_url_label(rec: dict[str, Any]) -> str:
    """Return source-specific URL label for preview cards."""
    provider = str(rec.get("Source") or "").strip().lower()
    if provider == "reliefweb":
        return "ReliefWeb URL"
    if provider == "un digital library":
        return "UN DL URL"
    if provider == "world bank":
        return "World Bank URL"
    return "OpenAlex URL"


def _display_record_url(rec: dict[str, Any]) -> str:
    """Return a display URL, normalizing UN DL file links to record pages."""
    raw_url = str(rec.get("OpenAlex URL") or rec.get("URL") or "").strip()
    provider = str(rec.get("Source") or "").strip().lower()

    if provider == "un digital library":
        match = re.search(r"/record/(\d+)", raw_url)
        if match:
            return f"https://digitallibrary.un.org/record/{match.group(1)}"

    return raw_url


def _record_hash(rec_id: str) -> str:
    """Generate a short hash for a record identifier."""
    return hashlib.md5(rec_id.encode("utf-8")).hexdigest()[:10]


def _add_skipped_publication(rec_id: str) -> None:
    """Add a publication to the skipped list in session state."""
    skipped = st.session_state.get("html_skipped_publications", [])
    if rec_id not in skipped:
        st.session_state["html_skipped_publications"] = skipped + [rec_id]


def render_html_preview(
    payload: dict | None,
    container: Any = None,
    top_n: int | None = None,
    hide_abstracts: bool = False,
) -> None:
    """Render top-N records as a compact HTML-style preview.

    Per record layout (6/7 rows):
    1) Title, Type
    2) Year, Citation, Doi
    3) Relevance Score (if available)
    4) Authors
    5) Topic
    6) Keywords
    7) Abstract (optional)
    """
    display = container if container is not None else None
    if display is None:
        return

    if not payload:
        display.warning("No results available.")
        return

    raw = payload.get("json")
    if raw is None:
        display.warning("No results available.")
        return

    try:
        records = json.loads(raw)
    except Exception:
        display.warning("Could not parse results JSON.")
        return

    if not isinstance(records, list) or not records:
        display.warning("No results available.")
        return

    if top_n is None:
        preview = records
    else:
        preview = records[: max(int(top_n), 1)]

    display.markdown(
        """
        <style>
        .html-preview-card {
            border: 1px solid #d9e4ee;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 10px;
            background: #ffffff;
        }
        .html-preview-row {
            margin: 2px 0;
            line-height: 1.45;
            color: #1f2937;
        }
        .html-preview-label {
            color: #1f77b4;
            font-weight: 600;
        }
        .html-preview-view-btn {
            display: inline-block;
            margin-left: 8px;
            padding: 2px 8px;
            font-size: 12px;
            line-height: 1.4;
            color: #ffffff !important;
            background: #1f77b4;
            border: 1px solid #1f77b4;
            border-radius: 6px;
            text-decoration: none;
            vertical-align: middle;
        }
        .html-preview-view-btn:hover {
            background: #166aa3;
            border-color: #166aa3;
            text-decoration: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    for rec in preview:
        rec_id = record_identifier(rec)
        rec_hash = _record_hash(rec_id)

        title = _safe_text(rec.get("Title"))
        work_type = _safe_text(rec.get("Type"))
        publication_datetime = _display_cell_text(_display_publication_datetime(rec))
        citation = _display_cell_text(rec.get("Citations"))
        doi = _display_cell_text(rec.get("DOI"))
        relevance = _safe_text(rec.get("Relevance Score"))
        openalex_url = _safe_text(_display_record_url(rec))
        source = _display_cell_text(_display_record_source(rec))
        authors = _display_cell_text(rec.get("Authors"))
        topics = _display_cell_text(rec.get("Topics"))
        keywords = _display_cell_text(rec.get("Keywords"))
        abstract = _display_cell_text(rec.get("Abstract"))

        relevance_row = ""
        view_btn = ""
        if openalex_url:
            view_btn = (
                f'<a class="html-preview-view-btn" href="{openalex_url}" target="_blank" rel="noopener noreferrer">View</a>'
            )

        if relevance or openalex_url:
            row_parts: list[str] = []
            if relevance:
                row_parts.append(f'<span class="html-preview-label">Relevance Score</span>: {relevance}')
            if openalex_url:
                url_label = _display_url_label(rec)
                row_parts.append(f'<span class="html-preview-label">{url_label}</span>: {openalex_url} {view_btn}')
            relevance_row = f'<div class="html-preview-row">{", ".join(row_parts)}</div>'

        provider = str(rec.get("Source") or "").strip().lower()
        is_reliefweb = provider == "reliefweb"
        is_un_digital_library = provider == "un digital library"
        abstract_row = ""
        if not is_reliefweb and not hide_abstracts and abstract != "&nbsp;":
            abstract_row = (
                f'<div class="html-preview-row"><span class="html-preview-label">Abstract</span>: {abstract}</div>'
            )

        date_row_parts = [f'<span class="html-preview-label">Datetime</span>: {publication_datetime}']
        if not is_reliefweb:
            date_row_parts.append(f'<span class="html-preview-label">Citation</span>: {citation}')
            date_row_parts.append(f'<span class="html-preview-label">Doi</span>: {doi}')
        date_row_html = ", ".join(date_row_parts)

        source_row = f'<div class="html-preview-row"><span class="html-preview-label">Source</span>: {source}</div>'
        authors_row = (
            ""
            if is_reliefweb
            else f'<div class="html-preview-row"><span class="html-preview-label">Authors</span>: {authors}</div>'
        )
        topics_row = f'<div class="html-preview-row"><span class="html-preview-label">Topic</span>: {topics}</div>'
        keywords_row = (
            ""
            if is_reliefweb or is_un_digital_library
            else f'<div class="html-preview-row"><span class="html-preview-label">Keywords</span>: {keywords}</div>'
        )

        card_rows = [
            f'<div class="html-preview-row"><span class="html-preview-label">Title</span>: {title}, <span class="html-preview-label">Type</span>: {work_type}</div>',
            f'<div class="html-preview-row">{date_row_html}</div>',
        ]
        if relevance_row:
            card_rows.append(relevance_row)
        if source_row:
            card_rows.append(source_row)
        if authors_row:
            card_rows.append(authors_row)
        if topics_row:
            card_rows.append(topics_row)
        if keywords_row:
            card_rows.append(keywords_row)
        if abstract_row:
            card_rows.append(abstract_row)

        card_html = '<div class="html-preview-card">' + ''.join(card_rows) + '</div>'

        display.markdown(card_html, unsafe_allow_html=True)

        btn_col1, btn_col2, btn_col3, btn_col4 = display.columns(4)
        with btn_col1:
            st.button(
                "Skip",
                key=f"skip_pub_{rec_hash}",
                type="primary",
                on_click=_add_skipped_publication,
                args=(rec_id,),
                use_container_width=True,
            )
        with btn_col2:
            similar_clicked = st.button(
                "Similar works",
                key=f"similar_pub_{rec_hash}",
                type="secondary",
                use_container_width=True,
            )
        with btn_col3:
            citing_clicked = st.button(
                "Citing works",
                key=f"citing_pub_{rec_hash}",
                type="secondary",
                use_container_width=True,
            )
        with btn_col4:
            cited_clicked = st.button(
                "Cited works",
                key=f"cited_pub_{rec_hash}",
                type="secondary",
                use_container_width=True,
            )

        if similar_clicked:
            display.info("Similar works is under construction.")
        if citing_clicked:
            display.info("Citing works is under construction.")
        if cited_clicked:
            display.info("Cited works is under construction.")
