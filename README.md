# 🏸 Squash Hub

*[🇬🇧 English version available here](README.en.md)*

Eine kleine [Streamlit](https://streamlit.io)-Webanwendung zur Verwaltung
einer gemeinsam genutzten Squash-Wertkarte: Kosten pro Session erfassen und
automatisch splitten, Guthaben verfolgen, Endabrechnungen erstellen sowie
sportliche Ergebnisse und Statistiken führen. Als Datenbank kommt
[Supabase](https://supabase.com) (Postgres) zum Einsatz.

Diese Dokumentation beschreibt den kompletten Setup-Prozess von null auf
eine lauffähige, selbst gehostete Instanz – inklusive Datenbankschema,
lokaler Entwicklung und Deployment.

> **Hinweis:** Diese Dokumentation und der zugehörige Code enthalten keine
> personenbezogenen Daten (keine echten Namen, Zugangsdaten oder
> Finanzdaten). Alle Beispielwerte sind frei erfunden bzw. exemplarisch.

---

## Inhaltsverzeichnis

1. [Funktionsübersicht](#funktionsübersicht)
2. [Technischer Stack](#technischer-stack)
3. [Projektstruktur](#projektstruktur)
4. [Voraussetzungen](#voraussetzungen)
5. [Setup Schritt 1: Supabase-Projekt einrichten](#setup-schritt-1-supabase-projekt-einrichten)
6. [Setup Schritt 2: Datenbankschema anlegen](#setup-schritt-2-datenbankschema-anlegen)
7. [Setup Schritt 3: Lokale Entwicklungsumgebung](#setup-schritt-3-lokale-entwicklungsumgebung)
8. [Setup Schritt 4: Deployment auf Streamlit Community Cloud](#setup-schritt-4-deployment-auf-streamlit-community-cloud)
9. [Konfiguration](#konfiguration)
10. [Tests](#tests)
11. [Datenbank-Schema-Referenz](#datenbank-schema-referenz)
12. [Troubleshooting](#troubleshooting)
13. [Sicherheitshinweise](#sicherheitshinweise)
14. [Lizenz](#lizenz)

---

## Funktionsübersicht

| Bereich | Funktionen |
|---|---|
| 💰 **Abrechnung & Guthaben** | Neue Wertkarte aktivieren (inkl. optionaler Vergünstigung), Spiel-Sessions eintragen (mit zeitabhängiger Preisstufe), automatische Endabrechnung bei aufgebrauchtem Guthaben, fehlerhafte Einträge korrigieren/löschen, CSV-Export |
| 🏆 **Matches eintragen** | Ergebnisse (Sätze, Gewinner/Verlierer) erfassen und verwalten, CSV-Export |
| 📊 **Sportliche Statistiken** | Sieg-/Niederlagen-Quote pro Spieler, Head-to-Head-Matrix, Verlaufsdiagramme |
| 👥 **Spielerverwaltung** | Spieler hinzufügen, deaktivieren (reversibel) oder endgültig löschen – ohne Code-Änderung |
| 🔒 **Zugriffsschutz** | Einfacher, gemeinsamer Passwortschutz für die ganze App |

---

## Technischer Stack

- **Frontend/Backend:** [Streamlit](https://streamlit.io) (Python)
- **Datenbank:** [Supabase](https://supabase.com) (Postgres + REST/Data API)
- **Visualisierung:** Plotly, Matplotlib
- **Tests:** pytest
- **Hosting:** [Streamlit Community Cloud](https://streamlit.io/cloud) (oder jede andere Umgebung, die Streamlit-Apps hosten kann)

---

## Projektstruktur

```
.
├── app.py                     # Einstiegspunkt, Navigation, Login-Gate
├── auth.py                    # Passwortschutz
├── ui.py                      # Seite "Abrechnung & Guthaben" + Statistik-Seite
├── player_results.py          # Seite "Matches eintragen"
├── spieler_verwaltung.py      # Seite "Spielerverwaltung"
├── calculations.py            # Kernlogik: Kosten, Guthaben, Abrechnung, Statistik
├── database.py                # Sämtliche Supabase-Zugriffe (zentral gekapselt)
├── preise.py                  # NUR die Preistabelle (für Preisänderungen)
├── preisliste.py              # Logik rund um die Preistabelle (Feiertage, Zeitstufen)
├── zeit_utils.py              # Zeitzonen-Umrechnung (UTC -> Europe/Berlin)
├── export_utils.py            # CSV-Export-Hilfsfunktion
├── config.py                  # Globale Konstanten/Vorbelegungen
├── requirements.txt           # Python-Abhängigkeiten (Produktion)
├── requirements-dev.txt       # Zusätzlich für lokale Tests (pytest)
├── devcontainer.json           # Optionale Dev-Container-Konfiguration (VS Code/Codespaces)
├── .streamlit/
│   └── secrets.toml.example   # Vorlage für die Zugangsdaten (siehe unten)
├── tests/
│   ├── test_calculations.py
│   └── test_preisliste.py
├── setup_datenbank_komplett.sql   # Komplettes DB-Schema zum einmaligen Ausführen
├── migration.sql                  # Historische Einzel-Migration (Spielerverwaltung + Vergünstigung)
├── migration_preisliste.sql       # Historische Einzel-Migration (Uhrzeit-Spalte)
└── migration_ermaessigt.sql       # Historische Einzel-Migration (ermäßigter Tarif)
```

> Die einzelnen `migration_*.sql`-Dateien dokumentieren, wie sich das Schema
> historisch entwickelt hat. Für ein **neues** Projekt reicht es,
> ausschließlich `setup_datenbank_komplett.sql` auszuführen (siehe unten) –
> das legt bereits den vollständigen, aktuellen Stand an.

---

## Voraussetzungen

- Python 3.11 oder neuer
- Ein kostenloser [Supabase](https://supabase.com)-Account
- Ein [GitHub](https://github.com)-Account (für das Deployment auf Streamlit Community Cloud)
- Git

---

## Setup Schritt 1: Supabase-Projekt einrichten

1. Bei [supabase.com](https://supabase.com) einloggen und **New Project** anlegen.
2. Beim Anlegen erscheinen u. a. folgende Optionen – empfohlene Einstellung:
   - **Enable Data API**: **aktiviert lassen.** Ohne die Data API (REST-Schnittstelle)
     kann die App über `supabase-py` gar nicht auf die Tabellen zugreifen.
   - **Automatically expose new tables**: aktiviert lassen, solange ihr wie in
     dieser Anleitung mit deaktiviertem Row Level Security arbeitet (siehe
     Schritt 2) – sonst fehlen den Zugriffsrollen ggf. die Basis-Rechte auf
     neue Tabellen.
   - **Enable automatic RLS**: spielt keine Rolle, weil das Setup-Skript in
     Schritt 2 Row Level Security für alle Tabellen ohnehin explizit
     deaktiviert (mehr dazu unter [Sicherheitshinweise](#sicherheitshinweise)).
3. Nach dem Erstellen: **Project Settings → API Keys** öffnen und notieren:
   - **Project URL** (z. B. `https://xxxxxxxxxxxx.supabase.co`)
   - **Publishable key** (moderner Nachfolger des klassischen `anon`-Keys;
     ein noch vorhandener `anon`-Key funktioniert ebenfalls, wird aber von
     Supabase perspektivisch abgelöst – die Publishable Key-Variante wird
     empfohlen)

   Diese beiden Werte werden später in `secrets.toml` benötigt.

---

## Setup Schritt 2: Datenbankschema anlegen

1. Im Supabase-Dashboard zu **SQL Editor → New query** wechseln.
2. Den kompletten Inhalt von [`setup_datenbank_komplett.sql`](#anhang-sql-skript)
   (siehe unten oder Datei im Repository) einfügen und ausführen.

Das Skript legt fünf Tabellen an (`spieler`, `karte`, `spiele`, `abrechnung`,
`spielergebnisse`) und deaktiviert Row Level Security auf allen fünf
Tabellen (Begründung siehe [Sicherheitshinweise](#sicherheitshinweise)).

Spieler werden **nicht** per SQL vorbelegt – das passiert nach dem ersten
Start bequem über die Seite **👥 Spielerverwaltung** in der App selbst.

### Anhang: SQL-Skript

```sql
-- =========================================================
-- SQUASH APP - KOMPLETTES DATENBANK-SETUP
-- =========================================================
-- Im Supabase SQL-Editor ausführen (Projekt -> SQL Editor -> New query).
--
-- ⚠️ Die DROP TABLE-Zeilen unten sind absichtlich auskommentiert. Nur
-- einkommentieren, wenn ein bestehendes Projekt mit vorhandenen Daten
-- bewusst komplett zurückgesetzt werden soll (unwiderruflich!).
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

-- Spieler werden über die App-Seite "Spielerverwaltung" angelegt.
-- Alternativ direkt per SQL, z. B.:
-- INSERT INTO spieler (name) VALUES ('Anna'), ('Ben');


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
-- BERECHTIGUNGEN (Row Level Security)
-- =========================================================
-- RLS wird deaktiviert, weil die App ohne individuelles Supabase-Login
-- direkt mit einem gemeinsamen API-Key zugreift - der Zugriffsschutz läuft
-- stattdessen über das Passwort in der App selbst (siehe auth.py). Für
-- strengere Sicherheit könnte man RLS stattdessen aktiviert lassen und
-- gezielte Policies je Tabelle vergeben.
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
```

---

## Setup Schritt 3: Lokale Entwicklungsumgebung

### 3.1 Repository klonen

```bash
git clone <URL-eures-Repositories>
cd <Repository-Ordner>
```

### 3.2 Python-Umgebung einrichten

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3.3 Secrets konfigurieren

```bash
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Anschließend `.streamlit/secrets.toml` öffnen und mit echten Werten füllen:

```toml
SUPABASE_URL = "https://euer-projekt.supabase.co"
SUPABASE_KEY = "euer-publishable-oder-anon-key"

# Optional, aber empfohlen: gemeinsames Passwort für die App
APP_PASSWORD = "ein-sicheres-passwort"
```

> ⚠️ `.streamlit/secrets.toml` **niemals** committen! Sie ist bereits in
> `.gitignore` eingetragen. Fehlt `APP_PASSWORD` komplett, läuft die App
> ohne Passwortschutz (mit deutlichem Warnhinweis in der Oberfläche).

### 3.4 App lokal starten

```bash
streamlit run app.py
```

Die App ist danach unter `http://localhost:8501` erreichbar.

### 3.5 Optional: Dev Container / GitHub Codespaces

Das Repository enthält eine `devcontainer.json` für VS Code Dev Containers
bzw. GitHub Codespaces – damit lässt sich eine vollständige, vorkonfigurierte
Entwicklungsumgebung direkt im Browser starten, ohne lokale Installation.

---

## Setup Schritt 4: Deployment auf Streamlit Community Cloud

1. Repository auf GitHub pushen (ohne `secrets.toml`!).
2. Bei [share.streamlit.io](https://share.streamlit.io) einloggen, **New app**
   wählen und das Repository sowie `app.py` als Hauptdatei auswählen.
3. Unter **Advanced settings → Secrets** die gleichen Werte wie in
   `.streamlit/secrets.toml` eintragen (TOML-Format, siehe oben).
4. Deployen. Bei jedem Push auf den verbundenen Branch aktualisiert
   Streamlit Community Cloud die App automatisch neu.

---

## Konfiguration

### Preise anpassen

Ändert sich die Preisliste des Betreibers, genügt es, **ausschließlich**
`preise.py` zu bearbeiten – die beiden Preisstufen-Listen für Wochentage
(regulär und ermäßigt) sowie fürs Wochenende/Feiertage. Keine andere Datei
muss angefasst werden.

```python
# preise.py
PREISSTUFEN_WOCHENTAG = [
    (time(8, 0), time(15, 0), 19.00),
    # ... weitere Zeitstufen
]
```

Die Berechnungslogik (`preisliste.py`) ermittelt daraus automatisch, welche
Preisstufe für ein gegebenes Datum/Uhrzeit gilt, inklusive automatischer
Erkennung gesetzlicher Feiertage in Berlin (bewegliche Feiertage werden
über die Gauß'sche Osterformel berechnet – keine externe Abhängigkeit
nötig). Für einen anderen Bundesland-Feiertagskalender müsste die Liste in
`preisliste.py` (`_berliner_feiertage`) angepasst werden.

### Kartenrabatt / Vergünstigung

Manche Betreiber bieten beim Aufladen einer Wertkarte einen Rabatt (z. B.
"X € bezahlt für Y € Guthaben"). Beim Aktivieren einer neuen Karte fragt die
App optional danach und speichert `anfangsguthaben`, `bezahlt_betrag` sowie
den daraus berechneten `faktor` in der Datenbank. Wichtig dabei: Der
Rabattfaktor wirkt sich **nicht** auf die laufende Guthaben-Abbuchung pro
Session aus (die erfolgt zum vollen Listenpreis, wie es die meisten
Betreiber selbst handhaben), sondern ausschließlich auf die **Endabrechnung**
– dort wird der tatsächlich bezahlte Betrag proportional zur Nutzung auf die
Spieler verteilt.

### Spieler verwalten

Spieler werden ausschließlich über die App-Seite **👥 Spielerverwaltung**
verwaltet (hinzufügen, deaktivieren/aktivieren, löschen) – nicht im Code.
Deaktivierte Spieler verschwinden aus den Auswahllisten für neue Einträge,
bleiben aber in der Statistik sichtbar (für bereits gespielte Matches).

### Passwortschutz

Ein einzelnes, gemeinsames Passwort für die gesamte App, hinterlegt als
`APP_PASSWORD` in den Secrets (siehe oben). Kein Zugriffsschutz pro Person –
für eine kleine, vertrauenswürdige Gruppe ausreichend, aber kein Ersatz für
ein echtes Mehrbenutzer-Login-System.

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Die Tests decken die Kernlogik ab (Kostenberechnung, Preisstufen,
Feiertagsberechnung, Abrechnungsverteilung, Statistik-Funktionen) und
verwenden ein Fake-Modul anstelle einer echten Datenbankverbindung – es
werden also keine echten Supabase-Zugangsdaten für die Tests benötigt.

---

## Datenbank-Schema-Referenz

| Tabelle | Zweck | Wichtige Spalten |
|---|---|---|
| `spieler` | Spielerverwaltung | `name`, `aktiv` |
| `karte` | Aktuelle/vergangene Wertkarten | `guthaben`, `bezahlt_von`, `anfangsguthaben`, `bezahlt_betrag`, `faktor`, `aktiv` |
| `spiele` | Einzelne Spiel-Sessions (Kostenverteilung) | `spieler`, `einheiten`, `kosten`, `gespielt_am`, `gespielt_uhrzeit`, `ermaessigt`, `abgerechnet` |
| `abrechnung` | Endabrechnungs-Historie je Karte | `spieler`, `betrag`, `karte_id` |
| `spielergebnisse` | Sportliche Ergebnisse | `gewinner`, `verlierer`, `satz_gewinner`, `satz_verlierer` |

Alle Tabellen verwenden Textfelder für Spielernamen (kein Fremdschlüssel auf
`spieler.id`) – das Löschen eines Spielers in der Spielerverwaltung
entfernt ihn daher nur aus zukünftigen Auswahllisten, historische Einträge
bleiben unverändert erhalten.

---

## Troubleshooting

**"Oh no. Error running app." ohne erkennbaren Grund**
Meist hilft ein Blick in die vollständigen Logs (Streamlit Cloud:
App-Menü → *Manage app* → *Logs*) – die kurze Fehlermeldung auf der
Oberfläche zeigt selten die eigentliche Ursache.

**Zugriff auf Supabase schlägt fehl, obwohl die Zugangsdaten korrekt sind**
Meist ein Berechtigungsproblem: entweder ist Row Level Security aktiv ohne
passende Policy (siehe Setup-Skript, das RLS bewusst deaktiviert), oder den
Rollen `anon`/`authenticated` fehlen die Grundrechte auf die Tabellen. Zur
Not helfen:
```sql
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
```

**Streamlit-Version verursacht Fehler**
`requirements.txt` pinnt bewusst `streamlit>=1.51` (der `width`-Parameter
für `st.plotly_chart` existiert erst ab dieser Version). Bei Problemen mit
neueren Versionen: exakte, getestete Version pinnen (`streamlit==x.y.z`)
statt eines offenen Bereichs.

**Zeitangaben wirken "falsch" (ein/zwei Stunden daneben)**
Der Anwendungsserver läuft in UTC. Zeitstempel werden explizit als UTC
gespeichert und erst bei der Anzeige nach `Europe/Berlin` umgerechnet
(`zeit_utils.py`), inklusive korrekter Sommer-/Winterzeit-Behandlung über
Pythons `zoneinfo`.

---

## Sicherheitshinweise

- Diese App bietet **keinen** individuellen Nutzer-Login, sondern ein
  einzelnes gemeinsames Passwort für eine kleine, vertrauenswürdige Gruppe.
  Für einen größeren oder weniger vertrauenswürdigen Nutzerkreis wäre ein
  echtes Auth-System (z. B. Supabase Auth) angebracht.
- Row Level Security ist bewusst deaktiviert (siehe oben) – das bedeutet,
  der verwendete Supabase-API-Key gewährt vollen Lese-/Schreibzugriff auf
  alle Tabellen. Diesen Key entsprechend vertraulich behandeln (niemals in
  öffentlichen Repositories committen, `.gitignore` beachten).
- Es wird empfohlen, den modernen **Publishable Key** zu verwenden statt
  des klassischen `service_role`/Secret Keys – letzterer umgeht RLS
  komplett und sollte niemals in einer Client-Anwendung verwendet werden,
  selbst wenn RLS ohnehin deaktiviert ist.

---

## Lizenz

Privates Projekt. Lizenz nach Bedarf ergänzen (z. B. MIT), falls das
Repository öffentlich geteilt werden soll.
