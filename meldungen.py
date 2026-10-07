"""
Meldungen, die einen st.rerun() überleben.

Problem: st.success(...) gefolgt von st.rerun() zeigt die Meldung nie an,
weil der Rerun die Seite sofort neu aufbaut. Deshalb wird die Meldung hier
zwischengespeichert (st.session_state) und von app.py einmalig ganz oben auf
der nächsten Seite angezeigt.

Nutzung:  meldungen.merke("Gespeichert!")  ->  st.rerun()
          meldungen.zeige()  (einmal pro Durchlauf, siehe app.py)
"""
import streamlit as st

_KEY = "_meldungen"


def merke(text: str, art: str = "success"):
    """Merkt eine Meldung für die nächste Seitendarstellung vor.
    art: "success", "info", "warning" oder "error"."""
    st.session_state.setdefault(_KEY, []).append((art, text))


def zeige():
    """Zeigt alle vorgemerkten Meldungen an und leert den Speicher."""
    darstellung = {
        "success": st.success,
        "info": st.info,
        "warning": st.warning,
        "error": st.error,
    }
    # Der Container wird IMMER angelegt (auch ohne Meldung): Würde die Meldung
    # nur manchmal als zusätzliches Element oben eingefügt, verschöbe sich alles
    # darunter - und die Tabs der Seite sprängen dann zurück auf den ersten Tab.
    platz = st.container()
    with platz:
        for art, text in st.session_state.pop(_KEY, []):
            darstellung.get(art, st.info)(text)
