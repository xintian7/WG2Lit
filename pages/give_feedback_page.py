from typing import Callable
import streamlit as st


def render_give_feedback_page(
    write_feedback_to_notion: Callable[..., tuple[bool, str]],
    show_back_link: bool = False,
) -> None:
    st.divider()
    st.markdown("# Give Feedback")
    st.markdown("## Feedback Form")
    st.markdown("Any feedback is welcome! Please share your questions or suggestions below to help us improve the app. We will review all feedback carefully and get back to you if you indicate that we can contact you.")
    st.markdown("Please fill out the form below. Fields marked with * are required.")

    with st.form("feedback_form"):
        name = st.text_input("Name (optional)", value="")
        chapter = st.text_input("Chapter (optional)", value="")
        email = st.text_input("Email address (required if you want to be contacted)", value="")
        message = st.text_area("Question or suggestion *", value="", height=160)
        contact_ok = st.checkbox("I would like to be contacted about this inquiry", value=False)
        submitted = st.form_submit_button("Submit")

    if submitted:
        missing = [
            label
            for label, value in (("Question or suggestion", message.strip()),)
            if not value
        ]
        if contact_ok and not email.strip():
            missing.append("Email address")
        email_value = email.strip()
        if email_value and "@" not in email_value:
            st.error("Please enter a valid email address.")
        elif missing:
            st.error(f"Please complete the required fields: {', '.join(missing)}.")
        else:
            ok, msg = write_feedback_to_notion(
                name=name.strip(),
                chapter=chapter.strip(),
                email=email.strip(),
                message=message.strip(),
                contact_ok=contact_ok,
            )
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    if show_back_link:
        st.markdown("[Back to Climate Literature Navigator](?page=)")
