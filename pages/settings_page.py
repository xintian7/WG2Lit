import streamlit as st


def render_settings_page() -> None:
    st.markdown("# Settings")

    label_col, input_col = st.columns([1, 4])
    with label_col:
        st.write("OpenAlex API")
    with input_col:
        st.text_input(
            "",
            value="",
            placeholder="Placeholder for a future version (currently not required until version 0.5)",
            label_visibility="collapsed",
            key="openalex_api_input",
        )
