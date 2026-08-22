# P18 FINALIZATION & REALISTIC MIGRATION READINESS REPORT

**Datum:** 2026-08-22
**Scope:** (A) CONCEPT.md als Rebuild-Spezifikation bereinigen (aktuelle PlanPhase-only-
Architektur klar von historischem Pass-1-Design und dem noch aktiven Legacy-Compat-Pfad
trennen), (B) realistischen Migrations-Dry-Run gegen eine echte Produktivdatenkopie
durchführen bzw. vollständig vorbereiten, (C) B-8 GO/NO-GO final bewerten.
**Keine neue Architektur, keine neue Planungslogik, keine neue Capacity Engine, keine neue
Monatsplanung, kein erneutes Grob-/Feindesign. Keine produktive Migration, kein Legacy-Code
entfernt, keine irreversible Datenänderung.**

---

## 1. Executive Summary

Dieser Durchgang schließt P18 fachlich/dokumentarisch ab, bis auf den produktiven Cutover
(B-8). CONCEPT.md wurde grundlegend bereinigt: Was vorher als drei nebeneinander stehende
Kapazitätsabschnitte (6 = aktiver Legacy-Zwei-Achsen-Pfad, 6a = superseded Pass-1-Design, 6b =
finale Zielarchitektur) im Hauptteil stand, ist jetzt genau **ein** aktueller Abschnitt 6
(`PlanPhase`-only, aus dem ehemaligen 6b hervorgegangen) plus zwei vollständig, ohne Kürzung
in die Historie verschobene Kapitel (17.7 Pass-1-Design, 17.8 Legacy-Compat). Ein neuer
Agent, der nur Abschnitte 1–14 liest, sieht jetzt keine zwei konkurrierenden
Kapazitätsarchitekturen mehr.

Der verbleibende B-8-Blocker wurde erneut geprüft: Diese Arbeitsumgebung (frischer, isolierter
Remote-Container) hat **weiterhin keinen Zugriff auf eine echte oder repräsentative Kopie der
Produktivdatenbank** — kein laufender Docker-Daemon, kein laufender Postgres-Cluster, keine
Zugangsdaten, kein Snapshot im Repository. Wie in den vorangegangenen Durchgängen (16.15,
16.16) ausdrücklich gefordert, wurden **keine synthetischen Daten als Ersatz deklariert**. Das
Migrationstooling (`migrate_to_planphase_hierarchy.py`) und das gesamte Regressions-Testset
wurden erneut live ausgeführt — **alle grün, keine Regression** — das deckt die
Migrationslogik strukturell ab, ersetzt aber nicht den ausstehenden Lauf gegen echte
Datenrealität.

**Ergebnis: B-8 CUTOVER BLOCKED.** Einziger roter Punkt: der realistische Migrations-Dry-Run
gegen eine echte Produktivkopie steht weiterhin aus (externe Vorbedingung, kein Code-Defekt).
Ein vollständiger, sofort ausführbarer Cutover-Runbook-Plan liegt bereit (Abschnitt 19), der
erst nach einem grünen realistischen Dry-Run und in einem separaten, explizit freigegebenen
Auftrag angestoßen werden darf.

---

## 2. CONCEPT Cleanup Performed

- **Abschnitt 6 (neu)** = ehemaliger Abschnitt 6b ("PlanPhase-only Zielarchitektur, P18 Pass
  2"), umbenannt und an seine Zielposition verschoben. Interne Unterabschnittsnummern `6b.X`
  wurden mechanisch zu `6.X` (inkl. `6.1a`), alle ca. 50 Querverweise im übrigen Dokument
  wurden konsistent mitgezogen.
- **Abschnitt 6.15 "Legacy / Pending Cutover"** neu ergänzt: kompakte Zusammenfassung des
  aktiven Compat-Zustands (`ResourceDemandGrid`, Subproject-UI, `plan_phase_id = NULL`,
  sekundäre Effort-/PPTX-Konsumenten) mit Verweis auf das volle Detail in Abschnitt 17.8.
- **Abschnitt 17.7 "P18 Pass 1 — superseded Grob-/Feinplanung"** neu: der komplette,
  ursprüngliche Abschnitt 6a (Design, nie implementiert) ist **vollständig und ungekürzt**
  hierher verschoben, nur um eine Zeile Herkunftshinweis ergänzt und die internen
  `6a.X`-Überschriften eine Ebene tiefer gesetzt (`####` statt `###`). Die
  `6a.X`-Unterabschnittsnummern blieben unverändert (kollisionsfrei, da nirgends sonst
  wiederverwendet) — alle ca. 20 Querverweise außerhalb dieses Kapitels bleiben damit gültig
  und wurden zusätzlich mit `(Historie 17.7)` annotiert.
- **Abschnitt 17.8 "P18 Legacy-Compat — aktiver Zwei-Achsen-Pfad"** neu: der komplette,
  ursprüngliche Abschnitt 6 (aktiver, aber abzulösender `ResourceDemandGrid`/Subproject-Pfad)
  ist **vollständig und ungekürzt** hierher verschoben. Da seine vier Unterabschnitte (`6.1`–
  `6.4`) sonst mit den neuen `6.1`–`6.4` (aus 6b) kollidiert hätten, wurden sie eindeutig zu
  `L6.1`–`L6.4` umbenannt (`L` = Legacy) und alle ca. 25 Querverweise im übrigen Dokument
  entsprechend umbenannt und mit `(Historie 17.8)` annotiert. Zwei echte
  Selbstreferenzen innerhalb des verschobenen Texts ("Dieser Abschnitt …", "… bleibt
  trotzdem technisch aktiver Code") wurden von einer jetzt mehrdeutigen bloßen "Abschnitt
  6" auf eine explizite Referenz auf "Abschnitt (17.8)" korrigiert.
- **Dokumentkopf + "Wie dieses Dokument zu lesen ist"** neu geschrieben: beschreibt jetzt die
  neue Struktur (ein aktueller Kapazitätsabschnitt, zwei klar benannte Historie-/Compat-
  Kapitel) statt der alten "6a vs. 6b, bei Widerspruch gilt 6b"-Erklärung.
- **Abschnitt 3 (Kernprinzipien)**, Einleitungsabsatz neu geschrieben: verweist nicht mehr auf
  "Abschnitt 6/6a" für den Legacy-Pfad, sondern explizit auf `L6.1` (Historie 17.8) bzw.
  Abschnitt 17.7 für das superseded Pass-1-Design. Kein einzelner Kernprinzip-Bullet verweist
  mehr auf Pass-1-Grobplanung.
- **Abschnitt 16.17 "P18 Finalization"** neu ergänzt: dokumentiert diesen Durchgang selbst
  (Cleanup, erneute Umgebungsprüfung, GO/NO-GO-Ergebnis) nach demselben Muster wie 16.7–16.16.
- **Version** von v0.22 auf v0.23 angehoben.
- **Keine inhaltliche Kürzung.** Nettoeffekt: CONCEPT.md wuchs von 2668 auf 2792 Zeilen (nur
  Herkunfts-/Navigationshinweise, Mapping-Tabelle Abschnitt 6, neue 6.15/16.17 hinzugekommen —
  kein Bit historischer Analyse verloren).

---

## 3. Current Source-of-Truth Architecture

Unverändert gegenüber dem bereits implementierten und CONFIRMED-Stand (B-1–B-7, jetzt
CONCEPT.md Abschnitt 6): `PlanPhase` ist die einzige operative Planungseinheit. Leaf-Phasen
tragen Zeitraum + `plan_fte` + Personenbesetzung; Parent-Phasen aggregieren ausschließlich aus
Kindern (max. 3 Ebenen, BD-10 CLOSED). `ResourceDemand`/`ResourceAssignment` sind eine
optionale Rollen-/Personen-Schicht ohne eigene Kapazitätswirkung. Monats-/Portfoliokapazität
ist strikt derived (`compute_project_monthly_capacity`, werktage-anteilige
`monthly_distribution`), keine editierbare Monats-FTE-Eingabe existiert für neue Planung.
Direktzuweisung ohne Rollenzwang läuft über die interne Systemrolle "Ohne Rolle". Available
Capacity ist bereichsbasiert (`compute_person_capacity_for_range`), inzwischen auch für den
Legacy-Candidates-Endpoint (seit 16.16). Details/Codeverweise: CONCEPT.md Abschnitt 6.1–6.14.

---

## 4. Legacy Architecture Moved to History

| Historisches Kapitel | Inhalt | Status |
|---|---|---|
| CONCEPT.md 17.7 | P18 Pass 1: Grob-/Feinplanung, `max(Grob,Fein)`-Reconciliation, Konkretisierungsgrad | Design, **nie implementiert**, superseded durch Abschnitt 6 |
| CONCEPT.md 17.8 | Aktiver Zwei-Achsen-Legacy-Pfad: `ResourceDemand.plan_phase_id = NULL`, `ResourceDemandGrid`, Subproject | **Technisch weiterhin aktiver Code** für unmigrierte Alt-Projekte, keine Zielarchitektur, wird mit B-8 entfernt |

Beide Kapitel sind vollständig, mit Beispielrechnungen/Tabellen/API-Entwürfen erhalten — ein
Engineering-Team kann daraus sowohl die verworfene Pass-1-Idee als auch das heute noch aktive
Compat-Verhalten vollständig rekonstruieren, ohne dass beides die aktuelle Architektur
(Abschnitt 6) verwässert.

---

## 5. Production Snapshot Status

**Nicht verfügbar — erneut verifiziert in diesem Durchgang:**

| Prüfung | Befund |
|---|---|
| `docker info` | Kein laufender Docker-Daemon (CLI installiert, Daemon nicht gestartet) |
| `pg_lsclusters` / `service postgresql status` | Postgres-16-Cluster `down`, keine laufende Instanz |
| `DATABASE_URL` / Zugangsdaten | Nicht gesetzt, keine Produktions-Connection-Strings verfügbar |
| Snapshot-Dateien (`*.dump`, `*.pgdump`, `*.sql.gz`) im Repo/Dateisystem | Keine gefunden |

Es existiert **keine echte oder repräsentative Kopie der Produktivdaten** in dieser Umgebung.
Gemäß expliziter Vorgabe wurden **keine synthetischen Daten als Ersatz deklariert**. DB-
Version, Snapshot-Zeitpunkt, Datenbankgröße sowie die Zählungen aus Abschnitt 10 der
Aufgabenstellung (Projekte/Subprojects/PlanPhases/ResourceDemands/ResourceAssignments/
Milestones) können daher **nicht** erhoben werden — sie erfordern den externen Schritt 1/2 des
Runbooks (`backend/scripts/MIGRATION_DRY_RUN_RUNBOOK.md`).

**Benötigter externer Schritt (unverändert gegenüber 16.16, hier erneut exakt dokumentiert):**

1. Auf dem Produktivserver (Person mit Postgres-Zugriff): `pg_dump --format=custom` gegen die
   echte `DATABASE_URL`, Transfer auf eine isolierte Staging-/Migrationsmaschine.
2. Auf der Staging-Maschine (niemals auf Produktion): `createdb` + `pg_restore` in eine
   isolierte Kopie.
3. Ab hier ist der Ablauf werkzeugseitig vollständig vorbereitet (Abschnitt 6 unten).

---

## 6. Realistic Migration Dry-Run

**Nicht ausführbar in dieser Umgebung** (siehe Abschnitt 5) — daher **NICHT durchgeführt**,
NICHT gegen synthetische Daten simuliert. Stattdessen erneut vollständig vorbereitet und
verifiziert:

- `backend/scripts/MIGRATION_DRY_RUN_RUNBOOK.md` aktualisiert: dokumentiert jetzt explizit die
  in diesem Durchgang durchgeführte Umgebungsprüfung (Docker/Postgres/Zugangsdaten/Snapshot)
  statt nur pauschal "keine Umgebung vorhanden" zu behaupten.
- Migrationstooling (`migrate_to_planphase_hierarchy.py`, inkl. `--report-file`,
  Orphan-/FTE-/Hierarchietiefe-/Zyklen-/Milestone-/Assignment-Checks) unverändert, keine
  Code-Änderung in diesem Durchgang nötig — es war bereits vollständig (16.16).
- **Regressionslauf in diesem Durchgang, alle grün:**

| Test | Ergebnis |
|---|---|
| `check_migrations.py` | OK — Kette integer, kein Drift, Seeds vollständig, Upgrade/Downgrade-Roundtrip sauber |
| `scripts/test_migrate_to_planphase_hierarchy.py` | OK — Dry-Run isoliert (kein Schreibzugriff), Apply verlustfrei, Re-Run idempotent |
| `scripts/test_planning_phase_tree_api.py` | OK — Tiefe/Zyklus/Projektgrenze, Leaf→Parent-Historisierung, BD-11-Block, Reparent/Subtree-Delete |
| `scripts/test_direct_assignment_and_capacity_range.py` | OK — Systemrollen-Guard, Direktzuweisung, Überbesetzung, Range-Capacity, Legacy-Candidates-Range |
| `scripts/test_derived_monthly_capacity.py` | OK — monthly_distribution exakt nach CONCEPT-Beispiel, Cockpit liest PlanPhase statt ResourceDemand |
| `scripts/test_milestone_and_baseline_tree.py` | OK — Milestone-Verknüpfung, Planstand friert Baum ein, "added"/"removed" strukturell erkannt |
| `scripts/test_capacity_range_edge_cases.py` | OK — 11 Szenarien (WorkingTime/Holiday/Absence/InternalAllocation/Überbuchung/Teilmonat/…) |

Kein Code wurde geändert — reine Bestätigung, dass das vorbereitete Tooling weiterhin
funktioniert und startbereit ist, sobald Schritt 1/2 (Abschnitt 5) extern durchgeführt wurden.

---

## 7. Apply-on-Copy Results

**Nicht durchführbar** — Voraussetzung (realer Dry-Run gegen echte Kopie, Abschnitt 6) ist
nicht erfüllt. Kein `--apply` wurde gegen irgendeine Datenquelle außer der Wegwerf-
SQLite-Testfixture ausgeführt (dort: Apply verlustfrei, Re-Run idempotent, siehe Abschnitt 6).

---

## 8. Integrity Results

Nur gegen die synthetische Fixture verfügbar (unverändert gegenüber 16.15/16.16):
`orphan_resource_demands_after = 0`, `hierarchy_depth_violations = []`,
`fte_sum_before == fte_sum_after`, `milestones_before == milestones_after`,
`assignments_count_before == assignments_count_after`,
`assignments_fte_sum_before == assignments_fte_sum_after`. **Diese Werte sind gegen die reale
Datenrealität nicht abgesichert**, bis Schritt 1/2 extern durchgeführt und Schritt 3–10 des
Runbooks real durchlaufen wurden.

---

## 9. FTE / Capacity Parity

Nicht bewertbar ohne echte Daten. Das Runbook (Schritt 7) dokumentiert die notwendige Methode:
`compute_project_monthly_capacity` auf denselben Perioden vor und nach dem Apply vergleichen,
wobei "vorher" die alte, `ResourceDemand`-basierte Soll-Rechnung ist (da
`compute_project_monthly_capacity` bereits seit B-5 ausschließlich aus `PlanPhase.plan_fte`
liest und vor der Migration für unmigrierte Projekte 0 liefert). Ein dediziertes
Vergleichsskript dafür existiert bewusst noch nicht (kein Sinn, es gegen nichts zu
verifizieren) — sollte unmittelbar vor dem echten Cutover, sobald eine reale Kopie vorliegt,
ergänzt werden (siehe Abschnitt 19, Step 7).

---

## 10. Subproject Migration Results

Nicht durchführbar ohne echte Daten. Tooling-seitig unverändert vollständig (Abschnitt 6):
`_migrate_subprojects` reparentet Kinder-Phasen, hängt Milestones/Comments um, erzeugt eine
neue Top-Level-Parent-Phase je `Subproject`, bleibt idempotent bei Re-Run. In der
synthetischen Fixture strukturell verifiziert (1 Subproject, 2 Kindphasen, 1 Milestone, 1
Comment — alle korrekt migriert, siehe 16.15).

---

## 11. Assignment Preservation

Nicht durchführbar ohne echte Daten. Tooling-seitig CONFIRMED: `ResourceAssignment` hängt nur
an `resource_demand_id`, wird durch die Migration nie direkt verändert; Vorher-/Nachher-Check
(`assignments_count_before/after`, `assignments_fte_sum_before/after`) ist Teil des
`has_discrepancies`-Gates (seit 16.16). In der Fixture: 1 Assignment, vollständig erhalten.

---

## 12. Milestone Preservation

Nicht durchführbar ohne echte Daten. Tooling-seitig CONFIRMED: `milestones_before ==
milestones_after` ist Teil des Migrationsreports; Subproject-Migration hängt betroffene
Milestones auf die neue Parent-Phase um (`plan_phase_id` gesetzt). In der Fixture: 1
Milestone, korrekt umgehängt.

---

## 13. UI Smoke Tests

Nicht durchführbar gegen migrierte Realdaten (keine laufende Instanz mit echten Daten). Der
zugrunde liegende PlanPhase-Tree-UI-Flow selbst ist unverändert seit B-6/16.12 CONFIRMED
(Baum in Liste/Gantt/Workspace, Direct-Assignment-UX, BD-11-Blockierdialog, keine rohen
technischen Begriffe) — dieser Durchgang hat daran nichts geändert und keinen neuen Code-Test
dafür nötig gemacht, da kein Code geändert wurde.

---

## 14. Planstand Tests

Nicht durchführbar gegen migrierte Realdaten. Die zugrunde liegende Planstand-Diff-Logik ist
seit P18.1 (16.16) vollständig: "Phase hinzugefügt"/"Phase entfernt" werden strukturell mit
sprechendem Namen erkannt (kein Roh-ID-Leck), Regressionstest `test_milestone_and_baseline_
tree.py` in diesem Durchgang erneut grün (Abschnitt 6 oben).

---

## 15. Gantt Tests

Nicht durchführbar gegen migrierte Realdaten. Gantt liest denselben `PlanPhase`-Baum wie die
Liste (Parent = Hüllkurve, Leaf = Balken, beide öffnen denselben Workspace) — unverändert seit
B-7/16.13 CONFIRMED, keine Subproject-Gantt-Struktur mehr im primären Flow.

---

## 16. Secondary Consumer Assessment

Unverändert gegenüber der Bewertung in 16.16 (kein Code seitdem geändert): `gap_analysis.
_soll_je_monat` (Effort-/Health-Soll-Track) und der PPTX-Export-"fte"-Feld lesen weiterhin
direkt `ResourceDemand.fte`, nicht die PlanPhase-Kapazität. Das ist **bewusst deferred**, aus
zwei Gründen: (1) fachlich andere Semantik (Effort-Soll ≠ Capacity-Soll, BD-1-Tempo-Kontext),
(2) vor der echten B-2-Migration hätte ein Umstieg für praktisch alle unmigrierten Projekte
sofort `Soll = 0` geliefert — ein reales Regressionsrisiko. **Kein Doppelzählungsblocker**,
da beide Konsumenten nicht zur zentralen PlanPhase-Kapazität addieren. Diese Entscheidung
bleibt richtig, solange B-2 nicht produktiv ausgeführt ist — sie sollte direkt nach dem
tatsächlichen Cutover (Abschnitt 19, nach Step 7) neu bewertet werden, da `PlanPhase.plan_fte`
dann flächendeckend vorhanden ist und ein Umstieg kein Regressionsrisiko mehr birgt.

---

## 17. Remaining Risks

1. **Migration Dry-Run gegen echte Produktivdaten steht weiterhin aus** — einzige externe
   Vorbedingung vor B-8, siehe Abschnitt 5/6.
2. Zwei kleine, nicht B-8-relevante Code-Funde aus 16.15/16.16 bleiben offen: kein atomarer
   Bulk-Reorder-Endpoint für `PlanPhase.reihenfolge`; einfaches `DELETE /plan-phases/{id}`
   verlässt sich auf DB-seitiges `ON DELETE SET NULL` statt Anwendungscode (unter
   Produktions-Postgres funktional korrekt).
3. Sekundäre Effort-/PPTX-Konsumenten bleiben auf `ResourceDemand.fte` (Abschnitt 16 oben) —
   nach dem echten Cutover erneut bewerten, sonst driftet die PPTX-Folie langfristig von der
   PlanPhase-Kapazität weg.
4. Ohne reale Datenkopie ist unbekannt, ob die Migrationsstrategie "Parent 'Grobplanung
   (migriert)' + Monats-Leafs" bei sehr vielen Grobplanungsperioden/Monaten in der Praxis zu
   unhandlichen Bäumen führt (Abschnitt 18 der Aufgabenstellung) — das lässt sich nur an
   echten Daten beurteilen, nicht synthetisch. Falls sich das im echten Dry-Run als Problem
   zeigt: **STOP**, als konkreten Migrations-Gap dokumentieren und eskalieren, nicht spontan
   die Architektur ändern (siehe Abschnitt 19, Step 4).

---

## 18. GO / NO-GO Checklist

| # | Kriterium | Status |
|---|---|---|
| 1 | Migration Dry Run realistic | 🔴 **NOT RUN** — externe Vorbedingung (keine Produktivdatenkopie in dieser Umgebung) |
| 2 | Apply auf Datenkopie | 🔴 **NOT RUN** — Voraussetzung 1 nicht erfüllt |
| 3 | Orphans = 0 | 🟡 CONFIRMED nur in der synthetischen Fixture, nicht real verifiziert |
| 4 | Cycles = 0 | 🟡 CONFIRMED nur in der synthetischen Fixture |
| 5 | Depth violations = 0 | 🟡 CONFIRMED nur in der synthetischen Fixture |
| 6 | FTE parity | 🟡 CONFIRMED nur in der synthetischen Fixture |
| 7 | Assignments preserved | 🟡 CONFIRMED nur in der synthetischen Fixture |
| 8 | Milestones preserved | 🟡 CONFIRMED nur in der synthetischen Fixture |
| 9 | PlanPhase Tree UI | 🟢 GREEN (CONFIRMED gegen Code, B-6, unverändert) |
| 10 | Direct Assignment | 🟢 GREEN (CONFIRMED gegen Code, B-4, unverändert) |
| 11 | Available Capacity Range | 🟢 GREEN (CONFIRMED gegen Code, B-4/16.16, unverändert) |
| 12 | Planstand Tree Diff | 🟢 GREEN (CONFIRMED gegen Code, B-7/16.16, unverändert) |
| 13 | Gantt Tree | 🟢 GREEN (CONFIRMED gegen Code, B-7, unverändert) |
| 14 | Zentrale Capacity-Konsumenten derived-only | 🟢 GREEN (5 zentrale Endpunkte CONFIRMED, 2 sekundäre Tracks bewusst deferred, kein Doppelzählungsrisiko) |
| 15 | ResourceDemandGrid Removal Dependencies bekannt | 🟢 GREEN (Inventar vollständig, Abschnitt 20 unten) |
| 16 | Subproject Removal Dependencies bekannt | 🟢 GREEN (Inventar vollständig, Abschnitt 20 unten) |
| 17 | Rollback Plan vorhanden | 🟢 GREEN (Abschnitt 20 unten) |
| 18 | CONCEPT aktuell | 🟢 GREEN (dieser Durchgang) |

**Punkte 1/2 sind rot, Punkte 3–8 sind nur gegen die Fixture grün, nicht gegen reale Daten
abgesichert.** Gemäß der verbindlichen Regel dieses Auftrags ("nur wenn ALLE grün: READY,
sonst BLOCKED mit exakten Restblockern") ergibt sich:

## FINAL STATUS: **B-8 CUTOVER BLOCKED**

**Exakter Restblocker (einer, unverändert gegenüber 16.16):** Der realistische Migrations-
Dry-Run gegen eine echte oder repräsentative Kopie der Produktivdaten ist noch nicht erfolgt.
Das ist eine **externe Vorbedingung** (Zugriff auf eine Produktivdaten-Kopie außerhalb dieser
Entwicklungsumgebung), kein Code-Defekt. Alle Code-seitigen B-8-Blocker sind geschlossen.

---

## 19. Final B-8 Cutover Runbook

**Darf erst angestoßen werden, wenn GO/NO-GO Abschnitt 18 vollständig grün ist — also nach
einem tatsächlich durchgeführten, grünen realistischen Dry-Run (Schritt 1/2 extern +
Schritt 3–10 des Runbooks real durchlaufen). Dieser Durchgang stößt keinen der folgenden
Schritte an.**

| Step | Aktion | Hinweis |
|---|---|---|
| 1 | Production Backup | Vollständiger `pg_dump`, verschlüsselt aufbewahrt, unabhängig vom Migrations-Snapshot aus Abschnitt 5 |
| 2 | Backup Restore Test | Das Backup aus Step 1 selbst in eine separate, isolierte DB restaurieren und Applikations-Smoke-Test fahren — verifiziert, dass das Backup im Ernstfall wirklich nutzbar ist |
| 3 | Maintenance / Write Freeze | Schreibzugriff auf die Produktiv-DB einfrieren (Wartungsfenster), damit der finale Snapshot konsistent ist |
| 4 | Migration Dry-Run unmittelbar vor Cutover | `migrate_to_planphase_hierarchy.py` ohne `--apply` gegen die Produktions-DB im Wartungsfenster, `--report-file` archivieren; bei `has_discrepancies == true` → Abbruch, Freeze aufheben, Defekt beheben, diesen Durchgang wiederholen. Bei Migrations-Gap aus Abschnitt 17 Punkt 4: hier prüfen, ob real reproduzierbar — falls ja: **STOP**, eskalieren, nicht weiterlaufen |
| 5 | Apply Migration | Nur bei grünem Step 4: `--apply` gegen dieselbe Produktions-DB, `--report-file` archivieren |
| 6 | Integrity Validation | `has_discrepancies == false` aus Step 5 plus manuelle Stichproben (Abschnitt 20 der Aufgabenstellung: Projekt ohne Subprojects, mit mehreren Subprojects, mit Legacy-Grobplanung, mit Assignments, mit Milestones, mit Monatsgrenzen-Phasen, mit Comments/Blocker/Tasks/Documents) |
| 7 | Capacity Parity | Legacy-Monats-FTE (vor Step 5, aus dem alten `ResourceDemand`-Stand) vs. `compute_project_monthly_capacity` (nach Step 5) je Projekt/Monat vergleichen — 0 Abweichung oder fachlich exakt erklärt, kein stiller Kapazitätsverlust; Vergleichsskript vorher ergänzen (Abschnitt 9 oben) |
| 8 | Enable PlanPhase-only UI | Ab hier ist für alle Projekte ein vollständiger `PlanPhase`-Baum vorhanden — keine UI-Änderung nötig, der bestehende Baum-Flow bedient jetzt auch die migrierten Projekte |
| 9 | Disable ResourceDemandGrid Editing | UI-Zugriffspfad auf `ResourceDemandGrid` deaktivieren (read-only oder ausgeblendet) — **kein Schema-Drop in diesem Step** |
| 10 | Disable Subproject Editing | Subproject-Erstellung/-Bearbeitung im normalen UI deaktivieren — **kein Schema-Drop in diesem Step**, Compat-Tabelle bleibt bestehen |
| 11 | Regression Suite | Vollständiges Backend-Testset (Abschnitt 6 oben) + Frontend-Typecheck gegen die jetzt migrierte Produktions-DB (oder eine frische Kopie davon) |
| 12 | Smoke Tests | Manuelle Kernflows: Projekt öffnen, Phase anlegen/ändern, Person zuordnen, Planstand anlegen, Gantt öffnen — für mindestens je einen migrierten Subproject- und einen migrierten Grobplanungs-Fall |
| 13 | Observation Window | Definierten Zeitraum (z. B. 3–5 Arbeitstage) mit aktivem Monitoring von Cockpit-/Portfolio-Zahlen, bevor Step 14 final entschieden wird |
| 14 | Rollback Decision | Nach Observation Window: bei Auffälligkeiten aus Abschnitt 21 (Rollback Plan) → Rollback; sonst Cutover final bestätigen |
| 15 | CONCEPT Update | Header auf "P18 COMPLETE" setzen, Abschnitt 6 bleibt unverändert (bereits reine Zielarchitektur), Abschnitt 17.8 wird explizit als abgeschlossen markiert ("kein aktiver Codepfad mehr"), Satz "bestehende Projekte nutzen noch ResourceDemandGrid" wird entfernt |

**Kein Schema-Drop im selben Cutover** (Steps 9/10 sind reine UI-/Zugriffs-Deaktivierung, nicht
Tabellen-Drop) — ein separater, späterer Auftrag entscheidet über das tatsächliche Entfernen
von `ResourceDemandGrid`-Code/`subprojects`-Compat-Schema, frühestens nach einem stabilen
Observation Window.

---

## 20. Rollback Plan

**Rollback wird ausgelöst bei mindestens einem der folgenden Befunde** (während oder nach
Step 5–13 des Runbooks in Abschnitt 19):

- Datenverlust (Comments/Tasks/Blocker/Decisions/Documents/Tags/Relations fehlen nach der
  Migration).
- Orphan-Records (`orphan_resource_demands_after != 0` oder ein manueller Fund danach).
- FTE-/Capacity-Parity nicht erklärbar (Abweichung ohne fachlichen Grund, Abschnitt 19 Step 7).
- Projekte lassen sich nach der Migration nicht mehr laden (API/UI-Fehler).
- Assignments fehlen oder sind falsch zugeordnet.
- `PlanPhase`-Baum ist strukturell ungültig (Zyklen, Tiefe > 3, verwaiste Kinder).
- Wichtige Portfolio-/Cockpit-Zahlen sind sichtbar falsch (z. B. Kapazität eines migrierten
  Projekts erscheint als 0 oder doppelt).

**Rollback-Mechanik:** DB-Restore aus dem Backup von Step 1 (Abschnitt 19) **plus**
Zurücksetzen der Applikation auf den Feature-Stand vor Step 8 (PlanPhase-only-UI-Umschaltung
ist rein additiv/kein Schema-Drop, daher unkompliziert reversibel). **Kein Versuch, eine
fehlerhafte Migration manuell in Produktion zu reparieren** — bei einem der obigen Befunde
sofort Rollback, Ursache in Ruhe am Snapshot analysieren, Skript korrigieren, Kopie neu
herstellen (Abschnitt 6 oben) und den gesamten Ablauf erneut von Step 4 an durchlaufen, bevor
ein zweiter Produktiv-Versuch stattfindet.

---

## 21. CONCEPT Rebuild-Safety Assessment

CONCEPT.md erfüllt nach diesem Durchgang die in der Aufgabenstellung (Abschnitt 33) genannten
Rebuild-Kriterien:

| Kriterium | Wo im Dokument |
|---|---|
| Projektstruktur | Abschnitt 4/5 |
| PlanPhase-Funktionsweise | Abschnitt 5.1/6.1–6.3 |
| Parent/Leaf | Abschnitt 6.1/6.1a/6.3 |
| Zeitraumplanung | Abschnitt 5.1/6.2 |
| `plan_fte`-Semantik | Abschnitt 3/6.1a |
| Personenzuordnung | Abschnitt 6.4/6.10 |
| Available Capacity | Abschnitt 6.5/6.11 |
| Monatswerte (derived) | Abschnitt 6.6 |
| Portfolio-Aggregation | Abschnitt 6.6/9 |
| Milestones | Abschnitt 5.5/6.8 |
| Planstände | Abschnitt 5.3/6.14 |
| Tags/Comments/Documents | Abschnitt 8 |
| Integrationen | Abschnitt 7 (Tempo/Jira), Abschnitt 1 (plx.crew Portal) |
| Legacy-Modelle (Kompatibilität) | Abschnitt 6.15 (Kurzfassung) + 17.7/17.8 (volles Detail) |

Ein neues Team, das nur Abschnitte 1–14 liest, sieht **eine** Kapazitätsarchitektur, keine
zwei konkurrierenden Versionen mehr. Historische Entscheidungen (17.7) und der noch aktive,
aber abzulösende Compat-Pfad (17.8) sind eindeutig als solche gekennzeichnet und beeinflussen
keine aktuelle Implementierungsanweisung.

---

## 22. Final Status

**B-8 CUTOVER BLOCKED**

Grund: Der realistische Migrations-Dry-Run gegen eine echte oder repräsentative
Produktivdaten-Kopie ist weiterhin nicht durchgeführt — eine externe Vorbedingung (kein
Zugriff auf eine solche Kopie in dieser Entwicklungsumgebung), kein Code-Defekt. Alle
Code-seitigen B-8-Kriterien sind erfüllt und gegen die synthetische Fixture erneut grün
verifiziert. CONCEPT.md ist jetzt eine bereinigte, eindeutige Rebuild-Spezifikation. Der
vollständige Cutover-Runbook-Plan (Abschnitt 19) liegt bereit, wird aber in diesem Durchgang
**nicht** angestoßen. **Nächster Schritt:** Schritt 1/2 des Migrations-Runbooks
(`backend/scripts/MIGRATION_DRY_RUN_RUNBOOK.md`) extern durchführen (Produktivdaten-Snapshot
beziehen, isoliert restaurieren), danach Schritt 3–10 gegen die reale Kopie durchlaufen, das
GO/NO-GO-Gate ein weiteres Mal ausführen, und erst danach den produktiven Cutover (Abschnitt
19) in einem separaten, explizit freigegebenen Auftrag anstoßen.
