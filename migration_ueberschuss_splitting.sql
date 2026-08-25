-- ============================================================
-- Migration: Session-Splitting zwischen Karten (Überschuss-Verrechnung)
-- Im Supabase SQL-Editor ausführen. Gefahrlos mehrfach ausführbar.
-- ============================================================

-- Der bisherige Fremdschlüssel spiele.karte_id -> karte.id hatte kein
-- ON DELETE-Verhalten festgelegt (Standard: RESTRICT). Das hätte "Aktive
-- Karte stornieren" scheitern lassen, sobald noch offene (nicht
-- abgerechnete) Spiele an der Karte hingen. Jetzt: beim Löschen einer
-- Karte werden zugehörige Spiele-Zeilen automatisch "herrenlos"
-- (karte_id = NULL) statt die Löschung zu blockieren - genau der gleiche
-- Zustand, den auch ein Überschuss aus einer zu teuren Session bekommt,
-- und der beim nächsten "Karte aktivieren" automatisch übernommen wird.
ALTER TABLE public.spiele
    DROP CONSTRAINT IF EXISTS spiele_karte_id_fkey;

ALTER TABLE public.spiele
    ADD CONSTRAINT spiele_karte_id_fkey
    FOREIGN KEY (karte_id) REFERENCES public.karte(id) ON DELETE SET NULL;
