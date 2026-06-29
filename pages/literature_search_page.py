from typing import Any, Callable
import json
import streamlit as st


def render_literature_search_page(
    normalize_keyword_query: Callable[[str], tuple[str, bool, str]],
    run_keyword_search: Callable[..., dict | None],
    keyword_correction_dialog: Callable[[dict[str, str]], None],
    max_work_types: int,
    un_member_states: list[str],
    un_member_state_to_country_code: dict[str, str],
) -> None:
    st.divider()
    st.markdown("# Literature Search")

    # Keyword: label+help line, then control line
    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Keyword**")
    with help_col:
        st.caption(
            "Use Boolean operators to combine terms:  \n"
            "**AND**: requires all terms,  \n"
            "**OR**: allows either term,  \n"
            "**Parentheses**: group logic,  \n"
            "**Double quotes**: exact phrases,  \n"
            "**Notes**: Other operators are not supported at this moment. Please submit feedback using the feedback form if you need additional operators.  \n"
            "**Example**: \"climate change\" AND (water OR \"land use\") AND Bahamas.  \n"
            "**Reference**: [OpenAlex searching guide](https://developers.openalex.org/guides/searching)"
        )
    kw_col1, kw_col2 = st.columns([1, 4])
    with kw_col1:
        st.write("")
    with kw_col2:
        keyword = st.text_input("", value="climate change", label_visibility="collapsed", key="kw")
        use_semantic_search = st.checkbox(
            "Semantic search",
            value=False,
            key="semantic_search",
            help="If checked, use semantic search (broader, AI-powered matching). If unchecked, use regular Boolean search (more precise, keyword-based). Note: Semantic search does not support country/institution filters. Reference: https://developers.openalex.org/guides/semantic-search",
        )

    # Publication year: label+help line, then slider line
    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Publication year**")
    with help_col:
        st.caption("Select a start and end year for the publication date range.")
    yr_col1, yr_col2 = st.columns([1, 4])
    with yr_col1:
        st.write("")
    with yr_col2:
        year_range = st.slider("", 1900, 2027, (2000, 2025), label_visibility="collapsed", key="yr")

    # Type: label+help line, then multiselect line
    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Type**")
    with help_col:
        st.caption(
            f"Due to processing time, you can select up to {max_work_types} categories at one time. "
            "It will be improved in a future version to allow more categories."
        )
    type_col1, type_col2 = st.columns([1, 4])
    with type_col1:
        st.write("")
    with type_col2:
        work_types = st.multiselect(
            "",
            options=[
                "article",
                "book",
                "book-chapter",
                "dataset",
                "dissertation",
                "editorial",
                "erratum",
                "letter",
                "libguides",
                "other",
                "paratext",
                "peer-review",
                "preprint",
                "reference-entry",
                "report",
                "retraction",
                "review",
                "standard",
                "supplementary-materials",
            ],
            default=["report"],
            label_visibility="collapsed",
            key="wt",
        )
        if work_types and len(work_types) > max_work_types:
            st.warning(f"You selected more than {max_work_types} types — only the first {max_work_types} will be used.")
            work_types = work_types[:max_work_types]

    # Language: label+help line, then control line
    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Language**")
    with help_col:
        st.caption("Filter results by language. Default is English. When selecting other languages, the keywords can be in the selected language or in English, which will give different results. We are working on a future version to allow more flexible combinations of languages and keywords.")
    lang_col1, lang_col2 = st.columns([1, 4])
    with lang_col1:
        st.write("")
    with lang_col2:
        language_option = st.selectbox(
            "",
            options=[
                "Any",
                "English",
                "Arabic",
                "Chinese",
                "French",
                "Russian",
                "Spanish",
            ],
            index=1,
            label_visibility="collapsed",
            key="lang",
        )
        language_code_map = {
            "Any": None,
            "English": "en",
            "Arabic": "ar",
            "Chinese": "zh",
            "French": "fr",
            "Russian": "ru",
            "Spanish": "es",
        }
        selected_language = language_code_map.get(language_option)

    filter_global_south = False

    # UN member states: label+help line, then control line
    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**UN member states**")
    with help_col:
        st.caption(
            "Filter results to works where **at least one institution/affiliation of this publication is from the selected UN member state** "
            "([UN member states](https://www.un.org/en/about-us/member-states)). "
            "When this filter is not applied, results will include works from any state worldwide."
        )
    state_col1, state_col2 = st.columns([1, 4])
    with state_col1:
        st.write("")
    with state_col2:
        selected_member_state = st.selectbox(
            "",
            options=un_member_states,
            index=None,
            placeholder="You can leave this field empty to include works from all states.",
            label_visibility="collapsed",
            key="un_member_state",
        )
        selected_member_state_code = un_member_state_to_country_code.get(selected_member_state or "")

    # Number of results: label line then control line
    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Max Number**")
    with help_col:
        st.caption("Select the maximum number of results to return (max 5000 for the time being). More results take longer to load.")
    nr_col1, nr_col2 = st.columns([1, 4])
    with nr_col1:
        st.write("")
    with nr_col2:
        num_results = st.slider("", 1, 5000, 500, label_visibility="collapsed", key="nr")

    sort_by = st.session_state.get("sb", "Relevance")

    results_container = st.container()
    with st.container():
        did_search = False
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Search OpenAlex", key="main_search_button", type="primary", use_container_width=True):
                normalized_keyword, needs_review, explanation = normalize_keyword_query(keyword)
                if needs_review and not use_semantic_search:
                    st.session_state["keyword_search_request"] = {
                        "keyword": keyword,
                        "year_range": year_range,
                        "num_results": num_results,
                        "work_types": work_types,
                        "language": selected_language,
                        "language_label": language_option,
                        "is_global_south": filter_global_south,
                        "institution_country_code": selected_member_state_code,
                        "member_state": selected_member_state,
                        "display_limit": 5,
                        "sort_by": sort_by,
                        "use_semantic_search": use_semantic_search,
                    }
                    st.session_state["keyword_search_review"] = {
                        "original": keyword,
                        "corrected": normalized_keyword,
                        "explanation": explanation,
                    }
                    st.session_state.pop("keyword_search_decision", None)
                else:
                    did_search = True
                    st.session_state.pop("keyword_search_request", None)
                    st.session_state.pop("keyword_search_review", None)
                    st.session_state.pop("keyword_search_decision", None)
                    run_keyword_search(
                        normalized_keyword,
                        keyword,
                        year_range,
                        num_results,
                        work_types,
                        selected_language,
                        language_option,
                        filter_global_south,
                        selected_member_state_code,
                        selected_member_state,
                        results_container,
                        5,
                        sort_by,
                        use_semantic_search,
                    )
        with c2:
            st.write("")
        with c3:
            st.write("")
        with c4:
            st.write("")

        pending_review = st.session_state.get("keyword_search_review")
        pending_request = st.session_state.get("keyword_search_request")
        pending_decision = st.session_state.get("keyword_search_decision")

        if pending_review and not pending_decision:
            keyword_correction_dialog(pending_review)

        if pending_request and pending_decision:
            request_keyword = pending_request.get("keyword", "")
            if pending_decision == "apply":
                request_keyword = st.session_state.get("kw", request_keyword)

            did_search = True
            run_keyword_search(
                request_keyword,
                pending_request.get("keyword", request_keyword),
                pending_request.get("year_range", year_range),
                pending_request.get("num_results", num_results),
                pending_request.get("work_types", work_types),
                pending_request.get("language", selected_language),
                pending_request.get("language_label", language_option),
                pending_request.get("is_global_south", filter_global_south),
                pending_request.get("institution_country_code", selected_member_state_code),
                pending_request.get("member_state", selected_member_state),
                results_container,
                pending_request.get("display_limit", 5),
                pending_request.get("sort_by", sort_by),
                pending_request.get("use_semantic_search", use_semantic_search),
            )
            st.session_state.pop("keyword_search_request", None)
            st.session_state.pop("keyword_search_review", None)
            st.session_state.pop("keyword_search_decision", None)

    cached_payload = st.session_state.get("last_payload")

    if cached_payload and not did_search:
        results_container.success(cached_payload.get("summary", "Results"))

