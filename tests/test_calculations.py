"""
Ein paar Basis-Tests für die Kernlogik in calculations.py - vor allem für die
Abrechnung, weil dort echtes Geld verteilt wird.

Ausführen mit:  pytest

Das echte "database"-Modul braucht beim Import gültige Streamlit-Secrets
(SUPABASE_URL/SUPABASE_KEY), die in einer Test-Umgebung normalerweise nicht
vorhanden sind. Deshalb wird "database" hier durch ein einfaches Fake-Modul
ersetzt, BEVOR calculations importiert wird. Die einzelnen Tests ersetzen die
benötigten Funktionen dann gezielt per monkeypatch.
"""
import sys
import types
from datetime import date, time

import pandas as pd
import pytest

_fake_db = types.ModuleType("database")
_fake_db.get_karte = lambda: None
_fake_db.get_spiele = lambda: []
_fake_db.get_offene_spiele_fuer_karte = lambda karte_id: []
_fake_db.insert_spiel = lambda data: True
_fake_db.update_karte_guthaben = lambda *a, **k: True
_fake_db.insert_abrechnung = lambda data: True
_fake_db.set_spiele_abgerechnet_fuer_karte = lambda karte_id: True
_fake_db.set_karte_inaktiv = lambda karte_id: True
sys.modules.setdefault("database", _fake_db)

import calculations as calc  # noqa: E402  (Import bewusst nach dem Fake-Setup)
import config as cfg  # noqa: E402


# ---------------------------------------------------------------------------
# Abrechnung: Rundung muss exakt dem bezahlten Betrag der Karte entsprechen
# ---------------------------------------------------------------------------

def test_abrechnung_logik_summe_stimmt_exakt(monkeypatch):
    spiele = [
        {"spieler": "Anna", "einheiten": 7, "kosten": 30.0, "abgerechnet": False},
        {"spieler": "Ben", "einheiten": 3, "kosten": 12.5, "abgerechnet": False},
        {"spieler": "Clara", "einheiten": 5, "kosten": 20.0, "abgerechnet": False},
    ]
    inserted = []

    monkeypatch.setattr(calc.db, "get_offene_spiele_fuer_karte", lambda karte_id: spiele)
    monkeypatch.setattr(calc.db, "insert_abrechnung", lambda data: inserted.append(data) or True)
    monkeypatch.setattr(calc.db, "set_spiele_abgerechnet_fuer_karte", lambda karte_id: True)
    monkeypatch.setattr(calc.db, "set_karte_inaktiv", lambda karte_id: True)

    karte = {"id": 1, "bezahlt_von": "Anna", "bezahlt_betrag": 200.0}
    calc.abrechnung_logik(karte)

    total = sum(e["betrag"] for e in inserted)
    assert len(inserted) == 3
    assert total == pytest.approx(karte["bezahlt_betrag"], abs=1e-9)


def test_abrechnung_logik_verwendet_bezahlten_betrag_nicht_fixen_wert(monkeypatch):
    """Bei einer vergünstigten Karte muss der TATSÄCHLICH bezahlte Betrag
    verteilt werden, nicht ein globaler Standardwert."""
    spiele = [
        {"spieler": "Anna", "einheiten": 1, "kosten": 10.0, "abgerechnet": False},
        {"spieler": "Clara", "einheiten": 1, "kosten": 10.0, "abgerechnet": False},
    ]
    inserted = []
    monkeypatch.setattr(calc.db, "get_offene_spiele_fuer_karte", lambda karte_id: spiele)
    monkeypatch.setattr(calc.db, "insert_abrechnung", lambda data: inserted.append(data) or True)
    monkeypatch.setattr(calc.db, "set_spiele_abgerechnet_fuer_karte", lambda karte_id: True)
    monkeypatch.setattr(calc.db, "set_karte_inaktiv", lambda karte_id: True)

    karte = {"id": 2, "bezahlt_von": "Anna", "bezahlt_betrag": 150.0}
    calc.abrechnung_logik(karte)

    total = sum(e["betrag"] for e in inserted)
    assert total == pytest.approx(150.0, abs=1e-9)


def test_abrechnung_logik_keine_spiele_macht_nichts(monkeypatch):
    calls = {"abgerechnet": False, "inaktiv": False}
    monkeypatch.setattr(calc.db, "get_offene_spiele_fuer_karte", lambda karte_id: [])
    monkeypatch.setattr(calc.db, "set_spiele_abgerechnet_fuer_karte", lambda karte_id: calls.__setitem__("abgerechnet", True))
    monkeypatch.setattr(calc.db, "set_karte_inaktiv", lambda karte_id: calls.__setitem__("inaktiv", True))

    calc.abrechnung_logik({"id": 1, "bezahlt_von": "Anna", "bezahlt_betrag": 200.0})

    assert calls == {"abgerechnet": False, "inaktiv": False}


def test_abrechnung_logik_ignoriert_fremde_karten(monkeypatch):
    """abrechnung_logik darf nur Spiele der EIGENEN Karte einbeziehen, keine
    Überschuss-Zeilen (karte_id=None) oder Spiele einer anderen Karte -
    genau das war der Kern des Doppelverrechnungs-Problems."""
    aufrufe = []
    monkeypatch.setattr(calc.db, "get_offene_spiele_fuer_karte", lambda karte_id: aufrufe.append(karte_id) or [
        {"spieler": "Anna", "einheiten": 2, "kosten": 20.0, "abgerechnet": False, "karte_id": karte_id},
    ])
    monkeypatch.setattr(calc.db, "insert_abrechnung", lambda data: True)
    monkeypatch.setattr(calc.db, "set_spiele_abgerechnet_fuer_karte", lambda karte_id: True)
    monkeypatch.setattr(calc.db, "set_karte_inaktiv", lambda karte_id: True)

    calc.abrechnung_logik({"id": 7, "bezahlt_von": "Anna", "bezahlt_betrag": 200.0})

    assert aufrufe == [7]  # wurde exakt für Karte 7 angefragt, nichts global


# ---------------------------------------------------------------------------
# Speichern-Logik: Erfolgsfall + Optimistic-Locking-Konflikt + zeitabhängige
# Preisliste. WICHTIG: Der Kartenfaktor (Vergünstigung) darf die
# Guthaben-Abbuchung NICHT beeinflussen (siehe speichern_logik-Docstring) -
# er zählt nur in der finalen Abrechnung (abrechnung_logik).
# ---------------------------------------------------------------------------

MONTAG = date(2026, 8, 3)      # Wochentag, Hauptzeit-Fenster
SAMSTAG = date(2026, 8, 1)     # Wochenende


def test_speichern_logik_ignoriert_kartenfaktor_bei_der_abbuchung(monkeypatch):
    """Regressionstest für den Kartenabgleich: 4 Einheiten Montag 11 Uhr
    (19 €/Einheit) müssen exakt 76 € abbuchen, egal welcher Rabattfaktor auf
    der Karte hinterlegt ist."""
    karte = {"id": 1, "guthaben": 240.0, "faktor": 200 / 240}
    updates, inserts = [], []

    monkeypatch.setattr(calc.db, "get_karte", lambda: karte)
    monkeypatch.setattr(calc.db, "update_karte_guthaben", lambda kid, alt, neu: updates.append((kid, alt, neu)) or True)
    monkeypatch.setattr(calc.db, "insert_spiel", lambda data: inserts.append(data) or True)

    status, msg = calc.speichern_logik(["Anna", "Clara", "Ben", "David"], 4, "Anna", MONTAG, time(11, 0))

    assert status == "success"
    abzug = updates[0][1] - updates[0][2]
    assert abzug == pytest.approx(76.0, abs=1e-9)


def test_speichern_logik_speichert_karte_id_mit(monkeypatch):
    """Jede Session bekommt die id der aktuell aktiven Karte mit auf den Weg -
    Grundlage für die spätere Kartenreaktivierung nach einer versehentlichen
    automatischen Abrechnung."""
    karte = {"id": 42, "guthaben": 100.0}
    inserts = []
    monkeypatch.setattr(calc.db, "get_karte", lambda: karte)
    monkeypatch.setattr(calc.db, "update_karte_guthaben", lambda *a, **k: True)
    monkeypatch.setattr(calc.db, "insert_spiel", lambda data: inserts.append(data) or True)

    status, msg = calc.speichern_logik(["Anna", "Clara"], 2, "Anna", MONTAG, time(9, 0))

    assert status == "success"
    assert all(row["karte_id"] == 42 for row in inserts)


def test_speichern_logik_nutzt_preisliste_hauptzeit(monkeypatch):
    karte = {"id": 1, "guthaben": 100.0, "faktor": 0.5}
    updates, inserts = [], []

    monkeypatch.setattr(calc.db, "get_karte", lambda: karte)
    monkeypatch.setattr(calc.db, "update_karte_guthaben", lambda kid, alt, neu: updates.append((kid, alt, neu)) or True)
    monkeypatch.setattr(calc.db, "insert_spiel", lambda data: inserts.append(data) or True)

    # Montag 18:00 -> Hauptzeit-Tarif 21 €/Einheit lt. Preisliste
    status, msg = calc.speichern_logik(["Anna", "Clara"], 2, "Anna", MONTAG, time(18, 0))

    assert status == "success"
    assert len(inserts) == 2
    assert len(updates) == 1
    # 2 Einheiten * 21€ (Preisliste Montag 18 Uhr), Faktor bleibt unberücksichtigt
    erwartete_kosten = round(2 * 21.0, 2)
    assert updates[0][1] - updates[0][2] == pytest.approx(erwartete_kosten, abs=1e-9)
    assert inserts[0]["gespielt_uhrzeit"] == "18:00:00"


def test_speichern_logik_wochenend_tarif(monkeypatch):
    karte = {"id": 1, "guthaben": 100.0, "faktor": 1.0}
    updates = []
    monkeypatch.setattr(calc.db, "get_karte", lambda: karte)
    monkeypatch.setattr(calc.db, "update_karte_guthaben", lambda kid, alt, neu: updates.append((kid, alt, neu)) or True)
    monkeypatch.setattr(calc.db, "insert_spiel", lambda data: True)

    # Samstag 09:00 -> Wochenend-Frühtarif 17 €/Einheit
    status, msg = calc.speichern_logik(["Anna"], 1, "Anna", SAMSTAG, time(9, 0))

    assert status == "success"
    assert updates[0][1] - updates[0][2] == pytest.approx(17.0, abs=1e-9)


def test_speichern_logik_ermaessigter_tarif(monkeypatch):
    """Regressionstest für den Kartenabgleich vom 11.08.: Montag 16:45 Uhr
    muss mit ermaessigt=True 19 € statt 21 € kosten."""
    karte = {"id": 1, "guthaben": 100.0, "faktor": 1.0}
    updates, inserts = [], []
    monkeypatch.setattr(calc.db, "get_karte", lambda: karte)
    monkeypatch.setattr(calc.db, "update_karte_guthaben", lambda kid, alt, neu: updates.append((kid, alt, neu)) or True)
    monkeypatch.setattr(calc.db, "insert_spiel", lambda data: inserts.append(data) or True)

    status, msg = calc.speichern_logik(["Anna", "Clara"], 2, "Anna", MONTAG, time(16, 45), ermaessigt=True)

    assert status == "success"
    assert updates[0][1] - updates[0][2] == pytest.approx(2 * 19.00, abs=1e-9)
    assert inserts[0]["ermaessigt"] is True


def test_speichern_logik_funktioniert_auch_ohne_faktor_feld_auf_der_karte(monkeypatch):
    """Die Karte braucht für's Speichern kein 'faktor'-Feld mehr, da der
    Faktor hier gar nicht mehr gelesen wird (nur noch in abrechnung_logik)."""
    karte = {"id": 1, "guthaben": 100.0}  # kein "faktor"-Schlüssel
    updates = []
    monkeypatch.setattr(calc.db, "get_karte", lambda: karte)
    monkeypatch.setattr(calc.db, "update_karte_guthaben", lambda kid, alt, neu: updates.append((kid, alt, neu)) or True)
    monkeypatch.setattr(calc.db, "insert_spiel", lambda data: True)

    status, msg = calc.speichern_logik(["Anna"], 1, "Anna", MONTAG, time(9, 0))

    assert status == "success"
    # Montag 09:00 -> 19€/Einheit lt. Preisliste
    assert updates[0][1] - updates[0][2] == pytest.approx(19.0, abs=1e-9)


def test_speichern_logik_konflikt_wird_wiederholt(monkeypatch):
    karte = {"id": 1, "guthaben": 100.0, "faktor": 1.0}
    versuche = {"count": 0}

    def fake_update(karte_id, alt, neu):
        versuche["count"] += 1
        return versuche["count"] > 1  # 1. Versuch: Konflikt, 2. Versuch: klappt

    monkeypatch.setattr(calc.db, "get_karte", lambda: karte)
    monkeypatch.setattr(calc.db, "update_karte_guthaben", fake_update)
    monkeypatch.setattr(calc.db, "insert_spiel", lambda data: True)

    status, msg = calc.speichern_logik(["Anna"], 1, "Anna", MONTAG, time(9, 0))

    assert status == "success"
    assert versuche["count"] == 2


def test_speichern_logik_keine_karte(monkeypatch):
    monkeypatch.setattr(calc.db, "get_karte", lambda: None)
    status, msg = calc.speichern_logik(["Anna"], 1, "Anna", MONTAG, time(9, 0))
    assert status == "error"


# ---------------------------------------------------------------------------
# Überschuss-Splitting: reicht das Guthaben nicht für die volle Session,
# wird sie zwischen der alten Karte (gedeckter Teil) und einem noch
# "herrenlosen" Überschuss (karte_id=None, für die nächste Karte) aufgeteilt.
# ---------------------------------------------------------------------------

def test_speichern_logik_teilt_session_bei_ueberschuss_auf(monkeypatch):
    """Exakter Regressionstest für den Nutzer-Fall: 15 € Restguthaben,
    38 € Session (4 Spieler, 19 €/Einheit ermäßigt) -> 15 € gedeckt (auf der
    alten Karte, wird abgerechnet), 23 € Überschuss (noch keiner Karte
    zugeordnet), exakt gleichmäßig auf alle 4 Spieler verteilt."""
    karte = {"id": 1, "guthaben": 15.0, "bezahlt_betrag": 200.0}
    updates, inserts, abrechnungen = [], [], []

    monkeypatch.setattr(calc.db, "get_karte", lambda: karte)
    monkeypatch.setattr(calc.db, "update_karte_guthaben", lambda kid, alt, neu: updates.append((kid, alt, neu)) or True)
    monkeypatch.setattr(calc.db, "insert_spiel", lambda data: inserts.append(data) or True)
    monkeypatch.setattr(calc.db, "get_offene_spiele_fuer_karte", lambda karte_id: [
        r for r in inserts if r["karte_id"] == karte_id and not r["abgerechnet"]
    ])
    monkeypatch.setattr(calc.db, "insert_abrechnung", lambda data: abrechnungen.append(data) or True)
    monkeypatch.setattr(calc.db, "set_spiele_abgerechnet_fuer_karte", lambda karte_id: True)
    monkeypatch.setattr(calc.db, "set_karte_inaktiv", lambda karte_id: True)

    status, msg = calc.speichern_logik(
        ["Emma", "Clara", "David", "Anna"], 2, "Anna", MONTAG, time(16, 45), ermaessigt=True
    )

    assert status == "warning"

    # Guthaben der alten Karte: nur die gedeckten 15 €, nicht die vollen 38 €
    abzug = updates[0][1] - updates[0][2]
    assert abzug == pytest.approx(15.0, abs=1e-9)

    gedeckt_zeilen = [r for r in inserts if r["karte_id"] == 1]
    ueberschuss_zeilen = [r for r in inserts if r["karte_id"] is None]

    assert len(gedeckt_zeilen) == 4
    assert sum(r["kosten"] for r in gedeckt_zeilen) == pytest.approx(15.0, abs=1e-9)

    assert len(ueberschuss_zeilen) == 4
    assert sum(r["kosten"] for r in ueberschuss_zeilen) == pytest.approx(23.0, abs=1e-9)
    assert all(r["einheiten"] == 0 for r in ueberschuss_zeilen)
    assert all(r["abgerechnet"] is False for r in ueberschuss_zeilen)

    # Abrechnung der alten Karte verteilt weiterhin den vollen bezahlt_betrag
    # (200 €) proportional zur Nutzung dieser Karte - hier war die Nutzung
    # ausschließlich die gedeckten 15 €, also gleichmäßig auf die 4 Spieler.
    # Wichtig ist NUR: die Überschuss-Zeilen (23 €) sind NICHT Teil dieser
    # Verteilung (siehe get_offene_spiele_fuer_karte-Mock oben, der nur die
    # karte_id=1-Zeilen liefert) - keine Doppelverrechnung.
    assert sum(a["betrag"] for a in abrechnungen) == pytest.approx(200.0, abs=1e-9)


def test_speichern_logik_ohne_ueberschuss_erzeugt_keine_karte_id_none_zeilen(monkeypatch):
    """Passt das Guthaben normal, dürfen KEINE Überschuss-Zeilen entstehen."""
    karte = {"id": 5, "guthaben": 100.0}
    inserts = []
    monkeypatch.setattr(calc.db, "get_karte", lambda: karte)
    monkeypatch.setattr(calc.db, "update_karte_guthaben", lambda *a, **k: True)
    monkeypatch.setattr(calc.db, "insert_spiel", lambda data: inserts.append(data) or True)

    status, msg = calc.speichern_logik(["Anna", "Clara"], 2, "Anna", MONTAG, time(9, 0))

    assert status == "success"
    assert all(r["karte_id"] == 5 for r in inserts)
    assert not any(r["karte_id"] is None for r in inserts)


# ---------------------------------------------------------------------------
# Statistik-Funktionen
# ---------------------------------------------------------------------------

def test_player_stats_basic():
    df = pd.DataFrame([
        {"gewinner": "Anna", "verlierer": "Clara"},
        {"gewinner": "Clara", "verlierer": "Anna"},
        {"gewinner": "Anna", "verlierer": "Ben"},
    ])
    stats = calc.player_stats(df, "Anna")
    assert stats["siege"] == 2
    assert stats["niederlagen"] == 1
    assert stats["gesamt"] == 3
    assert stats["quote"] == pytest.approx(66.7, abs=0.1)


def test_head_to_head_matrix():
    df = pd.DataFrame([
        {"gewinner": "Anna", "verlierer": "Clara"},
        {"gewinner": "Anna", "verlierer": "Clara"},
        {"gewinner": "Clara", "verlierer": "Anna"},
    ])
    alle_spieler = ["Anna", "Ben", "Clara", "David"]
    matrix = calc.head_to_head_matrix(df, alle_spieler)
    assert matrix.loc["Clara", "Anna"] == 2  # Spalte Anna, Zeile Clara: Anna gewann 2x gegen Clara
    assert matrix.loc["Anna", "Clara"] == 1


def test_filter_matchups():
    df = pd.DataFrame([
        {"gewinner": "Anna", "verlierer": "Clara"},
        {"gewinner": "Ben", "verlierer": "Anna"},
    ])
    alle_spieler = ["Anna", "Ben", "Clara", "David"]
    matchups = calc.filter_matchups(df, "Anna", alle_spieler)
    assert set(matchups.keys()) == {"Clara", "Ben"}
    assert "David" not in matchups
