from datetime import date, time

import preisliste as pl


def test_wochentag_preisstufen():
    montag = date(2026, 8, 3)
    assert pl.ermittle_preis(montag, time(9, 0)) == 19.00
    assert pl.ermittle_preis(montag, time(15, 30)) == 18.00
    assert pl.ermittle_preis(montag, time(18, 0)) == 21.00
    assert pl.ermittle_preis(montag, time(21, 30)) == 18.00


def test_wochenend_preisstufen():
    samstag = date(2026, 8, 1)
    assert pl.ermittle_preis(samstag, time(9, 0)) == 17.00
    assert pl.ermittle_preis(samstag, time(11, 0)) == 19.00


def test_feiertag_zaehlt_als_wochenende():
    tag_der_arbeit = date(2026, 5, 1)  # Freitag, gesetzlicher Feiertag
    assert pl.ist_wochenend_tarif(tag_der_arbeit) is True
    assert pl.ermittle_preis(tag_der_arbeit, time(11, 0)) == 19.00


def test_normaler_werktag_ist_kein_wochenendtarif():
    montag = date(2026, 8, 3)
    assert pl.ist_wochenend_tarif(montag) is False


def test_bewegliche_feiertage_2026():
    feiertage = pl._berliner_feiertage(2026)
    assert date(2026, 4, 3) in feiertage   # Karfreitag
    assert date(2026, 4, 6) in feiertage   # Ostermontag
    assert date(2026, 5, 14) in feiertage  # Christi Himmelfahrt
    assert date(2026, 5, 25) in feiertage  # Pfingstmontag


def test_grenzfall_ausserhalb_der_bekannten_zeiten_stuerzt_nicht_ab():
    montag = date(2026, 8, 3)
    # Vor Öffnung: nimmt die erste Stufe als Näherung statt abzustürzen
    assert pl.ermittle_preis(montag, time(6, 0)) == 19.00
    # Nach Ladenschluss: nimmt die letzte Stufe
    assert pl.ermittle_preis(montag, time(23, 0)) == 18.00


def test_ermaessigter_tarif_wochentag():
    montag = date(2026, 8, 3)
    assert pl.ermittle_preis(montag, time(9, 0), ermaessigt=True) == 18.00
    assert pl.ermittle_preis(montag, time(15, 30), ermaessigt=True) == 17.00
    assert pl.ermittle_preis(montag, time(18, 0), ermaessigt=True) == 19.00
    assert pl.ermittle_preis(montag, time(21, 30), ermaessigt=True) == 17.00


def test_ermaessigt_wird_am_wochenende_ignoriert():
    """Laut Preisliste gibt es am Wochenende keinen ermäßigten Tarif -
    ermaessigt=True darf dort keinen Unterschied machen."""
    samstag = date(2026, 8, 1)
    assert pl.ermittle_preis(samstag, time(11, 0), ermaessigt=True) == pl.ermittle_preis(samstag, time(11, 0), ermaessigt=False)
    assert pl.ermittle_preis(samstag, time(11, 0), ermaessigt=True) == 19.00


def test_preisstufen_fuer_datum_ermaessigt():
    montag = date(2026, 8, 3)
    stufen_regulaer = pl.preisstufen_fuer_datum(montag, ermaessigt=False)
    stufen_ermaessigt = pl.preisstufen_fuer_datum(montag, ermaessigt=True)
    assert stufen_regulaer != stufen_ermaessigt
    assert len(stufen_regulaer) == len(stufen_ermaessigt) == 4
