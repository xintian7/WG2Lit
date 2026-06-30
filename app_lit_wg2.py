import streamlit as st
from pathlib import Path
import json
import os
import pandas as pd
from dotenv import load_dotenv
from typing import Any

from features.search.search import normalize_keyword_query, perform_search
from features.analyze.analyze import perform_analyze
from features.graph.neo4j_export import build_neo4j_cypher
from features.preview.html_preview import render_html_preview
from services.notion_logging_service import (
    write_feedback_to_notion,
    write_search_log_to_notion,
)
from core.constants import (
    DISPLAY_CONTAINER_HEIGHT,
    MAX_WORK_TYPES,
    UN_MEMBER_STATES,
    UN_MEMBER_STATE_TO_COUNTRY_CODE,
)
from utils import record_identifier
from pages import (
    render_about_page,
    render_disclaimer_page,
    render_user_guide_page,
    render_give_feedback_page,
    render_other_apps_page,
    render_todo_page,
    render_settings_page,
    render_literature_analysis_page,
    render_literature_review_page,
    render_literature_network_page,
    render_literature_export_page,
    render_literature_search_page,
)


load_dotenv()


st.markdown("""
<style>

/* Hide Streamlit footer ("Hosted with Streamlit") */
footer {
    visibility: hidden;
    display: none !important;
}

/* Hide bottom decoration (GitHub avatar / repo badge) */
[data-testid="stDecoration"] {
    display: none;
}
            
</style>
""", unsafe_allow_html=True)


def _payload_after_skips(payload: dict | None) -> dict | None:
    """Return a payload filtered by skipped publications for downloads."""
    if not payload:
        return payload

    skipped_ids = set(st.session_state.get("html_skipped_publications", []))
    if not skipped_ids:
        return payload

    try:
        records = json.loads(payload.get("json") or "[]")
    except Exception:
        return payload

    if not isinstance(records, list):
        return payload

    filtered_records = [
        rec for rec in records
        if record_identifier(rec) not in skipped_ids
    ]

    filtered_payload = dict(payload)
    filtered_payload["json"] = json.dumps(
        filtered_records,
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")
    filtered_payload["csv"] = pd.DataFrame(filtered_records).to_csv(index=False).encode("utf-8")
    filtered_payload["total"] = len(filtered_records)
    return filtered_payload


def _bibtex_escape(value: object) -> str:
    """Escape BibTeX-sensitive characters in field values."""
    text = str(value or "")
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{").replace("}", "\\}")
    return text


def _build_bibtex_key(record: dict, used_keys: set[str], index: int) -> str:
    """Build a deterministic, unique BibTeX key for one record."""
    authors_raw = str(record.get("Authors") or "").strip()
    first_author = authors_raw.split(",")[0].strip() if authors_raw else "unknown"
    first_author_token = "".join(ch for ch in first_author.split(" ")[-1].lower() if ch.isalnum()) or "unknown"

    year = str(record.get("Publication Year") or "n.d.").strip() or "n.d."

    title = str(record.get("Title") or "").strip().lower()
    first_word = ""
    for token in title.split():
        cleaned = "".join(ch for ch in token if ch.isalnum())
        if cleaned:
            first_word = cleaned
            break
    if not first_word:
        first_word = f"item{index}"

    base_key = f"{first_author_token}{year}{first_word}"
    key = base_key
    suffix = 1
    while key in used_keys:
        suffix += 1
        key = f"{base_key}{suffix}"
    used_keys.add(key)
    return key


def _record_to_bibtex_entry(record: dict, used_keys: set[str], index: int) -> str:
    """Convert one result record to a BibTeX entry string."""
    work_type = str(record.get("Type") or "").strip().lower()
    entry_type_map = {
        "article": "article",
        "book": "book",
        "book-chapter": "incollection",
        "dataset": "misc",
        "dissertation": "phdthesis",
        "preprint": "unpublished",
        "report": "techreport",
    }
    entry_type = entry_type_map.get(work_type, "misc")

    key = _build_bibtex_key(record, used_keys, index)

    authors = [a.strip() for a in str(record.get("Authors") or "").split(",") if a.strip()]
    bib_authors = " and ".join(_bibtex_escape(a) for a in authors)

    fields: list[tuple[str, str]] = []

    title = str(record.get("Title") or "").strip()
    if title:
        fields.append(("title", "{" + _bibtex_escape(title) + "}"))

    if bib_authors:
        fields.append(("author", "{" + bib_authors + "}"))

    year = str(record.get("Publication Year") or "").strip()
    if year:
        fields.append(("year", "{" + _bibtex_escape(year) + "}"))

    journal = str(record.get("Journal") or "").strip()
    if journal:
        journal_field = "journal" if entry_type == "article" else "booktitle"
        fields.append((journal_field, "{" + _bibtex_escape(journal) + "}"))

    publisher = str(record.get("Publisher") or "").strip()
    if publisher:
        fields.append(("publisher", "{" + _bibtex_escape(publisher) + "}"))

    doi = str(record.get("DOI") or "").strip()
    if doi:
        fields.append(("doi", "{" + _bibtex_escape(doi) + "}"))

    url = str(record.get("URL") or record.get("OpenAlex URL") or "").strip()
    if url:
        fields.append(("url", "{" + _bibtex_escape(url) + "}"))

    abstract = str(record.get("Abstract") or "").strip()
    if abstract:
        fields.append(("abstract", "{" + _bibtex_escape(abstract) + "}"))

    keywords = str(record.get("Keywords") or "").strip()
    if keywords:
        fields.append(("keywords", "{" + _bibtex_escape(keywords) + "}"))

    body = ",\n".join(f"  {name} = {value}" for name, value in fields)
    return f"@{entry_type}{{{key},\n{body}\n}}"


def _payload_to_bibtex(payload: dict | None) -> bytes:
    """Build a BibTeX file content from the cached payload records."""
    if not payload:
        return b""

    raw_json = payload.get("json")
    if raw_json is None:
        return b""

    if isinstance(raw_json, (bytes, bytearray)):
        raw_json = raw_json.decode("utf-8", errors="ignore")

    try:
        records = json.loads(raw_json)
    except Exception:
        return b""

    if not isinstance(records, list) or not records:
        return b""

    used_keys: set[str] = set()
    entries = [
        _record_to_bibtex_entry(rec, used_keys, idx)
        for idx, rec in enumerate(records, start=1)
        if isinstance(rec, dict)
    ]
    bib_text = "\n\n".join(entries).strip()
    if not bib_text:
        return b""
    return (bib_text + "\n").encode("utf-8")


def render_text_document_page(doc_key: str) -> None:
    """Render a markdown document from assets based on the selected key."""
    docs = {
        "privacy": ("Privacy Policy", "Privacy Policy.txt"),
        "terms": ("Terms of Use", "Terms of Use.txt"),
    }

    doc_meta = docs.get(doc_key)
    if not doc_meta:
        st.error("Requested document was not found.")
        return

    doc_title, doc_filename = doc_meta
    doc_path = Path(__file__).parent / "assets" / doc_filename

    st.divider()
    st.markdown("## Climate Literature Navigator")

    if not doc_path.exists():
        st.error(f"Document file not found: assets/{doc_filename}")
        return

    doc_text = doc_path.read_text(encoding="utf-8").strip()
    if not doc_text:
        st.warning(f"Document is empty: assets/{doc_filename}")
    else:
        lines = doc_text.splitlines()
        if lines:
            first_line = lines[0].lstrip("# ").strip().strip("*")
            if first_line.lower() == doc_title.lower():
                doc_text = "\n".join(lines[1:]).lstrip()
        st.markdown(doc_text)

    st.markdown("[Back to Climate Literature Navigator](?doc=)")


def _get_query_param(param_name: str) -> str | None:
    """Return the requested query param, if any."""
    try:
        query_params = st.query_params
        value = query_params.get(param_name)
    except Exception:
        query_params = st.experimental_get_query_params()
        values = query_params.get(param_name)
        value = values[0] if isinstance(values, list) and values else values

    if isinstance(value, list):
        value = value[0] if value else None

    if value is None:
        return None

    value = str(value).strip()
    return value or None


def _run_keyword_search(
    keyword_value: str,
    original_keyword: str,
    year_range: tuple[int, int],
    num_results: int,
    work_types: list[str],
    language: str | None,
    language_label: str,
    is_global_south: bool,
    institution_country_code: str | None,
    member_state: str | None,
    container: Any,
    display_limit: int,
    sort_by: str,
    use_semantic_search: bool,
) -> dict | None:
    """Run a search, cache the payload, and log it when successful."""
    result_payload = perform_search(
        keyword_value,
        year_range,
        num_results,
        work_types=work_types,
        language=language,
        is_global_south=is_global_south,
        institution_country_code=institution_country_code,
        container=container,
        display_limit=display_limit,
        sort_by=sort_by,
        use_semantic_search=use_semantic_search,
    )
    st.session_state["last_payload"] = result_payload
    st.session_state.pop("last_analyze_triggered", None)
    st.session_state.pop("html_skipped_publications", None)

    if result_payload:
        try:
            log_ok, log_msg = write_search_log_to_notion(
                original_keyword=original_keyword,
                used_keyword=keyword_value,
                year_range=year_range,
                work_types=work_types,
                language=language_label,
                member_state=member_state,
                max_number=num_results,
                returned_results=int(result_payload.get("total") or 0),
            )
        except Exception as exc:
            log_ok, log_msg = False, f"Failed to write search log to Notion: {exc}"
        if not log_ok:
            st.warning(log_msg)

    return result_payload


def _accept_keyword_correction(corrected_keyword: str) -> None:
    """Persist the corrected keyword into the textbox state."""
    st.session_state["kw"] = corrected_keyword
    st.session_state["keyword_search_decision"] = "apply"


def _keep_keyword_correction() -> None:
    """Keep the original keyword in the textbox state."""
    st.session_state["keyword_search_decision"] = "keep"


@st.dialog("Suggested keyword(s)")
def _keyword_correction_dialog(review: dict[str, str]) -> None:
    """Ask the user to confirm the auto-corrected keyword query."""
    st.write("Your keyword search was adjusted to follow Boolean search syntax.")
    st.markdown(f"**Original:** {review['original']}")
    st.markdown(f"**Suggested:** {review['corrected']}")
    if review.get("explanation"):
        st.info(review["explanation"])

    left_col, right_col = st.columns(2)
    with left_col:
        if st.button(
            "Use corrected query",
            key="keyword_correction_accept",
            type="primary",
            use_container_width=True,
        ):
            _accept_keyword_correction(review["corrected"])
            st.rerun()
    with right_col:
        if st.button(
            "Keep original query",
            key="keyword_correction_keep",
            use_container_width=True,
        ):
            _keep_keyword_correction()
            st.rerun()


def render_feedback_page() -> None:
    st.divider()
    st.markdown("## Climate Literature Navigator")
    st.markdown("Any feedback is welcome! Please share your questions or suggestions below to help us improve the app. We will review all feedback carefully and get back to you if you indicate that we can contact you.")
    st.markdown("Please fill out the form below. Fields marked with * are required.")

    with st.form("feedback_form"):
        name = st.text_input("Name (optional)", value="")
        chapter = st.text_input("Chapter (optional)", value="")
        email = st.text_input("Email address (required if you want to be contacted)", value="")
        message = st.text_area("Question or suggestion *", value="", height=160)
        contact_ok = st.checkbox("I would like to be contacted about this inquiry", value=False)
        submitted = st.form_submit_button("Submit")

    if submitted:
        missing = [
            label
            for label, value in (
                ("Question or suggestion", message.strip()),
            )
            if not value
        ]
        if contact_ok and not email.strip():
            missing.append("Email address")
        email_value = email.strip()
        if email_value and "@" not in email_value:
            st.error("Please enter a valid email address.")
        elif missing:
            st.error(f"Please complete the required fields: {', '.join(missing)}.")
        else:
            ok, msg = write_feedback_to_notion(
                name=name.strip(),
                chapter=chapter.strip(),
                email=email.strip(),
                message=message.strip(),
                contact_ok=contact_ok,
            )
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.markdown("[Back to Climate Literature Navigator](?page=)")


page_key = _get_query_param("page")
if page_key == "feedback":
    render_give_feedback_page(write_feedback_to_notion, show_back_link=True)
    st.stop()

# Render doc pages before the main UI.
doc_key = _get_query_param("doc")
if doc_key:
    render_text_document_page(doc_key)
    st.stop()

# ---- IPCC STYLE ----
st.markdown("""
<style>
.main-title {
    /* no background to keep default page background */
    color: #00a9cf;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    font-size: 42px;
    font-weight: 700;
    letter-spacing: 1px;
}

/* Center main content with 20% gutters and 60% content width */
section.main > div.block-container {
    padding-left: 20%;
    padding-right: 20%;
}

/* Primary button styling */
div.stButton > button[kind="primary"] {
    background-color: #1f77b4;
    color: #ffffff;
    border: 1px solid #1f77b4;
    min-height: 52px;
    padding: 0.45rem 0.9rem;
    white-space: normal;
    line-height: 1.2;
    font-size: 0.92rem;
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #166aa3;
    border-color: #166aa3;
}

div.stButton > button[kind="secondary"] {
    background-color: #a3a3a3;
    color: #ffffff;
    border: 1px solid #a3a3a3;
    min-height: 52px;
    padding: 0.45rem 0.9rem;
    white-space: normal;
    line-height: 1.2;
    font-size: 0.92rem;
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
}
div.stButton > button[kind="secondary"]:hover {
    background-color: #8a8a8a;
    border-color: #8a8a8a;
}

div.stButton > button[kind="primary"]:disabled {
    background-color: #a3a3a3;
    color: #ffffff;
    border-color: #a3a3a3;
    cursor: not-allowed;
}
/* Download button styling to match primary */
div.stDownloadButton > button {
    background-color: #1f77b4;
    color: #ffffff;
    border: 1px solid #1f77b4;
    min-height: 52px;
    padding: 0.45rem 0.9rem;
    white-space: normal;
    line-height: 1.2;
    font-size: 0.92rem;
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
}
div.stDownloadButton > button:hover {
    background-color: #166aa3;
    border-color: #166aa3;
}

div.stFormSubmitButton > button {
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
}

/* Show selected topics one per line without text overlap (topic filter only) */
div[data-testid="stMultiSelect"]:has(input[id*="html_topic_filter"]) [data-baseweb="tag"] {
    display: flex;
    align-items: center;
    width: 100%;
    max-width: 100% !important;
    min-height: 2rem;
    margin-right: 0;
}
div[data-testid="stMultiSelect"]:has(input[id*="html_topic_filter"]) [data-baseweb="tag"] > span {
    display: block;
    flex: 1 1 auto;
    min-width: 0;
    max-width: none !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.2;
}

/* Keep emphasized terms in captions blue */
div[data-testid="stCaptionContainer"] strong {
    color: #00a9cf !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}

/* Keep caption links in the same app cyan */
div[data-testid="stCaptionContainer"] a,
div[data-testid="stCaptionContainer"] a:link,
div[data-testid="stCaptionContainer"] a:visited,
div[data-testid="stCaptionContainer"] a:hover,
div[data-testid="stCaptionContainer"] a:active {
    color: #00a9cf !important;
    font-weight: 700 !important;
    text-decoration-thickness: 2px;
    opacity: 1 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"> Climate Literature Navigator </div>', unsafe_allow_html=True)
st.markdown(
    """
    <div style="
        background-color:#EAF4FF;
        border:1px solid #BBDFFF;
        border-radius:8px;
        padding:12px 14px;
        margin:8px 0 14px 0;
        text-align:center;
        font-weight:600;
        font-size:17px;
        color:#1F2D3D;
    ">
        ℹ️ Please first carefully read the information from the left sidebar before using the app.
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
section[data-testid="stSidebar"] div[data-baseweb="radio"] > div:first-child,
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child,
section[data-testid="stSidebar"] div[role="radiogroup"] label [aria-checked] {
    display: none !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
    padding: 3px 8px !important;
    border-radius: 6px !important;
    margin-bottom: 1px !important;
    min-height: 0 !important;
    line-height: 1.15 !important;
    transition: background-color 0.15s ease;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background-color: rgba(0, 169, 207, 0.28) !important;
    border: 1px solid rgba(0, 169, 207, 0.65) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background-color: rgba(0, 169, 207, 0.16);
}

section[data-testid="stSidebar"] hr {
    margin: 0.45rem 0 !important;
}
</style>
""",
unsafe_allow_html=True,
)

if "sidebar_info_section" not in st.session_state:
    st.session_state["sidebar_info_section"] = "about"
if "sidebar_main_section" not in st.session_state:
    st.session_state["sidebar_main_section"] = None
if "active_panel" not in st.session_state:
    st.session_state["active_panel"] = "info:about"

tab_key = _get_query_param("tab")
last_processed_tab_key = st.session_state.get("last_processed_tab_key")
if tab_key and tab_key != last_processed_tab_key:
    normalized_tab_key = tab_key.strip().lower().replace("_", "-")
    info_tab_map = {
        "about": "about",
        "disclaimer": "disclaimer",
        "user-guide": "user guide",
        "give-feedback": "give feedback",
        "other-apps": "other apps",
        "to-do": "to do",
    }
    main_tab_map = {
        "settings": "settings",
        "litereature-search": "litereature search",
        "literature-analysis": "literature analysis",
        "literature-review": "literature review",
        "literature-network": "literature network",
        "literature-export": "literature export",
    }

    info_tab = info_tab_map.get(normalized_tab_key)
    main_tab = main_tab_map.get(normalized_tab_key)

    if info_tab:
        st.session_state["sidebar_info_section"] = info_tab
        st.session_state["sidebar_main_section"] = None
        st.session_state["active_panel"] = f"info:{info_tab}"
        st.session_state["last_processed_tab_key"] = tab_key
    elif main_tab:
        st.session_state["sidebar_info_section"] = None
        st.session_state["sidebar_main_section"] = main_tab
        st.session_state["active_panel"] = f"main:{main_tab}"
        st.session_state["last_processed_tab_key"] = tab_key

requested_info_tab = st.session_state.pop("requested_info_tab", None)
if requested_info_tab in {"about", "disclaimer", "user guide", "give feedback", "other apps", "to do"}:
    st.session_state["sidebar_info_section"] = requested_info_tab
    st.session_state["sidebar_main_section"] = None
    st.session_state["active_panel"] = f"info:{requested_info_tab}"


def _on_info_section_change() -> None:
    selected_info = st.session_state.get("sidebar_info_section")
    st.session_state["sidebar_main_section"] = None
    if selected_info:
        st.session_state["active_panel"] = f"info:{selected_info}"


def _on_main_section_change() -> None:
    selected_main = st.session_state.get("sidebar_main_section")
    if selected_main:
        st.session_state["sidebar_info_section"] = None
        st.session_state["active_panel"] = f"main:{selected_main}"


with st.sidebar:
    st.markdown(
        "<span style='color: #00a9cf; font-weight: bold;'>Climate Literature Navigator (ver 0.2)</span>",
        unsafe_allow_html=True,
    )
    st.markdown("Read information")

    info_icon_map = {
        "about": "ℹ️ About",
        "disclaimer": "⚠️ Disclaimer",
        "user guide": "📘 User Guide",
        "give feedback": "💬 Give Feedback",
        "other apps": "🧩 Other Apps",
        "to do": "✅ Development Plan",
    }

    main_icon_map = {
        "settings": "⚙️ Settings",
        "litereature search": "🔎 Litereature Search",
        "literature analysis": "📊 Literature Analysis",
        "literature review": "📑 Literature Review",
        "literature network": "🔗 Literature Network",
        "literature export": "📤 Literature Export",
    }

    st.radio(
        "",
        options=["about", "disclaimer", "user guide", "give feedback", "other apps", "to do"],
        index=None,
        key="sidebar_info_section",
        label_visibility="collapsed",
        on_change=_on_info_section_change,
        format_func=lambda label: info_icon_map.get(label, label.title()),
    )

    st.divider()

    st.markdown("Find Literature")

    st.radio(
        "",
        options=["litereature search", "literature analysis", "literature review", "literature network", "literature export", "settings"],
        index=None,
        key="sidebar_main_section",
        label_visibility="collapsed",
        on_change=_on_main_section_change,
        format_func=lambda label: main_icon_map.get(label, label.title()),
    )

active_panel = st.session_state.get("active_panel", "info:about")

if active_panel == "info:about":
    render_about_page()
    st.stop()

if active_panel == "info:disclaimer":
    render_disclaimer_page(Path(__file__).parent)
    st.stop()

if active_panel == "info:user guide":
    render_user_guide_page()
    st.stop()

if active_panel == "info:give feedback":
    render_give_feedback_page(write_feedback_to_notion, show_back_link=False)
    st.stop()

if active_panel == "info:other apps":
    render_other_apps_page()
    st.stop()

if active_panel == "info:to do":
    render_todo_page()
    st.stop()

active_main_section = st.session_state.get("sidebar_main_section")

if active_main_section == "literature analysis":
    render_literature_analysis_page(perform_analyze)
    st.stop()

if active_main_section == "literature review":
    render_literature_review_page(render_html_preview)
    st.stop()

if active_main_section == "literature network":
    render_literature_network_page()
    st.stop()

if active_main_section == "literature export":
    render_literature_export_page(
        _payload_after_skips,
        _payload_to_bibtex,
        build_neo4j_cypher,
    )
    st.stop()

if active_main_section == "settings":
    render_settings_page()
    st.stop()

if active_main_section != "litereature search":
    st.stop()

render_literature_search_page(
    normalize_keyword_query=normalize_keyword_query,
    run_keyword_search=_run_keyword_search,
    keyword_correction_dialog=_keyword_correction_dialog,
    max_work_types=MAX_WORK_TYPES,
    un_member_states=UN_MEMBER_STATES,
    un_member_state_to_country_code=UN_MEMBER_STATE_TO_COUNTRY_CODE,
)
