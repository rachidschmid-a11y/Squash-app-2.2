import streamlit as st
import ui
import player_results
import spieler_verwaltung
from auth import check_password

def main():
    st.set_page_config(page_title="Squash Hub", page_icon="🏸")

    if not check_password():
        st.stop()

    st.sidebar.title("🏸 Squash Hub")
    st.sidebar.markdown("Wähle ein Modul aus:")

    wahl = st.sidebar.radio(
        "Navigation",
        ["💰 Abrechnung & Guthaben", "🏆 Matches eintragen", "📊 Sportliche Statistiken", "👥 Spielerverwaltung"]
    )

    st.sidebar.divider()
    st.sidebar.caption("Gekoppelt mit Supabase Live-Datenbank.")

    if st.sidebar.button("🚪 Abmelden"):
        st.session_state["authenticated"] = False
        st.rerun()

    # Zentrales Modul-Routing
    if wahl == "💰 Abrechnung & Guthaben":
        ui.render_abrechnung_page()
    elif wahl == "🏆 Matches eintragen":
        player_results.render_player_results_page()
    elif wahl == "📊 Sportliche Statistiken":
        ui.render_statistics_page()
    elif wahl == "👥 Spielerverwaltung":
        spieler_verwaltung.render_spielerverwaltung_page()

if __name__ == "__main__":
    main()
