from pathlib import Path
import streamlit as st


def render_disclaimer_page(base_path: Path) -> None:
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
    st.markdown("# Disclaimer")
    st.markdown(
        "Please carefully review the Terms of Use and Privacy Policy before using this app. "
        "By using the app, you agree to the terms outlined in these documents."
    )
    st.markdown("Jump to: [Terms of Use](#terms-of-use) | [Privacy Policy](#privacy-policy)")
    st.markdown(
        "Please also note that the information provided by Climate Literature Navigator is sourced from "
        "[OpenAlex](https://openalex.org/), [ReliefWeb](https://reliefweb.int/), "
        "[UN Digital Library](https://digitallibrary.un.org/), and "
        "[World Bank Documents & Reports](https://documents.worldbank.org/). While we strive to ensure accuracy, we cannot guarantee the completeness "
        "or reliability of the data. Users should verify the information independently before making decisions based on it."
    )

    st.markdown("<a id='terms-of-use'></a>", unsafe_allow_html=True)
    st.markdown("## Terms of Use")
    terms_path = base_path / "assets" / "Terms of Use.txt"
    if terms_path.exists():
        terms_text = terms_path.read_text(encoding="utf-8").strip()
        terms_lines = terms_text.splitlines()
        if terms_lines:
            first_line = terms_lines[0].lstrip("# ").strip().strip("*")
            if first_line.lower() == "terms of use":
                terms_text = "\n".join(terms_lines[1:]).lstrip()
        terms_text = terms_text.replace("## ", "### ")
        st.markdown(terms_text if terms_text else "Terms of Use content is currently unavailable.")
    else:
        st.warning("Document file not found: assets/Terms of Use.txt")

    st.divider()
    st.markdown("<a id='privacy-policy'></a>", unsafe_allow_html=True)
    st.markdown("## Privacy Policy")
    privacy_path = base_path / "assets" / "Privacy Policy.txt"
    if privacy_path.exists():
        privacy_text = privacy_path.read_text(encoding="utf-8").strip()
        privacy_lines = privacy_text.splitlines()
        if privacy_lines:
            first_line = privacy_lines[0].lstrip("# ").strip().strip("*")
            if first_line.lower() == "privacy policy":
                privacy_text = "\n".join(privacy_lines[1:]).lstrip()
        privacy_text = privacy_text.replace("## ", "### ")
        st.markdown(privacy_text if privacy_text else "Privacy Policy content is currently unavailable.")
    else:
        st.warning("Document file not found: assets/Privacy Policy.txt")
