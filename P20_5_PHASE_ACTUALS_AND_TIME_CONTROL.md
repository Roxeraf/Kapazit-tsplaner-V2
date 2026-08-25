# P20.5 — Phase Actuals, Time Control & Automatic Jira/Tempo Sync

> Hinweis zur Nummerierung: Die Projekthistorie hat "P20.1"–"P20.8" bereits zweimal für zwei
> fachlich unterschiedliche Arbeitspakete vergeben (siehe `git log`: eine erste Welle
> abgeschlossen mit `P20.8: Regression / CONCEPT / E2E`, eine zweite mit eigenen Reports von
> `P20.1_PLANPHASE_SIMPLIFICATION_REPORT.md` bis `P20_4_PLANPHASE_WORKSPACE_UX_REDIRECT.md`).
> Dieses Paket ist ein DRITTES, chronologisch danach folgendes Arbeitspaket unter derselben
> Nummer "P20.5" (Kollision mit der ersten Welle "P20.5: Plan-vs-Actual Workspace UX") — siehe
> CONCEPT.md Abschnitt 16.31 für die vollständige Disambiguierung.

## 1. Executive Summary

Die bestehende Phase-Ist-Logik (P20.4/P20.6) zählte jeden Jira/Tempo-Worklog, der über den
Resolver eindeutig einem Issue zugeordnet werden konnte — unabhängig davon, ob der Autor
Consultant, Developer, externer Beteiligter oder ein völlig unbekannter Jira-User war. Für
Kapazitätssteuerung beantwortete das die falsche Frage ("wie viele Jira-Stunden existieren
insgesamt auf den Tickets dieser Phase?") statt der richtigen ("wie viel hat unser
kapazitätsplanbares Projektteam tatsächlich verbraucht?"). Dieser Auftrag trennt beide Begriffe
sauber (**Capacity Actual** vs. **Project/Jira Total Actual**), macht den Jira/Tempo-Sync
automatisch (alle 15 Minuten statt ausschließlich manuell), und ergänzt eine vollständig
system-abgeleitete Terminsteuerung: automatischer `actual_start`, statusbasierter `actual_end`,
ein einmalig eingefrorenes, immutables **Start Commitment** als stabile Referenz für
Terminabweichungen — ohne manuelle Planstände, ohne Actual-Datumsfelder, ohne manuellen Sync
als Voraussetzung.

**Ergebnis: P20.5 COMPLETE.** Alle 28 Punkte der Definition of Done (Abschnitt 62 des
Auftrags) sind erfüllt und regressionsgetestet — 21 SQLite-Regressionsskripte (18 bestehend +
3 neu), 8 davon zusätzlich gegen eine echte PostgreSQL-16-Instanz erneut verifiziert (dazu die
3 neuen Skripte selbst), Migration `0009_p20_5_phase_actuals` gegen SQLite und PostgreSQL
angewendet, Frontend-Build/Lint grün, eine vollständige Playwright-Browser-Journey ohne
Konsolenfehler.

## 2. Existing Actual Architecture Audit

`PlanPhase.actual_start`/`actual_end` existierten bereits als Spalten (seit P18), waren aber
bis zu diesem Durchgang Teil von `PlanPhaseCreate`/`PlanPhaseUpdate` (manuell beschreibbar über
die API, auch wenn seit P20.1 keine UI-Karte mehr dafür existierte — siehe CONCEPT.md
Abschnitt 6.16/16.29/16.30, "Compat-only"). `worklog_actuals.py`/`phase_metrics_calc.py`
(P20.4) lieferten bereits Resolver-basiertes Phase-Ist (`leaf_ist_hours`/`parent_ist_hours`),
aber ungefiltert nach Autor — jeder MATCHED-Worklog zählte, unabhängig davon, ob der Autor
überhaupt eine lokale Person war. `Person.active` + `ResourceProfile.capacity_relevant`
existierten bereits als etablierter "kapazitätsplanbare Person"-Filter an drei Stellen
(`capacity_calc.compute_available_capacity`/`compute_portfolio_available_capacity`,
`routers/planning.py.list_plan_phase_assignment_candidates`, `routers/capacity.py`) — dieselbe
fachliche Eigenschaft wurde für P20.5 wiederverwendet, nicht neu erfunden (Auftrag Abschnitt 3
verlangt genau das). Kein Scheduler-Framework im Repo (`requirements.txt` enthält weder Celery
noch APScheduler/RQ) — der automatische Sync brauchte einen neuen, aber minimalen Mechanismus
(Abschnitt 8). `_plan_phase_detail()` in `routers/planning.py` baute einen zweiten,
eigenständig gepflegten Feldsatz statt `_plan_phase_out()` wiederzuverwenden — dieses
strukturelle Risiko realisierte sich während der Implementierung tatsächlich (Abschnitt 18,
"gefundener Bug") und wurde behoben.

## 3. Capacity Scope Definition

Kapazitätsplanbar ist eine Person, wenn `Person.active` UND ein zugehöriges `ResourceProfile`
mit `capacity_relevant == True` existiert (`worklog_actuals.capacity_planbare_accounts`,
gejoined über `jira_account_id`). Bewusst dieselbe Definition wie an den drei bestehenden
Stellen oben — keine neue, konkurrierende "kapazitätsplanbar"-Semantik. Ein Jira-Worklog-Autor
ohne passenden `jira_account_id`-Treffer auf eine solche Person zählt NICHT zum Capacity
Actual, verschwindet aber nicht: er bleibt Teil des Project/Jira Total Actual und wird
zusätzlich transparent als "außerhalb Kapazitätsscope" ausgewiesen (Abschnitt 4/9).
`ResourceProfile.active` wird bewusst NICHT zusätzlich geprüft — kein bestehender Aufrufer tut
das (Feld ist im Code aktuell ungenutzt/reserviert), eine zusätzliche Bedingung hier hätte eine
neue, von allen anderen Consumern abweichende Definition eingeführt.

## 4. Project Actual vs Capacity Actual

Zwei bewusst getrennte Funktionsfamilien in `worklog_actuals.py`, beide auf denselben
Resolver-Zeilen (`_matched_worklog_rows`) aufsetzend:

| | Project/Jira Total Actual | Capacity Actual |
|---|---|---|
| Funktionen | `hours_by_issue`, `hours_by_matched_phase`, `leaf_ist_hours`, `parent_ist_hours`, `person_hours_by_matched_phase`, `person_hours_for_phase` (**unverändert seit P20.4**) | `capacity_hours_by_matched_phase`, `leaf_capacity_ist_hours`, `parent_capacity_ist_hours`, `person_capacity_hours_for_phase` (**neu**) |
| Zählt | JEDEN MATCHED-Worklog, jeder Autor | NUR Worklogs kapazitätsplanbarer Personen |
| Konsumenten | `jira_sync.berechne_ist_fte`, `actuals_coverage.py` (Projekt-Coverage) | `PhaseMetricsOut.ist_hours` (Plan-vs-Ist einer PlanPhase), `PlanPhasePersonActualsOut` |
| Ändert sich mit P20.5? | Nein | Ja — ersetzt das bisherige ungefilterte Phase-Ist als Quelle für Plan-vs-Ist |

`routers/planning.py._plan_phase_metrics` und `get_plan_phase_person_actuals` wurden auf die
Capacity-Actual-Funktionen umgestellt; alle anderen Konsumenten der alten Funktionen (Projekt-
Ist-FTE, Mapping-Coverage) blieben unangetastet — verifiziert durch
`test_p20_project_rollup_unchanged.py` (unverändert grün) und die neue Prüfung in
`test_p20_5_capacity_scope.py`, dass `GET /projects/{id}/actuals-coverage` weiterhin die volle,
ungefilterte Summe zeigt (240 h im Testfall trotz 60 h Capacity Actual).

## 5. Person Filtering

`worklog_actuals.capacity_rows_by_matched_phase`/`outside_scope_rows_by_matched_phase` teilen
dieselben MATCHED-Zeilen in zwei disjunkte Mengen. Eine kapazitätsplanbare Person OHNE
`ResourceAssignment` auf der Phase zählt trotzdem zum Capacity Actual — Assignment bestimmt
ausschließlich `planned`/`unplanned` im Personen-Drilldown (`PersonActualOut.planned`), nie ob
die Stunden überhaupt gezählt werden (Auftrag Abschnitt 4, Testfall Abschnitt 54). Ein Autor
ohne kapazitätsplanbare Person landet nie in `PlanPhasePersonActualsOut.persons`, sondern
ausschließlich in `outside_scope` (Stunden + eindeutige Autorenzahl) — kein stiller
Informationsverlust, aber auch keine Vermischung mit dem primären, kapazitätsrelevanten
Drilldown.

## 6. Phase Actual Calculation

`leaf_capacity_ist_hours`/`parent_capacity_ist_hours` folgen exakt derselben None-vs-0.0-
Konvention wie ihre P20.4-Vorbilder: `None` = kein `jira_label` konfiguriert ("noch nicht
zugeordnet"), `0.0` = Label konfiguriert, aber keine (oder ausschließlich außerhalb des Scopes
liegende) Worklogs — eine echte Messung. Keine Zeitraum-Kappung: Worklogs vor dem geplanten
Start oder nach dem geplanten Ende zählen unverändert zur Summe (Testfall Abschnitt 55: 10+30
im Zeitraum + 10+20 nach Commitment-Ende = 70 h Gesamt-Ist, nicht 40 h). Parent-Aggregation
bleibt rekursiv über alle Leaf-Nachfahren, keine doppelte Speicherung.

## 7. Worklog Date Classification

`classify_leaf_capacity_hours`/`parent_classify_capacity_hours` schlüsseln dieselben
Capacity-Ist-Zeilen nach `datum < start` (before) / `start <= datum <= end` (within) /
`datum > end` (after) auf — reine Aufschlüsselung, verändert die Summe nicht. Referenzzeitraum
ist bevorzugt das Start Commitment (`commitment_start`/`commitment_end`), ersatzweise der
aktuelle Plan (`forecast_start`/`forecast_end`), solange noch kein Commitment existiert
(Abschnitt 39/40 — eine spätere Planverschiebung darf die Klassifikation bereits gebuchter
Stunden nicht rückwirkend verändern). Explizit getrennte Dimensionen (Auftrag Abschnitt 52):
Jira-Label/Override bestimmt WELCHE Phase, Worklog-Datum bestimmt NUR WANN (Klassifikation +
`actual_start`-Ableitung, niemals das Mapping selbst — der P20.2-Resolver ist unverändert),
Person-Mapping bestimmt, OB der Aufwand zum Capacity Scope gehört.

## 8. Automatic Jira/Tempo Sync

Kein Scheduler-Framework im Repo gefunden → `app/scheduler.py`: ein `asyncio`-Loop, gestartet
über einen FastAPI-`startup`-Event (`main.py`), ruft `jira_sync.sync_project_and_refresh()`
alle 15 Minuten (`JIRA_AUTOSYNC_INTERVAL_SECONDS`, Default 900) für alle Projekte mit gesetzter
`jira_component` auf; eigene, kurzlebige DB-Session je Zyklus (nicht die Request-Session).
Abschaltbar über `JIRA_AUTOSYNC_ENABLED` (Default an). Der manuelle "Jetzt aktualisieren"-Button
(`POST /jira/sync`) bleibt als Sonderfall bestehen, läuft aber über **dieselbe** Orchestrierung
(`jira_sync.sync_project_and_refresh`) — kein zweiter, abweichender Code-Pfad. Diese Funktion
kapselt: `jira_sync.sync_project()` (unverändert) → `worklog_actuals.refresh_actual_start()`
(actual_start-/Commitment-Ableitung) → Sync-Status-Update, alles in einer Transaktion.

## 9. Sync Error Handling

Fehlerisolation auf zwei Ebenen: `sync_project_and_refresh()` fängt eine Exception EINES
Projekts ab, rollt die Transaktion zurück, schreibt `last_error`/`last_error_at` in
`JiraSyncStatus` und reicht den Fehler als Rückgabewert (nicht als Exception) an den Aufrufer
weiter; `scheduler.run_sync_cycle()` umschließt zusätzlich jeden Projekt-Sync mit einem eigenen
`try/except`, sodass ein unerwarteter Fehler außerhalb von `sync_project_and_refresh` selbst
(z. B. beim DB-Zugriff) den Zyklus nicht abbricht — Projekt B synchronisiert unabhängig von
einem Fehler bei Projekt A. Kein Retry-Sturm: der nächste Versuch wartet den vollen 15-Minuten-
Intervall ab. `last_success_at` wird durch einen späteren Fehler NIE überschrieben oder
gelöscht — bestehende Ist-Werte bleiben sichtbar, nur `last_error`/`last_error_at` zeigen
zusätzlich den aktuellen Fehlerzustand. Verifiziert in `test_p20_5_autosync.py` (Projekt-A-
Fehler stoppt Projekt B nicht, ein zweiter Fehler nach einem Erfolg löscht `last_success_at`
nicht).

## 10. Actual Start Semantics

`actual_start` = `min(datum)` über alle Capacity-Worklogs einer Leaf-Phase
(`worklog_actuals.leaf_first_capacity_worklog_date`), nachgezogen bei jedem Sync-Lauf
(`refresh_actual_start`, aufgerufen aus `sync_project_and_refresh`). Selbstkorrigierend NUR
nach früher — ein neuer, rückdatierter Worklog verschiebt `actual_start` nach vorne, ein
später gebuchter Worklog verschiebt ihn nie zurück. `NULL`, solange kein Capacity-Worklog
existiert (Abschnitt 46: Abschluss ohne Worklog lässt `actual_start` bewusst `NULL`, statt es
z. B. auf `forecast_start` zu setzen). Kein automatischer Statuswechsel bei Erst-Erfassung
(Abschnitt 21) — Ist-Daten und Workflow-Status bleiben getrennt; die UI zeigt stattdessen das
Datum im ZEIT-Block, sobald es vorliegt.

## 11. Actual End Semantics

`actual_end` wird AUSSCHLIESSLICH durch einen Statuswechsel gesetzt, nie aus Worklogs
abgeleitet (Abschnitt 19). `routers/planning.py._apply_status_transition_side_effects`:
Übergang NACH `"abgeschlossen"` setzt `actual_end = heute` (nur bei tatsächlichem Übergang,
nicht bei einem erneuten Speichern desselben Status); Übergang WEG von `"abgeschlossen"`
(Reopen) setzt `actual_end` zurück auf `NULL` (Abschnitt 45 — die History dokumentiert den
Statuswechsel selbst bereits automatisch, `status` ist ein getracktes Feld). Ein Worklog nach
`actual_end` erhöht `ist_hours` weiter, verändert `actual_end` selbst aber nicht (Testfall
Abschnitt 57) — im ZEIT-Block sichtbar über das unveränderte `Abgeschlossen`-Datum bei
gleichzeitig gestiegenem Ist-Aufwand. Reale Vokabular-Prüfung (Abschnitt 44): das Repo nutzt
`geplant`/`laufend`/`abgeschlossen`/`entfaellt` (kein `closed`/`done`) — `"abgeschlossen"` ist
der Wert, der `actual_end` setzt; `"entfaellt"` setzt es bewusst NICHT (eine entfallene Phase
ist nie "fertig geworden").

## 12. Last Activity Semantics

`last_activity_date` (`worklog_actuals.leaf_last_activity_date`/`parent_last_activity_date`) =
`max(datum)` über dieselben Capacity-Worklogs — bewusst NICHT persistiert (Auftrag Abschnitt
42: "bevorzuge Ableitung aus Worklogs, wo sinnvoll"), da sie ohnehin bei jeder Abfrage aus
demselben Cache-Durchlauf wie `ist_hours` mitfolgt und keine Korrektur-Semantik wie
`actual_start` braucht. Nur im ZEIT-Block sichtbar, solange die Phase NICHT abgeschlossen ist
(danach zeigt das Abschluss-Datum die relevantere Information).

## 13. Start Commitment Semantics

`PlanPhase.commitment_start`/`commitment_end`/`commitment_plan_fte`/`commitment_captured_at`
(neue, persistierte Spalten — Auftrag Abschnitt 42: ohne Persistenz wäre die Referenz nach
einer späteren Planänderung nicht mehr rekonstruierbar, ohne die komplette History
rückwärts auszuwerten). Einmalig eingefroren beim ERSTEN fachlichen Beginn-Ereignis
(`worklog_actuals.maybe_capture_commitment`): entweder erster relevanter Capacity-Worklog
ODER erster Statuswechsel aus `"geplant"` in `"laufend"`/`"abgeschlossen"`, je nachdem was
zuerst geschieht (Abschnitt 47/48) — beide Auslöser rufen dieselbe, idempotente Funktion auf.
Danach immutable: ein erneuter Aufruf ist ein No-Op, solange `commitment_start` bereits gesetzt
ist (Abschnitt 26). Kein Commitment ohne gültigen aktuellen Plan (`forecast_start` muss
gesetzt sein) — sonst wäre die eingefrorene Referenz bedeutungslos; der nächste
Trigger-Versuch holt es nach, sobald ein Plan existiert.

## 14. Current Plan vs Commitment vs Actual

Drei Ebenen gleichzeitig über die API sichtbar, nie vermischt: Start-Referenz
(`commitment_start`/`commitment_end`/`commitment_plan_fte`), aktueller Plan
(`forecast_start`/`forecast_end`/`plan_fte`, weiterhin frei editierbar), Actual
(`actual_start`/`actual_end`/`last_activity_date`). Testfall Abschnitt 56 (Plan verschoben)
verifiziert: eine Änderung an `forecast_end` NACH bereits gesetztem Commitment lässt
`commitment_end` unverändert, wird aber automatisch in `PlanHistory` dokumentiert
(`forecast_end` ist getrackt) — keine manuelle Historisierung nötig.

## 15. Schedule Variance Metrics

`phase_metrics_calc.workday_delta`/`duration_workdays`/`schedule_variance`/`workdays_overdue`
— reine Funktionen ohne DB-/Uhrzeit-Zugriff, Arbeitstage ausschließlich über die bestehende
`capacity_calc.count_weekdays_in_range` (keine neue Kalenderengine, Abschnitt 28/60).
`start_delay_workdays` = Commitment-Start → Actual-Start, `end_delay_workdays` = Commitment-
Ende → Actual-Ende (nur befüllt, sobald abgeschlossen), `plan_shift_workdays` = Commitment-Ende
→ aktueller Plan (unabhängig vom Abschluss, Abschnitt 31), `workdays_overdue` = wie viele
Arbeitstage "heute" bereits über dem Commitment-Ende liegt, solange die Phase noch läuft —
bewusst KEINE Ampel/Bewertung (Abschnitt 30). `duration_workdays` liefert zusätzlich geplante
vs. tatsächliche Dauer (Abschnitt 32), primäre Termin-KPI bleibt aber die Endabweichung.

## 16. Parent Aggregation

`planning_calc.derive_parent_commitment_bounds`/`derive_parent_actual_start`/
`derive_parent_actual_end` (neu, analog zu `derive_parent_bounds`/`derive_parent_capacity`):
Commitment = MIN/MAX über Leaf-Commitments, `actual_start` = frühestes Leaf-`actual_start`,
`actual_end` = spätestes Leaf-`actual_end`, ABER nur wenn ALLE relevanten (mit `jira_label`
konfigurierten) Leaf-Nachfahren bereits abgeschlossen sind — sonst `None` (Abschnitt 35).
`worklog_actuals.parent_last_activity_date`/`parent_classify_capacity_hours`/
`parent_outside_scope_summary` aggregieren analog. Kein eigenes Parent-Commitment-System
(Abschnitt 36) — alles rein aus den Leaf-Nachfahren abgeleitet, keine doppelte
Worklog-Speicherung.

## 17. UX Changes

`PlanPhaseWorkspace.tsx`, Steuerung-Karte (additiv, keine neue Karte): "Bei Phasenstart
geplant" (nur bei gesetztem Commitment, aktueller Plan nur zusätzlich gezeigt, wenn er
abweicht), "Ist-Aufwand Beraterteam" (umbenannt, macht Capacity Scope explizit), Transparenz-
Zeile "Weitere Jira-Aufwände: X h außerhalb Kapazitätsscope · N Jira-Autoren" (nur bei > 0 h),
before/within/after-Zeile, und ein ZEIT-Block (Tatsächlich gestartet / Letzte Aktivität ODER
Abgeschlossen / Endabweichung bzw. "Ursprünglicher Termin überschritten"). **Keine** Rückkehr
der in P20.1 entfernten manuellen "Tatsächlicher Verlauf"-Karte (Abschnitt 41) — alle neuen
Felder sind read-only. `ProjectJiraTab.tsx`: Sync-Freshness-Zeile ("Stand: … (vor X Minuten)",
Fehlerzustand ohne Löschen bestehender Werte), Button-Copy "Jetzt synchronisieren" → "Jetzt
aktualisieren".

## 18. Data Model Changes

Vier neue, nullable Spalten auf `plan_phases`: `commitment_start`/`commitment_end`
(`String(10)`), `commitment_plan_fte` (`Float`), `commitment_captured_at` (`String(40)`). Eine
neue Tabelle `jira_sync_status` (PK `project_id`, FK auf `projects.id`):
`last_attempt_at`/`last_success_at`/`last_error`/`last_error_at`. `actual_start`/`actual_end`
strukturell unverändert (bereits vorhanden), fachlich umgewidmet (system- statt
user-gepflegt — aus `PlanPhaseCreate`/`PlanPhaseUpdate` entfernt). Ein während der
Implementierung gefundener struktureller Bug wurde zusätzlich behoben: `_plan_phase_detail()`
baute bislang einen zweiten, separat gepflegten Feldsatz statt `_plan_phase_out()`
wiederzuverwenden — neue `PlanPhaseOut`-Felder landeten dadurch nur mit ihrem Pydantic-Default
(`None`) in `PlanPhaseDetail` statt mit dem echten Wert (reproduziert, als `commitment_start`
über den Detail-Endpoint konsequent `None` lieferte, obwohl direkt in der DB korrekt gesetzt —
siehe Abschnitt 26). Fix: `_plan_phase_detail()` baut den Basisfeldsatz jetzt aus
`_plan_phase_out(db, p).model_dump()`.

## 19. API Changes

Neu: `GET /projects/plan-phases/{id}/time-control` (`PhaseTimeControlOut`), additiv in
`PlanPhaseDetail.time_control` eingebettet. `GET /jira/sync-status/{project_id}`
(`JiraSyncStatusOut`). `PlanPhasePersonActualsOut` um `outside_scope` erweitert.
`PlanPhaseOut`/`PlanPhaseDetail` um `commitment_start/end/plan_fte/commitment_captured_at`,
`derived_commitment_start/end`, `derived_actual_start/end` erweitert. `PlanPhaseCreate`/
`PlanPhaseUpdate`: `actual_start`/`actual_end` entfernt (nicht mehr akzeptiert — ein
Aufrufer, der sie weiterhin mitschickt, bekommt sie stillschweigend ignoriert, da Pydantic
unbekannte Felder standardmäßig verwirft; keine 422, kein Breaking Change für bestehende
Klienten, die sie NICHT mitschicken). Alle Änderungen additiv, keine bestehende Response
verliert Felder.

## 20. CONCEPT.md Changes

Aktualisiert (rebuild-safe): Abschnitt 3 (Kernprinzipien — Actual/Commitment/Capacity-Scope-
Grundsätze), Abschnitt 5.1 (PlanPhase-Felder), Abschnitt 7 (Ist-Daten/Sync), Abschnitt 10
(Steuerung-Karte, Jira-Tab), Abschnitt 13 (Source-of-Truth-Matrix, 6 neue/geänderte Zeilen),
Abschnitt 15 (Deferred Features — "automatisches actual_start/end" als implementiert
markiert), neue Abschnitt 16.31 (vollständige Umsetzungsdokumentation nach demselben Muster
wie 16.1–16.30) inkl. explizitem Disambiguierungs-Hinweis zur P20.5-Namenskollision.

## 21. Migration

`backend/alembic/versions/0009_p20_5_phase_actuals.py`, `down_revision =
"0008_p20_3_plan_history"`, Revision-ID bewusst 24 Zeichen (< 32 — siehe P20.2-Lektion:
Alembics `alembic_version.version_num` ist standardmäßig `VARCHAR(32)`, SQLite ignoriert das,
PostgreSQL erzwingt es strikt). Rein additiv: vier neue nullable Spalten + eine neue Tabelle,
kein Datenverlust, sauberer Downgrade-Pfad. Verifiziert: `check_migrations.py` (Kette/Drift/
Seeds/Roundtrip, SQLite) UND direkter `alembic upgrade head` gegen eine echte lokale
PostgreSQL-16-Instanz (beide grün, keine Abweichung).

## 22. Backend Tests

21 Regressionsskripte insgesamt (18 bestehend + 3 neu), alle grün gegen SQLite:

- **Neu:** `test_p20_5_capacity_scope.py` (Testfall Abschnitt 53/54, Outside-Scope,
  before/within/after), `test_p20_5_commitment_and_variance.py` (Testfall Abschnitt 55-57,
  Reopen, Abschluss ohne Worklog, Commitment-Immutabilität), `test_p20_5_autosync.py`
  (Testfall Abschnitt 58, Fehlerisolation, Sync-Status).
- **Angepasst:** `test_p20_phase_actual_metrics.py`/`test_p20_person_actuals.py` — ihre
  Test-Personen hatten bislang KEIN `ResourceProfile` (waren also nie kapazitätsplanbar) und
  profitierten implizit von der jetzt bewusst geänderten "jeder Jira-Autor zählt"-Semantik;
  mit `capacity_relevant=True` ergänzt (fachlich korrekt: sie sollen ja weiterhin zum Capacity
  Actual zählen), zusätzlich ein neuer Fall "unbekannter Account landet in `outside_scope`,
  nicht mehr in `persons`" in `test_p20_person_actuals.py`.
- **Unverändert grün:** alle 16 übrigen bestehenden Skripte (u. a.
  `test_p20_project_rollup_unchanged.py`, `test_p20_actuals_coverage.py`,
  `test_p20_worklog_resolver.py`, `test_p20_jira_phase_mapping.py`) — Project/Jira Total
  Actual, Mapping-Resolver und Coverage sind strukturell unberührt.
- `check_migrations.py`: grün (Kette/Drift/Seeds/Roundtrip).

## 23. PostgreSQL Tests

Migration `0009_p20_5_phase_actuals` direkt gegen eine lokale PostgreSQL-16-Instanz angewendet
(`alembic upgrade head`, sauber, kein Fehler). Alle drei neuen P20.5-Skripte zusätzlich mit
einem `KAPA_TEST_DB_URL`-Override gegen PostgreSQL ausgeführt (statt der SQLite-Wegwerfdatei) —
grün. Acht bestehende, für dieses Paket besonders relevante Regressionsskripte ebenfalls gegen
PostgreSQL erneut verifiziert (per temporärem Override, keine dauerhafte Änderung an diesen
Skripten): `test_p20_1_delete_stabilization.py`, `test_p20_1_capacity_consumer_rewiring.py`,
`test_p20_2_regression_recovery.py`, `test_p20_3_project_history.py`,
`test_p20_jira_phase_mapping.py`, `test_p20_person_actuals.py`,
`test_p20_phase_actual_metrics.py`, `test_planning_phase_tree_api.py` — alle grün, keine
FK-/VARCHAR-/Ordering-Abweichung zu SQLite gefunden (die Klasse Bug, vor der P20.2 warnt).

## 24. Frontend Tests

`tsc -b` (Typecheck): grün, keine Fehler. `npm run build` (`tsc -b && vite build`): grün,
441.76 kB Bundle (unauffällig). `oxlint`: grün, nur bereits vor diesem Durchgang bestehende
Warnungen (kein neuer Fund in geänderten Dateien).

## 25. Playwright Results

Vollständige Browser-Journey (Backend auf Port 8000 + Vite-Dev-Server auf Port 5173, Chromium
headless über die im Environment vorinstallierte Browser-Binary): Projekt anlegen → Phase mit
`jira_label` und Plan (0.5 FTE, 01.10.–17.10.2026) → Worklogs direkt in den Cache eingespielt
(Dominik 32 h + 10 h, Christian 8 h — beide kapazitätsplanbar; Developer X 100 h, keine lokale
Person) → Drawer öffnen: Steuerung-Karte zeigt "Bei Phasenstart geplant 01.10.2026 –
17.10.2026", "Ist-Aufwand Beraterteam 50 h" (32+10+8, Developer korrekt ausgeschlossen),
"Aufwand verbraucht 104,17 %", "Überverbrauch 2 h", "Weitere Jira-Aufwände: 100 h außerhalb
Kapazitätsscope · 1 Jira-Autor", "Davon vor geplantem Start: 0 h · im geplanten Zeitraum: 40 h
· nach geplantem Ende: 10 h", ZEIT-Block "Tatsächlich gestartet 03.10.2026" → Status auf
"Abgeschlossen" gesetzt → ZEIT-Block aktualisiert sich live auf "Abgeschlossen: [heute]" +
"Endabweichung: [X] Arbeitstage", Status-Dropdown zeigt korrekt "Abgeschlossen". Kapazität-Tab
öffnet ohne Fehler. Keine Konsolen-/Seitenfehler während der gesamten Journey. Screenshots
lokal gesichert (nicht Teil dieses Reports, auf Anfrage verfügbar).

## 26. Remaining Risks

- **`last_activity_date` und `outside_scope` sind live berechnet, nicht gecacht** — bei sehr
  großen Worklog-Ständen (mehrere zehntausend Zeilen je Projekt) könnte das bei jedem
  Drawer-Öffnen spürbar werden; aktuell dieselbe Performance-Charakteristik wie die bereits
  bestehenden P20.4-Metriken (kein neuer Regressionsrisiko, aber kein zusätzliches Caching
  eingeführt).
- **Scheduler ist In-Process** (`asyncio`-Task im selben Uvicorn-Prozess) — bei mehreren
  Backend-Replikas (horizontale Skalierung) würde jede Instanz eigenständig synchronisieren
  (mehrfacher, aber idempotenter Sync, kein Datenfehler, nur unnötige Jira-API-Last). Für den
  aktuellen Single-Instance-Betrieb (siehe `docker-compose.yml`) unkritisch; bei künftiger
  horizontaler Skalierung wäre ein verteilter Lock oder ein externer Scheduler nötig.
- **Commitment-Trigger deckt keinen dritten, seltenen Fall ab:** eine Phase, die direkt mit
  `status="abgeschlossen"` UND bereits vorhandenen (nachträglich importierten) Worklogs
  angelegt wird, bekommt ihr Commitment beim Anlegen (Statuswechsel-Zweig) — `actual_start`
  wird erst beim NÄCHSTEN Sync-Lauf nachgezogen (bis zu 15 Minuten Verzögerung). Fachlich
  unkritisch (Commitment ist bereits korrekt gesetzt), aber `actual_start` kann für sehr kurze
  Zeit `NULL` bleiben, obwohl bereits Worklogs existieren.
- **`workdays_overdue` nutzt "heute" zum Anfragezeitpunkt** (kein Caching, kein Snapshot) —
  bei stark abweichender Server-/Client-Zeitzone könnte die Arbeitstage-Zählung um einen Tag
  abweichen; identisches, bereits vor P20.5 bestehendes Verhalten bei `time_progress_pct`
  (`gap_calc.expected_progress_pct`), keine neue Klasse von Risiko.
