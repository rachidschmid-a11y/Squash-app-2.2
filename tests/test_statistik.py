"""
Tests für statistik.py (Rangliste, Bilanz pro Gegner) und die Zeitstempel-
Umrechnung aus zeit_utils.py. Beide Module brauchen weder Datenbank noch
Streamlit-Secrets.

Ausführen mit:  pytest
"""
import pandas as pd

import statistik
import zeit_utils


def _ergebnisse():
    return pd.DataFrame([
        {"id": 1, "gespielt_am": "2026-08-01", "gewinner": "Anna", "verlierer": "Ben"},
        {"id": 2, "gespielt_am": "2026-08-02", "gewinner": "Anna", "verlierer": "Ben"},
        {"id": 3, "gespielt_am": "2026-08-03", "gewinner": "Ben", "verlierer": "Anna"},
        {"id": 4, "gespielt_am": "2026-08-04", "gewinner": "Clara", "verlierer": "Ben"},
    ])


def test_rangliste_sortiert_nach_quote_und_vergibt_raenge():
    tabelle = statistik.rangliste(_ergebnisse(), ["Anna", "Ben", "Clara", "David"])

    assert list(tabelle["Spieler"]) == ["Clara", "Anna", "Ben"]   # David: keine Spiele -> fehlt
    assert list(tabelle["Rang"]) == ["🥇", "🥈", "🥉"]
    assert list(tabelle["Quote %"]) == [100.0, 66.7, 25.0]
    anna = tabelle[tabelle["Spieler"] == "Anna"].iloc[0]
    assert (anna["Spiele"], anna["Siege"], anna["Niederlagen"]) == (3, 2, 1)


def test_rangliste_bei_gleicher_quote_entscheiden_mehr_siege():
    df = pd.DataFrame([
        {"gewinner": "Anna", "verlierer": "Ben"}, {"gewinner": "Ben", "verlierer": "Anna"},
        {"gewinner": "Clara", "verlierer": "David"}, {"gewinner": "David", "verlierer": "Clara"},
        {"gewinner": "Clara", "verlierer": "David"}, {"gewinner": "David", "verlierer": "Clara"},
    ])
    tabelle = statistik.rangliste(df, ["Anna", "Ben", "Clara", "David"])
    # Alle 50 %, aber Clara/David haben je 2 Siege, Anna/Ben nur 1
    assert set(tabelle["Spieler"][:2]) == {"Clara", "David"}


def test_rangliste_ohne_ergebnisse_ist_leer_aber_hat_die_spalten():
    leer = statistik.rangliste(pd.DataFrame(columns=["gewinner", "verlierer"]), ["Anna"])
    assert leer.empty
    assert list(leer.columns) == statistik.RANGLISTE_SPALTEN


def test_bilanz_pro_gegner_zaehlt_beide_richtungen_und_zeigt_form():
    bilanz = statistik.bilanz_pro_gegner(_ergebnisse(), "Anna", ["Anna", "Ben", "Clara", "David"])

    assert list(bilanz["Gegner"]) == ["Ben"]          # nur Gegner, gegen die gespielt wurde
    ben = bilanz.iloc[0]
    assert (ben["Spiele"], ben["Siege"], ben["Niederlagen"], ben["Quote %"]) == (3, 2, 1, 66.7)
    assert ben["Letzte Spiele"] == "✅ ✅ ❌"           # chronologisch, neuestes rechts


def test_bilanz_pro_gegner_begrenzt_die_form_auf_die_letzten_n_spiele():
    df = pd.DataFrame([
        {"id": i, "gespielt_am": f"2026-08-{i:02d}", "gewinner": "Anna" if i % 2 else "Ben",
         "verlierer": "Ben" if i % 2 else "Anna"} for i in range(1, 9)
    ])
    form = statistik.bilanz_pro_gegner(df, "Anna", ["Anna", "Ben"], letzte_n=3).iloc[0]["Letzte Spiele"]
    assert len(form.split()) == 3


def test_bilanz_ohne_spiele_ist_leer():
    leer = statistik.bilanz_pro_gegner(_ergebnisse(), "David", ["Anna", "David"])
    assert leer.empty
    assert list(leer.columns) == statistik.BILANZ_SPALTEN


# ---------------------------------------------------------------------------
# zeit_utils: gemischte Zeitstempel-Formate dürfen nicht abstürzen
# ---------------------------------------------------------------------------

def test_berlin_zeit_verkraftet_gemischte_zeitstempel_formate():
    # Postgres liefert Zeitstempel mal mit, mal ohne Sekundenbruchteile (z.B.
    # bei per SQL nachgetragenen Zeilen). Früher brach pandas dabei ab.
    reihe = pd.Series([
        "2026-08-17T19:27:00.540425+00:00",
        "2026-08-24T18:32:17+00:00",
        "2026-08-25T06:47:05.5+00:00",
    ])
    ergebnis = zeit_utils.to_berlin_time_str(reihe)
    assert list(ergebnis) == ["17.08.2026 21:27", "24.08.2026 20:32", "25.08.2026 08:47"]   # Sommerzeit: UTC+2
