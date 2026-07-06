from typing import Any, Callable
import json
import streamlit as st
from utils import record_identifier


_REVIEW_PAGE_SIZE = 10


def _topic_filter_button_label(selected_topics: list[str], all_topics: list[str]) -> str:
    """Build a compact dropdown label for the selected topics."""
    if not all_topics:
        return "No topics available"
    if not selected_topics:
        return "Filter Topic: None"
    if len(selected_topics) == len(all_topics):
        return f"Filter Topic: All ({len(all_topics)})"
    if len(selected_topics) <= 2:
        return f"Filter Topic: {', '.join(selected_topics)}"
    return f"Filter Topic: {selected_topics[0]}, {selected_topics[1]} +{len(selected_topics) - 2}"


def _record_date_sort_key(record: dict[str, Any]) -> tuple[int, str]:
    """Build a descending-friendly sort key from publication date/year text."""
    publication_date = str(record.get("Publication Date") or "").strip()
    publication_year = str(record.get("Publication Year") or "").strip()
    normalized = publication_date or publication_year
    digits_only = "".join(ch for ch in normalized if ch.isdigit())
    numeric_key = int(digits_only[:8]) if digits_only else 0
    return numeric_key, normalized


def render_literature_review_page(render_html_preview: Callable[..., Any]) -> None:
    st.divider()
    st.markdown("# Literature Review")

    cached_payload = st.session_state.get("last_payload")
    if not cached_payload:
        st.warning("Run a search first to review publications.")
        return

    no_generated_topics_label = "No Generated Topics"

    html_records_all = []
    html_source_options = []
    html_topic_options = []
    try:
        html_records_all = json.loads(cached_payload.get("json") or "[]")
    except Exception:
        html_records_all = []

    if isinstance(html_records_all, list) and html_records_all:
        skipped_ids = set(st.session_state.get("html_skipped_publications", []))

        if skipped_ids:
            html_records_all = [
                rec for rec in html_records_all
                if record_identifier(rec) not in skipped_ids
            ]

    if isinstance(html_records_all, list) and html_records_all:
        source_set = set()
        for rec in html_records_all:
            if not isinstance(rec, dict):
                continue
            source_name = str(rec.get("Source") or "OpenAlex").strip() or "OpenAlex"
            source_set.add(source_name)
        html_source_options = sorted(source_set, key=str.lower)

    existing_source_selection = st.session_state.get("html_source_filter")
    if not html_source_options:
        st.session_state["html_source_filter"] = []
    elif existing_source_selection is None:
        st.session_state["html_source_filter"] = html_source_options.copy()
    else:
        st.session_state["html_source_filter"] = [
            source for source in existing_source_selection if source in html_source_options
        ]

    def _toggle_source_selection(source: str) -> None:
        checkbox_key = f"html_source_option_{source}"
        selected_set = set(st.session_state.get("html_source_filter", []))
        if st.session_state.get(checkbox_key):
            selected_set.add(source)
        else:
            selected_set.discard(source)
        st.session_state["html_source_filter"] = [
            option for option in html_source_options if option in selected_set
        ]
        st.session_state["html_preview_page_index"] = 0

    selected_html_sources = st.session_state.get("html_source_filter", [])

    label_col, source_content_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Filter Data Source**")
    with source_content_col:
        st.caption("Select one or more data sources to narrow the results.")
        source_columns = st.columns(len(html_source_options)) if html_source_options else []
        for index, source in enumerate(html_source_options):
            checkbox_key = f"html_source_option_{source}"
            st.session_state[checkbox_key] = source in selected_html_sources
            with source_columns[index]:
                st.checkbox(
                    source,
                    key=checkbox_key,
                    on_change=_toggle_source_selection,
                    args=(source,),
                )

    source_filtered_records = html_records_all
    if isinstance(html_records_all, list):
        if not st.session_state.get("html_source_filter", []):
            source_filtered_records = []
        else:
            selected_sources = set(st.session_state.get("html_source_filter", []))
            source_filtered_records = [
                rec for rec in html_records_all
                if isinstance(rec, dict)
                and (str(rec.get("Source") or "OpenAlex").strip() or "OpenAlex") in selected_sources
            ]

    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Filter Topic**")
    with help_col:
        st.caption("Select one or more topics to display relevant publications.")

    if isinstance(source_filtered_records, list) and source_filtered_records:
        topic_set = set()
        has_no_generated_topics = False
        for rec in source_filtered_records:
            if not isinstance(rec, dict):
                continue
            topics_str = (rec.get("Topics") or "").strip()
            if not topics_str:
                has_no_generated_topics = True
                continue
            for topic in [x.strip() for x in topics_str.split(";") if x.strip()]:
                topic_set.add(topic)
        html_topic_options = sorted(topic_set, key=str.lower)
        if has_no_generated_topics:
            html_topic_options.append(no_generated_topics_label)

    existing_topic_selection = st.session_state.get("html_topic_filter")
    if not html_topic_options:
        st.session_state["html_topic_filter"] = []
    elif existing_topic_selection is None:
        st.session_state["html_topic_filter"] = html_topic_options.copy()
    else:
        st.session_state["html_topic_filter"] = [
            topic for topic in existing_topic_selection if topic in html_topic_options
        ]

    flt_col1, flt_col2 = st.columns([1, 4])
    with flt_col1:
        st.write("")
    with flt_col2:
        def _select_all_topics() -> None:
            st.session_state["html_topic_filter"] = html_topic_options.copy()
            st.session_state["html_preview_page_index"] = 0

        def _clear_all_topics() -> None:
            st.session_state["html_topic_filter"] = []
            st.session_state["html_preview_page_index"] = 0

        def _toggle_topic_selection(topic: str) -> None:
            checkbox_key = f"html_topic_option_{topic}"
            selected_set = set(st.session_state.get("html_topic_filter", []))
            if st.session_state.get(checkbox_key):
                selected_set.add(topic)
            else:
                selected_set.discard(topic)
            st.session_state["html_topic_filter"] = [
                option for option in html_topic_options if option in selected_set
            ]
            st.session_state["html_preview_page_index"] = 0

        selected_html_topics = st.session_state.get("html_topic_filter", [])
        topic_filter_label = _topic_filter_button_label(selected_html_topics, html_topic_options)

        with st.popover(topic_filter_label, use_container_width=True):
            action_col1, action_col2 = st.columns(2)
            with action_col1:
                if st.button("Select all", key="html_topic_select_all_button", use_container_width=True):
                    _select_all_topics()
                    st.rerun()
            with action_col2:
                if st.button("Clear", key="html_topic_clear_all_button", use_container_width=True):
                    _clear_all_topics()
                    st.rerun()

            topic_search = st.text_input(
                "Search topics",
                value=st.session_state.get("html_topic_filter_search", ""),
                key="html_topic_filter_search",
                placeholder="Search topics...",
            ).strip().lower()

            visible_topics = [
                topic for topic in html_topic_options
                if not topic_search or topic_search in topic.lower()
            ]

            if not visible_topics:
                st.caption("No topics match the current search.")
            else:
                for topic in visible_topics:
                    checkbox_key = f"html_topic_option_{topic}"
                    st.session_state[checkbox_key] = topic in selected_html_topics
                    st.checkbox(
                        topic,
                        key=checkbox_key,
                        on_change=_toggle_topic_selection,
                        args=(topic,),
                    )

    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Sort by**")
    with help_col:
        st.caption("Choose how to order the results: by relevance score or publication date.")
    sort_col1, sort_col2 = st.columns([1, 4])
    with sort_col1:
        st.write("")
    with sort_col2:
        has_openalex_records = any(
            str((rec or {}).get("Source") or "").strip().lower() == "openalex"
            for rec in html_records_all
            if isinstance(rec, dict)
        )
        default_sort = "Relevance" if has_openalex_records else "Date"
        current_sort = st.session_state.get("sb", default_sort)
        sort_options = ["Relevance", "Date"] if has_openalex_records else ["Date"]
        if current_sort not in sort_options:
            current_sort = default_sort
            st.session_state["sb"] = default_sort
        sort_index = sort_options.index(current_sort) if current_sort in sort_options else 0
        st.selectbox(
            "",
            options=sort_options,
            index=sort_index,
            label_visibility="collapsed",
            key="sb",
        )

    html_btn_col1, html_btn_col2, html_btn_col3, html_btn_col4 = st.columns(4)
    with html_btn_col1:
        if st.button("Read Publications", key="view_html_button", type="primary", use_container_width=True):
            st.session_state["show_html_preview"] = True
            st.session_state["html_preview_page_index"] = 0
    with html_btn_col2:
        if st.button("Load CSV", key="load_csv_button", type="secondary", use_container_width=True):
            st.warning("Load CSV is still under construction.")
    with html_btn_col3:
        st.write("")
    with html_btn_col4:
        st.write("")

    html_container = st.container()
    if st.session_state.get("show_html_preview"):
        payload_for_html = cached_payload
        filtered_records = []
        if isinstance(source_filtered_records, list):
            if not selected_html_topics:
                payload_for_html = dict(cached_payload)
                payload_for_html["json"] = json.dumps([], ensure_ascii=False)
                html_container.caption("Filtered results: 0")
            else:
                include_no_generated_topics = no_generated_topics_label in selected_html_topics
                selected_lc = {
                    topic.lower() for topic in selected_html_topics
                    if topic != no_generated_topics_label
                }
                for rec in source_filtered_records:
                    if not isinstance(rec, dict):
                        continue
                    topics_str = (rec.get("Topics") or "").strip()
                    rec_topics = {x.strip().lower() for x in topics_str.split(";") if x.strip()}
                    if rec_topics.intersection(selected_lc) or (include_no_generated_topics and not rec_topics):
                        filtered_records.append(rec)

                active_sort = st.session_state.get("sb", default_sort)
                if active_sort == "Date":
                    filtered_records = sorted(
                        filtered_records,
                        key=_record_date_sort_key,
                        reverse=True,
                    )

                total_filtered = len(filtered_records)
                if total_filtered == 0:
                    payload_for_html = dict(cached_payload)
                    payload_for_html["json"] = json.dumps([], ensure_ascii=False)
                    html_container.caption("Filtered results: 0")
                else:
                    current_page = int(st.session_state.get("html_preview_page_index", 0))
                    max_page = (total_filtered - 1) // _REVIEW_PAGE_SIZE
                    if current_page < 0:
                        current_page = 0
                    if current_page > max_page:
                        current_page = max_page
                    st.session_state["html_preview_page_index"] = current_page

                    start_idx = current_page * _REVIEW_PAGE_SIZE
                    end_idx = min(start_idx + _REVIEW_PAGE_SIZE, total_filtered)
                    page_records = filtered_records[start_idx:end_idx]

                    total_pages = max_page + 1
                    page_tokens: list[int | str] = []

                    html_container.markdown(
                        """
                        <style>
                        .st-key-html_prev_page button,
                        .st-key-html_next_page button,
                        div[class*="st-key-html_gap_"] button,
                        div[class*="st-key-html_page_"] button {
                            width: 30px !important;
                            min-width: 30px !important;
                            max-width: 30px !important;
                            min-height: 24px !important;
                            height: 24px !important;
                            margin: 0 auto !important;
                            padding: 0 !important;
                            font-size: 0.72rem !important;
                            line-height: 1 !important;
                            border-radius: 5px !important;
                            display: flex !important;
                            align-items: center !important;
                            justify-content: center !important;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    if total_pages <= 4:
                        page_tokens = list(range(1, total_pages + 1))
                    else:
                        page_num = current_page + 1
                        middle_start = max(2, page_num - 1)
                        middle_end = min(total_pages - 1, page_num + 1)

                        page_tokens.append(1)
                        if middle_start > 2:
                            page_tokens.append("...")

                        for token in range(middle_start, middle_end + 1):
                            if token not in page_tokens:
                                page_tokens.append(token)

                        if middle_end < total_pages - 1:
                            page_tokens.append("...")

                        if total_pages not in page_tokens:
                            page_tokens.append(total_pages)

                    controls: list[tuple[str, int | str]] = [("prev", "‹")]
                    controls.extend([(f"page_{idx}", token) for idx, token in enumerate(page_tokens)])
                    controls.append(("next", "›"))

                    side_spacer = 6
                    nav_cols = html_container.columns([side_spacer] + [1] * len(controls) + [side_spacer], gap="small")
                    for nav_col, (control_key, token) in zip(nav_cols[1:-1], controls):
                        with nav_col:
                            if control_key == "prev":
                                if st.button(
                                    str(token),
                                    key="html_prev_page",
                                    type="secondary",
                                    use_container_width=False,
                                    disabled=current_page == 0,
                                ):
                                    st.session_state["html_preview_page_index"] = max(current_page - 1, 0)
                                    st.rerun()
                            elif control_key == "next":
                                if st.button(
                                    str(token),
                                    key="html_next_page",
                                    type="secondary",
                                    use_container_width=False,
                                    disabled=current_page >= max_page,
                                ):
                                    st.session_state["html_preview_page_index"] = min(current_page + 1, max_page)
                                    st.rerun()
                            elif isinstance(token, int):
                                if st.button(
                                    str(token),
                                    key=f"html_page_{token}",
                                    type="primary" if token - 1 == current_page else "secondary",
                                    use_container_width=False,
                                ):
                                    st.session_state["html_preview_page_index"] = token - 1
                                    st.rerun()
                            else:
                                st.button(
                                    "…",
                                    key=f"html_gap_{control_key}",
                                    type="secondary",
                                    use_container_width=False,
                                    disabled=True,
                                )

                    html_container.caption(
                        f"Filtered results: {total_filtered} | Showing {start_idx + 1}-{end_idx} | Page {current_page + 1}/{max_page + 1}"
                    )
                    html_container.checkbox(
                        "Hide abstracts",
                        value=False,
                        key="html_hide_abstracts",
                    )

                    payload_for_html = dict(cached_payload)
                    payload_for_html["json"] = json.dumps(page_records, ensure_ascii=False)

        render_html_preview(
            payload_for_html,
            container=html_container,
            top_n=None,
            hide_abstracts=bool(st.session_state.get("html_hide_abstracts", False)),
        )
