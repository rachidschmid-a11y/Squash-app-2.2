import streamlit as st
import dashboard
import ui
import player_results
import spieler_verwaltung
from auth import check_password

SEITEN = [
    "🏠 Dashboard",
    "💰 Abrechnung & Guthaben",
    "🏆 Matches eintragen",
    "📊 Sportliche Statistiken",
    "👥 Spielerverwaltung",
]

def main():
    st.set_page_config(page_title="Squash Hub", page_icon="🏸")

    if not check_password():
        st.stop()

    st.sidebar.title("🏸 Squash Hub")
    st.sidebar.markdown("Wähle ein Modul aus:")

    # Falls eine "Schnelle Aktion" auf dem Dashboard eine Seite angefordert
    # hat (siehe dashboard.py::_wechsle_seite): JETZT übernehmen, bevor das
    # Radio-Widget unten instanziert wird. Streamlit erlaubt es nicht, den
    # session_state-Wert eines Widgets zu ändern, nachdem das Widget im
    # selben Durchlauf schon gerendert wurde ("nav_request" ist deshalb ein
    # eigener, nicht an ein Widget gebundener Zwischenspeicher).
    if "nav_request" in st.session_state:
        st.session_state["nav_choice"] = st.session_state.pop("nav_request")

    if "nav_choice" not in st.session_state:
        st.session_state["nav_choice"] = SEITEN[0]

    wahl = st.sidebar.radio("Navigation", SEITEN, key="nav_choice")

    st.sidebar.divider()
    st.sidebar.caption("Gekoppelt mit Supabase Live-Datenbank.")

    if st.sidebar.button("🚪 Abmelden"):
        st.session_state["authenticated"] = False
        st.rerun()

    # Zentrales Modul-Routing
    if wahl == "🏠 Dashboard":
        dashboard.render_dashboard_page()
    elif wahl == "💰 Abrechnung & Guthaben":
        ui.render_abrechnung_page()
    elif wahl == "🏆 Matches eintragen":
        player_results.render_player_results_page()
    elif wahl == "📊 Sportliche Statistiken":
        ui.render_statistics_page()
    elif wahl == "👥 Spielerverwaltung":
        spieler_verwaltung.render_spielerverwaltung_page()

if __name__ == "__main__":
    main()
