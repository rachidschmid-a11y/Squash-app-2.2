-- ============================================================
-- Migration: Kartenreaktivierung
-- Im Supabase SQL-Editor ausführen. Gefahrlos mehrfach ausführbar.
-- ============================================================

-- Neue Spalte: welche Karte war aktiv, als diese Session eingetragen wurde.
-- Nullable, damit alte Einträge ohne diese Zuordnung gültig bleiben.
-- Wird für die neue "Karte reaktivieren"-Funktion gebraucht, damit die App
-- zuverlässig weiß, welche (evtl. schon abgerechneten) Spiele zu einer
-- bestimmten Karte gehörten.
ALTER TABLE public.spiele
    ADD COLUMN IF NOT EXISTS karte_id INT REFERENCES public.karte(id);
