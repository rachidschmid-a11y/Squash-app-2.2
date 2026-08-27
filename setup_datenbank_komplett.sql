-- =========================================================
-- SQUASH APP - KOMPLETTES DATENBANK-SETUP (Stand: aktueller App-Code)
-- =========================================================
-- Im Supabase SQL-Editor ausführen (Projekt -> SQL Editor -> New query).
--
-- ⚠️ ACHTUNG: Die DROP TABLE-Zeilen unten sind absichtlich auskommentiert.
-- Wenn du ein bestehendes Projekt mit echten Daten zurücksetzt, werden diese
-- Daten UNWIDERRUFLICH gelöscht. Nur einkommentieren,
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

-- Beispiel-Spieler zum Start - Namen bei Bedarf anpassen/ergänzen
-- ("on conflict do nothing" macht das gefahrlos wiederholbar ausführbar).
INSERT INTO spieler (name) VALUES
    ('Anna'),
    ('Ben'),
    ('Clara'),
    ('David'),
    ('Emma')
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
    karte_id INT REFERENCES karte(id) ON DELETE SET NULL, -- welche Karte war aktiv (für Reaktivierung + Überschuss-Splitting)
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
-- RLS wird aktiviert (Supabase markiert Tabellen ohne RLS als "Critical
-- issue: Table publicly accessible"), aber mit einer offenen Policy für
-- die Rolle "anon" versehen - damit verhält sich der Zugriff für die App
-- identisch wie zuvor mit deaktiviertem RLS (die App nutzt ohnehin nur
-- einen einzigen, gemeinsamen API-Key statt individueller Supabase-Logins;
-- der eigentliche Zugriffsschutz läuft über das Passwort in der App
-- selbst, siehe auth.py). Für echten, zeilenweisen Schutz wären
-- individuelle Logins (Supabase Auth) mit entsprechend engeren Policies
-- nötig - für eine kleine, geschlossene Gruppe ist der Aufwand dafür meist
-- nicht gerechtfertigt.
ALTER TABLE spieler ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "app_zugriff" ON spieler;
CREATE POLICY "app_zugriff" ON spieler FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE karte ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "app_zugriff" ON karte;
CREATE POLICY "app_zugriff" ON karte FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE spiele ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "app_zugriff" ON spiele;
CREATE POLICY "app_zugriff" ON spiele FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE abrechnung ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "app_zugriff" ON abrechnung;
CREATE POLICY "app_zugriff" ON abrechnung FOR ALL TO anon USING (true) WITH CHECK (true);

ALTER TABLE spielergebnisse ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "app_zugriff" ON spielergebnisse;
CREATE POLICY "app_zugriff" ON spielergebnisse FOR ALL TO anon USING (true) WITH CHECK (true);


-- =========================================================
-- Kontrolle: sollte 5 Tabellen mit den erwarteten Spalten zeigen
-- =========================================================
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name IN ('spieler', 'karte', 'spiele', 'abrechnung', 'spielergebnisse')
-- ORDER BY table_name, ordinal_position;
