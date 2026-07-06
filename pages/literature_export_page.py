from typing import Any, Callable
import streamlit as st


def render_literature_export_page(
    payload_after_skips: Callable[[dict | None], dict | None],
    payload_to_bibtex: Callable[[dict | None], bytes],
    build_neo4j_cypher: Callable[[dict], bytes],
) -> None:
    st.divider()
    st.markdown("# Literature Export")

    payload = st.session_state.get("last_payload")
    payload_for_download = payload_after_skips(payload)
    bibtex_payload = payload_to_bibtex(payload_for_download)

    csv_file_name = "csv_results.csv"
    json_file_name = "json_results.json"
    bib_file_name = "bibtex_results.bib"
    cypher_file_name = "neo4j_results.cypher"

    if not payload_for_download:
        st.warning("Run a search first to enable exports.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.download_button(
            "Download CSV",
            data=payload_for_download["csv"] if payload_for_download else b"",
            file_name=csv_file_name,
            mime="text/csv",
            key="download_csv_button_export_v2",
            disabled=not bool(payload_for_download),
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Download JSON",
            data=payload_for_download["json"] if payload_for_download else b"",
            file_name=json_file_name,
            mime="application/json",
            key="download_json_button_export_v2",
            disabled=not bool(payload_for_download),
            use_container_width=True,
        )
    with c3:
        st.download_button(
            "Download BibTex (for Zotero)",
            data=bibtex_payload if bibtex_payload else b"",
            file_name=bib_file_name,
            mime="application/x-bibtex",
            key="download_bibtex_button_export_v2",
            disabled=not bool(bibtex_payload),
            use_container_width=True,
        )
    with c4:
        st.download_button(
            "Download Neo4j",
            data=build_neo4j_cypher(payload_for_download) if payload_for_download else b"",
            file_name=cypher_file_name,
            mime="text/plain",
            key="download_neo4j_button_export_v2",
            disabled=not bool(payload_for_download),
            use_container_width=True,
        )
