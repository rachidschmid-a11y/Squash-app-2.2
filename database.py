import streamlit as st
from supabase import create_client

_client = None

def _get_client():
    """
    Erstellt den Supabase-Client beim ersten echten Zugriff (lazy) und
    cached ihn danach. Vorteil gegenüber einer Erstellung direkt beim
    Modul-Import: database.py lässt sich so auch importieren/testen, ohne
    dass sofort gültige st.secrets vorhanden sein müssen - der Fehler tritt
    erst beim tatsächlichen Datenbankzugriff auf und wird dort von den
    einzelnen try/except-Blöcken sauber abgefangen.
    """
    global _client
    if _client is None:
        _client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    return _client

# --- FINANZ-QUERIES (ex app.py) ---

def get_karte():
    try:
        result = _get_client().table("karte").select("*").eq("aktiv", True).execute()
        return result.data[0] if len(result.data) > 0 else None
    except Exception as e:
        st.error(f"Fehler beim Laden der Karte: {e}")
        return None

def get_letzte_inaktive_karte():
    try:
        result = _get_client().table("karte").select("*").eq("aktiv", False).order("id", desc=True).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Fehler beim Laden der letzten Karte: {e}")
        return None

def get_inaktive_karten(limit: int = 5):
    """Die letzten N deaktivierten (abgeschlossenen) Karten - für die
    'Karte reaktivieren'-Funktion, falls versehentlich zu früh/falsch
    abgerechnet wurde."""
    try:
        result = _get_client().table("karte").select("*").eq("aktiv", False).order("id", desc=True).limit(limit).execute()
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der letzten Karten: {e}")
        return []

def set_karte_aktiv(karte_id, aktiv: bool) -> bool:
    """Setzt den aktiv-Status einer Karte (True oder False) - generische
    Version von set_karte_inaktiv, u.a. für die Reaktivierung genutzt."""
    try:
        _get_client().table("karte").update({"aktiv": aktiv}).eq("id", karte_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Ändern des Kartenstatus: {e}")
        return False

def delete_abrechnung_fuer_karte(karte_id) -> bool:
    """Löscht alle Abrechnungs-Zeilen einer Karte - wird beim Reaktivieren
    einer versehentlich abgerechneten Karte gebraucht, weil die (verfrühte)
    Abrechnung damit hinfällig wird."""
    try:
        _get_client().table("abrechnung").delete().eq("karte_id", karte_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Löschen der Abrechnung: {e}")
        return False

def reaktiviere_spiele_fuer_karte(karte_id) -> bool:
    """Setzt abgerechnet=False für alle Spiele, die während der Laufzeit
    dieser Karte eingetragen wurden (karte_id) und aktuell als abgerechnet
    markiert sind - macht sie in der normalen Spiele-Übersicht wieder
    sichtbar und bearbeitbar."""
    try:
        (
            _get_client()
            .table("spiele")
            .update({"abgerechnet": False})
            .eq("karte_id", karte_id)
            .eq("abgerechnet", True)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Fehler beim Zurücksetzen der Spiele: {e}")
        return False

def get_spiele_fuer_karte(karte_id):
    """Alle Spiele, die während der Laufzeit einer bestimmten Karte
    eingetragen wurden (karte_id) - unabhängig vom abgerechnet-Status. Für
    den CSV-Export der Abrechnungs-Historie: zeigt genau die Einzel-Sessions,
    aus denen sich die Verteilung der letzten Abrechnung zusammensetzt."""
    try:
        result = _get_client().table("spiele").select("*").eq("karte_id", karte_id).order("id").execute()
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der Spiele dieser Karte: {e}")
        return []

def get_offene_spiele_fuer_karte(karte_id):
    """Wie get_spiele_fuer_karte, aber nur die noch NICHT abgerechneten
    Zeilen - das ist genau die Grundlage für die Abrechnung EINER Karte
    (abrechnung_logik), damit dabei keine 'herrenlosen' Überschuss-Zeilen
    (karte_id = NULL) einer anderen/zukünftigen Karte versehentlich
    mitgezählt werden."""
    try:
        result = (
            _get_client()
            .table("spiele")
            .select("*")
            .eq("karte_id", karte_id)
            .eq("abgerechnet", False)
            .execute()
        )
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der offenen Spiele dieser Karte: {e}")
        return []

def set_spiele_abgerechnet_fuer_karte(karte_id) -> bool:
    """Markiert nur die Spiele EINER bestimmten Karte als abgerechnet -
    bewusst nicht global, damit noch nicht zugeordnete Überschuss-Zeilen
    (karte_id = NULL) unangetastet bleiben."""
    try:
        (
            _get_client()
            .table("spiele")
            .update({"abgerechnet": True})
            .eq("karte_id", karte_id)
            .eq("abgerechnet", False)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Fehler beim Markieren der Spiele als abgerechnet: {e}")
        return False

def get_offene_ueberschuss_spiele():
    """Spiele-Zeilen, die entstanden sind, weil eine Session das Guthaben
    der damaligen Karte überschritten hat (oder weil eine Karte storniert
    wurde, während noch offene Spiele daran hingen) - noch keiner Karte
    zugeordnet (karte_id IS NULL) und noch nicht abgerechnet. Werden beim
    nächsten 'Karte aktivieren' automatisch übernommen."""
    try:
        result = (
            _get_client()
            .table("spiele")
            .select("*")
            .is_("karte_id", "null")
            .eq("abgerechnet", False)
            .order("id")
            .execute()
        )
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der offenen Überschuss-Spiele: {e}")
        return []

def claim_offene_ueberschuss_spiele(karte_id) -> bool:
    """Ordnet alle noch nicht zugeordneten Überschuss-Spiele (karte_id IS
    NULL) einer neu aktivierten Karte zu. Wird direkt beim Aktivieren einer
    neuen Karte aufgerufen."""
    try:
        (
            _get_client()
            .table("spiele")
            .update({"karte_id": karte_id})
            .is_("karte_id", "null")
            .eq("abgerechnet", False)
            .execute()
        )
        return True
    except Exception as e:
        st.error(f"Fehler beim Zuordnen der Überschuss-Spiele: {e}")
        return False

def get_alle_spiele(limit: int = 50):
    """Die letzten N Spiele UNABHÄNGIG vom abgerechnet-Status - für die
    Ansicht 'auch bereits abgerechnete Einträge anzeigen', z.B. um einen
    Fehleintrag zu finden, der durch eine automatische Abrechnung schon aus
    der normalen Übersicht verschwunden ist."""
    try:
        result = _get_client().table("spiele").select("*").order("id", desc=True).limit(limit).execute()
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden aller Spiele: {e}")
        return []

def get_spiele():
    try:
        result = _get_client().table("spiele").select("*").eq("abgerechnet", False).order("id", desc=True).execute()
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der Spiele: {e}")
        return []

def get_letzte_abrechnung():
    try:
        last_card = get_letzte_inaktive_karte()
        if not last_card:
            return [], "Unbekannt"

        payer = last_card.get("bezahlt_von", "dem Zahler")
        result = _get_client().table("abrechnung").select("*").eq("karte_id", last_card["id"]).execute()
        return result.data or [], payer
    except Exception as e:
        st.error(f"Fehler beim Laden der letzten Abrechnung: {e}")
        return [], "Unbekannt"

def insert_spiel(data: dict) -> bool:
    try:
        _get_client().table("spiele").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern des Spiels: {e}")
        return False

def update_karte_guthaben(karte_id, alter_guthaben, neues_guthaben) -> bool:
    """
    Aktualisiert das Guthaben einer Karte.

    Nutzt Optimistic Locking: Das Update wird nur ausgeführt, wenn das
    Guthaben in der Datenbank noch exakt dem zuvor ausgelesenen Wert
    (`alter_guthaben`) entspricht. So wird verhindert, dass zwei gleichzeitige
    Sessions (z.B. von zwei Handys aus) sich gegenseitig überschreiben, ohne
    dass eine der beiden Änderungen "verloren geht".

    Gibt True zurück, wenn das Update erfolgreich war, False wenn
    zwischenzeitlich jemand anderes das Guthaben geändert hat (oder ein
    Fehler aufgetreten ist) - dann sollte die aufrufende Stelle die Karte
    neu laden und es erneut versuchen.
    """
    try:
        result = (
            _get_client()
            .table("karte")
            .update({"guthaben": round(neues_guthaben, 2)})
            .eq("id", karte_id)
            .eq("guthaben", round(alter_guthaben, 2))
            .execute()
        )
        return len(result.data) > 0
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren des Guthabens: {e}")
        return False

def insert_abrechnung(data: dict) -> bool:
    try:
        _get_client().table("abrechnung").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern der Abrechnung: {e}")
        return False

def set_spiele_abgerechnet() -> bool:
    try:
        _get_client().table("spiele").update({"abgerechnet": True}).eq("abgerechnet", False).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Markieren der Spiele als abgerechnet: {e}")
        return False

def set_karte_inaktiv(karte_id) -> bool:
    try:
        _get_client().table("karte").update({"aktiv": False}).eq("id", karte_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Deaktivieren der Karte: {e}")
        return False

def insert_karte(data: dict) -> bool:
    try:
        _get_client().table("karte").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Anlegen der Karte: {e}")
        return False

def delete_spiel_by_id(spiel_id) -> bool:
    try:
        _get_client().table("spiele").delete().eq("id", spiel_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Löschen des Spiels: {e}")
        return False

def update_karte_zahler(karte_id, neuer_zahler) -> bool:
    """Aktualisiert den Zahler einer bestehenden Karte im Falle eines Tippfehlers."""
    try:
        _get_client().table("karte").update({"bezahlt_von": neuer_zahler}).eq("id", karte_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren des Zahlers in der Datenbank: {e}")
        return False

def delete_karte(karte_id) -> bool:
    """Löscht eine aktive Karte vollständig aus der Datenbank (Storno)."""
    try:
        _get_client().table("karte").delete().eq("id", karte_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Löschen der Karte in der Datenbank: {e}")
        return False

# --- SPIELER-VERWALTUNG ---

def get_spieler():
    """Alle Spieler (aktiv + inaktiv) mit id/name/aktiv - für die Verwaltungsseite."""
    try:
        result = _get_client().table("spieler").select("*").order("name").execute()
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der Spieler: {e}")
        return []

def get_aktive_spieler_namen():
    """Namen aller aktiven Spieler - für Auswahlfelder bei neuen Einträgen."""
    try:
        result = _get_client().table("spieler").select("name").eq("aktiv", True).order("name").execute()
        return [row["name"] for row in (result.data or [])]
    except Exception as e:
        st.error(f"Fehler beim Laden der aktiven Spieler: {e}")
        return []

def get_alle_spieler_namen():
    """Namen aller Spieler (aktiv + inaktiv) - für Statistik-Ansichten, damit
    historische Daten von ausgeschiedenen Spielern nicht verschwinden."""
    try:
        result = _get_client().table("spieler").select("name").order("name").execute()
        return [row["name"] for row in (result.data or [])]
    except Exception as e:
        st.error(f"Fehler beim Laden der Spieler: {e}")
        return []

def insert_spieler(name: str) -> bool:
    try:
        _get_client().table("spieler").insert({"name": name, "aktiv": True}).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Anlegen des Spielers: {e}")
        return False

def set_spieler_aktiv(spieler_id, aktiv: bool) -> bool:
    try:
        _get_client().table("spieler").update({"aktiv": aktiv}).eq("id", spieler_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren des Spielers: {e}")
        return False

def delete_spieler(spieler_id) -> bool:
    """Löscht einen Spieler endgültig aus der Spielerliste (z.B. bei einem
    Tippfehler). Bereits gespeicherte Spiele/Ergebnisse mit diesem Namen
    bleiben in der Datenbank erhalten, da sie den Namen nur als Text und
    nicht als Fremdschlüssel referenzieren."""
    try:
        _get_client().table("spieler").delete().eq("id", spieler_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Löschen des Spielers: {e}")
        return False

# --- SPORT-QUERIES (ex Auswertung.py) ---

def get_spielergebnisse():
    try:
        result = _get_client().table("spielergebnisse").select("*").order("gespielt_am", desc=True).execute()
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der Spielergebnisse: {e}")
        return []

def save_spielergebnis(data: dict) -> bool:
    try:
        _get_client().table("spielergebnisse").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern des Spielergebnisses in Supabase: {e}")
        return False

def delete_spielergebnis(result_id: int) -> bool:
    try:
        _get_client().table("spielergebnisse").delete().eq("id", result_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Löschen: {e}")
        return False
