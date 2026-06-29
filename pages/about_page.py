import streamlit as st


def render_about_page() -> None:
    st.divider()
    st.markdown("# About")
    st.markdown(
        "Climate Literature Navigator (ver 0.2) is a web app developed by the "
        "[IPCC WGII](https://www.ipcc.ch/working-group/wg2/) TSU to help IPCC authors "
        "find climate-related literature from [OpenAlex](https://openalex.org/)'s database."
    )
    st.markdown(
        'Please kindly provide your feedback <a href="?tab=give-feedback" target="_self">here</a>, '
        'or contact <a href="mailto:tsu@ipccwg2.org">tsu@ipccwg2.org</a> '
        'if you have any questions or suggestions.',
        unsafe_allow_html=True,
    )
