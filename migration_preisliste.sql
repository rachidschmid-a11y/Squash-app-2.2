-- ============================================================
-- Migration: Zeitabhängige Preisliste
-- Im Supabase SQL-Editor ausführen (Projekt -> SQL Editor -> New query).
-- Gefahrlos mehrfach ausführbar.
-- ============================================================

-- Neue Spalte für die Start-Uhrzeit jeder Spiel-Session (wird für die
-- Preisstufe aus preisliste.py gebraucht). Nullable, damit alte Einträge
-- ohne Uhrzeit gültig bleiben - für die gilt weiterhin der Preis, der beim
-- Speichern damals berechnet wurde (deren "kosten"-Wert ändert sich nicht
-- rückwirkend).
alter table public.spiele
    add column if not exists gespielt_uhrzeit time;
