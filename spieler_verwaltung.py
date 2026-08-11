import streamlit as st
import database as db

@st.dialog("Spieler wirklich löschen?")
def confirm_delete_spieler_dialog(spieler_id, name):
    st.warning(
        f"'{name}' wird endgültig aus der Spielerliste entfernt.\n\n"
        f"Bereits gespeicherte Spiele und Ergebnisse mit diesem Namen bleiben "
        f"in der Datenbank erhalten - '{name}' taucht danach nur nicht mehr in "
        f"Auswahllisten für neue Einträge auf.\n\n"
        f"Tipp: Falls '{name}' nur vorübergehend pausiert (statt einem "
        f"Tippfehler), lieber 'Deaktivieren' statt 'Löschen' verwenden - das "
        f"lässt sich jederzeit rückgängig machen."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, endgültig löschen", type="primary", width="stretch"):
            if db.delete_spieler(spieler_id):
                st.success(f"'{name}' wurde gelöscht.")
            st.rerun()
    with col2:
        if st.button("Abbrechen", width="stretch"):
            st.rerun()

def render_spielerverwaltung_page():
    st.title("👥 Spielerverwaltung")
    st.caption(
        "Die Spielerliste wird in der Datenbank gepflegt - keine Code-Änderung "
        "mehr nötig, wenn jemand dazukommt oder aufhört."
    )

    st.subheader("➕ Neuen Spieler hinzufügen")
    with st.form("neuer_spieler_form", clear_on_submit=True):
        neuer_name = st.text_input("Name")
        submitted = st.form_submit_button("Hinzufügen")

    if submitted:
        name = neuer_name.strip()
        if not name:
            st.warning("Bitte einen Namen eingeben.")
        else:
            bestehende_namen = {s["name"].lower() for s in db.get_spieler()}
            if name.lower() in bestehende_namen:
                st.error(f"'{name}' ist bereits in der Liste vorhanden.")
            else:
                if db.insert_spieler(name):
                    st.success(f"'{name}' wurde hinzugefügt.")
                    st.rerun()

    st.divider()
    st.subheader("Aktuelle Spieler")

    spieler = db.get_spieler()
    if not spieler:
        st.info("Noch keine Spieler angelegt.")
        return

    for s in spieler:
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            status = "🟢 aktiv" if s["aktiv"] else "⚪ inaktiv"
            st.write(f"**{s['name']}** — {status}")
        with col2:
            label = "Deaktivieren" if s["aktiv"] else "Aktivieren"
            if st.button(label, key=f"toggle_{s['id']}", width="stretch"):
                if db.set_spieler_aktiv(s["id"], not s["aktiv"]):
                    st.rerun()
        with col3:
            if st.button("🗑️ Löschen", key=f"del_{s['id']}", width="stretch"):
                confirm_delete_spieler_dialog(s["id"], s["name"])
