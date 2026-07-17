import streamlit as st


def render_about_page() -> None:
    st.divider()
    st.markdown(
        """
        <div style="
            background-color:#EAF4FF;
            border:1px solid #BBDFFF;
            border-radius:8px;
            padding:12px 14px;
            margin:8px 0 14px 0;
            text-align:center;
            color:#1F2D3D;
            font-size:15px;
        ">
            <strong>Please also kindly note that, for operational reasons, this tool has been developed exclusively for WGII Coordinating Lead Authors (CLAs), Lead Authors (LAs), and Chapter Scientists (CSs) supporting their respective CLAs and LAs. Please do not share this tool beyond this designated user group.</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("# About")
    st.markdown(
        "Climate Literature Navigator (ver 0.4) is a web app developed by the "
        "[IPCC WGII](https://www.ipcc.ch/working-group/wg2/) TSU to help IPCC authors "
        "find climate-related literature from [OpenAlex](https://openalex.org/), "
        "[ReliefWeb](https://reliefweb.int/), [UN Digital Library](https://digitallibrary.un.org/), "
        "and [World Bank Documents & Reports](https://documents.worldbank.org/)."
    )
    st.markdown(
        "You can use the tabs from the left panel to search, analyze, or export literature. "
        "We strongly suggest that you read the Disclaimer and User Guide before using the app."
    )
    st.markdown(
        'Please kindly provide your feedback <a href="?tab=give-feedback" target="_self">here</a>, '
        'or contact <a href="mailto:tsu@ipccwg2.org">tsu@ipccwg2.org</a> '
        'if you have any questions or suggestions.',
        unsafe_allow_html=True,
    )
