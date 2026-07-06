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

    # Data source: label+help line, then control line
    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Data source**")
    with help_col:
        st.caption(
            "Select one or more sources."
        )
    src_col1, src_col2 = st.columns([1, 4])
    with src_col1:
        st.write("")
    with src_col2:
        st.markdown(
            "- [**OpenAlex**](https://openalex.org/) is a fully open catalog of the global research system - hundreds of millions of scholarly works, authors, institutions, and more.\n"
            "- [**ReliefWeb**](https://reliefweb.int/) is the leading humanitarian information service provided by the United Nations Office for the Coordination of Humanitarian Affairs (OCHA).\n"
            "- [**United Nations Digital Library**](https://digitallibrary.un.org/) is a primary bibliographic database of the United Nations established in 1979. It consists of the official documents and publications produced by the UN System."
        )
        selected_sources = st.multiselect(
            "",
            options=["OpenAlex", "ReliefWeb", "UN Digital Library"],
            default=["OpenAlex"],
            label_visibility="collapsed",
            key="search_sources",
        )

    if not selected_sources:
        st.warning("Please select at least one data source.")
        return

    normalized_sources = {source.strip().lower() for source in selected_sources}
    openalex_selected = "openalex" in normalized_sources
    openalex_only_selected = normalized_sources == {"openalex"}

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
        if openalex_selected:
            use_semantic_search = st.checkbox(
                "Semantic search",
                value=False,
                key="semantic_search",
                help="If checked, apply semantic search to OpenAlex only (broader, AI-powered matching). Other selected sources continue to use their regular keyword search. If unchecked, OpenAlex also uses regular Boolean search. Note: Semantic search does not support country/institution filters. Reference: https://developers.openalex.org/guides/semantic-search",
            )
            if not openalex_only_selected:
                st.caption("When Semantic search is enabled, it applies to OpenAlex only. ReliefWeb and UN Digital Library continue to use regular keyword search.")
        else:
            use_semantic_search = False
            st.caption("Semantic search is currently available for OpenAlex only.")

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
        year_range = st.slider("", 1900, 2027, (2000, 2027), label_visibility="collapsed", key="yr")

    # OpenAlex-only filters
    work_types: list[str] = []
    selected_language: str | None = None
    language_option = "Any"
    selected_member_state: str | None = None
    selected_member_state_code: str | None = None

    # Type: always visible; applies to OpenAlex only.
    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Type (OpenAlex only)**" if not openalex_only_selected else "**Type**")
    with help_col:
        st.caption(
            f"Due to processing time, you can select up to {max_work_types} categories at one time. "
            "It will be improved in a future version to allow more categories."
            + (" This filter only applies to OpenAlex due to the API constraint from other sources." if openalex_selected else "")
            + (" Select OpenAlex in Data source to enable this filter." if not openalex_selected else "")
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
            disabled=not openalex_selected,
        )
        if work_types and len(work_types) > max_work_types:
            st.warning(f"You selected more than {max_work_types} types — only the first {max_work_types} will be used.")
            work_types = work_types[:max_work_types]

    if openalex_only_selected:
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

    if openalex_only_selected:
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
    elif openalex_selected:
        st.caption("Language and UN member states are hidden unless OpenAlex is the only selected source. Type is still available above and applies only to OpenAlex.")
    else:
        st.caption("OpenAlex-only filters (Type, Language, UN member states, Semantic search) are hidden because OpenAlex is not selected.")

    # Number of results: label line then control line
    label_col, help_col = st.columns([1, 4])
    with label_col:
        st.markdown("**Max Number / Source**")
    with help_col:
        st.caption("Select the maximum number of results to return per selected data source (max 5000 for each source). For example, if 3 sources are selected and Max Number is 500, the theoretical maximum is 1500 results before filtering and deduplication. More results take longer to load.")
    nr_col1, nr_col2 = st.columns([1, 4])
    with nr_col1:
        st.write("")
    with nr_col2:
        num_results = st.slider("", 1, 1000, 200, label_visibility="collapsed", key="nr")

    sort_by = st.session_state.get("sb", "Relevance")

    results_container = st.container()
    with st.container():
        did_search = False
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Search Selected Source(s)", key="main_search_button", type="primary", use_container_width=True):
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
                        "sources": selected_sources,
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
                        selected_sources,
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
                pending_request.get("sources", selected_sources),
            )
            st.session_state.pop("keyword_search_request", None)
            st.session_state.pop("keyword_search_review", None)
            st.session_state.pop("keyword_search_decision", None)

    cached_payload = st.session_state.get("last_payload")

    if cached_payload and not did_search:
        results_container.success(cached_payload.get("summary", "Results"))

