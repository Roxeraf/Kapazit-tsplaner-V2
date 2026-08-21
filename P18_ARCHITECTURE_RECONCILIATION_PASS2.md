# P18 ARCHITECTURE RECONCILIATION — PASS 2

**PlanPhase als einzige Planungseinheit / Hierarchische Phasen statt Grob-/Feinplanung und
Teilprojekte**

Status: **Design/Architekturprüfung. Keine Implementierung in diesem Durchgang.** Kein Code,
keine Migration, keine Frontend-Änderung. Dieses Dokument prüft den in
[`CONCEPT.md`](CONCEPT.md) Abschnitt 6a und [`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md`](P18_DESIGN_AND_IMPLEMENTATION_PLAN.md)
spezifizierten Grob-/Feinplanung-Ansatz ("P18 Pass 1") gegen eine grundsätzliche Alternative:
**PlanPhase als hierarchische, einzige Planungseinheit** ("P18 Pass 2"). Ergebnis dieses
Durchgangs: **Pass 2 löst Pass 1 fachlich ab.** CONCEPT.md Abschnitt 6a bleibt als historisches
Design im Dokument stehen (nicht gelöscht — es war ein realer, sauber durchgeführter
Analysedurchgang), wird aber als **superseded** markiert; der neue Abschnitt 6b beschreibt das
jetzt empfohlene Zielbild.

---

## 1. Executive Summary

Pass 1 (P18) hat Grobplanung (`ResourceDemand.plan_phase_id = NULL`, projektweit, monatlich)
und Feinplanung (`PlanPhase`, tagegenau) als zwei "Konkretisierungsgrade derselben Planung"
modelliert und eine Reconciliation-Formel (`Konsumption = max(Grob, Fein)`) samt neuem
Vokabular ("Noch grob", "Konkretisierungsgrad"), einem neuen Endpoint und drei offenen Business
Decisions (BD-7/8/9) dafür entworfen. Das war in sich konsistent und korrekt hergeleitet — aber
es beantwortet nicht die vorgelagerte Frage: **Brauchen wir überhaupt zwei parallel gepflegte
Kapazitätsachsen?**

Dieser Durchgang prüft die Alternative: **`PlanPhase` wird hierarchisch (`parent_phase_id`,
selbstreferenzierend, nullable). Nur Blattphasen (Leaf) tragen operative Kapazität
(`plan_fte`, Zeitraum). Elternphasen (Parent) aggregieren ausschließlich aus ihren Kindern.**
Eine anfangs grobe Phase ("Projektumsetzung, 01.10.–31.12., 1,5 FTE") ist zunächst ein Leaf und
damit sofort eine gültige, vollständige Planung. Wird sie später in Unterphasen aufgeteilt,
wird sie automatisch zum Parent — ihre eigene `plan_fte` bleibt in der DB stehen (nichts wird
gelöscht), zählt aber ab dem Moment, in dem Kinder existieren, nicht mehr operativ.

**Kernbefund:** Diese Architektur beantwortet dieselbe fachliche Anforderung (frühe,
grobe Kapazitätssicht für noch nicht strukturierte Projekte, schrittweise Verfeinerung, keine
Doppelzählung) **durch Aggregation (Summe über Blätter) statt durch Reconciliation (Max aus
zwei unabhängig gepflegten Zahlen)**. Das eliminiert die Notwendigkeit von BD-7/8/9 **durch
Konstruktion**, nicht durch eine weitere Formel-Entscheidung — es gibt in diesem Modell gar
keine zwei Zahlen mehr, die auseinanderlaufen könnten.

Zusätzlicher, im Audit bestätigter Befund: `Subproject` ist heute technisch nichts als
`{id, name, reihenfolge, project_id}` — keine Zeiträume, keine Kapazität, eine feste
Hierarchietiefe von genau 1. Eine Parent-`PlanPhase` kann das vollständig ersetzen, ohne
Funktionsverlust, mit zusätzlichem Nutzen (beliebige Tiefe bis zur vereinbarten Grenze,
abgeleitete Zeiträume/Kapazität statt reiner Namensgruppierung).

**Weiterer Befund, der die Empfehlung stützt:** `ResourceDemandGrid.tsx`
(Rolle-×-Monat-Grobplanungs-UI, ~170 Zeilen JSX + zugehörige Backend-Aggregationslogik in
`capacity_calc.py`/`controlling.py`/`health.py`) entfällt unter Option B **vollständig** — sie
wird durch denselben `PlanPhaseCreateModal`/`PlanPhaseCapacityTab`-Flow ersetzt, den feine
Phasen ohnehin schon nutzen (eine grobe Leaf-Phase *ist* die Grobplanung, kein Extra-Werkzeug).
Das ist eine Nettoreduktion an Code und Konzepten, kein lateraler Umbau.

**Empfehlung dieses Durchgangs:** **MOVE TO PLANPHASE-ONLY ARCHITECTURE** (Option B), mit einer
kleinen, klar benannten Menge echter Business Decisions (BD-10 bis BD-13, Abschnitt 28) — nicht
"alles ist eine BD". Die meisten in der Auftragsvorgabe aufgeworfenen Detailfragen (Leaf/Parent-
Unterscheidung, Rollen-Optionalität, Available Capacity, Baseline-Strategie, Migration) haben
eine technisch eindeutige, im Audit verifizierte Antwort und sind **keine** offenen
Entscheidungen.

---

## 2. Warum der aktuelle P18-Ansatz (Pass 1) erneut geprüft wird

Pass 1 war fachlich sauber hergeleitet, aber sein eigenes Ergebnis enthält das Warnsignal: um
zwei Achsen widerspruchsfrei zu halten, musste ein **neues Vokabular** eingeführt werden
("Grobplanstunden", "Feinplanstunden", "Noch grob", "Konkretisierungsgrad"), eine **neue
Formel** (`max(Grob, Fein)`), ein **neuer Endpoint**
(`GET /projects/{id}/capacity/reconciliation`), eine **neue UI-Karte** ("Planungsstand
Kapazität") und **drei Business Decisions**, von denen zwei (BD-7, BD-9) ausdrücklich damit
begründet wurden, dass sie *heute sichtbare Portfolio-Zahlen verändern* — ein Symptom dafür,
dass zwei Systeme miteinander abgeglichen werden, die eigentlich dieselbe Aussage treffen
sollen ("wie viel Kapazität braucht dieses Projekt in diesem Monat").

CONCEPT.md Abschnitt 6a.1 beschreibt selbst bereits den Lifecycle, der die eigentliche
Antwort nahelegt:

> "Ein Projekt wird nicht an einem Tag vollständig tagegenau planbar. Es durchläuft
> typischerweise: 1. Kapazitätsrelevant, aber noch nicht strukturiert […] 2. Zunehmend
> konkretisiert […] 3. Vollständig fein geplant."

Das ist exakt der Leaf-wird-zu-Parent-Lifecycle dieses Durchgangs (Abschnitt 10) — nur wurde er
in Pass 1 mit **zwei verschiedenen Tabellen/Konzepten** (`ResourceDemand` ohne Phase vs.
`PlanPhase`) nachgebaut, statt mit **einer** rekursiven Struktur. Die Frage dieses Durchgangs
ist deshalb nicht "wie reconciliaten wir Grob und Fein technisch besser", sondern: **"Ist die
Zwei-Achsen-Prämisse selbst schon die vermeidbare Komplexität?"**

---

## 3. Codebase Validation

Vollständige Prüfung gegen den aktuellen Code (Stand dieser Session, Branch
`claude/p18-architecture-reconciliation-fvwx4r`). Alle Aussagen unten wurden gegen die
tatsächlichen Dateien verifiziert (Backend: `backend/app/models.py`,
`backend/app/routers/{planning,capacity,baselines,controlling,health,gap_engine}.py`,
`backend/app/{capacity_calc,phase_metrics_calc}.py`, `backend/app/schemas.py`; Frontend: siehe
Abschnitt 3.3).

### 3.1 Modelle (`backend/app/models.py`)

| Modell | Relevante Felder | Befund |
|---|---|---|
| `Project` | `start_monat`, `anzahl_monate`, `subprojects: list[Subproject]` (cascade `delete-orphan`) | Kein `parent`-Konzept nötig auf dieser Ebene — Projekt bleibt Wurzel des Baums. |
| `Subproject` | `id, project_id, name, reihenfolge` — **sonst nichts** | Bestätigt die Arbeitshypothese: keine Zeiträume, keine Kapazität, keine eigene fachliche Substanz jenseits einer Namensgruppierung. Hierarchietiefe technisch fest auf 1 Ebene (kein `parent_subproject_id`). |
| `PlanPhase` | `subproject_id` (nullable FK), `phase_type`, `baseline_/forecast_/actual_start/end`, `status`, `progress` (deprecated), `plan_fte` (nullable) | **Kein** `parent_phase_id` — flache Struktur. Kein Feld, das heute schon in Richtung Hierarchie zeigt. |
| `Milestone` | `subproject_id` (nullable), `name`, `baseline_/forecast_/actual_date`, `status` | Identisches Gruppierungsmuster wie `PlanPhase`, keine PlanPhase-Beziehung. |
| `ResourceDemand` | `project_id`, `plan_phase_id` (**nullable**), `resource_role_id` (**NOT NULL**), `period` (NOT NULL, "Apr 26"), `fte` | Bestätigt: Grobplanung = exakt dieses Modell mit `plan_phase_id = NULL`. Bestätigt außerdem: **jede** `ResourceDemand`-Zeile braucht eine Rolle — auch heute schon, auch auf der Phasenachse (`PlanPhaseCapacityTab.tsx` erzwingt eine Rollenauswahl beim Anlegen, Abschnitt 3.3). Das ist **kein** Pass-1/Pass-2-Unterschied, sondern eine bereits heute bestehende UX-Reibung, die Abschnitt 11 unabhängig von der Grundsatzentscheidung behebt. |
| `ResourceAssignment` | `resource_demand_id`, `person_id`, `fte` | Hängt zwingend an `ResourceDemand` — keine direkte `plan_phase_id`-Beziehung im Code, bestätigt Auftragsvorgabe-Annahme. |
| `BaselineSnapshot`/`BaselineEntry` | `_SNAPSHOT_FIELDS["plan_phase"] = [phase_type, baseline_start, baseline_end, forecast_start, forecast_end, plan_fte, status]` (siehe `routers/baselines.py:23-34`) | **Vollständig generischer Mechanismus** (`entity_type`/`entity_id`/`field`/`value`, alle Strings, `entity_id` bewusst **keine** FK). Eine neue Zeile `"parent_phase_id"` in der Liste kostet **keine Schema-Änderung** — bestätigt für Abschnitt 16 (Planstand-Strategie). |
| `PlanHistory` | `subproject_id` (nullable), `bereich`, `feld`, … | Trägt heute eine eigene `subproject_id`-Dimension für Audit-Gruppierung — relevant für Migration (Abschnitt 20). |
| `Comment` | `subproject_id` **und** `plan_phase_id` (beide nullable) | Einzige Collaboration-Entität mit beiden Feldern gleichzeitig — historisch (aus der Vor-PlanPhase-Ära). `Task`/`Blocker`/`Decision` haben **nur** `plan_phase_id`, kein `subproject_id`. Das ist bereits heute eine bestehende Inkonsistenz zwischen den Collaboration-Modellen, kein Pass-2-Problem, aber Pass 2 löst sie nebenbei mit (Abschnitt 19). |

### 3.2 Router/Calc-Layer

| Datei/Funktion | Befund |
|---|---|
| `routers/planning.py` (`create_plan_phase`, `update_plan_phase`, `_check_subproject`) | CRUD ist bereits sauber vom generischen `entity_links`-Muster (Tags/Documents) getrennt — ein `parent_phase_id`-Check ließe sich nach demselben Muster wie `_check_subproject`/`_check_owner` ergänzen (Guard-Funktion, kein struktureller Umbau). |
| `routers/projects.py::delete_subproject` (Zeilen 323-369) | **Wichtiger Befund:** Löschen eines `Subproject` löscht heute bereits **kaskadierend** alle zugehörigen `PlanPhase`/`Milestone`/`Comment` (inkl. TagLink/DocumentLink/EntityRelation-Aufräumung) — **kein** Nullsetzen von `subproject_id`. Das ist ein bestehender Präzedenzfall für die Frage "was passiert beim Löschen einer Parent-Phase mit Kindern" (Abschnitt 28, BD-11) — die heutige Antwort ist bereits "kaskadierend löschen, mit expliziter Aufräumlogik", nicht "verwaisen lassen". |
| `capacity_calc.compute_person_capacity` | Nimmt ausschließlich `period: "Apr 26"` (Monats-Bucket), keinen Datumsbereich — **identische Einschränkung wie in Pass 1 dokumentiert** (CONCEPT.md 6.2), unabhängig von Grob/Fein vs. Hierarchie. Bleibt in Pass 2 unverändert bestehen, siehe Abschnitt 12. |
| `controlling.py`/`health.py`/`gap_engine.py` — `ResourceDemand`-Summen | **Bestätigt CONFLICT aus Pass 1 (CONCEPT.md 6.3):** `compute_capacity_gap` (`capacity_calc.py:117`), `get_allocation_gaps`/`get_role_analysis` (`controlling.py:54,213-214`), `_cockpit_capacity` (`health.py:113-114`) summieren `ResourceDemand.period == period` **ohne** `plan_phase_id`-Filter — Grob- und Feindemand werden heute bereits ungefiltert addiert. **In Pass 2 verschwindet dieses Problem strukturell**, weil es unter Option B keine `plan_phase_id = NULL`-Zeilen mehr als Zielzustand gibt (Abschnitt 18) — kein Filter-Bugfix nötig, weil die Quelle der Doppelzählung selbst entfällt. |
| `phase_metrics_calc.plan_hours`/`reconcile` | Bleiben **unverändert wiederverwendbar** — Pass 2 ändert nichts an der Plan-FTE→Planstunden-Formel einer einzelnen Phase, nur daran, wie viele Phasen es gibt und wie sie sich zueinander verhalten. |
| Nur **4 Alembic-Revisionen** insgesamt (`0001_consolidated_baseline` … `0004_planning_consolidation`) | Die Migrationshistorie ist bewusst konsolidiert (frühere Revisionen wurden zu `0001` zusammengefasst, siehe Commit-Historie). Additive Spalten (wie `plan_fte` in `0004`) sind der etablierte, risikoarme Migrationsstil dieses Repos — ein zusätzliches `parent_phase_id`-Feld folgt exakt diesem Muster (Abschnitt 20). |

### 3.3 Frontend (vollständiger Audit, siehe Ergebnis des parallelen Recherche-Agents dieser
Session — Dateien einzeln gelesen: `ProjectPlanningTab.tsx`, `PlanPhaseList.tsx`,
`PlanPhaseWorkspace.tsx`, `PlanPhaseCapacityTab.tsx`, `PlanPhaseGantt.tsx`,
`PlanPhaseCreateModal.tsx`, `ResourceDemandGrid.tsx`, `MilestoneList.tsx`, `BaselineList.tsx`,
`types.ts`, `client.ts`, `ProjectCommunicationTab.tsx`, `PortfolioHealth.tsx`)

| Befund | Konsequenz für Pass 2 |
|---|---|
| **Keine einzige rekursive/Tree-UI-Komponente existiert im gesamten Frontend.** Grep nach `parent_id\|parentId\|children\|depth\|breadcrumb\|recursive\|treeNode` liefert außerhalb von React-`ReactNode`-Props keine Treffer. | Eine PlanPhase-Baum-UI ist **echte neue Frontend-Infrastruktur**, kein Wiederverwendungsfall — ehrlich als Aufwand einzuplanen (Abschnitt 25/30). |
| `PlanPhaseList.tsx` und `PlanPhaseGantt.tsx` implementieren **unabhängig voneinander** dasselbe Ein-Ebenen-Gruppierungsmuster (`Map` keyed by `subproject_id`, eigener `collapsedGroups`-State je Komponente, "Projektweit" immer zuerst) — **dupliziert, nicht geteilt.** | Eine gemeinsame, rekursive Gruppierungs-Komponente/-Hook (`groupBy parent_phase_id`, Einzug pro Tiefe) würde diese Duplizierung gleichzeitig auflösen — Pass 2 ist eine Gelegenheit, nicht nur zusätzlicher Aufwand. |
| `ResourceDemandGrid.tsx` liest **alle** `ResourceDemand`-Zeilen eines Projekts ungefiltert (`listResourceDemands(projectId)`) und gruppiert nur nach Rolle × Periode — **kein** `plan_phase_id`-Filter irgendwo im Code. Jede über diese Komponente angelegte Zeile hat `plan_phase_id: null` (kein Feld im Payload). | Bestätigt Pass-1-Fund (CONCEPT.md 6.3, Frontend-Kollisionsrisiko) unabhängig — und bestätigt, dass diese ganze Komponente unter Option B ersatzlos entfällt (Abschnitt 18). |
| `PlanPhaseCapacityTab.tsx`/`DemandAssignments`: Personenzuordnung läuft **ausschließlich** über `ResourceDemand` (Rolle) → `ResourceAssignment` — **keine** direkte Person-zu-Phase-Zuordnung ohne Rollen-Zwischenschritt existiert **schon heute für Feinplanung**, nicht nur für Grobplanung. | Bestätigt, dass die in Abschnitt 2 der Auftragsvorgabe verlangte "Rolle optional"-UX eine **bestehende** Lücke behebt, unabhängig von Grob/Fein vs. Hierarchie (Abschnitt 11). |
| `PortfolioAllocationGapEntry` (types.ts) hat **kein** `plan_phase_id`/`subproject_id`-Feld — Portfolio-Sichten sind heute schon blind gegenüber Phase/Teilprojekt, nur Projekt+Rolle+Periode. | Portfolio-Aggregation bleibt unter Pass 2 auf Projekt-/Monatsebene, keine neue Teilprojekt-Dimension nötig (deckt sich mit Pass 1s Abschnitt 6a.11-Einschätzung). |
| `client.ts` definiert `createSubproject`/`updateSubproject`/`listAllSubprojects` — **`updateSubproject` und `listAllSubprojects` werden nirgends im Frontend aufgerufen** (kein Rename-UI, kein globales Teilprojekt-Verzeichnis verwendet). | Blast Radius von Subproject-UI ist kleiner als das Datenmodell vermuten lässt — im Wesentlichen nur `ProjectPlanningTab.tsx` (Create/Delete) und die Gruppierungs-Konsumenten (`PlanPhaseList`, `PlanPhaseGantt`, `MilestoneList`, `PlanPhaseWorkspace`, `PlanPhaseCreateModal`, `ProjectCommunicationTab`). |
| Backend läuft auf **SQLite** (`database.py`: `DATABASE_URL` Default `sqlite:///./kapazitaetsplaner.db`). | Bei max. 3 Hierarchie-Ebenen und typischerweise wenigen Dutzend Phasen je Projekt ist **keine rekursive SQL-Query (`WITH RECURSIVE`) nötig** — der komplette `PlanPhase`-Baum eines Projekts lässt sich mit einer flachen Query laden (`WHERE project_id = ?`, wie heute schon in `list_plan_phases`) und in Python zum Baum zusammensetzen. Das entschärft einen der in der Auftragsvorgabe befürchteten Komplexitätspunkte (Rekursion/Performance, Abschnitt 9) technisch vollständig. |

---

## 4. Option A — Bestehendes Grob-/Fein-Modell (Pass 1) beibehalten

**Was es leistet:** Fachlich korrekt hergeleitet, mathematisch sauber (`max()`-Formel algebraisch
bewiesen äquivalent zu Alternativformel B), rebuild-safe dokumentiert, minimal-invasiv im
Sinne von "keine neue Tabelle".

**Was es kostet:**
- Zwei parallel gepflegte Konzepte (`ResourceDemand` ohne Phase vs. `PlanPhase`), die **dasselbe
  fachliche Ding** ("wie viel Kapazität für dieses Projekt in diesem Monat") aus zwei
  Richtungen beschreiben.
- Ein neues Vokabular, das Nutzer:innen lernen müssen (Grobplanstunden, Feinplanstunden, "Noch
  grob", Konkretisierungsgrad) — für ein Konzept, das sich mit Hierarchie ohne dieses Vokabular
  erklären lässt: "diese Phase ist noch nicht weiter aufgeteilt."
- Drei Business Decisions, von denen zwei explizit *"ändert heute sichtbare Portfolio-Zahlen"*
  als Begründung tragen — ein Symptom, kein Zufall.
- `ResourceDemandGrid.tsx` bleibt als eigenständige, von `PlanPhase`-Planung losgelöste
  UI-Fläche bestehen — Nutzer:innen müssen wissen, *welches* der beiden Werkzeuge für welche
  Planungstiefe zuständig ist.
- Die in CONCEPT.md 6.3 dokumentierte Aggregationslücke bleibt bestehen, bis P18.3 (BD-7/9-
  abhängig) umgesetzt wird — ein weiterer Gate vor "keine Doppelzählung mehr".

**Bewertung:** Technisch vollständig; fachlich eine Notlösung für eine Anforderung
(Grob→Fein-Konkretisierung), die es bereits als natives Konzept geben könnte (Hierarchie). Kein
KO-Kriterium, aber auch kein Grund, ihn Option B vorzuziehen, sobald B als tragfähig
verifiziert ist (Abschnitt 5).

---

## 5. Option B — PlanPhase-only / Hierarchische Phasen

**Kernidee:** Ein Feld, `PlanPhase.parent_phase_id` (nullable, self-referencing FK). Nur
Blattphasen (keine Kinder) tragen operative `plan_fte`/Zeitraum. Elternphasen aggregieren.
`Subproject` wird durch eine Parent-`PlanPhase` ersetzt (Abschnitt 15). Grobplanung wird durch
eine noch nicht aufgeteilte Leaf-Phase ersetzt (Abschnitt 10).

**Was es leistet (siehe Abschnitt 3 für die Belege):**
- **Ein** Strukturmodell statt zwei (Grob/Fein) plus drei (Projekt/Subproject/PlanPhase) — de
  facto eine Zusammenlegung von zwei separaten Pass-1-Diskussionen (Grob/Fein-Reconciliation
  UND Subproject-vs-PlanPhase) in eine gemeinsame Lösung.
- Keine Doppelzählung *by construction* — eine Elternphase mit Kindern liefert nie eine eigene
  operative Zahl, es gibt nichts zu maximieren.
- `ResourceDemandGrid.tsx` und die zugehörige Backend-Sonderbehandlung entfallen — Netto-
  Codereduktion.
- Gantt-Hierarchie entspricht direkt der Planungsstruktur (Abschnitt 17) statt einer separaten
  Teilprojekt-Gruppierung.
- Migrationsaufwand ist konkret bezifferbar und additiv (Abschnitt 20/21) — keine Big-Bang-
  Migration nötig, entspricht dem etablierten "kein Drop-and-Pray"-Prinzip dieses Repos (siehe
  Legacy Cutover Phase 26.9 als Präzedenzfall für saubere, additive Datenkonvertierung).

**Was es kostet (kritisch, nicht nur Vorteile):**
- **Echte neue Frontend-Infrastruktur** (Baum-Rendering, rekursive Gruppierung) — der Audit
  bestätigt, dass es dafür **keine** Vorlage im Code gibt (Abschnitt 3.3). Das ist der größte
  reale Mehraufwand gegenüber Option A.
- Tree-Operationen (Zyklenprävention, Tiefenbegrenzung, Löschverhalten) sind neue fachliche
  Regeln, auch wenn sie technisch einfach sind (Abschnitt 9).
- Migration von **zwei** bestehenden, potenziell mit Echtdaten befüllten Konzepten
  (`Subproject`, `ResourceDemand.plan_phase_id IS NULL`) ist ein einmaliger, aber realer
  Aufwand (Abschnitt 20/21) — nicht "kein Migrationsaufwand", nur ein **anderer**
  Migrationsaufwand als der von Pass 1 (der keine strukturelle Datenmigration brauchte, weil er
  am bestehenden Modell festhielt).
- `Konkretisierungsgrad`/"Planungsreife" als Kennzahl (Pass 1, 6a.7) hat unter Option B keine
  direkte 1:1-Entsprechung mehr (es gibt keine zwei Zahlen mehr, deren Verhältnis das ausdrückt)
  — wird als bewusst nicht übernommenes Nice-to-have behandelt (Abschnitt 26), kein Blocker.

**Bewertung:** Fachlich die konsistentere Zielarchitektur — löst die Ausgangsfrage
("brauchen wir zwei Kapazitätsebenen?") mit Nein, durch ein einziges, in sich vollständiges
Konzept. Der Mehraufwand ist real, aber bekannt, begrenzt und additiv migrierbar.

---

## 6. Option C — Migration Hybrid (PlanPhase-only für neue Projekte, Legacy kompatibel)

Geprüft und **nicht empfohlen** als Dauerzustand, aber relevant als **Rollout-Strategie**
(nicht als Zielarchitektur) — siehe Abschnitt 21 (Migrationspakete). Ein dauerhaftes
Nebeneinander zweier Planungsmodelle (alte Projekte: Subproject + evtl. Grobplanung; neue
Projekte: PlanPhase-Baum) wäre exakt die Art Doppelkomplexität, die dieser gesamte Durchgang
vermeiden soll — zwei Codepfade in Gantt, Liste, Portfolio, Baseline, dauerhaft. Als
**Übergangszustand während der Migration** (Abschnitt 21, wenige Wochen, nicht dauerhaft) ist er
unvermeidbar und wird dort explizit eingeplant.

---

## 7. Empfehlung

**MOVE TO PLANPHASE-ONLY ARCHITECTURE (Option B).** Siehe Abschnitt 34 für die formale
Endentscheidung und die verbleibenden, echten Business Decisions (BD-10–13, Abschnitt 28), die
vor P18-Pass-2-Implementierungspaketen zu klären sind.

---

## 8. Ziel-Domain-Modell

```
Project (unverändert: Stammdaten, start_monat/anzahl_monate bleiben Portfolio-Rahmen, Abschnitt 24)
  │
  └── PlanPhase (selbstreferenzierend über parent_phase_id, max. 3 Ebenen, Abschnitt 9.3)
        │
        ├── parent_phase_id: int | None   ── NEU, einziges neues Feld
        ├── phase_type, forecast_start/end, status   ── unverändert
        ├── plan_fte: float | None        ── unverändert im Typ, NEU in der Semantik:
        │                                     nur operativ wirksam, wenn KEINE Kinder existieren
        │                                     (has_children = false)
        ├── owner_person_id/team_id, tags, documents   ── unverändert
        │
        ├── (Leaf, has_children = false)
        │     ├── ResourceDemand (plan_phase_id gesetzt, optional, Rollen-Aufschlüsselung)
        │     │     └── ResourceAssignment (Personenbesetzung)
        │     ├── Comment / Task / Blocker / Decision (plan_phase_id)
        │     └── Milestone (plan_phase_id, NEU statt subproject_id)
        │
        └── (Parent, has_children = true)
              ├── Zeitraum = abgeleitet: MIN(child.forecast_start) … MAX(child.forecast_end)
              ├── Kapazität = abgeleitet: SUM(monthly_distribution(child) für alle Leaf-Nachfahren)
              ├── plan_fte = inert (bleibt in DB, zählt nicht operativ, kein Auto-Clear)
              ├── Comment / Task / Blocker / Decision weiterhin erlaubt (Abschnitt 19)
              └── Milestone weiterhin erlaubt (projektweite ODER phasen-/sammelphasenbezogene Meilensteine)

BaselineSnapshot / BaselineEntry ── unverändert generisch, zusätzliches Feld "parent_phase_id"
  in _SNAPSHOT_FIELDS["plan_phase"] (Abschnitt 16)

ResourceDemand / ResourceAssignment ── unverändert, ABER: plan_phase_id wird faktisch für neue
  Zeilen immer gesetzt sein (Zielzustand hat keine projektweite Grobplanung mehr, Abschnitt 18)

Subproject ── entfällt als aktives Konzept (Tabelle bleibt vorerst bestehen, compat-only,
  Abschnitt 15/20), durch Parent-PlanPhase ersetzt
```

Kein neues Modell, keine neue Engine — **ein** additives Feld (`parent_phase_id`) auf einer
bereits bestehenden Tabelle, plus ein query-seitiges Prädikat (`has_children`), das aus
`EXISTS(...)` berechnet wird, nie gespeichert (Abschnitt 9).

---

## 9. Leaf-/Parent-Semantik

### 9.1 Kein neues Statusfeld

Die Auftragsvorgabe fragt explizit, ob `phase_kind = leaf|parent` nötig ist, oder ob
`has_children` reicht. **Antwort: `has_children` reicht, kein neues Feld.**

```sql
-- has_children einer PlanPhase p (query-seitig, kein gespeichertes Feld):
EXISTS (SELECT 1 FROM plan_phases c WHERE c.parent_phase_id = p.id)
```

Begründung (gegen die in der Auftragsvorgabe genannten Edge Cases geprüft):

| Edge Case | Verhalten mit `has_children` (berechnet) | Bewertung |
|---|---|---|
| Parent hat noch einen alten `plan_fte`-Wert, während er Kinder bekommt | `plan_fte` bleibt unverändert in der DB stehen (**kein Auto-Clear beim Anlegen des ersten Kindes**) — wird aber ab `has_children = true` von keiner Berechnung mehr gelesen. | Kein Datenverlust (Auftragsvorgabe Abschnitt 7/22: "Die historische ursprüngliche Planung darf nicht verloren gehen"), kein Sonderfall im Code nötig — reine Lesart-Änderung, kein Schreibpfad-Sonderfall. |
| Alle Kinder werden gelöscht | `has_children` wird automatisch wieder `false` — Phase ist augenblicklich wieder Leaf, ihr alter `plan_fte`-Wert (falls seit der Umwandlung nie überschrieben) wird augenblicklich wieder operativ sichtbar. | Genau das in Abschnitt 8 der Auftragsvorgabe gewünschte Verhalten ("Parent wird wieder Leaf"), ohne jede Zusatzlogik. |
| Migration bestehender Daten | Alle heutigen `PlanPhase`-Zeilen haben `parent_phase_id = NULL` → `has_children` ist für alle `false` (sofern nicht selbst Ziel eines `parent_phase_id` einer neuen Zeile) → alle bestehenden Phasen sind nach der Migration automatisch Leaf-Phasen. Kein Migrationsschritt nötig, um einen Status zu setzen. | Migration wird dadurch einfacher, nicht schwerer. |
| Planstand-Historie | `BaselineEntry` friert `parent_phase_id` als Wert ein (Abschnitt 16) — der eingefrorene Stand *"war zu diesem Zeitpunkt Leaf/Parent"* ergibt sich beim Anzeigen des Snapshots aus dem eingefrorenen `parent_phase_id`-Wert, nicht aus einem separat gespeicherten Status. | Konsistent mit dem bestehenden Prinzip, dass `BaselineEntry` Rohwerte einfriert, keine abgeleiteten Werte. |

**Ergebnis:** Keine neue Statusdimension — exakt die im Kapitel 8 der Auftragsvorgabe favorisierte,
einfachere Variante ist die richtige.

### 9.2 Operative Konsequenz von `has_children`

| Bereich | Leaf (`has_children = false`) | Parent (`has_children = true`) |
|---|---|---|
| `forecast_start`/`forecast_end` | Direkt editierbar (wie heute) | Read-only, abgeleitet: `MIN(children.forecast_start)` / `MAX(children.forecast_end)`, rekursiv über Enkel |
| `plan_fte` | Direkt editierbar, operative Quelle für Planstunden/Monatsverteilung | Nicht editierbar im normalen Fluss (Feld existiert, wird ignoriert); UI zeigt stattdessen "Aggregiert aus N Unterphasen" |
| `ResourceDemand`/`ResourceAssignment` | Wie heute (optional, Abschnitt 11) | **Nicht sinnvoll auf Parent-Ebene** — Kapazität wird nicht doppelt (auf Parent UND Leaf) geplant. UI blendet den Kapazitäts-Editier-Pfad für Parents aus (nur Aggregations-Ansicht, Abschnitt 22 der Auftragsvorgabe/Abschnitt 14 dieses Dokuments). |
| Monatsverteilung/Portfolio-Aggregation | Fließt ein (`monthly_distribution`) | Fließt **nicht** ein — nur Leaf-Nachfahren zählen (Abschnitt 18) |
| Comment/Task/Blocker/Decision | Erlaubt (wie heute) | Erlaubt (Abschnitt 19, neu explizit dokumentiert) |
| Milestone | Erlaubt | Erlaubt (z. B. "Fachkonzept freigegeben" am Ende von "Wareneingang") |
| Gantt | Balken = eigener Zeitraum | Balken = aggregierte Hüllkurve, ein-/ausklappbar (Abschnitt 17) |

### 9.3 Maximale Hierarchietiefe

Arbeitshypothese der Auftragsvorgabe: max. 3 Ebenen (Projekt → Bereich → Detailphase, z. B.
Wareneingang → Schnittstellen → WE-API Test). **Empfehlung: 3 Ebenen**, technisch erzwungen
**nicht** über eine DB-`CHECK`-Constraint (SQLite `CHECK` über eine rekursive Selbstreferenz ist
umständlich), sondern **anwendungsseitig** beim Anlegen/Verschieben einer Phase: beim Setzen von
`parent_phase_id` wird die Elternkette höchstens 2 Hops nach oben verfolgt (trivial bei max. 3
Ebenen, kein rekursives SQL nötig, siehe Abschnitt 3.3) — wird dabei eine 3. Ebene überschritten,
ein Zyklus gefunden oder das Projekt verlassen, wird der Request mit `422` abgelehnt (exakt
analog zum bestehenden Muster `_check_subproject`/`_check_plan_phase` in `planning.py`/
`capacity.py`). Begründung für 3 statt 2: deckt das in der Auftragsvorgabe (Abschnitt 5/10)
durchgängig verwendete Beispiel "Wareneingang → Pflichtenheft/Konfiguration/Test" **und**
"Wareneingang → Schnittstellen → WE-API Test" gleichzeitig ab, ohne dass Projektleiter:innen
sich zwischen zwei nicht kompatiblen Gruppierungsstilen entscheiden müssen. Wird als Empfehlung
in eine BD überführt (BD-10, Abschnitt 28), da es eine Produktentscheidung mit UX-Konsequenz
ist (mehr Tiefe = mehr Jira-artige Komplexität), keine rein technische.

---

## 10. PlanPhase Lifecycle — Zeitraum → Kapazität → Personen → Konkretisierung

Dies ist die in der Auftragsvorgabe (Abschnitt 1) verlangte Kernkette, jetzt mit der
Hierarchie-Erweiterung:

**Stufe 1 — Zeitraum.** `+ Phase hinzufügen` → Name, Start, Ende. Optional: `parent_phase_id`
(leer = Top-Level-Phase des Projekts). Das ist bereits ein gültiger, vollständiger
Planungszustand — identisch zu heute (`PlanPhaseCreateModal.tsx`, unverändert außer dem neuen
optionalen Parent-Feld statt `subproject_id`).

**Stufe 2 — Kapazität.** `plan_fte` setzen (Drawer, Tab "Übersicht", wie heute). Planstunden
werden wie heute über `phase_metrics_calc.plan_hours` berechnet — **keine Änderung** an dieser
Formel.

**Stufe 3 — Personen.** `[+ Mitarbeiter zuweisen]` direkt auf der Phase — **ohne** erzwungene
Rollenauswahl (Abschnitt 11). Optional: `[Rollen aufschlüsseln]`, falls gewünscht.

**Konkretisierung (statt einer zweiten Planungsebene):** Aus derselben Phase heraus:
`[+ Unterphase hinzufügen]`. Sobald die erste Unterphase existiert, wird die Elternphase
automatisch zur Sammelphase (`has_children = true`, Abschnitt 9) — ihre bisherige `plan_fte`
bleibt als historischer Wert in der DB stehen, wird aber ab sofort durch die Summe der
Unterphasen ersetzt. Kein Datenverlust, kein manueller "Modus-Wechsel"-Klick nötig. Dieselbe
Sequenz (Zeitraum → Kapazität → Personen) beginnt für jede neue Unterphase von vorn — bis zur
vereinbarten Tiefenbegrenzung (Abschnitt 9.3).

---

## 11. ResourceDemand / Assignment UX

**Befund (Abschnitt 3):** `ResourceDemand.resource_role_id` ist NOT NULL — und zwar **schon
heute**, unabhängig von Grob-/Fein-/Hierarchie-Frage. Auch die heutige Phasenachse
(`PlanPhaseCapacityTab.tsx`) erzwingt eine Rollenauswahl, bevor eine Person zugeordnet werden
kann.

**Bewertung der Optionen A–D aus der Auftragsvorgabe:**

| Option | Bewertung |
|---|---|
| A — transparente Default-/Generic-`ResourceDemand` je Phase | **Empfohlen.** Kein neues Modell, keine neue Tabelle. Ein System-`ResourceRole` (Name z. B. "Ohne Rolle" oder "Allgemein", per Migration geseedet, analog zu bestehenden Seed-Mustern) wird von der UI transparent verwendet, wenn der User "Person zuordnen" klickt, ohne vorher eine Rolle gewählt zu haben: Backend legt (falls noch nicht vorhanden) eine `ResourceDemand(plan_phase_id=phase.id, resource_role_id=<Generic>, period=<Monat von forecast_start>, fte=0)` an und hängt das `ResourceAssignment` daran — exakt dieselbe Mechanik, die Pass 1 (CONCEPT.md 6a.5) bereits für Level-1-Grobplanung vorschlug, hier nur auf **jede** Phase (nicht nur Grobplanung) angewendet. |
| B — `ResourceDemand` technisch weiter erzeugen, aber UX-seitig unsichtbar | Deckungsgleich mit A in der Umsetzung — A **ist** die konkrete Ausprägung von B. Keine getrennte Bewertung nötig. |
| C — bestehendes Modell erweitern | Geprüft, **nicht nötig** — A erreicht dasselbe Ziel ohne Schemaänderung. |
| D — direktes Assignment an `PlanPhase` (neues Modell) | **Abgelehnt.** Würde die etablierte Trennung Demand≠Assignment (CONCEPT.md Abschnitt 3, ein Kernprinzip) aufweichen und eine zweite Zuordnungs-Tabelle neben `ResourceAssignment` schaffen — genau die Art Doppelstruktur, die dieser gesamte Durchgang vermeiden will. Nicht nötig, weil Option A das fachliche Ziel ("User muss keine Rolle wählen") vollständig erreicht, ohne die Modelltrennung aufzugeben. |

**UI-Konsequenz:** "Rollen aufschlüsseln" wird ein expliziter, optionaler Button (wie in
Auftragsvorgabe Abschnitt 2 skizziert) — klickt der User ihn, wird die generische Demand-Zeile
durch echte rollenspezifische Zeilen ersetzt/ergänzt (bestehende Assignments auf der
generischen Zeile bleiben unangetastet, bis der User sie manuell umhängt — kein automatisches
Splitten, da FTE-Aufteilung pro Rolle eine fachliche, keine technische Entscheidung ist).

---

## 12. Available Capacity

**Unverändert gegenüber Pass 1 (CONCEPT.md 6.2/6a.8) — keine neue Capacity-Engine, exakt
dieselbe Erweiterung bleibt nötig, unabhängig von Grob/Fein vs. Hierarchie:**
`compute_person_capacity` bleibt monatsbasiert; für Leaf-Phasen, deren Zeitraum eine
Monatsgrenze überschreitet, wird weiterhin eine bereichsbasierte Variante gebraucht
(`compute_person_capacity_for_range`, Formel bereits in
`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md` Abschnitt 11 vollständig hergeleitet und unverändert
gültig — **1:1 aus Pass 1 übernehmbar**, da sie ausschließlich mit Leaf-Zeiträumen arbeitet,
nicht mit Grob-/Fein-Unterscheidung). Kein Unterschied zwischen Option A und B in diesem
Punkt — dieses Paket ist bereits in Pass 1 als unabhängig vom Rest markiert (P18.6) und bleibt
das unter Pass 2 identisch (Abschnitt 30, Paket B-6).

---

## 13. Monthly / Portfolio Aggregation

```
Projektkapazität(Monat) = SUM( phase_metrics_calc.monthly_distribution(leaf.plan_fte,
                                leaf.forecast_start, leaf.forecast_end)[Monat]
                                für alle Leaf-Nachfahren des Projekts )
```

Identischer Verteilungsschlüssel wie Pass 1 (CONCEPT.md 6a.6, werktage-anteilig, kein 50/50,
kein Feiertagsabzug — unverändert BD-4-konform). Der einzige Unterschied zu Pass 1: es gibt nur
**eine** Quelle (Leaf-`PlanPhase.plan_fte`) statt zwei (Grob-`ResourceDemand` UND Fein-
`PlanPhase.plan_fte`) — deshalb keine `max()`-Formel, kein "Noch grob", keine
Konkretisierungsgrad-Kennzahl mehr nötig (Abschnitt 26 zur bewussten Nicht-Übernahme dieser
Kennzahl).

**SQL-Prädikat für "ist Leaf" bei der Aggregation** (kein rekursives SQL nötig, siehe
Abschnitt 3.3, direkt aus dem bereits geladenen, flachen `project_id`-Query ableitbar):

```sql
SELECT * FROM plan_phases p
WHERE p.project_id = :project_id
  AND NOT EXISTS (SELECT 1 FROM plan_phases c WHERE c.parent_phase_id = p.id)
```

**Mathematischer Vergleich zu Pass 1:** Wo Pass 1 `max(Grobplanstunden, Feinplanstunden)`
berechnete, berechnet Pass 2 direkt `SUM(Leaf-Planstunden)` — es gibt keine zweite Zahl, die
verglichen werden müsste. Für ein Projekt, das (wie im Pass-1-Beispiel) im Oktober grob mit
1,5 FTE geplant war und dann zu 0,64 FTE-äquivalent (112h) fein geplant wurde, wäre die
Pass-2-Antwort identisch **konzeptionell einfacher**: solange die grobe Phase noch ein Leaf ist
(Stufe 1/2 in Abschnitt 10), zählen ihre 1,5 FTE (264h) voll. Sobald sie in Unterphasen
aufgeteilt wird (Stufe "Konkretisierung"), zählt automatisch nur noch die Summe der
Unterphasen — kein Nebeneinander, kein "noch 152h grob" als eigene Kennzahl. Der grobe
Ausgangswert ist historisch in der DB sichtbar (Abschnitt 9.1), aber nicht mehr operativ
addiert.

---

## 14. Subproject Strategy

**Fachliche Bewertung (Antwort auf die Kernfrage aus Abschnitt 9 der Auftragsvorgabe): Nein,
`Subproject` ist fachlich nicht mehr als eine PlanPhase-Gruppierung — bestätigt durch den
Modell-Audit (Abschnitt 3.1: `{id, name, reihenfolge, project_id}`, sonst nichts).**

| Heutige Subproject-Funktion | Ersetzung durch Parent-PlanPhase |
|---|---|
| Gruppierung von `PlanPhase` (`subproject_id`) | `parent_phase_id` |
| Gruppierung von `Milestone` (`subproject_id`) | `plan_phase_id` (Abschnitt 19) |
| Gruppierung von `Comment` (`subproject_id`, historisch) | `plan_phase_id` (bereits vorhanden, vereinheitlicht die bisherige Doppelverknüpfung von `Comment`, Abschnitt 3.1) |
| `reihenfolge` (Sortierung in Liste/Gantt) | Übernimmt eine neue `reihenfolge`-Spalte auf `PlanPhase` (Abschnitt 22) ODER Sortierung nach `forecast_start` der Kinder (empfohlen: explizite `reihenfolge`, da Sammelphasen ohne Kinder-Zeitraum sonst keine stabile Sortierposition hätten) |
| "Projektweit" als Default-Gruppe (`subproject_id = NULL`) | Top-Level-Phasen ohne `parent_phase_id` **sind** bereits die "projektweite" Ebene — kein Sonderfall mehr nötig, jede Phase ohne Parent ist einfach Ebene 1 |
| `GET /projects/subprojects/{id}/history` (separate Audit-Historie je Teilprojekt) | `PlanHistory` bekommt (falls gewünscht) dieselbe Filterlogik über `plan_phase_id`-Ketten statt `subproject_id` — kleines, additives Router-Package (Abschnitt 22) |
| `list_all_subprojects` (globale Teilprojekt-Liste) | Laut Frontend-Audit (Abschnitt 3.3) **nirgends im Frontend verwendet** — entfällt ersatzlos, kein Migrationsbedarf |

**Vorteile (bestätigt gegen die Auftragsvorgabe-Liste in Abschnitt 9):**
- Ein Strukturmodell statt zwei — bestätigt.
- Gantt-Hierarchie direkt aus der Planung — bestätigt, siehe Abschnitt 17.
- Beliebige Gruppierung (innerhalb der Tiefenbegrenzung) statt fixer 1-Ebenen-Teilprojekte —
  bestätigt, deckt das Auftragsvorgabe-Beispiel "Wareneingang → Schnittstellen → WE-API Test"
  ab, das mit dem heutigen `Subproject`-Modell (nur 1 Ebene) gar nicht abbildbar wäre.
- Grob→Fein innerhalb desselben Modells — bestätigt, Abschnitt 10.
- Knowledge-Kontext entlang der Phase-Hierarchie — bestätigt möglich, da Tags/EntityRelations
  bereits generisch über `entity_type`/`entity_id` funktionieren, unabhängig von der Baumtiefe.
- Weniger spezielle Subproject-UX — bestätigt: die Subproject-CRUD-UI in
  `ProjectPlanningTab.tsx` (Zeilen 93-111 laut Audit) entfällt, ersetzt durch denselben
  `PlanPhaseCreateModal`-Flow mit `parent_phase_id`-Auswahl.

**Risiken (kritisch geprüft gegen die Auftragsvorgabe-Liste):**
- Milestones brauchen Parent-Phase-Kontext statt Subproject → gelöst, Abschnitt 19.
- Bestehende Datenmigration → real, aber additiv lösbar, Abschnitt 20.
- Semantik Sammelphase vs. echte Arbeitsphase → gelöst durch `has_children`, Abschnitt 9.
- Komplexere Tree-Operationen/Rekursion/Performance → durch SQLite + kleine Projektgrößen +
  Tiefenbegrenzung entschärft (Abschnitt 3.3/9.3), **kein** ungelöstes technisches Risiko.
- Zyklische Beziehungen verhindern → anwendungsseitige Prüfung beim Schreiben, trivial bei
  Tiefe ≤ 3 (Abschnitt 9.3).
- Rechte/Ownership → kein Auth-System im Repo (CONCEPT.md Abschnitt 7), keine neue
  Fragestellung gegenüber heute.
- Reporting → CSV-Export (`routers/export.py`) müsste die neue Struktur berücksichtigen
  (Abschnitt 22), überschaubarer Zusatzaufwand.

**Migrationspfad:** `subprojects`-Tabelle bleibt **vorerst bestehen** (compat-only, wie beim
Legacy Cutover Phase 26.9 üblich — "mit Datenkonvertierung, nicht Drop-and-Pray"), wird aber
nach der Migration (Abschnitt 20) von keiner aktiven Logik mehr gelesen. Tatsächlicher
Schema-Drop ist ein späterer, eigenständiger Cleanup-Schritt (analog zu `PlanPhase.progress`,
das seit P6/P11 ebenfalls "compat-only, nicht gedroppt" ist — etabliertes Muster dieses Repos,
CONCEPT.md Abschnitt 15).

---

## 15. Milestone Strategy

**Empfehlung:** `Milestone.subproject_id` (nullable) → `Milestone.plan_phase_id` (nullable).
`NULL` bleibt "projektweiter Meilenstein" (identische Semantik wie heute, nur bezogen auf die
Baumwurzel statt auf "kein Teilprojekt"). Ein gesetzter Wert kann auf **jede** Ebene zeigen —
Leaf **oder** Parent (im Unterschied zur Kapazitätsplanung, die Leaf-only ist, Abschnitt 9.2) —
weil ein Meilenstein ("Fachkonzept freigegeben") oft eine Sammelphase abschließt, nicht eine
einzelne Detailphase. Das deckt exakt das Auftragsvorgabe-Beispiel ab ("Wareneingang →
Pflichtenheft, ◆ Fachkonzept freigegeben" — Milestone am Parent "Wareneingang", nicht an einem
seiner Kinder).

Kein neues Modell, keine neue Tabelle, keine Änderung an `MilestoneOut`/`MilestoneCreate`
außer dem Feldnamen-Wechsel (`subproject_id` → `plan_phase_id`, gleicher Typ `int | None`).
Baseline/Gantt/Tags/Documents/Activity bleiben unverändert (alle bereits generisch über
`entity_type = "milestone"`).

---

## 16. Planstand / Baseline Strategy

**Erweiterung von `_SNAPSHOT_FIELDS["plan_phase"]`** (`routers/baselines.py:24-32`) um
`"parent_phase_id"`:

```python
_SNAPSHOT_FIELDS: dict[str, list[str]] = {
    "plan_phase": [
        "phase_type", "baseline_start", "baseline_end", "forecast_start", "forecast_end",
        "plan_fte", "status",
        "parent_phase_id",  # NEU — friert die Baumstruktur mit ein
    ],
    "milestone": ["name", "baseline_date", "forecast_date", "status", "plan_phase_id"],  # NEU: plan_phase_id statt subproject_id
}
```

**Keine Schema-Änderung** — `BaselineEntry.value` ist bereits `str | None`, `entity_id` bereits
keine FK (also robust gegenüber späterem Löschen/Reparenting der referenzierten Phase — exakt
dasselbe Verhalten wie heute für `forecast_start` einer inzwischen gelöschten Phase).

**Was ein Planstand damit rekonstruieren kann:** nicht nur "welche Termine/FTE hatte Phase X am
Tag Y", sondern auch "war Phase X am Tag Y ein Leaf oder Teil von Sammelphase Z" — direkt
relevant für die in Abschnitt 7 der Auftragsvorgabe verlangte Nachvollziehbarkeit
("Vorher: Projektumsetzung 1,5 FTE / Nachher: Projektumsetzung → Pflichtenheft, Konfiguration,
Testing").

**Deviation-Anzeige (`baseline_calc.compute_deviations`):** kleine, additive Erweiterung, um
eine Änderung von `parent_phase_id` als strukturelle Abweichung darzustellen (z. B. "Phase war
Top-Level → jetzt Unterphase von 'Wareneingang'"), statt sie wie eine gewöhnliche Feldänderung
zu behandeln. Eingeplant als eigenes kleines Paket (Abschnitt 30, Paket B-7), kein Blocker für
den Kern.

Das entspricht exakt dem in Pass 1 (BD-8) bereits vorgeschlagenen Weg ("technisch bereits ohne
Schemaänderung möglich") — Pass 2 löst BD-8 damit vollständig auf (keine offene Frage mehr,
Granularität ist durch die Struktur selbst vorgegeben, kein "granular vs. aggregiert"-Dilemma
wie bei Grob-`ResourceDemand`, weil es nur noch eine Kapazitätsquelle je Phase gibt).

---

## 17. Gantt Strategy

**Heute** (bestätigt durch Audit, Abschnitt 3.3): `PlanPhaseGantt.tsx` gruppiert bereits nach
`subproject_id` in einer Ein-Ebenen-`Map`, mit eigenem, undupliziertem `collapsedGroups`-State
— **dieselbe Logik wie `PlanPhaseList.tsx`, aber unabhängig implementiert.**

**Zielbild:** Rekursive Gruppierung nach `parent_phase_id` statt `subproject_id` (max. 3 Ebenen,
also technisch mit **höchstens 2 verschachtelten Gruppierungs-Durchläufen** umsetzbar — kein
generischer, beliebig tiefer Rekursions-Algorithmus zwingend nötig, auch wenn eine kleine
rekursive React-Komponente wartbarer ist als eine hart auf 3 Ebenen ausgeschriebene Struktur).

```
▼ Wareneingang                              (Parent, Summary-Balken 01.10.–13.11.)
   Pflichtenheft      █████                 (Leaf)
   Konfiguration          ███████           (Leaf)
   Testing                       ███        (Leaf)

▼ Warenausgang                              (Parent)
   Pflichtenheft        █████               (Leaf)
   Konfiguration             ██████         (Leaf)
```

- Parent-Zeile: ein-/ausklappbar (wie heute die Subproject-Gruppen), **optional** ein
  aggregierter Summary-Balken (Hüllkurve `MIN(start)…MAX(end)`, visuell abgesetzt, z. B.
  heller/gestrichelt) — als schnell entscheidbare Produktfrage behandelt, nicht als echte BD
  (Empfehlung: ja, zeigen — konsistent mit dem bereits etablierten Wunsch nach einem
  Gesamtüberblick, geringes Risiko).
- Leaf-Zeile: echter Planungsbalken, unverändert zu heute (`forecast_start`/`forecast_end`,
  Klick öffnet `PlanPhaseWorkspace`).
- Gantt bleibt **read-only** (unverändert, CONCEPT.md 5.6) — kein Drag&Drop-Zwang, keine neue
  Anforderung durch die Hierarchie.
- Die von `PlanPhaseList.tsx` und `PlanPhaseGantt.tsx` **unabhängig implementierte**
  Ein-Ebenen-Gruppierung wird im selben Zug auf eine **gemeinsame** rekursive
  Gruppierungs-Utility konsolidiert (kleiner Zusatznutzen, kein Muss, aber naheliegend, da beide
  Dateien ohnehin angefasst werden müssen).

---

## 18. Portfolio / Monthly Aggregation — Auswirkungen

Siehe Formel Abschnitt 13. Auswirkungen auf bestehende Endpunkte:

| Endpoint | Heutiges Verhalten (CONFLICT, Abschnitt 3.1) | Verhalten unter Pass 2 |
|---|---|---|
| `capacity_calc.compute_capacity_gap` | `ResourceDemand.period == period`, kein `plan_phase_id`-Filter → addiert Grob+Fein ungefiltert | Summiert weiterhin `ResourceDemand.period == period` — aber da es unter Pass 2 **keine** `plan_phase_id IS NULL`-Zeilen mehr als Zielzustand gibt (jede Kapazität hängt an einer Leaf-Phase), verschwindet die Doppelzählungsquelle **strukturell**, kein Code-Fix im Sinne eines neuen Filters nötig — nur die Migration (Abschnitt 20) muss vollständig sein. |
| `controlling.get_allocation_gaps`/`get_role_analysis` | dito | dito |
| `health._cockpit_capacity` | dito | dito |
| `gap_engine.get_capacity_gap` | dito (nutzt dieselbe Funktion) | dito |

**Wichtiger Unterschied zu Pass 1:** Pass 1 musste diese vier Stellen aktiv per Code-Änderung
reparieren (P18.3, BD-7/9-abhängig, mit explizit dokumentiertem Risiko "sichtbarer
Zahlensprung am Umstellungstag"). Unter Pass 2 **ist ein Zahlensprung am Umstellungstag
unvermeidbar** (die Migration selbst verändert, wie Kapazität berechnet wird — es gibt ja gar
keine Grobplanung mehr, an die man sich weiter anlehnen könnte), muss also ebenfalls
kommuniziert werden — das ist kein Vorteil von Pass 2 gegenüber Pass 1 in diesem einen Punkt,
sondern ein **unvermeidbarer, einmaliger Umstellungs-Effekt** in beiden Optionen. Der
Unterschied ist: bei Pass 2 passiert er **einmal, zum Migrationszeitpunkt**, exakt beschreibbar
(Abschnitt 21); bei Pass 1 wäre er **dauerhaft latent** (jedes Mal, wenn ein Projekt von
"vorwiegend grob" zu "vorwiegend fein" wechselt, ändert sich `max(Grob,Fein)`s Ergebnisquelle
unbemerkt).

---

## 19. Collaboration / Knowledge

**Frage aus der Auftragsvorgabe (Abschnitt 24):** Dürfen Leaf und Parent beide
Kontextobjekte (Comment/Task/Blocker/Decision) haben?

**Antwort: Ja — und zwar ohne jede Zusatzarbeit.** `Comment`/`Task`/`Blocker`/`Decision` sind
bereits heute ausschließlich über `plan_phase_id` (nullable, `ON DELETE SET NULL`) an eine
`PlanPhase` gebunden — der Code unterscheidet nirgends, ob die referenzierte Phase Kinder hat
oder nicht (`_get_plan_phase_or_404` prüft nur Existenz). Ein Blocker "WE-Konzept Kunde nicht
freigegeben" an der Parent-Phase "Wareneingang" funktioniert mit dem heutigen Modell
unverändert, sobald `parent_phase_id` existiert — **kein Code-Zusatz nötig**, nur
Dokumentation, dass Collaboration-Objekte bewusst sowohl auf Leaf- als auch auf
Parent-Phasen erlaubt sind (analog zur "nicht als BD aufgenommen"-Kategorie in Pass 1, CONCEPT.md
Abschnitt 14 unten).

**Trennung, die dokumentiert werden muss (Auftragsvorgabe Abschnitt 24, "sauber
dokumentieren"):** Kapazitätsplanung ist **Leaf-only** (Abschnitt 9.2), Collaboration ist
**Leaf- und Parent-fähig**. Diese Trennung existiert im Code implizit bereits (Kapazitäts-Tab
vs. Aktivitäts-Tab sind unabhängige Bereiche des `PlanPhaseWorkspace`-Drawers) und muss nur in
CONCEPT.md explizit als Regel benannt werden (Abschnitt 29 dieses Dokuments).

**Tags/Knowledge:** Keine neue Knowledge Engine nötig (bereits generisch über
`entity_type`/`entity_id`). Breadcrumbs/`child_of`-Relation entlang der Phase-Hierarchie sind
ein optionales, kleines Zusatzfeature (Knowledge-Kontext könnte `EntityRelation(relation_type=
"child_of")` beim Anlegen einer Unterphase automatisch setzen) — **nicht Kernbestandteil**
dieses Durchgangs, da `parent_phase_id` selbst bereits die Baumstruktur trägt und
`EntityRelation` dafür nicht zwingend gebraucht wird (keine doppelte Modellierung derselben
Kante). Tag-Vererbung bleibt bewusst nicht automatisch (unverändert zu Pass 1/CONCEPT.md
Abschnitt 8).

---

## 20. Migration Existing Grob-Demands

**Ausgangslage:** `ResourceDemand`-Zeilen mit `plan_phase_id = NULL` sind heute produktiv
nutzbar (Grobplanung ist seit Phase 26 aktiv, `ResourceDemandGrid.tsx` existiert und wird laut
CONCEPT.md 6.1 bereits verwendet) — es kann echte Daten geben, die nicht verloren gehen dürfen.

**Migrationsstrategie (deterministisch, additiv, kein Drop-and-Pray):**

Für jedes Projekt mit mindestens einer `ResourceDemand(plan_phase_id IS NULL)`-Zeile:

1. Ermittle den Zeitraum aller Grob-Demand-Perioden des Projekts:
   `range_start = 1. Tag des frühesten Monats`, `range_end = letzter Tag des spätesten Monats`.
2. Lege **eine** neue Top-Level-`PlanPhase` an: `phase_type = "Grobplanung (migriert)"`,
   `forecast_start = range_start`, `forecast_end = range_end`, `parent_phase_id = NULL`,
   `plan_fte = NULL` (bewusst **nicht** automatisch befüllt — siehe Punkt 4).
3. Alle bestehenden `ResourceDemand`-Zeilen mit `plan_phase_id IS NULL` dieses Projekts erhalten
   `plan_phase_id = <neue Phase>` — **ihre `period`-Werte bleiben unverändert** (nichts spricht
   dagegen, dass eine Leaf-Phase mehrere `ResourceDemand`-Zeilen mit unterschiedlichen
   `period`-Werten trägt; das Schema erzwingt heute schon keine 1:1-Beziehung zwischen Phase und
   Periode, siehe Abschnitt 3.1). Damit bleibt die **komplette, monatsscharfe** Rollen-/
   FTE-Historie 1:1 erhalten, nur "umgehängt" — keine Rundung, keine Aggregation, kein
   Informationsverlust.
4. `plan_fte` der neuen Phase bleibt bewusst `NULL` statt automatisch aus der
   Rollen-Aufschlüsselung befüllt zu werden — konsistent mit dem bestehenden Grundsatz "keine
   automatische Synchronisierung von `plan_fte` aus `SUM(ResourceDemand.fte)`" (CONCEPT.md
   Abschnitt 3). Die neue Phase zeigt entsprechend ehrlich "Kein Plan-FTE gesetzt, N
   Rollen-Zeilen vorhanden" — der Projektleiter bestätigt/setzt den Wert einmalig nach der
   Migration, statt dass das System einen möglicherweise falschen Wert erfindet.
5. Bestehende `ResourceAssignment`-Zeilen auf diesen Demands sind über den unveränderten
   `resource_demand_id`-FK automatisch mitmigriert — **keine Handlung nötig** (Antwort auf
   Auftragsvorgabe Abschnitt 26: nichts wird gelöscht, weil nichts an der
   `ResourceDemand`/`ResourceAssignment`-Beziehung selbst geändert wird, nur `plan_phase_id`
   auf der Demand-Zeile).

**Warum keine feinere Aufteilung (z. B. eine Phase pro Monat) gewählt wird:** würde 1:1 die alte
Monatsraster-Struktur nachbauen, die dieser Durchgang gerade auflösen will. Eine Sammelphase pro
Projekt ist der ehrlichste Reflex des Ist-Zustands: "hier war einmal grob geplant, jetzt ist es
Aufgabe des Projektleiters, das in echte Phasen zu übersetzen" — exakt der in Abschnitt 10
beschriebene Lifecycle, nur rückwirkend angewendet.

---

## 21. Migration Existing Assignments

Vollständig durch Abschnitt 20, Punkt 5 beantwortet: `ResourceAssignment` referenziert
ausschließlich `resource_demand_id` (nicht `plan_phase_id` direkt) — die Migration ändert
`ResourceDemand.plan_phase_id`, lässt `ResourceAssignment`-Zeilen selbst vollständig unberührt.
**Kein Assignment wird gelöscht, keines muss neu angelegt werden.**

---

## 22. Migration Subprojects

Für jedes Projekt mit mindestens einem `Subproject`:

1. Für jedes `Subproject sp`: lege eine neue Top-Level-`PlanPhase` an:
   `phase_type = sp.name`, `parent_phase_id = NULL`,
   `forecast_start/end = NULL` (wird unmittelbar danach aus den migrierten Kindern abgeleitet,
   Abschnitt 9.2 — kein manueller Zwischenschritt nötig, sobald Kinder reparented sind, greift
   die abgeleitete Berechnung automatisch), neue Spalte `reihenfolge = sp.reihenfolge`
   (Abschnitt 14 — Sortierung bleibt erhalten).
2. Alle `PlanPhase`-Zeilen mit `subproject_id = sp.id` erhalten `parent_phase_id = <neue
   Phase>` (ihr `subproject_id`-Feld bleibt zunächst unverändert stehen, compat-only, siehe
   unten).
3. Alle `Milestone`-Zeilen mit `subproject_id = sp.id` erhalten `plan_phase_id = <neue Phase>`
   (Abschnitt 15).
4. Alle `Comment`-Zeilen mit `subproject_id = sp.id` und (noch) `plan_phase_id IS NULL` erhalten
   `plan_phase_id = <neue Phase>` — vereinheitlicht die historische Doppelverknüpfung von
   `Comment` (Abschnitt 3.1) im selben Zug.
5. `PlanHistory`-Zeilen mit `subproject_id = sp.id` bleiben unverändert (reines Audit-Log,
   rückwirkend nicht umzuschreiben — Audit-Trails werden grundsätzlich nicht nachträglich
   verändert, auch nicht bei Migrationen, CONCEPT.md-Prinzip).
6. `subprojects`-Tabelle und `subproject_id`-Spalten bleiben **bestehen** (compat-only,
   Abschnitt 14) — kein `DROP COLUMN` in diesem Migrationsschritt.

**IDs:** Neue `PlanPhase`-Zeilen erhalten neue, fortlaufende IDs — keine ID-Wiederverwendung
von `Subproject`-IDs (unterschiedliche Tabellen, unterschiedlicher Namensraum, kein Konflikt
möglich).

**Plan History/Baseline/Milestone/Documents/Tags/Relations:** Alle bereits generisch über
`entity_type`/`entity_id` — funktionieren mit den neuen `PlanPhase`-IDs ohne weitere Anpassung,
**außer** an den Stellen, die heute explizit `entity_type = "subproject"` nirgends verwenden
(bestätigt: kein `TagLink`/`DocumentLink`/`EntityRelation`-Datensatz mit `entity_type =
"subproject"` existiert im Code — `Subproject` ist nirgends taggbar/dokumentverknüpfbar, siehe
Abschnitt 3.1 — **kein Migrationsbedarf für diese drei Tabellen**).

**API/Frontend:** Siehe Abschnitt 25/30 (Implementierungspakete) für die konkreten Dateien.

---

## 23. Data Model Changes

**Ein additives Feld, eine additive Spalte, kein Drop:**

```python
class PlanPhase(Base):
    ...
    parent_phase_id: Mapped[int | None] = mapped_column(
        ForeignKey("plan_phases.id"), nullable=True, index=True
    )
    reihenfolge: Mapped[int] = mapped_column(default=0)  # übernimmt Subproject.reihenfolge-Rolle


class Milestone(Base):
    ...
    plan_phase_id: Mapped[int | None] = mapped_column(
        ForeignKey("plan_phases.id", ondelete="SET NULL"), nullable=True, index=True
    )  # ersetzt subproject_id operativ; subproject_id bleibt compat-only im Schema stehen
```

Alembic-Migration (additiv, folgt exakt dem Muster von `0004_planning_consolidation.py`):
- `ALTER TABLE plan_phases ADD COLUMN parent_phase_id INTEGER REFERENCES plan_phases(id)`
- `ALTER TABLE plan_phases ADD COLUMN reihenfolge INTEGER DEFAULT 0`
- `ALTER TABLE milestones ADD COLUMN plan_phase_id INTEGER REFERENCES plan_phases(id)`
- Kein `DROP COLUMN` (weder `subproject_id` noch `subprojects`-Tabelle) in diesem Schritt.
- `_SNAPSHOT_FIELDS`-Erweiterung (Abschnitt 16) ist reine Python-Konstante, keine
  Migration nötig.

**Kein neues Feld für Leaf/Parent-Status** (Abschnitt 9.1). **Kein neues `commitment_level`
o. ä.** — unverändert.

---

## 24. Calculation Changes

Neue/geänderte Funktionen (additiv, `phase_metrics_calc.py`/`capacity_calc.py`/`planning.py`):

- `models`-seitig: keine neue Berechnung, nur ein neues Prädikat `has_children` (SQL `EXISTS`,
  Abschnitt 9.1) — direkt in den betroffenen Routern verwendet, kein eigenes Calc-Modul nötig
  für so einen einzeiligen Ausdruck.
- `planning_calc.derive_parent_bounds(db, plan_phase) -> tuple[str|None, str|None]` (NEU) —
  `MIN(child.forecast_start)`/`MAX(child.forecast_end)` rekursiv über alle Nachfahren
  (bei Tiefe ≤ 3 mit höchstens 2 Join-Ebenen, kein rekursives SQL nötig, Abschnitt 3.3).
- `planning_calc.derive_parent_capacity(db, plan_phase) -> dict` (NEU) — Summe der
  `monthly_distribution`-Werte aller Leaf-Nachfahren, gruppiert nach Periode (dieselbe
  Datenstruktur wie die Rückgabe von `phase_metrics_calc.monthly_distribution`, nur über
  mehrere Phasen aggregiert statt über eine).
- `phase_metrics_calc.monthly_distribution(plan_fte, forecast_start, forecast_end) ->
  dict[str, float]` — **unverändert aus Pass 1 übernommen** (P18.1), unabhängig von der
  Grundsatzentscheidung, da sie ausschließlich mit einer einzelnen Phase arbeitet.
- `capacity_calc.compute_project_monthly_capacity(db, project_id, periods: list[str]) ->
  dict[str, float]` (NEU, ersetzt `compute_grob_hours`/`compute_fein_hours`/
  `compute_reconciliation` aus Pass 1 — **einfacher**, da nur eine Quelle statt zwei plus
  Vergleichsformel): Summe `monthly_distribution` über alle Leaf-`PlanPhase`s des Projekts.
- `capacity_calc.compute_person_capacity_for_range(...)` — **unverändert aus Pass 1
  übernommen** (Abschnitt 12).
- **Geänderte Funktionen (nur Lesart, kein neues Verhalten):** `compute_capacity_gap`,
  `controlling.get_allocation_gaps`, `controlling.get_role_analysis`, `health._cockpit_capacity`
  benötigen **keinen neuen Filter** (im Unterschied zu Pass 1, Abschnitt 18) — sie summieren
  weiterhin unverändert über `ResourceDemand.period`, korrekt, sobald die Migration
  abgeschlossen ist (keine `plan_phase_id IS NULL`-Zeilen mehr im Zielzustand).

---

## 25. API Changes

**Neu, additiv:**
- `GET /projects/{id}/plan-phases` liefert weiterhin die flache Liste (unverändert im
  Response-Envelope) — **plus** `parent_phase_id` im `PlanPhaseOut`-Schema (additives Feld).
  Baumaufbau bleibt bewusst **client-seitig** (wie heute schon die Subproject-Gruppierung
  client-seitig aus der flachen Liste erfolgt, Abschnitt 3.3) — kein neuer
  `GET /plan-phases/tree`-Endpoint nötig, konsistent mit dem bestehenden Muster.
- `PlanPhaseDetail` bekommt ein neues Feld `children: list[PlanPhaseOut]` (nur befüllt, wenn
  `has_children`) und `derived_capacity: dict[str, float] | None` (nur befüllt für Parents) —
  additive Schema-Erweiterung, kein Breaking Change.
- `POST/PUT /projects/{id}/plan-phases`: `parent_phase_id` statt/zusätzlich zu `subproject_id`
  im Payload (Übergangszeit: beide Felder im Schema erlaubt, `subproject_id` wird nach der
  Migration ignoriert, siehe Abschnitt 27 Rollout).
- `POST/PUT /milestones`: `plan_phase_id` statt `subproject_id`.

**Entfällt (nach Migration, Abschnitt 20):**
- Keine neuen Grobplanungs-Endpunkte mehr nötig — `POST /projects/{id}/resource-demands` mit
  `plan_phase_id = NULL` wird zum **Legacy-Pfad** (Payload-Validierung könnte ihn nach der
  Migration ablehnen, muss aber nicht zwingend — reines Aufräumen, kein Blocker).
- `GET /projects/subprojects/{id}/history` → durch Filterung von `GET
  /projects/{id}/history` nach Phasen-Unterbaum ersetzbar (kleines additives Paket, Abschnitt
  30 Paket B-7).

**Kein Reconciliation-Endpoint** (`GET /projects/{id}/capacity/reconciliation` aus Pass 1
entfällt ersatzlos — es gibt nichts mehr zu reconciliaten, Abschnitt 13).

---

## 26. Frontend Changes

- `PlanPhaseCreateModal.tsx`: `subprojectId`-Select → `parentPhaseId`-Select (befüllt aus der
  flachen Phasenliste des Projekts, gefiltert auf Phasen mit Tiefe < 3, Abschnitt 9.3).
- `PlanPhaseList.tsx`: Ein-Ebenen-`Map`-Gruppierung → rekursive Gruppierung nach
  `parent_phase_id`, Einzug pro Tiefe, Klick auf Parent-Zeile öffnet denselben
  `PlanPhaseWorkspace`-Drawer mit einer Parent-Variante der Ansicht (Abschnitt 9.2/`children`-
  Feld) statt einer neuen Komponente (bestätigt wiederverwendbar, Abschnitt 3.3-Analyse: der
  Drawer ist bereits datengetrieben aus `PlanPhaseDetail`).
- `PlanPhaseGantt.tsx`: dieselbe Umstellung, plus optionaler Summary-Balken für Parents
  (Abschnitt 17). Gelegenheit, die bisher duplizierte Gruppierungslogik mit `PlanPhaseList.tsx`
  zu teilen (neuer Hook `usePhaseTree(phases)`).
- `PlanPhaseWorkspace.tsx`: "Teilprojekt"-Select → "Übergeordnete Phase"-Select. Tab
  "Kapazität" verzweigt: `has_children` → read-only Aggregationsansicht (`derived_capacity`);
  sonst unverändert `PlanPhaseCapacityTab`. Tab "Übersicht" zeigt bei Parents zusätzlich eine
  `children`-Liste mit Sprung-Links.
- `PlanPhaseCapacityTab.tsx`: "Person zuordnen" ohne erzwungene Rollenauswahl (Abschnitt 11),
  "Rollen aufschlüsseln" als expliziter Button.
- `ResourceDemandGrid.tsx`: **entfällt vollständig** (Abschnitt 5/18) — größte einzelne
  Codereduktion dieses Durchgangs.
- `MilestoneList.tsx`: `subproject_id`/`NO_SUBPROJECT`-Sentinel → `plan_phase_id`, sonst
  strukturell unverändert (bereits eine reine `select`-Zuordnung).
- `ProjectPlanningTab.tsx`: Subproject-CRUD-Block (Zeilen 93-111 laut Audit) entfällt — Anlegen
  einer "Sammelphase" läuft über denselben `PlanPhaseCreateModal` wie jede andere Phase (kein
  separates UI-Element mehr).
- `ProjectCommunicationTab.tsx`: `subproject_id`-Filterung von Kommentaren → `plan_phase_id`-
  Filterung (Abschnitt 3.1, vereinheitlicht die historische Doppelverknüpfung von `Comment`).
- `BaselineList.tsx`: `FIELD_LABELS` um `parent_phase_id` ergänzt (Abschnitt 16).
- `types.ts`/`client.ts`: `PlanPhase.parent_phase_id`, `Milestone.plan_phase_id`,
  `PlanPhaseDetail.children`/`derived_capacity` neu; `createSubproject`/`updateSubproject`/
  `deleteSubproject`/`listAllSubprojects` als deprecated markiert (nicht sofort entfernt,
  Abschnitt 27).

---

## 27. Rollout-Strategie (ersetzt Pass 1s BD-9)

Anders als Pass 1 (additiver Endpoint neben unverändertem Bestand, BD-9) verlangt Pass 2 eine
**einmalige strukturelle Migration** — ein reiner "additiv daneben"-Rollout ist hier nicht
sinnvoll, weil das Ziel *ein* Modell statt zwei ist, nicht ein weiteres drittes daneben.
Empfohlene Reihenfolge (Details siehe Implementierungspakete, Abschnitt 30):

1. Schema-Migration (additive Spalten, Abschnitt 23) — risikofrei, keine Verhaltensänderung.
2. Backend-Berechnungen (`has_children`, `derive_parent_bounds/capacity`,
   `compute_project_monthly_capacity`) — additiv, noch nicht von bestehenden Endpunkten genutzt,
   vollständig testbar isoliert.
3. Datenmigration (Abschnitt 20/22) — einmaliges Skript, mit Vorher-/Nachher-Zahlenreport je
   Projekt (analog zu Pass 1s "Snapshot-Vergleich vor/nach", P18.3-Akzeptanzkriterium) zur
   Verifikation, dass keine FTE-Summe verloren geht.
4. Frontend-Umstellung (Abschnitt 26) — nach Punkt 3, da die UI sonst auf eine noch nicht
   migrierte Datenlage träfe.
5. Aufräumen (`ResourceDemandGrid.tsx` entfernen, `subproject_id`/`subprojects` als
   deprecated markieren) — letzter Schritt, keine funktionale Änderung mehr.

Kein dauerhafter Hybrid-Zustand (Option C, Abschnitt 6) — nur ein kurzer, geplanter
Übergangszeitraum zwischen Schritt 3 und 4.

---

## 28. Business Decisions

**Prinzip (wie in der Auftragsvorgabe gefordert): nur echte offene Entscheidungen, keine
technischen Detailfragen als BD verkleidet.** Im Unterschied zu Pass 1 (drei BDs, alle mit der
Begründung "ändert heute sichtbare Zahlen") sind die meisten hier geprüften Detailfragen
(Leaf/Parent-Unterscheidung, Rollen-Optionalität, Available Capacity, Baseline-Mechanik,
Zyklenprävention, Milestone-Bindung) technisch eindeutig beantwortet (siehe jeweiliger
Abschnitt) und **keine** BD.

| ID | Frage | Empfehlung | Warum trotzdem offen |
|---|---|---|---|
| BD-10 | Maximale Hierarchietiefe: 2 oder 3 Ebenen? (Abschnitt 9.3) | 3 (deckt beide in der Auftragsvorgabe genutzten Beispielmuster ab) | Reine UX-/Produktentscheidung (mehr Tiefe = mehr potenzielle Komplexität für Nutzer:innen), keine technische Notwendigkeit für eine bestimmte Zahl. |
| BD-11 | Löschverhalten einer Parent-Phase mit Kindern: kaskadierend löschen (wie heute bei `Subproject`, Abschnitt 3.1) vs. blockieren vs. Kinder eine Ebene hochstufen ("reparenting")? | Kaskadierend löschen mit explizitem Bestätigungsdialog (Anzahl betroffener Nachfahren + Kapazitäts-Summe anzeigen) — konsistent mit dem bestehenden `delete_subproject`-Verhalten | Destruktive Operation an Nutzerdaten — verdient explizite Produkt-/UX-Freigabe, auch wenn die technische Umsetzung (Cascade, analog zu `delete_subproject`) bereits vollständig spezifizierbar ist. |
| BD-12 | Migrationsstrategie für bestehende `Subproject`- und Grob-`ResourceDemand`-Daten: automatisiertes Einmal-Skript (Abschnitt 20/22, empfohlen) vs. manuelle Nachplanung durch Projektleiter:innen vs. Übergangs-UI mit beiden Modellen parallel? | Automatisiertes, deterministisches Skript mit Vorher-/Nachher-Report (Abschnitt 20/22/27) | Berührt echte, historisch gewachsene Planungsdaten — eine Entscheidung mit Wertungscharakter ("ist eine automatische 1:1-Übersetzung ausreichend treu, oder wollen Projektleiter:innen die Migration lieber selbst kuratieren"), keine rein technische Frage. |
| BD-13 | Soll `Konkretisierungsgrad`/"Planungsreife" als Kennzahl in irgendeiner Form weiterleben (z. B. neu definiert als "Anteil des Projektzeitraums, der durch terminierte Leaf-Phasen abgedeckt ist"), oder wird sie ersatzlos gestrichen (Abschnitt 13/26)? | Ersatzlos streichen — die Kennzahl war eine Krücke der Zwei-Achsen-Architektur, keine eigenständig wertvolle Fachkennzahl | Produktentscheidung: manche Nutzer:innen mochten die "X % konkretisiert"-Anzeige aus Pass 1 (6a.14) möglicherweise unabhängig von ihrem ursprünglichen Zweck — sollte vor dem endgültigen Streichen kurz abgefragt werden. |

**Nicht als BD aufgenommen, weil bereits eindeutig beantwortet:**
- Leaf/Parent-Statusfeld → kein neues Feld nötig (`has_children` berechnet, Abschnitt 9.1).
- Rollen-Optionalität → Option A, kein neues Modell (Abschnitt 11).
- Available Capacity über Zeitraum → identisch zu Pass 1 P18.6, unverändert nötig (Abschnitt
  12), unabhängig von A/B.
- Collaboration an Parent-Phasen → bereits heute technisch uneingeschränkt möglich, nur
  Dokumentationsnachtrag (Abschnitt 19).
- Milestone-Bindung (Leaf und Parent erlaubt) → technisch eindeutig, Abschnitt 15.
- Baseline-Granularität → durch die Struktur selbst vorgegeben, kein "granular vs.
  aggregiert"-Dilemma mehr (Abschnitt 16) — löst Pass 1s BD-8 auf.

**Aus Pass 1 übernommen, unverändert weiterhin offen (unabhängig von A/B/dieser Empfehlung):**
BD-1 (Tempo-Mapping), BD-3 (Ampel-Schwellen), BD-4 (Feiertags-Handling), BD-5
(Assignment-Sub-Ranges), BD-6 (Allocation-Gap-Vorzeichen).

**Obsolet durch diesen Durchgang (Pass 1s BD-7/8/9):**
- BD-7 (Konsumptionsformel) — entfällt, es gibt keine zwei Achsen mehr zu reconciliaten.
- BD-8 (Baseline-Granularität der Grobplanung) — entfällt, siehe oben.
- BD-9 (Rollout additiv vs. direkt) — ersetzt durch die in Abschnitt 27 beschriebene
  Migrationsreihenfolge (kein reiner Formel-Rollout mehr, sondern eine Strukturmigration).

---

## 29. CONCEPT.md Rebuild-Safe Changes

Siehe tatsächlich vorgenommene Änderungen an [`CONCEPT.md`](CONCEPT.md) (dieser Durchgang):

- **Kopfzeile:** Versions-/Statushinweis auf Pass 2 ergänzt, Pass 1 (Abschnitt 6a) als
  historisch/superseded markiert, ohne ihn zu löschen (er bleibt als dokumentierter,
  vollständig durchgeprüfter Alternativentwurf im Dokument stehen — Transparenz über den
  Entscheidungsweg, kein stilles Überschreiben).
- **Neuer Abschnitt 6b** (nach 6a): Zielarchitektur-Kurzfassung (Leaf/Parent-Semantik,
  Lifecycle, Aggregation, Subproject-/Milestone-Ablösung) — Verweis auf dieses Dokument für die
  vollständige Herleitung, exakt nach dem Muster, das Pass 1 für Abschnitt 6a vs.
  `P18_DESIGN_AND_IMPLEMENTATION_PLAN.md` bereits etabliert hat.
- **Abschnitt 14 (Open Business Decisions):** BD-7/8/9 als obsolet markiert (mit Verweis
  hierher), BD-10 bis BD-13 ergänzt.
- **Abschnitt 15 (Deferred Features):** P18-Pass-1-Eintrag aktualisiert (verweist jetzt auf
  Pass 2 als aktuellen Stand).
- **Abschnitt 16 (Umsetzungsstand):** neuer Abschnitt 16.5 (P18 Pass 2, Design-Zusammenfassung,
  analog zu 16.4 für Pass 1).

Alle inhaltlich vollständigen Regeln (Formeln, Migrationslogik, Business-Decision-Begründungen)
leben in **diesem** Dokument (analog zur bestehenden Konvention: CONCEPT.md Abschnitt 6a
verweist für Prozess-/Paketierungsdetails ebenfalls auf
`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md`) — CONCEPT.md selbst bleibt so knapp wie möglich,
aber **rebuild-safe**: Ein neues Team könnte allein aus CONCEPT.md Abschnitt 6b das Zielmodell
(Leaf/Parent, `has_children`, Aggregation, Subproject-/Milestone-Ablösung) korrekt
rekonstruieren, ohne dieses Dokument gelesen zu haben — die Begründungen/Alternativenabwägung
(warum nicht Option A/C, warum keine BD für X) müssen das nicht, das ist Prozesswissen, kein
Fachwissen (identische Trennung wie in Pass 1 etabliert).

---

## 30. Implementation Packages

Reihenfolge = Abhängigkeitsreihenfolge (Abschnitt 31). Jedes Paket ist unabhängig
freigebbar/testbar. Namensschema `B-<n>` (Pass 2), um Verwechslung mit Pass 1s `P18.<n>` zu
vermeiden — beide Nummernkreise dürfen im selben Projekt nicht parallel abgearbeitet werden
(Pass 2 ersetzt Pass 1, Abschnitt 27).

### B-1 — Schema: `parent_phase_id`, `PlanPhase.reihenfolge`, `Milestone.plan_phase_id`

- **Ziel:** Additive Spalten, keine Verhaltensänderung.
- **Scope:** Alembic-Migration (Abschnitt 23), Modell-Update (`models.py`).
- **Out of Scope:** Jede Backend-Logik, die diese Spalten liest/schreibt.
- **DB:** 3 additive `ALTER TABLE`-Statements, kein Datenverlust, keine Downtime-Anforderung.
- **Tests:** `check_migrations.py` (Kette intakt), Roundtrip-Test (Migration hoch/runter).
- **Dependencies:** keine.
- **Risks:** minimal — rein additiv.
- **Acceptance Criteria:** Migration läuft sauber gegen eine Kopie der aktuellen DB, alle
  bestehenden Endpunkte unverändert funktionsfähig (Regressionstest).
- **Definition of Done:** Code Review, `check_migrations.py` grün.

### B-2 — Calculation Layer: `has_children`, `derive_parent_bounds/capacity`,
`compute_project_monthly_capacity`

- **Ziel:** Neue, reine Berechnungsfunktionen (Abschnitt 24), keine API-Exposition.
- **Scope:** `backend/app/phase_metrics_calc.py`/`capacity_calc.py`, neues
  `backend/app/planning_calc.py` für die Baum-Aggregation.
- **Out of Scope:** Router-Änderungen, Frontend.
- **Tests:** Unit-Tests mit dem Red-Bull-WMS-Zahlenbeispiel aus Pass 1 (unverändert
  wiederverwendbar, Abschnitt 24), jetzt als 3-Phasen-Baum statt Grob+Fein modelliert.
- **Dependencies:** B-1.
- **Risks:** Divide-by-zero/leere Kinderliste bei `derive_parent_bounds` — Schutz analog zu
  bestehendem `plan_hours`-Nullchecks.
- **Acceptance Criteria:** Alle Testfälle aus Pass 1 (T1-T7, angepasst auf Baum-Terminologie)
  grün.
- **DoD:** Code Review, Unit-Tests grün.

### B-3 — Router: `parent_phase_id`-CRUD-Guards, `PlanPhaseDetail.children`/`derived_capacity`

- **Ziel:** `planning.py` um Parent-Validierung (Zyklen, Tiefe ≤ 3, Projekt-Grenze) erweitern,
  analog zu `_check_subproject`/`_check_owner`.
- **Scope:** `backend/app/routers/planning.py`, `backend/app/schemas.py`
  (`PlanPhaseOut.parent_phase_id`, `PlanPhaseDetail.children`/`derived_capacity`).
- **Out of Scope:** Datenmigration (B-5), Löschen bestehender Endpunkte.
- **Tests:** `TestClient`-Integrationstests (Zyklus ablehnen, Tiefe-4 ablehnen,
  projektfremden Parent ablehnen — analog zu bestehenden `_check_subproject`-Tests).
- **Dependencies:** B-1, B-2.
- **Risks:** gering — additiv, kein bestehender Endpoint verliert Funktionalität.
- **Acceptance Criteria:** Guards greifen in allen dokumentierten Edge Cases (Abschnitt 9.3).
- **DoD:** Code Review, Integrationstests grün.

### B-4 — Router: Milestone `plan_phase_id`, Baseline-`_SNAPSHOT_FIELDS`-Erweiterung

- **Ziel:** `Milestone.subproject_id` → `plan_phase_id` operativ (Abschnitt 15),
  `_SNAPSHOT_FIELDS`-Erweiterung (Abschnitt 16).
- **Scope:** `backend/app/routers/planning.py` (Milestone-CRUD), `backend/app/routers/
  baselines.py`, `backend/app/baseline_calc.py` (Deviation-Anzeige für `parent_phase_id`-
  Änderungen).
- **Out of Scope:** Milestone-Frontend (B-6).
- **Tests:** Integrationstest: Milestone an Parent-Phase, Baseline friert Struktur ein und
  zeigt eine strukturelle Abweichung nach Reparenting korrekt an.
- **Dependencies:** B-1, B-3.
- **Risks:** gering.
- **DoD:** Code Review, Integrationstests grün.

### B-5 — Migration: Bestehende `Subproject`- und Grob-`ResourceDemand`-Daten

- **Ziel:** Einmaliges, deterministisches Migrationsskript (Abschnitt 20/22).
- **Scope:** Neues Skript (z. B. `backend/scripts/migrate_to_planphase_hierarchy.py`), **kein**
  Alembic-Bestandteil (Datenmigration, keine Schemaänderung — folgt damit demselben Muster wie
  frühere Datenkonvertierungen dieses Repos, z. B. Legacy Cutover Phase 26.9).
- **Out of Scope:** Schema-Drop von `subprojects`/`subproject_id` (späterer, eigener Schritt).
- **DB:** nur Daten-INSERT/UPDATE, keine Struktur.
- **Tests:** Vorher-/Nachher-Zahlenvergleich je Projekt (FTE-Summen, Assignment-Anzahl,
  Milestone-Anzahl unverändert) — Pflicht-Akzeptanzkriterium, kein optionaler Test.
- **Dependencies:** B-1, B-3, B-4. **Blockiert bis BD-11/BD-12 entschieden sind.**
- **Risks:** einziges Paket mit echtem Datenrisiko in diesem Durchgang — Dry-Run-Modus
  (Report ohne Schreiben) als Pflichtfeature vor dem echten Lauf.
- **Acceptance Criteria:** Zahlenreport zeigt 0 verlorene FTE-Summe, 0 verlorene Assignments,
  0 verlorene Milestones/Comments über alle migrierten Projekte.
- **DoD:** Code Review, Dry-Run-Report gegen eine Kopie der Produktivdaten (oder
  repräsentativer Testdaten) verifiziert.

### B-6 — Frontend: Baum-UI (Liste, Gantt, Workspace, Create-Modal)

- **Ziel:** Abschnitt 26 vollständig umsetzen.
- **Scope:** `PlanPhaseList.tsx`, `PlanPhaseGantt.tsx`, `PlanPhaseWorkspace.tsx`,
  `PlanPhaseCapacityTab.tsx`, `PlanPhaseCreateModal.tsx`, `MilestoneList.tsx`,
  `ProjectPlanningTab.tsx`, `ProjectCommunicationTab.tsx`, `types.ts`, `client.ts`, neuer Hook
  `usePhaseTree`.
- **Out of Scope:** `ResourceDemandGrid.tsx`-Entfernung (eigenes Paket B-8, da destruktiv am
  Frontend-Code).
- **Tests:** Playwright — Baum anlegen (3 Ebenen), Parent-Aggregation korrekt angezeigt,
  Kollabieren/Expandieren, Milestone an Parent-Phase, Rollen-optionale Personenzuordnung
  (Abschnitt 11).
- **Dependencies:** B-3, B-4.
- **Risks:** größtes Frontend-Einzelpaket dieses Durchgangs (Abschnitt 3.3: keine
  Tree-UI-Vorlage vorhanden) — realistisch mehrteilig, nicht in einem Zug.
- **DoD:** `npm run build`/`npm run lint` clean, Playwright-Checks grün.

### B-7 — Available Capacity über Phasenzeitraum

- **Ziel:** `compute_person_capacity_for_range` (Abschnitt 12), 1:1 aus Pass 1 (P18.6)
  übernommen.
- **Scope, Tests, Risks:** unverändert identisch zu Pass 1s P18.6-Beschreibung.
- **Dependencies:** keine (unabhängig, kann parallel zu B-1…B-6 laufen).

### B-8 — Aufräumen: `ResourceDemandGrid.tsx` entfernen, Subproject-Legacy markieren

- **Ziel:** Abschnitt 27, Schritt 5.
- **Scope:** `ResourceDemandGrid.tsx` löschen, zugehörige `client.ts`-Funktionen als
  `@deprecated` markieren (nicht sofort entfernen — Frontend/Backend-Rollout-Reihenfolge
  könnte kurzzeitig auseinanderlaufen).
- **Out of Scope:** Schema-Drop (eigener, noch späterer Schritt, erst nach einer
  Beobachtungsphase — analog zu `PlanPhase.progress`, das seit P6/P11 ebenfalls nur
  compat-only bleibt, CONCEPT.md Abschnitt 15).
- **Dependencies:** B-5, B-6 (Migration muss abgeschlossen, Frontend muss umgestellt sein,
  bevor die alte Grobplanungs-UI verschwindet).
- **Risks:** gering, da rein additiv-vorbereitet.
- **DoD:** Code Review, keine verwaisten Imports (`npm run lint`/`tsc` clean).

---

## 31. Dependency Graph

```
B-1 (Schema)
  │
  ├──> B-2 (Calc Layer)
  │      │
  │      └──> B-3 (Router: Guards, children/derived_capacity)
  │             │
  │             ├──> B-4 (Milestone/Baseline)
  │             │      │
  │             │      └──> B-5 (Datenmigration) ── blockiert bis BD-11 + BD-12 entschieden
  │             │             │
  │             │             └──> B-6 (Frontend Baum-UI)
  │             │                    │
  │             │                    └──> B-8 (Aufräumen)
  │             │
  │             └──> (B-6 kann UI-Gerüst parallel zu B-4 bauen, sofern Backend-Mocks reichen —
  │                    tatsächliche Live-Integration wartet auf B-5)
  │
  └──> B-7 (Available Capacity über Zeitraum) ── unabhängig, sofort umsetzbar
```

Kritischer Pfad: B-1 → B-2 → B-3 → B-4 → B-5 → B-6 → B-8. B-7 ist vollständig entkoppelt
(identisch zu Pass 1s P18.6-Einordnung). B-5 ist der einzige echte Blocker vor Business-
Decision-Freigabe (BD-11/BD-12) — alles davor (B-1…B-4) kann sofort nach Freigabe dieses
Designs beginnen, unabhängig vom BD-Ausgang, da es keine Datenmigration vorwegnimmt.

---

## 32. Parallel Agent Plan

- **Strang A (Backend-Kern):** B-1 → B-2 → B-3 → B-4, sequenziell (jeweils voneinander
  abhängig).
- **Strang B (Migration):** B-5 — kann erst nach Strang A vollständig starten, aber
  eigenständig vorbereitet werden (Skript-Grundgerüst, Dry-Run-Report-Format) sobald B-1
  gemergt ist.
- **Strang C (Frontend):** B-6 — UI-Gerüst (Baum-Rendering-Hook, Komponenten-Umbau) kann gegen
  Mock-Daten parallel zu Strang A entstehen, echte Integration wartet auf B-3/B-4/B-5.
- **Strang D (unabhängig):** B-7 — kann jederzeit parallel zu A/B/C laufen, exakt wie in Pass 1.
- **Nicht parallelisierbar vor Freigabe:** B-5 darf **nicht** gestartet werden, bevor BD-11 und
  BD-12 vorliegen — kein Agent sollte darauf angesetzt werden, solange diese offen sind.
- **Koordinationspunkt:** B-6 und B-8 berühren teilweise dieselben Dateien
  (`ResourceDemandGrid.tsx` wird in B-6 noch nicht verändert, in B-8 gelöscht) — B-8 darf erst
  nach B-6-Merge starten, um Merge-Konflikte zu vermeiden.

---

## 33. Rebuild Safety Assessment

Prüf-Frage (wie in Pass 1): Könnte ein kompetentes Team allein aus CONCEPT.md (ohne dieses
Dokument) rekonstruieren, was die PlanPhase-Hierarchie ist, wie sie Subproject/Grobplanung
ablöst und welche Regeln gelten?

| Anforderung | Erfüllt in CONCEPT.md (nach den in Abschnitt 29 vorgenommenen Änderungen)? |
|---|---|
| Was die App tut | Ja — Abschnitt 1/2 unverändert |
| Wie Projektplanung funktioniert (jetzt hierarchisch) | Ja — Abschnitt 5 wird um den Verweis auf 6b ergänzt |
| Wie Kapazität geplant wird (Leaf-only, Aggregation) | Ja — neuer Abschnitt 6b, vollständig |
| Welche Modelle benötigt werden | Ja — Abschnitt 4 (Tabellenliste) wird um `parent_phase_id`/`reihenfolge` auf `PlanPhase`, `plan_phase_id` auf `Milestone` ergänzt, `subprojects` als "compat-only, siehe 6b" markiert |
| Welche Berechnungen gelten (mit Formeln/Beispielen) | Ja — Abschnitt 6b referenziert die Formel aus Abschnitt 13 dieses Dokuments, mit dem übernommenen Zahlenbeispiel |
| Wie die UI funktionieren soll | Ja — Abschnitt 6b, Kurzfassung mit Verweis auf dieses Dokument für Details |
| Welche Regeln/Edge Cases gelten | Ja — Leaf/Parent-Semantik (Abschnitt 9) vollständig in 6b übernommen |
| Welche Entscheidungen offen sind | Ja — Abschnitt 14 (BD-10 bis BD-13) |
| Warum Pass 1 (6a) nicht mehr aktuell ist | Ja — expliziter Superseded-Hinweis am Anfang von 6a (Abschnitt 29) |

**Bewertung: Rebuild-safe**, unter derselben bewussten Ausnahme wie Pass 1: Migrationsskript-
Detailcode (Abschnitt 20/22) und Paket-/Abhängigkeitsplanung (Abschnitt 30/31) bleiben in
diesem Prozessdokument, nicht in CONCEPT.md — konsistent mit der etablierten
Trennung "CONCEPT.md trägt Fachwissen, `P18_*`-Dokumente tragen Prozesswissen".

---

## 34. Final Recommendation

Die fachliche Analyse favorisiert eindeutig **Option B (PlanPhase-only, hierarchisch)**
gegenüber Option A (Pass 1, Grob-/Feinplanung) — nicht als Geschmacksfrage, sondern weil Option
B dieselbe fachliche Anforderung mit **einer** Struktur statt **drei** (Grobplanung,
Feinplanung, Subproject) löst, Doppelzählung durch Konstruktion statt durch eine
Reconciliation-Formel verhindert, und in der Codebase-Prüfung (Abschnitt 3) bestätigt eine
Nettoreduktion an Code/Konzepten bewirkt (`ResourceDemandGrid.tsx` entfällt vollständig, drei
Business Decisions aus Pass 1 werden obsolet).

Die verbleibenden vier Business Decisions (BD-10 bis BD-13, Abschnitt 28) sind bewusst klein
gehalten — anders als in Pass 1 ist **nicht** "alles" eine offene Entscheidung: Leaf/Parent-
Semantik, Rollen-Optionalität, Available-Capacity-Erweiterung, Baseline-Mechanik,
Zyklenprävention und Collaboration-Bindung sind technisch eindeutig beantwortet und **keine**
BD. Nur die Migrationsstrategie für echte Bestandsdaten (BD-12), das Löschverhalten (BD-11),
die Hierarchietiefe (BD-10) und der Umgang mit der jetzt überflüssigen
Konkretisierungsgrad-Kennzahl (BD-13) sind echte Produktentscheidungen mit Wertungscharakter,
die eine Freigabe verdienen.

**MOVE TO PLANPHASE-ONLY ARCHITECTURE**

Konkret benötigt, bevor Paket B-5 (Datenmigration, Abschnitt 30) gestartet werden darf:
Freigabe zu BD-11 (Löschverhalten) und BD-12 (Migrationsstrategie). BD-10 (Hierarchietiefe)
wird vor B-3 benötigt (Guard-Logik hängt von der Zahl ab), BD-13 (Konkretisierungsgrad) vor
B-6 (Frontend). Pakete B-1, B-2, B-7 können unabhängig davon sofort freigegeben und begonnen
werden, sobald dieses Design abgenommen ist — identisch zur in Pass 1 etablierten Praxis,
BD-unabhängige Pakete nicht auf die langsamste Entscheidung warten zu lassen.

`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md` (Pass 1) bleibt als historisches Dokument im Repository
bestehen — es wird durch diesen Durchgang **fachlich abgelöst**, nicht gelöscht (derselbe
Grundsatz wie bei `Subproject`/Grobplanung selbst: kein Drop-and-Pray, auch nicht bei
Dokumenten).
