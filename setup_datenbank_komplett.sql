-- =========================================================
-- SQUASH APP - KOMPLETTES DATENBANK-SETUP (Stand: aktueller App-Code)
-- =========================================================
-- Im Supabase SQL-Editor ausführen (Projekt -> SQL Editor -> New query).
--
-- ⚠️ ACHTUNG: Die DROP TABLE-Zeilen unten sind absichtlich auskommentiert.
-- Wenn du ein bestehendes Projekt mit echten Daten (z.B. Marlons Karte)
-- zurücksetzt, werden diese Daten UNWIDERRUFLICH gelöscht. Nur einkommentieren,
-- wenn du wirklich bei null anfangen willst. Für ein brandneues, leeres
-- Supabase-Projekt kannst du sie drin lassen (dann schlagen sie einfach
-- fehl bzw. tun nichts, wenn die Tabellen noch nicht existieren) oder
-- die Kommentare entfernen.
-- =========================================================

-- DROP TABLE IF EXISTS abrechnung CASCADE;
-- DROP TABLE IF EXISTS spielergebnisse CASCADE;
-- DROP TABLE IF EXISTS spiele CASCADE;
-- DROP TABLE IF EXISTS karte CASCADE;
-- DROP TABLE IF EXISTS spieler CASCADE;


-- =========================================================
-- 1) TABELLE: spieler (Spielerverwaltung)
-- =========================================================
CREATE TABLE IF NOT EXISTS spieler (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    aktiv BOOLEAN DEFAULT TRUE NOT NULL,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Eure bisherige Spielerliste einmalig übernehmen (passt die Namen bei
-- Bedarf an - "on conflict do nothing" macht das gefahrlos wiederholbar).
INSERT INTO spieler (name) VALUES
    ('Jonas'),
    ('Marlon'),
    ('Paul'),
    ('Vossi'),
    ('Karsten')
ON CONFLICT (name) DO NOTHING;


-- =========================================================
-- 2) TABELLE: karte (Wertkarten / Guthaben / Vergünstigung)
-- =========================================================
CREATE TABLE IF NOT EXISTS karte (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guthaben NUMERIC(10,2) NOT NULL,
    aktiv BOOLEAN DEFAULT TRUE NOT NULL,
    bezahlt_von TEXT NOT NULL,
    anfangsguthaben NUMERIC(10,2),   -- wie viel Guthaben beim Aktivieren aufgeladen wurde
    bezahlt_betrag NUMERIC(10,2),    -- wie viel dafür tatsächlich bezahlt wurde
    faktor NUMERIC                   -- bezahlt_betrag / anfangsguthaben, für die Endabrechnung
);


-- =========================================================
-- 3) TABELLE: spiele (einzelne Spiel-Sessions / Kosten-Splitting)
-- =========================================================
CREATE TABLE IF NOT EXISTS spiele (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    spieler TEXT NOT NULL,
    einheiten INT NOT NULL,
    kosten NUMERIC(10,2) NOT NULL,
    eingetragen_von TEXT NOT NULL,
    eingetragen_am TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    gespielt_am DATE NOT NULL,
    gespielt_uhrzeit TIME,            -- Startzeit für die Preisstufe (preisliste.py)
    ermaessigt BOOLEAN DEFAULT FALSE NOT NULL,
    karte_id INT REFERENCES karte(id), -- welche Karte war beim Eintragen aktiv (für Reaktivierung)
    abgerechnet BOOLEAN DEFAULT FALSE NOT NULL
);


-- =========================================================
-- 4) TABELLE: abrechnung (wer schuldet wem was, je Karte)
-- =========================================================
CREATE TABLE IF NOT EXISTS abrechnung (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    spieler TEXT NOT NULL,
    betrag NUMERIC(10,2) NOT NULL,
    karte_id INT REFERENCES karte(id) ON DELETE CASCADE
);


-- =========================================================
-- 5) TABELLE: spielergebnisse (sportliche Ergebnisse)
-- =========================================================
CREATE TABLE IF NOT EXISTS spielergebnisse (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gespielt_am DATE NOT NULL,
    gewinner TEXT NOT NULL,
    verlierer TEXT NOT NULL,
    satz_gewinner INT NOT NULL,
    satz_verlierer INT NOT NULL,
    eingetragen_von TEXT NOT NULL,
    eingetragen_am TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);


-- =========================================================
-- BERECHTIGUNGEN (RLS)
-- =========================================================
-- Wie beim letzten Setup: RLS deaktiviert, da die App ohne Supabase-Login
-- direkt mit dem anon-Key zugreift (Zugriffsschutz läuft stattdessen über
-- das Passwort in der App selbst, siehe auth.py). Für strengere Sicherheit
-- könnte man stattdessen RLS aktiviert lassen und gezielte Policies je
-- Tabelle vergeben - für eine kleine, geschlossene Gruppe ist das hier aber
-- ausreichend.
ALTER TABLE spieler DISABLE ROW LEVEL SECURITY;
ALTER TABLE karte DISABLE ROW LEVEL SECURITY;
ALTER TABLE spiele DISABLE ROW LEVEL SECURITY;
ALTER TABLE abrechnung DISABLE ROW LEVEL SECURITY;
ALTER TABLE spielergebnisse DISABLE ROW LEVEL SECURITY;


-- =========================================================
-- Kontrolle: sollte 5 Tabellen mit den erwarteten Spalten zeigen
-- =========================================================
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name IN ('spieler', 'karte', 'spiele', 'abrechnung', 'spielergebnisse')
-- ORDER BY table_name, ordinal_position;
