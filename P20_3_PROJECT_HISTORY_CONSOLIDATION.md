# P20.3 Project History Consolidation

## 1. Executive Summary

P20.3 entfernt das Benutzerkonzept „Planstand“ aus dem normalen Produkt und macht
`PlanHistory` zum automatischen, unveränderlichen Audit Trail.

Fachliches Prinzip:

```text
USER ACTION → DOMAIN CHANGE → AUTOMATIC HISTORY ENTRY
```

Ein Projektleiter plant wie bisher (PlanPhase, Kapazität, Milestones, Zusammenarbeit). Das
System schreibt die Änderung. Es gibt kein „Planstand festhalten“, keine Versionen V1/V2,
keinen Vergleichs-Button und keine Einstellung, welche Änderungen historisiert werden.

Bestehende Infrastruktur wurde erweitert (`app/history.py` + additive Spalten auf
`plan_history`). Es gibt **keine** zweite History-Engine. `BaselineSnapshot` /
`BaselineEntry` bleiben als **LEGACY COMPAT** im Schema und in den APIs (Controlling,
Bestandsdaten, bestehende Tests). Sie sind kein Bestandteil des normalen Userflows.
Keine destruktive Migration.

Actor/`Person` bleibt nullable: das Repository hat bewusst kein Login-/RBAC-System.

## 2. Existing History Architecture Audit

Vor der Implementierung (Ist-Stand auf `claude/architecture-concept-reconciliation-due4vz`):

| Mechanismus | Rolle vor P20.3 | Schreibpfade |
|---|---|---|
| `PlanHistory` | Feld-Diff-Tabelle (`bereich`, `feld`, `alter_wert`, `neuer_wert`, `geaendert_am`, `batch_id`, `plan_phase_id`, optional `kommentar_id`) | Spärlich: Projektstammdaten-Update (`projects.py`); Leaf→Parent nullt `plan_fte`/`jira_label` (`bereich=phase_struktur`); Subtree-Delete (`bereich=phase_subtree_delete`) |
| `Activity` / `entity_links.ACTIVITY_ENTITY_TYPES` | Collaboration-Feed aus `created_at` von Kommentar/Task/Blocker/Decision/Risk/Meeting/PlanPhase/Milestone/**BaselineSnapshot** | Abgeleitet, kein Alt/Neu |
| `BaselineSnapshot` / `BaselineEntry` | Manuelles Userkonzept „Planstand“ (`BaselineList.tsx` im Planung-Tab) | `POST /projects/{id}/baselines` friert PlanPhase/Milestone-Felder ein; Vergleich über `GET .../deviations` und `baseline_calc` |
| Comments | Collaboration | Kein History-Write |
| Tasks / Blockers / Decisions | Collaboration-CRUD | Kein History-Write |
| ResourceAssignment / Milestone / PlanPhase CRUD | Domain-CRUD | Kein History-Write (außer den zwei Parent-/Delete-Sonderfällen) |
| Jira Sync / Worklog Cache | Technischer Sync | Kein History-Write (korrekt, Noise) |
| Worklog Override / `jira_label` | Manuelles Mapping | `jira_label` nur beim Parent-Übergang historisiert |

**Was ein History-Eintrag vor P20.3 speichern konnte:** `project_id`, Timestamp
(`geaendert_am`), Feldname, Alt/Neu, Bereich, optionale `plan_phase_id`/`subproject_id`/
`batch_id`/`kommentar_id`. **Nicht:** `entity_type`/`entity_id`/`entity_label`/`action`/
Actor.

**Doppelung:** Activity und PlanHistory waren bereits getrennte Konzepte. Planstände
erschienen zusätzlich im Activity-Feed („Planstand erstellt“) — das war fachlich ein
Benutzerereignis, das P20.3 abschafft.

**Baseline-Consumer (nicht droppen):**

- APIs unter `/projects/.../baselines` und `/projects/baselines/{id}`
- `baseline_calc.compute_deviations`
- Controlling `GET /controlling/baseline-deviations`
- Regressionsskript `backend/scripts/test_milestone_and_baseline_tree.py`
- Frontend-Client-Methoden und unimportierte `BaselineList.tsx`

Klassifikation: **A — noch technisch benötigt → Legacy/Compat behalten.**

## 3. History Coverage Matrix

Stand **nach** P20.3. History = automatischer `PlanHistory`-Eintrag. Activity bleibt
Collaboration-Feed.

| Domain Entity | Create | Update | Delete | Assignment/Relation | History heute | Gap |
|---|---|---|---|---|---|---|
| Project (Stammdaten) | ja | relevante Felder; No-Op still | n/a (kein Drop im normalen Flow) | — | `history.py` in `projects.py` | — |
| PlanPhase | ja („Phase X erstellt“ + Zeitraum/`plan_fte`) | Rename, Daten, Status, Owner, `plan_fte`, Parent, Reihenfolge, `jira_label`; Mehrfelder-Save gebündelt | ja, Label gesichert | Parent-Wechsel / Subtree-Delete | `planning.py` | — |
| ResourceAssignment | ja | FTE; No-Op still | ja, Personenlabel gesichert | Direct Assignment an Leaf | `planning.py` | Legacy-Demand-Assignments ohne direkten Phasenpfad nicht extra (kein normaler UI-Pfad) |
| Milestone | ja | Datum/Status/Name/Owner/Phase | ja | Tags | `planning.py` | — |
| Tags an projektbezogenen Entitäten | hinzufügen | — | entfernen | `record_tag_diff` | PlanPhase, Milestone, Task, Blocker, Decision | Tag-Rename in Administration ist globale Stammdatenänderung, **nicht** Projekt-History (bewusst) |
| Task | ja | relevante Felder inkl. Status | ja | Tags | `communication.py` | — |
| Blocker | ja | inkl. gelöst | ja | Tags | `communication.py` | — |
| Decision | ja | relevante Felder | ja | Tags | `communication.py` | — |
| Comment | Activity only | Activity only | Activity only | — | **kein** History-Write (keine Doppelung) | — |
| Risk / MeetingMinutes | Activity (Create-Zeitpunkt) | — | — | Tags ohne History | bewusst Collaboration, nicht Audit-Pflicht laut Auftrag | optionales späteres Coverage, kein P20.3-Scope |
| Document-Link | Projekt-Upload; Link auf Phase/Milestone | — | Verknüpfung entfernt | nur `plan_phase`/`milestone` | `documents.py` | Anhänge an Kommentar/Task nicht (Collaboration) |
| Jira Label | nicht als Create-Noise | manuelle Änderung | Parent-Nullung weiterhin | — | `planning.py` | — |
| Worklog Override | manuell setzen | Verschieben (Phase) | entfernen | — | `planning.py` | — |
| Jira/Tempo Sync / Cache | nein | nein | nein | — | **kein** Import von `history` | gewollt |
| BaselineSnapshot | API LEGACY COMPAT | — | API bleibt | Tags an Snapshot | **kein** neues „Planstand erstellt“ | Bestandsdaten lesbar |
| Derived Capacity / Health / Planstunden | nein | nein | nein | — | nicht historisiert | gewollt |

## 4. PlanHistory Changes

Keine neue Tabelle. Additive Erweiterung der bestehenden `plan_history`-Zeile:

Neue nullable Spalten (Migration `0008_p20_3_plan_history`, Revision-ID 22 Zeichen,
`down_revision = 0007_p20_1_direct_assignment`):

- `entity_type` (String 40)
- `entity_id` (Integer)
- `entity_label` (String 300)
- `action` (`created` / `updated` / `deleted`)
- `actor_person_id` (FK `persons.id` `ON DELETE SET NULL`)

Bestehende Spalten bleiben die Feld-Diff-Quelle: `feld`, `alter_wert`, `neuer_wert`,
`batch_id`, `geaendert_am`, `bereich`, `plan_phase_id`.

Create/Delete nutzen das Marker-Feld `_entity` statt einer Kette „null → Wert“.
`CREATE_DETAIL_FIELDS` begrenzt Intro-Felder (z. B. Phase: Name/Zeitraum/`plan_fte`, **nicht**
`jira_label` beim Anlegen — sonst bräche der bestehende Leaf→Parent-`jira_label`-Test).

Schreibpfad ausschließlich `backend/app/history.py`. Kein Update/Delete einzelner History-
Zeilen im Modul oder in Routern.

## 5. Project History Coverage

- Create Project → `action=created`, Label = Projektname, ausgewählte Stammdaten als Details.
- Relevante Updates: `name`, `kunde`, `status`, `projektleiter_person_id`, `start_monat`,
  `anzahl_monate`, `jira_component`.
- Identisches PUT (No-Op) erzeugt keinen Eintrag.
- `GET /projects/{id}/history` liefert **alle** Projektzeilen (Filter
  `subproject_id IS NULL` entfernt), neueste zuerst.
- Kein PUT/PATCH/DELETE auf History-Routen.

## 6. PlanPhase History Coverage

- Create: „Phase … erstellt“ plus Zeitraum/`plan_fte` (kein Null→Wert-Dump aller Felder).
- Rename, Datumsänderung, `plan_fte`, Status, Owner, Parent, Reihenfolge, `jira_label`.
- Mehrere Felder eines Speicherns teilen eine `batch_id`.
- Leaf→Parent: weiterhin Historisierung des genullten `plan_fte`/`jira_label`
  (`bereich=phase_struktur` über `record_rows`, bestehende Tests bleiben gültig).
- Delete / Subtree-Delete: Label bleibt verständlich („Phase X gelöscht“), nicht
  „Entity 472 deleted“.
- Tags an der Phase über `record_tag_diff`.

## 7. ResourceAssignment History Coverage

Direkte Assignments (`plan_phase_id` + `person_id` + `fte`):

- Create: Person zugewiesen + FTE.
- FTE-Änderung: Alt → Neu, gebündelt.
- Delete: Personenlabel gesichert.
- FTE-No-Op erzeugt keinen zweiten Eintrag.

Schreibpfade: REST-CRUD `.../plan-phases/{id}/assignments` **und** der UI-Pfad
`POST/DELETE .../plan-phases/{id}/assign-person` (P20.3 Nachzug, derselbe `history.py`-Write).

`plan_fte` und Assignment-FTE bleiben getrennte Source-of-Truth-Felder. Derived monthly
capacity / Planstunden / Portfolio-Werte werden nicht zusätzlich geschrieben.

## 8. Milestone History Coverage

Create / Datumsverschiebung / Status / Name / Owner / Phasenverknüpfung / Delete / Tags.
UI-Titel z. B. „Milestone ‚Go-Live‘ verschoben“ bei `forecast_date`.

## 9. Collaboration History Coverage

| Objekt | History | Activity | Begründung |
|---|---|---|---|
| Task | CRUD + Tags | Create-Event im Feed | Audit der Änderung (Status, Zuständig, …) |
| Blocker | CRUD inkl. gelöst + Tags | Create-Event | ebenso |
| Decision | CRUD + Tags | Create-Event | ebenso |
| Comment | **nein** | ja | Collaboration, keine doppelte History-Zeile |
| Risk / MeetingMinutes | nein | Create-Event | Auftrag listet sie nicht als Pflicht-Audit |

Keine zweite Collaboration-Historie im Planung-Tab.

## 10. Jira/Tempo History Coverage

Historisiert (manuell):

- `PlanPhase.jira_label` geändert
- Worklog-Override gesetzt / auf andere Phase verschoben / entfernt

Nicht historisiert (Noise):

- `POST /jira/sync`
- Cache-Refresh (`jira_worklogs_cache`, `jira_issue_cache`)
- automatische Worklog-Upserts

Nachweis: `jira.py` und `jira_sync.py` importieren `history` nicht (Testschritt in
`test_p20_3_project_history.py`).

## 11. Noise Prevention

Nicht historisiert:

- `updated_at` / `created_at`
- interne IDs als Selbstzweck
- derived monthly/portfolio capacity
- berechnete Planstunden / Available Capacity
- Health-Neuberechnungen
- Jira-Cache-Sync
- No-Op-Updates (`stringify(old) == stringify(new)`)
- Create nicht als vollständige Null→Wert-Liste
- Kommentare
- Baseline-POST als „Planstand erstellt“

Grundregel: Source-of-Truth historisieren, Derived Values rekonstruierbar lassen.

## 12. History UX

Zentraler Ort: Projekt-Tab **Historie** (`ProjectHistoryTab.tsx` + `HistoryTimeline.tsx`).

- Filter **Alle / Planung / Kapazität / Team / Zusammenarbeit** — reine View-Filter.
- Optionaler Zeitraum (Von/Bis).
- Gruppierung nach Kalendertag (Heute / Gestern / Datum) und `batch_id`.
- Collapsed: Uhrzeit + verständlicher Titel (z. B. „Phase ‚Konfiguration‘ geändert“).
- Expanded: Feldlabels auf Deutsch, Alt → Neu, Datums-/FTE-Formatierung, kein JSON-Dump.
- Keine Buttons „Historie bearbeiten“ / „Eintrag löschen“.
- Übersicht „Letzte Änderungen“ nutzt dieselbe Titel-/Gruppierungslogik
  (`historyFormat.ts`) und verlinkt auf den Historie-Tab.
- Actor-Name wird nicht erfunden: ohne Auth-Kontext erscheint kein Fake-Benutzer.

## 13. Planstand UX Removal

Entfernt aus dem normalen Workflow:

- Planstände-Card im Planning-Tab (`ProjectPlanningTab.tsx` importiert `BaselineList`
  nicht mehr)
- „+ Planstand festhalten“
- Planstand erstellen / benennen / löschen / auswählen
- „Mit aktuellem Plan vergleichen“
- Planstand-Hinweise in PlanPhases (bereits P20.1, bestätigt)
- `baseline_snapshot` aus dem Activity-Feed (`ACTIVITY_ENTITY_TYPES`)

Kein leerer Placeholder, kein „Legacy Planstände“, kein „Planstände wurden verschoben“.

Planning bleibt: PlanPhase-Liste, Milestones, derived monthly capacity.

`BaselineList.tsx` und `baselineDeviationFormat.ts` liegen ungenutzt auf der Platte
(Cleanup-Kandidat, Abschnitt 23).

## 14. BaselineSnapshot Compatibility

Klassifikation **A — noch technisch benötigt**.

Behalten:

- Tabellen `baseline_snapshots` / `baseline_entries`
- Router `backend/app/routers/baselines.py` (Docstring: LEGACY COMPAT)
- `baseline_calc.py` und Controlling-Portfolio-Deviations
- `PlanPhase.baseline_start` / `baseline_end` (compat-only Felder, Schedule-Gap)
- Knowledge-Registry-Eintrag (Label „Snapshot“, nicht „Planstand“)
- Frontend-API-Client-Methoden

Nicht mehr im normalen Userflow. Keine destruktive Migration. Keine neuen Activity-/
History-Ereignisse „Planstand erstellt“. Historische Snapshot-Zeilen bleiben in der DB.

## 15. API Changes

| Endpoint | Klassifikation | Änderung |
|---|---|---|
| `GET /projects/{id}/history` | **ACTIVE REQUIRED** | Liefert den vollen projektweiten Audit Trail inkl. neuer Felder; kein `subproject_id IS NULL`-Filter mehr |
| `GET /subprojects/{id}/history` | **LEGACY COMPAT** | unverändert, `@deprecated`-Umfeld Subproject |
| `POST /projects` | **ACTIVE REQUIRED** | schreibt Create-History |
| `PUT /projects/{id}` | **ACTIVE REQUIRED** | schreibt nur relevante Diffs |
| PlanPhase / Assignment / Milestone CRUD | **ACTIVE REQUIRED** | History-Writes |
| Task / Blocker / Decision CRUD | **ACTIVE REQUIRED** | History-Writes |
| Worklog-Override CRUD | **ACTIVE REQUIRED** | History-Writes |
| Document upload/link (Phase/Milestone/Projekt) | **ACTIVE REQUIRED** | History-Writes |
| `GET/POST /projects/{id}/baselines` | **LEGACY COMPAT** | kein History-Event; UI ungebunden |
| `GET/DELETE /projects/baselines/{id}` | **LEGACY COMPAT** | bleibt |
| `GET /projects/baselines/{id}/deviations` | **LEGACY COMPAT** | Controlling + Alt-Tests |
| `GET /controlling/baseline-deviations` | **LEGACY COMPAT** | Portfolio |
| History PUT/PATCH/DELETE | **UNUSED / nicht vorhanden** | Immutability |

UNUSED Baseline-Frontend-Routen wurden nicht serverseitig gedroppt (Migrations-/Compat-Risiko).

## 16. Database Changes

Nur additiv:

- Datei: `backend/alembic/versions/0008_p20_3_plan_history.py`
- Revision: `0008_p20_3_plan_history` (22 Zeichen, PostgreSQL `VARCHAR(32)`-Grenze)
- Kein `DROP` von `baseline_snapshots` / `baseline_entries`
- Kein Rewrite bestehender History-Zeilen (neue Spalten nullable)
- `check_migrations.py`: ein Head, Kette, kein Drift, Upgrade/Downgrade-Roundtrip

## 17. CONCEPT.md Changes

Abschnitte 1–14 beschreiben Planstand **nicht** mehr als normalen Workflow.

- Kopf: v0.26 (P20.3)
- Abschnitt 3: Project History = `PlanHistory`
- Abschnitt 4: `plan_history` Audit Trail; Baseline-Tabellen Legacy/Compat
- Abschnitt 5.3 neu: Project History + Legacy-Baseline-Unterabschnitt
- Abschnitt 6.14: von „Planstand-Strategie“ zu verbindlicher Project-History-Regel
- Abschnitt 10: Planung-Tab ohne Planstände; Historie ist die zentrale Oberfläche
- Abschnitt 13: Matrix-Zeile Planstand → Legacy/Compat; neue Zeile Project History
- Abschnitt 16.29: dieser Durchgang
- Abschnitt 16.1/16.3/16.13 bleiben **historische** Umsetzungsnotizen (P13 Planstand
  Experience etc.) — das ist Abschnitt 16, keine aktuelle Anforderung

Actor-Dokumentation: kein Auth im Repo, `actor_person_id` nullable.

## 18. Backend Tests

Skript: `backend/scripts/test_p20_3_project_history.py` (bestehendes Skript-Muster, kein
pytest-Framework).

Abgedeckt:

- Project create / relevantes Update / No-Op
- PlanPhase create / rename / Datums+`plan_fte` gebündelt / Parent / delete verständlich
- Assignment create / FTE / No-Op / delete mit Label
- Milestone create/update/delete
- Task / Blocker / Decision
- Tags an Phase
- Kommentare erzeugen keine History
- `jira_label` + Worklog-Override create/move/delete
- Jira-Sync-Module importieren `history` nicht
- Baseline POST schreibt kein Planstand-Event, GET bleibt 200
- project-scoped, chronologisch (`geaendert_am` desc)
- keine schreibenden History-Routen
- Actor-FK `ON DELETE SET NULL`

Zusätzliche Regression (nicht abgeschwächt):

- `backend/scripts/test_planning_phase_tree_api.py`
- `backend/scripts/test_p20_jira_phase_mapping.py`
- `backend/scripts/test_p20_1_delete_stabilization.py`

## 19. PostgreSQL Tests

Dasselbe Skript mit `P20_3_POSTGRES_TEST_URL` gegen eine lokale Wegwerf-Datenbank
(`postgresql+psycopg2:///kapa_p20_3?host=/var/run/postgresql`). Keine Produktiv-DB.

`python backend/check_migrations.py` auf der Wegwerf-DB des Wächters (SQLite laut
bestehendem Wächter; Revision-ID-Länge analog P20.2 geprüft: `0008_p20_3_plan_history`
= 22 Zeichen).

FK-Semantik Actor `ON DELETE SET NULL` ist Teil des P20.3-Skripts unter PostgreSQL.

## 20. Frontend Tests

- `npm run lint` (oxlint)
- `npm run build` (`tsc -b && vite build`)

Kein neues Vitest/Jest-Framework.

## 21. Playwright Journey

Kein Playwright-Framework als neue Projektdependency. Verifikation gegen den echten Stack
(Frontend `http://127.0.0.1:5173`, Backend `http://127.0.0.1:8000`, Wegwerf-SQLite).

| Check | Ergebnis |
|---|---|
| App öffnen, Projekt anlegen | **PASS** — „P20.3 History Demo“, Kunde Acme |
| Planung ohne Planstände | **PASS** — kein „Planstände“, kein „+ Planstand festhalten“, kein „Mit aktuellem Plan vergleichen“, kein V1 |
| Phase-Create-Modal | **PARTIALLY_VERIFIED** — Modal öffnet; Speichern blieb in der Browser-Automatisierung deaktiviert, weil US-Datumsstrings (`11/13/2026`) das HTML-`type=date`-Feld nicht füllten (`canSave` false). Kein Produkt-Bug, kein Console-Error. Phase „Konfiguration“ danach über `POST /plan-phases` angelegt. |
| Zeitraum / plan_fte ändern | **PASS** — Drawer Übersicht/Kapazität; Ende und Plan-FTE 0,60 → 0,80 in der Historie |
| Mitarbeiter zuweisen | **PASS** nach Fix des UI-Pfads `POST /plan-phases/{id}/assign-person` (History hing zuvor nur am REST-CRUD `/assignments`). Historie: „Christian Cron zugewiesen“, 0,20 FTE. Filter **Team** zeigt den Eintrag. |
| Milestone Datum | **PASS** — Go-Live 15.12.2026 → 18.12.2026, Titel „Milestone ‚Go-Live‘ verschoben“ |
| Historie-Tab zentral, keine Extra-Aktion | **PASS** |
| Filter Alle/Planung/Kapazität/Team/Zusammenarbeit | **PASS** — View-Filter; Team = Assignment; Kapazität = Plan-FTE; Zusammenarbeit leer ohne Collaboration-Events |
| Expand: deutsche Labels, Alt/Neu, kein JSON | **PASS** (Plan-FTE, Ende, Datum, FTE) |
| Kein Planstand-Button, keine History-Edit/Delete | **PASS** |
| Console | **PASS** — keine Application-Errors (nur React-DevTools-Hinweis) |

Zwischenstand-Artefakt der Datums-Automatisierung: eine History-Zeile mit Rohwert `202026-11-11` (getipptes US-Datum). Endzustand der Phase ist `forecast_end=2026-11-20`.

## 22. Remaining Legacy

Weiterhin vorhanden und bewusst nicht in diesem Auftrag entfernt:

- `BaselineSnapshot` / `BaselineEntry` Tabellen + APIs
- `PlanPhase.baseline_start` / `baseline_end` / Milestone `baseline_date`
- Controlling Baseline-Deviations
- `GET /subprojects/{id}/history`
- Knowledge-Registry `baseline_snapshot` (Label „Snapshot“)
- Frontend `api.listBaselines` / `createBaseline` / `deleteBaseline` / `getBaselineDeviations`
- `BaselineList.tsx`, `baselineDeviationFormat.ts` (unimportiert)
- Historische PlanHistory-Zeilen ohne `entity_type` (weiter lesbar über `bereich`/`feld`)

Direct ResourceAssignments, derived Capacity und P20 Actuals sind unverändert.

## 23. Deferred Cleanup

Eigene spätere Aufträge, **nicht** P20.3:

- Destruktives Drop von `baseline_snapshots` / `baseline_entries` (erst wenn alle Consumer
  inkl. Controlling und Alt-Tests abgelöst sind)
- Entfernen unimportierter UI (`BaselineList.tsx`, `baselineDeviationFormat.ts`) und
  ungenutzter Client-Methoden
- Optional: unused Baseline-POST aus dem öffentlichen API-Vokabular nehmen
- Auth-Kontext → `actor_person_id` befüllen (braucht Login, explizit out of scope)
- History für Risk/MeetingMinutes, falls fachlich gewünscht
- Admin-Tag-Rename als globale Admin-History
- Undo/Redo / Time Travel / Restore (explizit out of scope: Historie = Nachvollziehen)
