"""
NUR die Preistabelle des Betreibers - keine Logik, keine Funktionen.

Diese Datei ist absichtlich so einfach wie möglich gehalten: Wenn der
Betreiber die Preise ändert, reicht es, hier die Zahlen anzupassen. Die
Berechnungslogik (welche Preisstufe an welchem Tag gilt usw.) liegt in
preisliste.py und muss dafür nicht angefasst werden.

Format je Zeile: (Start-Uhrzeit, End-Uhrzeit, Preis pro Einheit in €)
Start ist inklusive, Ende ist exklusiv (z.B. "16:45" gehört schon zur
nächsten Stufe).
"""
from datetime import time

# Montag bis Freitag - regulärer Preis
PREISSTUFEN_WOCHENTAG = [
    (time(8, 0), time(15, 0), 19.00),
    (time(15, 0), time(16, 45), 18.00),
    (time(16, 45), time(21, 0), 21.00),
    (time(21, 0), time(22, 0), 18.00),
]

# Montag bis Freitag - ermäßigter Tarif (Schüler + Studenten)
PREISSTUFEN_WOCHENTAG_ERMAESSIGT = [
    (time(8, 0), time(15, 0), 18.00),
    (time(15, 0), time(16, 45), 17.00),
    (time(16, 45), time(21, 0), 19.00),
    (time(21, 0), time(22, 0), 17.00),
]

# Samstag, Sonntag und gesetzliche Feiertage (Berlin) - lt. Preisliste gibt
# es hier KEINEN ermäßigten Tarif, nur den einen (regulären) Preis.
PREISSTUFEN_WOCHENENDE = [
    (time(8, 0), time(10, 0), 17.00),
    (time(10, 0), time(20, 0), 19.00),
]
