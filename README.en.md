# 🏸 Squash Hub

*[🇩🇪 Deutsche Version hier verfügbar](README.md)*

A small [Streamlit](https://streamlit.io) web app for managing a shared
squash court value card: log session costs and split them automatically,
track the remaining balance, generate final settlements, and keep track of
match results and statistics. [Supabase](https://supabase.com) (Postgres)
is used as the database.

This documentation covers the complete setup process from scratch to a
running, self-hosted instance — including the database schema, local
development, and deployment.

> **Note:** This documentation and the accompanying code contain no
> personal data (no real names, credentials, or financial figures). All
> example values are fictional or illustrative only.

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Setup Step 1: Set Up a Supabase Project](#setup-step-1-set-up-a-supabase-project)
6. [Setup Step 2: Create the Database Schema](#setup-step-2-create-the-database-schema)
7. [Setup Step 3: Local Development Environment](#setup-step-3-local-development-environment)
8. [Setup Step 4: Deploy to Streamlit Community Cloud](#setup-step-4-deploy-to-streamlit-community-cloud)
9. [Configuration](#configuration)
10. [Tests](#tests)
11. [Database Schema Reference](#database-schema-reference)
12. [Troubleshooting](#troubleshooting)
13. [Security Notes](#security-notes)
14. [License](#license)

---

## Feature Overview

| Area | Features |
|---|---|
| 🏠 **Dashboard** | Central home page: card balance, active players, last session, and match stats at a glance, plus quick links to the other pages |
| 💰 **Billing & Balance** | Activate a new value card (with optional bulk-purchase discount), log play sessions (with time-of-day-based pricing and a preview before saving), automatic final settlement once the balance runs out, correct/delete faulty entries (including already-settled ones), reactivate accidentally-settled cards, CSV export |
| 🏆 **Log Matches** | Record and manage match results (sets, winner/loser), CSV export |
| 📊 **Sports Statistics** | Win/loss ratio per player, head-to-head matrix, trend charts |
| 👥 **Player Management** | Add players, deactivate them (reversible), or delete them permanently — no code changes required |
| 🔒 **Access Control** | Simple shared password protection for the whole app |

---

## Tech Stack

- **Frontend/Backend:** [Streamlit](https://streamlit.io) (Python)
- **Database:** [Supabase](https://supabase.com) (Postgres + REST/Data API)
- **Visualization:** Plotly, Matplotlib
- **Tests:** pytest
- **Hosting:** [Streamlit Community Cloud](https://streamlit.io/cloud) (or any other environment capable of hosting Streamlit apps)

---

## Project Structure

```
.
├── app.py                     # Entry point, navigation, login gate
├── auth.py                    # Password protection
├── dashboard.py                # "🏠 Dashboard" page (home/overview)
├── ui.py                      # "Billing & Balance" page + statistics page
├── player_results.py          # "Log Matches" page
├── spieler_verwaltung.py      # "Player Management" page
├── calculations.py            # Core logic: costs, balance, settlement, statistics
├── database.py                # All Supabase access, centrally encapsulated
├── preise.py                  # ONLY the price table (edit this for price changes)
├── preisliste.py              # Logic around the price table (holidays, time tiers)
├── zeit_utils.py               # Timezone conversion (UTC -> Europe/Berlin)
├── export_utils.py            # CSV export helper
├── config.py                  # Global constants/default values
├── requirements.txt           # Python dependencies (production)
├── requirements-dev.txt       # Additional dependencies for local tests (pytest)
├── devcontainer.json           # Optional dev container config (VS Code/Codespaces)
├── .streamlit/
│   └── secrets.toml.example   # Template for credentials (see below)
├── tests/
│   ├── test_calculations.py
│   └── test_preisliste.py
├── setup_datenbank_komplett.sql   # Complete DB schema to run once
├── migration.sql                  # Historical incremental migration (player management + discount)
├── migration_preisliste.sql       # Historical incremental migration (time-of-day column)
├── migration_ermaessigt.sql       # Historical incremental migration (discounted tariff)
└── migration_karte_reaktivierung.sql  # Historical incremental migration (card reactivation)
```

> The individual `migration_*.sql` files document how the schema evolved
> historically. For a **new** project, it is sufficient to run only
> `setup_datenbank_komplett.sql` (see below) — it already creates the
> complete, current schema.

---

## Prerequisites

- Python 3.11 or newer
- A free [Supabase](https://supabase.com) account
- A [GitHub](https://github.com) account (for deployment to Streamlit Community Cloud)
- Git

---

## Setup Step 1: Set Up a Supabase Project

1. Log in at [supabase.com](https://supabase.com) and create a **New Project**.
2. During creation you'll see a few options — recommended settings:
   - **Enable Data API**: **keep this enabled.** Without the Data API
     (REST interface), the app cannot access the tables at all via
     `supabase-py`.
   - **Automatically expose new tables**: keep enabled — otherwise the
     access roles may lack basic privileges on new tables.
   - **Enable automatic RLS**: doesn't matter either way, since the setup
     script in Step 2 explicitly enables Row Level Security for all tables
     itself and attaches a matching policy (see [Security Notes](#security-notes) for why).
3. After creation, open **Project Settings → API Keys** and note down:
   - **Project URL** (e.g. `https://xxxxxxxxxxxx.supabase.co`)
   - **Publishable key** (the modern successor to the classic `anon` key;
     an existing `anon` key still works too but is being phased out by
     Supabase over time — the Publishable Key variant is recommended)

   You'll need both values later in `secrets.toml`.

---

## Setup Step 2: Create the Database Schema

1. In the Supabase dashboard, go to **SQL Editor → New query**.
2. Paste the full contents of [`setup_datenbank_komplett.sql`](#appendix-sql-script)
   (see below, or the file in the repository) and run it.

The script creates five tables (`spieler`, `karte`, `spiele`, `abrechnung`,
`spielergebnisse`) and enables Row Level Security on all five, attached to
a policy that grants full access to the shared API key (see
[Security Notes](#security-notes) for the reasoning).

Players are **not** pre-populated via SQL — that's done conveniently after
the first launch, from the **👥 Player Management** page in the app itself.

### Appendix: SQL Script

```sql
-- =========================================================
-- SQUASH APP - COMPLETE DATABASE SETUP
-- =========================================================
-- Run in the Supabase SQL Editor (Project -> SQL Editor -> New query).
--
-- ⚠️ The DROP TABLE lines below are intentionally commented out. Only
-- uncomment them if you deliberately want to reset an existing project
-- with existing data (irreversible!).
-- =========================================================

-- DROP TABLE IF EXISTS abrechnung CASCADE;
-- DROP TABLE IF EXISTS spielergebnisse CASCADE;
-- DROP TABLE IF EXISTS spiele CASCADE;
-- DROP TABLE IF EXISTS karte CASCADE;
-- DROP TABLE IF EXISTS spieler CASCADE;


-- =========================================================
-- 1) TABLE: spieler (player management)
-- =========================================================
CREATE TABLE IF NOT EXISTS spieler (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    aktiv BOOLEAN DEFAULT TRUE NOT NULL,
    erstellt_am TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Players are added via the app's "Player Management" page.
-- Alternatively, directly via SQL, e.g.:
-- INSERT INTO spieler (name) VALUES ('Anna'), ('Ben');


-- =========================================================
-- 2) TABLE: karte (value cards / balance / bulk discount)
-- =========================================================
CREATE TABLE IF NOT EXISTS karte (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    guthaben NUMERIC(10,2) NOT NULL,
    aktiv BOOLEAN DEFAULT TRUE NOT NULL,
    bezahlt_von TEXT NOT NULL,
    anfangsguthaben NUMERIC(10,2),   -- how much balance was loaded on activation
    bezahlt_betrag NUMERIC(10,2),    -- how much was actually paid for it
    faktor NUMERIC                   -- bezahlt_betrag / anfangsguthaben, used for final settlement
);


-- =========================================================
-- 3) TABLE: spiele (individual play sessions / cost splitting)
-- =========================================================
CREATE TABLE IF NOT EXISTS spiele (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    spieler TEXT NOT NULL,
    einheiten INT NOT NULL,
    kosten NUMERIC(10,2) NOT NULL,
    eingetragen_von TEXT NOT NULL,
    eingetragen_am TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    gespielt_am DATE NOT NULL,
    gespielt_uhrzeit TIME,            -- start time, used for the pricing tier (preisliste.py)
    ermaessigt BOOLEAN DEFAULT FALSE NOT NULL,
    karte_id INT REFERENCES karte(id), -- which card was active when this was logged (for reactivation)
    abgerechnet BOOLEAN DEFAULT FALSE NOT NULL
);


-- =========================================================
-- 4) TABLE: abrechnung (who owes whom what, per card)
-- =========================================================
CREATE TABLE IF NOT EXISTS abrechnung (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    spieler TEXT NOT NULL,
    betrag NUMERIC(10,2) NOT NULL,
    karte_id INT REFERENCES karte(id) ON DELETE CASCADE
);


-- =========================================================
-- 5) TABLE: spielergebnisse (sports results)
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
-- PERMISSIONS (Row Level Security)
-- =========================================================
-- RLS is enabled (Supabase flags tables without it as "Critical issue:
-- Table publicly accessible"), but attached to an open policy for the
-- "anon" role - access behaves identically to disabled RLS, since the app
-- only uses a single shared API key rather than individual Supabase
-- logins anyway (actual access control happens via the password inside
-- the app itself, see auth.py). Genuine row-level protection would
-- require individual logins (Supabase Auth) with correspondingly tighter
-- policies.
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
-- Verification: should show 5 tables with the expected columns
-- =========================================================
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name IN ('spieler', 'karte', 'spiele', 'abrechnung', 'spielergebnisse')
-- ORDER BY table_name, ordinal_position;
```

---

## Setup Step 3: Local Development Environment

### 3.1 Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-folder>
```

### 3.2 Set Up the Python Environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3.3 Configure Secrets

```bash
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then open `.streamlit/secrets.toml` and fill in real values:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-publishable-or-anon-key"

# Optional but recommended: shared password for the app
APP_PASSWORD = "a-secure-password"
```

> ⚠️ **Never** commit `.streamlit/secrets.toml`! It's already listed in
> `.gitignore`. If `APP_PASSWORD` is missing entirely, the app runs
> without password protection (with a clear warning shown in the UI).

### 3.4 Run the App Locally

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`.

### 3.5 Optional: Dev Container / GitHub Codespaces

The repository includes a `devcontainer.json` for VS Code Dev Containers
and GitHub Codespaces, allowing a fully pre-configured development
environment to be launched directly in the browser without any local
installation.

---

## Setup Step 4: Deploy to Streamlit Community Cloud

1. Push the repository to GitHub (without `secrets.toml`!).
2. Log in at [share.streamlit.io](https://share.streamlit.io), choose
   **New app**, and select the repository with `app.py` as the main file.
3. Under **Advanced settings → Secrets**, enter the same values as in
   `.streamlit/secrets.toml` (TOML format, see above).
4. Deploy. On every push to the connected branch, Streamlit Community
   Cloud automatically redeploys the app.

---

## Configuration

### Adjusting Prices

If the facility's price list changes, it is sufficient to edit **only**
`preise.py` — the two price-tier lists for weekdays (regular and
discounted) as well as weekends/holidays. No other file needs to be
touched.

```python
# preise.py
PREISSTUFEN_WOCHENTAG = [
    (time(8, 0), time(15, 0), 19.00),
    # ... further time tiers
]
```

The calculation logic (`preisliste.py`) automatically determines which
price tier applies for a given date/time, including automatic detection of
public holidays in Berlin (movable holidays are calculated using the
Gaussian Easter algorithm — no external dependency required). For a
different region's holiday calendar, the list in `preisliste.py`
(`_berliner_feiertage`) would need to be adjusted.

### Card Discount / Bulk-Purchase Bonus

Some facilities offer a discount when topping up a value card (e.g. "pay X
to get Y credited"). When activating a new card, the app optionally asks
for this and stores `anfangsguthaben`, `bezahlt_betrag`, and the resulting
`faktor` in the database. Importantly, this discount factor does **not**
affect the ongoing per-session balance deduction (which happens at the
full list price, matching how most facilities themselves handle it) — it
only affects the **final settlement**, where the amount actually paid is
distributed among players proportionally to their usage.

### Managing Players

Players are managed exclusively through the app's **👥 Player Management**
page (add, deactivate/activate, delete) — not in the code. Deactivated
players disappear from selection lists for new entries but remain visible
in statistics (for matches already played).

### Reactivating an Accidentally-Settled Card

If a faulty entry pushes the balance below zero, the app automatically
settles the card and deactivates it — corrections are no longer possible
through the normal interface afterward, since every editing feature only
operates on the currently active card. Under **💰 Billing & Balance →
🗑️ Correct/Delete Faulty Entry or Card → ↩️ Reactivate a Recently Settled
Card**, one of the last five completed cards can be switched back to
active: the premature settlement gets deleted, its associated sessions
become editable again, and the faulty entry can be corrected/deleted
through the normal flow. This is made possible by the `spiele.karte_id`
column, which records which card was active at the time each session was
logged.

### Password Protection

A single, shared password for the entire app, stored as `APP_PASSWORD` in
the secrets (see above). There is no per-person access control — sufficient
for a small, trusted group, but not a substitute for a proper multi-user
login system.

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover the core logic (cost calculation, price tiers, holiday
calculation, settlement distribution, statistics functions) and use a fake
module in place of a real database connection — so no real Supabase
credentials are needed to run the tests.

---

## Database Schema Reference

| Table | Purpose | Key Columns |
|---|---|---|
| `spieler` | Player management | `name`, `aktiv` |
| `karte` | Current/past value cards | `guthaben`, `bezahlt_von`, `anfangsguthaben`, `bezahlt_betrag`, `faktor`, `aktiv` |
| `spiele` | Individual play sessions (cost splitting) | `spieler`, `einheiten`, `kosten`, `gespielt_am`, `gespielt_uhrzeit`, `ermaessigt`, `karte_id`, `abgerechnet` |
| `abrechnung` | Final settlement history per card | `spieler`, `betrag`, `karte_id` |
| `spielergebnisse` | Sports results | `gewinner`, `verlierer`, `satz_gewinner`, `satz_verlierer` |

All tables use text fields for player names (no foreign key to
`spieler.id`) — deleting a player in Player Management therefore only
removes them from future selection lists; historical entries remain
unchanged.

---

## Troubleshooting

**"Oh no. Error running app." with no obvious cause**
Checking the full logs usually helps (Streamlit Cloud: app menu → *Manage
app* → *Logs*) — the short error shown in the UI rarely reveals the actual
cause.

**Supabase access fails even though credentials are correct**
Usually a permissions issue: either Row Level Security is enabled without a
matching policy, or the `anon`/`authenticated` roles are missing base
privileges on the tables (e.g. because "Automatically expose new tables"
was disabled when the project was created). If needed:
```sql
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
```

**Supabase shows "Table publicly accessible" / "rls_disabled_in_public"**
Supabase's built-in security linter reports this for any table without Row
Level Security enabled. The setup script already enables RLS by default
with a matching policy (see [Security Notes](#security-notes)) — if the
warning still appears, a table was likely created or modified manually
afterward. To fix, e.g. for the `karte` table:
```sql
ALTER TABLE karte ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "app_zugriff" ON karte;
CREATE POLICY "app_zugriff" ON karte FOR ALL TO anon USING (true) WITH CHECK (true);
```
(repeat for any other affected tables).

**Streamlit version causes errors**
`requirements.txt` deliberately pins `streamlit>=1.51` (the `width`
parameter for `st.plotly_chart` only exists from this version onward). If
problems occur with newer versions, pin an exact, tested version
(`streamlit==x.y.z`) instead of an open range.

**Timestamps look "wrong" (off by one or two hours)**
The application server runs in UTC. Timestamps are explicitly stored as
UTC and only converted to `Europe/Berlin` for display (`zeit_utils.py`),
including correct daylight-saving handling via Python's `zoneinfo`.

---

## Security Notes

- This app does **not** provide individual user logins, only a single
  shared password for a small, trusted group. For a larger or less
  trusted user base, a proper auth system (e.g. Supabase Auth) would be
  more appropriate.
- Row Level Security is enabled, but attached to a deliberately open
  policy for the `anon` role (see above) — this formally satisfies
  Supabase's security checks but doesn't change the actual protection: the
  Supabase API key used still grants full read/write access to all
  tables. Treat this key as sensitive accordingly (never commit it to a
  public repository, respect `.gitignore`). Genuine row-level protection
  would require individual Supabase logins with correspondingly tighter
  policies.
- It is recommended to use the modern **Publishable Key** rather than the
  classic `service_role`/Secret Key — the latter bypasses RLS entirely and
  should never be used in a client application, even when the policy is
  open anyway.

---

## License

Private project. Add a license as needed (e.g. MIT) if the repository is
to be shared publicly.
