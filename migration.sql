-- ============================================================
-- Migration: Spielerverwaltung per Datenbank + Vergünstigung pro Karte
-- Im Supabase SQL-Editor ausführen (Projekt -> SQL Editor -> New query).
-- ============================================================

-- 1) Neue Tabelle für die Spielerverwaltung
create table if not exists public.spieler (
    id bigint generated always as identity primary key,
    name text not null unique,
    aktiv boolean not null default true,
    erstellt_am timestamptz not null default now()
);

-- Beispiel-Spieler zum Start - Namen bei Bedarf anpassen/ergänzen.
-- "on conflict do nothing" macht das Skript gefahrlos mehrfach ausführbar.
insert into public.spieler (name) values
    ('Anna'),
    ('Ben'),
    ('Clara'),
    ('David'),
    ('Emma')
on conflict (name) do nothing;

-- 2) karte-Tabelle um die Vergünstigungs-Felder erweitern
alter table public.karte
    add column if not exists anfangsguthaben numeric,
    add column if not exists bezahlt_betrag numeric,
    add column if not exists faktor numeric;

-- Bestehende Karten (alte, feste Logik: 200 € bezahlt für 250 € Guthaben)
-- rückwirkend befüllen, damit Session-Kosten und Abrechnung für sie auch
-- weiterhin korrekt berechnet werden. Läuft nur auf Zeilen, die noch keine
-- Werte haben - mehrfaches Ausführen ist ungefährlich.
update public.karte
set anfangsguthaben = coalesce(anfangsguthaben, 250),
    bezahlt_betrag = coalesce(bezahlt_betrag, 200),
    faktor = coalesce(faktor, 200.0 / 250.0)
where anfangsguthaben is null or bezahlt_betrag is null or faktor is null;

-- Optional zur Kontrolle:
-- select * from public.spieler order by name;
-- select id, aktiv, guthaben, anfangsguthaben, bezahlt_betrag, faktor from public.karte;
