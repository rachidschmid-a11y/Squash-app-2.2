import streamlit as st

def check_password() -> bool:
    """
    Einfacher, gemeinsamer Passwortschutz für die ganze App.

    Das Passwort wird NICHT im Code hinterlegt, sondern in
    st.secrets["APP_PASSWORD"] (lokal in .streamlit/secrets.toml,
    in der Streamlit-Cloud über die App-Settings -> Secrets).

    Das ist ein simpler Zugriffsschutz für eine kleine, geschlossene Gruppe
    (ein gemeinsames Passwort für alle) - kein Login pro Person. Reicht aber,
    um die App nicht komplett offen für jeden mit dem Link zu lassen.

    Gibt True zurück, wenn die Seite weiter angezeigt werden darf.
    """
    if "APP_PASSWORD" not in st.secrets:
        st.warning(
            "⚠️ Kein `APP_PASSWORD` in den Secrets hinterlegt – die App läuft "
            "aktuell **ohne** Zugriffsschutz. Siehe `.streamlit/secrets.toml.example`."
        )
        return True

    if st.session_state.get("authenticated", False):
        return True

    st.title("🏸 Squash Hub")
    st.subheader("🔒 Anmeldung")

    with st.form("login_form"):
        pw = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("Anmelden")

    if submitted:
        if pw == st.secrets["APP_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Falsches Passwort")

    return False
