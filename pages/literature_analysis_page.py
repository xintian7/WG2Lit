from typing import Any, Callable
import streamlit as st


def render_literature_analysis_page(perform_analyze: Callable[..., Any]) -> None:
    st.divider()
    st.markdown("# Literature Analysis")

    payload = st.session_state.get("last_payload")
    if not payload:
        st.warning("Run a search first to analyze results.")
        return

    year_range = st.session_state.get("yr", (2000, 2025))
    analyze_container = st.container()
    did_analyze = False

    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    with btn_col1:
        if st.button("Analyze Results", key="analyze_results_button", type="primary", use_container_width=True):
            st.session_state["last_analyze_triggered"] = True
            perform_analyze(payload, year_range, container=analyze_container)
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
        perform_analyze(payload, year_range, container=analyze_container)
