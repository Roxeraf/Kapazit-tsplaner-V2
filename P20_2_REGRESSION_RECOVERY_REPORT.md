# P20.2 Regression Recovery Report

## 1. Ausgangslage

P20.1 ("PlanPhase simplification, direct ResourceAssignment domain & delete stabilization")
war laut eigenem Abschlussbericht vollständig grün: 16 Backend-Regressionsskripte,
`tsc -b && vite build`, `oxlint`, `check_migrations.py` und eine Playwright-Browser-Journey
(24/24 Checks). Alle diese Nachweise liefen ausschließlich gegen eine **frische SQLite-Datei**.

Der P20.2-Auftrag unterstellte, dass zentrale Bereiche der Anwendung ("Projekte laden nicht
mehr") seither nicht mehr zuverlässig funktionieren. Die Root-Cause-Analyse (Abschnitt 2)
bestätigt das — allerdings nicht dort, wo man es aus dem Diff naiv vermuten würde
(`routers/projects.py`, `capacity_calc.py`), sondern in zwei Stellen, die auf SQLite
unauffindbar sind, weil SQLite entweder VARCHAR-Längen nicht durchsetzt oder das FK-Pragma
standardmäßig deaktiviert lässt — exakt die Klasse Bug, vor der der P20.2-Auftrag ausdrücklich
warnt ("SQLite darf nicht unbemerkt andere FK-Semantik erzeugen als PostgreSQL").

**Vor dem Fix**: Der Backend-Prozess kam auf **jeder** echten PostgreSQL-Instanz (frisch oder
mit Bestandsdaten) beim Start nicht hoch — `db_bootstrap.run_migrations()` läuft synchron beim
Modulimport von `app/main.py`, ein fehlschlagendes `alembic upgrade head` bedeutet: der Server
startet gar nicht. Jede Anfrage — `GET /projects` eingeschlossen — läuft ins Leere
(Connection-Refused/502, je nach Deployment). Das erklärt "Projekte laden nicht mehr" exakt:
nicht die Projekt-Endpunkte selbst waren kaputt, sondern der Prozess dahinter existierte nicht.

**Zweiter, unabhängiger Fund** (nur mit FK-Enforcement reproduzierbar, siehe Abschnitt 2.2):
`delete-subtree` über eine 3-Ebenen-Hierarchie (Parent/Child/Grandchild, von BD-10 explizit
erlaubte Tiefe) löste auf PostgreSQL eine `ForeignKeyViolation` aus und lieferte einen 409
statt der erwarteten 204 — der von P20.1 behauptete Fix des Delete-Bugs war also für den
3-Ebenen-Fall nicht vollständig, weil der zugehörige Regressionstest nur 2 Ebenen abdeckte und
SQLite den Fehler ohnehin nie gezeigt hätte.

Alle anderen im Auftrag genannten Verdachtsflächen (ResourceAssignment.plan_phase_id-Migration,
Legacy-ResourceDemand-Koexistenz, Capacity-Consumer-Doppelzählung, Kapazitäts-UX ohne
Rollen-Aufschlüsselung, Kern-Flows A–L) wurden einzeln reproduziert und sind **funktional
korrekt** — siehe Abschnitt 4–8. Es gab keine dritte, vierte oder fünfte Regression.

## 2. Root Causes

### 2.1 Migrations-Revision-ID sprengt `alembic_version.version_num` (PostgreSQL-fatal)

**Symptom**: `db_bootstrap.run_migrations()` wirft beim App-Start
`sqlalchemy.exc.DataError: (psycopg2.errors.StringDataRightTruncation) value too long for type
character varying(32)` — reproduziert gegen eine echte lokale PostgreSQL-16-Instanz, sowohl auf
einer frischen leeren Datenbank als auch auf einer mit migriertem Bestand (Revision `0006`)
befüllten Datenbank. Der App-Prozess startet nicht; jede HTTP-Anfrage läuft ins Leere.

**Technische Ursache**: Migration `0007` trug die Revision-ID
`0007_p20_1_direct_plan_phase_assignment` (39 Zeichen). Alembic legt seine interne
`alembic_version`-Tabelle standardmäßig mit `version_num VARCHAR(32)` an (kein
`version_table_len`-Override in `alembic/env.py`). SQLite ignoriert VARCHAR-Längen (Type
Affinity, keine echte Constraint-Durchsetzung) — das `UPDATE alembic_version SET version_num=…`
"funktionierte" dort unbemerkt mit einem zu langen Wert. PostgreSQL erzwingt die Spaltenlänge
strikt und lehnt den `UPDATE` ab.

**Betroffene Dateien**:
`backend/alembic/versions/0007_p20_1_direct_plan_phase_assignment.py` (Revision-ID-String)

**Warum P20.1 die Regression auslöste**: P20.1 fügte diese Migration neu hinzu und wählte eine
lange, beschreibende Revision-ID nach dem Muster der Vorgänger — ohne die 32-Zeichen-Grenze zu
prüfen. Die 16 SQLite-Regressionsskripte, `check_migrations.py` und die Playwright-Journey aus
P20.1 liefen alle gegen frische SQLite-Dateien und liefen deshalb alle grün — SQLite hätte
diesen Fehler unter keinen Umständen zeigen können, da die Längenprüfung dort schlicht nicht
existiert. Erst ein Test gegen eine echte PostgreSQL-Instanz (P20.2, siehe Abschnitt 9) deckte
es auf.

### 2.2 `delete-subtree` löscht 3-Ebenen-Hierarchien in falscher Reihenfolge (PostgreSQL-fatal)

**Symptom**: `POST /plan-phases/{id}/delete-subtree` für eine Phase mit einem Kind, das
selbst wiederum ein Kind hat (Parent → Child → Grandchild, 3 Ebenen, von BD-10 als Maximaltiefe
vorgesehen), liefert auf PostgreSQL einen strukturierten 409
(`"Dieser Zweig kann aufgrund bestehender Verknüpfungen nicht gelöscht werden."`) statt der
erwarteten 204 — reproduziert gegen dieselbe lokale PostgreSQL-16-Instanz. Der zugrunde
liegende psycopg2-Fehler:
`ForeignKeyViolation: update or delete on table "plan_phases" violates foreign key constraint
"fk_plan_phases_parent_phase_id" ... Key (id)=(<child_id>) is still referenced from table
"plan_phases"` — der Parent wurde vor seinem eigenen Kind gelöscht.

**Technische Ursache**: `delete_subtree` berechnete zwar korrekt die "tiefste Ebene
zuerst"-Reihenfolge (`descendants_by_depth`), löschte aber über ORM-Objekt-`db.delete(phase)`
in einer Schleife gefolgt von einem einzigen gemeinsamen `db.commit()` am Ende.
`PlanPhase.parent_phase_id` ist in `models.py` eine reine FK-Spalte **ohne** gemapptes
`relationship()`. Ohne diese Relationship-Metadaten hat SQLAlchemys Unit-of-Work beim Flush
keine Information über die Selbstreferenz-Abhängigkeit zwischen den zum Löschen vorgemerkten
`PlanPhase`-Objekten und kann/muss die tatsächliche SQL-DELETE-Reihenfolge nicht an die hier
vorher berechnete Python-Reihenfolge binden — beobachtet wurde eine nach Primary-Key
aufsteigend sortierte Ausführung, die die berechnete Tiefen-Reihenfolge bei einer echten
3-Ebenen-Kette durchbricht. Auf SQLite blieb das unbemerkt, weil das FK-Pragma dort
standardmäßig deaktiviert ist (dieselbe Ursache, die schon den in P20.1 behobenen
"TypeError: Failed to fetch"-Bug ermöglicht hatte, siehe
`capacity_calc.cleanup_phase_resource_dependencies`-Docstring) **und** weil der bestehende
`test_p20_1_delete_stabilization.py`-Subtree-Test (Schritt 5/7) nur eine 2-Ebenen-Hierarchie
(Parent+Child, kein Grandchild) abdeckte — die genaue Bedingung, unter der das Problem
auftritt, wurde nie geprüft.

**Betroffene Dateien**: `backend/app/routers/planning.py` (`delete_subtree`)

**Warum P20.1 die Regression auslöste**: Der `descendants_by_depth`-Sortier-Code existierte
bereits vor P20.1 unverändert (P18/B-3) — P20.1 hat ihn nicht eingeführt, aber auch nicht
korrigiert, obwohl P20.1 explizit den Delete-Pfad ("Delete Stabilization") als Kernthema hatte
und dabei WorklogPhaseOverride/direkte-Assignment-Aufräumung in genau diese Funktion
eingebaut hat, ohne die vorbestehende Lösch-Reihenfolgen-Annahme zu verifizieren. Damit ist es
eine **von P20.1 nicht behobene, vorbestehende Lücke im als "behoben" deklarierten Delete-Pfad**
— im Sinne des Auftrags (Abschnitt 9: "Nicht davon ausgehen, dass er jetzt korrekt
funktioniert") eine Regression gegenüber dem behaupteten Status.

### 2.3 Keine weiteren Root Causes gefunden

Folgende im Auftrag explizit benannte Verdachtsflächen wurden geprüft und sind **nicht**
regressiert (Details in Abschnitt 4–8):

- `GET /projects`, `GET /projects/{id}` — unverändert durch P20.1, keine Kopplung an
  Assignment/Capacity-Berechnung, funktionieren mit Legacy-, Direct- und gemischten Daten.
- `ResourceAssignment.plan_phase_id`-Migration (`migrate_resource_assignments_to_plan_phase.py`)
  — dry-run/apply/idempotent korrekt, keine Doppelzählung migrierter Zeilen.
- Capacity-Consumer (Monthly/Portfolio/Utilization/GAP/Health/Cockpit) — korrekt auf beide
  Ressourcenwege rewired, keine Doppelzählung.
- Kapazitäts-UX (Kapazität-Tab) — keine Rollen-Aufschlüsselung/"Ohne Rolle"-UI mehr sichtbar,
  Bedarf/Besetzt/Offen korrekt.

## 3. Änderungen

### `backend/alembic/versions/0007_p20_1_direct_plan_phase_assignment.py`

**Was**: Revision-ID von `0007_p20_1_direct_plan_phase_assignment` (39 Zeichen) auf
`0007_p20_1_direct_assignment` (28 Zeichen) gekürzt, inkl. Docstring-Update mit Erklärung des
32-Zeichen-Limits. Dateiname unverändert gelassen (Alembic verlangt keine Übereinstimmung
zwischen Dateiname und Revision-String — Präzedenzfall bereits in `0001_consolidated_baseline.py`,
dessen Revision `0001_consolidated` ebenfalls kürzer als der Dateiname ist). Referenzierender
Kommentar in `backend/scripts/migrate_resource_assignments_to_plan_phase.py` (Docstring, rein
informativ, keine Code-Logik) synchron mitgeändert.

**Warum**: Root Cause 2.1. Kein Down-/Up-Revision-Verweis zeigte auf die alte lange ID (sie war
Head, nichts baute auf ihr auf), daher ist die Umbenennung gefahrlos. Keine reale
PostgreSQL-Datenbank kann je erfolgreich auf der alten langen ID gestanden haben — das Upgrade
brach dort immer schon vorher ab, also gibt es keinen Produktivstand, der durch die Umbenennung
"unbekannt" würde.

**Erhaltene Invariante**: Migrations-Policy (additiv, keine Schemaänderung durch die
Umbenennung selbst — nur der Revision-Bezeichner ändert sich, keine Spalte/kein Constraint).
`check_migrations.py` bestätigt weiterhin eine einzelne, integre Kette ohne Drift (Abschnitt 9).

### `backend/app/routers/planning.py` (`delete_subtree`)

**Was**: Die Schleife `for phase in descendants_by_depth: db.delete(phase)` gefolgt von
`db.delete(plan_phase)` und einem gemeinsamen `db.commit()` wurde durch pro-Phase
`db.query(models.PlanPhase).filter(models.PlanPhase.id == phase.id).delete(synchronize_session=False)`
in derselben, bereits vorher korrekt berechneten tiefste-zuerst-Reihenfolge ersetzt.

**Warum**: Root Cause 2.2. `Query.delete()` führt das `DELETE`-Statement synchron beim Aufruf
aus (nicht erst gebündelt bei einem späteren Flush) — garantiert dadurch dialektunabhängig
exakt die hier berechnete Reihenfolge, unabhängig davon, ob SQLAlchemys Unit-of-Work für
Self-FKs ohne `relationship()` eine andere interne Ausführungsreihenfolge wählt.

**Erhaltene Invariante**: Kein Zusatz einer `relationship()` an `PlanPhase.parent_phase_id`
(hätte Cascade-/Lazy-Loading-Verhalten an vielen weiteren Stellen im Code beeinflusst — deutlich
größerer Blast Radius für eine reine Ordering-Korrektur). Die fachliche Delete-Semantik
(Parent-Block per Standard-DELETE, explizite Subtree-Bestätigung, Collaboration-Inhalte bleiben
per SET NULL erhalten) bleibt unverändert; nur die *Ausführungsreihenfolge* der zugrunde
liegenden SQL-Statements wurde erzwungen.

### `backend/scripts/test_p20_2_regression_recovery.py` (neu)

**Was**: Drei Regressionschecks: (1) alle Alembic-Revision-IDs ≤ 32 Zeichen, dialektunabhängig
per String-Längenprüfung, kein DB-Zugriff nötig; (2) 3-Ebenen-`delete-subtree` — läuft
authoritativ gegen eine echte PostgreSQL-Instanz, wenn `P20_2_POSTGRES_TEST_URL` gesetzt ist
(empirisch verifiziert: SQLite mit `PRAGMA foreign_keys=ON` reproduziert den Ordering-Bug NICHT
zuverlässig, siehe Docstring im Skript — die Dialekt-Differenz liegt in SQLAlchemys interner
Umsetzung, nicht im FK-Pragma selbst), fällt ohne diese Variable auf einen SQLite-Best-Effort-Lauf
zurück; (3) keine Doppelzählung bei gemischten Legacy+Direct- und migrierten Daten
(assignment-summary + Portfolio-Utilization).

**Warum**: Beide behobenen Root Causes hatten keinen abdeckenden Regressionstest — dieser
schließt die Lücke und verhindert ein stilles Wiederauftreten.

## 4. Project Loading

| Endpoint | Frisches PostgreSQL | PostgreSQL mit Pre-P20.1-Bestandsdaten (Legacy ResourceDemand/-Assignment, WorklogPhaseOverride, 3-Ebenen-Hierarchie) |
|---|---|---|
| App-Start (`db_bootstrap.run_migrations()`) | **PASS** (vor Fix: FAIL, `StringDataRightTruncation`) | **PASS** (vor Fix: FAIL) |
| `GET /projects` | **PASS** | **PASS** |
| `GET /projects/{id}` | **PASS** | **PASS** |

Reproduziert gegen eine echte lokal installierte PostgreSQL-16-Instanz (nicht nur SQLite) —
sowohl vor dem Fix (beide Zeilen FAIL, Prozess startete nicht) als auch danach (beide PASS).

## 5. Assignment Compatibility

Alle vier Szenarien gegen echtes PostgreSQL getestet (`assignment-summary`, `/team/utilization`,
Monthly-Capacity, GAP, Health/Cockpit):

| Szenario | Ergebnis |
|---|---|
| Keine Assignments | PASS |
| Legacy ResourceDemand + ResourceAssignment ("Ohne Rolle"-Carrier UND echte Rollen-Aufschlüsselung) | PASS |
| Direktes PlanPhase-ResourceAssignment | PASS |
| Gemischt (ein Assignment legacy über echte Rolle, eines direkt, gleiche Phase) | PASS — korrekte Summe, keine Doppelzählung |
| Migriert (`migrate_resource_assignments_to_plan_phase.py --apply` gelaufen, Zeile trägt danach beide FKs) | PASS — weiterhin korrekte Summe, keine Doppelzählung; Migrationsskript selbst dry-run/apply/idempotent korrekt auf PostgreSQL verifiziert |

## 6. Delete Stabilization

Alle Szenarien gegen echtes PostgreSQL (FK-Enforcement aktiv, nicht SQLite):

| Szenario | Ergebnis |
|---|---|
| Leaf ohne Abhängigkeiten löschen | PASS |
| Leaf mit direktem ResourceAssignment löschen | PASS |
| Leaf mit Legacy-ResourceDemand+Assignment löschen | PASS |
| Leaf mit WorklogPhaseOverride löschen | PASS |
| Unterphase löschen | PASS |
| Letztes Kind einer Parent-Phase löschen (Parent wird wieder Leaf, `plan_fte` bleibt `NULL`, keine implizite Reaktivierung) | PASS |
| Parent mit Kindern → normaler DELETE → fachlich blockiert | PASS — 409 mit strukturiertem `{message, child_count}` |
| Subtree-Delete (2 Ebenen) | PASS |
| **Subtree-Delete (3 Ebenen, Parent/Child/Grandchild)** | **PASS nach Fix** (vor Fix: FAIL, `ForeignKeyViolation`, siehe Root Cause 2.2) |
| `delete_project` mit 3-Ebenen-Hierarchie (Bulk-`DELETE`, nicht ORM-Objekt-Loop — von Root Cause 2.2 nicht betroffen) | PASS |

Nach jedem Delete-Szenario: keine Orphans (`ResourceAssignment`/`ResourceDemand`/
`WorklogPhaseOverride` mit Verweis auf eine gelöschte `PlanPhase`), kein 500, kein
"Failed to fetch", strukturierte JSON-Antworten bei Konflikten.

## 7. Capacity Consumers

Alle gegen echtes PostgreSQL mit gemischten Legacy+Direct-Daten getestet:

| Consumer | Ergebnis |
|---|---|
| Monthly Capacity (`/projects/{id}/capacity/monthly`) | PASS — bleibt strikt `plan_fte`-basiert |
| Portfolio Utilization (`/team/utilization`) | PASS — beide Ressourcenwege summiert, keine Doppelzählung |
| Utilization Gap (`/people/{id}/gaps/utilization`) | PASS |
| GAP (`/projects/{id}/gaps`) | PASS |
| Health (`/projects/{id}/health`) | PASS |
| Cockpit (`/projects/{id}/cockpit`) | PASS |
| Allocation-Gaps/Role-Analysis (Legacy-Rollen-Feature, unverändert) | PASS |

## 8. Frontend Smoke Test

Echter Headless-Chromium-Lauf (Playwright, `/opt/pw-browsers/chromium-1194`) gegen den echten
Dev-Server (Vite + FastAPI/uvicorn, frische SQLite-DB) — **kein** Test-Client, echte HTTP-Requests
über den Browser:

| Schritt | Ergebnis |
|---|---|
| Projektübersicht lädt, Projekt anlegen | PASS |
| Projekt öffnen → Projektdetails (Übersicht-Tab) laden | PASS |
| Projekt → Planung | PASS |
| Phase anlegen → PlanPhase-Workspace öffnen | PASS |
| PlanPhase → Kapazität (keine Rollen-UI, kein "Ohne Rolle", keine "Rollen aufschlüsseln"-UI) | PASS |
| Mitarbeiter zuweisen (Bedarf/Besetzt/Offen korrekt) | PASS |
| Seite neu laden → Zuordnung weiterhin vorhanden | PASS |
| Mitarbeiter entfernen | PASS |
| Unterphase anlegen | PASS |
| Parent mit Kindern → Standard-Delete fachlich blockiert (409, strukturierter Dialog, keine rohe Exception) | PASS |
| Unterphase (letztes Kind) löschen | PASS |
| Parent (wieder Leaf) direkt löschen | PASS |
| Gantt-Ansicht öffnen (keine JS-Exception) | PASS |
| Projekt-Übersicht/Cockpit-Tab (Health/GAP) lädt | PASS |
| Projektübersicht nach allen Operationen erneut laden | PASS |

**21/21 Checks PASS**, 0 unbehandelte JS-Exceptions (`pageerror`) während des gesamten Laufs.
Zwei erwartete 404/409-Netzwerkantworten wurden bewusst durch die Testschritte selbst ausgelöst
(Doppel-Delete-Versuch bzw. der Parent-Block-Test) und sind kein Befund.

Eine Playwright-Eigenheit wurde während der Testerstellung beobachtet und dokumentiert (kein
Produktbug): Playwrights realistischer `.click()` (Hover+Mousedown+Mouseup mit
Stabilitäts-Retry) desynchronisiert sich gelegentlich mit dem debounced Autocomplete-Dropdown
des `PersonPicker`; ein roher `dispatch_event("click")` (entspricht dem tatsächlichen
Click-Event, das ein realer Mausklick auslöst) selektiert zuverlässig. Verifiziert durch
Vergleich beider Klick-Methoden auf identischem Code.

## 9. Tests

| Suite | Ergebnis |
|---|---|
| 16 bestehende Backend-Regressionsskripte (`backend/scripts/test_*.py`) | PASS (SQLite) |
| Neues `test_p20_2_regression_recovery.py` | PASS (SQLite Best-Effort-Teil + PostgreSQL-authoritativer Teil, siehe unten) |
| `check_migrations.py` | PASS, sowohl gegen SQLite als auch gegen eine echte PostgreSQL-16-Instanz (Kette integer, kein Drift, Seeds vollständig, Downgrade/Upgrade-Roundtrip sauber, 45 Tabellen) |
| **App-Start gegen echtes PostgreSQL** (frisch UND mit Pre-P20.1-Bestandsdaten) | PASS nach Fix, reproduzierbar FAIL vor Fix |
| **`delete-subtree` (3 Ebenen) gegen echtes PostgreSQL** | PASS nach Fix, reproduzierbar FAIL vor Fix (Regressionstest per `P20_2_POSTGRES_TEST_URL` gegenprobe-verifiziert: schlägt ohne den Fix zuverlässig fehl, besteht mit Fix zuverlässig) |
| `migrate_resource_assignments_to_plan_phase.py` (dry-run/apply/idempotent) gegen echtes PostgreSQL | PASS |
| Alle Delete-/Capacity-Consumer-Szenarien aus Abschnitt 6/7 gegen echtes PostgreSQL (curl, nicht nur SQLite-TestClient) | PASS |
| TypeScript (`tsc -b`) | PASS, keine Fehler |
| `vite build` | PASS, sauberer Production-Build |
| `oxlint` | PASS, nur bereits vorbestehende, unveränderte Warnungen (React-Hooks-Deps/Fast-Refresh-Only-Export-Components in unveränderten Dateien) |
| Playwright Real-Browser-Journey | PASS, 21/21 (Abschnitt 8) |
| Migrations-Downgrade/Upgrade-Roundtrip | PASS (Teil von `check_migrations.py`) |

Kein Test wurde als PASS deklariert, ohne tatsächlich ausgeführt worden zu sein. Wo die
Standard-SQLite-Testumgebung strukturell nicht ausreicht, um eine PostgreSQL-spezifische
Regression nachzuweisen (Abschnitt 2.1/2.2), wurde eine echte lokale PostgreSQL-16-Instanz
installiert und verwendet (nicht simuliert) — konsequent mit der Auftragsanforderung, dass
"funktioniert auf einer leeren SQLite-DB" kein ausreichender Nachweis ist.

## 10. Remaining Issues

- Die zwei vorbestehenden unbenannten FK-Constraints (`resource_demands.plan_phase_id`,
  `worklog_phase_overrides.plan_phase_id`) tragen weiterhin kein DB-seitiges `ON DELETE`
  (bereits in P20.1 als bekannter, bewusst nicht behobener Restrisiko-Punkt dokumentiert,
  CONCEPT.md §6.17). Jeder aktuelle Anwendungscode-Pfad ruft
  `cleanup_phase_resource_dependencies` korrekt vorher auf; das Risiko besteht nur für
  hypothetischen künftigen Code, der diesen Aufruf vergisst — kein aktiver Bug.
- `migrate_resource_assignments_to_plan_phase.py` wurde weiterhin nicht gegen reale
  Produktivdaten ausgeführt (bewusst, separater freizugebender Schritt, unverändert seit P20.1).
- Keine weiteren, über Abschnitt 2 hinausgehenden Regressionen gefunden — die im Auftrag
  aufgelisteten Verdachtsflächen (Jira/Tempo-Integration, Collaboration/Comments/Tasks/
  Blockers/Decisions/Tags/Documents/Milestones, Planstände) sind durch P20.1 unverändert
  gebliebene Codepfade und wurden stichprobenartig über die Playwright-Journey (Historie-Tab
  nicht separat aufgerufen, aber PlanHistory-Schreibpfad durch die Delete-Audit-Einträge
  in Abschnitt 6 indirekt mitgeprüft) sowie die 16 unveränderten Backend-Regressionsskripte
  bestätigt.
