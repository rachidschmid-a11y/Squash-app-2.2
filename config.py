# Finanz-Parameter für Abrechnungslogik.
# Der Preis pro Einheit kommt jetzt aus preisliste.py (zeit-/tagabhängig
# nach der Preisliste des Betreibers) statt aus einem festen Wert hier.

# Vorbelegung für das Formular "Neue Karte aktivieren" (siehe ui.py).
# Diese Werte sind nur Startwerte für die Eingabefelder - der tatsächliche
# Betrag/Faktor wird pro Karte individuell erfragt und in der Tabelle
# "karte" gespeichert (Spalten anfangsguthaben, bezahlt_betrag, faktor).
STANDARD_ANFANGSGUTHABEN = 200.0                  # Vorbelegung ohne Vergünstigung
STANDARD_ANFANGSGUTHABEN_MIT_VERGUENSTIGUNG = 240.0  # Vorbelegung MIT Vergünstigung (lt. echter Karte)
STANDARD_BEZAHLT_BETRAG = 200.0

# Basis für die Verteilung der Karten-Abrechnung, wenn das Guthaben aufgebraucht ist:
#   "kosten"    -> Verteilung nach tatsächlich angefallenen Kosten pro Spieler
#                  (berücksichtigt, dass Sessions mit mehr Mitspielern pro Kopf
#                   günstiger waren)
#   "einheiten" -> alte Logik: Verteilung nach Summe der gespielten Einheiten,
#                  unabhängig davon, wie viele Personen sich die Session geteilt haben
ABRECHNUNG_BASIS = "kosten"

# Sortierungs-Reihenfolge für Tabellen-Anzeigen
ORDERED_COLUMNS = ["eingetragen_von", "gespielt_am", "gespielt_uhrzeit", "ermaessigt", "spieler", "eingetragen_am", "einheiten", "kosten"]
