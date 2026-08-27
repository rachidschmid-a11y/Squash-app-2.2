import streamlit as st
import pandas as pd
from datetime import date, datetime
import config as cfg
import database as db
import calculations as calc
import visualizations as vis
import export_utils
import preisliste
import zeit_utils

@st.dialog("Karte wirklich löschen?")
def confirm_delete_karte_dialog(karte_id):
    st.warning(
        "⚠️ Diese Aktion kann nicht rückgängig gemacht werden. "
        "Das aktuelle Kartenguthaben geht dabei verloren."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, endgültig löschen", type="primary", width="stretch"):
            if db.delete_karte(karte_id):
                st.success("Die aktive Karte wurde erfolgreich gelöscht!")
            st.rerun()
    with col2:
        if st.button("Abbrechen", width="stretch"):
            st.rerun()

@st.dialog("Eintrag wirklich löschen?")
def confirm_delete_spiel_dialog(eintrag, karte):
    ist_abgerechnet = eintrag.get("abgerechnet", False)
    st.warning(f"Eintrag ID {eintrag['id']} ({eintrag.get('kosten', 0):.2f} €) wird gelöscht.")

    guthaben_gutschreiben = False
    if ist_abgerechnet:
        st.info(
            "Dieser Eintrag wurde bereits abgerechnet (gehörte zu einer inzwischen "
            "abgeschlossenen Karte). Die damalige Abrechnung wird dadurch NICHT "
            "automatisch korrigiert - nur der Eintrag selbst wird entfernt."
        )
        if karte:
            guthaben_gutschreiben = st.checkbox(
                f"Betrag zusätzlich der aktuell aktiven Karte (ID {karte['id']}) gutschreiben",
                value=False,
                key=f"gutschrift_{eintrag['id']}",
            )
        else:
            st.caption("Keine aktive Karte vorhanden, daher keine Gutschrift möglich.")
    else:
        st.caption("Der Betrag wird automatisch dem aktuellen Kartenguthaben gutgeschrieben.")
        guthaben_gutschreiben = karte is not None

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, löschen", type="primary", width="stretch"):
            if guthaben_gutschreiben and karte:
                alter_guthaben = karte["guthaben"]
                neues_guthaben = alter_guthaben + eintrag.get("kosten", 0)
                db.update_karte_guthaben(karte["id"], alter_guthaben, neues_guthaben)
            if db.delete_spiel_by_id(eintrag["id"]):
                st.success(f"Eintrag {eintrag['id']} erfolgreich gelöscht!")
            st.rerun()
    with col2:
        if st.button("Abbrechen", width="stretch"):
            st.rerun()

@st.dialog("Karte wirklich reaktivieren?")
def confirm_reaktiviere_karte_dialog(karte_zum_reaktivieren, aktuelle_karte):
    st.warning(
        f"Karte ID {karte_zum_reaktivieren['id']} (bezahlt von "
        f"{karte_zum_reaktivieren.get('bezahlt_von', 'Unbekannt')}, aktuelles Guthaben "
        f"{karte_zum_reaktivieren['guthaben']:.2f} €) wird wieder aktiv geschaltet."
    )
    st.markdown(
        "- Die automatisch erstellte Abrechnung für diese Karte wird gelöscht.\n"
        "- Die während ihrer Laufzeit eingetragenen, bereits abgerechneten Spiele "
        "werden wieder bearbeitbar (erscheinen wieder in der normalen Übersicht)."
    )
    if aktuelle_karte and aktuelle_karte["id"] != karte_zum_reaktivieren["id"]:
        st.warning(
            f"⚠️ Die aktuell aktive Karte (ID {aktuelle_karte['id']}, bezahlt von "
            f"{aktuelle_karte.get('bezahlt_von', 'Unbekannt')}) wird dabei deaktiviert. "
            f"Ihre Daten bleiben erhalten - bereits darauf eingetragene Spiele zählen "
            f"automatisch zur nächsten aktivierten Karte."
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, reaktivieren", type="primary", width="stretch"):
            if aktuelle_karte and aktuelle_karte["id"] != karte_zum_reaktivieren["id"]:
                db.set_karte_aktiv(aktuelle_karte["id"], False)
            db.delete_abrechnung_fuer_karte(karte_zum_reaktivieren["id"])
            db.reaktiviere_spiele_fuer_karte(karte_zum_reaktivieren["id"])
            if db.set_karte_aktiv(karte_zum_reaktivieren["id"], True):
                st.success(f"Karte ID {karte_zum_reaktivieren['id']} wurde reaktiviert.")
            st.rerun()
    with col2:
        if st.button("Abbrechen", width="stretch"):
            st.rerun()

def render_abrechnung_page():
    st.title("🏸 Squash Abrechnung & Guthaben")

    aktive_spieler = db.get_aktive_spieler_namen()
    if not aktive_spieler:
        st.warning(
            "Es sind noch keine aktiven Spieler hinterlegt. Bitte zuerst unter "
            "'👥 Spielerverwaltung' Spieler anlegen."
        )

    with st.expander("➕ Neue Karte starten"):
        st.markdown("#### 📋 Letzte Abrechnung (Historie)")
        letzte_schulden, alter_zahler = db.get_letzte_abrechnung()

        if letzte_schulden:
            st.caption(f"Zur Erinnerung: Das waren die Ausgleichszahlungen für die letzte Karte von **{alter_zahler}**:")
            summe_kontrolle = 0.0
            for eintrag in letzte_schulden:
                summe_kontrolle += eintrag["betrag"]
                if eintrag['spieler'] != alter_zahler:
                    st.write(f"• **{eintrag['spieler']}** → **{eintrag['betrag']:.2f} €** an {alter_zahler}")
                else:
                    st.write(f"• *{eintrag['spieler']} (Zahler der Karte)* → **{eintrag['betrag']:.2f} €** an sich selbst")
            st.caption(f"Σ Summe zur Kontrolle: **{summe_kontrolle:.2f} €**")

            letzte_karte_obj = db.get_letzte_inaktive_karte()
            spiele_fuer_abrechnung = db.get_spiele_fuer_karte(letzte_karte_obj["id"]) if letzte_karte_obj else []
            if spiele_fuer_abrechnung:
                df_spiele_abrechnung = calc.format_dataframe(pd.DataFrame(spiele_fuer_abrechnung))
                st.download_button(
                    "📥 Abrechnung als CSV exportieren (alle berücksichtigten Spiele)",
                    data=export_utils.to_csv_bytes(df_spiele_abrechnung),
                    file_name=f"abrechnung_spiele_{alter_zahler}_{date.today().isoformat()}.csv",
                    mime="text/csv",
                    key="dl_abrechnung_historie",
                )
        else:
            st.info("Keine historischen Abrechnungsdaten gefunden.")

        st.divider()

        st.markdown("#### Neue Karte aktivieren")

        if not aktive_spieler:
            st.info("Erst Spieler anlegen, um eine Karte zu starten.")
        else:
            bezahlt_von = st.selectbox("Wer hat die Karte bezahlt?", aktive_spieler, key="card_payer")

            hat_verguenstigung = st.checkbox(
                "Gibt es eine Vergünstigung für diese Karte?",
                key="card_discount_checkbox",
            )

            if hat_verguenstigung:
                col_a, col_b = st.columns(2)
                with col_a:
                    bezahlt_betrag = st.number_input(
                        "Wie viel wurde tatsächlich bezahlt (€)?",
                        min_value=0.0,
                        value=cfg.STANDARD_BEZAHLT_BETRAG,
                        step=1.0,
                        key="card_bezahlt_betrag",
                    )
                with col_b:
                    anfangsguthaben_eingabe = st.number_input(
                        "Wie viel Guthaben wird auf die Karte geladen (€)?",
                        min_value=0.01,
                        value=cfg.STANDARD_ANFANGSGUTHABEN_MIT_VERGUENSTIGUNG,
                        step=1.0,
                        key="card_anfangsguthaben",
                    )
                st.caption(
                    f"→ Rabatt-Faktor: {bezahlt_betrag / anfangsguthaben_eingabe:.3f} "
                    f"(bezahlt / aufgeladen)"
                )
            else:
                anfangsguthaben_eingabe = st.number_input(
                    "Kartenwert / aufgeladenes Guthaben (€)",
                    min_value=0.01,
                    value=cfg.STANDARD_ANFANGSGUTHABEN,
                    step=1.0,
                    key="card_wert_ohne_rabatt",
                )
                bezahlt_betrag = anfangsguthaben_eingabe

            offene_ueberschuss = db.get_offene_ueberschuss_spiele()
            summe_ueberschuss = round(sum(row["kosten"] for row in offene_ueberschuss), 2)
            if offene_ueberschuss:
                verursacher = ", ".join(sorted({row["spieler"] for row in offene_ueberschuss}))
                st.warning(
                    f"⚠️ Es liegen noch {summe_ueberschuss:.2f} € offener Überschuss von der "
                    f"letzten Karte vor (verursacht von: {verursacher}). Dieser Betrag wird beim "
                    f"Aktivieren automatisch von dieser neuen Karte abgezogen und bleibt in der "
                    f"Spiele-Übersicht/Kostenstatistik diesen Personen zugeordnet."
                )
                verbleibendes_startguthaben = round(anfangsguthaben_eingabe - summe_ueberschuss, 2)
                vis.render_split_balken(
                    verbleibendes_startguthaben,
                    summe_ueberschuss,
                    label_gedeckt="Verbleibt für neue Sessions",
                    label_neu="Übernommener Überschuss",
                )

            if st.button("Karte aktivieren"):
                # Kein pauschaler Übertrag eines negativen Endstands mehr: Die alte
                # Karte wird nur noch auf ihre EIGENEN Einträge abgerechnet. Ein
                # etwaiger Überschuss (Session größer als das verbleibende
                # Guthaben) wurde bereits beim Eintragen sauber abgespalten und
                # verursachergerecht auf die beteiligten Spieler verteilt (siehe
                # speichern_logik) - der wird hier jetzt übernommen, alles
                # andere NICHT nochmal abgezogen.
                start_guthaben = round(anfangsguthaben_eingabe - summe_ueberschuss, 2)
                faktor = round(bezahlt_betrag / anfangsguthaben_eingabe, 6)

                if db.insert_karte({
                    "guthaben": start_guthaben,
                    "aktiv": True,
                    "bezahlt_von": bezahlt_von,
                    "anfangsguthaben": anfangsguthaben_eingabe,
                    "bezahlt_betrag": bezahlt_betrag,
                    "faktor": faktor,
                }):
                    if offene_ueberschuss:
                        neue_karte = db.get_karte()
                        if neue_karte:
                            db.claim_offene_ueberschuss_spiele(neue_karte["id"])
                        st.success(
                            f"Neue Karte gestartet! Bezahlt von: {bezahlt_von}. "
                            f"{summe_ueberschuss:.2f} € Überschuss wurden direkt abgezogen "
                            f"(verursacht von: {verursacher})."
                        )
                    else:
                        st.success(f"Neue Karte gestartet! Bezahlt von: {bezahlt_von}")
                    st.rerun()

    st.divider()
    st.subheader("Neues Spiel (Session) eintragen")

    if not aktive_spieler:
        st.info("Erst Spieler unter '👥 Spielerverwaltung' anlegen, um ein Spiel einzutragen.")
    else:
        jetzt_berlin = datetime.now(zeit_utils.BERLIN_TZ)

        col1, col2 = st.columns(2)
        with col1:
            eingetragen_von = st.selectbox("Eingetragen von", aktive_spieler, key="fin_input_by")
        with col2:
            gespielt_am = st.date_input("Gespielt am", jetzt_berlin.date(), key="fin_date")

        ist_wochenende = preisliste.ist_wochenend_tarif(gespielt_am)
        ermaessigt = False
        if ist_wochenende:
            st.caption("Am Wochenende/Feiertag gibt es laut Preisliste keinen ermäßigten Tarif.")
        else:
            ermaessigt = st.checkbox(
                "Ermäßigten Tarif (Schüler/Studenten) abrechnen?",
                key="fin_ermaessigt",
            )

        kombi_stufen = preisliste.beide_preise_fuer_datum(gespielt_am)
        zeitraum_optionen = {}
        for start, ende, preis_regulaer, preis_erm in kombi_stufen:
            zeit_label = f"{start.strftime('%H:%M')}–{ende.strftime('%H:%M')} Uhr"
            if preis_regulaer == preis_erm:
                # Wochenende/Feiertag: kein ermäßigter Tarif verfügbar
                label = f"{zeit_label} ({preis_regulaer:.2f} €/Einheit)"
            else:
                label = f"{zeit_label} — {preis_regulaer:.2f} € (ermäßigt **{preis_erm:.2f} €**)"
            preis_gewaehlt = preis_erm if ermaessigt else preis_regulaer
            zeitraum_optionen[label] = (start, preis_gewaehlt)
        zeitraum_labels = list(zeitraum_optionen.keys())

        # Passenden Zeitraum vorauswählen, wenn heute gespielt wurde
        default_index = 0
        if gespielt_am == jetzt_berlin.date():
            for i, (start, ende, _preis_reg, _preis_erm) in enumerate(kombi_stufen):
                if start <= jetzt_berlin.time() < ende:
                    default_index = i
                    break

        # Eigener Key je nachdem ob Wochentag/Wochenende, damit ein
        # Datumswechsel zwischen den beiden Tarif-Sets nicht zu einer
        # ungültigen alten Auswahl führt. Das Umschalten der
        # "ermäßigt"-Checkbox ändert die Label-Texte nicht (nur den intern
        # zugeordneten Preis), braucht also keinen eigenen Key.
        zeitraum_key = f"fin_zeitraum_{'we' if ist_wochenende else 'wt'}"
        auswahl_label = st.radio(
            "In welchem Zeitraum wurde gespielt?",
            zeitraum_labels,
            index=default_index,
            key=zeitraum_key,
        )
        uhrzeit, preis_pro_einheit = zeitraum_optionen[auswahl_label]

        st.caption(
            f"→ Wird vom Guthaben abgebucht: {preis_pro_einheit:.2f} € pro Einheit "
            f"(ohne Kartenrabatt - der wirkt erst in der Endabrechnung)"
        )

        # st.multiselect statt einer Checkbox-Spalte pro Spieler: bei vielen
        # Spielern auf dem Handy sonst schnell zu eng nebeneinander (siehe
        # Übergabe-Notiz zur mobilen Darstellung). Liefert wie zuvor eine
        # einfache Liste von Namen.
        auswahl = st.multiselect("Mitspieler auswählen", aktive_spieler, key="fin_mitspieler")

        einheiten = st.number_input("Einheiten (45 Minuten)", min_value=1, max_value=20, value=1, key="fin_units")

        if auswahl:
            # --- Vorschau vor dem Speichern ------------------------------
            # Reine Anzeige-Berechnung, damit Fehleingaben (falsche
            # Mitspieler/Einheiten/Zeitraum) VOR dem eigentlichen Buchen
            # auffallen. Die tatsächliche, cent-exakte Aufteilung inkl.
            # Überschuss-Splitting passiert weiterhin ausschließlich in
            # calc.speichern_logik() - hier wird sie nur näherungsweise
            # nachgebildet (gleiche min()/max()-Formel wie dort), damit
            # nichts an der echten Buchungslogik geändert werden musste.
            st.markdown("**Vorschau:**")
            gesamtpreis = round(einheiten * preis_pro_einheit, 2)
            aktuelle_karte_vorschau = db.get_karte()
            aktuelles_guthaben = aktuelle_karte_vorschau["guthaben"] if aktuelle_karte_vorschau else 0.0

            p1, p2, p3 = st.columns(3)
            p1.metric("Spieler", len(auswahl))
            p2.metric("Gesamtpreis", f"{gesamtpreis:.2f} €")
            p3.metric("Preis/Spieler (ca.)", f"{gesamtpreis / len(auswahl):.2f} €")

            if aktuelle_karte_vorschau:
                kosten_gedeckt = round(min(gesamtpreis, max(aktuelles_guthaben, 0)), 2)
                kosten_ueberschuss = round(gesamtpreis - kosten_gedeckt, 2)
                if kosten_ueberschuss > 0:
                    vis.render_split_balken(kosten_gedeckt, kosten_ueberschuss)
                else:
                    neues_guthaben_vorschau = round(aktuelles_guthaben - gesamtpreis, 2)
                    st.caption(
                        f"Guthaben: {aktuelles_guthaben:.2f} € → **{neues_guthaben_vorschau:.2f} €** nach dieser Session"
                    )
            else:
                st.warning("Keine aktive Karte vorhanden - die Session kann nicht gebucht werden.")

        if st.button("💾 Session speichern"):
            if len(auswahl) == 0:
                st.warning("Bitte Spieler auswählen")
            else:
                status, msg = calc.speichern_logik(auswahl, einheiten, eingetragen_von, gespielt_am, uhrzeit, ermaessigt)
                if status == "success":
                    st.success(msg)
                elif status == "warning":
                    st.info(msg)
                else:
                    st.error(msg)
                if status != "error":
                    st.rerun()

    st.divider()
    st.subheader("Aktueller Stand")
    karte = db.get_karte()
    if karte:
        vis.render_karten_uebersicht(karte)
        st.caption(f"Diese Karte wurde bezahlt von: **{karte.get('bezahlt_von', 'Unbekannt')}**")
        if karte.get("bezahlt_betrag") is not None and karte.get("anfangsguthaben") is not None:
            st.caption(
                f"Bezahlt: {karte['bezahlt_betrag']:.2f} € für {karte['anfangsguthaben']:.2f} € Guthaben "
                f"(Faktor {karte.get('faktor', 1.0):.3f})"
            )

        # Funktion zur nachträglichen Korrektur des Karten-Zahlers bei Tippfehlern
        if aktive_spieler:
            with st.expander("✏️ Falschen Zahler eingetragen? Name korrigieren"):
                aktueller_zahler = karte.get("bezahlt_von")
                default_index = aktive_spieler.index(aktueller_zahler) if aktueller_zahler in aktive_spieler else 0

                neuer_zahler = st.selectbox(
                    "Wer hat die Karte wirklich bezahlt?",
                    aktive_spieler,
                    index=default_index,
                    key="correct_card_payer"
                )

                if st.button("Zahler aktualisieren", key="btn_correct_payer"):
                    if neuer_zahler == aktueller_zahler:
                        st.info("Dieser Spieler ist bereits als Zahler eingetragen.")
                    else:
                        if db.update_karte_zahler(karte["id"], neuer_zahler):
                            st.success(f"Zahler erfolgreich auf **{neuer_zahler}** geändert!")
                            st.rerun()
    else:
        st.warning("Keine aktive Karte vorhanden. Bitte neue Karte starten.")

    spiele = db.get_spiele()
    if spiele:
        if any(row.get("einheiten") == 0 for row in spiele):
            st.caption(
                "ℹ️ Zeilen mit 0 Einheiten sind keine eigenen Sessions, sondern "
                "Überschuss-Anteile aus einer Session, die das Guthaben einer Karte "
                "überschritten hat (siehe Warnhinweis oben bei 'Neue Karte aktivieren')."
            )
        df_display = calc.format_dataframe(pd.DataFrame(spiele))
        st.dataframe(df_display, width="stretch")
        st.download_button(
            "📥 Spiele-Übersicht als CSV exportieren",
            data=export_utils.to_csv_bytes(df_display),
            file_name=f"spiele_kosten_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="dl_spiele_kosten",
        )
    else:
        st.info("Noch keine Spiele auf der aktuellen Karte vorhanden")

    st.divider()
    with st.expander("🗑️ Fehlerhaften Eintrag oder Karte löschen"):
        st.markdown("#### 🏸 Spiel-Session löschen")
        zeige_abgerechnete = st.checkbox(
            "Auch bereits abgerechnete Einträge anzeigen (z.B. um einen Fehleintrag zu "
            "finden, der durch eine automatische Abrechnung aus der Übersicht verschwunden ist)",
            key="zeige_abgerechnete_spiele",
        )
        spiele_zum_loeschen = db.get_alle_spiele(limit=50) if zeige_abgerechnete else spiele

        if spiele_zum_loeschen:
            df_raw = pd.DataFrame(spiele_zum_loeschen)
            optionen = {
                row["id"]: (
                    f"ID {row['id']} | {pd.to_datetime(row['gespielt_am']).strftime('%d.%m.%Y')} | "
                    f"{row['spieler']} | {row['kosten']:.2f} €"
                    + (" | ✅ abgerechnet" if row.get("abgerechnet") else "")
                )
                for _, row in df_raw.iterrows()
            }
            auswahl_id = st.selectbox("Welcher Eintrag soll gelöscht werden?", list(optionen.keys()), format_func=lambda x: optionen[x], key="del_fin_id")

            if st.button("Eintrag löschen"):
                eintrag = next((s for s in spiele_zum_loeschen if s["id"] == auswahl_id), None)
                if eintrag:
                    confirm_delete_spiel_dialog(eintrag, karte)
        else:
            st.info("Keine Einträge vorhanden, die gelöscht werden könnten.")

        st.divider()
        st.markdown("#### ⚠️ Aktive Karte stornieren")
        if karte:
            st.warning("Achtung: Das Löschen der aktiven Karte setzt das aktuelle Kartenguthaben zurück. Offene Sessions bleiben als 'nicht abgerechnet' bestehen und zählen für die nächste aktivierte Karte.")
            if st.button("🔴 Aktive Karte unwiderruflich löschen", key="btn_delete_active_card"):
                confirm_delete_karte_dialog(karte["id"])
        else:
            st.info("Keine aktive Karte vorhanden, die gelöscht werden könnte.")

        st.divider()
        st.markdown("#### ↩️ Kürzlich abgerechnete Karte reaktivieren")
        st.caption(
            "Falls eine Karte versehentlich zu früh automatisch abgerechnet wurde "
            "(z.B. durch einen Fehleintrag, der das Guthaben ins Minus gebracht hat), "
            "kann sie hier wieder aktiv geschaltet werden."
        )
        inaktive_karten = db.get_inaktive_karten(limit=5)
        if inaktive_karten:
            reaktivieren_optionen = {
                k["id"]: f"ID {k['id']} | bezahlt von {k.get('bezahlt_von', 'Unbekannt')} | Guthaben {k['guthaben']:.2f} €"
                for k in inaktive_karten
            }
            reaktivieren_auswahl_id = st.selectbox(
                "Welche Karte reaktivieren?",
                list(reaktivieren_optionen.keys()),
                format_func=lambda x: reaktivieren_optionen[x],
                key="reaktivieren_karte_id",
            )
            if st.button("Karte reaktivieren"):
                karte_zum_reaktivieren = next(k for k in inaktive_karten if k["id"] == reaktivieren_auswahl_id)
                confirm_reaktiviere_karte_dialog(karte_zum_reaktivieren, karte)
        else:
            st.info("Keine abgeschlossenen Karten vorhanden.")

    st.divider()
    st.subheader("Kostenstatistik")
    if spiele:
        df_stats = pd.DataFrame(spiele).groupby("spieler")["kosten"].sum().reset_index()
        aktuelle_summe = df_stats["kosten"].sum()

        if karte and karte.get("anfangsguthaben") is not None:
            bezahlt_hinweis = (
                f" (dafür bezahlt: {karte['bezahlt_betrag']:.2f} €)"
                if karte.get("bezahlt_betrag") is not None else ""
            )
            st.caption(
                f"Bezieht sich auf die aktuelle Karte: bisher {aktuelle_summe:.2f} € von "
                f"{karte['anfangsguthaben']:.2f} € Guthaben verbraucht{bezahlt_hinweis}. "
                f"Die Kosten pro Session werden zum vollen Guthaben-Wert abgerechnet, "
                f"nicht zum vergünstigten bezahlten Betrag - der zählt erst in der Endabrechnung."
            )

        c1, c2 = st.columns(2)
        with c1:
            vis.plot_costs_bar(df_stats)
        with c2:
            vis.plot_costs_pie(df_stats)
        st.download_button(
            "📥 Kostenstatistik als CSV exportieren",
            data=export_utils.to_csv_bytes(df_stats),
            file_name=f"kostenstatistik_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="dl_kostenstatistik",
        )
    else:
        letzte_karte_obj = db.get_letzte_inaktive_karte()
        spiele_letzte_karte = db.get_spiele_fuer_karte(letzte_karte_obj["id"]) if letzte_karte_obj else []
        if spiele_letzte_karte:
            st.caption(
                f"Auf der aktuellen Karte wurde noch nicht gespielt. Hier die Kostenstatistik "
                f"der zuletzt abgerechneten Karte (bezahlt von "
                f"{letzte_karte_obj.get('bezahlt_von', 'Unbekannt')}):"
            )
            df_stats_letzte = pd.DataFrame(spiele_letzte_karte).groupby("spieler")["kosten"].sum().reset_index()

            if letzte_karte_obj.get("anfangsguthaben") is not None:
                bezahlt_hinweis = (
                    f" (dafür bezahlt: {letzte_karte_obj['bezahlt_betrag']:.2f} €)"
                    if letzte_karte_obj.get("bezahlt_betrag") is not None else ""
                )
                st.caption(
                    f"Gesamt {df_stats_letzte['kosten'].sum():.2f} € von "
                    f"{letzte_karte_obj['anfangsguthaben']:.2f} € Guthaben verbraucht{bezahlt_hinweis}."
                )

            c1, c2 = st.columns(2)
            with c1:
                vis.plot_costs_bar(df_stats_letzte)
            with c2:
                vis.plot_costs_pie(df_stats_letzte)
            st.download_button(
                "📥 Kostenstatistik (letzte Karte) als CSV exportieren",
                data=export_utils.to_csv_bytes(df_stats_letzte),
                file_name=f"kostenstatistik_letzte_karte_{date.today().isoformat()}.csv",
                mime="text/csv",
                key="dl_kostenstatistik_letzte_karte",
            )
        else:
            st.info("Noch keine Daten für eine Visualisierung vorhanden.")

def render_statistics_page():
    st.title("📊 Sportliche Statistiken")

    df = calc.build_dataframe()
    if df.empty:
        st.info("Noch keine Daten vorhanden")
        return

    alle_spieler = db.get_alle_spieler_namen()
    if not alle_spieler:
        st.info("Keine Spieler hinterlegt.")
        return

    spieler = st.selectbox("Spieler auswählen", alle_spieler, key="stats_player_select")

    stats = calc.player_stats(df, spieler)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Siege", stats["siege"])
    col2.metric("Niederlagen", stats["niederlagen"])
    col3.metric("Spiele", stats["gesamt"])
    col4.metric("Quote %", stats["quote"])

    st.divider()
    vis.plot_match_scatter(df, spieler, alle_spieler)

    st.subheader("🧮 Gesamt-Matrix")
    matrix = calc.head_to_head_matrix(df, alle_spieler)
    st.dataframe(matrix, width="stretch")
    st.download_button(
        "📥 Matrix als CSV exportieren",
        data=export_utils.to_csv_bytes(matrix, index=True),
        file_name=f"head_to_head_matrix_{date.today().isoformat()}.csv",
        mime="text/csv",
        key="dl_matrix",
    )
