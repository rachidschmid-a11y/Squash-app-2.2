import pandas as pd
from datetime import datetime, time as dtime, timezone
import database as db
import config as cfg
import zeit_utils
import preisliste

def _parse_uhrzeit(wert):
    teile = str(wert).split(":")
    return dtime(int(teile[0]), int(teile[1]))

def format_dataframe(df):
    df_clean = df.copy()
    if "gespielt_uhrzeit" in df_clean.columns and "gespielt_am" in df_clean.columns:
        daten_geparst = pd.to_datetime(df_clean["gespielt_am"])
        df_clean["gespielt_uhrzeit"] = [
            preisliste.zeitraum_label(datum.date(), _parse_uhrzeit(uhrzeit)) if uhrzeit else ""
            for datum, uhrzeit in zip(daten_geparst, df_clean["gespielt_uhrzeit"])
        ]
    elif "gespielt_uhrzeit" in df_clean.columns:
        df_clean["gespielt_uhrzeit"] = df_clean["gespielt_uhrzeit"].apply(
            lambda x: str(x)[:5] if x else ""
        )
    if "gespielt_am" in df_clean.columns:
        df_clean["gespielt_am"] = pd.to_datetime(df_clean["gespielt_am"]).dt.strftime('%d.%m.%Y')
    if "eingetragen_am" in df_clean.columns:
        df_clean["eingetragen_am"] = zeit_utils.to_berlin_time_str(df_clean["eingetragen_am"])
    cols = [c for c in cfg.ORDERED_COLUMNS if c in df_clean.columns]
    return df_clean[cols]

def speichern_logik(spieler, einheiten, eingetragen_von, gespielt_am, uhrzeit, ermaessigt=False, max_retries=3):
    """
    Speichert eine neue Spiel-Session und zieht die Kosten vom Kartenguthaben ab.

    Der Preis pro Einheit richtet sich nach der Preisliste des Betreibers
    (siehe preisliste.py), abhängig von Wochentag/Feiertag, der
    Start-Uhrzeit der Session und ob der ermäßigte Schüler-/Studenten-Tarif
    gilt (nur an Wochentagen verfügbar).

    WICHTIG: Der individuelle Rabatt-Faktor der Karte (Vergünstigung) wird
    HIER NICHT angewendet. Laut Abgleich mit den echten Kartenbuchungen des
    Betreibers zieht dieser das Guthaben zum vollen Listenpreis ab - der
    Rabatt wirkt sich nur beim Aufladen der Karte aus (z.B. 200 € bezahlt
    für 240 € Guthaben) bzw. in der finalen Abrechnung (siehe
    abrechnung_logik), wo der tatsächlich bezahlte Betrag verteilt wird.

    Gibt ein Tupel (status, nachricht) zurück, wobei status einer von
    "success", "warning" oder "error" ist:
      - "success": alles hat geklappt, Karte hat noch Guthaben
      - "warning": alles hat geklappt, aber die Karte wurde dabei automatisch
                    abgerechnet, weil das Guthaben aufgebraucht ist
      - "error":   es ist etwas schiefgegangen, es wurde nichts (inkonsistent)
                    gespeichert
    """
    for _ in range(max_retries):
        karte = db.get_karte()
        if karte is None:
            return "error", "Keine aktive Karte vorhanden"

        alter_guthaben = karte["guthaben"]
        preis_pro_einheit = preisliste.ermittle_preis(gespielt_am, uhrzeit, ermaessigt)
        kosten_fuer_spiel = round(einheiten * preis_pro_einheit, 2)
        muss_abgerechnet_werden = alter_guthaben < kosten_fuer_spiel
        kosten_pro_person = round(kosten_fuer_spiel / len(spieler), 2)
        neues_guthaben = round(alter_guthaben - kosten_fuer_spiel, 2)

        # Guthaben zuerst per Optimistic Locking reservieren. Schlägt das fehl,
        # hat zwischenzeitlich jemand anderes das Guthaben geändert -> Karte
        # neu laden und erneut versuchen, statt mit veralteten Daten weiterzurechnen.
        guthaben_aktualisiert = db.update_karte_guthaben(karte["id"], alter_guthaben, neues_guthaben)
        if not guthaben_aktualisiert:
            continue

        alle_gespeichert = True
        for person in spieler:
            erfolg = db.insert_spiel({
                "spieler": person,
                "einheiten": einheiten,
                "kosten": kosten_pro_person,
                "eingetragen_von": eingetragen_von,
                "eingetragen_am": datetime.now(timezone.utc).isoformat(),
                "gespielt_am": gespielt_am.isoformat(),
                "gespielt_uhrzeit": uhrzeit.isoformat(),
                "ermaessigt": ermaessigt,
                "abgerechnet": False
            })
            if not erfolg:
                alle_gespeichert = False
                break

        if not alle_gespeichert:
            # Best-effort Rollback: Guthaben-Abzug rückgängig machen, damit die
            # Karte nicht "unsichtbar" belastet wird, obwohl nicht alle
            # Spieler-Zeilen gespeichert werden konnten.
            db.update_karte_guthaben(karte["id"], neues_guthaben, alter_guthaben)
            return "error", "❌ Fehler beim Speichern der Spiel-Session. Guthaben wurde nicht verändert."

        if muss_abgerechnet_werden:
            abrechnung_logik(karte)
            return "warning", "⚠️ Guthaben aufgebraucht! Das Spiel wird noch verbucht, danach wird die Karte automatisch abgerechnet."

        return "success", "Erfolgreich verarbeitet!"

    return "error", "⚠️ Es gab mehrfach gleichzeitige Änderungen am Guthaben. Bitte versuche es gleich noch einmal."

def abrechnung_logik(karte):
    daten = db.get_spiele()
    if len(daten) == 0:
        return

    df = pd.DataFrame(daten)

    if cfg.ABRECHNUNG_BASIS == "kosten":
        # Aufteilung nach tatsächlich angefallenen Kosten pro Spieler
        # (berücksichtigt automatisch, dass Sessions mit mehr Mitspielern
        # pro Kopf günstiger waren)
        summen = df.groupby("spieler")["kosten"].sum()
    else:
        # Alte Logik: Aufteilung nach Summe der gespielten Einheiten,
        # unabhängig von der Gruppengröße der jeweiligen Session
        summen = df.groupby("spieler")["einheiten"].sum()

    gesamt = summen.sum()
    if gesamt == 0:
        return

    bezahlt_betrag = karte.get("bezahlt_betrag")
    if bezahlt_betrag is None:
        # Absicherung für sehr alte Karten ohne "bezahlt_betrag"-Spalte
        bezahlt_betrag = cfg.STANDARD_BEZAHLT_BETRAG

    # Anteile berechnen und per "größtem Rest"-Verfahren auf ganze Cent runden,
    # damit die Summe aller Schulden exakt dem bezahlten Betrag entspricht
    # (keine Cent-Abweichungen durch unabhängiges Runden je Spieler).
    zielbetrag_cents = round(bezahlt_betrag * 100)
    rohbetraege_cents = (summen / gesamt) * zielbetrag_cents
    abgerundete_cents = rohbetraege_cents.apply(lambda x: int(x + 1e-9))

    rest_cents = int(zielbetrag_cents - abgerundete_cents.sum())
    nachkomma_resten = (rohbetraege_cents - abgerundete_cents).sort_values(ascending=False)
    aufrundungs_kandidaten = list(nachkomma_resten.index[:rest_cents])

    for name in summen.index:
        cents = abgerundete_cents[name] + (1 if name in aufrundungs_kandidaten else 0)
        schulden = round(cents / 100, 2)

        db.insert_abrechnung({
            "spieler": name,
            "betrag": float(schulden),
            "karte_id": karte["id"]
        })

    db.set_spiele_abgerechnet()
    db.set_karte_inaktiv(karte["id"])

def build_dataframe():
    data = db.get_spielergebnisse()
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)

def filter_matchups(df, spieler, alle_spieler):
    gegner_liste = [s for s in alle_spieler if s != spieler]
    matchups = {}
    for g in gegner_liste:
        daten = df[
            ((df["gewinner"] == spieler) & (df["verlierer"] == g)) |
            ((df["gewinner"] == g) & (df["verlierer"] == spieler))
        ].copy()
        if len(daten) > 0:
            matchups[g] = daten
    return matchups

def player_stats(df, spieler):
    spiele = df[(df["gewinner"] == spieler) | (df["verlierer"] == spieler)]
    siege = len(spiele[spiele["gewinner"] == spieler])
    niederlagen = len(spiele[spiele["verlierer"] == spieler])
    gesamt = siege + niederlagen
    quote = (siege / gesamt * 100) if gesamt > 0 else 0
    return {
        "siege": siege,
        "niederlagen": niederlagen,
        "gesamt": gesamt,
        "quote": round(quote, 1)
    }

def head_to_head_matrix(df, alle_spieler):
    matrix = {}
    for p1 in alle_spieler:
        matrix[p1] = {}
        for p2 in alle_spieler:
            if p1 == p2:
                matrix[p1][p2] = None
                continue
            matches = df[(df["gewinner"] == p1) & (df["verlierer"] == p2)]
            matrix[p1][p2] = len(matches)
    return pd.DataFrame(matrix).fillna(0)
