from typing import Any, Callable
import streamlit as st


def render_literature_export_page(
    payload_for_all_exports: Callable[[dict | None], dict | None],
    payload_after_skips: Callable[[dict | None], dict | None],
    payload_after_review_filters: Callable[[dict | None], dict | None],
    payload_to_bibtex: Callable[[dict | None], bytes],
    build_neo4j_cypher: Callable[[dict], bytes],
) -> None:
    st.divider()
    st.markdown("# Literature Export")

    payload = st.session_state.get("last_payload")
    payload_for_download_all = payload_for_all_exports(payload)
    payload_for_download_skips = payload_after_skips(payload)
    payload_for_download_review = payload_after_review_filters(payload)
    bibtex_payload_all = payload_to_bibtex(payload_for_download_all)
    bibtex_payload_review = payload_to_bibtex(payload_for_download_review)

    csv_file_name = "csv_results.csv"
    json_file_name = "json_results.json"
    bib_file_name = "bibtex_results.bib"
    cypher_file_name = "neo4j_results.cypher"

    if not payload:
        st.warning("Run a search first to enable exports.")

    st.markdown("## Download All Files")
    st.caption("Exports the full cached search results without Literature Review filtering or skipping.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.download_button(
            "Download CSV",
            data=payload_for_download_all["csv"] if payload_for_download_all else b"",
            file_name=csv_file_name,
            mime="text/csv",
            key="download_csv_button_export_all",
            disabled=not bool(payload_for_download_all),
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Download JSON",
            data=payload_for_download_all["json"] if payload_for_download_all else b"",
            file_name=json_file_name,
            mime="application/json",
            key="download_json_button_export_all",
            disabled=not bool(payload_for_download_all),
            use_container_width=True,
        )
    with c3:
        st.download_button(
            "Download BibTex (for Zotero)",
            data=bibtex_payload_all if bibtex_payload_all else b"",
            file_name=bib_file_name,
            mime="application/x-bibtex",
            key="download_bibtex_button_export_all",
            disabled=not bool(bibtex_payload_all),
            use_container_width=True,
        )
    with c4:
        st.download_button(
            "Download Neo4j",
            data=build_neo4j_cypher(payload_for_download_all) if payload_for_download_all else b"",
            file_name=cypher_file_name,
            mime="text/plain",
            key="download_neo4j_button_export_all",
            disabled=not bool(payload_for_download_all),
            use_container_width=True,
        )

    st.markdown("## Download Files After Literature Review")
    st.caption("Exports only the records remaining after Literature Review filters and skipped items are applied.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.download_button(
            "Download CSV",
            data=payload_for_download_review["csv"] if payload_for_download_review else b"",
            file_name=csv_file_name,
            mime="text/csv",
            key="download_csv_button_export_review",
            disabled=not bool(payload_for_download_review),
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Download JSON",
            data=payload_for_download_review["json"] if payload_for_download_review else b"",
            file_name=json_file_name,
            mime="application/json",
            key="download_json_button_export_review",
            disabled=not bool(payload_for_download_review),
            use_container_width=True,
        )
    with c3:
        st.download_button(
            "Download BibTex (for Zotero)",
            data=bibtex_payload_review if bibtex_payload_review else b"",
            file_name=bib_file_name,
            mime="application/x-bibtex",
            key="download_bibtex_button_export_review",
            disabled=not bool(bibtex_payload_review),
            use_container_width=True,
        )
    with c4:
        st.download_button(
            "Download Neo4j",
            data=build_neo4j_cypher(payload_for_download_review) if payload_for_download_review else b"",
            file_name=cypher_file_name,
            mime="text/plain",
            key="download_neo4j_button_export_review",
            disabled=not bool(payload_for_download_review),
            use_container_width=True,
        )
