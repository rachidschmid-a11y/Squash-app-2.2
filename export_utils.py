def to_csv_bytes(df, sep: str = ";", index: bool = False) -> bytes:
    """
    Wandelt einen DataFrame in CSV-Bytes für st.download_button um.

    - Semikolon als Trennzeichen (Standard-Einstellung von Excel in
      deutscher Locale; Kommas würden dort sonst als eine einzige Spalte
      importiert werden).
    - UTF-8 mit BOM ("utf-8-sig"), damit Umlaute (ä, ö, ü) beim Öffnen in
      Excel korrekt angezeigt werden.
    """
    return df.to_csv(index=index, sep=sep).encode("utf-8-sig")
