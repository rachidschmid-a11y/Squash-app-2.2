-- ============================================================
-- Migration: Ermäßigter Tarif (Schüler/Studenten)
-- Im Supabase SQL-Editor ausführen. Gefahrlos mehrfach ausführbar.
-- ============================================================

ALTER TABLE public.spiele
    ADD COLUMN IF NOT EXISTS ermaessigt BOOLEAN DEFAULT FALSE NOT NULL;
