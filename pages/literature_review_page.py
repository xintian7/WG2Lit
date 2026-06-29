from typing import Any, Callable
import json
import streamlit as st
from utils import record_identifier


_REVIEW_PAGE_SIZE = 10


def render_literature_review_page(render_html_preview: Callable[..., Any]) -> None:
    st.divider()
    st.markdown("# Literature Review")

    cached_payload = st.session_state.get("last_payload")
    if not cached_payload:
        st.warning("Run a search first to review publications.")
        return

    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Filter Topic**")
    with help_col:
        st.caption("Select one or more topics to display relevant publications.")

    no_generated_topics_label = "No Generated Topics"

    html_records_all = []
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
        topic_set = set()
        has_no_generated_topics = False
        for rec in html_records_all:
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

    flt_col1, flt_col2 = st.columns([1, 4])
    with flt_col1:
        st.write("")
    with flt_col2:
        def _on_select_all_topics_change() -> None:
            if st.session_state.get("html_topic_select_all"):
                st.session_state["html_topic_filter"] = html_topic_options.copy()
                st.session_state["html_topic_deselect_all"] = False
            st.session_state["html_preview_page_index"] = 0

        def _on_deselect_all_topics_change() -> None:
            if st.session_state.get("html_topic_deselect_all"):
                st.session_state["html_topic_filter"] = []
                st.session_state["html_topic_select_all"] = False
                st.session_state["html_topic_deselect_all"] = False
            st.session_state["html_preview_page_index"] = 0

        def _on_topic_filter_change() -> None:
            selected_now = st.session_state.get("html_topic_filter", [])
            if st.session_state.get("html_topic_select_all") and len(selected_now) < len(html_topic_options):
                st.session_state["html_topic_select_all"] = False
            if selected_now:
                st.session_state["html_topic_deselect_all"] = False
            st.session_state["html_preview_page_index"] = 0

        toggle_col1, toggle_col2 = st.columns(2)
        with toggle_col1:
            st.checkbox(
                "Select all topics",
                value=False,
                key="html_topic_select_all",
                on_change=_on_select_all_topics_change,
            )
        with toggle_col2:
            st.checkbox(
                "Deselect all topics",
                value=False,
                key="html_topic_deselect_all",
                on_change=_on_deselect_all_topics_change,
            )

        selected_html_topics = st.multiselect(
            "",
            options=html_topic_options,
            key="html_topic_filter",
            label_visibility="collapsed",
            on_change=_on_topic_filter_change,
        )

    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Sort by**")
    with help_col:
        st.caption("Choose how to order the results: by relevance score, citation count, or publication date.")
    sort_col1, sort_col2 = st.columns([1, 4])
    with sort_col1:
        st.write("")
    with sort_col2:
        current_sort = st.session_state.get("sb", "Relevance")
        sort_options = ["Relevance", "Citation count", "Date"]
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
        if isinstance(html_records_all, list):
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
                for rec in html_records_all:
                    if not isinstance(rec, dict):
                        continue
                    topics_str = (rec.get("Topics") or "").strip()
                    rec_topics = {x.strip().lower() for x in topics_str.split(";") if x.strip()}
                    if rec_topics.intersection(selected_lc) or (include_no_generated_topics and not rec_topics):
                        filtered_records.append(rec)

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
