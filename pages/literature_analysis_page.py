from typing import Any, Callable
import json
import streamlit as st


def _payload_records(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Decode cached payload JSON records for source-scoped analysis."""
    if not payload:
        return []

    raw_json = payload.get("json") or "[]"
    if isinstance(raw_json, bytes):
        raw_json = raw_json.decode("utf-8", errors="ignore")

    try:
        records = json.loads(raw_json)
    except Exception:
        return []

    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def _payload_for_source(payload: dict[str, Any], selected_source: str) -> dict[str, Any]:
    """Return a payload narrowed to one selected source."""
    records = [
        record
        for record in _payload_records(payload)
        if str(record.get("Source") or "OpenAlex").strip() == selected_source
    ]

    filtered_payload = dict(payload)
    filtered_payload["json"] = json.dumps(records, indent=2, ensure_ascii=False).encode("utf-8")
    filtered_payload["total"] = len(records)
    filtered_payload["shown"] = len(records)
    return filtered_payload


def render_literature_analysis_page(perform_analyze: Callable[..., Any]) -> None:
    st.divider()
    st.markdown("# Literature Analysis")

    payload = st.session_state.get("last_payload")
    if not payload:
        st.warning("Run a search first to analyze results.")
        return

    records = _payload_records(payload)
    available_sources = []
    seen_sources = set()
    for record in records:
        source_name = str(record.get("Source") or "OpenAlex").strip() or "OpenAlex"
        if source_name in seen_sources:
            continue
        seen_sources.add(source_name)
        available_sources.append(source_name)

    if not available_sources:
        st.warning("No source information is available in the cached search results.")
        return

    selected_analysis_source = st.selectbox(
        "Data source",
        options=available_sources,
        index=0,
        key="analysis_source",
        help="Select one data source to analyze at a time.",
    )

    filtered_payload = _payload_for_source(payload, selected_analysis_source)
    if not filtered_payload.get("total"):
        st.warning(f"No records are available for {selected_analysis_source} in the cached results.")
        return

    year_range = st.session_state.get("yr", st.session_state.get("last_search_year_range", (1900, 2027)))
    analyze_container = st.container()
    did_analyze = False

    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    with btn_col1:
        if st.button("Analyze Results", key="analyze_results_button", type="primary", use_container_width=True):
            st.session_state["last_analyze_triggered"] = True
            perform_analyze(filtered_payload, year_range, container=analyze_container)
            did_analyze = True
    with btn_col2:
        if st.button("Clear Results", key="clear_results_button", type="primary", use_container_width=True):
            st.session_state.pop("last_analyze_triggered", None)
            analyze_container.empty()
            st.rerun()
    with btn_col3:
        st.write("")
    with btn_col4:
        st.write("")

    if st.session_state.get("last_analyze_triggered") and not did_analyze:
        perform_analyze(filtered_payload, year_range, container=analyze_container)
