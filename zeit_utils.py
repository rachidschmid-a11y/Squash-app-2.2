import pandas as pd
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")


def to_berlin_time_str(series: pd.Series, fmt: str = "%d.%m.%Y %H:%M") -> pd.Series:
    """
    Wandelt eine Spalte mit Zeitstempeln in lesbare Berliner Ortszeit um.

    Die Zeitstempel werden in der Datenbank als UTC gespeichert (egal ob von
    Python per datetime.now(timezone.utc) oder von Postgres per DEFAULT
    NOW() erzeugt) - hier wird auf Europe/Berlin umgerechnet. ZoneInfo statt
    eines festen Offsets, damit die Sommerzeit-Umstellung (CET/CEST)
    automatisch korrekt berücksichtigt wird.

    Funktioniert sowohl mit Zeitstempeln, die bereits ein UTC-Offset
    enthalten (z.B. "...+00:00" von Postgres), als auch mit "naiven"
    Zeitstempeln ohne Offset (die dann als UTC interpretiert werden).
    """
    return pd.to_datetime(series, utc=True).dt.tz_convert(BERLIN_TZ).dt.strftime(fmt)
