"""
Berechnungslogik rund um die Preisliste des Betreibers.

Die eigentlichen Preise stehen NICHT hier, sondern in preise.py - diese
Datei enthält nur die Logik (Feiertagsberechnung, Nachschlagen der
passenden Preisstufe usw.) und muss bei einer reinen Preisänderung nicht
angefasst werden.
"""
from datetime import date, time, timedelta

from preise import (
    PREISSTUFEN_WOCHENTAG,
    PREISSTUFEN_WOCHENTAG_ERMAESSIGT,
    PREISSTUFEN_WOCHENENDE,
)


def _ostersonntag(jahr: int) -> date:
    """Gauss/Meeus-Algorithmus zur Berechnung des Ostersonntags (proleptisch
    gregorianisch) - wird für die beweglichen Feiertage gebraucht."""
    a = jahr % 19
    b = jahr // 100
    c = jahr % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    monat = (h + l - 7 * m + 114) // 31
    tag = ((h + l - 7 * m + 114) % 31) + 1
    return date(jahr, monat, tag)


def _berliner_feiertage(jahr: int) -> set:
    """Gesetzliche Feiertage in Berlin für ein Jahr (inkl. dem seit 2019
    Berlin-spezifischen Feiertag "Internationaler Frauentag" am 8. März)."""
    ostern = _ostersonntag(jahr)
    return {
        date(jahr, 1, 1),                        # Neujahr
        date(jahr, 3, 8),                        # Internationaler Frauentag (nur Berlin)
        ostern - timedelta(days=2),               # Karfreitag
        ostern + timedelta(days=1),               # Ostermontag
        date(jahr, 5, 1),                        # Tag der Arbeit
        ostern + timedelta(days=39),              # Christi Himmelfahrt
        ostern + timedelta(days=50),              # Pfingstmontag
        date(jahr, 10, 3),                        # Tag der Deutschen Einheit
        date(jahr, 12, 25),                       # 1. Weihnachtsfeiertag
        date(jahr, 12, 26),                       # 2. Weihnachtsfeiertag
    }


def ist_wochenend_tarif(datum: date) -> bool:
    """True, wenn an diesem Tag der Wochenend-/Feiertags-Tarif gilt
    (Samstag, Sonntag oder gesetzlicher Feiertag in Berlin)."""
    if datum.weekday() >= 5:  # 5 = Samstag, 6 = Sonntag
        return True
    return datum in _berliner_feiertage(datum.year)


def preisstufen_fuer_liste(wochenend_liste: bool, ermaessigt: bool = False) -> list:
    """
    Gibt die Liste der Preisstufen (start, ende, preis) für die gewählte
    Preisliste zurück: Wochenende/Feiertag (True) oder Montag bis Freitag
    (False, optional mit dem ermäßigten Schüler-/Studenten-Tarif).

    Die Wochenend-Liste kennt laut Preisliste des Betreibers keinen
    ermäßigten Tarif - dort wird "ermaessigt" ignoriert.
    """
    if wochenend_liste:
        return PREISSTUFEN_WOCHENENDE
    return PREISSTUFEN_WOCHENTAG_ERMAESSIGT if ermaessigt else PREISSTUFEN_WOCHENTAG


def preisstufen_fuer_datum(datum: date, ermaessigt: bool = False) -> list:
    """
    Wie preisstufen_fuer_liste, aber die Liste ergibt sich automatisch aus
    dem Datum (Samstag/Sonntag/Feiertag = Wochenend-Liste).
    """
    return preisstufen_fuer_liste(ist_wochenend_tarif(datum), ermaessigt)


def beide_preise_fuer_liste(wochenend_liste: bool) -> list:
    """
    Gibt für eine Preisliste die Preisstufen mit BEIDEN Tarifen gleichzeitig
    zurück, als Liste von (start, ende, preis_regulaer, preis_ermaessigt) -
    praktisch für eine Anzeige, die beide Preise nebeneinander zeigt.

    In der Wochenend-Liste ist preis_ermaessigt == preis_regulaer, weil es
    dort laut Preisliste keinen ermäßigten Tarif gibt.
    """
    regulaer = preisstufen_fuer_liste(wochenend_liste, ermaessigt=False)
    ermaessigt = preisstufen_fuer_liste(wochenend_liste, ermaessigt=True)
    return [
        (r_start, r_ende, r_preis, e_preis)
        for (r_start, r_ende, r_preis), (_e_start, _e_ende, e_preis) in zip(regulaer, ermaessigt)
    ]


def beide_preise_fuer_datum(datum: date) -> list:
    """Wie beide_preise_fuer_liste, die Liste ergibt sich aus dem Datum."""
    return beide_preise_fuer_liste(ist_wochenend_tarif(datum))


def zeitraum_label(datum: date, uhrzeit: time) -> str:
    """
    Gibt den vollen Zeitraum-Text (z.B. "15:00–21:00 Uhr") für eine
    gespeicherte Start-Uhrzeit zurück - für Anzeige/CSV-Export der
    Spiele-Übersicht. Die Zeitgrenzen sind unabhängig vom ermäßigten Tarif
    (nur die Preise unterscheiden sich), daher wird hier immer die reguläre
    Tabelle als Nachschlagewerk verwendet.

    Gespeichert wird immer der START einer Preisstufe. Passt dieser Start
    nicht zur Liste des Datums, aber genau zur anderen Liste (Sonderfall:
    am Wochenende wurde die Wochentag-Preisliste gewählt, z.B. wegen einer
    Vergünstigung vom Platzwart), zeigt das Label den Zeitraum dieser Liste.
    """
    eigene = preisstufen_fuer_datum(datum)
    andere = PREISSTUFEN_WOCHENTAG if ist_wochenend_tarif(datum) else PREISSTUFEN_WOCHENENDE
    for stufen in (eigene, andere):
        for start, ende, _preis in stufen:
            if start == uhrzeit:
                return f"{start.strftime('%H:%M')}–{ende.strftime('%H:%M')} Uhr"

    stufen = eigene
    for start, ende, _preis in stufen:
        if start <= uhrzeit < ende:
            return f"{start.strftime('%H:%M')}–{ende.strftime('%H:%M')} Uhr"

    # Randfall außerhalb bekannter Stufen (siehe ermittle_preis)
    start, ende, _preis = stufen[0] if uhrzeit < stufen[0][0] else stufen[-1]
    return f"{start.strftime('%H:%M')}–{ende.strftime('%H:%M')} Uhr"


def ermittle_preis_fuer_liste(wochenend_liste: bool, uhrzeit: time, ermaessigt: bool = False) -> float:
    """
    Liefert den Preis pro Einheit (€) für die gewählte Preisliste und
    Startzeit.

    Maßgeblich ist die Startzeit der Session (nicht anteilig pro Minute
    berechnet, falls eine Session über eine Preisgrenze hinausgeht - das
    entspricht der üblichen Abrechnungspraxis beim Court-Buchen).
    """
    stufen = preisstufen_fuer_liste(wochenend_liste, ermaessigt)

    for start, ende, preis in stufen:
        if start <= uhrzeit < ende:
            return preis

    # Uhrzeit liegt außerhalb der bekannten Preisstufen (z.B. vor 8 Uhr oder
    # nach Ladenschluss) - nimm die nächstgelegene Stufe als Näherung,
    # anstatt abzustürzen.
    if uhrzeit < stufen[0][0]:
        return stufen[0][2]
    return stufen[-1][2]


def ermittle_preis(datum: date, uhrzeit: time, ermaessigt: bool = False) -> float:
    """
    Liefert den Preis pro Einheit (€) für einen Spieltermin, basierend auf
    der Preisliste des Betreibers; die Liste (Wochentag oder Wochenende)
    ergibt sich aus dem Datum.
    """
    return ermittle_preis_fuer_liste(ist_wochenend_tarif(datum), uhrzeit, ermaessigt)
