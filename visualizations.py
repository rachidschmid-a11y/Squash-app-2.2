import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import calculations as calc

def plot_costs_bar(df_stats):
    fig = px.bar(df_stats, x="spieler", y="kosten", title="Absolute Kosten pro Spieler (€)",
                  labels={"kosten": "Euro", "spieler": "Name"}, color="spieler")
    st.plotly_chart(fig, width="stretch")

def plot_costs_pie(df_stats):
    fig = px.pie(df_stats, names="spieler", values="kosten", title="Kostenverteilung (%)")
    st.plotly_chart(fig, width="stretch")

def render_karten_uebersicht(karte, spiele_der_karte=None):
    """
    Detaillierte Kartenübersicht (Aufgeladen/Bezahlt/Verbraucht/Restguthaben)
    + Fortschrittsbalken + grobe Reichweiten-Schätzung basierend auf dem
    bisherigen Durchschnittsverbrauch pro Session.

    Reine Anzeige-Funktion - berechnet nichts, was Auswirkungen auf
    Guthaben/Abrechnung hätte (das bleibt exklusiv calculations.py
    vorbehalten). Bei fehlenden Werten (z.B. alte Karten ohne
    anfangsguthaben) wird "–" statt eines falschen Werts angezeigt.
    """
    aufgeladen = karte.get("anfangsguthaben")
    bezahlt = karte.get("bezahlt_betrag")
    rest = karte["guthaben"]
    verbraucht = round(aufgeladen - rest, 2) if aufgeladen is not None else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aufgeladen", f"{aufgeladen:.2f} €" if aufgeladen is not None else "–")
    c2.metric("Bezahlt", f"{bezahlt:.2f} €" if bezahlt is not None else "–")
    c3.metric("Verbraucht", f"{verbraucht:.2f} €" if verbraucht is not None else "–")
    c4.metric("Restguthaben", f"{rest:.2f} €")

    if aufgeladen and aufgeladen > 0:
        anteil = max(0.0, min(1.0, verbraucht / aufgeladen))
        st.progress(anteil, text=f"{verbraucht:.2f} € von {aufgeladen:.2f} € verbraucht")

    if spiele_der_karte:
        df = pd.DataFrame(spiele_der_karte)
        # Mehrere Spieler-Zeilen derselben Session (gleicher Termin) zu einer
        # Session-Summe zusammenfassen, um einen realistischen
        # Durchschnittswert PRO SESSION statt pro Spieler-Anteil zu erhalten.
        session_summen = df.groupby(["gespielt_am", "gespielt_uhrzeit"])["kosten"].sum()
        durchschnitt = session_summen.mean() if len(session_summen) > 0 else 0
        if durchschnitt > 0:
            reichweite = int(rest // durchschnitt)
            st.caption(
                f"📈 Reicht bei ähnlichem Verbrauch noch für ca. **{reichweite}** "
                f"weitere Session(s) (Ø {durchschnitt:.2f} € / Session)."
            )


def render_split_balken(gedeckt: float, ueberschuss: float, label_gedeckt="Aktuelle Karte", label_neu="Nächste Karte"):
    """
    Zweigeteilter Fortschrittsbalken für einen Betrag, der (weil das
    Guthaben nicht mehr reicht) auf zwei Karten aufgeteilt wird - siehe
    calculations.py::speichern_logik, Abschnitt "Überschuss-Splitting".

    Reine Anzeige: die tatsächliche Aufteilung/Rundung passiert
    ausschließlich in calculations.py, hier wird nur visualisiert, was dort
    (bzw. für die Vorschau: was dort passieren WÜRDE) berechnet wurde.
    """
    gesamt = round(gedeckt + ueberschuss, 2)
    if gesamt <= 0:
        return
    if gedeckt < 0:
        # Randfall: der übernommene Überschuss ist größer als der komplette
        # verfügbare Betrag (z.B. neue Karte kleiner als der Alt-Überschuss).
        # st.progress() akzeptiert nur Werte zwischen 0 und 1 - hier lieber
        # eine deutliche Warnung statt eines Absturzes.
        st.error(
            f"⚠️ Der offene Überschuss ({ueberschuss:.2f} €) übersteigt bereits den gesamten "
            f"verfügbaren Betrag ({gesamt:.2f} €) - bitte Werte prüfen."
        )
        return
    st.caption(f"Gesamtkosten dieser Session: **{gesamt:.2f} €**")
    anteil_gedeckt = gedeckt / gesamt

    col1, col2 = st.columns(2)
    with col1:
        st.caption(label_gedeckt)
        st.progress(anteil_gedeckt, text=f"{gedeckt:.2f} €")
    with col2:
        st.caption(label_neu)
        st.progress(1 - anteil_gedeckt, text=f"{ueberschuss:.2f} €")

    if ueberschuss > 0:
        st.info(
            f"ℹ️ {ueberschuss:.2f} € übersteigen das aktuelle Guthaben und werden "
            f"automatisch auf die nächste aktivierte Karte übertragen."
        )


def plot_match_scatter(df, spieler, alle_spieler):
    st.subheader(f"📊 Statistik für {spieler}")
    matchups = calc.filter_matchups(df, spieler, alle_spieler)
    if not matchups:
        st.info("Keine Daten für diesen Spieler")
        return

    for gegner, daten in matchups.items():
        daten = daten.sort_values("gespielt_am")
        daten["spiel_nr"] = range(1, len(daten) + 1)
        daten["ergebnis"] = daten["gewinner"].apply(lambda x: 1 if x == spieler else 0)

        fig, ax = plt.subplots(figsize=(8, 3))
        ax.scatter(daten["spiel_nr"], daten["ergebnis"], s=80)
        ax.set_title(f"{spieler} vs {gegner}")
        ax.set_xlabel("Spielnummer")
        ax.set_ylabel("Ergebnis")
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Niederlage", "Sieg"])
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
