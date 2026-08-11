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
