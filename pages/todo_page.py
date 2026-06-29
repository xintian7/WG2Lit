import streamlit as st


def render_todo_page() -> None:
    st.divider()
    st.markdown("# To Do")
    st.checkbox("General maintenance after LAM2 (v0.1b)", value=True, key="todo_auth_gs")
    st.checkbox("Zotero integration (v0.2)", value=True, key="todo_zotero")
    st.checkbox("Add multi-page tabs (v0.2)", value=False, key="todo_multi_page")
    st.checkbox("Add more databases, e.g. Scopus, Overton, CORE, ReliefWeb (v0.3)", value=False, key="todo_search_sources")
    st.checkbox("Add cloud-based features (v0.4)", value=False, key="todo_cloud")
    st.checkbox("Performance improvements for larger result sets (v0.4)", value=False, key="todo_performance")
    st.checkbox("General maintenance (v0.4)", value=False, key="todo_maintenance")
    st.checkbox("User accounts and saved searches (v0.5)", value=False, key="todo_accounts")
    st.checkbox("Add Load CSV functionality (v0.5)", value=False, key="todo_load_csv")
    st.checkbox("Add semantic analysis (v0.6)", value=False, key="todo_analysis")
    st.checkbox("Add knowledge graphs (v0.7)", value=False, key="todo_knowledge_graph")
    st.checkbox("UI enhancements (v0.8)", value=False, key="todo_ui_enhancements")
