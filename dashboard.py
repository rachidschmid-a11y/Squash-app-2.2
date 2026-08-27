import streamlit as st
import pandas as pd
import database as db
import calculations as calc

"""
Zentrale Startseite ("🏠 Dashboard").

Zeigt nur eine kompakte Zusammenfassung bereits vorhandener Daten
(Kartenguthaben, aktive Spieler, letzte Session, Match-Statistik) sowie
Schnellzugriffe auf die anderen Seiten. Enthält bewusst KEINE eigene
Geschäftslogik - alle Zahlen kommen unverändert aus database.py bzw.
calculations.py (z.B. calc.player_stats, das auch die Statistik-Seite
nutzt).
"""


def _wechsle_seite(seite: str):
    """Schaltet die Sidebar-Navigation programmatisch um (für die
    'Schnelle Aktionen'-Buttons unten).

    Setzt bewusst NICHT direkt st.session_state['nav_choice'] - das ist der
    Key des Radio-Widgets in app.py, und Streamlit verbietet es, den
    session_state-Wert eines Widgets zu ändern, nachdem das Widget im
    selben Durchlauf schon gerendert wurde (hier: die Sidebar-Navigation
    ganz oben in app.py::main(), bevor render_dashboard_page() aufgerufen
    wird). Stattdessen wird ein eigener 'nav_request'-Zwischenspeicher
    gesetzt, den app.py beim nächsten Durchlauf VOR dem Radio-Widget
    ausliest und übernimmt."""
    st.session_state["nav_request"] = seite
    st.rerun()


def render_dashboard_page():
    st.title("🏸 Squash Hub")
    st.caption("Alles Wichtige auf einen Blick.")

    karte = db.get_karte()
    aktive_spieler = db.get_aktive_spieler_namen()
    spiele = db.get_spiele()
    ergebnisse = db.get_spielergebnisse()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 💳 Aktuelle Karte")
        if karte:
            st.metric("Guthaben", f"{karte['guthaben']:.2f} €")
            if karte.get("anfangsguthaben") is not None:
                verbraucht = round(karte["anfangsguthaben"] - karte["guthaben"], 2)
                st.caption(f"Verbraucht: {verbraucht:.2f} € von {karte['anfangsguthaben']:.2f} €")
            st.caption(f"Bezahlt von **{karte.get('bezahlt_von', 'Unbekannt')}**")
        else:
            st.info("Keine aktive Karte vorhanden.")
    with col2:
        st.markdown("#### 👥 Aktive Spieler")
        st.metric("Anzahl", len(aktive_spieler))
        if aktive_spieler:
            st.caption(", ".join(aktive_spieler))

    st.divider()
    st.markdown("#### 📅 Letzte Session")
    if spiele:
        df_spiele = pd.DataFrame(spiele)
        # get_spiele() liefert nach id absteigend sortiert -> erste Zeile
        # gehört zum zuletzt eingetragenen Termin.
        letzter_termin = df_spiele.iloc[0]
        beteiligte = df_spiele[
            (df_spiele["gespielt_am"] == letzter_termin["gespielt_am"])
            & (df_spiele["gespielt_uhrzeit"] == letzter_termin["gespielt_uhrzeit"])
        ]["spieler"].tolist()
        datum_str = pd.to_datetime(letzter_termin["gespielt_am"]).strftime("%d.%m.%Y")
        st.write(f"**{datum_str}** · {' · '.join(beteiligte)}")
    else:
        st.info("Noch keine Sessions auf der aktuellen Karte erfasst.")

    st.divider()
    st.markdown("#### 🏆 Match-Statistik")
    if ergebnisse and aktive_spieler:
        df_erg = pd.DataFrame(ergebnisse)
        bestenliste = []
        for name in aktive_spieler:
            stats = calc.player_stats(df_erg, name)
            if stats["gesamt"] > 0:
                bestenliste.append((name, stats))
        if bestenliste:
            bestenliste.sort(key=lambda eintrag: eintrag[1]["quote"], reverse=True)
            top_name, top_stats = bestenliste[0]
            st.write(
                f"🥇 **{top_name}** führt aktuell: {top_stats['siege']} Siege, "
                f"{top_stats['niederlagen']} Niederlagen ({top_stats['quote']:.1f} %)"
            )
        else:
            st.info("Noch keine ausgewerteten Matches unter den aktiven Spielern.")
    else:
        st.info("Noch keine Match-Ergebnisse erfasst.")

    st.divider()
    st.markdown("#### Schnelle Aktionen")
    if st.button("➕ Spiel eintragen", width="stretch"):
        _wechsle_seite("💰 Abrechnung & Guthaben")
    if st.button("🏆 Ergebnis eintragen", width="stretch"):
        _wechsle_seite("🏆 Matches eintragen")
    if st.button("📊 Statistiken öffnen", width="stretch"):
        _wechsle_seite("📊 Sportliche Statistiken")
    if st.button("👥 Spieler verwalten", width="stretch"):
        _wechsle_seite("👥 Spielerverwaltung")
