# P19 — PlanPhase Workspace & Project Planning Experience

**UX-Audit, Workflow-Konsolidierung und Implementierungsplan.** Kein Architektur-Durchgang —
P18 ist fachlich abgeschlossen (CONCEPT.md, BD-1–BD-13 geschlossen bzw. bewusst offen
dokumentiert). Dieser Durchgang ist NICHT implementiert; er ist Audit + Zielbild + Gap-Liste +
Implementierungsplan.

---

## 1. Executive Summary

Der Codebase-Audit (drei parallele Recherchen: Frontend-Workspace/IA, Frontend-Collaboration/
Tags, Backend-Router) ergibt ein deutlich positiveres Bild, als der Auftragstext befürchtet:

**Die in CONCEPT.md §10 dokumentierte Zielstruktur — ein `PlanPhaseWorkspace`-Drawer mit
genau vier Tabs (Übersicht/Kapazität/Aktivität/Dateien) — existiert bereits im Code und
funktioniert im Kern wie spezifiziert:**

- `PlanPhaseWorkspace.tsx` ist bereits der zentrale Arbeitskontext, öffnet identisch aus Liste
  und Gantt, lädt seine Kerndaten in einem Aufruf (`GET /plan-phases/{id}` →
  `PlanPhaseDetail`), speichert sofort ohne Grund-Workflow.
- Technische Feldnamen (`forecast_start`, `parent_phase_id`, `plan_fte`, `actual_start/end`)
  leaken **nicht** in die UI — Übersetzung in Fachsprache ist bereits konsequent umgesetzt.
- Direct Assignment ohne Rollenzwang, optionale Rollenaufschlüsselung, Parent-Phase mit
  ausgeblendetem Kapazitäts-Editierpfad, Planstand mit menschenlesbaren Labels inkl. "Phase
  hinzugefügt/entfernt" — alles bereits **CONFIRMED gegen Code**.

**P19 ist damit kein Neubau, sondern ein gezielter Politur-Durchgang.** Die real gefundenen
Lücken sind chirurgisch, nicht strukturell:

1. Milestones erscheinen nicht im PlanPhase-Workspace (nur projektweit).
2. Kommentar-Threading (`parent_id`) existiert im Backend, aber nirgends im Frontend.
3. "Aus Kommentar erstellen" ist nur im Activity-Feed erreichbar, nicht in der Kommentarliste
   selbst — und schlägt nur die Tags des Kommentars vor, nicht zusätzlich die der Phase.
4. Der Dateien-Tab im Workspace ist eine dritte, schwächere Implementierung der
   Dokumentenliste (kein Tags-Filter, keine "Verwendet in"-Backlinks) statt Wiederverwendung
   der bereits vorhandenen vollständigen Komponente.
5. Tasks/Blocker/Decisions erlauben Tags beim Anlegen, aber kein Nachbearbeiten (Milestones
   können das bereits).
6. Kein phasenbezogener Planstand-Vergleich ("Was hat sich seit V2 an dieser Phase
   geändert?") — nur der volle, projektweite Deviation-Feed.
7. Breadcrumbs zeigen nur die direkte Elternphase, keine vollständige Ahnenkette.
8. Der Planung-Tab zeigt die neue PlanPhase-Baum-Logik und die alte Subproject-/
   ResourceDemandGrid-Logik optisch gleichrangig nebeneinander (bewusster B-8-Compat-Zustand,
   aber UX-seitig aufräumbar ohne Datenmodelländerung).

Keine dieser Lücken erfordert ein neues Datenmodell, eine neue Capacity-Engine oder eine neue
Activity-Tabelle. Alle sind additive Frontend-Arbeit, teils mit kleinen additiven
Backend-Erweiterungen (nie neue Endpoints, wo ein bestehender reicht).

**Verdict am Ende dieses Dokuments: READY FOR P19 IMPLEMENTATION.**

---

## 2. Small CONCEPT Consistency Fix

Erledigt vor diesem Audit (Commit `0b33dcb`, bereits gepusht auf
`claude/p19-planphase-ux-audit-ajyv68`):

Abschnitt 4 (Aktuelles Datenmodell) beschrieb bei `baseline_snapshots`/`baseline_entries` noch
den Vor-P18.1-Zustand ("erkennt aber 'Phase hinzugefügt' nicht und 'Phase entfernt' nur
unvollständig"). Das wurde in Abschnitt 16.16 (P18.1 Stabilization) bereits behoben. Abschnitt
4 wurde korrigiert auf den aktuellen IST-Zustand:

> „…Deviation-Erkennung deckt Parent-Wechsel/Zeitraum/`plan_fte` ab **und erkennt seit P18.1
> (Abschnitt 16.16) zusätzlich strukturelle Baum-Änderungen**: ‚Phase hinzugefügt'
> (`type="added"`) und ‚Phase entfernt' (`type="removed"`, …) werden beide erkannt … — der
> frühere Gap (Abschnitt 16.15) ist behoben."

Abschnitt 16.16 selbst wurde **nicht verändert** — er bleibt als Umsetzungsverlauf/Historie
stehen (Abschnitt 1–14 = IST-Zustand, Abschnitt 16 = Umsetzungsverlauf, Abschnitt 17 =
Historie, wie gefordert).

---

## 3. Current UX Audit

Frontend-Root: `frontend/src`. Planungs-UI unter `frontend/src/views/project/` (+
`components/`). Backend-Root: `backend/app`, Router unter `backend/app/routers/`.

### 3.1 PlanPhaseWorkspace (Drawer)

`frontend/src/views/project/components/PlanPhaseWorkspace.tsx` (496 Zeilen) — fixiertes
Right-Side-Drawer, kein eigener Route-Screen, gerendert wenn `openPhaseId != null`.

- Öffnet identisch aus `PlanPhaseList.tsx` (Karte/„Öffnen →") **und** `PlanPhaseGantt.tsx`
  (Klick auf Balken) — beide treiben denselben `openPhaseId`-State, mounten dieselbe
  Drawer-Instanz. CONCEPT §5.6 ist damit CONFIRMED.
- Ein Datenaufruf (`api.getPlanPhaseDetail`) liefert `children`, `comments`, `tasks`,
  `blockers`, `decisions`, `resource_demands`, `metrics`, `derived_forecast_start/end`,
  `derived_capacity`, `has_children`, `tags`, `documents` — hydratisiert drei der vier Tabs in
  einem Call. **Nicht enthalten:** Milestones, Assignment-Summary (Bedarf/Besetzt/Offen),
  Activity-Feed-Items — je ein separater Aufruf.
- Vier Tabs exakt wie CONCEPT §10: Übersicht/Kapazität/Aktivität/Dateien. Header zeigt Name,
  „+ Unterphase" (nur wenn Tiefe < `MAX_PLAN_PHASE_DEPTH`), „Schließen", und **eine** Zeile
  „Übergeordnete Phase: X" — kein voller Breadcrumb-Pfad bis zur Wurzel.
- Speichern: jedes Feld `onBlur`/`onChange` → sofortiges `PUT` + Reload. Kein Batch-/
  Grund-Workflow (CONCEPT §10 CONFIRMED).

Es existiert **keine** separate `PlanPhaseOverviewTab.tsx` — die Übersicht ist inline in
`PlanPhaseWorkspace.tsx` (Zeilen 205–387), anders als `PlanPhaseCapacityTab.tsx`, die extrahiert
ist. Rein strukturell unauffällig, aber für P19.1 relevant, falls eine Milestones-Sektion
ergänzt wird (Datei wächst dann weiter).

### 3.2 Übersicht-Tab

Alle Felder bereits in Fachsprache, keine Rohfeldnamen sichtbar:

| Fachbegriff (UI) | Technisches Feld | Editierbar | Parent-Verhalten |
|---|---|---|---|
| Name | `phase_type` (mit Vorschlagsliste) | ja, inline | wie Leaf |
| Zeitraum | `forecast_start`/`forecast_end` | ja, inline | read-only, „abgeleitet aus N Unterphase(n)" |
| Status | `status` (Freitext, gemappt über Label-Tabelle) | ja, inline | wie Leaf |
| Geplanter Ressourcenbedarf | `plan_fte` | ja, inline | **ausgeblendet**, stattdessen „aggregiert, nicht direkt editierbar" |
| Übergeordnete Phase | `parent_phase_id` | ja, Select (= Reparenting-UX) | n/a |
| Owner | `owner_person_id` | ja, `PersonPicker` | wie Leaf |
| Tags | `tags[]` | ja, `TagInput` | wie Leaf |
| Planstunden/Zeitfortschritt/Ist-Aufwand | berechnet | nein | wie Leaf |
| Tatsächlicher Verlauf | `actual_start/end` | sekundär, „Ist-Daten korrigieren" | wie Leaf |

`BaselineSnapshot`/`ResourceDemand` erscheinen auf diesem Tab **nicht** — Planstand lebt in
`BaselineList.tsx` (Projektebene), `ResourceDemand` im Kapazität-Tab. Owner/Tags/Status sind
bereits direkt editierbar, kein separater Edit-Modus. **Section-4-Ziel des Auftrags ist damit
bereits erreicht**, keine Frontend-Änderung nötig.

### 3.3 Kapazität-Tab / Direct Assignment

`PlanPhaseCapacityTab.tsx` (449 Zeilen), nur für Leaf-Phasen gemountet.

1. Kopfzeile: Geplanter Ressourcenbedarf (`plan_fte`) + Planstunden, read-only.
2. **Personenbesetzung** (Primärpfad): „+ Mitarbeiter zuweisen" → `PersonPicker` + FTE-Zahl,
   zeigt Kandidatenvorschläge und verfügbare Kapazität im Zeitraum
   („Verfügbar: X FTE · Rest danach: Y FTE"). Ruft `assign-person` **ohne** Rollenauswahl auf
   — CONCEPT §6.4/§6.10 CONFIRMED. Bedarf/Besetzt/Offen (bzw. „Überbesetzt", rot) wird aus dem
   serverseitig vorberechneten `assignment-summary`-Endpoint gespeist.
3. **„▸ Rollen aufschlüsseln (optional)"** — eingeklappt per Default, explizite Caption „Nie
   Voraussetzung für eine direkte Personenzuweisung". Enthält eine **zweite**,
   rollen-scoped Zuweisungs-UI (`DemandAssignments` pro `ResourceDemand`) — funktional korrekt
   getrennt vom Primärpfad, aber zwei sichtbare Zuweisungswege auf einem Tab sind ein
   Komplexitätsrisiko, das in P19.2 durch klarere visuelle Hierarchie (nicht durch
   Funktionsentzug) entschärft werden sollte.
4. Backend-Ineffizienz: `assignment-summary` ist zwar vorberechnet, wird aber nicht in
   `PlanPhaseDetail` eingebettet, und bei aufgeklappter Rollenaufschlüsselung entsteht ein
   N+1-Muster (pro `ResourceDemand` je ein `listResourceAssignments`+`getCandidates`-Call).
   Kein Architekturfehler, aber ein Ziel für P19.2 (Response-Bündelung, kein neuer Endpoint
   nötig — Erweiterung von `PlanPhaseDetail` bzw. `assignment-summary` um die Rollenzeilen).

### 3.4 Parent-Phase-UX

Bereits CONFIRMED gegen Code: `plan_fte`-Eingabe komplett ausgeblendet für Parents
(`!detail.has_children`-Guard), Kapazität-Tab zeigt für Parents eine eigene, kleine
„Kapazität (aggregiert)"-Karte statt `PlanPhaseCapacityTab` zu mounten, keine
Personenzuweisungs-UI. Liste/Gantt zeigen `derived_*`-Werte mit „(abgeleitet)"/„(aggregiert)"
statt Rohfeldern; Parent-Gantt-Balken sind umrandete Hüllkurven, Leaf-Balken gefüllt (CONCEPT
§5.6/§6.3 CONFIRMED). **Kein Handlungsbedarf für P19** außer optischem Feinschliff (Dichte,
siehe §17 unten).

### 3.5 Tree-Navigation, Löschen, Reparenting

`PlanPhaseList.tsx`: rekursiver Tree über `parent_phase_id`, Collapse/Expand pro Parent, „+
Unterphase" pro Zeile (bis Tiefenlimit), Listen-/Gantt-Umschalter. `PlanPhaseGantt.tsx`: rein
visuell, eigener (nicht mit der Liste geteilter) Collapse-State — geringe Inkonsistenz, kein
Blocker. `PlanPhaseDeleteDialog.tsx`: dreistufiger Flow (Confirm → 409-Blocked →
Subtree-Delete mit Impact-Report und Namens-Bestätigung) — CONCEPT §6.9/BD-11 vollständig
CONFIRMED, inklusive „Unterphasen verschieben"-Option. Reparenting läuft ausschließlich über
den „Übergeordnete Phase"-Select im Drawer, kein Drag&Drop (bewusst, CONCEPT §21).

**Gap:** Breadcrumbs zeigen nur die direkte Elternphase (eine Zeile), keine volle Ahnenkette
bis zur Wurzel — bei 3 Ebenen ist das grenzwertig lesbar, wenn man auf Ebene 3 landet, ohne zu
sehen, unter welcher Ebene-1-Phase man sich befindet.

### 3.6 ProjectPlanningTab (Projektebene)

`ProjectPlanningTab.tsx` (140 Zeilen) stapelt fünf Karten: `PlanPhaseList`, `MilestoneList`,
**`ResourceDemandGrid`** (Legacy, `@deprecated P18/B-8` im eigenen Header-Kommentar),
`BaselineList`, **Subproject-CRUD** (inline, Legacy). Neue (`PlanPhase`-Baum) und alte
(`Subproject`/`ResourceDemandGrid`) Paradigmen sind auf derselben Seite optisch gleichrangig
sichtbar — exakt der von CONCEPT §5.4/§6.15 dokumentierte, bis B-8 unvermeidliche
Compat-Zustand. `ProjectHistoryTab.tsx` und `ProjectCommunicationTab.tsx` gruppieren
zusätzlich weiterhin nach `subproject_id`.

**P19-relevant, nicht B-8-relevant:** Die visuelle Gleichrangigkeit ist ein UX-Problem, das
sich ohne Datenmigration lösen lässt — Legacy-Karten können als klar beschrifteter, eingeklappter
Block „Altprojekte (Migration ausstehend)" dargestellt werden, ohne Funktion zu verlieren
(siehe P19.7).

### 3.7 Activity Feed & Filter

`ActivityFeed.tsx` (288 Zeilen) — ein Backend-Aufruf (`GET /plan-phases/{id}/activity` bzw.
projektweit), keine Client-seitige Merge-Logik über mehrere Endpoints. Typ-Filter-Buttons +
Tag-Filter bereits gebaut, beide client-seitig über das bereits geladene Array (kein
zusätzlicher Endpoint nötig, CONCEPT §8/§8-Auftrag „nur Backend-Erweiterung wenn Payload nicht
reicht" bereits erfüllt).

**Gap:** Der Backend-Endpoint (`_get_plan_phase_activity`) merged bereits `comment`/
`decision`/`task`/`blocker`/**`milestone`**/`baseline_snapshot` chronologisch — das Frontend
filtert aber aktuell nur `comment|decision|task|blocker` in seiner `PHASE_ACTIVITY_TYPES`-Liste
(`PlanPhaseWorkspace.tsx:36`) und zeigt Milestones/Baseline-Events im Phasen-Feed **nicht** an,
obwohl der Server sie liefert. Reiner Frontend-Fix (Typ-Liste erweitern), kein Backend-Bedarf.
Ein im Backend-Code gefundener veralteter Kommentar („Milestone hat keine `plan_phase_id`, wird
ausgeschlossen") ist sachlich falsch (das Feld existiert seit P18/B-7) und sollte bei der
Gelegenheit korrigiert werden.

### 3.8 Kommentare, Threading, "Aus Objekt erstellen"

`NotesSection.tsx` — **kein Threading/Reply in der UI**, obwohl `parent_id` im Backend-Modell
existiert (`models.py:257`) und CONCEPT §8 „inkl. Threading über parent_id" dokumentiert. Das
Backend-Feld wird von `api/client.ts` nicht einmal gesendet/angefragt. **Das ist eine echte,
im Auftrag (Tab 3 „Kommentare... Replies") explizit erwartete Lücke.**

„Aus Objekt erstellen" (`+ Aufgabe/+ Entscheidung/+ Blocker/+ Risiko`) existiert bereits
vollständig — aber **nur** innerhalb von `ActivityFeed.tsx`, wenn dort ein Kommentar gerendert
wird, nicht in `NotesSection.tsx`s eigener Kommentarliste. `EntityRelation(resulted_in)` wird
korrekt angelegt (`ActivityFeed.tsx:137-143`), Tags des Ursprungskommentars werden
vorgeschlagen (abwählbar) — aber **nicht** zusätzlich die Tags der Phase selbst, wie
Abschnitt 6 des Auftrags es als Beispiel zeigt (`#Schnittstelle #Kunde` von der Phase + `#API`
vom Kommentar).

### 3.9 Tags & Knowledge

`TagInput`/`TagChip`/`TagDossierPanel` bereits konsistent verdrahtet: ein
`TagDossierProvider` pro Projekt-Workspace, jeder `TagChip` überall öffnet dasselbe Dossier.
Tag-Erstellung ohne Admin-Seite (Suche → vorhandenen wählen → sonst „+ #{term} erstellen")
bereits CONCEPT-konform CONFIRMED. `TagDossierPanel` zeigt Entity-Type-Counts + bis zu 10
"Aktuelle Lage"-Activity-Items, aber **die Items sind nicht klickbar** — kein Drill-down von
Dossier zu Entität. Tag-Nachbearbeitung nach dem Anlegen fehlt bei Task/Blocker/Decision
(Milestone hat das bereits).

### 3.10 Dokumente

Backend: ein geteiltes System (`documents`/`document_links`), ein Upload-Pfad überall
CONFIRMED. Frontend: **drei unterschiedlich mächtige Renderer** für dieselben Daten —
`AttachmentList` (minimal, in Comment/Task/Blocker/Decision/Milestone), `ProjectDocumentsTab`
(volle Funktionalität: Suche, Tag-Filter, „Verwendet in"-Backlinks), und der Dateien-Tab in
`PlanPhaseWorkspace` (eigene, handgerollte `<ul>`-Liste ohne Tags/Suche/Backlinks). CONCEPT §8
verspricht „exakt dasselbe System" — technisch korrekt (gleicher Upload-Endpoint), UX-seitig
aber nicht gleich mächtig. **Konkreter P19-Fix:** Dateien-Tab auf die volle
`ProjectDocumentsTab`-Darstellung (gefiltert auf die Phase) umstellen statt eigener Liste.

### 3.11 Baseline / Planstand

`BaselineList.tsx` — bereits menschenlesbar: `FIELD_LABELS`-Mapping, Datums-Deltas
(„13.11.2026 → 20.11.2026 (+7 Tage)"), FTE-Deltas, strukturelle „+ Phase hinzugefügt"/„−
Phase entfernt" mit Namen statt Roh-ID. Ein bewusster Roh-ID-Fallback (`Phase #{id}`) bleibt
für den Randfall „Phase nach dem Planstand gelöscht" — dokumentiert, akzeptabel, keine
Änderung nötig.

**Gap:** Kein phasenscoped „Was hat sich seit Planstand V2 an dieser Phase geändert?" —
der Deviation-Endpoint liefert immer alle Abweichungen des ganzen Projekts, ohne
`plan_phase_id`-Parameter. Frontend müsste client-seitig nach `entity_id`/Nachfahren filtern.

### 3.12 Milestones

`MilestoneList.tsx` zeigt bereits den zugeordneten Phasennamen pro Zeile (`planPhaseName`),
inkl. „Projektweit" für `NULL`. **Aber:** `MilestoneList` wird nirgends in
`PlanPhaseWorkspace.tsx` gemountet — es gibt aktuell **keine** kompakte
„Meilensteine dieser Phase"-Ansicht im Workspace, wie der Auftrag (Abschnitt 18) es zeigt. Ein
Nutzer muss den Drawer verlassen, um Phasen-Milestones zu sehen.

### 3.13 Backend-Zusammenfassung (Round-Trip-Gaps)

| Bereich | Ein Call liefert bereits | Frontend/Backend braucht heute mehr |
|---|---|---|
| Phasendetail | `PlanPhaseDetail` (Kinder/Kommentare/Tasks/Blocker/Decisions/Demands/Metrics/Tags/Docs) | Milestones, Assignment-Summary, Activity — je separat |
| Assignment | `assignment-summary` (Bedarf/Besetzt/Offen) | 2. Call vs. Detail; N+1 bei Rollenaufschlüsselung |
| Follow-up-Objekt | Create-Endpoint + `POST /entity-relations` | zwei sequentielle Calls (laut CONCEPT so vorgesehen, kein Fix nötig) |
| Activity | merged, `plan_phase_id`-gefiltert, inkl. Milestone/Baseline | Typ/Tag-Filter clientseitig (ausreichend) |
| Knowledge/Tag-Counts | projekt-/tag-scoped Counts vorhanden | keine phasen-scoped Counts — clientseitig aus `knowledge/context` ableitbar |
| Baseline-Deviations | ganzes Projekt, menschenlesbar, added/removed-aware | keine `plan_phase_id`/Subtree-Filterung |
| Dokumente | ein System überall | Tag-Filter serverseitig in-memory (Performance-Nit, kein UX-Gap) |

---

## 4. Codebase Validation Matrix

| Bereich | Bestehender Code | CONCEPT | UX-Status | Gap | Änderung nötig |
|---|---|---|---|---|---|
| PlanPhase Overview | `PlanPhaseWorkspace.tsx` (inline) | §5.1/§10 | **CONFIRMED** | Breadcrumb nur 1 Ebene | klein (P19.1) |
| Capacity (Kopfzeile/Assignment) | `PlanPhaseCapacityTab.tsx` | §6.2/§6.10 | **CONFIRMED** | N+1 bei Rollenaufschlüsselung | klein (P19.2) |
| Direct Assignment | `assign-person`/`assignment-summary` | §6.4/§6.11 | **CONFIRMED** | Summary nicht in Detail eingebettet | klein (P19.2) |
| Rollen (optional) | `DemandAssignments` | §6.4 | **CONFIRMED** | zwei sichtbare Zuweisungswege | UX-Klarheit (P19.2) |
| Tags (Grundfunktion) | `TagInput`/`TagChip` | §8 | **CONFIRMED** | — | keine |
| Tags (Nachbearbeiten bei Task/Blocker/Decision) | fehlt (Milestone hat es) | §5/§6 (Auftrag) | **PARTIAL** | keine Tag-Edit nach Anlage | klein (P19.4) |
| Tag-Vorschläge bei Folgeobjekten | `ActivityFeed.tsx` (nur Kommentar-Tags) | §6 (Auftrag) | **PARTIAL** | Phasen-Tags fehlen im Vorschlag | klein (P19.4) |
| Activity Feed (Backend) | `_get_plan_phase_activity` | §7/§8 (Auftrag) | **CONFIRMED** | veralteter Kommentar zu Milestones | trivial (P19.3) |
| Activity Feed (Frontend Typen) | `PHASE_ACTIVITY_TYPES` fehlt Milestone/Baseline | §7 (Auftrag) | **PARTIAL** | Milestones/Planänderungen fehlen im Phase-Feed | klein (P19.3) |
| Activity Filter | Typ+Tag, clientseitig | §8 (Auftrag) | **CONFIRMED** | — | keine |
| Kommentare (Basis) | `NotesSection.tsx` | §8 | **CONFIRMED** | — | keine |
| Kommentare (Threading/Replies) | Backend `parent_id`, kein Frontend | §8/Tab3 (Auftrag) | **MISSING** | keine Reply-UI | mittel (P19.3) |
| „Aus Kommentar erstellen" | nur in `ActivityFeed`, nicht in `NotesSection` | §8/§9 (Auftrag) | **PARTIAL** | split-location UX | klein (P19.3) |
| Blocker/Decision/Task (Anlage) | `TaskList`/`BlockerList`/`DecisionList` | §8 | **CONFIRMED** | — | keine |
| Documents (Backend) | `documents`/`document_links` | §8/§16 (Auftrag) | **CONFIRMED** | — | keine |
| Documents (Workspace-Tab) | eigene, schwächere Liste | §16 (Auftrag) | **PARTIAL** | keine Tags/Suche/Backlinks im Dateien-Tab | klein (P19.5) |
| Knowledge/Context | `knowledge/context`, `/tags/dossier` | §8/§17 (Auftrag) | **CONFIRMED** (kompakte Sektion baubar) | keine phasen-scoped Counts, aber ableitbar | klein (P19.4) |
| Tag Dossier Drill-down | `TagDossierPanel` (Items nicht klickbar) | §17 (Auftrag) | **PARTIAL** | keine Navigation zur Entität | klein (P19.4) |
| Milestones (Liste, Projektebene) | `MilestoneList.tsx` | §5.5/§18 (Auftrag) | **CONFIRMED** | — | keine |
| Milestones (in PlanPhase Workspace) | fehlt komplett | §18 (Auftrag) | **MISSING** | keine kompakte Phasen-Ansicht | mittel (P19.5) |
| Planstände (Basis/Diff) | `BaselineList.tsx`, `compute_deviations` | §5.3/§14 (Auftrag) | **CONFIRMED** | — | keine |
| Planstand im Phasenkontext | fehlt | §15 (Auftrag) | **MISSING** | kein "was änderte sich an dieser Phase" | mittel (P19.6) |
| Tree Navigation (Collapse/Add/Delete/Reparent) | `PlanPhaseList`/`PlanPhaseGantt`/`PlanPhaseDeleteDialog` | §6.9/§13 (Auftrag) | **CONFIRMED** | Breadcrumb unvollständig, Collapse-State nicht geteilt | klein (P19.1) |
| Parent Workspace | `PlanPhaseWorkspace.tsx` (Parent-Zweig) | §6.3/§12 (Auftrag) | **CONFIRMED** | — | keine |
| Derived Capacity (Projekt/Monat) | `capacity_calc.compute_project_monthly_capacity` | §6.6/§20 (Auftrag) | **PARTIAL** (Backend CONFIRMED, Frontend-Drilldown nicht auditiert) | UI-Verifikation offen | klein (P19.7, Verifikation) |
| Project Planning Tab | `ProjectPlanningTab.tsx` | §19/§21 (Auftrag) | **CONFLICT** (Legacy gleichrangig mit neuer Struktur) | visuelle Gleichrangigkeit Alt/Neu | mittel (P19.7) |
| Legacy (ResourceDemandGrid/Subproject) | aktiv, `@deprecated` markiert | §21 (Auftrag)/CONCEPT §6.15 | **bewusst unverändert bis B-8** | kein P19-Gap, nur Sichtbarkeits-Politur | klein (P19.7) |

---

## 5. Final Workspace Information Architecture

Keine Änderung an der bestehenden vier-Tab-Struktur nötig — sie ist bereits das Zielbild. P19
ergänzt Inhalte **innerhalb** der bestehenden Tabs, baut keine neuen Tabs (vermeidet
„Tab-Wand"):

```
PLANPHASE WORKSPACE (Drawer, unverändert 4 Tabs)
│
├── Übersicht          [unverändert + voller Breadcrumb-Pfad]
│
├── Kapazität           [unverändert, UX-Klarheit zwischen Direct/Rollen-Pfad]
│
├── Aktivität
│   ├── Activity Feed    [+ Milestone-/Planänderungs-Events sichtbar]
│   ├── Kommentare       [+ Threading/Replies, + "Aus Kommentar erstellen" direkt hier]
│   ├── Aufgaben/Blocker/Entscheidungen  [+ Tags nachbearbeitbar]
│   └── kompakte Meilensteine dieser Phase   [NEU, kleine Karte oben im Tab]
│
└── Dateien              [ersetzt durch volle Dokumenten-Komponente, phasengefiltert]

Übersicht-Tab zusätzlich:
└── kompakte Sektion "Verknüpfte Themen" (Tags + Counts) UND
    "Seit Planstand VX geändert" (nur wenn Planstände existieren)
```

**Begründung gegen einen 5. Tab „Milestones" oder „Planstände":** Beide Objektarten sind pro
Phase typischerweise 0–3 Einträge — eine kompakte Karte reicht, ein eigener Tab wäre Overhead
("Wand aus technischen Cards", Abschnitt 22 des Auftrags). Diese Platzierungsentscheidung ist
eine UX-Empfehlung dieses Dokuments, kein offener Business-Punkt (siehe Abschnitt 28).

---

## 6. Overview UX

Bereits am Ziel (siehe §3.2). Einzige Ergänzung: voller Breadcrumb-Pfad statt nur direktem
Parent, z. B. „Wareneingang › Schnittstellen › WE-Anmeldung" — clientseitig aus `allPhases`
ableitbar (bereits als Prop vorhanden), kein Backend-Bedarf.

---

## 7. Capacity UX

Bereits sehr nah am Zielbild aus Abschnitt 10 des Auftrags (Bedarf/Besetzt/Offen,
„+ Mitarbeiter zuweisen", keine sichtbare `ResourceDemand`-Erstellung im Primärpfad). Zwei
gezielte Polituren:

- Visuelle Trennung zwischen „Personenbesetzung" (Primärpfad) und „Rollen aufschlüsseln"
  (Sekundärpfad) schärfen, damit die zwei Zuweisungswege nicht wie Redundanz wirken, sondern
  wie bewusst getrennte Ebenen (Gesamt-FTE vs. optionale Rollendetails).
- Response-Bündelung: `assignment-summary` in `PlanPhaseDetail` einbetten oder mit einem
  Aufruf abholen, N+1 bei Rollenaufschlüsselung durch eine gebündelte
  `resource_demands`-Antwort (inkl. Assignments) ersetzen. Keine neue Capacity-Engine, nur
  Response-Shape-Erweiterung bestehender Endpoints.

---

## 8. Direct Assignment UX

Bereits CONFIRMED wie in Abschnitt 10 des Auftrags beschrieben: Person + FTE, Verfügbarkeit im
Zeitraum, Rest danach, keine Rollenauswahl nötig. Keine Änderung am Flow selbst — nur die in
§7 genannte Backend-Bündelung, um die Ladezeit beim Öffnen des Kapazität-Tabs zu verbessern.

---

## 9. Parent Phase UX

Bereits vollständig CONFIRMED (§3.4). Kein Gap. Einzige Ergänzung aus Konsistenzgründen:
dieselbe Meilensteine-Kompaktkarte (§5) soll auch im Parent-Workspace erscheinen (Meilensteine
dürfen laut CONCEPT §6.8 sowohl auf Leaf als auch Parent zeigen).

---

## 10. Tags & Knowledge UX

Grundfunktion (Suche/Zuweisen/Autocreate, Dossier-Öffnen) bereits CONFIRMED. Ergänzungen:

- Tag-Nachbearbeitung nach Anlage bei Task/Blocker/Decision (Muster von `MilestoneList.tsx`
  übernehmen — bereits vorhandene Lösung wiederverwenden, kein neuer Code-Pfad).
- „Verknüpfte Themen"-Kompaktsektion im Übersicht-Tab: Tags der Phase + Counts (Entscheidungen/
  Blocker/Dokumente) — clientseitig aus dem bereits vorhandenen `knowledge/context`-Aufruf
  ableitbar (Anzahl über `len(relations)`/`len(documents)`), kein neuer Endpoint.
- `TagDossierPanel`: „Aktuelle Lage"-Items klickbar machen (Navigation zur jeweiligen Entität/
  zum jeweiligen PlanPhase-Workspace) — reine Frontend-Ergänzung.

---

## 11. Activity & Collaboration UX

- Frontend-Typliste um `milestone`/`baseline_snapshot` erweitern, damit der Phasen-Feed zeigt,
  was das Backend bereits liefert (§3.7).
- Kommentar-Threading (Replies) im Frontend nachbauen: Antwort-Button, Einrückung nach
  `parent_id`, `createComment`/`listComments` um `parent_id` erweitern (Backend-Feld existiert
  bereits, keine Migration nötig).
- „Aus Kommentar erstellen" zusätzlich direkt in `NotesSection.tsx` anbieten (nicht nur im
  Activity-Feed) — dieselbe bestehende Logik (Create + `EntityRelation resulted_in`)
  wiederverwenden, nicht duplizieren.
- Tag-Vorschlag bei Folgeobjekten um die Tags der Phase ergänzen (zusätzlich zu den
  Kommentar-Tags), wie im Auftragsbeispiel (`#Schnittstelle #Kunde` von der Phase + `#API` vom
  Kommentar).

---

## 12. Follow-up Object Flow

Grundmechanik (`EntityRelation(resulted_in)`, zwei sequentielle Calls) bleibt unverändert —
CONCEPT dokumentiert das explizit als ausreichend, kein atomarer Endpoint nötig. P19 behebt
nur die Erreichbarkeit (§11) und die Tag-Vorschlagsquelle (Phase + Kommentar statt nur
Kommentar). Ursprungs-Nachvollziehbarkeit bleibt über `EntityRelation` sichtbar, keine neue
`origin_id`-Spalte.

---

## 13. Documents UX

Backend bereits ein System für alle Kontexte. Der Workspace-Dateien-Tab wird auf dieselbe,
bereits vorhandene volle Darstellung wie `ProjectDocumentsTab.tsx` umgestellt (Suche,
Tag-Filter, „Verwendet in"-Backlinks), gefiltert auf `entity_type=plan_phase`. Kein neues
Attachment-System, keine zweite Backend-Logik — reine Frontend-Wiederverwendung einer
existierenden Komponente statt der schwächeren Eigenbau-Liste.

---

## 14. Milestones UX

Neue, kompakte „Meilensteine dieser Phase"-Karte im Aktivität-Tab (und im Parent-Workspace,
§9): Liste der Milestones mit `plan_phase_id == aktuelle Phase`, Datum, Status-Punkt,
„+ Meilenstein" mit vorbelegtem `plan_phase_id`. Wiederverwendung von `MilestoneList.tsx`
(gefiltert), kein Duplikat, keine zweite Milestone-Engine. Empty State: „Noch keine
Meilensteine für diese Phase."

---

## 15. Planstand UX

`BaselineList.tsx` bleibt die zentrale Planstand-Verwaltung auf Projektebene (Entscheidung
siehe §28 — B, nicht A). Zusätzlich im Übersicht-Tab des Workspace: kompakte Zeile „Seit
Planstand V2 (12.11.2026) geändert: Ende +7 Tage, Bedarf +0,20 FTE" (oder „Keine Abweichung"/
„Kein Planstand vorhanden"), wenn ein Planstand existiert. Berechnung: bestehenden
Deviation-Endpoint aufrufen und clientseitig auf `entity_id == aktuelle Phase` (bzw. bei
Parent-Phasen zusätzlich auf die bekannte Nachfahren-ID-Menge aus `allPhases`) filtern — kein
neuer Endpoint, keine neue Snapshot-Engine, wie vom Auftrag gefordert.

---

## 16. Project Planning Tab UX

Struktur bleibt: PlanPhase-Baum ist der primäre Einstieg, Projektweite Zusatzbereiche
(Milestones, Gantt, Planstände, Derived Capacity) bleiben als eigene Karten daneben — nicht
alle Detailfunktionen parallel im Hauptscreen (Auftrag Abschnitt 19 bereits erfüllt). Einzige
Änderung: Legacy-Block (Subproject-CRUD + `ResourceDemandGrid`) wird optisch klar als „Altdaten
— nur für unmigrierte Projekte" gekennzeichnet und standardmäßig eingeklappt dargestellt
(nicht entfernt, nicht funktional verändert — reine Sichtbarkeits-Politur, reversibel, keine
Datenmigration, kein B-8-Vorgriff).

---

## 17. Derived Capacity UX

Backend (`compute_project_monthly_capacity`) ist laut CONCEPT §6.6/§13
„final gelockt, IMPLEMENTIERT, gegen Code CONFIRMED" — read-only, Monat-für-Monat, keine
Doppelzählung. Die im Auftrag (Abschnitt 20) gewünschte Drilldown-Darstellung
(„Oktober 112h ≈ 0,64 FTE → Pflichtenheft 48h, Konfiguration 64h") wurde in diesem Audit-Pass
**nicht separat verifiziert** (kein dedizierter Rechercheauftrag dafür) — das ist als offener
Verifikationspunkt in P19.7 aufgenommen, kein Blocker, da die Backend-Berechnung bereits
vorhanden und CONFIRMED ist; nötigenfalls nur eine Frontend-Darstellungsergänzung, kein neuer
Algorithmus.

---

## 18. Empty States

Bereits vorhanden und im Ton konsistent mit dem Auftrag:

| Kontext | Vorhandener Text |
|---|---|
| Keine Kommentare | „Noch keine Notizen." |
| Keine Aufgaben | „Noch keine Aufgaben." |
| Keine Blocker | „Keine Blocker." |
| Keine Entscheidungen | „Noch keine Entscheidungen." |
| Keine Aktivität | „Noch keine Aktivität." |
| Keine Dateien (Workspace) | „Noch keine Dateien." |
| Keine Dokumente (Projekttab) | „Keine Dokumente gefunden." |
| Kein Planstand | „Noch kein Planstand festgehalten." |
| Keine Abweichungen | „Keine Abweichungen zum aktuellen Plan." |
| Keine Milestones | „Noch keine Milestones geplant." |

Neu zu ergänzen (P19.5): „Noch keine Meilensteine für diese Phase." (phasenscoped, siehe §14).
Keine technischen Null-/Array-Darstellungen gefunden.

---

## 19. End-to-End User Journey

Durchlauf des im Auftrag (Abschnitt 25) beschriebenen 17-Schritte-Flows gegen den aktuellen
Code:

| # | Schritt | Heutiger Zustand |
|---|---|---|
| 1–5 | Projekt öffnen, Phase anlegen, Tags setzen, Kapazität ergänzen | glatt, CONFIRMED |
| 6 | Kommentar „Kunde liefert Mapping Freitag" | glatt (Kommentarliste im Aktivität-Tab) |
| 7–8 | Blocker aus Kommentar erstellen, Tags übernehmen/vorschlagen | **Reibung:** nur über Activity-Feed erreichbar, Phasen-Tags fehlen im Vorschlag (§11) |
| 9 | Dokument hochladen | glatt, aber im Dateien-Tab funktional schwächer als Projekt-Dokumente-Tab (§13) |
| 10 | Milestone zuordnen | **Reibung:** Nutzer muss den Drawer verlassen, Workspace zeigt keine Phasen-Milestones (§14) |
| 11–12 | Unterphase erstellen, Parent-Workspace prüfen | glatt, CONFIRMED |
| 13–15 | Planstand festhalten, Phase verändern, Planstand vergleichen | glatt auf Projektebene, aber **kein phasenscoped Vergleich im Workspace** (§15) |
| 16 | Tag klicken → Dossier | glatt, aber Dossier-Items nicht klickbar (§10) |
| 17 | Gantt öffnen → dieselbe Phase/derselbe Tree | glatt, CONFIRMED |

Der Flow ist **an drei Stellen** spürbar reibungsbehaftet (7–8, 10, 13–15) — genau die drei
Bereiche, die P19.3/P19.5/P19.6 adressieren. Kein Schritt erfordert heute Kenntnis von
`ResourceDemand`, `BaselineSnapshot` oder `parent_phase_id` als Begriff — das im Auftrag
Abschnitt 31 formulierte Abschlusskriterium ist damit für 14 von 17 Schritten bereits erfüllt.

---

## 20. Identified Gaps

Konsolidiert aus §3/§4 (Kurzform, Priorität = Auswirkung auf den End-to-End-Flow):

1. **Kommentar-Threading/Replies fehlt im Frontend** (Backend bereit) — mittel.
2. **Keine Meilensteine-Ansicht im PlanPhase-Workspace** — mittel.
3. **Kein phasenscoped Planstand-Vergleich** — mittel.
4. **„Aus Kommentar erstellen" nur im Activity-Feed, nicht in der Kommentarliste** — klein.
5. **Tag-Vorschlag bei Folgeobjekten ignoriert Phasen-Tags** — klein.
6. **Dateien-Tab im Workspace schwächer als zentrale Dokumentenablage** — klein.
7. **Keine Tag-Nachbearbeitung bei Task/Blocker/Decision** — klein.
8. **Tag-Dossier-Items nicht klickbar** — klein.
9. **Nur 1-Ebenen-Breadcrumb statt voller Ahnenkette** — klein.
10. **Activity-Feed (Frontend) zeigt Milestones/Planänderungen nicht, obwohl Backend sie liefert** — klein.
11. **N+1-Calls bei Rollenaufschlüsselung, Assignment-Summary nicht in Detail eingebettet** — klein, Performance.
12. **Legacy Subproject/ResourceDemandGrid optisch gleichrangig mit neuer PlanPhase-Struktur** — mittel, rein visuell.
13. **Derived-Capacity-Drilldown-UI nicht verifiziert** — offen, Verifikationsaufgabe.
14. **Veralteter Backend-Kommentar zu Milestone/`plan_phase_id`** — trivial, Code-Hygiene.

Keine der 14 Lücken erfordert ein neues Datenmodell, eine neue Capacity-Engine, eine zweite
Resource-Planning-Quelle oder ein neues Subproject-Konzept — die Leitplanken aus dem Auftrag
sind eingehalten.

---

## 21. Backend/API Changes

Ausschließlich additive Erweiterungen bestehender Endpoints/Response-Shapes, keine neuen
Tabellen, keine neuen Router:

- `PlanPhaseDetail` (`planning.py`, `_plan_phase_detail`): additiv um `milestones` (gefiltert
  auf `plan_phase_id`) und optional die Assignment-Summary erweitern — reduziert Round-Trips
  (Gap 2, 11).
- `assignment-summary`/`resource_demands`-Antwort: pro Demand die zugehörigen Assignments
  direkt mitliefern, um das N+1-Muster im Frontend aufzulösen (Gap 11).
- `comments`-Schema (`CommentOut`/`CommentCreate`): additiv `parent_id` in Request/Response
  aufnehmen (Feld existiert bereits im Modell) — kein Migrations-Bedarf (Gap 1).
- Backend-Kommentar in `communication.py` zu Milestone/`plan_phase_id` korrigieren (Gap 14).
- Optional, nur falls clientseitiges Filtern performant nicht ausreicht: `plan_phase_id`-Query-
  Parameter auf `GET /baselines/{id}/deviations` (Gap 3) — **erst nach Frontend-Versuch mit
  clientseitigem Filter bewerten**, da CONCEPT/Auftrag explizit "keine neue komplexe Snapshot
  Engine" fordern und die Datenmenge pro Projekt überschaubar ist.

Keine Änderung an `entity_relations`, `tag_links`, `document_links`, `baseline_entries`,
`resource_demands`/`resource_assignments` als Tabellen.

---

## 22. Frontend Changes

- `NotesSection.tsx`: Reply-UI (Antwort-Button, Einrückung, `parent_id`-Anzeige), „Aus
  Kommentar erstellen"-Aktionen direkt integrieren (bestehende Logik aus `ActivityFeed.tsx`
  extrahieren in einen gemeinsamen Hook/Helper statt Duplikation).
- `ActivityFeed.tsx`: `PHASE_ACTIVITY_TYPES` um `milestone`/`baseline_snapshot` erweitern; Tag-
  Vorschlag um Phasen-Tags ergänzen (Prop `phaseTags` durchreichen).
- `PlanPhaseWorkspace.tsx`: neue kompakte Meilensteine-Karte (Aktivität-Tab, gefiltert
  `MilestoneList`-Wiederverwendung), neue „Seit Planstand …"-Zeile (Übersicht-Tab, clientseitig
  gefilterter Deviation-Aufruf), voller Breadcrumb-Pfad statt Einzeiler.
- Dateien-Tab: `ProjectDocumentsTab`-Darstellungslogik extrahieren/parametrisieren
  (`entityFilter`-Prop) und im Workspace wiederverwenden statt der eigenen `<ul>`-Liste.
- `TaskList.tsx`/`BlockerList.tsx`/`DecisionList.tsx`: Tag-Nachbearbeitung nach Muster von
  `MilestoneList.tsx` ergänzen.
- `TagDossierPanel.tsx`: „Aktuelle Lage"-Items klickbar machen (Navigation/Öffnen der
  referenzierten Entität bzw. des zugehörigen PlanPhase-Workspace).
- `PlanPhaseCapacityTab.tsx`: visuelle Überarbeitung (nicht funktional) zur klareren Trennung
  Direct-Assignment vs. optionale Rollenaufschlüsselung; Nutzung der gebündelten
  Backend-Antwort statt Einzel-Calls.
- `ProjectPlanningTab.tsx`: Legacy-Block (Subproject-CRUD + `ResourceDemandGrid`) in eine
  eingeklappte, klar beschriftete Sektion verschieben (reine Darstellungsänderung).

---

## 23. CONCEPT.md Changes

Nach Umsetzung von P19.1–P19.7 sind folgende CONCEPT.md-Ergänzungen fällig (nicht jetzt, da
NOCH NICHT IMPLEMENTIERT):

- §5.5 (Milestones): Ergänzung, dass der PlanPhase-Workspace eine phasenscoped
  Milestone-Kompaktkarte zeigt.
- §8 (Collaboration): Ergänzung um Kommentar-Threading-UX (bisher nur Backend-Feld
  dokumentiert) und die vereinheitlichte „Aus Objekt erstellen"-Erreichbarkeit.
- §5.3/§10: Ergänzung um die phasenscoped Planstand-Kurzanzeige im Übersicht-Tab.
- §10 (Planung-Tab): Ergänzung, dass Legacy-Subproject/ResourceDemandGrid ab P19 optisch
  separiert dargestellt werden (rein UX, keine Änderung an §6.15/§16.15-17-Aussagen zum
  IST-Datenmodell).
- Neuer Umsetzungsstand-Abschnitt „16.18 P19 Workspace UX Consolidation" nach Abschluss der
  Implementierung, analog zu 16.15–16.17.

Alle Änderungen sind additiv zu bestehenden Abschnitten, keine Umschreibung der
Architektur-Abschnitte 5/6.

---

## 24. Implementation Packages P19.1–P19.8

### P19.1 — Workspace Information Architecture
**Ziel:** Übersicht-Tab und Tree-Navigation abrunden (Breadcrumb), Struktur bestätigen.
**Scope:** Voller Breadcrumb-Pfad im Drawer-Header; Collapse-State-Konsistenz zwischen Liste
und Gantt (optional, geteilter Hook).
**Out of Scope:** neue Tabs, neue Felder.
**Backend:** keine.
**API:** keine.
**Frontend:** `PlanPhaseWorkspace.tsx` Header, ggf. gemeinsamer Collapse-Hook für
`PlanPhaseList`/`PlanPhaseGantt`.
**Datenmodell:** keins.
**Tests:** Snapshot-Test Breadcrumb bei Ebene 1/2/3.
**Dependencies:** keine.
**Risks:** minimal.
**Acceptance:** Breadcrumb zeigt volle Ahnenkette bis Wurzel auf allen drei Ebenen.
**DoD:** Manuell verifiziert an einer 3-Ebenen-Testphase.

### P19.2 — Capacity & Direct Assignment UX Polish
**Ziel:** Visuelle Klarheit Direct-Assignment vs. Rollenaufschlüsselung, Round-Trip-Reduktion.
**Scope:** `assignment-summary`/`resource_demands` bündeln, Frontend auf gebündelte Antwort
umstellen, visuelle Überarbeitung der Kapazität-Tab-Hierarchie.
**Out of Scope:** neue Capacity-Formeln, neue Rollen-Logik.
**Backend:** `planning.py` — `resource_demands`-Serialisierung um Assignments erweitern.
**API:** additive Felder auf bestehenden Schemas (`PlanPhaseDetail`/`ResourceDemandOut`).
**Frontend:** `PlanPhaseCapacityTab.tsx`.
**Datenmodell:** keins.
**Tests:** Backend-Schema-Test (additive Felder), Frontend: kein N+1 mehr bei aufgeklappter
Rollenansicht (Netzwerk-Call-Zähler im Test).
**Dependencies:** keine.
**Risks:** Response-Größe leicht erhöht bei vielen Rollen — vernachlässigbar.
**Acceptance:** Kapazität-Tab lädt mit ≤2 Calls (Detail + ggf. Candidates), unabhängig von
Rollenanzahl.
**DoD:** Performance-Vergleich vor/nach dokumentiert.

### P19.3 — Activity / Comments / Follow-up Objects
**Ziel:** Threading, vereinheitlichte Folgeobjekt-Erstellung, vollständiger Activity-Feed.
**Scope:** Reply-UI in `NotesSection.tsx`; `parent_id` in Comment-Schemas; „Aus Kommentar
erstellen" auch aus der Kommentarliste; Phasen-Tags in Vorschlag; Frontend-Typliste um
Milestone/Baseline erweitern; Backend-Kommentar-Fix.
**Out of Scope:** neue Activity-Tabelle, neuer Relation-Typ.
**Backend:** `schemas.py` (Comment-Schemas additiv), `communication.py` (Kommentar-Fix).
**API:** additives Feld `parent_id` auf `CommentOut`/`CommentCreate`.
**Frontend:** `NotesSection.tsx`, `ActivityFeed.tsx`, gemeinsamer „Follow-up erstellen"-Helper.
**Datenmodell:** keins (Feld existiert bereits).
**Tests:** Backend: Comment-Create/List mit `parent_id` (Regressionstest bestehender Suite
erweitern); Frontend: Reply rendert eingerückt, Folgeobjekt aus Kommentarliste erzeugt
korrekte `EntityRelation`.
**Dependencies:** keine.
**Risks:** Thread-Tiefe unbegrenzt — UI sollte optisch auf 1 Ebene Verschachtelung begrenzen
(wie bei den meisten Kommentarsystemen), das ist eine reine Darstellungsentscheidung.
**Acceptance:** Journey-Schritte 6–8 aus §19 ohne Tab-Wechsel durchführbar.
**DoD:** End-to-End manuell getestet (Kommentar → Reply → Blocker mit vorgeschlagenen
Phasen+Kommentar-Tags).

### P19.4 — Tags / Knowledge Integration
**Ziel:** Konsistente Tag-Nachbearbeitung, klickbares Dossier, „Verknüpfte Themen"-Sektion.
**Scope:** Tag-Edit-UI bei Task/Blocker/Decision; `TagDossierPanel`-Items klickbar; kompakte
„Verknüpfte Themen"-Karte im Übersicht-Tab aus `knowledge/context`.
**Out of Scope:** Tag-Merge, Vector-Search, neue Knowledge-Endpoints.
**Backend:** keine (bestehender `knowledge/context`-Endpoint reicht).
**API:** keine.
**Frontend:** `TaskList.tsx`/`BlockerList.tsx`/`DecisionList.tsx`, `TagDossierPanel.tsx`,
`PlanPhaseWorkspace.tsx` (neue Karte).
**Datenmodell:** keins.
**Tests:** Frontend-Komponententests für Tag-Edit-Affordanz; Klick auf Dossier-Item navigiert
korrekt.
**Dependencies:** keine.
**Risks:** minimal.
**Acceptance:** Journey-Schritt 16 (Tag klicken → Dossier → Entität öffnen) vollständig
möglich.
**DoD:** Manuell verifiziert.

### P19.5 — Documents / Milestones Integration
**Ziel:** Workspace-Dateien-Tab auf volle Funktionalität heben; Milestones im Workspace
sichtbar machen.
**Scope:** Dateien-Tab durch parametrisierte `ProjectDocumentsTab`-Logik ersetzen; neue
Meilensteine-Kompaktkarte (Leaf + Parent) mit Wiederverwendung von `MilestoneList.tsx`.
**Out of Scope:** neues Attachment-System, neue Milestone-Engine.
**Backend:** keine (ggf. `PlanPhaseDetail` um `milestones`-Liste erweitern, siehe P19.6-Overlap
— gehört inhaltlich hierher, technisch identischer Endpoint-Change wie in P19.6 gelistet).
**API:** additives Feld `milestones` auf `PlanPhaseDetail`.
**Frontend:** `PlanPhaseWorkspace.tsx` Dateien-Tab, neue Meilensteine-Karte, Extraktion einer
parametrisierbaren Dokumentenlisten-Komponente aus `ProjectDocumentsTab.tsx`.
**Datenmodell:** keins.
**Tests:** Dateien-Tab zeigt Tags/Suche/Backlinks identisch zum Projekt-Dokumente-Tab;
Meilensteine-Karte zeigt korrekt gefilterte Liste, Empty State bei 0 Einträgen.
**Dependencies:** keine.
**Risks:** Wiederverwendungs-Refactor von `ProjectDocumentsTab.tsx` muss bestehende
Projekt-Ansicht unverändert lassen (Regressionsgefahr) — durch Parametrisierung statt Kopie
mindern.
**Acceptance:** Journey-Schritte 9–10 aus §19 ohne Tab-Verlassen möglich.
**DoD:** Manuell verifiziert, bestehende Dokumente-Tab-Tests weiterhin grün.

### P19.6 — Planstand UX Enhancement
**Ziel:** Phasenscoped Planstand-Sichtbarkeit im Workspace.
**Scope:** „Seit Planstand VX geändert"-Zeile im Übersicht-Tab, clientseitig gefiltert aus dem
bestehenden Deviation-Endpoint (Filter auf `entity_id` der Phase + bekannte Nachfahren-IDs bei
Parent-Phasen).
**Out of Scope:** Snapshot-vs-Snapshot-Vergleich (bleibt deferred), neue Diff-Engine.
**Backend:** keine im Regelfall; optionaler `plan_phase_id`-Query-Parameter auf
`/baselines/{id}/deviations` nur falls clientseitiges Filtern sich als unzureichend erweist
(Performance-Test in P19.6 einplanen, Entscheidung danach treffen).
**API:** optional additiv, s.o.
**Frontend:** `PlanPhaseWorkspace.tsx` (neue Zeile/Card), Wiederverwendung der
`FIELD_LABELS`/Deviation-Rendering-Logik aus `BaselineList.tsx` (extrahieren, nicht
duplizieren).
**Datenmodell:** keins.
**Tests:** Frontend: korrekte Filterung bei Leaf und bei Parent (inkl. Nachfahren); Backend
(falls Query-Param ergänzt): Filterung liefert Teilmenge korrekt.
**Dependencies:** keine.
**Risks:** Performance bei sehr vielen Planständen/Phasen — durch den optionalen
Backend-Parameter (s.o.) mitigierbar, erst bei Bedarf umsetzen.
**Acceptance:** Journey-Schritt 15 aus §19 direkt im Workspace möglich, ohne zur Projektebene
zu wechseln.
**DoD:** Manuell verifiziert mit mind. zwei Planständen.

### P19.7 — Project Planning Tab Cleanup
**Ziel:** Visuelle Priorisierung neue PlanPhase-Struktur vs. Legacy; Derived-Capacity-Drilldown
verifizieren/ergänzen.
**Scope:** Legacy-Block (Subproject-CRUD + `ResourceDemandGrid`) in eingeklappte,
klar beschriftete Sektion verschieben; Derived-Capacity-UI im Planning-Tab bzw. Cockpit
verifizieren und ggf. um Monats-Drilldown ergänzen (nur Darstellung, Backend bereits
CONFIRMED).
**Out of Scope:** Entfernen der Legacy-Komponenten (B-8-Scope), neue Aggregationslogik.
**Backend:** keine.
**API:** keine.
**Frontend:** `ProjectPlanningTab.tsx` (Umstrukturierung, keine Funktionsänderung an
Legacy-Teilen), ggf. neue Drilldown-Darstellung für Derived Capacity.
**Datenmodell:** keins.
**Tests:** Legacy-Funktionen (Subproject anlegen/löschen, ResourceDemandGrid editieren)
funktional unverändert nach Umstrukturierung (Regressionstest).
**Dependencies:** keine.
**Risks:** Legacy-Nutzer (unmigrierte Projekte) dürfen keine Funktionalität verlieren — daher
nur Sichtbarkeit ändern, nie Verhalten.
**Acceptance:** Neue PlanPhase-Struktur ist visuell primär, Legacy klar als „Migration
ausstehend" erkennbar, aber weiterhin voll funktionsfähig.
**DoD:** Manuell verifiziert an einem unmigrierten Test-Projekt (falls vorhanden) oder Dry-Run-
Fixture.

### P19.8 — End-to-End UX Regression + CONCEPT
**Ziel:** Vollständiger Journey-Test (§19/Auftrag Abschnitt 25), CONCEPT.md-Nachpflege.
**Scope:** Alle 17 Journey-Schritte end-to-end manuell durchspielen nach P19.1–7; CONCEPT.md
um die in §23 gelisteten Ergänzungen erweitern (neuer Abschnitt „16.18").
**Out of Scope:** neue Features.
**Backend:** keine.
**API:** keine.
**Frontend:** keine (nur Verifikation).
**Datenmodell:** keins.
**Tests:** vollständiger manueller Journey-Durchlauf, bestehende automatisierte Test-Skripte
(`backend/scripts/test_*.py`) weiterhin grün.
**Dependencies:** P19.1–P19.7 abgeschlossen.
**Risks:** minimal, falls vorherige Pakete sauber abgeschlossen.
**Acceptance:** alle 17 Schritte aus §19 ohne technischen Begriff (`ResourceDemand`,
`BaselineSnapshot`, `parent_phase_id`) im UI-Text durchführbar.
**DoD:** CONCEPT.md aktualisiert, committed; Journey-Protokoll im PR/Report dokumentiert.

---

## 25. Dependency Graph

```
P19.1 (Workspace IA/Breadcrumb) ─┐
                                  ├─→ P19.8 (E2E Regression + CONCEPT)
P19.2 (Capacity Polish) ──────────┤
                                  │
P19.3 (Activity/Comments) ───────┤
                                  │
P19.4 (Tags/Knowledge) ───────────┤
                                  │
P19.5 (Documents/Milestones) ────┤   (P19.5 liefert `milestones`-Feld,
                                  │    das P19.6 optional mitnutzt — leichte
P19.6 (Planstand) ────────────────┤    Reihenfolge-Präferenz: P19.5 vor P19.6,
                                  │    kein harter Blocker)
P19.7 (Planning Tab Cleanup) ─────┘
```

Alle Pakete P19.1–P19.7 sind gegenseitig unabhängig und parallelisierbar (unterschiedliche
Dateien/Komponenten, keine gemeinsamen Schema-Änderungen außer der additiven
`PlanPhaseDetail`-Erweiterung, die P19.2/P19.5/P19.6 alle additiv und konfliktfrei erweitern
können, sofern jedes Paket sein eigenes Feld hinzufügt statt bestehende zu überschreiben).
P19.8 ist der einzige echte Nachfolger und setzt den Abschluss aller anderen voraus.

---

## 26. Parallel Agent Plan

Empfohlene Aufteilung für eine parallele Umsetzung (nach Freigabe dieses Plans):

| Agent | Pakete | Begründung |
|---|---|---|
| Agent A | P19.1 + P19.2 | beide isoliert in `PlanPhaseWorkspace.tsx`/`PlanPhaseCapacityTab.tsx`, gleicher Erfahrungsbereich (Kapazität/Übersicht) |
| Agent B | P19.3 + P19.4 | beide in Collaboration-Komponenten (`NotesSection`, `ActivityFeed`, Tag-Komponenten), thematisch zusammenhängend |
| Agent C | P19.5 + P19.6 | beide erweitern `PlanPhaseDetail` additiv (Milestones/Planstand-Filter), sinnvoll in einer Hand, um Schema-Konflikte zu vermeiden |
| Agent D | P19.7 | isoliert in `ProjectPlanningTab.tsx`, unabhängig von den Workspace-Änderungen |

P19.8 läuft **sequentiell nach** Abschluss aller vier Agenten (Merge-Punkt, End-to-End-Test,
CONCEPT.md-Update) — nicht parallelisierbar, da er auf dem Endergebnis aller anderen aufbaut.

---

## 27. Test Strategy

- **Backend:** bestehende `backend/scripts/test_*.py`-Suite (u. a.
  `test_milestone_and_baseline_tree.py`) um Szenarien für additive Felder erweitern
  (`parent_id` auf Comments, `milestones` auf `PlanPhaseDetail`, gebündelte
  `resource_demands`-Assignments). Keine neue Test-Infrastruktur, gleiche Runner wie P18.
- **Frontend:** vorhandene Komponententests (falls vorhanden) um die neuen
  UI-Elemente ergänzen (Reply-Button, Meilensteine-Karte, Planstand-Zeile, Breadcrumb).
  Schwerpunkt auf manuellen End-to-End-Durchläufen (P19.8), da UI-Polish-Änderungen dieser Art
  sich am zuverlässigsten durch den vollständigen Journey-Test verifizieren lassen.
- **Regression:** Legacy-Funktionalität (Subproject/ResourceDemandGrid) nach P19.7 explizit
  gegentesten — reine Darstellungsänderung darf keine Funktion brechen.
- **Kein Lasttest/Performance-Suite nötig** — Änderungsumfang ist additiv und klein genug für
  manuelle Verifikation, außer der in P19.2 empfohlenen Vorher-/Nachher-Call-Zählung.

---

## 28. Remaining Business Decisions

Der Auftrag verlangt hier ausdrücklich **nur echte fachliche Entscheidungen** — nach diesem
Audit sind keine offenen Architektur- oder Datenmodell-Fragen mehr vorhanden (BD-1–BD-13 sind
bereits in CONCEPT.md §14 geschlossen bzw. bewusst als offen/deferred dokumentiert, unverändert
durch P19). Die folgenden zwei Punkte sind **UX-Platzierungsentscheidungen**, die dieses
Dokument bereits mit einer begründeten Empfehlung beantwortet (§5/§15) — sie werden hier nur
zur expliziten Bestätigung aufgeführt, sind aber **kein Blocker** für den Start der
Implementierung:

1. **Planstände: eigener Bereich im Workspace vs. zentral auf Projektebene** (Auftrag
   Abschnitt 3) — Empfehlung dieses Dokuments: **B, zentral** (`BaselineList.tsx` bleibt
   Projektebene), ergänzt um eine phasenscoped Kurzanzeige im Workspace (P19.6). Reversibel,
   falls anders gewünscht.
2. **Milestones: eigener Tab vs. kompakte Karte im Workspace** (Auftrag Abschnitt 18) —
   Empfehlung: **kompakte Karte im Aktivität-Tab**, kein 5. Tab (P19.5). Reversibel.

Keine dieser beiden Empfehlungen erfordert eine Rückfrage vor Implementierungsbeginn — beide
sind rein additiv und ohne Datenverlust umkehrbar, falls der Product Owner nach Sichtung eine
andere Platzierung bevorzugt.

---

## 29. Implementation Readiness

- Keine offene Architekturfrage (P18/BD-1–BD-13 bleiben unverändert geschlossen bzw. bewusst
  deferred).
- Keine neue Tabelle, keine neue Capacity-Engine, keine zweite Resource-Planning-Quelle, kein
  neues Subproject-Konzept identifiziert oder vorgeschlagen.
- Alle 14 identifizierten Gaps (§20) sind additiv, klein bis mittel im Umfang, unabhängig
  parallelisierbar (§25/§26), und mit bestehender Infrastruktur lösbar
  (`EntityRelation`, `TagLink`, `DocumentLink`, `plan_phase_id`, `BaselineEntry`, `Activity`,
  `ResourceDemand`/`ResourceAssignment` — keine dieser Kernstrukturen muss erweitert werden,
  außer additive, rückwärtskompatible Felder).
- Die zwei verbleibenden Punkte in §28 sind UX-Empfehlungen mit klarer Begründung, kein
  Business-Blocker.
- Legacy-Pfad (ResourceDemandGrid/Subproject) bleibt unverändert funktional bestehen bis B-8 —
  P19 rührt nicht an dessen Datenmodell oder Funktion, nur an dessen visueller Prominenz.

**READY FOR P19 IMPLEMENTATION**
