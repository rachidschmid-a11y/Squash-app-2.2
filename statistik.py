"""
Auswertungen für die Seite "Sportliche Statistiken" (Rangliste, Bilanz pro
Gegner). Reine Funktionen auf einem DataFrame der Tabelle "spielergebnisse"
(Spalten gewinner, verlierer, gespielt_am) - ohne Streamlit- oder
Datenbank-Abhängigkeit, damit sie einfach testbar sind.
"""
import pandas as pd

RANG_ANZEIGE = {1: "🥇", 2: "🥈", 3: "🥉"}

RANGLISTE_SPALTEN = ["Rang", "Spieler", "Spiele", "Siege", "Niederlagen", "Quote %"]
BILANZ_SPALTEN = ["Gegner", "Spiele", "Siege", "Niederlagen", "Quote %", "Letzte Spiele"]


def rangliste(df: pd.DataFrame, spieler_namen) -> pd.DataFrame:
    """Rangliste aller Spieler mit mindestens einem Spiel, sortiert nach
    Siegquote (bei Gleichstand: mehr Siege, dann mehr Spiele)."""
    zeilen = []
    for name in spieler_namen:
        siege = int((df["gewinner"] == name).sum())
        niederlagen = int((df["verlierer"] == name).sum())
        gesamt = siege + niederlagen
        if gesamt == 0:
            continue
        zeilen.append({
            "Spieler": name,
            "Spiele": gesamt,
            "Siege": siege,
            "Niederlagen": niederlagen,
            "Quote %": round(siege / gesamt * 100, 1),
        })
    if not zeilen:
        return pd.DataFrame(columns=RANGLISTE_SPALTEN)

    ergebnis = (
        pd.DataFrame(zeilen)
        .sort_values(["Quote %", "Siege", "Spiele"], ascending=[False, False, False], kind="stable")
        .reset_index(drop=True)
    )
    ergebnis.insert(0, "Rang", [RANG_ANZEIGE.get(i, str(i)) for i in range(1, len(ergebnis) + 1)])
    return ergebnis


def bilanz_pro_gegner(df: pd.DataFrame, spieler: str, alle_spieler, letzte_n: int = 5) -> pd.DataFrame:
    """Bilanz eines Spielers gegen jeden Gegner, gegen den er schon gespielt
    hat, inkl. Form der letzten Spiele (✅ Sieg / ❌ Niederlage, älteste links,
    neuestes rechts)."""
    zeilen = []
    for gegner in alle_spieler:
        if gegner == spieler:
            continue
        duelle = df[
            ((df["gewinner"] == spieler) & (df["verlierer"] == gegner))
            | ((df["gewinner"] == gegner) & (df["verlierer"] == spieler))
        ]
        if duelle.empty:
            continue
        sortierung = ["gespielt_am", "id"] if "id" in duelle.columns else ["gespielt_am"]
        duelle = duelle.sort_values(sortierung, kind="stable")
        anzahl = len(duelle)
        siege = int((duelle["gewinner"] == spieler).sum())
        form = " ".join("✅" if g == spieler else "❌" for g in duelle["gewinner"].tolist()[-letzte_n:])
        zeilen.append({
            "Gegner": gegner,
            "Spiele": anzahl,
            "Siege": siege,
            "Niederlagen": anzahl - siege,
            "Quote %": round(siege / anzahl * 100, 1),
            "Letzte Spiele": form,
        })
    if not zeilen:
        return pd.DataFrame(columns=BILANZ_SPALTEN)
    return pd.DataFrame(zeilen)
