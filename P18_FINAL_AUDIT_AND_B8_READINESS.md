# P18 FINAL AUDIT & B-8 READINESS REPORT

**Datum:** 2026-08-22
**Scope:** Verifikation von B-1–B-7 gegen realen Code (nicht gegen CONCEPT.md-Selbstauskunft),
Migrations-Dry-Run, Kapazitäts-Konsumenten-Matrix, Legacy-Inventar (`ResourceDemandGrid`,
`Subproject`), CONCEPT.md-IST-Korrektur, finaler B-8-Cutover-Plan.
**Keine produktive Migration ausgeführt, kein Legacy-Code gelöscht, keine Subproject-Tabellen
gedroppt, keine compat-Felder entfernt, keine irreversible Datenänderung.**

---

## 1. Executive Summary

Die im CONCEPT.md-Abschnitt 16.7–16.14 dokumentierten Implementierungs-Claims für B-1 bis B-7
sind **überwiegend zutreffend und wurden unabhängig gegen den realen Code bestätigt** —
inklusive Live-Ausführung aller sechs bestehenden Verifikationsskripte gegen
Wegwerf-SQLite-Datenbanken. Die produktive Zielarchitektur (`PlanPhase`-Baum, Direktzuweisung
ohne Rollenzwang, bereichsbasierte Available Capacity, abgeleitete Monats-/Portfoliokapazität,
Baum-UX in Liste/Gantt/Workspace, `Milestone.plan_phase_id`) ist **implementiert, verdrahtet und
funktional**, nicht nur spezifiziert.

Der Audit fand jedoch **sieben Einzel-Defekte**, von denen drei explizit gegen die in dieser
Aufgabenstellung genannten Kriterien verstoßen (Planstand-"Phase hinzugefügt"-Erkennung fehlt
vollständig, Legacy-Candidate-Endpoint ist nicht bereichsbasiert, Migrations-Dry-Run lief nur
gegen eine synthetische Fixture statt gegen einen echten Produktions-Snapshot). Zusätzlich wurde
**kein** Doppelzählungs-Blocker gefunden: keiner der fünf zentralen Portfolio-/Cockpit-/
GAP-Endpunkte summiert `ResourceDemand.fte` mehr als Projektbedarf.

Die im Auftrag vorgegebene GO/NO-GO-Regel ("Wenn ein Punkt rot: B-8 CUTOVER BLOCKED") führt
damit zu **B-8 CUTOVER BLOCKED** — nicht wegen eines Architekturproblems, sondern wegen
konkreter, klein-skalierter Nacharbeiten plus des noch ausstehenden echten
Produktions-Dry-Runs. CONCEPT.md wurde in diesem Durchgang auf den echten IST-Stand korrigiert.

**Status: B-8 CUTOVER BLOCKED.**

---

## 2. B-1 Audit — Hierarchy Foundation

| # | Punkt | Status | Beleg |
|---|---|---|---|
| 1 | `PlanPhase.parent_phase_id` (self-FK, nullable) | CONFIRMED | Migration `0005:57-65`, `models.py:550-552`, indiziert, kein `ondelete` (NO ACTION) |
| 2 | `PlanPhase.reihenfolge` | CONFIRMED | `0005:59-61` (NOT NULL, default 0), `models.py:555` |
| 3 | `Milestone.plan_phase_id` | CONFIRMED | `0005:68-73` (`ON DELETE SET NULL`, indiziert), `models.py:603-605` |
| 4 | `PlanHistory.plan_phase_id` | CONFIRMED | `0005:76-81`, `models.py:284-286` |
| 5 | `ResourceRole.is_system_role` + Seed "Ohne Rolle" | CONFIRMED | `0005:84-103` (Seed genau einmal), `models.py:675`, `resource_roles.name` UNIQUE (`models.py:667`) erzwingt Einzigartigkeit |
| 6 | Migration Upgrade/Downgrade symmetrisch | CONFIRMED | `downgrade()` `0005:106-133` kehrt Reihenfolge korrekt um; live per `check_migrations.py` verifiziert (Roundtrip clean) |
| 7 | `models.py` == Migration (kein Drift) | CONFIRMED | 1:1 Abgleich aller 4 geänderten Tabellen |

**Caveat (kein Blocker, aber ein reales Risiko):** `ON DELETE SET NULL` und die self-referencing
FK werden unter dem **lokalen SQLite-Standard ohne `PRAGMA foreign_keys=ON`** nicht durchgesetzt
— `backend/app/database.py` aktiviert dieses Pragma nirgends. Produktionsziel ist Postgres
(`docker-compose.yml`), wo die Constraints greifen. Für Postgres kein Blocker; für lokale
Entwicklung/Tests ein Robustheits-Gap (siehe Defekt 5, Abschnitt 13).

**B-1: CONFIRMED.**

---

## 3. B-2 Migration Audit

- **Sicherheitsdefault bestätigt:** Ohne `--apply` läuft `migrate_to_planphase_hierarchy.py`
  ausschließlich als Dry-Run mit Rollback (`migrate()` Zeile 306-373: `db.commit()` nur
  `if apply:`, sonst `db.rollback()`).
- **Migrationsstrategie für Alt-Grobplanung: Variante A** (wie in Abschnitt 6b.12 der
  CONCEPT.md final festgelegt) — pro Projekt eine neue Parent-Top-Level-Phase "Grobplanung
  (migriert)", darunter eine Monats-Leaf-Kindphase je migrierter Periode, `plan_fte` der
  Leaf-Phase einmalig aus `SUM(ResourceDemand.fte)` dieser Periode abgeleitet
  (`_migrate_grobplanung()`, `migrate_to_planphase_hierarchy.py:187-276`). **Nicht** Variante B
  (Monats-Leafs direkt Top-Level).
- **Subproject-Migration:** pro `Subproject` eine neue Top-Level-Parent-`PlanPhase`, bestehende
  `PlanPhase`-Kinder reparented, `Milestone`/`Comment` auf `plan_phase_id` umgehängt,
  `subprojects`/`subproject_id` bleiben unverändert (compat-only).
- **Orphan-/Depth-/Cycle-Checks sind harte Diskrepanzen, keine weichen Warnungen** —
  `_compute_hierarchy_depth_violations()` (Zeile 279-303) läuft über den **gesamten**
  `PlanPhase`-Bestand (nicht nur neu erzeugte Zeilen) und erkennt sowohl Tiefenverletzung > 3 als
  auch Zyklen; `MigrationReport.has_discrepancies` (Zeile 92-103) prüft zusätzlich FTE-Summen
  vorher/nachher, Milestone-Zählungen und `orphan_resource_demands_after` — jede Abweichung
  kippt den Exit-Code auf 1.
- **Idempotenz bestätigt:** beide Migrationszweige filtern auf "noch nicht migriert"
  (`parent_phase_id IS NULL` bzw. offene Grobplanungs-Demands) — ein zweiter Lauf findet nichts
  mehr.

**Live-Testlauf gegen synthetische Fixture** (`test_migrate_to_planphase_hierarchy.py`, eigene
Wegwerf-SQLite-DB): 1 Subproject + 2 Kindphasen + 1 Milestone + 1 Comment, 2 Grobplanungs­perioden
× 2 Rollen + 1 Assignment.

```
subprojects_migrated=1, subproject_children_reparented=2,
grobplanung_month_leaves_created=2, resource_demands_reassigned=4,
fte_sum_before=3.0 (0.8+0.7+1.0+0.5)
```

Dry-Run schreibt nichts (verifiziert), Apply verlustfrei (Milestones/Comments/Assignments/
Demands-Zahlen vor/nach identisch, 0 Orphans danach), Re-Run nach Apply idempotent (nichts mehr
zu migrieren).

**Residuales Risiko:** In dieser Umgebung existiert **keine populierte Produktiv-/
Realdaten-Datenbank** — der Dry-Run konnte deshalb nur gegen die synthetische Fixture gefahren
werden, nicht gegen einen echten Produktions-Snapshot. Das ist exakt der in Abschnitt 24/Step 2
des B-8-Plans vorgesehene, noch ausstehende nächste Schritt — kein Fehler dieses Audits, aber
ein offener Punkt vor dem tatsächlichen Cutover.

**B-2: CONFIRMED (Tooling), produktive Ausführung weiterhin ausstehend.**

---

## 4. B-3 Tree API Audit

| # | Punkt | Status | Beleg |
|---|---|---|---|
| 1 | Parent muss im selben Projekt liegen | CONFIRMED (alle Pfade) | `_check_parent_phase`, `planning.py:71-72`, aufgerufen von create/update/reparent |
| 2 | Selbst-Parent blockiert | CONFIRMED | `planning.py:74-77` |
| 3 | Zyklus blockiert (auch bei Teilbaum-Reparenting) | CONFIRMED | `planning.py:78-83` via `planning_calc.all_descendants()` |
| 4 | Max. Tiefe 3 | CONFIRMED | `planning_calc.py:15` `MAX_HIERARCHY_DEPTH=3`, inkl. Teilbaum-Höhen-Korrektur (`subtree_max_depth`) |
| 5 | Kind anlegen | CONFIRMED | `POST /projects/{id}/plan-phases` |
| 6 | Reparent | CONFIRMED | `POST /plan-phases/{id}/reparent-children` |
| 7 | Reorder (`reihenfolge`) | **PARTIAL** | Nur Einzelfeld-Update via generisches `PUT`; **kein atomarer Bulk-Reorder-Endpoint** (anders als bei `Project.reihenfolge`, `routers/projects.py:120-132`), keine Uniqueness-Prüfung gegen doppelte Geschwister-Reihenfolge |
| 8 | `has_children` (berechnet) | CONFIRMED | `planning_calc.py:18-21`, EXISTS-Subquery |
| 9 | Parent-Aggregation (Zeitraum + Kapazität) | CONFIRMED | `derive_parent_bounds`/`derive_parent_capacity`, `planning_calc.py:83-98` |
| 10 | Delete Guard (BD-11, 409 bei Kindern) | **PARTIAL** | Block-Verhalten CONFIRMED (`planning.py:454-476`); einfaches Leaf-`DELETE` nullt abhängige Zeilen aber **nicht defensiv im Anwendungscode** — verlässt sich auf DB-`ON DELETE SET NULL`, das unter lokalem SQLite (B-1-Caveat) wirkungslos ist |
| 11 | Subtree-Delete | CONFIRMED | `POST /plan-phases/{id}/delete-subtree`, verlangt exakte Bestätigung, nullt Collaboration-Referenzen explizit im Code |
| 12 | Leaf→Parent-Historisierung | CONFIRMED (alle 3 Pfade) | `_maybe_historize_parent_fte`, `planning.py:104-124` |
| 13 | Parent→Leaf: keine Auto-Reaktivierung | CONFIRMED (durch Abwesenheit) | Kein Codepfad setzt `plan_fte` außer Zeile 124 |

**Live-Testlauf** (`test_planning_phase_tree_api.py`, `TestClient` gegen echte FastAPI-App,
Wegwerf-SQLite): alle 7 Schritte grün — 3-Ebenen-Baum, Tiefe-4-Ablehnung (422), Zyklus-Ablehnung
(422), projektfremder Parent (422), Leaf→Parent-Historisierung, BD-11-409-Block, Reparent +
Delete, Subtree-Impact/-Delete inkl. Collaboration-Erhalt.

**B-3: CONFIRMED für den Kern, zwei dokumentierte Einzel-Gaps (#7, #10).**

---

## 5. B-4 Resource Planning Audit

| # | Punkt | Status | Beleg |
|---|---|---|---|
| 1 | Direktzuweisung ohne sichtbare Rollenauswahl | CONFIRMED | `AssignPersonForm`, `PlanPhaseCapacityTab.tsx:33-117` → `POST /plan-phases/{id}/assign-person` |
| 2 | Backend nutzt intern Systemrolle | CONFIRMED | `_get_or_create_carrier_demand`, `planning.py:707-744` |
| 3 | Systemrolle im normalen Picker unsichtbar | CONFIRMED | `GET /resource-roles` filtert `is_system_role.is_(False)` per Default, `capacity.py:40-50` |
| 4 | Systemrolle nicht löschbar | **MISSING (folgenlos)** | Es existiert **kein** `DELETE /resource-roles/{id}`-Endpoint überhaupt — die Regel ist damit durch Abwesenheit erfüllt, nicht durch einen Guard |
| 5 | Systemrolle nicht im Skill-Matching | CONFIRMED (weil Feature nicht existiert) | `CandidatePersonOut`-Docstring (`schemas.py:763-767`): Skills sind rein informativ, nie Filterkriterium — für **keine** Rolle |
| 6 | UI zeigt "Ohne Rolle" nie an | CONFIRMED | Keine Fundstelle im gesamten Frontend |
| 7 | Assignments verändern `plan_fte` nie | CONFIRMED | Einziger `plan_fte = ...`-Schreibpfad außerhalb Create/Update ist `_maybe_historize_parent_fte` (Struktur-Übergang, nicht Assignment) |
| 8 | Bedarf/Besetzt/Offen (0,40/0,20/0,20) | CONFIRMED, live getestet | `phase_metrics_calc.assignment_summary` |
| 9 | Überbesetzt (0,40/0,50/−0,10, `plan_fte` unverändert) | CONFIRMED, live getestet | dieselbe Funktion, Testscript-Assertion Zeile 133-136 |

**Available Capacity (bereichsbasiert):**

- `compute_person_capacity_for_range` — CONFIRMED, iteriert Kalendermonate, wiederverwendet
  `compute_person_capacity` pro überlapptem Monat (keine zweite Engine).
- `GET /plan-phases/{id}/assignment-candidates` (Haupt-Flow) — CONFIRMED bereichsbasiert.
- `GET /resource-demands/{id}/candidates` (**Legacy-Rollen-Sub-Flow**, weiterhin erreichbar über
  "Rollen aufschlüsseln") — **CONFLICT**: prüft weiterhin nur `ResourceDemand.period`
  (Einzelmonat), nicht die volle Phasen-Range.
- Testabdeckung: Werktage-Gewichtung über Monatsgrenze und Grundfall-Kandidaten-Ausschluss sind
  automatisiert getestet; Absence/Holiday/InternalAllocation/fehlendes Kapazitätsprofil/bereits
  überbuchte Person sind **nicht** spezifisch für die Range-Funktion abgedeckt (Code-Pfade
  existieren, aber ohne Regressionstest).

**B-4: CONFIRMED für den Haupt-Flow, drei dokumentierte Einzel-Gaps (#4, Legacy-Candidates, Testabdeckung).**

---

## 6. B-5 Capacity Source-of-Truth Audit

- `phase_metrics_calc.monthly_distribution()` — CONFIRMED, Formel exakt wie spezifiziert
  (`overlap_start=max(...)`, `overlap_end=min(...)`, `weekdays_m/weekdays_total`-Gewichtung,
  kein 50/50, kein Feiertagsabzug).
- `compute_project_monthly_capacity()` — CONFIRMED, summiert über **alle** `PlanPhase`s eines
  Projekts; sicher, weil `monthly_distribution(None, ...) = {}` und jede Parent-Phase
  nachweislich `plan_fte = None` trägt (**Dateninvariante**, nicht nur Query-Filter) —
  `_maybe_historize_parent_fte` erzwingt das auf jedem Parent-erzeugenden Pfad.
- **Kein aktiver `max(Grobplanstunden, Feinplanstunden)`-Codepfad** — alle `max(`-Fundstellen
  sind unrelated (Datumsclamping, Health-Scoring, Ordering).
- **Kein Blocker:** `ResourceDemand.fte`/`ResourceAssignment.fte` werden an keiner Stelle
  zusätzlich zur PlanPhase-Kapazität summiert.

**B-5: CONFIRMED, kein Blocker.** Details siehe Kapazitäts-Konsumenten-Matrix (Abschnitt 12).

---

## 7. B-6 UX Audit

| Bereich | Status | Beleg |
|---|---|---|
| Echte rekursive Baumdarstellung (Liste + Gantt) | CONFIRMED | `PlanPhaseList.tsx:58-166` (`childrenOf`-Map, `renderPhase` rekursiv, Einrückung nach `depth`) |
| "+ Unterphase"-Aktion, tiefenbegrenzt | CONFIRMED | 3 Stellen: `PlanPhaseList.tsx:108-120`, `PlanPhaseWorkspace.tsx:172-176`, `PlanPhaseCreateModal.tsx:89` |
| Leaf zeigt Zeitraum/Plan-FTE/Direktzuweisung/Available Capacity/optionale Rollen | CONFIRMED | `PlanPhaseWorkspace.tsx`/`PlanPhaseCapacityTab.tsx`, siehe Detailbelege im Audit |
| Parent zeigt read-only aggregierte Werte, keine Kapazitätseingabe/Assignments | CONFIRMED | `PlanPhaseWorkspace.tsx:227-241,273,389-412` |
| Keine rohen technischen Begriffe in UI-Texten | CONFIRMED | Grep über alle `.tsx`: nur in Variablennamen/Typen/Kommentaren, nie in JSX-Textknoten |
| Alle 8 geforderten deutschen UX-Begriffe vorhanden | CONFIRMED | Übergeordnete Phase, Unterphase, Geplanter Ressourcenbedarf, Personenbesetzung, Bedarf, Besetzt, Offen, Überbesetzt |

**B-6: CONFIRMED.**

---

## 8. B-7 Gantt/Milestone/Planstand Audit

- **Milestones:** `plan_phase_id` operativ (NULL = projektweit, gesetzt = Leaf oder Parent, keine
  Hierarchie-Einschränkung) — CONFIRMED. `MilestoneList.tsx` zeigt nur noch
  "Übergeordnete Phase", kein "Teilprojekt"-Feld mehr. Migrationsskript hängt
  Subproject-Milestones idempotent auf `plan_phase_id` um — CONFIRMED.
- **Planstand-Snapshot-Felder:** `_SNAPSHOT_FIELDS` enthält `parent_phase_id`/`reihenfolge`
  (PlanPhase) und `plan_phase_id` (Milestone) — CONFIRMED.
- **Planstand-Deviation-Erkennung — PARTIAL:**
  - Zeitraum geändert — CONFIRMED
  - Plan-FTE geändert — CONFIRMED
  - Parent geändert — CONFIRMED, live regressionsgetestet
  - Reihenfolge geändert — bewusst **nicht** erkannt (korrekt wie spezifiziert)
  - **Phase hinzugefügt — MISSING.** `compute_deviations` iteriert nur zum Snapshot-Zeitpunkt
    eingefrorene `BaselineEntry`-Zeilen; eine nach dem Planstand neu angelegte Phase wird nie
    verglichen und taucht nie als Abweichung auf.
  - **Phase entfernt — PARTIAL.** Kein explizites "entfernt"-Flag; alle eingefrorenen Felder
    zeigen stattdessen "geändert auf `None`". Zusätzlicher Detail-Gap: Die
    Gruppenkopfzeile fällt in diesem einen Fall auf eine rohe `#<id>` zurück
    (`entity_summary` liefert `None` für eine gelöschte Zeile) — die einzige Stelle im gesamten
    Audit, an der eine rohe ID tatsächlich in der UI sichtbar würde.
- **Gantt:** liest dieselbe Datenquelle wie `PlanPhaseList` (kein Parallelmodell), Parent =
  umrandete Hüllkurve, Leaf = gefüllter Balken, beide öffnen denselben `PlanPhaseWorkspace`,
  vollständig read-only (kein Drag/Resize, keine API-Schreibaufrufe) — CONFIRMED.

**B-7: CONFIRMED für Milestones/Gantt, PARTIAL für Planstand-Deviation-Erkennung.**

---

## 9. Legacy ResourceDemandGrid Inventory

- **Einzige Verwendungsstelle:** `ProjectPlanningTab.tsx:8` (Import), `:86` (Render). Kein
  weiterer Importeur im gesamten Frontend.
- **Genutzte Endpoints** (alle auch von `PlanPhaseCapacityTab.tsx` mitgenutzt — **nicht**
  exklusiv für das Grid): `GET/POST/PUT/DELETE /projects/{id}/resource-demands`,
  `GET /resource-demands/{id}/assignments`, `POST/DELETE .../resource-assignments`,
  `GET /resource-demands/{id}/candidates`, `GET /resource-roles`.
- **Component-State:** ausschließlich lokale `useState`, keine komponentenspezifischen Custom
  Hooks.
- **Client-seitige Berechnung:** keine wesentliche — alle FTE-/Gap-Werte kommen vorberechnet vom
  Backend.
- **Tests:** keine (weder Frontend- noch Backend-Tests referenzieren die Komponente direkt).
- **Andere Abhängigkeiten:** keine weiteren Importeure; die geteilten Typen (`ResourceDemand`,
  `ResourceAssignment` in `types.ts`) werden weiterhin von `PlanPhaseCapacityTab.tsx` benötigt
  und dürfen bei einer Entfernung **nicht** gelöscht werden.

**Removal-Checkliste (auszuführen, sobald B-8 freigegeben ist — NICHT in diesem Durchgang):**

1. Bestätigen, dass die B-2-Migration in allen relevanten Umgebungen produktiv gelaufen ist.
2. `<ResourceDemandGrid .../>`-Render in `ProjectPlanningTab.tsx:86` entfernen.
3. `import ResourceDemandGrid …` in `ProjectPlanningTab.tsx:8` entfernen.
4. Prüfen, ob `draft.monate` (Props für das Grid) nach der Entfernung noch anderweitig gebraucht
   wird; sonst mit entfernen.
5. `frontend/src/views/project/components/ResourceDemandGrid.tsx` löschen.
6. **Nicht** die zugrunde liegenden `/resource-demands`-Endpoints entfernen —
   `PlanPhaseCapacityTab.tsx` benötigt sie weiterhin für die optionale Rollen-Aufschlüsselung.
7. **Nicht** die `ResourceDemand`/`ResourceAssignment`-Typen in `types.ts` löschen (weiterhin
   von `PlanPhaseCapacityTab.tsx` genutzt).
8. Kein API-Client-Cleanup nötig — keine Methode ist exklusiv für das Grid.

---

## 10. Legacy Subproject Inventory

| Layer | Ort | Noch aktiv? | Notiz |
|---|---|---|---|
| Backend-Modell | `models.py:43-53` `Subproject`, FK auf `Comment`/`PlanHistory`/`PlanPhase`/`Milestone` | Ja (Schema) | Compat-only laut Kommentar |
| Backend-Router `/subprojects/*` | `routers/projects.py:285-330` | Aktiv, aber `@deprecated` dokumentiert | Docstring benennt B-7/B-8 als Ablösung |
| Backend `planning.py` | `_check_subproject`, PlanPhase/Milestone Create/Update | Aktiv | Validiert weiterhin FK |
| Backend-Schemas | `schemas.py` diverse `Subproject*`-Schemas | Aktiv | — |
| Export | `routers/export.py:36,41-42,59-60,99` | Aktiv | Gruppiert Export-Output nach `subproject_id` |
| Frontend `PlanPhaseList.tsx`/`PlanPhaseGantt.tsx` | — | **Nicht mehr aktiv** | Vollständig auf `parent_phase_id` umgestellt |
| Frontend `MilestoneList.tsx` | — | **Nicht mehr aktiv** | Kein `subproject`-Bezug mehr |
| Frontend `ProjectPlanningTab.tsx` | Zeile 25-52, 93-95 | **Aktiv (Live-CRUD-UI)** | Eigenes Formular für Teilprojekt-Anlage/-Löschung |
| Frontend `ProjectHistoryTab.tsx` | Zeile 7-11, 34-35 | **Aktiv** | Pro-Teilprojekt-Historie-Sektion |
| Frontend `ProjectCommunicationTab.tsx` | Zeile 63, 67, 184, 189, 193 | **Aktiv** | Kommentare filterbar/gruppiert nach Teilprojekt |
| Tests | `test_migrate_to_planphase_hierarchy.py` | Migrationstest | Keine Frontend-Tests existieren |

**Wichtiger Unterschied zur bisherigen CONCEPT.md-Aussage:** Subproject ist **nicht** nur noch in
`ProjectPlanningTab.tsx` aktiv — auch `ProjectHistoryTab.tsx` und `ProjectCommunicationTab.tsx`
haben eigene, funktionale Subproject-Abhängigkeiten. Ein B-8-Cutover muss alle drei
Frontend-Stellen berücksichtigen, nicht nur eine.

---

## 11. Migration Dry-Run Results

Siehe Abschnitt 3 (B-2 Migration Audit) für Details. Zusammenfassung:

- `check_migrations.py`: **PASS** — genau ein Head (`0005`), Kette intakt, kein Drift, Seeds
  vollständig (inkl. Systemrolle "Ohne Rolle" = genau 1×), Downgrade/Upgrade-Roundtrip sauber.
- `test_migrate_to_planphase_hierarchy.py`: **PASS** gegen synthetische Fixture — Variante A
  bestätigt, FTE-Summe vorher=nachher erhalten, 0 Orphans, idempotenter Re-Run.
- `test_direct_assignment_and_capacity_range.py`, `test_derived_monthly_capacity.py`,
  `test_milestone_and_baseline_tree.py`, `test_planning_phase_tree_api.py`: alle **PASS**.
- **Keine Warnung wurde ignoriert** — alle Skripte werten Diskrepanzen als harten Fehler
  (Exit-Code 1), nicht als weiche Warnung.
- **Offen:** kein Dry-Run gegen einen echten Produktions-Snapshot (siehe B-8-Plan Step 2).

---

## 12. Capacity Consumer Matrix

| Consumer | Quelle | Leaf-only? | Status |
|---|---|---|---|
| GAP Engine Capacity (`GET /gap-engine/capacity`) | `compute_capacity_gap` → `compute_portfolio_planphase_demand_fte` | Ja (Invariante) | CONFIRMED derived-only |
| Capacity Heatmap (`GET /controlling/capacity-heatmap`) | dieselbe Funktion | Ja | CONFIRMED derived-only |
| Cockpit Capacity (`_cockpit_capacity`) | `compute_project_monthly_capacity` (`demand_fte`), `assigned_fte` separat, nie addiert | Ja | CONFIRMED derived-only |
| Project Monthly Capacity (`GET /projects/{id}/capacity/monthly`) | `compute_project_monthly_capacity` direkt | Ja | CONFIRMED derived-only |
| Portfolio-Demand (`compute_portfolio_planphase_demand_fte`) | Summe über alle Projekte | Ja | CONFIRMED derived-only |
| Allocation Gaps / Role Analysis (Controlling) | `ResourceDemand`/`ResourceAssignment`, Rollen-Ebene | N/A (Rollen-Layer) | CONFIRMED, kein Beitrag zur Projektkapazität |
| Utilization Gap (Personenebene) | `ResourceAssignment` vs. `compute_person_capacity` | N/A (Personen-Layer) | CONFIRMED, kein Beitrag |
| Project Health "Aufwand" (`health_calc._effort_health`) | `gap_analysis._soll_je_monat` → `SUM(ResourceDemand.fte)` | Nein | **PARTIAL** — eigener Soll-/Ist-Track, nicht doppelt gezählt, noch nicht umgestellt |
| PPTX-Export "fte"-Feld (`export.py`) | dieselbe `_soll_je_monat`-Quelle | Nein | **PARTIAL** — Deck zeigt ResourceDemand-Balken, nicht die P18-Kapazität |

**BLOCKER-Prüfung: NEIN.** Für keinen der fünf zentralen Portfolio-/Cockpit-/GAP-Endpunkte wird
`ResourceDemand.fte` zusätzlich zur PlanPhase-Kapazität summiert. Die beiden PARTIAL-Zeilen sind
separate, dokumentierte Soll-/Ist-Tracks (Tempo-Abgleich, Export-Legende).

---

## 13. Identified Defects / Gaps

1. **Planstand erkennt "Phase hinzugefügt" gar nicht**, "Phase entfernt" nur unvollständig (inkl.
   Roh-ID-Leck in der Gruppenkopfzeile bei gelöschter Phase). *(betrifft explizit geforderte
   Deviation-Erkennung, Abschnitt 8 B-7)*
2. **Legacy-Candidate-Endpoint `GET /resource-demands/{id}/candidates` ist nicht bereichsbasiert**
   (nur Einzelmonat), im Gegensatz zum neuen Haupt-Flow-Endpoint. *(betrifft explizit geforderte
   Range-basierte Candidate-Preview, Abschnitt 6)*
3. **Kein Backend-Guard gegen Löschen der Systemrolle** — aktuell folgenlos, weil kein
   `DELETE /resource-roles/{id}` existiert, aber die dokumentierte Governance-Regel ist nicht
   durch Code erzwungen.
4. **Kein atomarer Bulk-Reorder-Endpoint für `PlanPhase.reihenfolge`**, keine
   Eindeutigkeitsprüfung gegen doppelte Geschwister-Reihenfolge.
5. **Einfaches `DELETE /plan-phases/{id}` verlässt sich auf DB-`ON DELETE SET NULL`** statt
   abhängige Zeilen defensiv im Anwendungscode zu entkoppeln — unter lokalem SQLite ohne
   `PRAGMA foreign_keys=ON` (Repo-Standard) demonstrierbar wirkungslos; unter Produktions-Postgres
   funktional, aber nicht applikationsseitig abgesichert.
6. **Testabdeckung für `compute_person_capacity_for_range`** deckt Absence/Holiday/
   InternalAllocation/fehlendes Kapazitätsprofil/bereits überbuchte Person nicht ab.
7. **Migrations-Dry-Run bisher nur gegen synthetische Fixture**, nicht gegen echten
   Produktions-Datenbestand.

Keine der sieben Defekte ist ein Architektur- oder Datenverlust-Risiko — alle sind lokal
begrenzte, klein-skalierte Nacharbeiten.

---

## 14. Fixes Performed

**Keine Code-Änderungen in diesem Durchgang.** Ausschließlich CONCEPT.md wurde korrigiert (siehe
Abschnitt 15). Die in Abschnitt 13 gelisteten Defekte sind **Findings, keine in diesem
Audit-Durchgang behobenen Fixes** — sie erfordern Code-Änderungen, die außerhalb des
Audit-/Dokumentations-Scopes dieses Durchgangs liegen (Minimal-Change-Prinzip, `AGENTS.md`
Abschnitt 16/17: "Ein Task sollte nicht unnötig gleichzeitig Datenmodell/Migration/Backend/API/
Frontend verändern"). Empfehlung: jede der sieben Defekte als eigener, kleiner Folge-Task.

---

## 15. CONCEPT.md Changes

Durchgeführt in diesem Durchgang (`CONCEPT.md`, Commit siehe Git-Historie):

- **Kopfbereich (Zeilen 1–30):** Version v0.21 → v0.22, veraltete Aussage "P18 ist ein reiner
  Design-Durchgang, kein Produktcode/Frontend geändert" durch den tatsächlichen B-1–B-8-Status
  (B-1–B-7 IMPLEMENTED/CONFIRMED, B-8 BLOCKED) ersetzt.
- **"Wie dieses Dokument zu lesen ist":** Ausnahme-Regel für Abschnitt 6a als "P18-Design, noch
  nicht implementiert" entfernt (war stale); klargestellt, dass 6b jetzt IST-Verhalten für neue
  Planung ist, Abschnitt 6 nur noch für unmigrierte Alt-Projekte technisch aktiv bleibt.
- **Abschnitt 3 (Kernprinzipien):** Disclaimer "kein umgesetztes Verhalten" korrigiert auf
  "gegen Code CONFIRMED umgesetzt für neue PlanPhase-Bäume, Alt-Pfad bleibt bis B-8 aktiv".
- **Abschnitt 4 (Datenmodell):** Tabelle von "ZIEL P18, noch nicht implementiert" auf tatsächlich
  vorhandene Felder/Verhalten umgestellt, inkl. Benennung der in Abschnitt 13 gefundenen
  Einzel-Gaps direkt in den betroffenen Zeilen (Planstand-Deviation, Systemrolle-Delete-Guard).
- **Abschnitt 5.1/5.4/5.5/5.6:** "optionales Teilprojekt" als primäres PlanPhase-Feld ersetzt
  durch "Übergeordnete Phase"; Subproject-Abschnitt zu "Legacy/IST-Hinweis" mit korrigiertem,
  vollständigerem Aktiv-Inventar (inkl. `ProjectHistoryTab`/`ProjectCommunicationTab`);
  Milestone-/Gantt-Abschnitte auf `plan_phase_id` als primäre Verknüpfung umgestellt.
- **Abschnitt 6:** Umbenannt zu "Legacy-Pfad, aktiv nur für unmigrierte Alt-Projekte" mit
  Erklärung, warum er trotzdem noch aktiver Code ist.
- **Abschnitt 6b:** Kopfzeile von "noch nicht implementiert" auf "B-1–B-7 IMPLEMENTIERT und
  gegen Code CONFIRMED, B-8 BLOCKED" korrigiert, inkl. Verweis auf diesen Audit.
- **Abschnitt 13 (Source-of-Truth-Matrix):** Grobplanung/Projektmonatskapazität-Zeilen auf
  tatsächlichen Stand aktualisiert.
- **Abschnitt 15 (Deferred Features):** P18-Pass-2-Eintrag von "wartet auf Umsetzung" auf
  "B-1–B-7 nicht mehr deferred, nur B-8 bleibt deferred" korrigiert.
- **Neuer Abschnitt 16.15:** Vollständige Dokumentation dieses Final-Audit-Durchgangs inkl.
  Kapazitäts-Konsumenten-Matrix, Defekt-Liste, GO/NO-GO-Tabelle.

**Nicht verändert (bewusst):** Abschnitt 6a (P18 Pass 1) bleibt als Historie/superseded stehen,
keine Umnummerierung der Abschnitte 6/6a/6b auf die im Auftrag vorgeschlagene 6.1–6.6-Struktur
(Abschnitt 22 der Aufgabenstellung) — eine solche Umnummerierung würde die umfangreiche
Querverweis-Struktur im gesamten 2400+-Zeilen-Dokument brechen und ist als eigener,
dokumentationsonly Folge-Task empfohlen, nicht als Teil dieses Audits (Minimal-Change-Prinzip).

---

## 16. Final B-8 Cutover Plan

**Voraussetzung für Start:** Defekte 1 und 2 (Abschnitt 13) geschlossen — das sind die beiden
Punkte, die direkt gegen explizite Akzeptanzkriterien dieser Aufgabenstellung verstoßen.

**STEP 1 — Production Backup / Restore Test**
Vollständiges Backup der Produktions-DB erstellen, Restore auf einer separaten Instanz
verifizieren (nicht nur Backup-Datei-Existenz prüfen — echten Restore-Lauf durchführen).

**STEP 2 — Migration Dry-Run gegen Production Snapshot**
`migrate_to_planphase_hierarchy.py` (ohne `--apply`) gegen eine Kopie des echten
Produktions-Snapshots ausführen (nicht gegen die synthetische Fixture dieses Audits). Vollen
Report einsehen: Projects/Subprojects/PlanPhases/ResourceDemands/Assignments/Milestones,
FTE-Summen vorher/nachher, Orphans, Hierarchietiefe/Zyklen.

**STEP 3 — Migration Report Review**
Report von mindestens zwei Personen (Entwicklung + fachlicher Owner) gegenlesen. Jede
Diskrepanz (Orphan > 0, FTE-Abweichung, Tiefenverletzung) muss erklärt oder behoben werden, bevor
fortgefahren wird — keine Warnung wird ignoriert.

**STEP 4 — Maintenance / Write Freeze (falls nötig)**
Je nach Ausführungsdauer und Nutzungsmuster: kurzes Wartungsfenster mit Schreibsperre auf
`ResourceDemand`/`PlanPhase`/`Subproject`/`Milestone`, um Race Conditions während der Migration
auszuschließen.

**STEP 5 — Apply Migration**
`migrate_to_planphase_hierarchy.py --apply` gegen die echte Produktions-DB. Report archivieren.

**STEP 6 — Post-Migration Integrity Checks**
`check_migrations.py` erneut laufen lassen; zusätzlich stichprobenartig einzelne migrierte
Projekte manuell im Frontend prüfen (Baum korrekt, Milestones korrekt verknüpft, Kommentare/
Tasks/Blocker/Decisions nicht verloren).

**STEP 7 — Capacity Parity Checks**
Für eine Stichprobe von Projekten: `GET /projects/{id}/capacity/monthly` vor und nach der
Migration vergleichen (sollte durch die Migration selbst unverändert bleiben, da B-5 bereits
produktiv liest — die Migration verschiebt nur die Datenquelle von "Grobplanung" zu
"Grobplanung (migriert)"-Leaf-Phasen, die Summe darf sich nicht ändern).

**STEP 8 — Enable PlanPhase-only UX**
Kein Feature-Flag-Schalter nötig (B-6/B-7 sind bereits produktiv aktiv) — dieser Schritt ist im
Wesentlichen bereits erledigt, dient hier nur als Bestätigungspunkt im Plan.

**STEP 9 — Disable ResourceDemandGrid**
Erst nachdem STEP 5–7 für alle Projekte erfolgreich verifiziert sind: Removal-Checkliste aus
Abschnitt 9 dieses Reports abarbeiten.

**STEP 10 — Disable Subproject Editing**
Analog: CRUD-UI in `ProjectPlanningTab.tsx` **sowie** die Subproject-Bezüge in
`ProjectHistoryTab.tsx` und `ProjectCommunicationTab.tsx` (Abschnitt 10 dieses Reports — nicht
nur eine Stelle) deaktivieren/entfernen. `export.py`-Gruppierung auf `parent_phase_id`
umstellen.

**STEP 11 — Regression Tests**
Alle sechs bestehenden Verifikationsskripte erneut laufen lassen plus manueller
Browser-Durchlauf des End-to-End-Testszenarios (Abschnitt 28 der Aufgabenstellung).

**STEP 12 — Observation Window / Rollback Decision**
Mindestens einen vollen Arbeitszyklus (empfohlen: 1–2 Wochen) beobachten, bevor Schema-Cleanup
angegangen wird. Rollback-Kriterien siehe Abschnitt 17.

**STEP 13 — Compat-Feld-/Schema-Cleanup (separat, später)**
`subprojects`-Tabelle/`subproject_id`-Spalten/`ResourceDemand.plan_phase_id IS NULL`-Pfad erst
nach der Beobachtungsphase und mit eigener, dedizierter Freigabe droppen — **nicht** Teil dieses
B-8-Durchgangs.

---

## 17. Rollback Plan

- **DB-Backup:** Aus STEP 1, vor STEP 5 erneut ein frisches Backup unmittelbar vor Apply.
- **Migration-Rollback:** Die Migration selbst ist additiv (neue Parent-/Leaf-Phasen, umgehängte
  FKs) — ein Rollback bedeutet: Restore aus dem STEP-5-Backup, **nicht** ein manuelles
  Rückgängigmachen einzelner Zeilen (zu fehleranfällig bei Produktionsdaten).
- **Feature-Flag/UI-Fallback:** Da B-6/B-7 bereits produktiv sind, gibt es kein separates
  "altes UI" mehr zum Zurückschalten — der Rollback-Pfad ist ausschließlich der DB-Restore.
  Deshalb ist STEP 4 (Write Freeze) und ein frisches Backup unmittelbar vor STEP 5 besonders
  wichtig.
- **Wiederherstellung der Legacy-Datenbeziehungen:** Durch den DB-Restore automatisch gegeben
  (Subprojects/`ResourceDemand.plan_phase_id = NULL` sind zu diesem Zeitpunkt unverändert).
- **Rollback-Trigger:** Auslösen, wenn nach STEP 6/7 eine Kapazitätsabweichung > 0 (FTE-Summe
  vorher ≠ nachher für irgendein Projekt) oder ein Datenverlust (fehlende
  Comments/Tasks/Blocker/Decisions/Milestones/Documents) festgestellt wird, oder wenn
  `check_migrations.py` nach der Migration nicht mehr grün ist.

**Kein produktiver Cutover ohne diesen Rückfallplan.**

---

## 18. GO / NO-GO Checklist

| # | Kriterium | Status |
|---|---|---|
| 1 | B-1–B-7 Codeaudit vollständig CONFIRMED | **PARTIAL** — Kern CONFIRMED, 7 dokumentierte Einzel-Gaps |
| 2 | Migration Dry-Run fehlerfrei | CONFIRMED (synthetische Fixture; echter Produktiv-Dry-Run aussstehend) |
| 3 | Orphan-Count = 0 | CONFIRMED (Testfixture) |
| 4 | Hierarchy-Violations = 0 | CONFIRMED |
| 5 | Projektkapazität vorher/nachher fachlich erklärt/validiert | CONFIRMED |
| 6 | Keine zentrale Capacity View summiert weiter `ResourceDemand` als Projektbedarf | CONFIRMED (5/5 zentrale Endpunkte), 2 sekundäre Tracks offen |
| 7 | Direct Assignment funktioniert | CONFIRMED |
| 8 | Available Capacity über Phase Range funktioniert | **PARTIAL** — Haupt-Flow ja, Legacy-Endpoint nein |
| 9 | Planstand Tree funktioniert | **PARTIAL** — "Phase hinzugefügt" fehlt |
| 10 | Gantt Tree funktioniert | CONFIRMED |
| 11 | ResourceDemandGrid Removal Dependencies vollständig bekannt | CONFIRMED |
| 12 | Subproject Removal Dependencies vollständig bekannt | CONFIRMED (erweitert um `ProjectHistoryTab`/`ProjectCommunicationTab`) |
| 13 | CONCEPT auf echtem IST-Stand | CONFIRMED (dieser Durchgang) |

---

## 19. Final Status

**B-8 CUTOVER BLOCKED**

Begründung: drei Kriterien (1, 8, 9) sind laut der in der Aufgabenstellung vorgegebenen Regel
rot. Das ist **kein Architektur-Blocker** — die P18-Zielarchitektur ist implementiert, verdrahtet
und im Kern live end-to-end verifiziert (Baum, Direktzuweisung, abgeleitete Kapazität, Gantt,
Milestones). Es sind konkrete, klein-skalierte Nacharbeiten (primär Defekte 1 und 2 aus
Abschnitt 13), gefolgt von einem echten Produktions-Dry-Run (Defekt 7), bevor der in Abschnitt 16
beschriebene Cutover angestoßen werden sollte.
