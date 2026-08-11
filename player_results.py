import streamlit as st
import pandas as pd
from datetime import datetime
import config as cfg
import database as db
import export_utils
import zeit_utils

@st.dialog("Ergebnis wirklich löschen?")
def confirm_delete_ergebnis_dialog(result_id, beschreibung):
    st.warning(f"Dieses Ergebnis wird unwiderruflich gelöscht: {beschreibung}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, löschen", type="primary", width="stretch"):
            if db.delete_spielergebnis(result_id):
                st.success("Ergebnis erfolgreich gelöscht!")
            st.rerun()
    with col2:
        if st.button("Abbrechen", width="stretch"):
            st.rerun()

def render_player_results_page():
    st.title("🏆 Spielergebnisse eintragen & verwalten")

    aktive_spieler = db.get_aktive_spieler_namen()

    st.subheader("➕ Neues Spielergebnis eintragen")

    if not aktive_spieler:
        st.warning(
            "Es sind noch keine aktiven Spieler hinterlegt. Bitte zuerst unter "
            "'👥 Spielerverwaltung' Spieler anlegen."
        )
    elif len(aktive_spieler) < 2:
        st.warning("Es müssen mindestens 2 aktive Spieler hinterlegt sein, um ein Ergebnis einzutragen.")
    else:
        eingetragen_von = st.selectbox("Wer trägt das Ergebnis ein?", aktive_spieler, key="res_input_by")
        datum = st.date_input("Spieltag", value=datetime.today(), key="res_date")

        col1, col2 = st.columns(2)
        with col1:
            spieler1 = st.selectbox("Spieler 1", aktive_spieler, key="p1")
        with col2:
            spieler2 = st.selectbox("Spieler 2", aktive_spieler, key="p2")

        if spieler1 == spieler2:
            st.warning("Spieler müssen unterschiedlich sein")

        col3, col4 = st.columns(2)
        with col3:
            punkte1 = st.number_input(f"Punkte {spieler1}", min_value=0, max_value=30, value=11, key="pts1")
        with col4:
            punkte2 = st.number_input(f"Punkte {spieler2}", min_value=0, max_value=30, value=7, key="pts2")

        if punkte1 > punkte2:
            gewinner = spieler1
        elif punkte2 > punkte1:
            gewinner = spieler2
        else:
            gewinner = None

        st.write(f"🏆 Gewinner: {gewinner if gewinner else 'Unentschieden (ungültig)'}")

        if st.button("💾 Ergebnis speichern"):
            if spieler1 == spieler2:
                st.error("Spieler dürfen nicht identisch sein")
                return
            if punkte1 == punkte2:
                st.error("Unentschieden ist nicht erlaubt")
                return

            # eingetragen_am weggelassen, da die Datenbank das über DEFAULT NOW() selbst regelt
            data = {
                "gespielt_am": str(datum),
                "gewinner": gewinner,
                "verlierer": spieler2 if gewinner == spieler1 else spieler1,
                "satz_gewinner": punkte1 if gewinner == spieler1 else punkte2,
                "satz_verlierer": punkte2 if gewinner == spieler1 else punkte1,
                "eingetragen_von": eingetragen_von
            }

            # Nur bei echtem Erfolg Erfolgsmeldung zeigen und neu laden
            if db.save_spielergebnis(data):
                st.success("Ergebnis gespeichert!")
                st.rerun()

    st.divider()
    st.subheader("📋 Alle Ergebnisse")
    daten = db.get_spielergebnisse()

    if len(daten) == 0:
        st.info("Noch keine Spielergebnisse vorhanden")
        return

    df = pd.DataFrame(daten)
    if "eingetragen_am" in df.columns:
        df["eingetragen_am"] = zeit_utils.to_berlin_time_str(df["eingetragen_am"])
    st.dataframe(df, width="stretch")

    st.download_button(
        "📥 Ergebnisse als CSV exportieren",
        data=export_utils.to_csv_bytes(df),
        file_name=f"spielergebnisse_{datetime.now().strftime('%Y-%m-%d')}.csv",
        mime="text/csv",
        key="dl_spielergebnisse",
    )

    st.subheader("🗑 Ergebnis löschen")

    optionen = {}
    for r in daten:
        try:
            datum_formatiert = pd.to_datetime(r["gespielt_am"]).strftime('%d.%m.%Y')
        except Exception:
            datum_formatiert = str(r["gespielt_am"])
        text = f"ID {r['id']}: [{datum_formatiert}] {r['gewinner']} vs. {r['verlierer']} ({r['satz_gewinner']}:{r['satz_verlierer']})"
        optionen[r["id"]] = text

    delete_id = st.selectbox(
        "Spiel auswählen",
        options=list(optionen.keys()),
        format_func=lambda x: optionen[x],
        key="del_res_id"
    )

    if st.button("Ergebnis Löschen", type="secondary"):
        confirm_delete_ergebnis_dialog(delete_id, optionen[delete_id])
