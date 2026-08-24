# Kapazitätsplaner im plx.crew Portal — Konzept

**Version:** v0.23 (P18 Finalization — CONCEPT.md als Rebuild-Spezifikation bereinigt,
realistischer Migrations-Dry-Run bewertet, B-8 weiterhin BLOCKED — siehe Abschnitt 16.17)
**Stand:** Alle in Abschnitt 16 gelisteten Phasen bis P17 sind umgesetzt. **P18 ist fachlich/
dokumentarisch abgeschlossen bis auf den produktiven Cutover (B-8).** Die P18-Zielarchitektur
(`PlanPhase`-only, Abschnitt 6) ist **fachlich final gelockt und gegen Code CONFIRMED
implementiert** (B-1–B-7, Details Abschnitt 16.7–16.17) und in acht Umsetzungspaketen
realisiert:

```
B-1 Hierarchy Domain Foundation ............ IMPLEMENTED (16.7)
B-2 Migration Tooling ....................... IMPLEMENTED, Dry-Run-Tooling verifiziert,
                                               produktive Ausführung noch nicht erfolgt (16.8/16.17)
B-3 Phase Tree API ........................... IMPLEMENTED (16.9)
B-4 Capacity/Assignment Simplification ....... IMPLEMENTED (16.10)
B-5 Derived Monthly & Portfolio Capacity ..... IMPLEMENTED (16.11)
B-6 PlanPhase Tree UX ......................... IMPLEMENTED (16.12)
B-7 Gantt/Milestone/Planstand Integration .... IMPLEMENTED (16.13)
B-8 Legacy Cutover ............................ CUTOVER BLOCKED — nur noch wegen des
                                               externen Migrations-Dry-Run-Schritts (16.16/16.17)
```

**B-1 bis B-7 sind gegen den realen Code geprüft (nicht nur laut Selbstauskunft dieses
Dokuments) und CONFIRMED**, mit einer kleinen Zahl dokumentierter, nicht B-8-relevanter
Einzel-Gaps (Abschnitt 16.15/16.16). Produktcode und Frontend wurden für P18 geändert. **Die
produktive Legacy-Migration (B-2 gegen echte Produktivdaten) wurde weiterhin nicht
ausgeführt** — bestehende, unmigrierte Projekte laufen bis dahin unverändert über
`ResourceDemandGrid`/`Subproject` (Legacy-Compat-Pfad, kurz zusammengefasst in Abschnitt
6.15, volles Detail in Abschnitt 17.8). Neue Kapazitätsberechnungen (Abschnitt 6) sind
produktiv scharf und lesen ausschließlich noch den `PlanPhase`-Baum — die früher dokumentierte
Doppelzählungs-Lücke (Historie: Abschnitt 17.8) ist für die fünf zentralen Portfolio-/
Cockpit-/GAP-Endpunkte **strukturell aufgelöst** und **kein aktiver Blocker mehr**, bleibt aber
technisch relevant, solange `plan_phase_id = NULL`-Zeilen nicht migriert sind. **B-8
(`ResourceDemandGrid`/Subproject-UI entfernen) bleibt BLOCKIERT — ausschließlich wegen des
noch ausstehenden realistischen Migrations-Dry-Runs gegen echte Produktivdaten** (externe
Vorbedingung, Abschnitt 16.17), nicht mehr wegen offener Code-Defekte.
**Führende Modelle (aktuelle Source of Truth):** `PlanPhase`, `Milestone`,
`BaselineSnapshot`/`BaselineEntry`, `ResourceDemand`/`ResourceAssignment`, `Person` +
`ResourceProfile`. Die ursprünglichen Excel-abgeleiteten Parallelmodelle (`GanttPhase`/
`ProjectGanttPhase`, `FtePlan`/`ProjectFtePlan`, `TeamMember`, `Assignment`) sind seit Phase
26.9 **entfernt** (mit Datenkonvertierung, nicht Drop-and-Pray — siehe Abschnitt 17.3).
**Ablösung von:** Excel/VBA-Kapazitätsplaner (`PowerPointGenerator`, siehe [`legacy/`](legacy/))
**Ziel-Umgebung:** Integration als Kachel im BUILD-Bereich des plx.crew Portals (`crew-portal.pure-lox.com`)

---

## Wie dieses Dokument zu lesen ist

Dieses Dokument ist nach einem Konsolidierungsdurchgang (P11) grundlegend neu strukturiert,
weil es durch fortlaufendes Anhängen (17 Umsetzungsschritte + 27 weitere Phasen) intern
widersprüchlich geworden war: frühe Abschnitte beschrieben noch die ursprüngliche
Excel-1:1-Architektur, obwohl spätere Phasen sie bereits ersetzt hatten.

**Abschnitte 1–14 beschreiben den aktuellen Zielzustand** — das, was heute gilt, unabhängig
davon, wann es eingeführt wurde. Bei Widersprüchen zwischen diesen Abschnitten und Code:
Code hat Vorrang, aber meldet es als Doku-Bug.

**Abschnitt 14 (Offene Business Decisions)** und **Abschnitt 16 (Umsetzungsstand)** sind das
Bindeglied zwischen Ist und Soll.

**Abschnitt 6 (Kapazitätsplanung) beschreibt ab diesem Cleanup-Durchgang (P18 Finalization,
Abschnitt 16.17) ausschließlich die aktuelle, final gelockte `PlanPhase`-only-Architektur** —
es gibt im Hauptteil des Dokuments (Abschnitte 1–14) keine zwei konkurrierenden
Kapazitätsabschnitte mehr. Der frühere, nie implementierte Pass-1-Entwurf (Grob-/Feinplanung,
`max(Grob, Fein)`-Reconciliation) und die vollständige Beschreibung des noch aktiven, aber
abzulösenden Zwei-Achsen-Legacy-Pfads (`ResourceDemandGrid`/`Subproject`) wurden **ohne
Kürzung** in den Historie-/Compat-Bereich verschoben:

- **Abschnitt 17.7** — P18 Pass 1 (superseded Grob-/Feinplanung-Design, nie implementiert).
- **Abschnitt 17.8** — aktiver Legacy-Compat-Pfad (`ResourceDemand.plan_phase_id = NULL`,
  `ResourceDemandGrid`, `Subproject`), technisch weiterhin scharf für unmigrierte Alt-Projekte
  bis B-8, aber **keine Zielarchitektur**. Abschnitt 6.15 fasst den aktuellen Compat-Stand kurz
  zusammen und verweist dorthin für das volle Detail.

**Historische Entscheidungen sind niemals eine aktuelle Implementierungsanweisung** — auch
Abschnitt 17.8 beschreibt zwar einen technisch noch **aktiven** Codepfad, ist aber fachlich
nicht die Zielarchitektur und wird mit dem produktiven B-8-Cutover entfernt (Abschnitt 16.17).

**Abschnitt 17 (Historie)** enthält alles, was fachlich überholt, aber historisch
dokumentationswürdig ist — insbesondere die ursprüngliche Excel-Herkunft, den Legacy Cutover
und die beiden oben genannten P18-Kapitel. Aussagen aus Abschnitt 17 sind **niemals** aktuelle
Anforderungen, auch wenn sie technisch klingen.

Ein KI-Agent, der nur Abschnitte 1–14 liest, sollte die aktuelle Architektur vollständig und
widerspruchsfrei verstehen, ohne Abschnitt 17 gelesen zu haben.

---

## 1. Produktziel

Der Kapazitätsplaner ist ein Web-Tool für Projektplanung, Beraterkapazität und
Projektsteuerung im plx.crew Portal. Er entstand als Ablösung eines Excel/VBA-Tools, das
Gantt-Phasen und FTE-Planung pro Projekt abbildete und nach PPTX exportierte — das reichte
für die Präsentation, aber:

- keine Mehrbenutzer-Fähigkeit (eine `.xlsm`-Datei, Windows-only)
- kein Abgleich mit der Realität — reine Planung, kein Ist
- keine Team-/Auslastungssicht über alle Projekte hinweg

**Excel ist die Herkunft dieses Produkts, nicht sein heutiges UX-Vorbild.** Frühe
Formulierungen wie "Planungslogik 1:1 aus dem Excel übernehmen" beschrieben den
Migrations-MVP (Schritt 1, siehe Abschnitt 17.1) und sind seit dem Legacy Cutover (Phase
26.9) überholt — die heutige Planung ist tagegenaue `PlanPhase`/`Milestone`-Planung, kein
Monats-/Phasencode-Raster mehr (siehe Abschnitt 5).

Das Tool liefert heute zusätzlich:

1. **Ist-Daten aus Jira/Tempo** (Worklogs)
2. **Personen-/Teamstammdaten** mit Kapazität
3. **Soll-Ist-Gap-Analyse** über mehrere GAP-Dimensionen (Abschnitt 9)
4. **Projektsteuerung/Health** (Ampeln je Steuerungsdimension)
5. **Zusammenarbeit & Knowledge Layer** (Kommentare, Tasks, Blocker, Decisions, Tags,
   Relations, Volltextsuche)

---

## 2. Fachlicher Scope

- Projektplanung (PlanPhase-Baum, Milestone, Planstände, Gantt-Visualisierung; Teilprojekte
  nur noch Legacy/Compat bis B-8, siehe Abschnitt 5.4)
- Beraterkapazität (Plan-FTE, ResourceDemand/-Assignment, Available Capacity)
- Projektsteuerung (Health, GAP Engine, Cockpit)
- Tempo-Ist (Jira-Worklogs, projektweit; Phasenebene deferred, siehe BD-1)
- Zusammenarbeit (Kommentare inkl. Threading, Tasks, Blocker, Decisions, Risks, Meeting
  Minutes, Dokumente)
- Knowledge Layer (Tags, TagCategories, EntityRelations, Volltextsuche, Wissenskarten)
- Controlling (portfolioweite Aggregation über alle GAP-/Health-/Kapazitätsdimensionen)
- Administration (Personen, Teams, Rollen/Permissions, Ressourcenrollen/Skills, Tags,
  Health-Schwellen, Kapazitätskalender)

**Explizit außerhalb des Scopes: FTE-Planung für Development, Sales, Marketing oder andere
Abteilungen außerhalb des Beraterteams.** Die Kapazitätsplanung (`ResourceDemand`/
`ResourceAssignment`, `ResourceProfile`) gilt ausschließlich für das eigene Projekt-/
Beraterteam. Andere Beteiligte (Kunde, Entwicklung, Drittparteien) kommen im Tool als
Stakeholder-/Dependency-/Blocker-/Task-/Decision-/Kommentar-Kontext vor (z. B.
`Blocker.caused_by_party = CUSTOMER`), nie als planbare FTE-Ressource. `ResourceRole` ist
zwar technisch freies Vokabular (siehe Abschnitt 6), es werden aber bewusst keine
projektfremden Rollen (Development, Sales, …) angelegt.

---

## 3. Fachliche Kernprinzipien

Diese Sätze sind die Kurzfassung von Abschnitt 5/6 — bei jeder Änderung an Planung/Kapazität
gegen diese Liste prüfen. **Diese Liste beschreibt ausschließlich die aktuelle, einzige
gültige Architektur** (P18 Pass 2, final gelockt seit 16.6, gegen realen Code CONFIRMED seit
16.7–16.13/16.17) — für neu angelegte `PlanPhase`-Bäume ist dies das tatsächliche
IST-Verhalten, nicht mehr nur Zielarchitektur. Für **bestehende, noch nicht per
B-2-Migration überführte** Projektdaten gilt technisch weiterhin der ältere
Zwei-Achsen-Legacy-Pfad (`ResourceDemand.plan_phase_id = NULL`, `ResourceDemandGrid`,
Abschnitt L6.1 (Historie 17.8)) — dieser Pfad bleibt aktiv, aber **kein Bestandteil dieser
Liste**, bis B-8 abgeschlossen ist (Abschnitt 16.16/16.17). Der frühere, nie implementierte
Pass-1-Entwurf ("Grobplanung/Feinplanung sind zwei Konkretisierungsgrade,
`max()`-Reconciliation") ist vollständig als Historie in Abschnitt 17.7 erhalten
(**superseded**, nicht mehr gültig) — keiner der unten stehenden Grundsätze verweist mehr
darauf.

- **`PlanPhase` ist die Planungseinheit.** Sie wird **tagegenau** geplant (Start/Ende als
  Datum), nicht als Monats-/Phasencode-Zelle.
- **"Aktueller Plan" = `PlanPhase.forecast_start`/`forecast_end` intern.** In der normalen UI
  heißen diese Felder schlicht "Start"/"Ende". "Forecast" ist ein technischer Begriff, der im
  normalen Planungsworkflow nicht prominent sichtbar ist.
- **Planstand = `BaselineSnapshot`.** Ein Planstand ist ein benannter, eingefrorener
  historischer Stand des damaligen Plans — keine kontinuierlich editierbaren
  `baseline_start`/`baseline_end`-Felder im Tagesgeschäft. Die Baseline-Felder auf
  `PlanPhase`/`Milestone` existieren aus Kompatibilitätsgründen weiter, bestimmen aber nicht
  die normale UX.
- **Actual = tatsächlicher Verlauf.** `actual_start`/`actual_end` sind fachlich sinnvoll,
  aber sekundär: read-only in der normalen Übersicht, editierbar nur über eine explizite
  Korrektur-Aktion ("Ist-Daten korrigieren").
- **`plan_fte` ist die Source of Truth für den geplanten Gesamtaufwand einer Phase.**
  `ResourceDemand` ist eine optionale Rollen-Aufschlüsselung, keine zweite Source of Truth —
  es gibt keine automatische Synchronisierung, die `plan_fte` aus `SUM(ResourceDemand.fte)`
  überschreibt.
- **`ResourceDemand` ≠ `ResourceAssignment`.** Demand = Bedarf (Rolle × Periode × FTE),
  unabhängig von Personen. Assignment = konkrete Personenbesetzung eines Demands.
  Projektmitgliedschaft (`ProjectMembership`) ist wieder etwas anderes: das Hinzufügen einer
  Person zum Projektteam erzeugt keine automatische FTE-Zuordnung.
- **Gantt ist reine Visualisierung**, keine zweite Planungsdatenquelle. Er liest
  `forecast_start`/`forecast_end`, zeigt sie aber als normale Plan-Zeiträume.
- **Progress (`PlanPhase.progress`, manuelles Prozentfeld) ist deprecatet** (siehe P6/P11,
  Abschnitt 16.1). Kein Health-Dimension-Input mehr, keine neue Befüllung, aus
  Rückwärtskompatibilität im Modell/Schema erhalten.
- **Zeitfortschritt ist berechnet, nicht manuell** — reiner Datumsanteil (wie viel Prozent
  des geplanten Zeitraums vergangen sind), kein Health-/Fortschrittswert.
- **Tempo/Jira-Worklogs sind die Ist-Aufwandsquelle**, kein Personio/HR-System. Projekt-Level
  funktioniert; Phase-Level ist deferred (BD-1).
- **Tags sind eine Querschnittsschicht** mit generischer `TagLink`-Verknüpfung — kein
  Admin-Zwang zum Anlegen eines neuen Tags im normalen Arbeitsfluss.
- **`PlanPhase` ist die einzige operative Planungseinheit (P18 Pass 2, Abschnitt 6, final
  gelockt, IMPLEMENTIERT — CONFIRMED, Abschnitt 16.15).** Es gibt **keine** zweite, projektweite
  FTE-Monatsplanung mehr — eine noch nicht weiter aufgeteilte Phase (Leaf ohne Kinder) *ist*
  bereits die Grobplanung, kein separates Werkzeug.
- **`PlanPhase` kann hierarchisch sein** (`parent_phase_id`, max. 3 Ebenen, BD-10 **CLOSED**).
  Eine **Leaf**-Phase (ohne Kinder) trägt Zeitraum, `plan_fte` und Personenbesetzung. Eine
  **Parent**-Phase (mit Kindern) aggregiert ausschließlich aus ihren Kindern und trägt selbst
  **keine** operative Kapazität. Leaf/Parent ist kein gespeichertes Statusfeld, sondern
  `has_children` (berechnet).
- **Nur Leaf-Phasen zählen in der Kapazitätsaggregation.** Projekt-/Monats-/Portfoliokapazität
  ist **derived** (Summe über alle Leaf-Nachfahren, werktage-anteilige Monatsverteilung), keine
  separate Eingabe, kein `max(Grob, Fein)` mehr — es gibt nur noch eine Quelle je Phase.
  Parents zählen nicht zusätzlich, `ResourceDemand`/`ResourceAssignment` zählen nicht
  zusätzlich zur Projektkapazität (Abschnitt 6.6).
- **Konkretisierung erfolgt durch Kinder-Phasen**, nicht durch eine zweite Planungsebene:
  `[+ Unterphase hinzufügen]` auf einer Leaf-Phase macht sie automatisch zur Parent-Phase.
- **`Subproject` wird fachlich durch eine Parent-`PlanPhase` ersetzt** (Abschnitt 6.7). Die
  Tabelle bleibt zunächst compat-only bestehen, kein Drop-and-Pray.
- **`ResourceDemand` bleibt eine optionale Rollen-/technische Assignment-Schicht,
  `ResourceAssignment` die konkrete Personenzuordnung** — unverändert zum bereits geltenden
  Grundsatz oben, jetzt konsequent Leaf-only (Abschnitt 6.3).
- **Eine direkte Personenbesetzung verändert nie `plan_fte`.** `plan_fte` bleibt der Bedarf,
  Assignments zeigen die Besetzung; Über- oder Unterbesetzung wird angezeigt, nicht automatisch
  in `plan_fte` zurückgeschrieben (Abschnitt 6.10).
- **Gantt visualisiert denselben `PlanPhase`-Baum** wie Liste/Workspace — keine zweite
  Struktur, keine zweite Datenquelle (Abschnitt 6.3/5.6).
- **"Konkretisierungsgrad"/Planungsreife entfällt ersatzlos** (BD-13 **CLOSED**) — der
  `PlanPhase`-Baum selbst zeigt die Planungstiefe, keine neue Fortschrittskennzahl.

---

## 4. Aktuelles Datenmodell

Nur die aktuell gültigen, führenden Tabellen. Entfernte/historische Modelle stehen in
Abschnitt 17.3, nicht hier. **IST-Stand seit dem P18-Implementierungsdurchgang (B-1–B-7,
Abschnitt 16.7–16.13, gegen Code CONFIRMED, Abschnitt 16.15):** alle unten als "P18" markierten
Felder **existieren im Schema und sind operativ wirksam** — das ist keine Zielbeschreibung
mehr. Offen ist ausschließlich noch **B-8** (Abschnitt 16.15): die produktive Migration
bestehender Alt-Projekte auf diese Felder wurde noch nicht ausgeführt, und
`ResourceDemandGrid`/Subproject-UI wurden noch nicht entfernt — bis dahin bedienen Alt-Projekte
weiterhin `plan_phase_id = NULL`-Demands/`subprojects` parallel zum neuen Baum.

| Tabelle | Zweck |
|---|---|
| `projects` | Projektstammdaten (Name, Kunde, Startmonat, Anzahl Monate, Status, Jira-Verknüpfung, `projektleiter_person_id`) |
| `subprojects` | Teilprojekte (reine Gruppierung für Phasen/Milestones, kein eigenes Jira-Mapping). **Fachlich durch hierarchische `PlanPhase` (`parent_phase_id`) abgelöst** (Abschnitt 6.7, P18/B-2 IMPLEMENTIERT) — Tabelle/Router/Schemas bleiben bewusst compat-only bestehen (kein Drop-and-Pray), Backend-Endpoints sind explizit `@deprecated` dokumentiert. Frontend nutzt sie noch aktiv in `ProjectPlanningTab.tsx` (CRUD), `ProjectHistoryTab.tsx` (Historie) und `ProjectCommunicationTab.tsx` (Kommentar-Gruppierung) — Entfernung ist B-8-Scope, blockiert bis zur produktiven Migration (Abschnitt 16.15). |
| `plan_phases` | **Die** Planungseinheit — tagegenau, siehe Abschnitt 5. **Hierarchisch** (P18/B-1 IMPLEMENTIERT): `parent_phase_id` (self-referencing, nullable, max. 3 Ebenen, backend-validiert) und `reihenfolge` (int). Leaf/Parent-Baum operativ über `routers/planning.py`/`planning_calc.py` (B-3, IMPLEMENTIERT). Zusätzlich `jira_label` (nullable, P20.1 IMPLEMENTIERT, Abschnitt 16.19) — Jira-Label für den Worklog-Resolver, nur auf Leaf-Phasen gepflegt, gleicher Lifecycle wie `plan_fte` (wird beim Parent-Übergang serverseitig auf `NULL` gesetzt und historisiert), Konfliktprüfung verhindert identische Werte auf zwei Leaf-Phasen desselben Projekts (409). |
| `milestones` | Eigenständige Milestone-Entität. `plan_phase_id` (nullable, zeigt auf Leaf **oder** Parent) ist die primäre Verknüpfung (P18/B-7 IMPLEMENTIERT) — löst `subproject_id` operativ ab; `subproject_id` bleibt compat-only im Schema, aber nicht mehr in der UI (`MilestoneList.tsx` zeigt nur noch "Übergeordnete Phase"). |
| `baseline_snapshots` / `baseline_entries` | Planstände (eingefrorene Feldwerte je PlanPhase/Milestone). `_SNAPSHOT_FIELDS` umfasst `parent_phase_id`/`reihenfolge` (PlanPhase) und `plan_phase_id` (Milestone) (P18/B-7 IMPLEMENTIERT, Abschnitt 6.13/16.15) — Deviation-Erkennung deckt Parent-Wechsel/Zeitraum/`plan_fte` ab **und erkennt seit P18.1 (Abschnitt 16.16) zusätzlich strukturelle Baum-Änderungen**: "Phase hinzugefügt" (`type="added"`) und "Phase entfernt" (`type="removed"`, Name aus dem eingefrorenen `phase_type` rekonstruiert, kein `#<id>`-Roh-Fallback) werden beide erkannt und im Frontend (`BaselineList.tsx`) als eigene Zeilen dargestellt — der frühere Gap (Abschnitt 16.15) ist behoben. |
| `resource_roles`, `skills`, `person_skills` | Rollen-/Skill-Vokabular für Kapazitätsplanung. Interne, per Migration geseedete System-Rolle "Ohne Rolle" (`is_system_role`, P18/B-1 IMPLEMENTIERT) — im normalen Picker ausgeblendet, aus Rollenauswertungen ausgeblendet (P18/B-4/B-5 IMPLEMENTIERT). **Bekannter Gap:** es existiert aktuell kein `DELETE`-Endpoint für `resource_roles` überhaupt — die dokumentierte "nicht löschbar"-Regel ist damit faktisch, aber nicht durch einen Backend-Guard erzwungen (Abschnitt 16.15). |
| `resource_demands` | Bedarf (Rolle × Periode × FTE, optional `plan_phase_id`). Für **neue**, Baum-basierte Planung ist `plan_phase_id` immer gesetzt (direkte Personenzuordnung erzeugt automatisch eine `ResourceDemand` mit der System-Rolle, P18/B-4 IMPLEMENTIERT) — `plan_phase_id = NULL` (projektweite Grobplanung) bleibt für **bestehende, unmigrierte** Projekte weiterhin ein gültiger, aktiver Zustand (Abschnitt L6.1 (Historie 17.8)), bis B-2 produktiv ausgeführt wurde. |
| `resource_assignments` | Personenbesetzung eines `ResourceDemand` |
| `capacity_calendars`, `holidays`, `working_times`, `absences`, `internal_allocations` | Available-Capacity-Berechnung je Person/Periode — seit P18/B-4 zusätzlich bereichsbasiert abrufbar (`compute_person_capacity_for_range`, IMPLEMENTIERT) |
| `people`, `resource_profiles` | Personenstammdaten + Kapazitätsplanbarkeit (`weekly_hours`, `team_id`) |
| `teams` | Team-Stammdaten (Kapazitätsgruppierung) |
| `project_roles`, `project_memberships` | Person ↔ Projekt mit Rolle (≠ Assignment, siehe Abschnitt 3) |
| `permissions`, `app_roles`, `role_permissions` | Vorbereitung für künftiges Rollen-/Rechtesystem (kein Auth im Repo) |
| `comments` (inkl. `parent_id` für Threading), `tasks`, `blockers`, `decisions`, `risks`, `meeting_minutes` | Zusammenarbeit — alle taggbar, dokumentverknüpfbar, relationsfähig; alle außer `risks`/`meeting_minutes` zusätzlich `plan_phase_id`-verknüpfbar. An Leaf **und** Parent-Phasen uneingeschränkt erlaubt (Abschnitt 6.3, IMPLEMENTIERT/unverändert). |
| `documents`, `document_links` | Zentrale Dokumentenablage (Abschnitt 8) |
| `tags`, `tag_links`, `tag_categories` | Tag-System inkl. AI-Metadaten (`ai_relevant`, `ai_description`, `synonyms`) |
| `entity_relations` | Generische, typisierte Beziehung zwischen zwei beliebigen Entitäten (z. B. `resulted_in`, `depends_on`, `resolves`) |
| `health_thresholds` | Admin-konfigurierbare Schwellen für die neun Health-Dimensionen |
| `jira_worklogs_cache` | Ist-Daten-Cache aus Jira/Tempo (Projekt-Ebene, `projekt_mapping`) |
| `jira_issue_cache` | Issue-Metadaten (Labels/Component/Summary) aus demselben Sync-Suchergebnis wie `jira_worklogs_cache` (P20.1 IMPLEMENTIERT, Abschnitt 16.19) — Grundlage für den Worklog→PlanPhase-Resolver (P20.2, noch nicht implementiert). Upsert per Issue-Key bei jedem `POST /jira/sync`, kein zusätzlicher Jira-API-Call. |
| `worklog_phase_overrides` | Manuelle Worklog→PlanPhase-Korrektur auf Issue-Key-Ebene (P20.1 IMPLEMENTIERT, BD-1B CLOSED, Abschnitt 16.19) — höchste Priorität im künftigen Resolver, ändert nie Jira/Tempo-Originaldaten. CRUD über `/projects/plan-phases/{id}/worklog-overrides`. |
| `gap_snapshots` | Modell existiert, wird aktuell nicht befüllt — GAP Engine rechnet live (siehe Abschnitt 9) |
| `plan_history` | Änderungsprotokoll (Audit-Trail), gruppiert über `batch_id`. Additives Feld `plan_phase_id` (nullable, P18/B-1/B-3 IMPLEMENTIERT) — historisiert automatisch den `plan_fte`-Wert einer Phase, wenn sie durch das erste Kind zur Parent-Phase wird (Abschnitt 6.1a), verifiziert per Live-Testlauf (Abschnitt 16.15). |

Entfernt (Phase 26.9, siehe Abschnitt 17.3): `gantt_phases`, `project_gantt_phases`,
`fte_plan`, `project_fte_plan`, `team_members`, `assignments`, `projects.projektleiter`
(Freitext).

---

## 5. Projektplanung

### 5.1 PlanPhase — verbindliches Zielbild

`PlanPhase` ist die zentrale Einheit der konkreten Projektplanung, **tagegenau** geplant
(Beispiel: "Pflichtenheft, 01.10.2026–17.10.2026", nicht "Oktober = Pflichtenheft").

Der User plant eine PlanPhase über: Name (`phase_type`, Freitext mit Vorschlägen aus den
ehemaligen Gantt-Phasencodes), Start, Ende, Status, **Übergeordnete Phase** (optional,
`parent_phase_id` — Baumstruktur, P18/B-6 IMPLEMENTIERT), Owner, Tags, Plan-FTE. "Optionales
Teilprojekt" (`subproject_id`) ist **kein primäres Planungsfeld mehr** — die Baum-UI
(`PlanPhaseCreateModal.tsx`) bietet ausschließlich den "Übergeordnete Phase"-Picker an;
`subproject_id` bleibt nur als IST-/Legacy-Verknüpfung im Schema bestehen (Abschnitt 5.4).

Die normale Oberfläche zeigt **nicht** `baseline_start`/`baseline_end`,
`forecast_start`/`forecast_end`, `actual_start`/`actual_end` als sechs parallel editierbare
Fachfelder — das war ein bekanntes UX-Debt-Symptom (paralleler alter Inline-Editor neben dem
neuen Drawer) und ist mit P11 behoben (siehe Abschnitt 16.1).

- **Start/Ende** = `forecast_start`/`forecast_end` technisch, in der UI schlicht "Zeitraum"
  bzw. "Start"/"Ende".
- **Baseline** = Planstand-Konzept (Abschnitt 5.3), keine normalen Tagesfelder.
- **Actual** = "Tatsächlicher Verlauf", sekundär/read-only mit expliziter Korrektur-Aktion.
  Statuswechsel setzen `actual_start`/`actual_end` aktuell **nicht** automatisch — das wurde
  geprüft und bewusst zurückgestellt, um bestehende Ist-Daten nicht unkontrolliert zu
  überschreiben (siehe Abschnitt 15, mögliche spätere Ausbaustufe).
- **Progress** = deprecatet (Abschnitt 3).

### 5.2 Plan-FTE & Planstunden

`PlanPhase.plan_fte` ist die Source of Truth für den geplanten Gesamtaufwand (Abschnitt 3).
Planstunden werden zentral berechnet (`phase_metrics_calc.plan_hours`, nicht im Frontend
dupliziert):

```
plan_hours = plan_fte × Werktage(forecast_start, forecast_end) × VOLLZEIT_WOCHENSTUNDEN / 5
```

`VOLLZEIT_WOCHENSTUNDEN = 40` (`backend/app/constants.py`). Werktage = Mo–Fr, **ohne
Feiertagsabzug** — das ist ein bekannter, dokumentierter Scope (BD-4), keine Baseline die
sich still ändert.

**Zeitfortschritt** (`time_progress_pct`) ist rein datumsbasiert: Anteil des geplanten
Zeitraums (`forecast_start`…`forecast_end`), der bis heute vergangen ist. Kein Health-/
Fortschrittswert.

**Aufwandsverbrauch** (`effort_consumption_pct` = Ist-Aufwand / Plan-Aufwand) ist als
Kennzahl vorgesehen, aber das Tempo→PlanPhase-Mapping ist fachlich noch nicht entschieden
(BD-1). Die API liefert deshalb aktuell konsequent `null`/"noch nicht eindeutig
zugeordnet" — es gibt bewusst **keine Datumsheuristik** und **kein Fake-Ist**.

### 5.3 Planstand (`BaselineSnapshot`)

Ein Planstand ist ein eingefrorener historischer Stand des damaligen Plans (Beispiele: "V1 —
Initialplanung", "V2 — nach Kickoff", "V3 — Replanung Change Request"). Der User bearbeitet
**nicht** kontinuierlich Baseline-Start/-Ende, sondern:

1. bearbeitet den aktuellen Plan (Start/Ende, wie in 5.1),
2. hält bei Bedarf explizit einen "Planstand" fest (`POST /projects/{id}/baselines`).

Ein Snapshot friert je `PlanPhase` `phase_type`, `baseline_start`, `baseline_end`,
`forecast_start`, `forecast_end`, `plan_fte`, `status` ein (plan_fte seit P11 mit dabei —
vorher fehlte es, ein Planstand konnte historischen Aufwand nicht rekonstruieren), und je
`Milestone` `name`, `baseline_date`, `forecast_date`, `status`.

Planstand-Vergleich (`GET /projects/baselines/{id}/deviations`) zeigt je eingefrorenem Feld
`baseline_value → current_value`; für Datumsfelder zusätzlich `delta_days` (z. B. "Ende
25.08. → 29.08., +4 Tage"), für `plan_fte` die reine Wertdifferenz, die das Frontend selbst
berechnet (z. B. "0,5 → 0,7, +0,2 FTE"). Snapshot-vs-Snapshot-Vergleich (zwei Planstände
gegeneinander, nicht nur gegen live) ist deferred (Abschnitt 15).

Planstand anlegen: Name, Grund (optional), Tags. Tags werden über die generische
`TagLink`-Infrastruktur verwaltet; Baselines sind seit P5 taggbar (Erstellzeit-only, kein
Update-Endpoint — ein eingefrorener Stand ist unveränderlich).

Seit P19 zeigt der `PlanPhaseWorkspace` (Übersicht-Tab) zusätzlich eine kompakte
"Seit Planstand VX (Datum) geändert: …"-Zeile, clientseitig gegen denselben
Deviation-Endpoint berechnet und auf `entity_id == aktuelle Phase` (bei Parent-Phasen
zusätzlich ihre Nachfahren) gefiltert — keine neue Snapshot-Engine, kein
Snapshot-vs-Snapshot-Vergleich, reine Kurzform des ohnehin projektweiten Vergleichs. Siehe
Abschnitt 16.18.

### 5.4 Teilprojekte (Legacy/IST-Hinweis)

**Fachlich durch die hierarchische `PlanPhase` (`parent_phase_id`) abgelöst** (Abschnitt 6.7,
P18/B-2/B-6/B-7 IMPLEMENTIERT, gegen Code CONFIRMED, Abschnitt 16.15) — eine Parent-`PlanPhase`
leistet alles, was `Subproject` leistete, zusätzlich mit abgeleiteten Zeiträumen/Kapazität und
bis zu drei Gruppierungsebenen (BD-10, **CLOSED**). `PlanPhaseList.tsx`/`PlanPhaseGantt.tsx`/
`MilestoneList.tsx` gruppieren bereits ausschließlich nach `parent_phase_id`, nicht mehr nach
Subproject.

`subprojects`/`subproject_id` bleiben **compat-only** bestehen (`PlanPhase.subproject_id`/
`Milestone.subproject_id` weiterhin nullable, `NULL` = projektweit, gesetzt =
teilprojektbezogen) — kein Drop-and-Pray. Sie sind aber **kein primärer Bedienweg für neue
Planung** mehr. Noch aktiv genutzt: `ProjectPlanningTab.tsx` (Teilprojekt-CRUD),
`ProjectHistoryTab.tsx` (Teilprojekt-Historie), `ProjectCommunicationTab.tsx`
(Kommentar-Gruppierung nach Teilprojekt) und `export.py` (Export-Gruppierung) — diese Pfade
bleiben bestehen, bis die produktive B-2-Migration ausgeführt und B-8 (Legacy Cutover)
abgeschlossen ist (Abschnitt 16.15). Router-Endpunkte unter `/subprojects` sind bereits
`@deprecated` dokumentiert.

### 5.5 Milestones

Milestones sind echte Entitäten (`Milestone`-Tabelle seit Phase 17), kein Rückfall auf den
ehemaligen Gantt-Phasencode `?`. **Primäre Verknüpfung ist `plan_phase_id`** (nullable, zeigt
auf eine Leaf- **oder** Parent-`PlanPhase`; P18/B-7 IMPLEMENTIERT, gegen Code CONFIRMED) —
`NULL` bleibt "projektweiter Meilenstein". `subproject_id` bleibt im Schema compat-only, wird
aber in der UI (`MilestoneList.tsx`) nicht mehr angeboten — dort steht ausschließlich die
"Übergeordnete Phase"-Auswahl. Dieselbe UX-Regel wie bei PlanPhase gilt: das normale
Datumsfeld heißt schlicht "Datum" (= `forecast_date`), `baseline_date` ist compat-only,
`actual_date` sekundär mit expliziter Korrektur-Aktion ("Ist-Datum korrigieren").

Seit P19 zeigt der `PlanPhaseWorkspace` zusätzlich eine kompakte "Meilensteine"-Karte im
Aktivität-Tab (Leaf **und** Parent), gefiltert auf `plan_phase_id == aktuelle Phase`
(nicht rekursiv) — Wiederverwendung von `MilestoneList.tsx`, kein zweites Milestone-Modell,
kein neuer Tab. Siehe Abschnitt 16.18.

### 5.6 Gantt

Gantt ist **ausschließlich Visualisierung**. Source of Truth bleiben `PlanPhase`/`Milestone`.
Gantt liest `forecast_start`/`forecast_end`, zeigt sie aber als normale Plan-Zeiträume (ein
Balken pro Phase, keine technisch benannten Baseline-/Forecast-/Ist-Balken nebeneinander).
**Primär gruppiert Gantt nach dem `PlanPhase`-Baum** (`parent_phase_id`, P18/B-6 IMPLEMENTIERT,
gegen Code CONFIRMED): eine Parent-Phase rendert als umrandete Hüllkurve
(`derived_forecast_start`/`derived_forecast_end`), eine Leaf-Phase als gefüllter Balken; beide
öffnen per Klick denselben `PlanPhaseWorkspace`. Teilprojekt-Gruppierung ist kein aktiver
Gantt-Pfad mehr.

Gantt darf: PlanPhases tagegenau darstellen, Tag/Woche/Monat/Quartal zoomen (aktuell:
Monatsraster), Phase anklickbar machen → öffnet den PlanPhaseWorkspace-Drawer.

Gantt soll **nicht**: primäre Planungsoberfläche sein, eigene Planungsdaten speichern,
Drag&Drop oder Resize als notwendigen Workflow erzwingen (beides deferred, Abschnitt 15).
Milestones im Gantt darstellen ist ebenfalls deferred (bewusster Scope-Cut aus P8).

---

## 6. Kapazitätsplanung

**Status:** Fachlich final gelockt und gegen Code **CONFIRMED implementiert** (B-1–B-7;
Codebase Validation Matrix + vollständige Herleitung siehe separates
[`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)).
**BD-10/BD-11/BD-12/BD-13 sind CLOSED** (Abschnitt 14) — es gibt keine offene
Architekturentscheidung mehr, nur noch die technische Restarbeit vor dem produktiven Cutover
(B-8, Abschnitt 16.16/16.17). Dieser Abschnitt beschreibt **ausschließlich** die aktuelle,
einzige gültige Kapazitätsarchitektur — der frühere, nie implementierte Pass-1-Entwurf
(Grob-/Feinplanung, `max()`-Reconciliation) und der weiterhin aktive, aber abzulösende
Legacy-Pfad (`ResourceDemandGrid`/`Subproject`) sind vollständig nach Abschnitt 17.7 bzw.
17.8 verschoben (siehe "Wie dieses Dokument zu lesen ist").

**Orientierung — Mapping auf die Kapazitäts-Kernthemen** (dieser Abschnitt behält die
gewachsene, detaillierte 6.1–6.14-Gliederung bei, statt sie in ein grobes 7-Themen-Raster zu
pressen und dabei Rebuild-relevantes Detail zu verlieren; diese Tabelle ist die Navigationshilfe
dafür):

| Kernthema | Abschnitt |
|---|---|
| PlanPhase als Kapazitätsquelle (Leaf/Parent, `plan_fte`, Planstunden) | 6.1, 6.1a, 6.3 |
| Personenbesetzung (Direct Assignment, Bedarf/Besetzt/Offen/Überbesetzt) | 6.10, 6.11 |
| Rollenaufschlüsselung (`ResourceDemand` optional, Systemrolle "Ohne Rolle") | 6.4 |
| Available Capacity (`WorkingTime`/`Holiday`/`Absence`/`InternalAllocation`, Range) | 6.5, 6.11 |
| Derived Monthly Capacity (read-only, keine Monatsplanung) | 6.6 |
| Portfolio Capacity (dieselbe zentrale Aggregation, keine Doppelzählung) | 6.6 |
| Legacy / Pending Cutover | 6.15 |

**Zusammenfassung des Umsetzungsstands (Details: Abschnitt 16.7–16.17):** B-1 (Hierarchy
Domain Foundation), B-3 (Phase Tree API), B-4 (Direct Assignment/Available Capacity Range),
B-5 (Derived Monthly & Portfolio Capacity), B-6 (PlanPhase Tree UX) und B-7 (Gantt/Milestone/
Planstand Integration) sind **implementiert und CONFIRMED**. B-2 (Migration Tooling) ist
ebenfalls implementiert und CONFIRMED, **aber bisher nur gegen eine synthetische
Testfixture ausgeführt, nicht gegen echte Produktivdaten** — das ist der einzige verbliebene
B-8-Blocker (Abschnitt 16.17, Runbook `backend/scripts/MIGRATION_DRY_RUN_RUNBOOK.md`). Solange
B-2 nicht produktiv angewendet ist, bleiben bestehende, unmigrierte Projekte ausschließlich
über den in Abschnitt 6.15 zusammengefassten Legacy-Compat-Pfad bedienbar.

### 6.1 Kernidee

`PlanPhase` ist die **einzige** operative Planungseinheit — für Kapazität **und** für Strukturierung
(löst damit gleichzeitig die Grob-/Feinplanungs-Frage aus Abschnitt 6a **und** die
Subproject-Frage aus Abschnitt 5.4 ab). `PlanPhase` bekommt ein neues, additives, nullable Feld
`parent_phase_id` (self-referencing FK). Eine Phase **ohne** Kinder ("Leaf") trägt operative
Kapazität (`plan_fte`, Zeitraum) wie heute. Eine Phase **mit** Kindern ("Parent"/Sammelphase)
aggregiert ausschließlich aus ihren Kindern und trägt selbst **keine** operative Kapazität mehr
— was mit ihrem alten `plan_fte`-Wert beim Übergang zum Parent geschieht, regelt 6.1a (**das
ist eine bewusste Korrektur gegenüber dem ursprünglichen Pass-2-Entwurf**, siehe unten).

**Maximale Hierarchietiefe: 3 Ebenen** (BD-10, **CLOSED**). Beispiel: Ebene 1 "Wareneingang" →
Ebene 2 "Schnittstellen" → Ebene 3 "WE-Anmeldung". Eine vierte Ebene ist nicht erlaubt — das
Backend validiert diese Regel beim Anlegen/Verschieben einer Phase (analog zum bestehenden
Muster `_check_subproject`), das Frontend bietet auf Ebene 3 keine weitere
"+ Unterphase hinzufügen"-Aktion mehr an.

**Kein neues Statusfeld:** Leaf/Parent wird nicht gespeichert, sondern query-seitig berechnet
(`has_children = EXISTS(child mit parent_phase_id = diese Phase)`).

### 6.1a Parent-`plan_fte`-Lifecycle (Korrektur gegenüber dem ursprünglichen Pass-2-Entwurf)

**Problem mit dem ursprünglichen Entwurf:** Der erste Pass-2-Entwurf sah vor, dass eine
Leaf-Phase ihren `plan_fte`-Wert beim Wechsel zum Parent unverändert in der DB behält und —
werden alle Kinder wieder gelöscht — augenblicklich und automatisch wieder operativ sichtbar
wird. Das ist fachlich **nicht akzeptabel**: ein historischer, möglicherweise Monate alter
Kapazitätswert dürfte dann ohne bewusste Bestätigung plötzlich wieder als aktuelle Planung
gelten, nur weil jemand die letzte Unterphase gelöscht hat.

**Zielregel:** Der bisherige Planungszustand einer Phase muss historisch nachvollziehbar
bleiben — aber eine Parent-Phase besitzt **zu keinem Zeitpunkt** eine operative eigene
Kapazität, und wird eine Parent-Phase wieder zum Leaf, wird **niemals automatisch** ein alter
`plan_fte`-Wert reaktiviert. Die Phase braucht in diesem Fall eine bewusste, neue
Kapazitätsbestätigung durch den Projektleiter.

**Gewählte Umsetzung (Variante A):** Sobald eine Leaf-Phase ihr erstes Kind erhält
(`has_children` wechselt `false → true`), wird `PlanPhase.plan_fte` **serverseitig auf `NULL`
gesetzt**, und der bisherige Wert wird in einem Audit-Eintrag historisiert (additives, nullable
Feld `plan_phase_id` auf der bereits bestehenden `plan_history`-Tabelle — kein neues
Fachfeld wie `previous_plan_fte`, nur eine generische, technisch zwingende
Audit-Trail-Erweiterung, analog zum bereits etablierten Muster generischer Verknüpfungsfelder
wie `entity_type`/`entity_id`). Wird die Phase später wieder zum Leaf (letztes Kind entfernt),
bleibt `plan_fte = NULL` — die UI zeigt denselben leeren Zustand wie bei einer frisch
angelegten Leaf-Phase ohne Kapazität ("Kein Plan-FTE gesetzt", gültiger Zustand, Testfall B in
Abschnitt 20 des Implementierungsplans) und verlangt eine bewusste Neu-Eingabe. Zusätzlich
bleibt jeder vor der Umwandlung explizit festgehaltene **Planstand**
(`BaselineSnapshot`/`BaselineEntry`, unverändert) als weitere, unabhängige historische Quelle
bestehen — wer den alten Wert nachvollziehen will, findet ihn im Planstand-Vergleich oder im
Audit-Trail, nie automatisch reaktiviert im operativen Feld.

Bewertete Alternativen: **Variante B** (Wert physisch erhalten, aber über eine separate
Confirmation-State-Logik als "nicht gültig" markieren) wurde geprüft und verworfen — sie
bräuchte ein neues Statusfeld/-Flag, obwohl Variante A dasselbe Ergebnis ohne neues Fachfeld
erreicht (nur eine generische Audit-Spalten-Erweiterung). **Variante C** (andere Lösung) wurde
nicht identifiziert, die einen echten Vorteil gegenüber A hätte.

### 6.2 Lifecycle: Zeitraum → Kapazität → Personen → Konkretisierung

1. **Zeitraum:** `+ Phase hinzufügen` → Name, Start, Ende, optional `parent_phase_id` (leer =
   Top-Level-Phase des Projekts). Bereits ein gültiger, vollständiger Planungszustand.
2. **Kapazität:** `plan_fte` setzen — unverändert wie heute (Abschnitt 5.2).
3. **Personen:** `[+ Mitarbeiter zuweisen]` direkt auf der Phase, **ohne** erzwungene
   Rollenauswahl (Abschnitt 6.4). `[Rollen aufschlüsseln]` bleibt optional verfügbar.
4. **Konkretisierung statt zweiter Planungsebene:** `[+ Unterphase hinzufügen]` — sobald die
   erste Unterphase existiert, wird die Elternphase automatisch zur Sammelphase (Abschnitt
   6.1). Dieselbe Sequenz beginnt für jede neue Unterphase von vorn, bis zur Tiefenbegrenzung
   (BD-10).

Damit entfällt die in Abschnitt 6a beschriebene zweite, projektweite Monatsachse
(`ResourceDemand.plan_phase_id = NULL`) vollständig — eine anfangs grobe, noch nicht
aufgeteilte Phase **ist** bereits die Grobplanung, kein separates Werkzeug nötig. Die
Rolle-×-Monat-Grobplanungsoberfläche (`ResourceDemandGrid`, Abschnitt L6.1 (Historie 17.8)) entfällt damit
ersatzlos.

### 6.3 Leaf-/Parent-Semantik im Detail

| Bereich | Leaf | Parent |
|---|---|---|
| Zeitraum | direkt editierbar | read-only, abgeleitet: `MIN(child.forecast_start)`/`MAX(child.forecast_end)`, rekursiv |
| `plan_fte` | direkt editierbar, operative Quelle | nicht editierbar im normalen Fluss; wird beim Entstehen des ersten Kindes serverseitig auf `NULL` gesetzt und historisiert (Abschnitt 6.1a) — UI zeigt "Aggregiert aus N Unterphasen" |
| `ResourceDemand`/`ResourceAssignment` | wie heute, optional (Abschnitt 6.4) | nicht sinnvoll — Kapazität wird nicht doppelt (Parent UND Leaf) geplant, UI blendet den Editier-Pfad aus |
| Monatsverteilung/Portfolio-Aggregation | fließt ein | fließt **nicht** ein — nur Leaf-Nachfahren zählen (Abschnitt 6.6) |
| Comment/Task/Blocker/Decision | erlaubt (wie heute) | erlaubt — bereits heute technisch uneingeschränkt möglich, da diese Modelle nur `plan_phase_id` prüfen, nicht Leaf/Parent-Status |
| Milestone | erlaubt | erlaubt (z. B. "Fachkonzept freigegeben" am Ende einer Sammelphase) |
| Gantt | eigener Balken | aggregierte Hüllkurve, ein-/ausklappbar, optionaler Summary-Balken |
| Löschen | normales DELETE, wie heute | **standardmäßig blockiert**, sofern Kinder existieren (BD-11, Abschnitt 6.9) |

### 6.4 Rollen-Aufschlüsselung bleibt optional (ohne neues Modell)

`ResourceDemand.resource_role_id` ist heute NOT NULL — bereits jetzt, unabhängig von Grob/Fein.
Damit ein Projektleiter eine Person direkt mit FTE zuordnen kann, ohne vorher eine Rolle zu
wählen: eine System-`ResourceRole` ("Ohne Rolle"/"Allgemein", per Migration geseedet) wird von
der UI transparent verwendet — Backend legt bei Bedarf automatisch eine generische
`ResourceDemand` an und hängt das `ResourceAssignment` daran. Kein neues Modell, keine
Aufweichung von Demand≠Assignment (Kernprinzip, Abschnitt 3) — reine UX-Abstraktion über dem
bestehenden Modell. `[Rollen aufschlüsseln]` bleibt als expliziter, optionaler Button
verfügbar.

**Verbindliche Governance-Regeln für die interne System-Rolle "Ohne Rolle" (Korrektur/Ergänzung
gegenüber dem ursprünglichen Entwurf):**

- Sie ist eine interne Systemrolle, **nicht löschbar** — fachliche Invariante, unabhängig vom
  aktuellen technischen Enforcement-Stand. **Aktueller Code (verifiziert, Abschnitt 16.15 Punkt
  5):** Es existiert aktuell **kein** `DELETE /resource-roles/{id}`-Endpoint überhaupt (jeder
  Aufruf liefert `405`, für alle Rollen, nicht nur "Ohne Rolle") — die Invariante ist damit
  heute bereits **faktisch** durchgesetzt, aber nicht durch einen gezielten Guard, sondern
  durch das Fehlen jedes Löschpfads. Ein zentraler Domain-Helper
  (`ensure_role_deletable(role)`, `routers/capacity.py`) kapselt die Regel bereits
  (`is_system_role == True → 409`) und **muss** von einem künftigen Lösch-Endpoint
  aufgerufen werden, sobald einer eingeführt wird — bis dahin ist er ungenutzter,
  aber getesteter Code (kein künstlicher Endpoint wurde nur für den Guard ergänzt, siehe
  Abschnitt 16.15 Punkt 5).
- Sie wird im **normalen Rollen-Picker ausgeblendet** — Projektleiter:innen wählen sie nie
  aktiv aus, sie entsteht ausschließlich transparent im Hintergrund beim direkten
  "Mitarbeiter zuweisen"-Flow.
- Sie erscheint **nicht als echte fachliche Rolle** in Reporting-/Skill-Analysen (Controlling,
  Rollenauswertung, `GET /controlling/roles`) — Auswertungen, die nach Rolle gruppieren, blenden
  sie aus oder weisen sie explizit als "ohne Rollenzuordnung" statt als eigenständige Rolle aus.
- Sie wird **nicht für Skill-Matching** verwendet (Kandidatenvorschläge, `resource-demands/
  {id}/candidates`) — ein Demand mit dieser Rolle filtert nicht nach Skill, da es keine echte
  Rollenanforderung repräsentiert.
- Die UI bezeichnet eine direkte Personenzuordnung **niemals** als "Rolle: Ohne Rolle" —
  sichtbar ist ausschließlich "Mitarbeiter zugeordnet: Name, X FTE", ohne Rollenlabel.

### 6.5 Available Capacity

Unverändert gegenüber Abschnitt L6.2 (Historie 17.8)/6a.8 — identische Erweiterung um eine bereichsbasierte
Variante von `compute_person_capacity` bleibt nötig, unabhängig von Grob/Fein vs. Hierarchie,
da sie ausschließlich mit Leaf-Zeiträumen arbeitet. Keine neue Capacity-Engine.

### 6.6 Monatsaggregation ohne zweite Achse

```
Projektkapazität(Monat) = SUM( monthly_distribution(leaf.plan_fte, leaf.forecast_start,
                                leaf.forecast_end)[Monat] für alle Leaf-Nachfahren des Projekts )
```

Identischer werktage-anteiliger Verteilungsschlüssel wie Abschnitt 6a.6 (Historie 17.7) (kein 50/50, kein
Feiertagsabzug, BD-4-konform) — der einzige Unterschied: **eine** Quelle statt zwei, daher keine
`max()`-Formel, kein "Noch grob", keine Konkretisierungsgrad-Kennzahl mehr nötig (BD-13). Die
in Abschnitt L6.3 (Historie 17.8) dokumentierte Aggregationslücke (heutige Portfolio-Endpoints summieren
`ResourceDemand` ohne `plan_phase_id`-Filter) löst sich **strukturell** auf, sobald die
Migration (Abschnitt 6.9) abgeschlossen ist — es gibt dann keine `plan_phase_id = NULL`-Zeilen
mehr, über die fälschlich mit-addiert werden könnte. Kein Filter-Bugfix an
`compute_capacity_gap`/`get_allocation_gaps`/`get_role_analysis`/`_cockpit_capacity` nötig.

`GET /projects/{id}/capacity/monthly` hatte vor P19 keinen Frontend-Konsumenten (Endpoint/Typ
existierten, wurden aber nirgends gerendert). Seit P19 zeigt `ProjectMonthlyCapacityCard.tsx`
im Planung-Tab diese Werte inkl. Monats-Drilldown (additives `by_phase`-Feld je Monatseintrag,
serverseitig aus derselben `monthly_distribution()`-Berechnung abgeleitet, keine zweite
Formel) — siehe Abschnitt 10/16.18.

### 6.7 Subproject wird durch Parent-PlanPhase ersetzt

`Subproject` ist heute technisch nur `{id, name, reihenfolge, project_id}` — keine Zeiträume,
keine Kapazität, feste Tiefe von genau 1 Ebene (Codebase-Audit, Pass-2-Dokument Abschnitt 3.1).
Eine Parent-`PlanPhase` leistet alles, was `Subproject` leistet, zusätzlich mit abgeleiteten
Zeiträumen/Kapazität und bis zu 3 Ebenen (BD-10, **CLOSED**). Migration: pro `Subproject` eine
neue Top-Level-`PlanPhase` anlegen, bestehende `PlanPhase`/`Milestone`/`Comment` dieses
Teilprojekts auf `parent_phase_id`/`plan_phase_id` umhängen (Details:
[`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)
Abschnitt 22). `subprojects`-Tabelle/`subproject_id`-Spalten bleiben zunächst compat-only
bestehen (kein Drop-and-Pray, analog zum Legacy Cutover Phase 26.9).

### 6.8 Milestones

`Milestone.subproject_id` → `Milestone.plan_phase_id` (nullable). `NULL` bleibt "projektweiter
Meilenstein". Ein gesetzter Wert kann sowohl auf eine Leaf- als auch auf eine Parent-Phase
zeigen (im Unterschied zur Kapazitätsplanung, die Leaf-only ist) — ein Meilenstein schließt oft
eine Sammelphase ab, nicht eine einzelne Detailphase.

### 6.9 Löschverhalten (BD-11, **CLOSED** — Korrektur gegenüber dem ursprünglichen Entwurf)

**Der ursprüngliche Pass-2-Entwurf empfahl ein kaskadierendes Löschen** (analog zum heutigen
`delete_subproject`-Verhalten). **Diese Empfehlung wurde revidiert.** Standard-`DELETE` einer
Parent-Phase mit Kindern wird **blockiert** (`409`), nicht automatisch kaskadierend gelöscht.

Beispiel-Fehlermeldung: *"Diese Phase enthält 8 Unterphasen und kann nicht direkt gelöscht
werden."* Angebotene Aktionen in der UI:

- **Unterphasen verschieben** (auf eine andere Parent-Phase oder auf Top-Level reparenten),
  danach ist die Phase leaf und normal löschbar.
- **Abbrechen.**
- Optional eine **separate, explizit destruktive Aktion**: "Gesamten Zweig löschen"
  (Subtree-Delete).

Ein kompletter Subtree-Delete ist **niemals** die Standardaktion, sondern:

- eine **separate**, eigenständige Operation (eigener Endpoint/eigene Bestätigung, nicht
  identisch mit dem normalen `DELETE`),
- verlangt eine **starke Bestätigung** (z. B. Anzahl betroffener Nachfahren + Namen eingeben),
- zeigt vorher die **Auswirkungen** auf Assignments, Collaboration (Comments/Tasks/Blocker/
  Decisions), Milestones und Documents der betroffenen Nachfahren an,
- ist **auditierbar** (Eintrag im Audit-Trail, wer wann welchen Zweig mit welchem Umfang
  gelöscht hat).

Kein stilles Cascade-Verhalten als Standard — das ist eine bewusste Abkehr vom heutigen
`delete_subproject`-Präzedenzfall, weil eine Parent-`PlanPhase` (anders als das heutige,
inhaltsleere `Subproject`) selbst Kapazität, Zuordnungen und Collaboration-Historie trägt, deren
Verlust nicht durch einen einzelnen, unauffälligen `DELETE`-Aufruf ausgelöst werden darf.

### 6.10 Assignment-Semantik

Eine direkte Personenbesetzung darf **nie** `plan_fte` verändern — `plan_fte` bleibt der Bedarf
(Abschnitt 3), Assignments zeigen ausschließlich die Besetzung:

```
Plan-FTE:            0,40
Assignments:  Dominik 0,20
              Max     0,20
→ Bedarf 0,40 / Besetzt 0,40 / Offen 0,00
```

Übersteigt die Summe der Assignments `plan_fte` (Überbesetzung), wird `plan_fte` **nicht**
automatisch erhöht — die UI zeigt die Überbesetzung als solche an (konsistent mit dem
bestehenden `open_fte`/Reconciliation-Prinzip, Abschnitt 3/L6.1).

### 6.11 Available Capacity beim Assignment

Beim Zuordnen einer Person zeigt die UI Bedarf, verfügbare Kapazität im Phasenzeitraum und ggf.
Unterdeckung, z. B. "Benötigt 0,40 / Verfügbar 0,25 / Unterdeckung 0,15" — unverändert die in
6.5 beschriebene bereichsbasierte Erweiterung von `compute_person_capacity`, keine neue
Capacity-Engine.

### 6.12 Migration bestehender Daten

Zwei bestehende, potenziell befüllte Konzepte müssen migriert werden, additiv und ohne
Informationsverlust (vollständiges Vorgehen und Migrationsreport-Anforderungen:
[`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)
Abschnitt 20-22/35): **automatisiert, deterministisch, mit Vorher-/Nachher-Report** (BD-12,
**CLOSED**) — kein manuelles Nachbauen bestehender Daten als Hauptstrategie.

- **Bestehende Grobplanung** (`ResourceDemand.plan_phase_id = NULL`) — **korrigierte Strategie
  gegenüber dem ursprünglichen Entwurf:** Der ursprüngliche Entwurf sah eine einzelne
  Leaf-Phase "Grobplanung (migriert)" mit `plan_fte = NULL` über den gesamten Zeitraum vor. Das
  widerspricht dem Zielbild, in dem `plan_fte` die operative Source of Truth jeder Leaf-Phase
  ist ("Demand trägt Kapazität, obwohl `plan_fte` NULL ist" wäre ein neuer Sonderfall). Statt
  dessen: pro Projekt eine neue **Parent**-Top-Level-Phase "Grobplanung (migriert)"
  (`parent_phase_id = NULL`), darunter **eine Leaf-Kindphase je Monat**, der bereits eine
  Grob-`ResourceDemand`-Periode zugeordnet war (z. B. "Grobplanung Oktober",
  01.10.–31.10., "Grobplanung November", 01.11.–30.11., …). **Ausnahme, ausdrücklich nur für
  diesen einmaligen Migrationsschritt:** `plan_fte` der neuen Monats-Leaf-Phase wird initial aus
  der **Summe** der bisherigen `ResourceDemand.fte`-Zeilen dieses Monats abgeleitet (Beispiel:
  Senior 0,80 + Consultant 0,70 → `plan_fte = 1,50`), weil diese Summe die bisher führende
  Monatsplanung repräsentiert. **Das ist keine neue Laufzeitregel** — nach der Migration gilt
  wieder uneingeschränkt "`plan_fte` ist führend, keine automatische Synchronisierung aus
  `SUM(ResourceDemand.fte)`" (Abschnitt 3). Bestehende `ResourceDemand`/`ResourceAssignment`-
  Zeilen werden auf die passende neue Monats-Leaf-Phase umgehängt (Perioden bleiben
  unverändert). Dadurch hat jede operative Leaf-Phase ein echtes `plan_fte`, Monatskapazität
  bleibt reproduzierbar, und eine spätere Konkretisierung ist Monat für Monat möglich (jede
  Monats-Leaf kann selbst wieder in echte Phasen aufgeteilt werden, Abschnitt 6.2).
- **Bestehende Subprojects:** siehe 6.7/6.9 (Migrationsdetails).
- Beide Migrationen sind einmalige, deterministische Skripte mit **Dry-Run-Modus** und
  Vorher-/Nachher-Zahlenreport, der mindestens enthält: Projekte, PlanPhases vorher/nachher,
  Subprojects vorher/nachher, ResourceDemands, ResourceAssignments, Milestones,
  Comments/Tasks/Blocker/Decisions soweit betroffen, FTE-Summen, Orphan-Checks,
  Hierarchietiefe-Checks — kein Datenverlust.

### 6.13 Was unverändert aus Abschnitt 6a übernommen wird

Nicht jede Pass-1-Überlegung wird verworfen — folgende Teile sind unabhängig von der
Grundsatzentscheidung gültig und werden 1:1 übernommen: die Formel für `plan_hours`/
`monthly_distribution` (Abschnitt 5.2/6a.6, werktage-anteilig, kein Feiertagsabzug, BD-4), die
`compute_person_capacity_for_range`-Erweiterung (Abschnitt 6a.8 (Historie 17.7)/L6.2), das Prinzip "`plan_fte`
bleibt führend, keine automatische Synchronisierung aus der Rollen-Aufschlüsselung"
(Abschnitt 3).

### 6.14 Planstand-Strategie

Ein Planstand muss künftig den `PlanPhase`-Baum rekonstruieren können: Kind neu hinzugekommen,
Kind entfernt, Parent geändert, Phase verschoben, `plan_fte` geändert. Der bestehende generische
`BaselineEntry`-Mechanismus (`entity_type`/`entity_id`/`field`/`value`) reicht dafür aus — er
wird um die zusätzlichen eingefrorenen Felder `parent_phase_id` und `reihenfolge` (PlanPhase)
sowie `plan_phase_id` (Milestone) erweitert, keine Schemaänderung nötig (Details:
[`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)
Abschnitt 16). Eine separate Grobplanung wird nicht mehr eingefroren — es gibt nach der
Migration nur noch `PlanPhase`-Felder.

### 6.15 Legacy / Pending Cutover

Nur zur Diagnose/Nachvollziehbarkeit — **keine Zielarchitektur**, volles Detail in Abschnitt
17.8:

- **`ResourceDemandGrid` existiert weiterhin** für unmigrierte Alt-Projekte
  (`ResourceDemand.plan_phase_id = NULL`) — einziger Bedienweg für deren Kapazität, bis B-2
  produktiv ausgeführt ist.
- **Die Subproject-UI existiert weiterhin** bis B-8 (Planning-Tab, Historie-/
  Kommunikations-Tab, PPTX-Export) — wird fachlich durch eine Parent-`PlanPhase` ersetzt
  (Abschnitt 6.7), Tabelle/Spalten bleiben compat-only bestehen.
- **`ResourceDemand.plan_phase_id = NULL` ist Legacy-Zustand**, kein Bestandteil der
  Zielarchitektur — soll operativ nicht mehr für neue Planung entstehen (jede neue
  Direktzuweisung erzeugt bereits heute automatisch eine phasengebundene `ResourceDemand`,
  Abschnitt 6.4).
- Zwei sekundäre Auswertungen (Effort-/Health-Soll-Track `gap_analysis._soll_je_monat`/
  `health_calc._effort_health`, PPTX-Export "fte"-Feld) lesen weiterhin direkt
  `ResourceDemand.fte` statt der PlanPhase-Kapazität — bewusst deferred (Abschnitt 16.16,
  Punkt 6), kein Doppelzählungsrisiko, da sie nicht zur zentralen Projektkapazität addieren.
- Entfernung von `ResourceDemandGrid`/Subproject-UI/Compat-Schema ist **nicht** Teil dieses
  Abschnitts, sondern erfolgt erst nach erfolgreichem produktivem B-8-Cutover, in einem
  separaten, explizit freigegebenen Auftrag (Abschnitt 16.17, Cutover-Runbook).
- Seit P19 ist dieser Legacy-Block im Planung-Tab (`ProjectPlanningTab.tsx`) visuell klar
  als sekundär gekennzeichnet: standardmäßig eingeklappt, mit der Überschrift
  "Legacy-Kapazitätsplanung — wird nach Migration ersetzt". Der `PlanPhase`-Baum ist
  darüber die primäre, immer offene Ansicht. Reine Darstellungsänderung — keine Funktion
  wurde entfernt oder verändert (siehe Abschnitt 16.18).

---

## 7. Ist-Daten / Tempo

**Datenquelle:** Jira/Tempo-Worklogs (gebuchte Zeit), nicht Ticket-Status. **Kein Personio,
keine HR-Integration.**

- Mapping MA → Jira: `Person.jira_account_id` (Team-Kapazität-Ansicht, `GET
  /jira/lookup-account?query=`).
- Mapping Ticket → Projekt: `projects.jira_component` (Component/Label), auf Projekt- statt
  Teilprojekt-/Phasenebene.
- Sync: `POST /jira/sync` (manuell auslösbar, kein periodischer Scheduler).
- Umrechnung: `Ist_FTE(Monat) = Summe_Stunden / (Wochenstunden_MA × Arbeitswochen_Monat)`,
  `Arbeitswochen_Monat ≈ 52/12`.

**Projekt-Level-Ist funktioniert** (`GET /projects/{id}` liefert `ist` je Monat, `GET
/gap`/`GET /forecast`) und bleibt die alleinige, unveränderte Quelle für diese Endpunkte —
Phase-Mapping ist eine zusätzliche, additive Aufschlüsselung derselben
`jira_worklogs_cache`-Zeilen, kein Ersatz.

**Phase-Level-Ist (P20, siehe
[`P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md`](P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md)):**
Mapping-Kriterium ist **CLOSED** (BD-1A–G) — Jira-Label pro Leaf-Phase (`PlanPhase.jira_label`,
matcht gegen `jira_issue_cache.labels`) mit manuellem Issue-Key-Override
(`worklog_phase_overrides`, höchste Priorität) als Ausnahme. Kein Datum als primäres
Kriterium, keine generische Regelmaschine. **Implementiert (P20.1, Abschnitt 16.19):**
Datenmodell, Sync-Erweiterung (`jira_sync.sync_project` befüllt `jira_issue_cache` beim
gleichen API-Call), Override-CRUD, Konfliktprüfung. **Noch nicht implementiert:** der
eigentliche Worklog→PlanPhase-Resolver (P20.2) und seine Verdrahtung in
`phase_metrics_calc.effort_consumption()`/`PhaseMetricsOut` (P20.4) — `ist_hours`/
`effort_consumption_pct` liefern bis dahin weiterhin konsequent `null`, nie eine
Datumsheuristik oder ein Fake-Ist.

Konfiguration über `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`; ohne diese bleibt der
Sync deaktiviert (`GET /jira/status`), die übrige Planung funktioniert unabhängig davon.

---

## 8. Collaboration & Knowledge

`PlanPhase` ist ein Arbeitskontext:

```
PlanPhase
├── Comments (inkl. Threading über parent_id)
├── Tasks
├── Blockers
├── Decisions
├── Documents
└── Activity (Aggregation der obigen, chronologisch)
```

Alle vier (`Comment`, `Task`, `Blocker`, `Decision`) haben eine nullable `plan_phase_id`
(`ON DELETE SET NULL`) und werden im PlanPhaseWorkspace-Tab "Aktivität" gemeinsam mit dem
Activity Feed gezeigt — bestehende generische Infrastruktur, keine neue Activity-Tabelle.

Comment-Threading (`parent_id`) ist seit P19 auch im Frontend umgesetzt (vorher nur
Backend-Feld, siehe Abschnitt 16.18): `NotesSection.tsx` zeigt Antworten eingerückt unter
ihrem jeweiligen Wurzelkommentar (eine Verschachtelungsebene, unabhängig von der
tatsächlichen `parent_id`-Tiefe).

**"Aus Objekt erstellen":** aus einem Kommentar (oder einer Decision/einem Blocker) kann
über eine kontextuelle Aktion ein fachliches Folgeobjekt entstehen (z. B. `+ Aufgabe`), das
per `EntityRelation(relation_type="resulted_in")` mit dem Ursprung verknüpft wird — keine
neue Source-of-Truth-Spalte für "Origin", `EntityRelation` reicht. Seit P19 ist diese Aktion
direkt in der Kommentarliste (`NotesSection.tsx`) verfügbar, nicht mehr nur im Activity Feed,
und die vorgeschlagenen Tags sind die Vereinigung aus Kommentar-Tags **und** den Tags der
Phase selbst (weiterhin nur Vorschlag, keine harte Vererbung).

**Dokumente:** zentrale Ablage (`documents`/`document_links`), ein Upload-Pfad (`POST
/projects/{id}/documents`, optional `entity_type`+`entity_id` für atomare Verknüpfung). Jede
Datei existiert physisch/als Datensatz genau einmal, unabhängig davon, wo sie hochgeladen
wurde; andere Bereiche referenzieren nur über `document_links`. Der Dateien-Tab von
`PlanPhase` nutzt exakt dasselbe System (kein zweites Attachment-System).

**Tags:** systemweit wiederverwendbar, generische `tag_links`-Verknüpfung
(`entity_type`/`entity_id`, aktuelles Vokabular: `comment`, `decision`, `risk`,
`meeting_minutes`, `task`, `document`, `blocker`, `plan_phase`, `milestone`,
`baseline_snapshot`). Der User darf im normalen Arbeitsfluss: bestehenden Tag suchen, Tag
zuweisen, neuen Tag direkt erstellen (`GET /tags?search=`, Autocreate bei Verwendung) — **keine
Admin-Seite nötig für einen normalen Tag.** Tag-Governance (Kategorie, Beschreibung,
Synonyme, `active`, `ai_relevant`, `ai_description`) bleibt Admin-Funktion
(`/administration`). Keine harte Tag-Vererbung: beim Erstellen eines Blocker/Task aus einem
Kommentar werden dessen Tags nur **vorgeschlagen**, nicht automatisch übernommen.

**Knowledge Layer:** `GET /knowledge/entities`, `/knowledge/search` (Volltext über
Titel/Text **und** Tag-Namen, kein Vector-RAG — bewusst zurückgestellt, Abschnitt 15),
`/knowledge/context` (Wissenskarte einer Entität: Tags+Dokumente+Relationen),
`/knowledge/relations`, `/knowledge/project/{id}` (Aggregation), `/knowledge/tags/dossier`
(Tag-Dossiers, Related Entities über Tag-Overlap-Ähnlichkeit).

---

## 9. Project Control / GAP / Health

**GAP Engine** (`backend/app/gap_calc.py`, `capacity_calc.py`, rein berechnend, keine eigene
Tabelle — `gap_snapshots` existiert, bleibt aber ungenutzt):

| GAP-Typ | Bedeutung | Endpoint |
|---|---|---|
| Allocation Gap | `ResourceDemand.fte − assigned_fte` | Feld auf `ResourceDemandOut` |
| Capacity Gap | Portfolioweiter Kapazitätsbedarf vs. verfügbare Kapazität je Rolle/Periode | `GET /gap-engine/capacity` |
| Effort Gap | Soll/Ist/Gap je Projekt/Monat (unverändert seit Schritt 3) | `GET /projects/{id}/gaps/effort` |
| Schedule Gap | Baseline vs. Forecast **und** Forecast vs. Actual, live (nicht auf einen Planstand angewiesen) | `GET /projects/{id}/gaps/schedule` |
| Progress Gap | Expected Progress (Zeitanteil) minus `PlanPhase.progress` — **rechnerisch weiter verfügbar, aber nicht mehr Teil der Health-Bewertung** (siehe unten) | `GET /projects/{id}/gaps/progress` |
| Utilization Gap | Zugeordnete FTE vs. Available Capacity vs. 100 %-Ziel | `GET /people/{id}/gaps/utilization` |

⚠️ Bekannte, bewusst nicht rückwirkend behobene Inkonsistenz: `allocation_gap` wird an zwei
Stellen mit gegensätzlichem Vorzeichen berechnet (`ResourceDemandOut`/
`PortfolioAllocationGapEntry`: `fte − assigned_fte`, positiv = Unterdeckung; `CockpitCapacity
.allocation_gap_fte`: `assigned_fte − fte`, negativ = Unterdeckung). Bei Erweiterungen an
diesen Stellen prüfen, welche Konvention der jeweilige Call-Site erwartet.

**Health** (`backend/app/health_calc.py`, `GET /projects/{id}/health`): neun Dimensionen —
`overall`, `schedule`, `capacity`, `effort`, `progress`, `risks`, `blockers`, `milestones`,
`customer`, je `{status: gruen|gelb|rot|grau, value, explanation}`. `status="grau"` heißt
"keine belastbare Datenbasis", bewusst von "gruen" unterschieden.

**Progress Health ist grau/nicht belastbar** (seit P6/P11, siehe Abschnitt 16.1):
`_progress_health` liefert dauerhaft `status="grau"` und fließt nicht mehr in `overall` ein —
**keine neue Prozentbewertung erfinden.** `PlanPhase.progress` bleibt als Rohfeld/Endpoint
aus Kompatibilität erhalten, ist aber kein strategischer Kern mehr. 🟢/🟡/🔴-Scoring für die
P2-Phasenmetriken (`plan_hours`, `time_progress_pct`, Reconciliation) ist bewusst noch nicht
gebaut (BD-3) — die Metriken werden aktuell als Rohwerte ohne Ampel gezeigt.

**Cockpit** (`GET /projects/{id}/cockpit`): bündelt Health, Projektleiter, laufende Phase,
Forecast-Ende, Milestones, Kapazität, Blocker-Breakdown, Tasks, Tags — eine Aggregation
bestehender Endpoints.

---

## 10. UI / Workspace

Zwei-Ebenen-Navigation: **Ebene 1 Projektmanagement** (Portfolio-Dashboard →
Projekt-Workspace mit Tab-Leiste) und **Ebene 2 Controlling** (portfolioweite Views). Reine
Navigations-Gruppierung, keine Zugriffskontrolle (kein Rollen-/Login-System im Repo).

### Projekt-Workspace-Tabs

| Tab | Inhalt |
|---|---|
| Übersicht | Cockpit-Aggregation: Health-Ampel, Projektleiter, letzte Änderungen/Notizen, offene Aufgaben |
| **Planung** | PlanPhase-Liste + Drawer, Milestones, Kapazität (Portfolio-Achse), Planstände, Teilprojekt-Verwaltung — siehe unten |
| Kommunikation | Diskussionen, Aufgaben, Entscheidungen, Risiken, Meetingprotokolle (projektweit; phasenbezogene Sicht siehe Planung-Tab-Drawer) |
| Dokumente | Zentrale Dokumentenablage des gesamten Projekts, Suche/Filter, "Verwendet in"-Backlinks |
| Historie | Automatisches Änderungsprotokoll (Audit), nach Datum/Revision (`batch_id`) gruppiert |
| Jira | Sync-Status, Ist-FTE-Tabelle, "Jetzt synchronisieren" |
| Einstellungen | **Projektstammdaten** (Name/Kunde/Startmonat/Anzahl Monate, mit Grund-/Batch-Speichern-Workflow), Projektparameter (Status/Projektleiter), Projektteam/Berechtigungen, Jira-Verknüpfung. **Nicht** hier: PlanPhase-Planung, Kapazitätsplanung, Assignments, Planstände, Tag-Verwendung, Kommentare/Tasks/Blocker/Milestones — das bleibt Planungsarbeit im Planung-Tab. |

### Planung-Tab im Detail

**PlanPhase-Liste:** kompakte, scannbare Karten (Name, Zeitraum "18.08.–29.08.", Status,
Plan-FTE, Owner, Tags, "Öffnen →"-Button), nach Teilprojekt gruppiert. **Keine** sechs
Datumsfelder direkt in der Karte — das war der konkrete UX-Debt-Fund (Screenshot-Symptom),
siehe Abschnitt 16.1. Bearbeitung erfolgt ausschließlich im Drawer.

**PlanPhase anlegen:** `+ Phase hinzufügen` öffnet einen kleinen Create-Dialog (Modal), kein
großes Inline-Formular. Pflicht: Name, Start, Ende. Optional: Status, Teilprojekt, Owner,
Plan-FTE, Tags. Dateien gehören **nicht** ins Create-Formular — sie werden nach dem Anlegen
über den Dateien-Tab des Drawers verwaltet.

**PlanPhase-Workspace (Drawer):** die primäre Detail-/Bearbeitungsoberfläche, vier Tabs
(unverändert seit P19 — P19 ergänzt Inhalte **innerhalb** der Tabs, baut keine neuen):

- **Übersicht** — editierbar: Name, Start/Ende (= "Zeitraum"), Status, Owner, Teilprojekt,
  Tags, Plan-FTE, alles sofort speichernd (kein Batch-/Grund-Workflow, siehe unten).
  Read-only/berechnet: Planstunden, Zeitfortschritt, Ist-Aufwand (aktuell "noch nicht
  eindeutig zugeordnet", BD-1). Sekundär: "Tatsächlicher Verlauf" (Gestartet/Abgeschlossen),
  mit Aktion "Ist-Daten korrigieren" für die seltene manuelle Nachpflege. Header zeigt seit
  P19 den vollen Breadcrumb-Pfad von der Wurzel bis zur aktuellen Phase (klickbare Vorfahren,
  wechselt die im Drawer offene Phase ohne den Drawer zu schließen). Zusätzlich seit P19: eine
  kompakte "Verknüpfte Themen"-Karte (Tags + Entscheidungen-/Blocker-/Dokumente-Counts, aus dem
  bereits geladenen Detail abgeleitet) und, falls ein Planstand existiert, die
  "Seit Planstand VX geändert"-Zeile (Abschnitt 5.3).
- **Kapazität** — Plan-FTE/Planstunden-Kopfzeile, Personenbesetzung (Primärpfad, visuell
  hervorgehoben) + optionale Rollen-Aufschlüsselung (eingeklappt, sekundär) in Fachsprache
  (siehe Abschnitt 6). Seit P19 liefert `PlanPhaseDetail` Assignment-Summary und die
  Assignments je Rolle bereits eingebettet (Round-Trip-Reduktion, kein neuer Endpoint).
- **Aktivität** — Activity Feed (zeigt seit P19 auch Milestone-/Planstand-Ereignisse) +
  Kommentare (inkl. Threading über `parent_id` mit einer Einrückungsebene, "aus Objekt
  erstellen" direkt in der Kommentarliste), Aufgaben, Entscheidungen, Blocker im
  Phasenkontext (Tags dieser drei sind seit P19 nachbearbeitbar). Seit P19 zusätzlich eine
  kompakte Meilensteine-Karte (Leaf und Parent, Abschnitt 5.5).
- **Dateien** — seit P19 dieselbe volle Dokumentenkomponente wie der projektweite
  Dokumente-Tab (Suche, Typ-/Tag-Filter, "Verwendet in"-Backlinks), phasengefiltert statt der
  früheren schwächeren Eigenbau-Liste — ein System, eine Komponente, zwei Filteransichten.

**Speichern-Paradigma:** Der Planung-Tab ist konsequent Sofort-Speichern (jede Änderung im
Drawer/in der Liste wird direkt persistiert) — **kein** globales "Grund für diese
Änderung"-Feld mehr auf diesem Tab. Der Batch-/Grund-Speichern-Workflow
(`PlanHistory.batch_id`, optionaler `kommentar_id`) bleibt als Audit-Trail-Mechanismus
bestehen, ist aber auf die vier Projektstammdaten-Felder im Einstellungen-Tab beschränkt
(siehe P11, Abschnitt 16.1) — dort ändert sich selten mehr als ein Feld auf einmal, ein
expliziter "Speichern"-Klick mit Begründung passt fachlich. Zwei konkurrierende
Speicherparadigmen auf derselben Seite (Planung) wurden damit aufgelöst, ohne den
Audit-Trail-Mechanismus selbst zu entfernen.

**Milestones, Planstände** liegen als eigene, projektweite Karten unterhalb der
PlanPhase-Liste (die seit P19 visuell die primäre, immer offene Karte ist), jeweils mit
Sofort-Speichern. Seit P19 zeigt eine weitere Karte "Projektkapazität nach Monat" die
derived monthly capacity read-only (Balken/Stunden/FTE-Äquivalent je Monat, Klick auf einen
Monat schlüsselt ihn nach beitragender Leaf-PlanPhase auf) — Quelle ist unverändert
`compute_project_monthly_capacity` (Abschnitt 6.6), keine neue Berechnung, keine
Ampel-/Erfüllungsbewertung. Die Legacy-Karten (Teilprojekt-Verwaltung, `ResourceDemandGrid`)
liegen seit P19 gebündelt in einem eingeklappten "Legacy-Kapazitätsplanung"-Block ganz unten
(Abschnitt 6.15) — unverändert funktionsfähig, aber visuell klar sekundär zur
`PlanPhase`-Struktur.

---

## 11. Controlling

Portfolioweite Aggregation über alle Projekte (`backend/app/routers/controlling.py`):
`capacity-heatmap`, `allocation-gaps`, `schedule-gaps`, `progress-gaps`,
`baseline-deviations`, `portfolio-health`, `blockers`, `milestones`, `roles`. Zusätzlich
eigenständige Views: **Forecast** (Hochrechnung Jahresende/Projektende je Projekt),
**Auslastung** (zugeordnete FTE / Available Capacity je Person/Team), **KPIs**
(Portfolio-Kennzahlen), **Reporting** (clientseitiger CSV-Export, `;`-Trennzeichen +
UTF-8-BOM für Excel-DE).

`/jira-projekte` (Jira-Projekt-Katalog) bleibt als eigene, projektübergreifende
Verwaltungsseite außerhalb der zwei Navigations-Ebenen bestehen.

---

## 12. Administration

`/administration`: Personen/Teams (lokal editierbar, extern verwaltete Personen read-only),
Rollen/Permissions (`AppRole`/`Permission`, reine Vorbereitung — kein Auth-System im Repo),
Ressourcenrollen/Skills, Tags/Tag-Kategorien (Governance, siehe Abschnitt 8), Health-Schwellen
(`health_thresholds`), Kapazitätskalender (`Holiday`).

---

## 13. Source-of-Truth-Matrix

| Konzept | Source of Truth | Editierbar wo | Abgeleitet aus | Legacy-Status |
|---|---|---|---|---|
| Projektstammdaten | `Project` | Einstellungen-Tab | — | aktuell |
| Phasen-Termine ("Plan") | `PlanPhase.forecast_start/end` | Planung-Tab → Drawer "Übersicht" | — | aktuell (UI zeigt technischen Begriff "forecast" nicht) |
| Planstand | `BaselineSnapshot`/`BaselineEntry` | Planung-Tab, Aktion "Planstand festhalten" | Snapshot von PlanPhase/Milestone-Feldern zum Zeitpunkt X | aktuell; `PlanPhase.baseline_start/end` sind compat-only, nicht mehr die UX-Quelle |
| Tatsächlicher Verlauf | `PlanPhase.actual_start/end` | Drawer "Übersicht" → "Ist-Daten korrigieren" | — | aktuell, sekundär |
| Plan-Aufwand | `PlanPhase.plan_fte` | Drawer "Übersicht"/Create-Modal | — | aktuell, führend |
| Planstunden | berechnet (`phase_metrics_calc.plan_hours`) | nicht editierbar | `plan_fte` × Werktage × Wochenstunden/5 | aktuell |
| Aufschlüsselung | `ResourceDemand` (mit `plan_phase_id`) | Drawer "Kapazität" | — | aktuell, optional, keine Sync-Pflicht zu `plan_fte` |
| Besetzung | `ResourceAssignment` | Drawer "Kapazität" | — | aktuell |
| Ist-Aufwand (Phase) | — | — | Tempo/Jira, Resolver fehlt noch (P20.2) | Mapping-Kriterium **CLOSED**, Datenmodell **IMPLEMENTIERT** (P20.1, Abschnitt 16.19) — Resolver/Verdrahtung fehlen, liefert bis dahin weiterhin `null` |
| Phase-Jira-Zuordnung | `PlanPhase.jira_label` | Drawer "Übersicht" (Label-Picker folgt in P20.5) | — | **IMPLEMENTIERT (P20.1)**, nur auf Leaf-Phasen, gleicher Lifecycle wie `plan_fte` |
| Worklog-Metadaten-Cache | `jira_issue_cache` | nicht editierbar (Sync-Ergebnis) | Jira-Issue-Suche bei `POST /jira/sync` | **IMPLEMENTIERT (P20.1)** |
| Manuelle Worklog-Zuordnung | `worklog_phase_overrides` | `POST/DELETE .../worklog-overrides` (UI folgt in P20.5) | — | **IMPLEMENTIERT (P20.1)**, ändert nie Jira/Tempo-Originaldaten, höchste Resolver-Priorität sobald P20.2 existiert |
| Zeitfortschritt | berechnet (`phase_metrics_calc.time_progress`) | nicht editierbar | Datumsanteil | aktuell |
| Progress (%) | `PlanPhase.progress` | nirgends (deprecatet) | — | **deprecated**, compat-only |
| Status | `PlanPhase.status`/`Milestone.status` (Freitext) | Drawer/Liste, Zielvokabular in Dropdown | — | aktuell; historische Werte lesbar, siehe Abschnitt 16.1 |
| Tags | `Tag`/`TagLink` | überall wo taggbar | — | aktuell |
| Available Capacity | berechnet (`capacity_calc.compute_person_capacity`) | nicht editierbar | `WorkingTime`/`ResourceProfile` − `Holiday` − `Absence` − `InternalAllocation` | aktuell |
| Gantt-Balken | — | nicht editierbar (read-only Visualisierung) | `PlanPhase.forecast_start/end` | aktuell |
| Grobplanung (Monats-FTE, Alt-Projekte) | `ResourceDemand` mit `plan_phase_id = NULL` | Planning-Tab → `ResourceDemandGrid` | — | **Legacy, aktiv nur bis B-2-Migration** (Abschnitt L6.1 (Historie 17.8)); fließt in die fünf zentralen Portfolio-/Cockpit-/GAP-Endpunkte seit B-5 **nicht mehr** ein (Lücke Abschnitt L6.3 (Historie 17.8) dort strukturell aufgelöst) — zwei sekundäre Auswertungen (Effort-Gap-Track, PPTX-Export) lesen sie weiterhin direkt |
| Grobplanstunden/Feinplanstunden/Konsumption/Konkretisierungsgrad | berechnet (P18 Pass 1-Vorschlag, **superseded**) | nicht editierbar | `ResourceDemand`(Grob)/`PlanPhase.plan_fte`(Fein) × Werktage-Monatsverteilung | **P18 Pass 1 — Design, superseded durch Pass 2** (Abschnitt 6a.3 (Historie 17.7)/6a.6/6a.10), nie implementiert |
| Projektmonatskapazität (unter P18 Pass 2) | berechnet (`capacity_calc.compute_project_monthly_capacity`) | nicht editierbar | `SUM` über `monthly_distribution` aller Leaf-`PlanPhase`s | **P18 Pass 2 — final gelockt, IMPLEMENTIERT, gegen Code CONFIRMED** (Abschnitt 6.6/16.15) |

---

## 14. Open Business Decisions

| ID | Frage | Status |
|---|---|---|
| BD-1 | Tempo/Jira-Worklog → PlanPhase-Mapping: welches Kriterium (Datum, Ticket-Feld, manuelle Zuordnung)? | Kriterium **CLOSED** (siehe BD-1A–G, [`P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md`](P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md) Abschnitt 28) — Label-Match + manueller Issue-Key-Override. Datenmodell + Sync-Erweiterung + Konfliktprüfung sind implementiert (P20.1, Abschnitt 16.19). Resolver (P20.2) und die Metriken-Verdrahtung (P20.4) fehlen noch — `effort_consumption_pct`/`ist_hours` liefern bis dahin weiterhin konsequent `null`, keine Heuristik. |
| BD-3 | Bewertungs-Thresholds für Phasenmetriken (🟢/🟡/🔴 auf `plan_hours`/`time_progress_pct`/Reconciliation)? | offen — Metriken werden aktuell ohne Ampel gezeigt |
| BD-4 | Feiertags-Handling für Planstunden (aktuell Mo–Fr ohne Feiertagsabzug) | offen, dokumentierter Scope-Cut, keine stille Baseline-Änderung |
| BD-5 | `ResourceAssignment` mit Teil-Zeiträumen (Sub-Ranges) statt einer FTE über die ganze Demand-Periode? | offen |
| BD-6 | `allocation_gap`-Vorzeichenkonvention vereinheitlichen (siehe Abschnitt 9, bekannte Inkonsistenz zwischen `ResourceDemandOut` und `CockpitCapacity`) | offen, bewusst nicht rückwirkend angefasst |
| BD-7 | *(P18 Pass 1)* Capacity-Consumption-Formel `max(Grobplanstunden, Feinplanstunden)` (Abschnitt 6a.10 (Historie 17.7))? | **obsolet** — Pass 2 (Abschnitt 6) hat keine zwei Achsen mehr, die reconciliert werden müssten (siehe Pass-2-Dokument Abschnitt 28) |
| BD-8 | *(P18 Pass 1)* Soll `BaselineSnapshot` Grobplanung einfrieren, granular oder aggregiert (Abschnitt 6a.9 (Historie 17.7))? | **obsolet** — unter Pass 2 gibt es nur noch eine Kapazitätsquelle je Phase, kein Granularitäts-Dilemma mehr (Abschnitt 6.9, Pass-2-Dokument Abschnitt 16) |
| BD-9 | *(P18 Pass 1)* Rollout additiv vs. direkt (Abschnitt 6a.13 (Historie 17.7))? | **obsolet** — ersetzt durch die Migrationsreihenfolge in Abschnitt 6.9/Pass-2-Dokument Abschnitt 27 |
| BD-10 | *(P18 Pass 2)* Maximale `PlanPhase`-Hierarchietiefe: 2 oder 3 Ebenen (Abschnitt 6.1)? | **CLOSED — 3 Ebenen.** Backend validiert, Frontend bietet auf Ebene 3 keine weitere Unterphase an (Pass-2-Dokument Abschnitt 9.3/28/35). |
| BD-11 | *(P18 Pass 2)* Löschverhalten einer Parent-Phase mit Kindern: kaskadierend (wie heute bei `Subproject`) vs. blockieren vs. Reparenting? | **CLOSED — Standard-`DELETE` wird blockiert (`409`)**, nicht kaskadierend (**Korrektur** gegenüber der ursprünglichen Pass-2-Empfehlung "kaskadierend"). Reparenting oder eine separate, stark bestätigte "Gesamten Zweig löschen"-Aktion sind die vorgesehenen Wege (Abschnitt 6.9, Pass-2-Dokument Abschnitt 28/35). |
| BD-12 | *(P18 Pass 2)* Migrationsstrategie für bestehende `Subproject`-/Grobplanungs-Daten: automatisiertes Skript vs. manuelle Nachplanung? | **CLOSED — automatisiert, deterministisch, mit Dry-Run und Vorher-/Nachher-Report** (Abschnitt 6.12, Pass-2-Dokument Abschnitt 20/22/28/35). |
| BD-13 | *(P18 Pass 2)* Soll "Konkretisierungsgrad"/Planungsreife als Kennzahl in neuer Form weiterleben oder ersatzlos entfallen (Abschnitt 6.6)? | **CLOSED — ersatzlos gestrichen**, keine Ersatzkennzahl. Der `PlanPhase`-Baum selbst zeigt die Planungstiefe (Pass-2-Dokument Abschnitt 28/35). |

**BD-10 bis BD-13 wurden im Final-Lock-Durchgang (Abschnitt 16.6) geschlossen** — keine der
vier Entscheidungen ist mehr offen. Dieser Durchgang hat geprüft, ob die Schließung neue
fachliche Blocker aufwirft, und **keinen echten neuen Blocker gefunden**: die einzigen
Korrekturen betreffen die konkrete Umsetzung (Parent-`plan_fte`-Lifecycle, Migrationsdetail der
Grobplanung, Rollen-Governance, siehe Abschnitt 6.1a/6.9/6.4/6.12), nicht eine neue offene
Frage. Es wurden bewusst **keine neuen BDs** erzeugt.

**Aufgelöst mit P11 (nicht mehr offen):** Status-Normalisierung (vormals BD-2) — Zielvokabular
Geplant/In Arbeit/Abgeschlossen/Entfällt ist definiert und über eine Frontend-Mapping-Schicht
umgesetzt (Details Abschnitt 16.1). Die Backend-Spalte bleibt bewusst Freitext (keine
destruktive Migration), Governance ist damit vollständig für dieses Konsolidierungsziel.

**Nicht als BD aufgenommen (P18-Audit, weil Code/Analyse bereits eindeutig sind):**
Rollenbedarf/Personen auf der Grobachse (Level 1–3, Abschnitt 6a.5 (Historie 17.7)) — bereits heute technisch
unterschränkt möglich, keine offene Frage. Teilprojekt-scharfe Grobplanung (Abschnitt 6a.11 (Historie 17.7))
— kein identifizierter fachlicher Bedarf, daher keine BD, sondern bewusst außerhalb des
Scopes. Monatsverteilungsschlüssel (Abschnitt 6a.6 (Historie 17.7)) — eindeutig aus bestehender
Werktage-Logik ableitbar, keine offene Frage.

---

## 15. Deferred Features

- Tempo→PlanPhase-Mapping: **Mapping-Domain implementiert (P20.1, Abschnitt 16.19)** —
  Resolver/Coverage/Metriken-Verdrahtung (P20.2–P20.7) bleiben deferred
- `PlanPhase.progress`-Spalte tatsächlich droppen (Schema-Cleanup erst, wenn alle Consumer
  entfernt sind — kein destruktives Cleanup nur für UX)
- `phase_control_status`/🟢🟡🔴-Bewertung der Phasenmetriken (BD-3)
- Snapshot-vs-Snapshot-Vergleich (zwei Planstände direkt gegeneinander)
- Gantt Drag&Drop/Resize als Planungsworkflow
- Milestones im Gantt darstellen
- Automatisches Setzen von `actual_start`/`actual_end` bei Statuswechsel (geprüft, bewusst
  zurückgestellt — Risiko unkontrollierten Überschreibens bestehender Ist-Daten)
- Tag-Merge (Duplikate zusammenführen)
- `ResourceAssignment`-Sub-Ranges (BD-5)
- `allocation_gap`-Vorzeichenkonvention vereinheitlichen (BD-6)
- Vector-/Embedding-basierte Suche (Knowledge Layer nutzt bewusst Tag-Overlap/Volltext)
- Personio/HR-Integration (explizit nicht geplant, Tempo/Jira bleibt die Ist-Quelle)
- Development-/Sales-/Marketing-FTE-Planung (explizit nicht geplant, siehe Abschnitt 2)
- KI Project Agent, automatische Ressourcenoptimierung, What-if/Szenarioplanung,
  Enterprise-SSO (alle Bucket "D", siehe Abschnitt 17.4)
- vollständiger Schema-Drop aller deprecateten Felder (`progress`, `baseline_*` bleiben
  bewusst bestehen, bis alle Consumer entfernt sind)
- großformatige neue Design-System-Einführung
- Planstand-Relations-UX (Planstand ↔ Blocker/Decision/Comment über `EntityRelation`
  verknüpfen) — geprüft in P13.6, keine bestehende generische Auswahl-UX dafür wiederverwendbar,
  nicht künstlich gebaut (siehe Abschnitt 16.3)
- **P18 Pass 1 (Grob-/Feinplanung-Reconciliation, Abschnitt 6a)** — fachlich fertig
  spezifiziert, aber **superseded durch P18 Pass 2** (Abschnitt 6); BD-7/BD-8/BD-9 obsolet.
- **P18 Pass 2 (PlanPhase-only/hierarchische Phasen, Abschnitt 6)** — fachlich **final
  gelockte** Zielarchitektur, BD-10/BD-11/BD-12/BD-13 **CLOSED** (Abschnitt 14). **B-1 bis B-7
  sind implementiert und gegen Code CONFIRMED** (Abschnitt 16.15) — nicht mehr deferred. Die in
  Abschnitt L6.3 (Historie 17.8) dokumentierte Aggregationslücke ist für die fünf zentralen
  Portfolio-/Cockpit-/GAP-Endpunkte **strukturell aufgelöst**. **Deferred bleibt ausschließlich
  B-8 (Legacy Cutover)** — blockiert bis zur produktiven B-2-Migration und dem Schließen der in
  Abschnitt 16.15 gelisteten Einzel-Defekte.

---

## 16. Umsetzungsstand

### 16.1 P1–P11 — Planungs- und Kapazitätskonsolidierung

Konsolidierungsdurchgang, ausgelöst durch die Beobachtung, dass die Planungsoberfläche trotz
bereits existierendem PlanPhase-Drawer (P7) weiterhin einen parallelen, vollständigen
Sechs-Felder-Inline-Editor zeigte (`baseline_*`/`forecast_*`/`actual_*` einzeln editierbar in
jeder Listenkarte) — der Drawer war additiv eingebaut worden, ohne den alten Editor zu
ersetzen. Zusätzlich war CONCEPT.md durch fortlaufendes Anhängen widersprüchlich geworden
(frühe Abschnitte beschrieben die längst abgelöste Excel-1:1-Architektur als aktuell).

- **P1 Migration `0004_planning_consolidation`** (bereits vor diesem Durchgang gemergt):
  additive Spalten `PlanPhase.plan_fte`, `BaselineSnapshot.reason`, `plan_phase_id` auf
  Comment/Task/Blocker/Decision, neuer EntityType `baseline_snapshot`.
- **P2 `phase_metrics_calc.py`** (vorbestehend): `time_progress`, `plan_hours`, `reconcile`,
  `effort_consumption` (liefert bewusst immer `None`, BD-1).
- **P5 Planstand-Tagging** (vorbestehend): `BaselineSnapshot` taggbar.
- **P6 Progress-Deprecation** (vorbestehend): `create_plan_phase` ignoriert `progress`,
  `_progress_health` liefert dauerhaft `grau`.
- **P7 PlanPhase Workspace Frontend** (vorbestehend, in diesem Durchgang erweitert): Drawer
  existierte bereits mit zwei Tabs (Übersicht/Kommunikation, beide **read-only** in
  Übersicht) — in diesem Durchgang auf vier Tabs erweitert (Übersicht **editierbar**,
  Kapazität **neu**, Aktivität, Dateien **neu mit Upload**), siehe Abschnitt 10.
- **P8 Gantt-Visualisierung** (vorbestehend, in diesem Durchgang bereinigt): zeigte bisher
  drei technisch benannte Balken (Baseline/Forecast/Ist) ohne Klick-Interaktion — jetzt ein
  Balken (Forecast = "aktueller Plan"), Klick öffnet den Drawer.
- **P9 Project Settings Cleanup** (vorbestehend, verifiziert clean).
- **P10 Dokumentation** (vorbestehender Durchgang, jetzt durch diesen Konsolidierungsdurchgang
  ersetzt/erweitert — siehe P11 unten).
- **P11 (dieser Durchgang) — Reconciliation:**
  - Backend: `update_plan_phase` ignoriert `progress` jetzt auch im Update-Pfad (vorher nur
    beim Anlegen) — kein Update-Pfad kann `progress` mehr schreiben.
    `baselines._SNAPSHOT_FIELDS["plan_phase"]` friert jetzt zusätzlich `plan_fte` ein.
    `baseline_calc.compute_deviations`/`_parse_date` erweitert, damit auch `plan_fte`
    (numerisch) als Deviation-Eintrag erscheint, nicht nur Datumsfelder (inkl. Fix eines
    dabei gefundenen `TypeError` bei numerischen `current_value`-Werten).
    Zielvokabular für `PlanPhase.status` dokumentiert (`geplant`/`laufend`/`abgeschlossen`/
    `entfaellt`, UI: Geplant/In Arbeit/Abgeschlossen/Entfällt); `entfaellt` neu als gültiger
    Wert, `verzoegert` bleibt als historischer Wert lesbar, **keine** Migration die
    `verzoegert` zu `entfaellt` ummappt (fachlich falsch — Verzögerung ist eine berechnete
    Steuerungsinformation, kein manuell auf "entfällt" gesetzter Status).
  - Frontend: `PlanPhaseList.tsx` — kompletter Sechs-Felder-Inline-Editor entfernt, ersetzt
    durch kompakte Karten (Name/Zeitraum/Status/Plan-FTE/Owner/Tags/"Öffnen"). Create-Flow
    aus großem Inline-Formular in ein Modal (`PlanPhaseCreateModal.tsx`) verschoben.
    `PlanPhaseWorkspace.tsx` — Übersicht jetzt editierbar (vorher komplett read-only),
    "Tatsächlicher Verlauf" als sekundärer Block mit "Ist-Daten korrigieren"-Aktion, zwei
    neue Tabs (Kapazität: `PlanPhaseCapacityTab.tsx`, neu; Dateien: Upload+Löschen, vorher
    nur statische Liste innerhalb "Übersicht"). `PlanPhaseGantt.tsx` — von drei auf einen
    Balken reduziert, `onOpen`-Callback für Klick-zu-Drawer ergänzt. `MilestoneList.tsx` —
    dieselbe Drei-auf-eins-Reduktion für Datumsfelder (`forecast_date` = "Datum",
    `actual_date` sekundär mit Korrektur-Aktion, `baseline_date` nicht mehr angezeigt).
    `plan_fte` in `client.ts` `createPlanPhase`/`updatePlanPhase`-Payload ergänzt (vorher ein
    Bug: das Feld war aus der UI heraus gar nicht schreibbar). Neues Zielvokabular
    `PLAN_PHASE_STATUS_OPTIONS` in `types.ts` (ohne `verzoegert` als Neu-Wahlmöglichkeit,
    siehe oben).
  - Projektstammdaten (Name/Kunde/Startmonat/Anzahl Monate) inkl. des batch-/grund-basierten
    Speichern-Workflows von `ProjectPlanningTab.tsx` nach `ProjectSettingsTab.tsx`
    verschoben — löst den Konflikt zweier Speicherparadigmen auf derselben Seite auf, ohne
    den Audit-Trail-Mechanismus (`PlanHistory.batch_id`) zu entfernen (siehe Abschnitt 10).
  - Verifiziert: Python-Import-/Router-Import-Checks, `check_migrations.py` (Kette intakt,
    kein Drift, Roundtrip sauber), gezielte End-to-End-Prüfung über `TestClient` (Progress-
    Deprecation auf Create **und** Update, `entfaellt`-Status, Planstand friert `plan_fte`
    ein, Deviations liefert FTE-Delta), `npm run build`/`npm run lint` (clean), Playwright-
    Browserprüfung gegen echten Dev-Server (Listenkarte zeigt keine Plan-/Forecast-/
    Ist-Technikfelder, Drawer mit vier funktionierenden Tabs, Create-Modal, Gantt-Klick öffnet
    Drawer, Sofort-Speichern-Rundlauf über Plan-FTE/Status/Ist-Korrektur bestätigt gegen die
    laufende API, Einstellungen-Tab zeigt die umgezogenen Stammdaten).
  - Bewusst nicht angefasst: destruktive Schema-Migration (keine Spalten gedroppt), keine
    neue Chatty-API (alle Kapazitäts-/Planstand-Erweiterungen nutzen bestehende Endpoints),
    kein Tempo→PlanPhase-Mapping (BD-1 bleibt offen), kein 🟢/🟡/🔴-Scoring für Phasenmetriken
    (BD-3 bleibt offen).

### 16.2 Frühere Phasen (Kurzfassung)

Ausführliche historische Beschreibung siehe Abschnitt 17. Kurzfassung des aktuellen Stands:

- **Schritte 1–10** (MVP bis Aufgaben-Datenmodell): Grundfunktionen, inzwischen größtenteils
  durch Phase 17+ und den Legacy Cutover (26.9) technisch abgelöst bzw. ersetzt; fachlich
  weiterhin gültig sind Jira-Integration, Gap-Analyse/Hochrechnung, Team-Kapazität-Konzept
  (jetzt auf Person/ResourceProfile), Kommunikation-Datenmodell (Decisions/Risks/Meeting
  Minutes/Tasks), zentrale Dokumentenablage + Tags.
- **Phase 13–16** (Technisches Fundament, Personen/Organisation, Semantic Knowledge
  Foundation, Activity & Blocker Core): Alembic-Einführung, `Person`/`ResourceProfile`/
  `ProjectMembership`/Permissions-Vorbereitung, Tag-AI-Metadaten + Knowledge Query Layer,
  `Blocker`-Modell + Comment-Threading + Activity Feed.
- **Phase 17–24** (Project Planning Core bis Knowledge Experience): `PlanPhase`/`Milestone`,
  `BaselineSnapshot`, `ResourceDemand`/`ResourceAssignment`, Available-Capacity-Berechnung,
  GAP Engine, Project Health, Controlling-Aggregation, Knowledge-Erweiterungen
  (Tag-Dossiers, Related Entities).
- **Phase 25** (Administration UX): `/administration`-Bündelung bestehender Admin-Endpoints.
- **Phase 26** (Functional Integration, 26.1–26.9): Frontend auf die neuen Modelle
  umgestellt (Person statt Freitext-Owner, PlanPhase/Milestone statt Gantt-Grid,
  ResourceDemandGrid statt FTE-Raster, Cockpit statt einzelner Ampel, Actionable GAPs), mit
  **26.9 Legacy Cutover** als Abschluss: alte Parallelmodelle real entfernt, siehe Abschnitt
  17.3.
- **P1–P11 Planungs-/Kapazitätskonsolidierung:** siehe 16.1.

Alle oben gelisteten Phasen sind vollständig umgesetzt. Nicht umgesetzt: Restaufwand-basierte
Hochrechnung (Variante 2 der Gap-Hochrechnung), Portal-SSO, offene-Jira-Issues-Endpoint für
den Jira-Tab, ein tatsächlicher Excel-Migrationslauf gegen eine echte Bestands-`.xlsm`-Datei,
Portfolio-PPTX-Export.

---

### 16.3 P12–P17 — Planning UX & Workflow Completion (dieser Durchgang)

Konsolidierungsdurchgang auf Basis der bereits vorhandenen Bausteine aus P1–P11 und den
früheren Phasen (Tag-System, Knowledge Layer, ActivityFeed, PlanPhaseWorkspace). Ziel: die
fachlich längst vorhandenen Funktionen im Planung-Tab als EINEN zusammenhängenden Workflow
erlebbar machen, statt technisch getrennte UI-Inseln. Keine neue Architektur, keine neue
Grob-/Feinplanung, kein Tempo-Mapping, kein Gantt-Drag&Drop — reine Vervollständigung
bestehender Endpoints/Komponenten.

- **P12 Tag Experience:** `TagInput` zeigt jetzt explizit zwischen "vorhandener Tag"
  (anklickbare Vorschläge) und "existiert nicht → direkt erstellen" (eigener Hinweis + Button)
  – Backend-Autocreate (`entity_links.sync_tags`) unverändert, reine UX-Klarheit
  (`components/TagInput.tsx`). `TagChip`/`TagDossierPanel` waren bereits vollständig
  (klickbar überall, Dossier bereits nach Entity-Typ gruppiert mit Fachlabels aus
  `entityTypeMeta.ts`) – ergänzt wurde nur `entity_links._ACTIVITY_TIMESTAMP_FIELD["baseline_snapshot"]
  = "created_at"`, damit Planstände auch in der "Aktuelle Lage" eines Tag-Dossiers erscheinen
  (vorher nur in den Counts). `ActivityFeed` bekam einen frontendseitigen Tag-Filter
  (Chips aus den im Feed vorkommenden Tags, kein neuer Endpoint) und zeigt bei "aus Objekt
  erstellen" jetzt die Tags des Ursprungs als abwählbare Vorschläge in einem `TagInput`
  (`components/ActivityFeed.tsx`) – keine harte Vererbung, reine Vorauswahl. Tag-Merge bleibt
  bewusst deferred (unverändert).
- **P13 Planstand Experience:** Das Wort "Baseline" ist aus dem normalen UI entfernt
  (`BaselineList.tsx` komplett neu geschrieben, technische Modell-/Endpointnamen bleiben
  unverändert). Neu: Kopfzeile "Aktueller Plan" mit Erklärung, Versionsnummerierung (V1…Vn
  nach Erstellreihenfolge), "Grund"-Feld beim Festhalten (`BaselineSnapshot.reason` war seit
  P1 im Modell, aber nie in `schemas.py`/im Router exponiert – jetzt auf
  `BaselineSnapshotCreate`/`-Out`/`-Summary` ergänzt und im Frontend sichtbar/editierbar bei
  Erstellung). Neu gebaut: die Vergleichs-UX (`ComparisonPanel` in `BaselineList.tsx`) nutzt
  den bestehenden `GET /projects/baselines/{id}/deviations`-Endpoint (`getBaselineDeviations`
  in `client.ts`, `BaselineDeviation`-Typ in `types.ts`), filtert clientseitig auf tatsächlich
  geänderte Felder (Backend liefert bewusst alle eingefrorenen Felder, auch unveränderte) und
  zeigt nur `forecast_start/-end/-date`→"Start"/"Ende"/"Datum" sowie `plan_fte`→"Plan-Aufwand"
  in Fachsprache – `baseline_start/-end/-date` (compat-only) werden im Vergleich bewusst nicht
  angezeigt, sonst käme der Begriff "Baseline" durch die Hintertür zurück. Snapshot-vs-
  Snapshot-Vergleich bleibt deferred; eine Relations-UI (Planstand ↔ Blocker/Decision/Comment)
  wurde geprüft – es existiert keine generische "Verknüpfen mit …"-UX außerhalb des
  "aus Objekt erstellen"-Musters in `ActivityFeed`, die dafür ohne neue Komponente
  wiederverwendbar wäre; **neu deferred**, siehe unten.
- **P14 Capacity UX:** `PlanPhaseCapacityTab.tsx` zeigt bei Überdeckung (Aufschlüsselung >
  Plan-FTE) jetzt einen klaren Satz ("Aufgeschlüsselter Bedarf liegt X FTE über dem geplanten
  Phasenaufwand. Plan-FTE bleibt führend.") statt einer rohen negativen Zahl – reine
  Darstellung von bereits vorhandenem `reconciliation.open_fte` aus `phase_metrics_calc.py`,
  keine neue Berechnung. Je Rolle wird jetzt zusätzlich "noch unbesetzt X FTE" angezeigt, wenn
  `allocation_gap > 0`. Kartenüberschrift von "Aufwand" auf "Phasenaufwand" präzisiert, mit
  Hinweistext, der explizit von der projektweiten Monatsachse abgrenzt. `ResourceDemandGrid.tsx`
  (Portfolio-/Monatsachse) heißt jetzt "Projektkapazität nach Monat" mit demselben
  Abgrenzungshinweis (P14.5 – zwei Achsen, keine automatische Synchronisierung, unverändert
  zwei getrennte `ResourceDemand`-Populationen über `plan_phase_id`). `ProjectTeamSection.tsx`
  bekam eine Klarstellungszeile "Projektteam ≠ Kapazitätsbesetzung" (P14.4, war UX-seitig
  bereits sauber getrennt, nur nicht erklärt).
- **P15 Milestones/Teilprojekte:** `MilestoneList.tsx` zeigt Milestones jetzt standardmäßig als
  kompakte, scannbare Zeile (Name/Datum/Status/Teilprojekt/Owner/Tags, "◆"-Symbol wie im
  Konzeptbeispiel) statt permanent offener Sechs-Feld-Editoren – Bearbeiten klappt die Felder
  bei Bedarf auf (kein neues Drawer-Bauteil, Inline-Expand reicht für eine einzelne
  Datumsentität). `PlanPhaseList.tsx`/`PlanPhaseGantt.tsx` bekamen einklappbare
  Teilprojekt-Gruppen sowie `PlanPhaseList.tsx` einen Teilprojekt-Filter (beides rein
  frontendseitig, keine neue Backend-Logik) – adressiert P15.4 für Projekte mit vielen
  Teilprojekten.
- **P16 Collaboration & Knowledge:** Beim Erstellen eines Folgeobjekts aus `ActivityFeed`
  (Kommentar/Decision/Blocker → Task/Decision/Blocker/Risk) wird jetzt `plan_phase_id` vom
  Ursprung übernommen, wenn der Feed im Phasenkontext läuft und der Zieltyp die Spalte hat
  (Risk bewusst ausgenommen, hat keine `plan_phase_id`) – vorher wurde dieses Feld schlicht
  nicht gesetzt, ein aus der Phasen-Aktivität heraus erstellter Blocker landete "phasenlos".
  Dabei außerdem gefunden und behoben: `ActivityFeed` lud nur einmal beim Mount, bekam aber
  keine Mitteilung, wenn eine Geschwisterkomponente im selben Tab (NotesSection/TaskList/
  DecisionList/BlockerList/MeetingMinutesList) eine neue Aktivität anlegte – ein frisch
  erstellter Kommentar erschien dadurch nicht im Feed, bis der Drawer neu geöffnet wurde. Fix:
  neuer `refreshToken`-Prop, den `PlanPhaseWorkspace.tsx`/`ProjectCommunicationTab.tsx` bei
  jeder Mutation hochzählen. "Aktuelle Themen" (P16.5) neu als `CurrentTopicsWidget.tsx` im
  Kommunikation-Tab: nutzt `GET /knowledge/project/{id}` für die im Projekt verwendeten Tags
  und je Tag `GET /knowledge/tags/dossier` für die Objektanzahl (keine neue Aggregation im
  Backend, Anzahl Requests durch tatsächlich verwendete Tags begrenzt).
- **P17 Final Review:** `npm run lint`/`npm run build` clean, Python-Import-/
  `check_migrations.py`-Checks clean (kein Schema-Drift, `reason` war bereits im Modell). Ein
  `TestClient`-Skript deckte die Backend-Änderungen ab (Planstand-`reason`-Roundtrip,
  Deviations inkl. `plan_fte`, Tag-Dossier-Aktivität, `plan_phase_id`-Vererbung + Relation).
  Ein Playwright-Lauf gegen den echten Dev-Server (Backend :8000/Frontend :5173) deckte den
  Projektleiter-Flow end-to-end ab: Phase anlegen → öffnen → Plan-FTE ändern → Tag direkt
  erstellen → Kapazitätstab → Kommentar → daraus Blocker (inkl. `plan_phase_id`+Relation) →
  Termin ändern → Planstand festhalten (kein "Baseline"-Wort im UI) → Vergleich zeigt
  Plan-Aufwand-Abweichung → Gantt-Klick öffnet denselben Drawer → Tag-Klick öffnet Dossier →
  Milestone anlegen (15/15 Checks grün). Negativ-Grep über `frontend/src` fand und behob zwei
  zusätzliche Vorkommen technischer Begriffe im normalen UI außerhalb des Planung-Tabs
  (`Utilization.tsx`: "ResourceAssignment" im Beschreibungstext; `ProjectOverviewTab.tsx`:
  "Forecast-Ende" im Cockpit → "Voraussichtliches Projektende").

**Neu deferred (P13.6):** eine generische "Planstand mit Blocker/Decision/Comment verknüpfen"-UX
existiert nicht und wurde nicht künstlich gebaut – es gibt keine saubere bestehende
Relations-Auswahlkomponente außerhalb des kontextgebundenen "aus Objekt erstellen"-Musters in
`ActivityFeed`, die sich ohne neue UI-Bauteile dafür wiederverwenden ließe. `EntityRelation`
bleibt technisch bereits generisch genug (Baseline ist seit je regsitriert in
`entity_links.ENTITY_TYPES`); eine erste UX dafür ist ein sinnvoller eigener nächster Schritt,
kein Blocker für diesen Durchgang.

### 16.4 P18 — Grob-/Feinplanung, Capacity Reconciliation (Design, dieser Durchgang)

**Reiner Design-/Spezifikations-Durchgang — kein Code, keine Migration, keine
Frontend-Änderung.** Auslöser: die bestehende Trennung Portfolio-/Monatsachse
(Grobplanung) vs. Phasenachse (Feinplanung, Abschnitt L6.1 (Historie 17.8)) war technisch korrekt getrennt,
aber fachlich nirgends erklärt — insbesondere fehlte eine Antwort darauf, warum ein
Projektleiter beide pflegt und wie sie zusammenhängen, ohne sich zu addieren.

- **Codebase-Audit:** Modelle (`PlanPhase`, `ResourceDemand`, `ResourceAssignment`,
  `WorkingTime`, `Absence`, `Holiday`, `InternalAllocation`, `BaselineSnapshot`/`-Entry`,
  `Subproject`), Calc-Layer (`phase_metrics_calc.py`, `capacity_calc.py`, `gap_calc.py`,
  `baseline_calc.py`, `constants.py`), Router (`capacity.py`, `planning.py`,
  `controlling.py`, `gap_engine.py`, `health.py`, `real_capacity.py`) und Frontend
  (`ResourceDemandGrid.tsx`, `PlanPhaseCapacityTab.tsx`, `ProjectPlanningTab.tsx`) wurden
  gegen CONCEPT.md Abschnitt 3/5/6/9/13 geprüft. Ergebnis dokumentiert direkt in Abschnitt 6
  (korrigiert/ergänzt um zwei bisher undokumentierte Ist-Zustände: die ungefilterte
  Grob+Fein-Summierung in allen Portfolio-/Cockpit-Aggregationen, Abschnitt L6.3 (Historie 17.8), und die
  Monats-only-Beschränkung von `compute_person_capacity`, Abschnitt L6.2 (Historie 17.8)) sowie in der
  Codebase Validation Matrix im separaten
  [`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md`](P18_DESIGN_AND_IMPLEMENTATION_PLAN.md).
- **Fachliches Zielbild:** Grobplanung/Feinplanung als zwei Konkretisierungsgrade derselben
  Planung (nicht additiv), Planstunden als gemeinsame Vergleichsbasis, werktage-anteiliger
  Monatsverteilungsalgorithmus für phasenübergreifende Zeiträume, Konkretisierungsgrad als
  reine Kennzahl (keine Ampel, kein Fortschritt) — vollständig in Abschnitt 6a
  spezifiziert, inkl. durchgerechnetem Zahlenbeispiel (6a.6).
- **Keine neue Architektur:** Grobplanung bleibt exakt `ResourceDemand` mit
  `plan_phase_id = NULL` (bereits existierend, nur erstmals benannt). Kein neues Feld, keine
  zweite Available-Capacity-Berechnung, keine zweite Planning Engine (Abschnitt 6a.2 (Historie 17.7)). Level
  1–3 der Grobplanungs-Reifegrade (Gesamt-FTE/Rollen/Personen, Abschnitt 6a.5 (Historie 17.7)) sind bereits
  heute ohne Codeänderung nutzbar.
- **Drei neue offene Business Decisions** (Abschnitt 14): BD-7 (Konsumptions-Formel für
  Portfolio-Sichten), BD-8 (Grobplanung Teil eines Planstands?), BD-9 (Rollout-Strategie:
  bestehende Endpoints umstellen vs. additiv neuer Endpoint zuerst). Bewusst **keine** BD für
  Fragen, die Code/Analyse bereits eindeutig beantworten (Abschnitt 14, Liste "nicht als BD
  aufgenommen").
- **Nicht umgesetzt (wartet auf BD-7/8/9):** neuer Endpoint
  `GET /projects/{id}/capacity/reconciliation` (Abschnitt 6a.13 (Historie 17.7)), UI-Block "Planungsstand
  Kapazität" (Abschnitt 6a.14 (Historie 17.7)), `phase_metrics_calc.monthly_distribution()`, Fix der unter
  Abschnitt L6.3 (Historie 17.8) dokumentierten Aggregationslücke, Erweiterung von
  `compute_person_capacity` um Datumsbereich-Unterstützung (Abschnitt 6a.8 (Historie 17.7)).
- Vollständiger Implementierungsplan (Pakete P18.1–P18.n, Abhängigkeitsgraph, Testfälle,
  Rebuild-Safety-Assessment) im separaten
  [`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md`](P18_DESIGN_AND_IMPLEMENTATION_PLAN.md).
- **Status nach 16.5: superseded durch P18 Pass 2.** BD-7/8/9 obsolet, `max()`-Reconciliation
  und der geplante `/capacity/reconciliation`-Endpoint werden nicht mehr umgesetzt.

### 16.5 P18 Pass 2 — PlanPhase-only/hierarchische Phasen (Design, dieser Durchgang)

**Reiner Architekturprüfungs-/Design-Durchgang — kein Code, keine Migration, keine
Frontend-Änderung.** Auslöser: P18 Pass 1 (16.4) beantwortete die Grob-/Feinplanungsfrage
technisch korrekt, warf aber selbst die vorgelagerte Frage auf, ob zwei parallel gepflegte
Kapazitätsachsen überhaupt nötig sind — sichtbar an drei neuen Business Decisions, von denen
zwei explizit mit "ändert heute sichtbare Portfolio-Zahlen" begründet waren.

- **Codebase-Audit:** vollständige Prüfung von `models.py` (alle planungsrelevanten Modelle),
  `routers/{planning,capacity,baselines,controlling,health,gap_engine,projects}.py`,
  `capacity_calc.py`/`phase_metrics_calc.py`, sowie — per Recherche-Agent — des vollständigen
  Planungs-Frontends (`ProjectPlanningTab.tsx`, `PlanPhaseList.tsx`, `PlanPhaseWorkspace.tsx`,
  `PlanPhaseCapacityTab.tsx`, `PlanPhaseGantt.tsx`, `PlanPhaseCreateModal.tsx`,
  `ResourceDemandGrid.tsx`, `MilestoneList.tsx`, `BaselineList.tsx`,
  `ProjectCommunicationTab.tsx`, `PortfolioHealth.tsx`, `types.ts`, `client.ts`). Zentrale
  Befunde: `Subproject` trägt technisch nur `{id, name, reihenfolge}` (kein eigener
  fachlicher Gehalt über eine Namensgruppierung hinaus); `ResourceDemand.resource_role_id` ist
  bereits heute NOT NULL (Rollen-Zwang besteht bereits für die Feinplanung, nicht nur für
  Grobplanung); Löschen eines `Subproject` kaskadiert bereits heute auf seine `PlanPhase`s
  (kein Nullsetzen); im Frontend existiert **keine** rekursive/Tree-UI-Vorlage — echter
  Neubauaufwand für die Baum-Darstellung. Vollständige Matrix im separaten
  [`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)
  Abschnitt 3.
- **Fachliches Zielbild:** `PlanPhase.parent_phase_id` (nullable, self-referencing, max. 3
  Ebenen), Leaf-Phasen tragen Kapazität, Parent-Phasen aggregieren (Summe statt `max()`,
  Abschnitt 6). Kein neues Leaf/Parent-Statusfeld (`has_children` wird berechnet, nicht
  gespeichert). Ersetzt gleichzeitig Grob-/Feinplanung (6a) **und** `Subproject` (5.4).
- **Empfehlung: MOVE TO PLANPHASE-ONLY ARCHITECTURE**, mit vier neuen, bewusst klein
  gehaltenen Business Decisions (BD-10 bis BD-13, Abschnitt 14) — im Unterschied zu Pass 1
  wird **nicht** jede Detailfrage zur BD erhoben; die meisten (Leaf/Parent-Semantik, Rollen-
  Optionalität, Available Capacity, Baseline-Mechanik, Collaboration an Parent-Phasen) sind im
  Audit technisch eindeutig beantwortet.
- **Nicht umgesetzt (wartet auf BD-10–13):** Schema-Erweiterung (`parent_phase_id`,
  `PlanPhase.reihenfolge`, `Milestone.plan_phase_id`), Migration bestehender
  `Subproject`-/Grobplanungs-Daten, Entfernung von `ResourceDemandGrid.tsx`, Baum-UI in
  Liste/Gantt/Workspace.
- Vollständiger Implementierungsplan (Pakete B-1–B-8, Abhängigkeitsgraph, Migrationslogik,
  Rebuild-Safety-Assessment) im separaten
  [`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md).

### 16.6 P18 Pass 2 — Final Architecture Lock & Implementation Planning (dieser Durchgang)

**Reiner Architektur-Freigabe-/Planungsdurchgang — kein Code, keine Migration, keine
Frontend-Änderung.** Auslöser: 16.5 hatte Pass 2 als **empfohlene** Zielarchitektur mit vier
offenen Business Decisions (BD-10–13) hinterlassen. Dieser Durchgang schließt diese vier
Entscheidungen fachlich final, arbeitet drei notwendige Korrekturen gegenüber dem ursprünglichen
Pass-2-Entwurf ein und leitet daraus einen finalen, direkt umsetzbaren B-1–B-8-Implementierungs-
plan ab.

- **BD-10 CLOSED:** Maximale Hierarchietiefe 3 Ebenen, backend-validiert, frontend-begrenzt
  (Abschnitt 6.1).
- **BD-11 CLOSED, mit Korrektur:** Standard-`DELETE` einer Parent-Phase mit Kindern wird
  **blockiert** (`409`), nicht kaskadiert — die ursprüngliche Pass-2-Empfehlung
  ("kaskadierend, analog `delete_subproject`") wurde **revidiert**. Ein kompletter Subtree-
  Delete ist eine separate, stark bestätigte, auditierbare Aktion (Abschnitt 6.9).
- **BD-12 CLOSED:** automatisierte, deterministische Migration mit Dry-Run und
  Vorher-/Nachher-Report (Abschnitt 6.12).
- **BD-13 CLOSED:** "Konkretisierungsgrad" entfällt ersatzlos, keine Ersatzkennzahl.
- **Korrektur 1 — Parent-`plan_fte`-Lifecycle (Abschnitt 6.1a):** Der ursprüngliche Entwurf
  sah eine automatische Reaktivierung des alten `plan_fte`-Werts vor, sobald eine Parent-Phase
  durch Löschen aller Kinder wieder zum Leaf wird. Das wurde als fachlich nicht akzeptabel
  identifiziert (überraschende Reaktivierung historischer Planung) und durch eine
  Historisierungs-/Nullsetzungs-Regel ersetzt (Variante A: `plan_fte → NULL` beim ersten Kind,
  historisiert über eine additive `plan_history.plan_phase_id`-Spalte; keine automatische
  Rückkehr, bewusste Neubestätigung nötig).
- **Korrektur 2 — Migration der Grobplanung (Abschnitt 6.12):** Der ursprüngliche Entwurf sah
  eine einzelne Leaf-Phase "Grobplanung (migriert)" mit `plan_fte = NULL` über den gesamten
  Zeitraum vor. Das widersprach dem Zielprinzip "`plan_fte` ist die operative Source of Truth
  jeder Leaf-Phase". Ersetzt durch: eine Parent-Phase "Grobplanung (migriert)" mit **einer
  Monats-Leaf-Kindphase je migrierter Periode**, deren `plan_fte` einmalig (nur für diesen
  Migrationsschritt, keine neue Laufzeitregel) aus der Summe der bisherigen
  `ResourceDemand.fte`-Werte dieses Monats abgeleitet wird.
- **Korrektur 3 — Rollen-Governance (Abschnitt 6.4):** Die interne System-Rolle "Ohne Rolle"
  wurde um verbindliche Regeln ergänzt (nicht löschbar, im normalen Picker ausgeblendet, nicht
  in Reporting/Skill-Matching als echte Rolle behandelt, UI zeigt sie nie als Rollenlabel).
- **Abschnitt 3 (Kernprinzipien) wurde auf PlanPhase-only umgestellt** — die alten
  Pass-1-Grundsätze (Grob-/Feinplanung als zwei Konkretisierungsgrade, `max()`-Formel) sind
  daraus entfernt und leben ausschließlich noch als Historie in Abschnitt 6a (**superseded**).
- **Kein neuer echter Business-Decision-Blocker gefunden** — die Prüfung, ob das Schließen von
  BD-10–13 neue offene Fragen aufwirft, ergab ausschließlich Umsetzungsdetails (oben), keine
  neue BD.
- Finaler Implementierungsplan (Pakete B-1–B-8 mit Ziel/Scope/Out-of-Scope/DB/Backend/API/
  Frontend/Migration/Tests/Dependencies/Parallelisierung/Risiken/Acceptance
  Criteria/Definition-of-Done je Paket, Abhängigkeitsgraph, Testfälle A–J, Rebuild-Safety-
  Assessment) im separaten
  [`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)
  Abschnitt 35.
- **Status: READY FOR P18 IMPLEMENTATION.** Keine offene Architekturfrage mehr — Pakete B-1,
  B-2, B-7 sind ab sofort ohne weitere Freigabe startbar; B-5 (Datenmigration) ist technisch
  spezifiziert und nicht mehr durch eine offene BD blockiert, sollte aber wie jede
  produktionswirksame Datenmigration erst nach expliziter Umsetzungsfreigabe durch das Team
  ausgeführt werden (kein automatischer Trigger durch diesen Dokumentations-Durchgang).

### 16.7 P18 Implementierung — B-1 Hierarchy Domain Foundation (dieser Durchgang)

**Erstes Umsetzungspaket der PlanPhase-only-Zielarchitektur (Abschnitt 6), Validation Gate
bestanden.** Rein additive Schema-Grundlage, exakt wie in Abschnitt 6.1/6.1a/6.8 und
Pass-2-Dokument Abschnitt 35.5 (Paket B-1) spezifiziert — bewusst **ohne** jede
Backend-Logik, API-Änderung oder Datenmigration (folgt in B-2/B-3/B-4/B-5):

- Neue Alembic-Revision `0005_p18_hierarchy_foundation` (additiv, `check_migrations.py` grün:
  Kettenintegrität, Upgrade base→head, kein Drift zu `models.py`, Seeds vollständig,
  Downgrade/Upgrade-Roundtrip sauber).
- `PlanPhase.parent_phase_id` (self-referencing FK, nullable, indiziert) und
  `PlanPhase.reihenfolge` (Integer, NOT NULL, default 0) — Grundlage der Hierarchie
  (Tiefenvalidierung ≤ 3 Ebenen und Zyklenprüfung folgen als Backend-Guard in B-3).
- `Milestone.plan_phase_id` (nullable FK, `ON DELETE SET NULL`, indiziert) — ersetzt
  `subproject_id` fachlich (Abschnitt 6.8); `subproject_id` bleibt compat-only bestehen.
- `PlanHistory.plan_phase_id` (nullable FK, `ON DELETE SET NULL`, indiziert) — Voraussetzung
  für die in Abschnitt 6.1a spezifizierte Historisierung des `plan_fte`-Werts beim
  Leaf→Parent-Übergang (Schreibpfad folgt in B-3).
- `ResourceRole.is_system_role` (Boolean, NOT NULL, default false) + Seed-Zeile "Ohne Rolle"
  (`is_system_role = true`, einmalig per Migration angelegt) — technische Trägerschicht für
  die in Abschnitt 6.4 spezifizierte direkte Personenzuordnung ohne erzwungene Rollenauswahl.
  Governance-Regeln (nicht löschbar, im normalen Rollen-Picker ausgeblendet, kein
  Skill-Matching, keine eigenständige Rolle in Reporting/Controlling) sind mit diesem Flag
  technisch möglich, werden aber **noch nicht** durchgesetzt — das ist Backend-Scope von B-3/B-4.
- `check_migrations.py` um eine Seed-Verifikation ergänzt (Systemrolle "Ohne Rolle" existiert
  nach jedem Rebuild genau einmal).
- **Keine Verhaltensänderung an bestehenden Endpunkten** — alle neuen Spalten sind bislang
  ungenutzt (kein Router liest/schreibt sie), Regressionsrisiko minimal.
- **Nächstes Paket:** B-2 (Migration Tooling, Dry-Run-Skript) und B-3 (Phase Tree API) —
  siehe Pass-2-Dokument Abschnitt 35.5.

### 16.8 P18 Implementierung — B-2 Migration Tooling (dieser Durchgang)

**Zweites Umsetzungspaket, Validation Gate bestanden.** Neues, eigenständiges Skript
`backend/scripts/migrate_to_planphase_hierarchy.py` (kein Alembic-Bestandteil, reine
Datenmigration) — setzt B-1 voraus, **noch keine Ausführung gegen Produktivdaten** (siehe
Abschnitt 6.12/BD-12, Pass-2-Dokument Abschnitt 35.5 Paket B-2):

- **Sicherheitsdefault:** Ohne `--apply` läuft das Skript ausschließlich als Dry-Run —
  alle Änderungen werden berechnet und reportet, danach steht ein expliziter Rollback (keine
  Zeile geschrieben). Nur `--apply` committet wirklich. Kein automatischer Produktivlauf.
- **Subproject-Migration** (Abschnitt 6.7/Pass-2-Dokument Abschnitt 22): pro `Subproject`
  eine neue Top-Level-Parent-`PlanPhase` (`phase_type = Subproject.name`,
  `reihenfolge = Subproject.reihenfolge`), bestehende `PlanPhase`-Kinder reparented
  (`parent_phase_id`), `Milestone`/`Comment` umgehängt (`plan_phase_id`).
  `subprojects`/`subproject_id` bleiben unverändert bestehen (compat-only).
- **Grobplanungs-Migration** (Abschnitt 6.12, korrigierte Monats-Leaf-Strategie): pro
  Projekt mit `ResourceDemand(plan_phase_id IS NULL)`-Zeilen eine neue Parent-Phase
  "Grobplanung (migriert)" + eine Monats-Leaf-Phase je distinkter Periode, `plan_fte` der
  Leaf-Phase einmalig aus `SUM(ResourceDemand.fte)` dieser Periode abgeleitet (keine neue
  Laufzeitregel — danach gilt wieder uneingeschränkt "`plan_fte` ist führend").
  `ResourceAssignment` bleibt unberührt (hängt nur an `resource_demand_id`).
- **Idempotenz:** beide Migrationszweige filtern auf "noch nicht reparented/relinked"
  (`parent_phase_id`/`plan_phase_id IS NULL`) bzw. "noch offene Grobplanungs-Demands" — ein
  zweiter Lauf gegen bereits migrierte Daten findet nichts mehr und legt keine doppelten
  Phasen an.
- **Report:** je Projekt Subprojects/Grobplanung migriert, reparented/relinked-Zählungen,
  FTE-Summen vorher/nachher, verwaiste `ResourceDemand`-Zeilen danach (Soll: 0),
  Milestones vorher/nachher — plus ein globaler Hierarchietiefe-/Zyklus-Check über den
  gesamten `PlanPhase`-Bestand (BD-12-Report-Anforderungen).
- **Verifikation:** `backend/scripts/test_migrate_to_planphase_hierarchy.py` (kein pytest im
  Repo, analog zu `check_migrations.py` als Muster für eigenständige Prüfskripte) — baut eine
  Wegwerf-SQLite-DB, seedet einen repräsentativen Testfall (1 Subproject mit 2 Kindphasen,
  Milestone, Comment; 2 Grobplanungsperioden mit je 2 Rollen, 1 Assignment) und prüft: Dry-Run
  schreibt nichts, Apply verliert keine Milestones/Comments/Assignments/ResourceDemands, keine
  verwaisten Demands danach, Re-Run nach Apply ist idempotent (kein doppelter Report-Eintrag,
  keine doppelten Phasen). Alle Prüfungen grün.
- **Keine Verhaltensänderung an bestehenden Endpunkten, keine Ausführung gegen echte
  Projektdaten** — reines, verifiziertes Werkzeug. Die tatsächliche Ausführung gegen
  Produktivdaten erfordert eine gesonderte Freigabe außerhalb dieses Pakets (B-2 Definition of
  Done, unverändert).
- **Nächstes Paket:** B-3 (Phase Tree API: CRUD-Guards, Baum-Payload, Löschguards gemäß
  BD-11) — siehe Pass-2-Dokument Abschnitt 35.5.

### 16.9 P18 Implementierung — B-3 Phase Tree API (dieser Durchgang)

**Drittes Umsetzungspaket, Validation Gate bestanden.** Erstes Paket mit echter
Backend-Logik/API-Verhaltensänderung — `PlanPhase.parent_phase_id` ist jetzt operativ
wirksam (CONCEPT.md Abschnitt 6.1/6.1a/6.3/6.9, Pass-2-Dokument Abschnitt 35.5 Paket B-3):

- Neues Modul `backend/app/planning_calc.py`: `has_children`, `direct_children`, `depth_of`,
  `all_descendants`, `leaf_descendants`, `subtree_max_depth`, `derive_parent_bounds`,
  `derive_parent_capacity` — reine, lesende Aggregationsfunktionen, kein neues Statusfeld
  (Leaf/Parent bleibt query-seitig berechnet).
- **CRUD-Guards** (`_check_parent_phase` in `routers/planning.py`): projektfremder Parent
  (`422`), Selbst-Parent (`422`), Zyklus — auch bei Reparenting eines ganzen Teilbaums, nicht
  nur der einzelnen Phase (`422`), maximale Hierarchietiefe 3 Ebenen inkl. der Höhe eines
  bereits vorhandenen eigenen Teilbaums (`422`, BD-10).
- **Leaf→Parent-Übergang** (`_maybe_historize_parent_fte`): sobald eine Phase ihr erstes Kind
  erhält (per `POST .../plan-phases` oder `PUT /plan-phases/{id}`), wird ihr `plan_fte`
  serverseitig auf `NULL` gesetzt und der alte Wert in `PlanHistory`
  (`bereich="phase_struktur"`, `plan_phase_id` gesetzt) historisiert — keine automatische
  Reaktivierung beim Rückweg (Abschnitt 6.1a). `PlanHistoryOut`/`GET
  /projects/{id}/history` geben `plan_phase_id` jetzt mit aus (kleine, additive Erweiterung,
  nötig um die Historisierung überhaupt beobachtbar zu machen).
- **Löschguard** (BD-11, CLOSED): Standard-`DELETE /plan-phases/{id}` einer Phase mit Kindern
  liefert `409` mit `{child_count, message}` statt zu kaskadieren.
- **Neu:** `POST /plan-phases/{id}/reparent-children` (Kinder auf einen anderen Parent oder
  Top-Level verschieben, danach ist die Phase leaf und normal löschbar).
- **Neu:** `GET /plan-phases/{id}/subtree-impact` (Vorschau: Anzahl Nachfahren, betroffene
  Comments/Tasks/Blocker/Decisions/Milestones/Documents/ResourceDemands/ResourceAssignments)
  und `POST /plan-phases/{id}/delete-subtree` (separate, stark bestätigte Aktion — verlangt
  `confirm_phase_type`/`confirm_descendant_count` exakt passend zur aktuellen Impact-Zahl,
  sonst `422`). Löscht Nachfahren-Phasen inkl. ihrer `ResourceDemand`/`ResourceAssignment`-
  Zeilen; Collaboration-Inhalte (Comment/Task/Blocker/Decision/Milestone) werden **nicht**
  gelöscht, nur entkoppelt (`plan_phase_id → NULL`, wie beim bestehenden Einzel-Delete);
  auditiert über einen `PlanHistory`-Eintrag (`bereich="phase_subtree_delete"`).
- **`PlanPhaseOut`/`PlanPhaseDetail` erweitert:** `parent_phase_id`, `reihenfolge`,
  `has_children`, `derived_forecast_start`/`derived_forecast_end`/`derived_capacity` (nur bei
  `has_children=true` befüllt, abgeleitet aus Leaf-Nachfahren, nie aus einem eigenen Feld der
  Parent-Phase); `PlanPhaseDetail.children` (direkte Kinder, für die Baum-UI in B-6).
- **Verifikation:** `backend/scripts/test_planning_phase_tree_api.py` (TestClient gegen die
  echte FastAPI-App, kein pytest im Repo) — prüft alle sieben oben genannten Punkte plus
  subtree-impact/delete-subtree inkl. Assignment-/Comment-Erhalt. Alle Prüfungen grün,
  `check_migrations.py` weiterhin grün (keine Schema-Änderung in diesem Paket).
- **Noch nicht in Scope:** Direct-Assignment-UX ohne Rollenzwang, Available Capacity über
  Zeiträume (B-4); Monatsaggregation/Portfolio-Cutover (B-5); Frontend (B-6/B-7).
- **Nächstes Paket:** B-4 (Capacity/Assignment Simplification: direkte Personenzuordnung ohne
  Rollenzwang über die interne Systemrolle "Ohne Rolle", `compute_person_capacity_for_range`)
  — siehe Pass-2-Dokument Abschnitt 35.5.

### 16.10 P18 Implementierung — B-4 Capacity/Assignment Simplification (dieser Durchgang)

**Viertes Umsetzungspaket, Validation Gate bestanden** (CONCEPT.md Abschnitt 6.4/6.5/6.10/
6.11, Pass-2-Dokument Abschnitt 35.5 Paket B-4):

- **`capacity_calc.compute_person_capacity_for_range(db, person_id, range_start, range_end)`**
  (neu): bereichsbasierte Erweiterung von `compute_person_capacity` — keine neue Holiday-/
  Absence-/InternalAllocation-Query, jeder überlappte Kalendermonat ruft die bestehende
  Funktion unverändert auf und wird nur werktage-anteilig gewichtet (identische Konvention
  wie die Monatsverteilung, BD-4-konform). Neues Schema `PersonCapacityRangeOut`, neuer
  Endpoint `GET /people/{id}/capacity-range?start=&end=`.
- **Direct Assignment ohne Rollen-Zwang** (`routers/planning.py`): `POST
  /plan-phases/{id}/assign-person` ordnet eine Person direkt zu, ohne dass eine Rolle gewählt
  werden muss — legt dafür transparent (idempotent, genau einmal je Phase) eine
  `ResourceDemand` mit der internen Systemrolle "Ohne Rolle" an (`_get_or_create_system_role`/
  `_get_or_create_carrier_demand`). `DELETE
  /plan-phases/{id}/assign-person/{person_id}` entfernt nur diese direkte Zuordnung, rührt
  eine etwaige echte Rollen-Aufschlüsselung nicht an. Beide Endpunkte lehnen Parent-Phasen
  (`has_children=true`) mit `422` ab — Kapazität/Assignments sind Leaf-only (Abschnitt 6.3).
- **Bedarf/Besetzt/Offen** (`phase_metrics_calc.assignment_summary`, neu, + `GET
  /plan-phases/{id}/assignment-summary`): `plan_fte` bleibt immer der Bedarf, `assigned_fte`
  ist die Summe **aller** `ResourceAssignment.fte` über alle `ResourceDemand`s der Phase
  (Systemrolle UND echte Rollen-Aufschlüsselung zählen gleichermaßen), `open_fte` kann negativ
  sein (Überbesetzung wird angezeigt, nicht verhindert) — `plan_fte` wird dabei **nie**
  automatisch erhöht (Kernprinzip, Abschnitt 3/6.10, exakt das Zahlenbeispiel aus Abschnitt 8
  der Aufgabenstellung nachgestellt und verifiziert: 0,40/0,20/0,20 → 0,40/0,50/−0,10).
- **`GET /plan-phases/{id}/assignment-candidates`** (neu): wie die bestehenden
  `resource-demands/{id}/candidates`, aber Available Capacity über den **gesamten**
  Phasenzeitraum geprüft (`compute_person_capacity_for_range`) statt nur einen Monats-Bucket;
  schließt bereits zugeordnete Personen aus (Systemrolle + echte Rollen-Demands gemeinsam).
- **Rollen-Governance** (Abschnitt 6.4/35.3, Teilumsetzung): `GET /resource-roles` blendet
  die Systemrolle standardmäßig aus (`include_system_roles=true` als expliziter Opt-in).
  Skill-Matching-Filterung existiert für **keine** Rolle im heutigen Code (`candidates`
  filtert nie nach Skill, zeigt sie nur informativ an) — die Governance-Regel "kein
  Skill-Matching für die Systemrolle" ist damit strukturell bereits erfüllt, ohne
  Code-Änderung. **Noch offen (bewusst nicht in diesem Paket):** `GET /controlling/roles`
  filtert die Systemrolle noch nicht explizit aus der Rollenauswertung heraus — das ist eine
  reine Reporting-Kosmetik ohne Auswirkung auf Kapazitätszahlen und wird mit B-5
  (Monatsaggregation/Portfolio-Cutover) mit erledigt, da beide denselben Router
  (`controlling.py`) berühren.
- **Verifikation:** `backend/scripts/test_direct_assignment_and_capacity_range.py`
  (TestClient-Integrationstest) — prüft Range-Capacity über eine Monatsgrenze (inkl. exakter
  Nachrechnung der werktage-anteiligen Gewichtung, nicht nur ein Toleranzband), Rollen-Picker-
  Filterung, idempotente Carrier-Demand, Bedarf/Besetzt/Offen inkl. Überbesetzung, Parent-
  Block, Candidates-Ausschluss. Alle Prüfungen grün, `check_migrations.py`/B-2/B-3-Skripte
  weiterhin grün (keine Schema-Änderung in diesem Paket).
- **Nächstes Paket:** B-5 (Monthly/Portfolio Capacity Cutover: `compute_project_monthly_
  capacity`, Anschluss an Controlling/GAP/Cockpit — blockiert produktiv erst nach
  ausgeführter B-2-Migration) — siehe Pass-2-Dokument Abschnitt 35.5.

### 16.11 P18 Implementierung — B-5 Derived Monthly & Portfolio Capacity (dieser Durchgang)

**Fünftes Umsetzungspaket, Validation Gate bestanden** (CONCEPT.md Abschnitt 6.6, Abschnitt
13 der Aufgabenstellung — bewusst NICHT "Monthly Planning" genannt, Pass-2-Dokument Abschnitt
35.5 Paket B-5). **Wichtig:** produktiv wirksam wird der Cutover erst, nachdem B-2 tatsächlich
gegen die Zieldaten ausgeführt wurde (noch nicht geschehen) — bis dahin können in einer
Produktiv-DB weiterhin `ResourceDemand(plan_phase_id IS NULL)`-Zeilen existieren, die von den
unten beschriebenen Endpunkten schlicht nicht mehr gelesen werden (kein Fehler, aber auch
keine Berücksichtigung mehr — Grund, warum B-2 zuerst ausgeführt werden muss).

- **`phase_metrics_calc.monthly_distribution(plan_fte, forecast_start, forecast_end) ->
  dict[str, float]`** (neu): werktage-anteilige Monatsverteilung der Planstunden einer Phase,
  1:1 nach der in Abschnitt 6a.6 (Historie 17.7) spezifizierten und jetzt verifizierten Formel (kein
  Feiertagsabzug, kein 50/50-Split).
- **`capacity_calc.compute_project_monthly_capacity(db, project_id, periods=None) ->
  dict[str, float]`** (neu): Summe von `monthly_distribution` über **alle** `PlanPhase`s des
  Projekts, in Stunden. Kein explizites Leaf-Filtering nötig — eine Parent-Phase trägt nach
  dem B-3-Lifecycle immer `plan_fte=None` und liefert damit automatisch `{}` bei
  `monthly_distribution`, ohne eigenen Beitrag zur Summe. **Das ist jetzt die einzige
  Berechnungsquelle für "Projektkapazität(Monat)"** — kein `ResourceDemand`-Summenmodell mehr.
- **`GET /projects/{id}/capacity/monthly?periods=`** (neu, additiv): read-only Auswertung
  (Stunden + FTE-Äquivalent je Monat), UI-Label "Projektkapazität" — kein Eingabefeld, kein
  `ResourceDemandGrid`-Ersatz. Default-Zeitraum aus `Project.start_monat`/`anzahl_monate`.
- **`GET /projects/{id}/cockpit` (Capacity-Block)**: `demand_fte` kommt jetzt ausschließlich
  aus `compute_project_monthly_capacity` (verifiziert: eine bewusst falsche
  `ResourceDemand.fte` im aktuellen Monat verändert das Ergebnis nicht mehr). `assigned_fte`
  bleibt unverändert die Summe der `ResourceAssignment.fte` (Personenauslastung ist ein
  eigenes, von `plan_fte` unabhängiges Konzept, Abschnitt 6.10/Abschnitt 15 der
  Aufgabenstellung — Projektbedarf ≠ Personenbelegung, beide Werte dürfen auseinanderlaufen).
- **`capacity_calc.compute_capacity_gap`** (Portfolio-GAP, genutzt von `GET
  /gap-engine/capacity` und `GET /controlling/capacity-heatmap`): ohne `resource_role_id`
  kommt die Bedarfsseite jetzt aus `compute_portfolio_planphase_demand_fte` (Summe der
  PlanPhase-abgeleiteten Kapazität über alle Projekte, als FTE-Äquivalent) statt aus einer
  `ResourceDemand`-Summe. Ein gesetzter `resource_role_id`-Filter bleibt bewusst auf der
  optionalen Rollen-Aufschlüsselung (`ResourceDemand`) — Rolle ist keine Dimension der
  PlanPhase-Kapazität (Abschnitt 6.4), das ist die einzige Stelle, an der Rolleninformation
  überhaupt existiert.
- **Rollen-Governance vervollständigt** (Rest von Abschnitt 6.4/35.3, nach der in B-4
  offengelassenen Lücke): `GET /controlling/allocation-gaps` und `GET /controlling/roles`
  blenden die interne Systemrolle "Ohne Rolle" jetzt aus — sie erscheint nicht mehr als
  eigenständige, gleichwertige Rolle neben echten Rollen wie "Senior Consultant".
- **Bewusst NICHT verändert:** Response-Schemas der bestehenden Endpunkte
  (`CapacityGapOut`/`PortfolioAllocationGapEntry`/`RoleAnalysisEntry`/`CockpitCapacity`) —
  nur die Berechnung dahinter wechselt, keine neue API-Landschaft (B-5-Vorgabe).
- **Verifikation:** `backend/scripts/test_derived_monthly_capacity.py` — prüft
  `monthly_distribution` exakt gegen das vollständig durchgerechnete Red-Bull-WMS-Beispiel aus
  Abschnitt 6a.6 (Historie 17.7) (112,0 h Oktober / 160,0 h November), `compute_project_monthly_capacity`
  inkl. Parent-Ignoranz, den neuen Endpoint, den Cockpit-Cutover (inkl. Beweis, dass die alte
  `ResourceDemand`-Summe nicht mehr einfließt) und die Rollen-Governance. Alle Prüfungen
  grün, `check_migrations.py`/B-2/B-3/B-4-Skripte weiterhin grün (keine Schema-Änderung in
  diesem Paket).
- **Nächstes Paket:** B-6 (PlanPhase Tree UX: Baum-UI in Liste/Gantt/Workspace, Löschverhalten
  gemäß BD-11 in der UI) — größtes verbleibendes Frontend-Einzelpaket, siehe Pass-2-Dokument
  Abschnitt 35.5.

### 16.12 P18 Implementierung — B-6 PlanPhase Tree UX (dieser Durchgang)

**Sechstes Umsetzungspaket, Validation Gate bestanden.** Erstes Frontend-Paket — verdrahtet
B-1–B-5 erstmals sichtbar in die Bedienoberfläche (CONCEPT.md Abschnitt 6, Pass-2-Dokument
Abschnitt 35.5 Paket B-6):

- **`PlanPhaseList.tsx`/`PlanPhaseGantt.tsx`:** von Teilprojekt-Gruppierung auf echte
  Baum-Darstellung nach `parent_phase_id` umgestellt (rekursiv, max. 3 Ebenen, BD-10) —
  Collapse/Expand pro Sammelphase, "+ Unterphase hinzufügen" pro Zeile (ausgeblendet auf
  Ebene 3). Eine Sammelphase (`has_children`) zeigt `derived_forecast_start/end`/
  `derived_capacity` ("abgeleitet"/"aggregiert") statt editierbarer eigener Werte; im Gantt
  ein umrandeter Summary-Balken statt eines gefüllten Leaf-Balkens.
- **`PlanPhaseCreateModal.tsx`:** "Übergeordnete Phase"-Select ersetzt das bisherige
  "Teilprojekt"-Select als primären Strukturierungs-Mechanismus (`subproject_id` bleibt im
  Modell compat-only bestehen, aber keine neue Bedienoberfläche dafür) — Ebene-3-Phasen
  werden aus der Auswahl gefiltert (Frontend-Vorfilterung, Backend validiert unabhängig
  davon verbindlich).
- **`PlanPhaseWorkspace.tsx`:** zeigt "Übergeordnete Phase"-Breadcrumb, "+ Unterphase"-Aktion
  (tiefenbegrenzt), verzweigt Zeitraum/Kapazität-Anzeige und den Kapazität-Tab auf
  Leaf-vs-Parent (Parent: read-only aggregierte Ansicht, keine Assignments — Abschnitt 6.3).
- **`PlanPhaseCapacityTab.tsx`:** komplett neu strukturiert nach Abschnitt 5 — **primär**
  Direct-Assignment-UX ("Personenbesetzung", `[+ Mitarbeiter zuweisen]` ohne Rollenzwang,
  zeigt Available Capacity über den Phasenzeitraum vor dem Zuweisen sowie
  Bedarf/Besetzt/Offen danach), die bestehende Rollen-Aufschlüsselung bleibt als
  eingeklappter, explizit optionaler Zusatzabschnitt "Rollen aufschlüsseln (optional)"
  bestehen — nie Voraussetzung für eine normale Personenzuweisung.
- **`PlanPhaseDeleteDialog.tsx`** (neu): setzt BD-11 in der UI um — Standard-Löschen zeigt bei
  `409` einen Blockier-Dialog mit "Unterphasen auf Top-Level verschieben, dann löschen" und
  "Gesamten Zweig löschen …" (mit Impact-Anzeige aus `subtree-impact` und
  Namens-Bestätigung), nie eine stille Kaskade.
- **`api/client.ts`/`types.ts`:** neue Typen/Endpunkte für alle B-3/B-4/B-5-Schnittstellen
  (`reparentPlanPhaseChildren`, `getPlanPhaseSubtreeImpact`, `deletePlanPhaseSubtree`,
  `getPlanPhaseAssignmentSummary`, `assignPersonToPlanPhase`,
  `unassignPersonFromPlanPhase`, `getPlanPhaseAssignmentCandidates`,
  `getPersonCapacityRange`, `getProjectMonthlyCapacity`); `tryDeletePlanPhase` gibt den
  409-Fall als typisiertes Ergebnis statt als geworfene Exception zurück, damit der
  Blockier-Dialog sauber angezeigt werden kann.
- **Verifikation:** manueller Browser-Durchlauf (Backend + Vite-Dev-Server lokal gestartet,
  Chromium-Smoke-Test) — Baum anlegen (Top-Level + Unterphase, Sammelphase zeigt
  abgeleitete Werte korrekt), Direct Assignment inkl. Available-Capacity-Vorschau und
  Bedarf/Besetzt/Offen (auch Überbesetzung), BD-11-Blockier-Dialog bei Löschversuch einer
  Sammelphase — alles wie spezifiziert. `npx tsc -b` und `npx oxlint` clean. Kein
  automatisierter Playwright-Testlauf in diesem Paket (im Repo bislang keine
  Playwright-Infrastruktur vorhanden) — das Aufsetzen eines dauerhaften E2E-Test-Setups ist
  ein eigenständiges Vorhaben, hier bewusst nicht mit-erledigt; die B-3/B-4/B-5
  Backend-Skripte und dieser manuelle Durchlauf sind der aktuelle Verifikationsstand.
- **Bewusst unverändert in diesem Paket:** `ResourceDemandGrid.tsx` (Grobplanungs-UI) und die
  Subproject-Verwaltung in `ProjectPlanningTab.tsx` bleiben bestehen (Legacy-Cutover ist
  B-8); `MilestoneList.tsx` nutzt weiterhin `subproject_id` (Migration auf `plan_phase_id`
  ist B-7).
- **Nächstes Paket:** B-7 (Gantt/Milestone/Planstand Integration: `Milestone.plan_phase_id`
  operativ in Router+UI, Baseline friert Baumstruktur ein) — siehe Pass-2-Dokument
  Abschnitt 35.5.

### 16.13 P18 Implementierung — B-7 Gantt/Milestone/Planstand Integration (dieser Durchgang)

**Siebtes Umsetzungspaket, Validation Gate bestanden** (CONCEPT.md Abschnitt 6.8/6.14,
Pass-2-Dokument Abschnitt 35.5 Paket B-7):

- **`Milestone.plan_phase_id` ist jetzt operativ** (Router + UI): `POST`/`PUT
  /projects/{id}/milestones` nehmen `plan_phase_id` statt `subproject_id` als primäre
  Verknüpfung entgegen (neuer Guard `_check_milestone_plan_phase` — Projekt-Grenze, aber
  **keine** Hierarchie-Validierung, da ein Milestone bewusst sowohl an eine Leaf- als auch an
  eine Parent-Phase gehängt werden darf, Abschnitt 6.8). `subproject_id` bleibt
  compat-only im Modell bestehen.
- **`_SNAPSHOT_FIELDS`/`DEVIATION_FIELDS` erweitert** (`baseline_calc.py`/`routers/
  baselines.py`): ein Planstand friert jetzt zusätzlich `PlanPhase.parent_phase_id`/
  `reihenfolge` und `Milestone.plan_phase_id` ein — additiv, keine Schemaänderung nötig
  (`BaselineEntry` ist generisch genug). `parent_phase_id`/`plan_phase_id` sind zusätzlich
  als sichtbare Deviation registriert (`reihenfolge` bewusst nicht — reine Sortierposition
  ist keine fachlich sichtbare Abweichung).
- **`MilestoneList.tsx`:** "Übergeordnete Phase"-Select ersetzt das "Teilprojekt"-Select
  (lädt `PlanPhase`s selbst über `listPlanPhases`, analog zu `PlanPhaseList.tsx`).
- **`BaselineList.tsx`:** neue Feldbeschriftung "Übergeordnete Phase" für
  `parent_phase_id`/`plan_phase_id`, mit Namensauflösung gegen den aktuellen `PlanPhase`-Baum
  statt roher IDs (`"Wareneingang → Top-Level"` statt `"2 → null"`) — genau das in Abschnitt
  6.14/Pass-2-Dokument Abschnitt 16 geforderte Beispiel, jetzt verifiziert.
- **Verifikation:** `backend/scripts/test_milestone_and_baseline_tree.py` (Milestone an
  Leaf/Parent, Projekt-Grenze, Snapshot-Felder, Deviation nach Reparenting) plus manueller
  Browser-Durchlauf (Milestone anlegen und mit Phasennamen statt ID anzeigen; Planstand vor
  einem Reparenting festhalten, danach zeigt der Vergleich exakt
  "Übergeordnete Phase: Wareneingang → Top-Level"). Alle Prüfungen grün, `check_migrations.py`/
  B-2/B-3/B-4/B-5-Skripte weiterhin grün (keine Schema-Änderung in diesem Paket).
- **Bewusst unverändert:** `PlanPhaseGantt.tsx` (Tree-Gantt kam bereits mit B-6);
  `ResourceDemandGrid.tsx`/Subproject-Verwaltung bleiben bestehen (B-8).
- **Nächstes Paket:** B-8 (Legacy Cutover: `ResourceDemandGrid.tsx` entfernen/deprecaten,
  Subproject-UI als deprecated markieren, vollständige Regression, finales CONCEPT.md-Update
  auf "implementiert") — abhängig von einer tatsächlich ausgeführten B-2-Migration, siehe
  Pass-2-Dokument Abschnitt 35.5.

### 16.14 P18 Implementierung — B-8 Legacy Cutover (dieser Durchgang, TEILWEISE — bewusst
nicht abgeschlossen)

**Achtes und letztes Paket. Nur der nicht-destruktive, migrationsunabhängige Teil wurde in
diesem Durchgang umgesetzt — der eigentliche Cutover (Entfernen von
`ResourceDemandGrid.tsx`/Subproject-UI) bleibt bewusst BLOCKIERT**, exakt wie im
Pass-2-Dokument Abschnitt 35.5 (Paket B-8) und CONCEPT.md Abschnitt 6.12 spezifiziert:
Dependency ist eine **tatsächlich gegen Produktivdaten ausgeführte B-2-Migration**, und diese
Ausführung erfordert laut Auftragsvorgabe (Abschnitt 25/35.2) eine **gesonderte Freigabe** —
kein automatischer Trigger durch einen Implementierungsdurchgang. Ohne diese Migration hätten
real existierende Projekte mit produktiver Grobplanung (`ResourceDemand.plan_phase_id IS
NULL`) nach einem Entfernen von `ResourceDemandGrid.tsx` keinen Bedienweg mehr für ihre
bereits gepflegten Daten — das wäre ein Datenverlust-Risiko für die Nutzer:innen, keine reine
Aufräumarbeit.

**In diesem Durchgang umgesetzt (sicher, nicht-destruktiv, jederzeit rückgängig machbar):**

- `ResourceDemandGrid.tsx`: `@deprecated`-Dokumentationskommentar ergänzt (P18/B-8,
  Ablösung durch den PlanPhase-Baum erklärt, Bedingung für die tatsächliche Entfernung
  benannt) — Komponente selbst **unverändert funktionsfähig**.
- `client.ts`: `createSubproject`/`updateSubproject`/`deleteSubproject`/
  `listAllSubprojects` mit `@deprecated`-JSDoc markiert (keine neuen Aufrufstellen anlegen) —
  Funktionen selbst **unverändert funktionsfähig**.
- `routers/projects.py::list_all_subprojects` und `routers/capacity.py::create_resource_demand`:
  Docstrings ergänzt, die den Legacy-Status bzw. den dokumentierten Legacy-Pfad
  (`plan_phase_id = None`) erklären — **keine Verhaltensänderung, keine Validierungssperre**
  (bewusst kein Blocker in diesem Paket, siehe Pass-2-Dokument Abschnitt 30/B-8-Scope).
- Vollständige Regression der bestehenden Verifikationsskripte (`check_migrations.py`,
  B-2–B-7-Skripte) nach diesen Änderungen: alle weiterhin grün.

**Bewusst NICHT umgesetzt (blockiert, bis eine Migrationsausführung freigegeben und
durchgeführt wurde):**

- `ResourceDemandGrid.tsx` **nicht gelöscht** — bleibt die einzige Bedienoberfläche für
  bestehende Grobplanungsdaten realer Projekte.
- Subproject-Verwaltungs-UI in `ProjectPlanningTab.tsx` **nicht entfernt**.
- `subprojects`-Tabelle/`subproject_id`-Spalten: kein Schema-Drop (war ohnehin nie Teil von
  B-8, siehe Abschnitt 6.7 — bleibt dauerhaft compat-only, unabhängig vom UI-Cutover).
- Finales CONCEPT.md-Update auf durchgängig "implementiert" (statt "Zielverhalten,
  teilweise Ist-Zustand"): folgt erst, wenn B-8 tatsächlich vollständig abgeschlossen werden
  kann.

**Ergebnis dieses Durchgangs (vor Final-Audit, 16.14): B-1–B-7 laut Selbstauskunft vollständig
implementiert und verifiziert, B-8 vorbereitet, aber mit offenem
Freigabe-/Ausführungsschritt (B-2-Migration gegen Produktivdaten) als einzigem genannten
Blocker.** Der nachfolgende Final-Audit-Durchgang (16.15) hat diese Selbstauskunft unabhängig
gegen den realen Code geprüft und dabei zusätzliche, kleinere Blocker gefunden — siehe dort.

---

### 16.15 P18 Final Audit & B-8 Cutover Readiness (dieser Durchgang)

**Unabhängiger Audit-Durchgang** — Ziel war, die in 16.7–16.14 dokumentierten
Implementierungs-Claims **gegen den realen Code zu verifizieren** (nicht nur die Dokumentation
zu glauben), die produktive Migration im Dry-Run-/Testkontext vollständig zu prüfen, alle
Kapazitäts-Konsumenten zu inventarisieren, Legacy-UX/-Codepfade (`ResourceDemandGrid`,
Subproject) zu inventarisieren und CONCEPT.md auf den tatsächlichen IST-Zustand zu bringen.
**Keine produktive Migration ausgeführt, kein Legacy-Code gelöscht, keine irreversible
Datenänderung vorgenommen** (siehe Aufgabenvorgabe, Abschnitt 30 des Auftrags).

**Methode:** sechs unabhängige Code-Audits (B-1/B-3, B-4 + Available Capacity, B-5 +
Kapazitäts-Konsumenten-Matrix, B-6-UX + Legacy-Inventar, B-7, Migrations-Dry-Run), jeweils mit
Datei:Zeile-Beleg, plus Live-Ausführung der bestehenden Verifikationsskripte
(`check_migrations.py`, `test_planning_phase_tree_api.py`,
`test_direct_assignment_and_capacity_range.py`, `test_derived_monthly_capacity.py`,
`test_migrate_to_planphase_hierarchy.py`, `test_milestone_and_baseline_tree.py`) gegen
Wegwerf-SQLite-DBs — nie gegen die reale `kapazitaetsplaner.db`.

**Ergebnis je Paket:**

- **B-1 Hierarchy Foundation — CONFIRMED.** Migration `0005` und `models.py` stimmen 1:1
  überein (FKs, Indexes, Nullability, Seeds, Upgrade/Downgrade-Roundtrip live verifiziert).
  **Caveat (kein Blocker für Produktiv-Cutover, aber ein reales Risiko für lokale
  SQLite-Umgebungen):** `ON DELETE SET NULL`/die self-referencing FK werden unter dem
  Standard-lokalen-SQLite ohne `PRAGMA foreign_keys=ON` **nicht** durchgesetzt — Produktivziel
  ist Postgres (`docker-compose.yml`), dort greifen die Constraints. `database.py` aktiviert
  diese Pragma aktuell nicht.
- **B-2 Migration Tooling — CONFIRMED.** Dry-Run-Default verifiziert (kein Schreibzugriff ohne
  `--apply`), Migrationsreport enthält harte Diskrepanz-Prüfungen (Orphans, FTE-Summen,
  Hierarchietiefe/Zyklen, Milestone-Zählungen — kein weiches "Warning", sondern Exit-Code 1 bei
  Abweichung). **Migrationsstrategie für Alt-Grobplanung ist Variante A** (Parent "Grobplanung
  (migriert)" + eine Monats-Leaf-Kindphase je migrierter Periode, `plan_fte` einmalig aus
  `SUM(ResourceDemand.fte)` abgeleitet) — exakt wie in Abschnitt 6.12 spezifiziert. Gegen eine
  repräsentative synthetische Testfixture (1 Subproject + 2 Kindphasen + Milestone + Comment, 2
  Grobplanungsperioden × 2 Rollen + 1 Assignment) lief Dry-Run/Apply/Re-Run fehlerfrei:
  `fte_sum_before = 3.0` bleibt nach der Verteilung auf die Monats-Leafs erhalten, 0 verwaiste
  `ResourceDemand`-Zeilen danach, Re-Run nach Apply idempotent. **Es existiert weiterhin keine
  populierte Produktiv-/Realdaten-DB in dieser Umgebung** — der Dry-Run wurde daher gegen die
  synthetische Fixture, nicht gegen einen echten Produktions-Snapshot gefahren. Das ist der in
  Abschnitt 24/Step 2 des B-8-Plans explizit vorgesehene nächste Schritt, kein Fehler dieses
  Audits.
- **B-3 Tree Domain Logic — CONFIRMED für den Kern**, live end-to-end getestet (3-Ebenen-Baum,
  Tiefe-4-Ablehnung, Zyklus-Ablehnung, projektfremder Parent, Leaf→Parent-Historisierung,
  BD-11-409-Block, Reparent, Subtree-Impact/-Delete inkl. Collaboration-Erhalt). **Zwei
  Einzel-Gaps:** (a) kein atomarer Bulk-Reorder-Endpoint für `reihenfolge` (existiert für
  `Project`, fehlt für `PlanPhase`); (b) das einfache `DELETE /plan-phases/{id}` einer Leaf-Phase
  nullt abhängige Zeilen (`Comment`/`Task`/`Blocker`/`Decision`/`Milestone`/`PlanHistory`) nicht
  defensiv im Anwendungscode (anders als `delete-subtree`), sondern verlässt sich auf
  DB-seitiges `ON DELETE SET NULL` — was gemäß B-1-Caveat unter lokalem SQLite wirkungslos ist.
- **B-4 Resource Planning + Available Capacity — CONFIRMED für den Haupt-Flow.** Direktzuweisung
  ohne Rollenzwang, Systemrolle korrekt im Picker/Reporting ausgeblendet, `plan_fte` nachweislich
  nie von Assignments verändert (live getestet inkl. Überbesetzung: 0,40/0,20/0,20 →
  0,40/0,50/−0,10, `plan_fte` blieb 0,40). Bereichsbasierte Available Capacity
  (`compute_person_capacity_for_range`) korrekt implementiert und wiederverwendet
  `WorkingTime`/`Holiday`/`Absence`/`InternalAllocation` ohne zweite Engine. **Drei
  Einzel-Gaps:** (a) es existiert **kein** `DELETE`-Endpoint für `resource_roles` überhaupt —
  die "nicht löschbar"-Regel für die Systemrolle ist damit faktisch, aber nicht durch einen
  Backend-Guard erzwungen; (b) der **legacy** Endpoint `GET /resource-demands/{id}/candidates`
  (erreichbar über den optionalen Rollen-Aufschlüsselungs-Pfad in `PlanPhaseCapacityTab.tsx`)
  prüft weiterhin nur einen Monats-Bucket statt der vollen Phasen-Range — nur der neue
  `GET /plan-phases/{id}/assignment-candidates`-Endpoint (Haupt-Flow) ist bereits
  bereichsbasiert; (c) Testabdeckung für Absence/Holiday/InternalAllocation/fehlendes
  Kapazitätsprofil/bereits überbuchte Person fehlt spezifisch für die Range-Funktion (nur
  Werktage-Gewichtung und Grundfall sind automatisiert getestet).
- **B-5 Capacity Source-of-Truth — CONFIRMED, KEIN BLOCKER.** Die vollständige
  Kapazitäts-Konsumenten-Matrix (siehe unten) zeigt: alle fünf zentralen Portfolio-/Cockpit-/
  GAP-Endpunkte lesen ausschließlich noch `compute_project_monthly_capacity`/
  `compute_portfolio_planphase_demand_fte`, mit korrekt werktage-anteiliger
  `monthly_distribution`-Formel und nachweislich erzwungenem Leaf-only-Verhalten
  (`_maybe_historize_parent_fte` setzt `parent.plan_fte = None` auf jedem Parent-erzeugenden
  Pfad — keine reine Query-Filterung, sondern ein Dateninvariante). Kein aktiver
  `max(Grob, Fein)`-Codepfad mehr. **Zwei sekundäre, dokumentierte Tracks bleiben auf
  `ResourceDemand.fte` stehen** (Effort-/Soll-Track in `gap_analysis.py` inkl.
  `health_calc._effort_health` und der PPTX-Export "fte"-Feld) — beide addieren **nicht** zur
  PlanPhase-Kapazität (kein Doppelzählungsrisiko), sind aber noch nicht auf die neue Quelle
  umgestellt.
- **B-6 UX — CONFIRMED.** Echte rekursive Baumdarstellung in Liste/Gantt, Leaf zeigt
  Zeitraum/Plan-FTE/Direktzuweisung ohne Rollenzwang/Available Capacity über die Range/optionale
  Rollen, Parent zeigt ausschließlich aggregierte, read-only Werte und blendet
  Kapazitätseingabe/Assignments aus, keine rohen technischen Begriffe in sichtbaren UI-Texten,
  alle acht geforderten deutschen UX-Begriffe vorhanden.
- **B-7 Gantt/Milestone/Planstand — CONFIRMED mit einem Planstand-Gap.** Milestones/Gantt
  vollständig auf den `PlanPhase`-Baum umgestellt (Gantt liest dieselbe Datenquelle wie die
  Liste, Parent = Hüllkurve, Leaf = Balken, beide öffnen denselben Workspace, read-only).
  **Planstand-Deviation-Erkennung ist unvollständig:** "Parent geändert"/"Zeitraum
  geändert"/"Plan-FTE geändert" sind CONFIRMED (inkl. Regressionstest), "reihenfolge geändert"
  ist bewusst nicht als Abweichung markiert (korrekt, wie spezifiziert) — aber **"Phase
  hinzugefügt" wird gar nicht erkannt** (nur zum Snapshot-Zeitpunkt eingefrorene Zeilen werden
  verglichen, eine später hinzugefügte Phase erscheint nie als Abweichung), und "Phase entfernt"
  wird nur unvollständig erkannt (kein explizites "entfernt"-Flag; zusätzlich ein Detail-Gap: die
  Gruppenkopfzeile einer entfernten Phase im Planstand-Vergleich fällt auf eine rohe `#<id>`
  zurück, wenn `entity_summary` für die gelöschte Zeile `None` liefert — der einzige Ort im
  gesamten Audit, an dem eine rohe ID tatsächlich sichtbar würde).

**Kapazitäts-Konsumenten-Matrix (Abschnitt 8 der Auftragsvorgabe):**

| Consumer | Quelle | Leaf-only? | Status |
|---|---|---|---|
| GAP Engine Capacity (`GET /gap-engine/capacity`) | `compute_capacity_gap` → `compute_portfolio_planphase_demand_fte` | Ja (Invariante) | CONFIRMED derived-only |
| Capacity Heatmap (`GET /controlling/capacity-heatmap`) | dieselbe Funktion | Ja | CONFIRMED derived-only |
| Cockpit Capacity (`_cockpit_capacity`) | `compute_project_monthly_capacity` (`demand_fte`); `assigned_fte` separat, nie addiert | Ja | CONFIRMED derived-only |
| Project Monthly Capacity (`GET /projects/{id}/capacity/monthly`) | `compute_project_monthly_capacity` direkt | Ja | CONFIRMED derived-only |
| Portfolio-Demand (`compute_portfolio_planphase_demand_fte`) | Summe über alle Projekte | Ja | CONFIRMED derived-only |
| Allocation Gaps / Role Analysis (Controlling) | `ResourceDemand`/`ResourceAssignment`, Rollen-Ebene | N/A (Rollen-Layer per Design) | CONFIRMED, kein Beitrag zur Projektkapazität |
| Utilization Gap (Personenebene) | `ResourceAssignment` vs. `compute_person_capacity` | N/A (Personen-Layer) | CONFIRMED, kein Beitrag zur Projektkapazität |
| Project Health "Aufwand"-Dimension (`health_calc._effort_health`) | `gap_analysis._soll_je_monat` → `SUM(ResourceDemand.fte)` | Nein (nicht P18-migriert) | **PARTIAL** — eigener Soll-/Ist-Track, nicht doppelt gezählt, aber noch nicht auf PlanPhase-Quelle umgestellt |
| PPTX-Export "fte"-Feld (`routers/export.py`) | dieselbe `_soll_je_monat`-Quelle | Nein | **PARTIAL** — Deck zeigt weiterhin ResourceDemand-basierte Balken, nicht die P18-Kapazität |

**BLOCKER-Prüfung (Abschnitt 8 der Aufgabenstellung, "wird ResourceDemand.fte irgendwo weiter
als Projektbedarf summiert?"): NEIN, für keinen der fünf zentralen Portfolio-/Cockpit-/
GAP-Endpunkte.** Die beiden PARTIAL-Zeilen sind separate, seit jeher dokumentierte
Soll-/Ist-Tracks (Tempo-Abgleich bzw. Export-Legende) und addieren an keiner Stelle zur
PlanPhase-Kapazität — sie sind ein offener Migrationsrest, kein Doppelzählungs-Blocker.

**Identifizierte Defekte/Gaps (Priorität für B-8):**

1. Planstand erkennt "Phase hinzugefügt" gar nicht und "Phase entfernt" nur unvollständig
   (inkl. Roh-ID-Leck in der Gruppenkopfzeile) — betrifft die im Auftrag explizit geforderte
   Deviation-Erkennung (Abschnitt 14 der Aufgabenstellung).
2. `GET /resource-demands/{id}/candidates` (Legacy-Rollen-Sub-Flow) prüft weiterhin nur einen
   Monats-Bucket statt der vollen Phasen-Range — widerspricht der im Auftrag geforderten
   Range-basierten Candidate-Preview (Abschnitt 6 der Aufgabenstellung), auch wenn der
   Haupt-Direktzuweisungs-Flow bereits korrekt ist.
3. Kein Backend-Guard verhindert das Löschen der Systemrolle "Ohne Rolle" — aktuell folgenlos,
   weil überhaupt kein `DELETE /resource-roles/{id}`-Endpoint existiert, aber die im Konzept
   dokumentierte Governance-Regel ist damit nicht durch Code erzwungen, sondern nur durch
   Abwesenheit einer Löschmöglichkeit zufällig erfüllt.
4. Kein atomarer Bulk-Reorder-Endpoint für `PlanPhase.reihenfolge`, keine Eindeutigkeitsprüfung
   gegen doppelte Geschwister-Reihenfolge.
5. Einfaches `DELETE /plan-phases/{id}` verlässt sich auf DB-seitiges `ON DELETE SET NULL`
   statt abhängige Zeilen defensiv im Anwendungscode zu entkoppeln — unter lokalem SQLite ohne
   `PRAGMA foreign_keys=ON` (Standard in diesem Repo) demonstrierbar wirkungslos; unter
   Produktions-Postgres funktional, aber nicht durch Applikationscode abgesichert.
6. Testabdeckung für `compute_person_capacity_for_range` deckt Absence/Holiday/
   InternalAllocation/fehlendes Kapazitätsprofil/bereits überbuchte Person nicht ab.
7. Migrations-Dry-Run wurde bisher ausschließlich gegen eine synthetische Testfixture gefahren,
   nie gegen einen echten Produktions-Datenbestand (kein Blocker, aber Pflichtschritt vor
   Apply, siehe B-8-Plan Step 2).

**Durchgeführte Fixes in diesem Durchgang:** Keine Code-Änderungen — nur CONCEPT.md-Korrekturen
(dieser Abschnitt sowie Abschnitte 0/3/4/5/6/6/13/15). Die oben gelisteten Defekte sind
**Findings, keine in diesem Audit-Durchgang behobenen Fixes** — sie erfordern Code-Änderungen,
die außerhalb des reinen Audit-/Dokumentations-Scopes dieses Durchgangs liegen (Minimal-Change-
Prinzip, AGENTS.md Abschnitt 16/17) und vor B-8 gezielt als eigene, kleine Tasks umgesetzt werden
sollten.

**GO/NO-GO (Abschnitt 27 der Aufgabenstellung):**

| # | Kriterium | Status |
|---|---|---|
| 1 | B-1–B-7 Codeaudit vollständig CONFIRMED | **PARTIAL** — Kern CONFIRMED, 7 dokumentierte Einzel-Gaps offen |
| 2 | Migration Dry-Run fehlerfrei | CONFIRMED (gegen synthetische Fixture; echter Produktiv-Dry-Run steht noch aus) |
| 3 | Orphan-Count = 0 | CONFIRMED (in der Testfixture) |
| 4 | Hierarchy-Violations = 0 | CONFIRMED |
| 5 | Projektkapazität vorher/nachher fachlich erklärt/validiert | CONFIRMED (FTE-Summe 3,0 vorher = Summe der Monats-Leafs nachher) |
| 6 | Keine zentrale Capacity View summiert weiter `ResourceDemand` als Projektbedarf | CONFIRMED für alle fünf zentralen Endpunkte, 2 sekundäre Tracks offen (kein Doppelzählungsrisiko) |
| 7 | Direct Assignment funktioniert | CONFIRMED |
| 8 | Available Capacity über Phase Range funktioniert | **PARTIAL** — Haupt-Flow ja, Legacy-Candidates-Endpoint nein |
| 9 | Planstand Tree funktioniert | **PARTIAL** — Parent/Zeitraum/FTE-Änderung ja, "Phase hinzugefügt" nein |
| 10 | Gantt Tree funktioniert | CONFIRMED |
| 11 | ResourceDemandGrid Removal Dependencies vollständig bekannt | CONFIRMED (Removal-Checkliste erstellt) |
| 12 | Subproject Removal Dependencies vollständig bekannt | CONFIRMED (erweitertes Inventar: `ProjectPlanningTab`/`ProjectHistoryTab`/`ProjectCommunicationTab`/`export.py`, nicht nur `ProjectPlanningTab`) |
| 13 | CONCEPT auf echtem IST-Stand | CONFIRMED (dieser Durchgang) |

**Drei rote Punkte (1, 8, 9) → gemäß der in der Aufgabenstellung festgelegten Regel ("Wenn ein
Punkt rot: B-8 CUTOVER BLOCKED") ist dieser Durchgang mit `B-8 CUTOVER BLOCKED` abzuschließen.**
Das ist **kein** Architektur-Blocker — die Zielarchitektur ist vollständig implementiert und der
Kern (Baum, Direktzuweisung, abgeleitete Kapazität, Gantt) ist live end-to-end verifiziert. Es
sind **konkrete, klein-skalierte Nacharbeiten** (Defekte 1–2 oben schließen genügt, um die drei
roten Punkte grün zu bekommen), gefolgt von einem echten Produktiv-Dry-Run (Defekt 7), bevor der
eigentliche Cutover (finaler Plan siehe unten) angestoßen werden sollte.

### 16.16 P18.1 Stabilization & B-8 Unblock (dieser Durchgang)

**Auftrag:** die drei in 16.15 identifizierten B-8-Blocker (Defekte 1/2/9-Deviation-Erkennung,
2/8-Legacy-Candidates-Range, plus die begleitenden Defekte 3/6/7) gezielt schließen und das
GO/NO-GO-Gate erneut ausführen — **ausdrücklich ohne** produktive Migration, ohne
`ResourceDemandGrid`-Removal, ohne Subproject-Cutover, ohne irreversible Änderungen (siehe
Auftrag Abschnitt 10). Alle Änderungen sind Code+Test, keine neue Architekturentscheidung.

#### 1. Fixed Defects

| # (aus 16.15) | Defekt | Status nach diesem Durchgang |
|---|---|---|
| 1 | Planstand erkennt "Phase hinzugefügt" gar nicht, "Phase entfernt" unvollständig (Roh-ID-Leck) | **FIXED** — siehe Abschnitt 2 unten |
| 2 | `GET /resource-demands/{id}/candidates` prüft nur einen Monats-Bucket statt der vollen Phasen-Range | **FIXED** — siehe Abschnitt 3 unten |
| 3 | Kein Backend-Guard verhindert das Löschen der Systemrolle "Ohne Rolle" | **FIXED** (Domain-Guard, kein künstlicher Endpoint) — siehe Abschnitt 5 unten |
| 4 | Kein atomarer Bulk-Reorder-Endpoint für `PlanPhase.reihenfolge` | **unverändert offen** — außerhalb des Scopes dieses Durchgangs (kein B-8-Blocker laut 16.15-Kategorisierung, reine UX-Komfortfunktion ohne Datenrisiko) |
| 5 | Einfaches `DELETE /plan-phases/{id}` verlässt sich auf DB-seitiges `ON DELETE SET NULL` statt Anwendungscode | **unverändert offen** — außerhalb des Scopes dieses Durchgangs (unter Produktions-Postgres funktional, kein B-8-Blocker) |
| 6 | Testabdeckung für `compute_person_capacity_for_range` unvollständig | **FIXED** — siehe Abschnitt 4 unten |
| 7 | Migrations-Dry-Run nur gegen synthetische Fixture, nie gegen echte Produktivdaten | **Tooling/Runbook vorbereitet, Ausführung weiterhin extern blockiert** — siehe Abschnitt 7 unten |

Defekte 4/5 waren in der Aufgabenstellung dieses Durchgangs nicht explizit adressiert (Fokus:
Abschnitte 1–7 des Auftrags) und sind laut 16.15 kein B-8-Blocker (sie tauchten nicht unter den
drei roten GO/NO-GO-Punkten 1/8/9 auf) — bewusst nicht mit-erledigt (Minimal-Change-Prinzip),
bleiben aber als offene, dokumentierte Kleinfunde bestehen.

#### 2. Planstand Diff

`baseline_calc.compute_deviations` (Backend) erkennt jetzt zusätzlich zur bestehenden
Feld-für-Feld-Abweichung strukturelle Baum-Änderungen einer `PlanPhase`, über eine neue
`_structural_plan_phase_deviations`-Hilfsfunktion — **erweitert die bestehende Baseline-/
Deviation-API additiv, keine zweite Diff-Engine, kein neuer Endpoint**:

- **Phase hinzugefügt:** aktuelle `PlanPhase`-ID des Projekts ohne Snapshot-Eintrag → neue
  Deviation mit `type="added"`, `label`/`current_value` = aktueller `phase_type` (Live-Wert).
- **Phase entfernt:** Snapshot-`entity_id` (aus `BaselineEntry`) ohne zugehörige aktuelle
  `PlanPhase`-Zeile → neue Deviation mit `type="removed"`, Name aus dem eigenen, zum
  Snapshot-Zeitpunkt bereits eingefrorenen `phase_type`-Feld rekonstruiert (kein neues
  Snapshot-Feld nötig, `phase_type` war schon vorher Teil von `_SNAPSHOT_FIELDS`) — **kein
  `#<id>`-Fallback im normalen UI**, da die Quelle immer vorhanden ist.
- Für eine bereits als `removed` markierte Phase werden die redundanten Feld-Deltas (z.B.
  "Start: 2024-01-01 → —") unterdrückt, damit dieselbe Löschung nicht doppelt/widersprüchlich
  dargestellt wird.
- `BaselineDeviationOut` bekommt ein additives Feld `type: "changed" | "added" | "removed"`
  (Default `"changed"`, keine Breaking Change für bestehende Konsumenten wie
  `routers/controlling.py`s portfolioweite Baseline-Deviations, die weiterhin nur auf
  `delta_days is not None` filtern und `type="added"/"removed"` damit automatisch ignorieren —
  fachlich korrekt, da diese Ansicht reine Termin-Abweichungen zeigt).
- Frontend (`BaselineList.tsx`): strukturelle Deviations werden getrennt von den
  Feld-Änderungs-Gruppen als eigene Zeilen dargestellt — `"+ Phase hinzugefügt: <Name>"` (grün)
  bzw. `"− Phase entfernt: <Name>"` (rot), ohne rohe ID.
- "reihenfolge geändert" bleibt weiterhin bewusst kein fachlicher Delta (unverändert, wie
  CONCEPT.md das seit B-7 definiert).

**Tests** (`backend/scripts/test_milestone_and_baseline_tree.py`, erweitert, Schritte 5–8):
Phase added, Phase removed, Parent geändert (Regression, bereits vorher grün), plan_fte
geändert (Regression), forecast_start geändert inkl. `delta_days` (Regression), gelöschte
Entität liefert lesbaren Namen statt Roh-ID, kein Roh-ID-Leck in normalen Deviation-Labels,
unveränderter Baum liefert keine strukturellen Deviations. Live grün verifiziert.

#### 3. Legacy Candidates Range Fix

`GET /resource-demands/{demand_id}/candidates` (`routers/capacity.py`) prüft jetzt: ist
`ResourceDemand.plan_phase_id` gesetzt, wird die zugehörige `PlanPhase` geladen und — sofern
`forecast_start`/`forecast_end` gesetzt sind — Available Capacity über
`compute_person_capacity_for_range` (**wiederverwendet, kein neuer Kapazitätsalgorithmus**)
für den vollen Phasenzeitraum geprüft, exakt wie der bereits bestehende Haupt-Flow
`GET /plan-phases/{id}/assignment-candidates`. Ohne `plan_phase_id` (unmigrierte
Alt-Grobplanung) bleibt die bisherige `compute_person_capacity(db, person_id, demand.period)`-
Logik unverändert als Fallback erhalten — kein Regressionsrisiko für Legacy-Daten.

**Tests** (`backend/scripts/test_direct_assignment_and_capacity_range.py`, erweitert, Schritte
7–8): Phasen-Demand über eine Monatsgrenze hinweg (Person mit Kapazität nur im zweiten Monat,
via volle Oktober-Abwesenheit erzwungen) wird jetzt korrekt als Kandidat gefunden; Ergebnis ist
deckungsgleich (Personen-IDs + `available_fte`) mit `GET /plan-phases/{id}/assignment-
candidates` für dieselbe Phase; Legacy-Demand ohne `plan_phase_id` bleibt nachweislich
periodenbasiert (dieselbe Person mit reiner November-Kapazität taucht dort korrekt NICHT auf).
Live grün verifiziert.

#### 4. Capacity Edge-Case Tests

Neues Testskript `backend/scripts/test_capacity_range_edge_cases.py`, ruft
`capacity_calc.compute_person_capacity_for_range` direkt auf (11 Szenarien, keine
Formeländerung — reine Testabdeckung gemäß Auftrag Abschnitt 3): WorkingTime,
ResourceProfile-Fallback, Holiday, Absence, InternalAllocation, fehlendes
ResourceProfile/WorkingTime (→ `None`), bestehende ResourceAssignments (Kapazität bleibt
unverändert — Demand ≠ Assignment-Invariante bestätigt), überbuchte Person (`available_fte`
wird negativ, kein Clamping bei 0), Teilmonat, mehrere Monate (3 Kalendermonate), Zero-Workday
Edge Case (reines Wochenende → `None`). Alle 11 Szenarien live grün, keine fachliche Formel
geändert.

#### 5. System Role Invariant

Es existiert weiterhin **kein** `DELETE /resource-roles/{id}`-Endpoint (verifiziert: keine
Route registriert, `DELETE` liefert 405). Da damit aktuell kein realer Löschpfad existiert,
wurde bewusst **kein** künstlicher Endpoint nur für diesen Guard ergänzt (Auftrag Abschnitt 4:
"Wenn aktuell wirklich kein Delete-Pfad existiert: kein künstlicher Endpoint nur dafür
bauen"). Stattdessen verankert ein neuer, zentraler Domain-Helper
`ensure_role_deletable(role)` (`routers/capacity.py`, direkt neben
`create_resource_role`/`update_resource_role`) die Invariante `is_system_role == True →
Löschen verboten` (wirft `HTTPException(409)`) — ein künftiger Lösch-Pfad (Admin-UI,
Cleanup-Skript) muss ihn beim Einbau zwingend aufrufen, statt die Regel unabhängig neu zu
erfinden oder zu vergessen. Test (`test_direct_assignment_and_capacity_range.py`, Schritt 2b):
kein `DELETE`-Endpoint (405), Guard wirft für die Systemrolle (409), lässt eine normale Rolle
unangetastet. Live grün.

#### 6. Secondary Consumer Assessment

Geprüft: `gap_analysis._soll_je_monat` (Tempo-/Effort-Gap-Track), `health_calc._effort_health`
(nutzt dieselbe Quelle), PPTX-Export `"fte"`-Feld (`routers/export.py`, nutzt ebenfalls
dieselbe Quelle über `gap_analysis.project_gap(...)["soll"]`). **Entscheidung: B) bewusst
deferred**, aus zwei zusammenhängenden Gründen, nicht nur wegen Semantik-Unschärfe:

1. **Fachliche Semantik unterscheidet sich real:** `_soll_je_monat` speist die
   Tempo-/Effort-Gap-Analyse (Soll-Aufwand vs. Ist-Aufwand aus Jira, Trendfortschreibung,
   BD-1-Kontext) — das ist eine andere fachliche Frage ("wird so gearbeitet wie geplant?") als
   die zentrale Projektkapazität ("wie viel Kapazität ist für dieses Projekt verplant?", seit
   B-5 exklusiv aus `PlanPhase.plan_fte` abgeleitet). Eine Gleichsetzung von Effort-Soll und
   Capacity-Soll ohne explizite fachliche Prüfung würde eine Architekturentscheidung erfinden,
   die der Auftrag ausdrücklich untersagt ("Nicht versehentlich Effort-Soll und Capacity-Soll
   gleichsetzen").
2. **Konkretes Regressionsrisiko vor B-2:** Da die produktive Migration (B-2) noch nicht
   ausgeführt wurde, haben die meisten aktuell aktiven Projekte **keinen** oder nur einen
   unvollständigen `PlanPhase`-Baum — ihre Kapazität steht ausschließlich in
   `ResourceDemand` (Alt-Grobplanung). Ein Umstieg von `_soll_je_monat` auf eine rein
   `PlanPhase`-abgeleitete Quelle **jetzt** würde für praktisch alle unmigrierten Projekte
   sofort `Soll = 0` liefern und sowohl die Effort-Gap-Anzeige als auch das PPTX-"Übersicht
   FTE"-Slide für den überwiegenden Teil des aktuellen Portfolios kaputt machen — ein reales,
   vermeidbares Regressionsrisiko, keine bloße Geschmacksfrage.

**Konsequenz:** alle drei Konsumenten bleiben unverändert auf `ResourceDemand.fte` (Track
"Effort-Soll", separat von "Capacity-Soll") — dokumentiert deferred, keine Doppelzählung zur
zentralen `PlanPhase`-Kapazität (unverändert CONFIRMED, siehe Kapazitäts-Konsumenten-Matrix in
16.15). Diese Entscheidung sollte spätestens direkt nach einer tatsächlich ausgeführten
B-2-Migration neu bewertet werden, sobald `PlanPhase.plan_fte` flächendeckend vorhanden ist.

#### 7. Migration Dry-Run Status

**Diese Entwicklungsumgebung hat keinen Zugriff auf eine Kopie oder einen Snapshot der
Produktivdatenbank** (kein Docker-/Postgres-Zugriff, keine Zugangsdaten) — Schritt 1/2 eines
realistischen Dry-Runs (Snapshot beziehen, isoliert restaurieren) sind damit ein **externer,
hier nicht ausführbarer Vorbedingungs-Schritt**. Es wurden **keine Daten erfunden oder
simuliert** (Auftrag Abschnitt 6). Stattdessen in diesem Durchgang vorbereitet:

- Neues Runbook `backend/scripts/MIGRATION_DRY_RUN_RUNBOOK.md` mit dem vollständigen
  10-Schritte-Ablauf (Snapshot → Restore → Dry-Run → Report → Apply-auf-Kopie → Integrity →
  Capacity Parity → Tree/Assignment/Milestone Validation) inkl. der geforderten Stichproben
  (Projekt mit Subprojects/Grob-Demands/Assignments/Milestones/mehreren Monaten/ohne
  Grob-Demands) als Checkliste.
- `migrate_to_planphase_hierarchy.py` erweitert: neues `--report-file PATH` (JSON-Export des
  vollständigen Reports, für ein archivierbares Freigabe-Artefakt) und ein zusätzlicher
  Vorher/Nachher-Vergleich für `ResourceAssignment` (Anzahl UND FTE-Summe je Projekt,
  `assignments_count_before/after`, `assignments_fte_sum_before/after`) — fließt in
  `has_discrepancies` mit ein, ergänzt die bereits bestehenden Orphan-/FTE-Summen-/
  Hierarchietiefe-/Zyklus-/Milestone-Checks. Weiterhin: kein Schreibzugriff ohne `--apply`,
  Dry-Run macht explizit `db.rollback()`.
- Beides gegen die bestehende synthetische Fixture verifiziert
  (`test_migrate_to_planphase_hierarchy.py`, weiterhin grün) sowie `--report-file` manuell
  gegen eine frische, migrierte SQLite-DB durchgespielt (JSON-Report korrekt geschrieben).

**Status: weiterhin nicht gegen echte Produktivdaten ausgeführt** — das bleibt der offene,
extern zu beschaffende Schritt vor dem eigentlichen B-8-Cutover (unverändert gegenüber 16.15,
Defekt 7, jetzt mit vollständig vorbereitetem Tooling/Runbook statt nur der synthetischen
Fixture).

#### 8. Regression Results

Alle bestehenden Verifikationsskripte erneut live ausgeführt, **alle grün**, keine Regression:
`check_migrations.py` (kein Drift, Seeds vollständig, Downgrade/Upgrade-Roundtrip sauber),
`test_planning_phase_tree_api.py`, `test_direct_assignment_and_capacity_range.py` (erweitert),
`test_derived_monthly_capacity.py`, `test_migrate_to_planphase_hierarchy.py` (erweitert),
`test_milestone_and_baseline_tree.py` (erweitert), plus die zwei neuen Skripte
`test_capacity_range_edge_cases.py`. Zusätzlich: Frontend-Typecheck (`tsc -b`) fehlerfrei nach
den `BaselineList.tsx`/`types.ts`-Änderungen.

#### 9. CONCEPT Updates

Dieser Abschnitt (16.16) sowie Ergänzungen in Abschnitt 6 (Available-Capacity-Grenze,
historische Anmerkung zum jetzt geschlossenen Legacy-Candidates-Gap) und Abschnitt 6
(Kopfzeile: B-8-Status präzisiert — nicht mehr wegen Code-Defekten blockiert, nur noch wegen
des externen Migrations-Dry-Run-Schritts). Keine Aufwertung der alten Pass-1-Architektur
(Abschnitt 6a bleibt unverändert als abgelöst markiert).

#### 10. GO/NO-GO Checklist

| # | Kriterium | Status (16.15) | Status (16.16, dieser Durchgang) |
|---|---|---|---|
| 1 | B-1–B-7 Codeaudit vollständig CONFIRMED | PARTIAL (7 Gaps) | **PARTIAL** (nur noch 2 nicht-blockierende Kleinfunde #4/#5, außerhalb Scope) |
| 2 | Migration Dry-Run realistic green | PARTIAL (nur synthetische Fixture) | **PARTIAL** — Tooling/Runbook fertig, Ausführung extern blockiert (kein Prod-Zugriff in dieser Umgebung) |
| 3 | Orphan-Count = 0 | CONFIRMED | CONFIRMED (unverändert) |
| 4 | Hierarchy-Violations = 0 | CONFIRMED | CONFIRMED (unverändert, jetzt zusätzlich mit Assignment-Vorher/Nachher-Check im Migrationsreport) |
| 5 | Capacity parity valid | CONFIRMED (Fixture) | CONFIRMED (Fixture) — echte Parity erst nach Schritt 1/2 des Runbooks möglich |
| 6 | Zentrale Capacity-Konsumenten derived-only | CONFIRMED (5 zentrale Endpunkte), 2 sekundäre Tracks offen | CONFIRMED (unverändert) — sekundäre Tracks jetzt explizit als Entscheidung B) deferred dokumentiert (Abschnitt 6 oben), kein Doppelzählungsrisiko |
| 7 | Direct Assignment funktioniert | CONFIRMED | CONFIRMED (unverändert) |
| 8 | Available Capacity über Phase Range funktioniert | **PARTIAL** | **GREEN** — Legacy-Candidates-Endpoint jetzt ebenfalls range-basiert |
| 9 | Planstand Tree funktioniert | **PARTIAL** | **GREEN** — Phase hinzugefügt/entfernt jetzt strukturell erkannt, kein Roh-ID-Leck |
| 10 | Gantt Tree funktioniert | CONFIRMED | CONFIRMED (unverändert) |
| 11 | ResourceDemandGrid Removal Dependencies bekannt | CONFIRMED | CONFIRMED (unverändert) |
| 12 | Subproject Removal Dependencies bekannt | CONFIRMED | CONFIRMED (unverändert) |
| 13 | CONCEPT auf echtem IST-Stand | CONFIRMED | CONFIRMED (dieser Durchgang) |

Punkte 8 und 9 sind jetzt **grün** (die beiden explizit benannten B-8-Blocker aus 16.15 sind
geschlossen). Punkt 1 bleibt PARTIAL, aber nur noch wegen zweier kleiner, nicht
B-8-relevanter Restfunde (#4/#5, bewusst außerhalb dieses Scopes). **Punkt 2 bleibt PARTIAL**
— nicht durch einen Code-Defekt, sondern durch eine externe Vorbedingung (kein
Produktivdaten-Zugriff in dieser Umgebung), die dieser Durchgang nicht auflösen kann, ohne
Daten zu erfinden.

#### 11. Remaining Risks

- **Migration Dry-Run gegen echte Produktivdaten steht weiterhin aus** (externe
  Vorbedingung — Snapshot/Restore außerhalb dieser Umgebung, siehe Runbook). Solange das
  nicht erfolgt ist, ist die Aussage "Orphan=0/FTE-Parity/Capacity-Parity" nur gegen die
  synthetische Fixture, nicht gegen die reale Datenrealität abgesichert.
- Zwei kleine, nicht B-8-relevante Code-Funde bleiben offen (#4 Bulk-Reorder-Endpoint für
  `reihenfolge`, #5 defensives Anwendungscode-Löschen statt DB-`ON DELETE SET NULL`) —
  unter Produktions-Postgres funktional korrekt, aber nicht Anwendungscode-abgesichert.
- Sekundäre Effort-/PPTX-Konsumenten bleiben bewusst auf `ResourceDemand.fte` — nach der
  echten B-2-Migration sollte diese Deferred-Entscheidung erneut geprüft werden (Abschnitt 6
  oben), sonst driftet die PPTX-"Übersicht FTE"-Folie langfristig von der neuen
  PlanPhase-Kapazität weg.

#### 12. Final Status

**B-8 CUTOVER BLOCKED**

Grund: GO/NO-GO-Punkt 2 (Migration Dry-Run realistic) ist weiterhin nicht grün — nicht wegen
eines Code-Defekts, sondern wegen einer externen Vorbedingung (kein Zugriff auf eine
Produktivdaten-Kopie in dieser Entwicklungsumgebung), die dieser Durchgang nicht auflösen
kann, ohne gegen die ausdrückliche Vorgabe zu verstoßen, keine Daten zu erfinden. Alle
Code-seitigen B-8-Blocker aus 16.15 (Punkte 1/8/9, konkret Defekte 1/2 sowie die begleitenden
Defekte 3/6) sind geschlossen und live verifiziert. **Nächster Schritt vor dem eigentlichen
Cutover:** Schritt 1/2 des neuen Runbooks (`backend/scripts/MIGRATION_DRY_RUN_RUNBOOK.md`)
extern ausführen (Produktivdaten-Snapshot beziehen, isoliert restaurieren), danach Schritt 3–10
gegen die reale Kopie durchlaufen und das GO/NO-GO-Gate ein drittes Mal ausführen.

### 16.17 P18 Finalization — CONCEPT Cleanup & Realistic Migration Readiness (dieser Durchgang)

**Auftrag:** P18 endgültig abschließen — (A) CONCEPT.md als Rebuild-Spezifikation bereinigen
(aktuelle vs. historische Architektur klar trennen, keine Verkürzung), (B) den realistischen
Migrations-Dry-Run gegen eine echte/repräsentative Produktivdatenkopie durchführen bzw.
vollständig vorbereiten, (C) B-8 GO/NO-GO final bewerten. **Keine neue Architektur, keine
zweite Planungsquelle, keine neue Monatsplanung, keine produktive Migration in diesem
Durchgang.**

**A) CONCEPT Cleanup:** Der frühere Abschnitt 6b (P18 Pass 2, final gelockt, IMPLEMENTIERT)
ist jetzt **Abschnitt 6** — die einzige Kapazitätsbeschreibung im Hauptteil. Der frühere
Abschnitt 6a (P18 Pass 1, superseded, nie implementiert) ist vollständig, ungekürzt nach
**Abschnitt 17.7** verschoben. Der frühere Abschnitt 6 (aktiver Zwei-Achsen-Legacy-Pfad,
`ResourceDemandGrid`/`Subproject`) ist vollständig, ungekürzt nach **Abschnitt 17.8**
verschoben, mit einer kompakten Zusammenfassung in der neuen **Abschnitt 6.15** ("Legacy /
Pending Cutover") im aktuellen Kapitel. Alle Querverweise im übrigen Dokument (Abschnitte
0/3/4/5/13/14/16) wurden konsistent mitgezogen (`6b.X` → `6.X`, die vier alten `6.1`–`6.4`
Legacy-Verweise → `L6.1`–`L6.4` in Abschnitt 17.8, `6a.X`-Verweise unverändert gültig, da
Abschnitt 17.7 dieselben Unterabschnittsnummern beibehält). Keine inhaltliche Kürzung an
6a/6/6b — nur Verschiebung, Umbenennung und Ergänzung von Herkunfts-/Navigationshinweisen.
Abschnitt 3 (Kernprinzipien) und Abschnitt 13 (Source-of-Truth-Matrix) verweisen jetzt
durchgängig auf Abschnitt 6 als einzige Kapazitätsquelle, mit expliziten Verweisen auf
17.7/17.8 für den historischen bzw. Compat-Kontext.

**B) Realistic Migration Dry-Run — erneut geprüft, unverändertes Ergebnis:** Diese
Entwicklungsumgebung (frischer, isolierter Remote-Container) wurde erneut auf Zugriff auf
eine Produktivdaten-Kopie geprüft: `docker info` liefert keinen laufenden Docker-Daemon,
der lokal installierte Postgres-Cluster (`pg_lsclusters`) ist `down`, es existieren keine
`DATABASE_URL`-Zugangsdaten zu einer Produktivinstanz und keine `.dump`/Backup-Datei ist im
Repository oder auf dem Dateisystem vorhanden. **Es existiert weiterhin keine echte oder
repräsentative Kopie der Produktivdaten in dieser Umgebung.** Gemäß ausdrücklicher Vorgabe
("Wenn keine echte Datenkopie verfügbar ist: NICHT synthetische Daten als Ersatz
deklarieren") wurden **keine Daten erfunden oder simuliert** — Schritt 1/2 des Runbooks
(`backend/scripts/MIGRATION_DRY_RUN_RUNBOOK.md`) bleiben ein **externer, außerhalb dieser
Umgebung auszuführender Vorbedingungs-Schritt**, unverändert gegenüber 16.16. Das Tooling
selbst (`migrate_to_planphase_hierarchy.py` inkl. `--report-file`, Orphan-/FTE-/
Assignment-/Milestone-/Hierarchietiefe-Checks) ist vollständig vorbereitet und gegen die
synthetische Regressionsfixture (`test_migrate_to_planphase_hierarchy.py`) erneut grün
verifiziert — das deckt die Migrationslogik strukturell ab, ersetzt aber nicht den
ausstehenden Lauf gegen echte Datenrealität (Volumen, echte Rollenverteilung, echte
Sonderfälle in Alt-Daten, siehe Abschnitt 18/20 der Auftragsvorgabe dieses Durchgangs).

**C) B-8 GO/NO-GO — unverändert BLOCKED:** Alle Code-seitigen Kriterien aus der 18-Punkte-
GO/NO-GO-Liste dieses Durchgangs sind unverändert grün gegenüber 16.16 (Orphans/Cycles/
Depth-Violations = 0 in der Fixture, Direct Assignment/Available Capacity Range/Planstand
Tree/Gantt Tree CONFIRMED, zentrale Capacity-Konsumenten derived-only, Removal-Dependencies
für `ResourceDemandGrid`/Subproject bekannt, Rollback-Plan vorhanden, CONCEPT jetzt aktuell).
**Einziges rotes Kriterium: "Migration Dry-Run realistic" — weiterhin nicht gegen echte
Produktivdaten ausgeführt**, aus demselben externen Grund wie in 16.16. Ergebnis
unverändert: **B-8 CUTOVER BLOCKED**. Ein vollständiger, sofort ausführbarer
Produktiv-Cutover-Runbook-Plan (Snapshot → Restore → Dry-Run → Apply → Integrity/Parity →
UI-Umschaltung → Regression → Observation → Rollback-Entscheidung) ist als separates
Artefakt dieses Durchgangs erstellt (P18 Finalization & Realistic Migration Readiness
Report) — der eigentliche produktive Cutover selbst wird **nicht** in diesem Durchgang
angestoßen, sondern erfordert einen separaten, explizit freigegebenen Auftrag, sobald
Schritt 1/2 des Runbooks extern durchgeführt wurden. Vollständiger Report dieses Durchgangs
inkl. Cutover-Runbook und Rollback-Plan:
[`P18_FINALIZATION_REPORT.md`](P18_FINALIZATION_REPORT.md).

**Durchgeführte Änderungen in diesem Durchgang:** Ausschließlich CONCEPT.md-Restrukturierung
(Abschnitte 0/3/4/5/6/13/14/16/17, siehe oben) sowie das externe Report-Artefakt. **Keine
Code-Änderungen**, keine Schema-Änderungen, keine produktive Migration, kein Legacy-Code
entfernt — konsistent mit der ausdrücklichen Vorgabe dieses Durchgangs ("keine produktive
Migration ohne separaten Auftrag").

---

### 16.18 P19 — PlanPhase Workspace UX Consolidation (dieser Durchgang)

**Auftrag:** P18 ist fachlich abgeschlossen, Architektur bleibt unverändert. P19 sollte die
vorhandenen Funktionen zu einem verständlichen, intuitiven Arbeitsbereich zusammenführen —
kein Neubau. Erster Schritt war ein Audit des realen Codes gegen diese Spezifikation
([`P19_PLANPHASE_WORKSPACE_UX_AUDIT.md`](P19_PLANPHASE_WORKSPACE_UX_AUDIT.md)): Ergebnis war,
dass die in Abschnitt 10 dokumentierte Zielstruktur (ein `PlanPhaseWorkspace`-Drawer mit genau
vier Tabs) bereits existierte und im Kern funktionierte — die real gefundenen 14 Lücken waren
additiv/chirurgisch, keine davon erforderte ein neues Datenmodell, eine neue Capacity-Engine
oder eine zweite Planungsquelle. Verdict des Audits: **READY FOR P19 IMPLEMENTATION.**

**Umsetzung (P19.1–P19.7, parallel implementiert, danach gemeinsam gemerged und gegen die
volle Backend-Testsuite + einen manuellen Browser-Durchlauf verifiziert):**

- **P19.1 (Workspace IA):** voller Breadcrumb-Pfad im Drawer-Header statt nur der direkten
  Elternphase, clientseitig aus der bereits geladenen Phasenliste abgeleitet, klickbare
  Vorfahren wechseln die offene Phase ohne den Drawer zu schließen.
- **P19.2 (Kapazität-Polish):** `PlanPhaseDetail` bettet seit P19 `assignment_summary` und je
  `ResourceDemand` seine `assignments` ein (additive Felder, bestehende Einzel-Endpoints
  bleiben für andere Aufrufer bestehen) — löst den Großteil des N+1-Musters bei
  aufgeklappter Rollenaufschlüsselung auf. Visuelle Trennung Personenbesetzung
  (Primärpfad, hervorgehoben) vs. Rollenaufschlüsselung (sekundär, eingeklappt) geschärft.
- **P19.3 (Activity/Comments):** Comment-Threading (`parent_id`) im Frontend nachgebaut
  (Backend-Feld existierte bereits), "aus Kommentar erstellen" zusätzlich direkt in der
  Kommentarliste, Tag-Vorschlag bei Folgeobjekten um die Tags der Phase ergänzt, Activity-Feed
  zeigt jetzt auch Milestone-/Planstand-Ereignisse (Backend lieferte sie bereits).
- **P19.4 (Tags/Knowledge):** Tag-Nachbearbeitung nach Anlage bei Task/Blocker/Decision
  (Muster von `MilestoneList.tsx` übernommen), Tag-Dossier-Einträge sind klickbar (Navigation
  zur referenzierten Entität bzw. PlanPhase), neue "Verknüpfte Themen"-Karte im Übersicht-Tab.
- **P19.5 (Documents/Milestones):** Dateien-Tab im Workspace nutzt jetzt dieselbe volle
  Dokumentenkomponente wie der projektweite Dokumente-Tab (extrahiert, parametrisiert nach
  Entity-Filter) statt einer schwächeren Eigenbau-Liste; neue kompakte Meilensteine-Karte im
  Aktivität-Tab (Leaf und Parent), `PlanPhaseDetail` liefert dafür additiv `milestones`.
- **P19.6 (Planstand-UX):** kompakte "Seit Planstand VX geändert"-Zeile im Übersicht-Tab,
  clientseitig gegen den bestehenden Deviation-Endpoint gefiltert (Phase bzw. bei Parents
  zusätzlich ihre Nachfahren) — kein neuer Endpoint, keine neue Diff-Engine.
- **P19.7 (Planning-Tab-Cleanup):** `PlanPhase`-Baum ist jetzt die primäre, immer offene
  Karte im Planung-Tab; Legacy-Block (Teilprojekt-CRUD + `ResourceDemandGrid`) in einen
  eingeklappten, klar beschrifteten Abschnitt verschoben (reine Darstellungsänderung, keine
  Funktion verändert). Zusätzlich neue `ProjectMonthlyCapacityCard.tsx`: die
  derived-monthly-capacity-Werte (`GET /projects/{id}/capacity/monthly`) hatten vor P19
  **keinen Frontend-Konsumenten** — jetzt sichtbar inkl. Monats-Drilldown nach beitragender
  Leaf-Phase (additives `by_phase`-Feld, aus derselben bestehenden Berechnung abgeleitet).

**Backend-Änderungen:** ausschließlich additive Felder auf bestehenden Pydantic-Schemas
(`PlanPhaseDetail.milestones`/`.assignment_summary`, `ResourceDemandOut.assignments`,
`ProjectMonthlyCapacityEntry.by_phase`, `CommentOut`/`CommentCreate.parent_id` — Feld
existierte bereits im Modell, nur bisher nicht in Schema/API exponiert) — keine neue Tabelle,
keine neue Migration, keine geänderte Berechnungsformel.

**Verifikation:** alle sechs Backend-Testskripte (`backend/scripts/test_*.py`, je um
gezielte Assertions für die neuen additiven Felder erweitert) grün; `npm run build`
(`tsc -b && vite build`) und `npm run lint` sauber; zusätzlich ein manueller
Playwright-Durchlauf gegen den laufenden Dev-Stack (Projekt anlegen → PlanPhase mit
0,40 FTE → zwei Personen direkt zuweisen, ohne Rollenauswahl → Bedarf/Besetzt/Offen
0,40/0,40/0,00 → Kommentar mit Thread-Antwort → Milestone sichtbar im Workspace →
Monatskapazität automatisch berechnet und nur als Drilldown aufschlüsselbar, nicht editierbar
→ Legacy-Block eingeklappt, aber unverändert funktionsfähig), keine Konsolenfehler.

**Nicht Teil dieses Durchgangs** (unverändert wie im Auftrag begrenzt): kein
Tempo→PlanPhase-Mapping, keine neue Capacity-Engine, keine neue Monatsplanung, kein
Gantt-Drag&Drop, keine produktive B-8-Migration. Die zwei einzigen offenen
UX-Platzierungsfragen des Audits (Planstände zentral vs. im Workspace; Milestones als Karte
vs. eigener Tab) wurden mit begründeter Empfehlung umgesetzt (zentral/Karte) — reversibel,
kein Business-Blocker.

### 16.19 P20.1 — Jira/Tempo Mapping Domain (dieser Durchgang)

**Auftrag:** P20 verbindet die (durch P18/P19 fertige, hier unveränderte) `PlanPhase`-Planung
mit den tatsächlich gebuchten Tempo/Jira-Stunden — ausschließlich additiv, keine zweite
FTE-Quelle, keine Datumsheuristik. Die fachliche Analyse
([`P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md`](P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md),
zweifach verifiziert gegen den realen Code) empfiehlt Option F (Label-Match + manueller
Override) und kommt zu **READY FOR P20 IMPLEMENTATION**. Dieser Durchgang implementiert das
erste von acht additiven Paketen: **P20.1 — Jira/Tempo Mapping Domain** (Datenmodell +
Sync-Erweiterung + Konfliktprüfung, keine Abhängigkeiten).

**Umsetzung:**

- **`PlanPhase.jira_label`** (nullable `String(200)`) — Pendant zu `Project.jira_component`
  auf Phasenebene. Gleicher Lifecycle wie `plan_fte`: `_maybe_historize_parent_fte`
  (`routers/planning.py`) setzt bei allen drei bestehenden "Phase erhält erstes Kind"-Stellen
  (`create_plan_phase`, `update_plan_phase`-Reparenting, `reparent_children`) jetzt zusätzlich
  `jira_label` auf `NULL` und historisiert den alten Wert in `PlanHistory`
  (`feld="jira_label"`) — kein neuer Code-Pfad, dieselbe bereits bestehende Funktion erweitert.
- **Konfliktprüfung (BD-1G):** `_check_jira_label_conflict` blockiert (409) beim Anlegen
  (`POST .../plan-phases`) und Ändern (`PUT .../plan-phases/{id}`), wenn zwei Leaf-Phasen
  desselben Projekts denselben `jira_label`-Wert erhielten — mit Verweis auf die
  kollidierende Phase in der Fehlermeldung.
- **`jira_issue_cache`** (neue Tabelle: `jira_issue_key` PK, `project_id`, `labels`
  kommagetrennt, `component`, `summary`, `last_synced_at`) — befüllt von
  `jira_sync._upsert_issue_cache()`, aufgerufen aus `jira_sync.sync_project()` bei jedem
  `POST /jira/sync`. **Kein zusätzlicher Jira-API-Call:**
  `jira_client.search_issues_for_component()` fragt jetzt `fields=key,labels,components,summary`
  statt nur `key`/`labels` ab — derselbe Suchaufruf, der zuvor nur die Issue-Keys behielt.
  `jira_client.fetch_worklogs_for_component()` wurde zu `fetch_worklogs_for_issue_keys()`
  (nimmt Issue-Keys statt Component+since entgegen), da `jira_sync.sync_project()` die Issues
  jetzt ohnehin bereits einmal aufgelöst hat und sie nicht für den nativen Worklog-Fallback ein
  zweites Mal per JQL suchen muss.
- **`worklog_phase_overrides`** (neue Tabelle: `id` PK, `project_id`, `jira_issue_key`
  UNIQUE, `plan_phase_id`, `previous_status`, `note`, `created_by_person_id`, `created_at`) +
  CRUD (`GET`/`POST /projects/plan-phases/{id}/worklog-overrides`,
  `DELETE .../worklog-overrides/{jira_issue_key}`). `POST` ist ein Upsert per
  `jira_issue_key` (erneutes Anlegen mit anderer Ziel-Phase verschiebt den bestehenden
  Override statt ein Duplikat zu erzeugen — fachlich "Override bearbeiten"). Ändert nie
  Jira/Tempo-Originaldaten. Kein Auth-/Session-Mechanismus im Backend (verifiziert) —
  `created_by_person_id` ist wie überall im Produkt ein manuell gewählter, nullable
  Personen-Verweis, keine neue Auth-Anforderung. `previous_status` bleibt bis P20.2
  unbefüllt/optional (der Resolver, der ihn eigentlich berechnet, existiert noch nicht).
- **Migration `0006_p20_jira_phase_mapping`** (additiv, `down_revision =
  "0005_p18_hierarchy_foundation"`).

**Bewusst nicht Teil von P20.1** (folgt in späteren Paketen, siehe
P20-Dokument Abschnitt 30/31): der eigentliche Worklog→PlanPhase-Resolver (P20.2), Unmapped/
Ambiguous/Coverage (P20.3), die Verdrahtung von `ist_hours`/`effort_consumption_pct` in
`phase_metrics_calc`/`PhaseMetricsOut` (P20.4) — beide bleiben bis dahin unverändert `null` —,
Workspace-UX/Label-Picker/Mapping-Preview (P20.5), Personen-Drilldown (P20.6),
Coverage-UI (P20.7). `GET /gap`, `GET /forecast`, `health_calc.compute_project_health`,
`jira_sync.berechne_ist_fte` sind durch P20.1 unverändert (nur additiv erweitert, keine
bestehende Formel angefasst).

**Verifikation:** neues Testskript
`backend/scripts/test_p20_jira_phase_mapping.py` (jira_label Create/Update/Konflikt/
Parent-Übergang inkl. PlanHistory-Eintrag, WorklogPhaseOverride-CRUD inkl. Upsert/404,
`jira_sync._upsert_issue_cache` inkl. Idempotenz) sowie alle sechs bestehenden
Backend-Testskripte (u. a. `test_planning_phase_tree_api.py`, das denselben
Parent-Übergangs-Pfad testet) unverändert grün — keine Regression am `plan_fte`-Lifecycle.
App-Import, Migration auf frischer SQLite-DB und OpenAPI-Schema-Generierung geprüft.

---

## 17. Historie / Architecture Decision Log

Dieser Abschnitt ist bewusst historisch — nichts hier ist eine aktuelle Anforderung. Er
existiert, damit Entscheidungsgründe nicht verloren gehen.

### 17.1 Ursprüngliches Excel-Modell (Schritt 1, MVP)

Das ursprüngliche Konzept übernahm die Planungslogik des Excel/VBA-Tools bewusst 1:1
(Struktur, Phasencodes `p/k/t/s/g/?`, FTE-Raster als editierbares Gitter "wie Excel"),
ergänzt um Jira-Ist-Daten, Team-Stammdaten und Gap-Analyse. Datenmodell:
`gantt_phases`/`fte_plan` je Teilprojekt/Monat, `team_members`/`assignments` für
Personenzuordnung. Das war eine bewusste, für den MVP sinnvolle Entscheidung — eine
1:1-Migration senkt die Einstiegshürde für Nutzer:innen des alten Tools.

### 17.2 Additive Parallelphase (Phase 17–19, "kein Big-Bang-Wechsel")

Ab Phase 17 wurden `PlanPhase`/`Milestone`/`ResourceDemand`/`ResourceAssignment` als
Zielarchitektur-native Entitäten eingeführt — **additiv und zunächst leer**, ausdrücklich
ohne automatischen Sync aus den bestehenden Gantt-Zellen. Das alte Gantt-Grid blieb in dieser
Phase explizit "die einzige Quelle für die Monatsplanung im Frontend". Begründung: ein
Migrationspfad (1-Zeichen-Phasencode+Monat → strukturierte Start-/Enddaten) sollte
UI-getrieben entschieden werden, nicht vorab. `TeamMember`/`Assignment` liefen bewusst
komplett parallel zu `Person`/`ResourceDemand`/`ResourceAssignment` — "keine Migration, keine
Bridge", das war zu diesem Zeitpunkt der geforderte Grundsatz, kein Versehen.

### 17.3 Legacy Cutover (Phase 26.2–26.9)

Phase 26 löste die additive Parallelphase auf: **26.2** stellte die Planung-Tab-UI
vollständig auf `PlanPhase`/`Milestone` um ("Nutzerentscheidung: ersetzen, nicht parallel
bestehen lassen"). **26.3** ersetzte das FTE-Raster durch `ResourceDemandGrid`. **26.9
(Legacy Cutover, Welle 2)** entfernte die alten Tabellen strukturell, mit Datenkonvertierung
statt Drop-and-Pray:

- `gantt_phases`/`project_gantt_phases` → `PlanPhase` (aufeinanderfolgende gleiche
  Phasencode-Monate zu einer Phase mit `forecast_start`/`forecast_end` zusammengeführt) +
  `Milestone` für `?`-Zellen.
- `fte_plan`/`project_fte_plan` → `ResourceDemand` (projektweite Monatssummen, Default-Rolle
  "Allgemein").
- `team_members` → `Person` (Best-Effort-Match über `jira_account_id`/Name) +
  `ResourceProfile`.
- `assignments` → `ResourceDemand` + `ResourceAssignment` je Projekt-Monat.
- Danach gedroppt: `assignments`, `team_members`, `gantt_phases`, `fte_plan`,
  `project_gantt_phases`, `project_fte_plan`, `projects.projektleiter` (Freitext).

Migration `0003_phase26_legacy_cutover` (heute Teil der konsolidierten Migrationskette, siehe
Alembic-Historie im Repo). Seitdem sind `PlanPhase`/`Milestone`/`ResourceDemand`/`Person` die
**eine** führende Wahrheit für Planung, Kapazität und Personen.

### 17.4 Frühere Roadmap-Nummerierung

Die Umsetzungsschritte wurden ursprünglich zweifach nummeriert (Section-11-Liste 1–27 vs.
eine separate 12.4-Phasentabelle 13–29), was zu einer Kollision führte: Section-11-Punkt 27
("Planungs-/Kapazitätskonsolidierung", das P1-P11-Paket dieses Dokuments) hatte denselben
Namen wie "Phase 27" in der alten 12.4-Tabelle ("UX Consolidation", ursprünglich als "reine
UI-Politur" geplant). Mit diesem Konsolidierungsdurchgang entfällt die doppelte Nummerierung
zugunsten der Umsetzungsstand-Liste in Abschnitt 16. Zukünftige, noch nicht terminierte
Großvorhaben (KI-Readiness Review, AI Project Agent, Vector-/Embedding-Layer,
Enterprise-SSO, automatische Ressourcenoptimierung, What-if/Szenarioplanung) bleiben
"Bucket D" — bewusst später, siehe Abschnitt 15.

### 17.5 Frühere offene Fragen, die inzwischen beantwortet sind

- ~~Mapping Jira-Ticket → Kapa-Projekt: Component, Label oder Custom Field?~~ Entschieden:
  Component/Label über `projects.jira_component`.
- ~~Kein Migrationstool im Repo~~ Alembic eingeführt (Phase 13), Policy siehe Repo
  (`backend/alembic/`, `check_migrations.py`).
- ~~"Offene Aufgaben" ist ein Alias auf offene Risiken+Entscheidungen~~ Echtes `tasks`-Modell
  seit Schritt 10.
- ~~Milestones sind bewusst kein eigenes Datenmodell, sondern der Gantt-Phasencode `?`~~
  Überholt seit Phase 17: `Milestone` ist eine eigenständige Tabelle.
- ~~`TeamMember`/`Assignment` bleiben parallel zu `Person`/`ResourceDemand` bestehen~~
  Überholt seit Phase 26.9: entfernt, siehe 17.3.

### 17.6 Migrationsstrategie & Policy

Der Alembic-Verlauf wurde einmalig konsolidiert (Squash der historischen Kette 0001–0014 in
eine Baseline `0001_consolidated`, da zwei spätere Revisionen ein reines
Drop-and-Recreate-Paar ohne fachlichen Mehrwert bildeten). Aktuelle Kette:
`0001_consolidated` → `0002_align_project_nullable` → `0003_phase26_legacy_cutover` →
`0004_planning_consolidation`. `backend/app/db_bootstrap.py` erkennt beim Start automatisch
zwischen frischer DB, bekannter Revision und (historisch) unbekannten/abgelösten
Zwischenständen.

Policy (verbindlich für künftige Schemaänderungen):

1. Jede Schemaänderung ist eine Alembic-Revision, kein manuelles `ALTER TABLE`.
2. Einmal referenzierte Revisionen werden nicht rückwirkend gelöscht.
3. Destruktive Migrationen (Spalten-/Tabellen-Drop) nur mit vorheriger Datenkonvertierung,
   nicht Drop-and-Pray (siehe 26.9 als Referenzbeispiel).
4. `python backend/check_migrations.py` vor jedem Commit mit Schemaänderung (prüft
   Kettenintegrität, Drift gegen `models.py`, Seeds, Downgrade/Upgrade-Roundtrip).
5. `alembic/env.py` liest `DATABASE_URL` aus `app.database`, keine eigene Konfiguration.

### 17.7 P18 Pass 1 — superseded Grob-/Feinplanung & Capacity Reconciliation (Design, nie implementiert)

**Herkunft:** vormals Abschnitt 6a im Hauptteil. Mit dem P18-Finalization-Cleanup (Abschnitt 16.17) hierher verschoben, damit Abschnitt 6 nur noch die aktuelle Architektur zeigt. Inhalt unverändert und vollständig erhalten (kein Kürzen einer sauber durchgeführten Analyse) — er ist und bleibt **fachlich nicht mehr gültig**.

> ⚠️ **Dieser Abschnitt ist superseded.** P18 Pass 2 (Abschnitt 6) hat die hier beschriebene
> Zwei-Achsen-Architektur (Grobplanung/Feinplanung + Reconciliation-Formel) erneut geprüft und
> durch eine hierarchische `PlanPhase`-only-Architektur ersetzt, die dieselbe fachliche
> Anforderung (frühe grobe Kapazitätssicht, schrittweise Konkretisierung, keine Doppelzählung)
> ohne eine zweite Planungsebene erfüllt (siehe
> [`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)
> Abschnitt 2 für die Begründung). Dieser Abschnitt bleibt **ausschließlich aus
> Nachvollziehbarkeit** im Dokument stehen (der Analysedurchgang war real und sauber
> durchgeführt) — er ist **keine** gültige Umsetzungsgrundlage mehr. BD-7/BD-8/BD-9 (unten)
> sind durch Abschnitt 6 obsolet. Bei jedem Widerspruch zu Abschnitt 6 gilt 6.

**Status dieses Abschnitts:** Fachlich vollständig spezifiziert und gegen Code/CONCEPT
geprüft (Codebase Validation Matrix siehe separates
[`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md`](P18_DESIGN_AND_IMPLEMENTATION_PLAN.md)). **Nicht
implementiert** — und nach Pass 2 auch nicht mehr zur Implementierung vorgesehen. Beschreibt
ein geprüftes, aber nicht mehr empfohlenes Zielverhalten. Ist-Zustand bleibt weiterhin
Abschnitt 6 (aktuelles Verhalten) bis zur Umsetzung von Pass 2.

#### 6a.1 Warum zwei Ebenen — fachliche Begründung

Ein Projekt wird nicht an einem Tag vollständig tagegenau planbar. Es durchläuft typischerweise:

1. **Kapazitätsrelevant, aber noch nicht strukturiert:** Der Projektleiter weiß "im Oktober
   brauchen wir ca. 1,5 FTE", aber noch keine Phasen, Rollen oder Personen.
2. **Zunehmend konkretisiert:** Phasen entstehen, zunächst grob befüllt (nur `plan_fte`),
   dann mit Rollen-Aufschlüsselung, dann mit Personenbesetzung.
3. **Vollständig fein geplant:** Jede relevante Kapazität steckt in tagegenauen `PlanPhase`s.

**Grobplanung** (Abschnitt L6.1 (Historie 17.8), Portfolio-/Monatsachse) beantwortet: *"Wie viel Kapazität
erwarten wir ungefähr für dieses Projekt in diesem Monat?"* — Zweck: Portfolio-/
Teamplanung kann kommende Projekte berücksichtigen, bevor sie strukturiert planbar sind.

**Feinplanung** (Abschnitt 5, tagegenaue `PlanPhase`s + Phasenachse) beantwortet: *"Wann
benötigen wir wie viel Kapazität für welche konkrete Projektphase, später welche
Rollen/Personen?"*

Beide sind **Konkretisierungsgrade derselben Planung**, keine unabhängigen Bedarfe — ein
Projekt plant nicht zweimal Kapazität, es beschreibt denselben erwarteten Aufwand mit
zunehmender Präzision.

#### 6a.2 Keine neue Tabelle, keine neue Engine

Grobplanung ist **kein neues Modell**. Sie ist exakt das bereits existierende
`ResourceDemand` mit `plan_phase_id = NULL` (Abschnitt L6.1 (Historie 17.8)) — hier nur erstmals fachlich
benannt und mit einer expliziten Reconciliation zur Feinplanung versehen. Es wird **kein**
neues `gross_plan_fte`-Feld, keine zweite `ResourceDemand`-Tabelle und keine zweite
Available-Capacity-Berechnung eingeführt (Abschnitt 20 der Auftragsvorgabe, verbindlich).

Rollenbedarf innerhalb der Grobplanung (Abschnitt 17 der Auftragsvorgabe, "Level 2": z. B.
Oktober → Senior Consultant 0,80 + Consultant 0,70) ist bereits heute möglich: mehrere
`ResourceDemand`-Zeilen mit `plan_phase_id = NULL`, unterschiedlichem `resource_role_id`,
demselben `period`. Kein neues Feld nötig — `ResourceDemandGrid` bildet das bereits als
Rolle-Zeile ab.

#### 6a.3 Definitionen

| Begriff | Definition |
|---|---|
| **Grobplanung** | Menge der `ResourceDemand`-Zeilen eines Projekts mit `plan_phase_id = NULL`, aggregiert je Monat. Antwortet auf Projekt-/Monatsebene, unabhängig von Phasen/Rollen/Personen (auch wenn Rollen/Personen optional bereits angereichert sein können, Abschnitt 6a.5). |
| **Feinplanung** | Menge der `PlanPhase`-Zeilen eines Projekts (unabhängig davon, ob sie zusätzlich über phasengebundene `ResourceDemand`/`ResourceAssignment` weiter aufgeschlüsselt sind). Trägt tagegenaue Zeiträume. |
| **Grobplanstunden(Monat)** | Aus der Grobplanung abgeleitete Planstunden eines Monats (Abschnitt 6a.4). |
| **Feinplanstunden(Monat)** | Aus der Feinplanung abgeleitete Planstunden eines Monats (Abschnitt 6a.4/6a.6, Monatsverteilungsalgorithmus). |
| **Noch grob** | `max(Grobplanstunden(Monat) − Feinplanstunden(Monat), 0)` — der Teil der Grobplanung, der noch nicht durch konkrete Phasen beschrieben ist. |
| **Konkretisierung / Konkretisierungsgrad** | `Feinplanstunden(Monat) / Grobplanstunden(Monat) × 100`, sofern `Grobplanstunden(Monat) > 0`. **Kein Projektfortschritt**, sondern ausschließlich ein Maß dafür, wie viel des grob erwarteten Kapazitätsbedarfs bereits durch konkrete Phasen beschrieben ist (Abschnitt 6a.7). |
| **Konsumption(Monat)** | Der in Portfolio-/Team-/GAP-Sichten tatsächlich gezählte Wert je Projekt/Monat: `max(Grobplanstunden(Monat), Feinplanstunden(Monat))` (Abschnitt 6a.6, BD-7). |
| **Planstunden (allgemein)** | `FTE × Werktage(Zeitraum) × VOLLZEIT_WOCHENSTUNDEN/5` — identische Formel wie `phase_metrics_calc.plan_hours` (Abschnitt 5.2), nur mit unterschiedlicher Quelle für FTE und Zeitraum je nach Grob-/Feinachse. |

#### 6a.4 Plan-FTE- und Planstunden-Semantik geschärft

`PlanPhase.plan_fte` (und analog jeder `ResourceDemand.fte`-Wert) ist fachlich **kein
punktueller Stellenbedarf**, sondern ein **durchschnittlicher Ressourceneinsatz über den
Zeitraum**: "0,50 FTE über 12 Arbeitstage" bedeutet 0,50 × 12 × 8h = 48 Planstunden verteilt
über den Zeitraum — nicht "eine halbe Stelle an jedem der 12 Tage" im Sinn einer täglich
fixen Kapazitätsreservierung (die Engine kennt keine Tagesauflösung unterhalb des
Zeitraums). Diese Semantik gilt bereits heute für `plan_hours` (Abschnitt 5.2); P18 präzisiert
sie nur explizit, weil sie für die Monatsverteilung (6a.6) fachlich vorausgesetzt wird.

**UI-Bezeichnung (P18-Vorschlag, noch nicht umgesetzt):** Die technische Semantik ändert sich
nicht. Vorschlag für die Kopfzeile im Kapazitäts-Tab: "Geplanter Ressourcenbedarf" statt
"Plan-Aufwand", mit Sekundärzeile "≈ 48 Planstunden über 12 Arbeitstage" direkt daneben, damit
der Zusammenhang FTE↔Stunden nicht erklärungsbedürftig bleibt. Eine finale
Bezeichnungsentscheidung ist kein Blocker für P18.1 (Backend), da sie rein UI-seitig ist.

#### 6a.5 Reifegrade der Grobplanung (Level 1–4)

Bereits heute technisch abbildbar, ohne neue Architektur:

| Level | Beispiel | Modell |
|---|---|---|
| 1 — nur Gesamt-FTE | "Oktober ca. 1,5 FTE" | eine `ResourceDemand`-Zeile mit einer generischen/Default-Rolle, `plan_phase_id = NULL` |
| 2 — Rollen | "0,8 Senior + 0,7 Consultant" | mehrere `ResourceDemand`-Zeilen, `plan_phase_id = NULL`, unterschiedliche `resource_role_id` |
| 3 — Personen | "Dominik 0,5, Max 0,3" | `ResourceAssignment` auf einer Grob-`ResourceDemand` (bereits ohne Einschränkung im Code möglich, Abschnitt L6.1 (Historie 17.8)) |
| 4 — Feinplanung | tagegenaue `PlanPhase`s, ggf. mit eigener Rollen-/Personen-Aufschlüsselung | `PlanPhase` + phasengebundene `ResourceDemand`/`ResourceAssignment` |

Level 1–3 sind kein neues Datenmodell — nur eine neue fachliche Lesart des bereits
existierenden `ResourceDemand`/`ResourceAssignment`. **Keine BD nötig für Level 1–3.**

#### 6a.6 Monatsverteilungsalgorithmus (Feinplanstunden)

Ein `PlanPhase`-Zeitraum ist tagegenau und kann Monatsgrenzen überschreiten
("Konfiguration", 19.10.–13.11., 0,80 FTE). Für die monatliche Reconciliation werden die
Planstunden der Phase **anteilig nach Werktagen** auf die berührten Monate verteilt — **keine
pauschale 50/50-Aufteilung.**

```
weekdays_total      = count_weekdays_in_range(forecast_start, forecast_end)      # bestehend, capacity_calc.py
plan_hours_total     = plan_fte × weekdays_total × VOLLZEIT_WOCHENSTUNDEN / 5      # bestehend, phase_metrics_calc.plan_hours

je Monat M, der [forecast_start, forecast_end] überlappt:
    overlap_start    = max(forecast_start, Monatsanfang(M))
    overlap_end      = min(forecast_end,   Monatsende(M))
    weekdays_M       = count_weekdays_in_range(overlap_start, overlap_end)        # bestehend
    phase_hours(M)   = plan_hours_total × weekdays_M / weekdays_total             # NEU (Verteilungsschlüssel)
```

**Kein Feiertagsabzug** (konsistent mit BD-4/`plan_hours`, Abschnitt 5.2 — dieselbe
Werktage-Definition Mo–Fr wird wiederverwendet, keine abweichende Baseline für die
Monatsverteilung). Reuse: `capacity_calc.count_weekdays_in_range` und
`capacity_calc._month_bounds` (Signatur ggf. `public` machen), keine neue Kalenderlogik.
Neue Funktion (Vorschlag P18.1): `phase_metrics_calc.monthly_distribution(plan_fte,
forecast_start, forecast_end) -> dict[str, float]` (Periode im "Apr 26"-Format → Stunden).

**Feinplanstunden(Monat)** eines Projekts = Summe von `phase_hours(M)` über alle
`PlanPhase`s des Projekts (unabhängig von Status; Abschnitt 6a.9 regelt, ob `entfaellt`
ausgenommen wird — offen, siehe Testfälle). **Bewusst nicht** aus der phasengebundenen
`ResourceDemand`-Rollen-Aufschlüsselung berechnet — deren Summe kann von `plan_fte`
abweichen (`open_fte`, Abschnitt 3/6) und ist zudem nicht monatlich aufgelöst (Abschnitt
L6.1). `plan_fte` bleibt die einzige Quelle für Feinplanstunden, identisch zum bestehenden
Grundsatz "plan_fte bleibt führend".

**Vollständig durchgerechnetes Beispiel** (Projekt "Red Bull WMS Rollout", Kalenderjahr 2026,
`VOLLZEIT_WOCHENSTUNDEN = 40`):

| Phase | Zeitraum | Plan-FTE | Werktage gesamt | Planstunden gesamt |
|---|---|---|---|---|
| Pflichtenheft | 01.10.–17.10. | 0,50 | 12 | 48,0 h |
| Konfiguration | 19.10.–13.11. | 0,80 | 20 | 128,0 h |
| Test | 16.11.–27.11. | 1,20 | 10 | 96,0 h |

Monatsverteilung (Werktage Okt 2026 = 22, Nov 2026 = 21, Dez 2026 = 23):

| Phase | Okt-Anteil | Nov-Anteil | Dez-Anteil |
|---|---|---|---|
| Pflichtenheft | 12 Werktage → 48,0 h | — | — |
| Konfiguration | 10 Werktage → 64,0 h | 10 Werktage → 64,0 h | — |
| Test | — | 10 Werktage → 96,0 h | — |
| **Feinplanstunden(Monat)** | **112,0 h** | **160,0 h** | **0,0 h** |

Grobplanung desselben Projekts (Beispiel aus der Auftragsvorgabe): Okt 1,50 FTE, Nov 2,00
FTE, Dez 1,00 FTE →

| | Grobplanstunden (FTE × Werktage × 8) | Feinplanstunden | Noch grob | Konsumption = max(…) | Konkretisierungsgrad |
|---|---|---|---|---|---|
| Okt | 1,50 × 22 × 8 = **264,0 h** | 112,0 h | 152,0 h | 264,0 h | 42,4 % |
| Nov | 2,00 × 21 × 8 = **336,0 h** | 160,0 h | 176,0 h | 336,0 h | 47,6 % |
| Dez | 1,00 × 23 × 8 = **184,0 h** | 0,0 h | 184,0 h | 184,0 h | 0,0 % |

(FTE-Rückrechnung für die UI, sofern gewünscht: `Stunden / (Werktage_Monat × 8)`, z. B. Okt
Feinplanung ≈ 112 / 176 = 0,64 FTE.)

#### 6a.7 Konkretisierungsgrad ("Planungsreife") — keine Ampel, kein Fortschritt

`Konkretisierungsgrad(Monat) = Feinplanstunden(Monat) / Grobplanstunden(Monat) × 100`, nur
wenn `Grobplanstunden(Monat) > 0` (sonst nicht definiert/`null`, nicht 0 % — "keine
Grobplanung" ist ein anderer Zustand als "0 % konkretisiert", siehe Abschnitt 6a.9 Edge
Case "keine Grobplanung"). UI-Label: **"Planung konkretisiert X %"**, ausdrücklich **nicht**
"Fortschritt" (Verwechslungsgefahr mit `PlanPhase.progress`, das ohnehin deprecatet ist,
Abschnitt 3) und **keine 🟢/🟡/🔴-Bewertung** (konsistent mit BD-3, das dieselbe
Zurückhaltung für alle Phasenmetriken bereits festlegt).

#### 6a.8 Available Capacity im Planungsfluss (Personenbesetzung prüfen)

Ziel: bei einer `ResourceAssignment` (Grob- oder Phasenachse) soll der Projektleiter sehen,
ob die Person im relevanten Zeitraum tatsächlich Kapazität hat — **ohne neue
Capacity-Engine** (Abschnitt 20 der Auftragsvorgabe).

- **Grobachse:** unverändert `compute_person_capacity(db, person_id, demand.period)` —
  passt bereits, weil eine Grob-Demand ohnehin genau einen Monat trägt (Abschnitt L6.1 (Historie 17.8)).
- **Phasenachse:** heute geprüft nur gegen den einen in `ResourceDemand.period` gespeicherten
  Monat (Abschnitt L6.2 (Historie 17.8)), nicht gegen den vollen `PlanPhase`-Zeitraum. **Minimal-invasiver
  P18-Vorschlag:** `compute_person_capacity` um eine Variante ergänzen, die statt eines
  einzelnen `period`-Strings einen Datumsbereich nimmt und intern **denselben
  Monatsverteilungsschlüssel wie 6a.6** anwendet — je überlappendem Monat
  `compute_person_capacity(person, Monat)` aufrufen und die verfügbare Kapazität
  werktage-gewichtet auf den angefragten Teilzeitraum herunterrechnen. Keine neue
  Holiday-/Absence-/InternalAllocation-Abfrage — reine Wiederverwendung, nur mit einem
  Zeitraum statt eines Monats als Eingabe. Formel und Konsequenzen (Rundungsverhalten bei
  Teilmonaten) sind in
  [`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md`](P18_DESIGN_AND_IMPLEMENTATION_PLAN.md) Abschnitt
  11 im Detail ausgeführt.
- Absence/Holiday/InternalAllocation fließen dabei exakt so ein, wie sie es heute in
  `compute_person_capacity` bereits tun (Abschnitt L6.2 (Historie 17.8)) — **keine idealisierte Formel**, keine
  neue HR-Integration, kein Personio (Abschnitt 21 der Auftragsvorgabe).

#### 6a.9 Planstände (Baseline) und Grobplanung

Heute friert ein `BaselineSnapshot` keine `ResourceDemand`-Werte ein (Abschnitt L6.4 (Historie 17.8)). Damit
lässt sich nicht rekonstruieren "im Oktober hatten wir ursprünglich 1,5 FTE grob geplant,
später waren es 1,8 FTE." Der generische `BaselineEntry`-Mechanismus
(`entity_type`/`entity_id`/`field`, Abschnitt 4) ist dafür bereits ausreichend generisch —
`entity_type = "resource_demand"`, `field = "fte"` wäre ohne Schemaänderung möglich. Die
fachliche Frage ist nicht die Technik, sondern der Umfang: friert man jede einzelne
Grob-`ResourceDemand`-Zeile ein (granular, aber ein Planstand kann dann sehr viele Zeilen
erzeugen) oder nur die aggregierten Grobplanstunden je Monat (kompakter, aber keine
Rollen-Historie mehr)? **Offen — BD-8.**

#### 6a.10 Capacity Consumption Source-of-Truth-Matrix

Die zentrale Entscheidung dieses Designs — welcher Wert zählt wo:

| Situation | Portfolio-/Team-Kapazität, Cockpit, Allocation/Capacity Gap |
|---|---|
| Projekt/Monat nur grob geplant (keine überlappende Feinplanung) | Grobplanstunden |
| Projekt/Monat nur fein geplant (keine Grobplanung) | Feinplanstunden |
| Projekt/Monat teilweise fein geplant (Feinplanstunden < Grobplanstunden) | Grobplanstunden (Fein zählt implizit mit, siehe Formel) |
| Projekt/Monat vollständig/über Plan fein geplant (Feinplanstunden ≥ Grobplanstunden) | Feinplanstunden |
| **Formel (alle Fälle einheitlich)** | **`Konsumption(Monat) = max(Grobplanstunden(Monat), Feinplanstunden(Monat))`** |
| Phasengebundene `ResourceDemand` (Rollen-Aufschlüsselung einer Phase) | zählt **nicht separat** in der Monats-Konsumption — nur `plan_fte` der Phase fließt über Feinplanstunden ein (Abschnitt 6a.6); die Rollen-Aufschlüsselung bleibt eine reine Innenansicht der Phase (`open_fte`, Abschnitt 3) |
| `ResourceAssignment` (Grob- oder Phasenachse) | zählt in die **personenbezogene** Auslastung (Utilization Gap, `compute_portfolio_utilization`), nicht direkt in die Projekt-Monats-Konsumption |

**Bewertung der Strategien (Vorgabe-Optionen A–D):** Option A (`max(Grob, Fein)`) und Option
B (`Fein + max(Grob − Fein, 0)`) sind **algebraisch identisch**
(`Fein + max(Grob−Fein,0) ≡ max(Grob,Fein)`), sobald auf Gesamt-Projekt/Monat-Ebene
verglichen wird (keine rollenscharfe Aufteilung der Grobplanung vorausgesetzt). **Empfehlung:
Option A/B kombiniert** — intern Formel A (einfach, ein Aggregat), UI-seitig Darstellung B
("konkret geplant" + "noch grob" als zwei sichtbare Anteile, wie im Zielbild
Abschnitt 6a.6-Tabelle). Option C (expliziter Planungsmodus GROB/FEIN je Projekt/Monat) wurde
geprüft und verworfen: sie würde eine neue Statusdimension einführen, die bei
Phasen-über-Monatsgrenzen (6a.6) nicht sauber "ein Monat = ein Modus" abbildbar ist (ein
Monat kann teilweise fein sein) — mehr Komplexität ohne fachlichen Zusatznutzen gegenüber
der stetigen `max()`-Formel.

**Warum das keine reine Formel-Implementierung, sondern eine BD ist (BD-7):** Die Formel
ändert das **heutige** (in L6.3 dokumentierte, ungefilterte Summen-)Verhalten der
Portfolio-Endpoints. Das ist eine Verhaltensänderung an produktiv sichtbaren Zahlen
(Portfolio-Dashboard, Cockpit, Controlling), kein reiner Bugfix im technischen Sinn — daher
Business-Freigabe vor Umsetzung nötig, auch wenn die fachliche Analyse eindeutig für die
`max()`-Formel spricht.

#### 6a.11 Teilprojekte

Grobplanung bleibt **projektweit** (`ResourceDemand` hat kein `subproject_id`-Feld, Abschnitt
4) — keine neue Dimension. Feinplanung kann bereits heute optional über
`PlanPhase.subproject_id` auf Teilprojekte verteilt werden (Abschnitt 5.4). Die
Monatsverteilung (6a.6) rechnet Feinplanstunden je Projekt/Monat unabhängig davon, ob eine
Phase einem Teilprojekt zugeordnet ist — eine teilprojektscharfe Reconciliation (Grob vs.
Fein je Teilprojekt) ist **kein Bestandteil von P18**, da Grobplanung dafür keine
Teilprojekt-Dimension hat und keine bekannte fachliche Notwendigkeit dafür vorliegt (kein
neuer Bedarf identifiziert, daher keine neue Dimension eingeführt).

#### 6a.12 Edge Cases

| Fall | Verhalten |
|---|---|
| Keine Grobplanung, nur Feinplanung | Gültiger Zustand (kleines Projekt, Phasen sofort bekannt). `Grobplanstunden(Monat) = 0` → Konkretisierungsgrad `null` (nicht 0 %, Abschnitt 6a.7), Konsumption = Feinplanstunden. Keine künstliche Grobplanung wird erzeugt. |
| Nur Grobplanung, keine Feinplanung | Gültiger Zustand (Projekt in früher Phase). `Feinplanstunden(Monat) = 0` → Konkretisierungsgrad 0 %, Konsumption = Grobplanstunden. Hauptzweck der Grobplanung (Abschnitt 6a.1). |
| Feinplanung > Grobplanung | Kein Fehler, keine automatische Anpassung der Grobplanung. UI zeigt "Grob geplant 1,50 FTE / Konkret geplant 1,80 FTE / Abweichung +0,30 FTE" als Planungsabweichung. Konsumption = Feinplanstunden (Formel 6a.10). |
| Feinplanung < Grobplanung | Erwarteter Zwischenzustand während der Konkretisierung. "Noch grob" > 0 (6a.3). Konsumption = Grobplanstunden. |
| Phase über Monatsgrenze | Monatsverteilungsalgorithmus 6a.6 (werktage-anteilig, kein 50/50). |
| Projektstart/-ende mitten im Monat | Deckt sich automatisch mit 6a.6, da `count_weekdays_in_range` nur den tatsächlichen Überlappungszeitraum zählt — kein Sonderfall nötig. |
| Vollständig fein geplantes Projekt | Historische Grobplanung bleibt in der DB erhalten (kein Auto-Löschen, Abschnitt 11 der Auftragsvorgabe) — wertvoll als ursprüngliche Kapazitätserwartung/Portfolio-Vergleich/Planungsreife-Indikator, zählt aber operativ nicht mehr zusätzlich (Konsumption = Feinplanstunden, sobald diese ≥ Grobplanstunden). |
| Person ohne `ResourceProfile`/`WorkingTime` | `compute_person_capacity` liefert `None` (bestehendes Verhalten, Abschnitt L6.2 (Historie 17.8)) — Aufrufer blendet die Person in Kandidatenlisten aus, keine Kapazitätsprüfung möglich, kein Fehler. |
| Urlaub/Krankheit (`Absence`) | Fließt bereits heute in `compute_person_capacity` über `absence_fte` ein (Abschnitt L6.2 (Historie 17.8)), unverändert für 6a.8. |
| Feiertag (`Holiday`) | Fließt bereits heute in `compute_person_capacity` über `holiday_fte` ein — **nur** dort (personenbezogene Available Capacity). Für Planstunden/Monatsverteilung (6a.6) gilt weiterhin BD-4 (kein Feiertagsabzug) — zwei unterschiedliche, bereits heute bestehende Konventionen, die P18 nicht vereinheitlicht. |
| Interne Allokation | Fließt bereits heute über `internal_fte` in `compute_person_capacity` ein, unverändert. |
| Überbuchte Person | `available_fte` kann negativ werden (keine Untergrenze in der Formel) — bereits heute möglich, P18 ändert daran nichts; UI zeigt Unterdeckung (Abschnitt 22 der Auftragsvorgabe: "Benötigt 0,50 / Verfügbar 0,31 / Unterdeckung 0,19"). |

#### 6a.13 API (bestehend vs. Zielbild)

**Bestehend, unverändert wiederverwendet:** `GET/POST/PUT/DELETE /projects/{id}/resource-demands`,
`/resource-demands/{id}/assignments`, `/resource-demands/{id}/candidates`,
`GET /people/{id}/capacity`, `GET /projects/{id}/plan-phases`, `GET
/plan-phases/{id}/metrics` (`backend/app/routers/capacity.py`/`planning.py`).

**Neu, additiv (P18-Vorschlag, noch nicht implementiert):**

```
GET /projects/{id}/capacity/reconciliation?periods=Okt 26,Nov 26,Dez 26

→ [
    {
      "period": "Okt 26",
      "grob_hours": 264.0, "grob_fte_equiv": 1.5,
      "fein_hours": 112.0, "fein_fte_equiv": 0.64,
      "noch_grob_hours": 152.0,
      "konsumption_hours": 264.0,
      "konkretisierungsgrad_pct": 42.4
    },
    ...
  ]
```

Aggregiert bestehende Bausteine (`ResourceDemand`-Summe für Grob, `phase_metrics_calc`-Werte
für Fein), keine neue Tabelle, kein neuer Schreibpfad. Genutzt vom neuen UI-Block
"Planungsstand Kapazität" (Abschnitt 6a.14). Vorschlag, Endpoint-Pfad/-Form ist mit dem
Implementierungspaket P18.1 final abzustimmen (siehe Implementation Plan).

#### 6a.14 UX-Zielbild (Entwurf, nicht implementiert)

Im Planung-Tab, unterhalb von `ResourceDemandGrid` ("Projektkapazität nach Monat"):

```
Planungsstand Kapazität

Oktober
  Grob geplant        1,50 FTE
  Konkret geplant      1,10 FTE
  Noch grob             0,40 FTE
  Planung konkretisiert  73 %

November
  Grob geplant         2,00 FTE
  Konkret geplant       1,60 FTE
  Noch grob              0,40 FTE
  Planung konkretisiert  80 %

[Monatliche Grobplanung bearbeiten] → öffnet/scrollt zu ResourceDemandGrid (kein neues
Formular, bestehende Komponente bleibt Bearbeitungsoberfläche)
```

Im `PlanPhaseWorkspace`-Drawer, Tab "Kapazität" (`PlanPhaseCapacityTab.tsx`): unverändert wie
Abschnitt L6.1 (Historie 17.8), keine neuen Elemente vorgesehen — die Reconciliation ist eine
Projekt-/Monatssicht, keine Phasensicht.

#### 6a.15 User Flows (Zielbild)

1. **Neues zukünftiges Projekt grob planen:** Projekt anlegen → Planning-Tab →
   `ResourceDemandGrid` → je Monat eine Zeile (Default-Rolle) mit FTE befüllen. Keine
   `PlanPhase` nötig.
2. **Rollen grob planen:** In `ResourceDemandGrid` weitere Rollen-Zeile hinzufügen, je Monat
   befüllen (Level 2, Abschnitt 6a.5).
3. **Personen grob reservieren:** Zelle anklicken → bestehendes "Person zuordnen"-Panel
   (bereits vorhanden, Abschnitt L6.1 (Historie 17.8)) nutzen (Level 3).
4. **Erste `PlanPhase` erstellen:** Planning-Tab → "+ Phase hinzufügen" → Start/Ende/Plan-FTE.
   Reconciliation-Block (6a.14) aktualisiert sich automatisch (Feinplanstunden > 0).
5. **Weitere Phasen konkretisieren:** Weitere Phasen anlegen, bis der Monat vollständig
   abgedeckt ist ("Noch grob" nähert sich 0).
6. **Grob-vs-Fein prüfen:** Reconciliation-Block ansehen, "Planung konkretisiert X %" pro
   Monat.
7. **Phase mit Rollen aufschlüsseln:** `PlanPhaseWorkspace` → Tab "Kapazität" →
   Rollen-Aufschlüsselung wie Abschnitt L6.1 (Historie 17.8) (unverändert).
8. **Personen zuordnen:** Wie 7, "Person zuordnen" je Rollen-Demand (unverändert).
9. **Unterdeckung erkennen:** Kandidatenliste/Available-Capacity-Anzeige (Abschnitt 6a.8)
   zeigt "Unterdeckung X FTE", wenn `available_fte < benötigtes FTE`.
10. **Grobplan anpassen:** Zurück zu `ResourceDemandGrid`, FTE-Wert eines Monats ändern —
    unabhängig von bereits existierenden Phasen (keine automatische Kopplung, Abschnitt L6.2 (Historie 17.8)
    der Auftragsvorgabe: keine doppelte Source of Truth).

---

### 17.8 P18 Legacy-Compat — aktiver Zwei-Achsen-Pfad (`ResourceDemandGrid`/`Subproject`, aktiv bis B-8)

**Herkunft:** vormals Abschnitt 6 im Hauptteil. Beschreibt **keine historische, abgeschlossene Entscheidung**, sondern einen heute technisch noch aktiven Codepfad für bestehende, noch nicht per B-2-Migration überführte Projekte — deshalb hier im Compat-Teil der Historie dokumentiert statt im aktuellen Abschnitt 6, um dessen Lesbarkeit als reine Zielarchitektur-Beschreibung nicht zu verwässern (Abschnitt 6.15 fasst den Stand kurz zusammen). Wird mit dem produktiven B-8-Cutover entfernt (Abschnitt 16.17); danach verliert dieser Abschnitt jede operative Bedeutung und bleibt nur noch als Historie stehen.

**Status seit dem P18-Implementierungsdurchgang (Abschnitt 16.7–16.13, final CONFIRMED per
Audit, Abschnitt 16.15):** Dieser Abschnitt (17.8, inkl. L6.1–L6.4) beschrieb ursprünglich den
projektweit einzig gültigen IST-Zustand — zwei getrennte Kapazitätsachsen
(Grobplanung/Feinplanung, siehe L6.1). Das ist **nicht mehr korrekt für neu geplante
`PlanPhase`-Bäume**: dort gilt ausschließlich Abschnitt 6 (`PlanPhase`-only, IMPLEMENTIERT).
Dieser Abschnitt (17.8) bleibt trotzdem **technisch aktiver Code**, weil:

1. bestehende Projekte mit bereits gepflegter `ResourceDemand(plan_phase_id = NULL)`-Grobplanung
   bis zur produktiven B-2-Migration ausschließlich über `ResourceDemandGrid` bedienbar sind
   (kein anderer Bedienweg existiert für diese Altdaten), und
2. `ResourceDemandGrid.tsx`/die Subproject-Verwaltung noch nicht entfernt sind (B-8, blockiert).

Für die **fünf zentralen Portfolio-/Cockpit-/GAP-Endpunkte** ist die in Abschnitt L6.3 (Historie 17.8)
beschriebene Doppelzählungs-Lücke bereits **strukturell aufgelöst** — sie lesen seit B-5
ausschließlich noch den `PlanPhase`-Baum, nicht mehr `ResourceDemand.plan_phase_id = NULL`
(Abschnitt 16.15, Kapazitäts-Konsumenten-Matrix). Zwei sekundäre Auswertungen
(`gap_analysis`-Soll-Track/Health-Dimension "Aufwand" und der PPTX-Export) lesen weiterhin
direkt `ResourceDemand.fte`, unabhängig von P18 — kein Doppelzählungs-Risiko (sie addieren
nichts zur PlanPhase-Kapazität), aber auch noch nicht auf die neue Quelle umgestellt.

#### L6.1 Zwei Achsen — aktueller Stand

Zwei sauber getrennte Achsen, beide über dasselbe Modell (`ResourceDemand`), unterschieden
ausschließlich über `plan_phase_id`:

- **Portfolio-/Monatsachse ("Grobplanung", Abschnitt 6a):** `ResourceDemand` mit
  `plan_phase_id = NULL`, `period` im "Apr 26"-Format (`constants.berechne_monate`/
  `parse_period`). UI: `ResourceDemandGrid` (Rolle × Periode-Raster) im Planning-Tab,
  projektweit über den gesamten Planungszeitraum (`Project.start_monat`/`anzahl_monate`).
- **Phasenachse ("Feinplanung", Abschnitt 6a):** `ResourceDemand` mit gesetztem
  `plan_phase_id`, im `PlanPhaseWorkspace`-Drawer, Tab "Kapazität". Zeigt Plan-FTE +
  Planstunden der Phase, dann die Rollen-Aufschlüsselung in Fachsprache (nicht
  "ResourceDemand"/"ResourceAssignment" als UI-Begriffe):

  ```
  Plan-Aufwand            0,80 FTE
  Aufschlüsselung
    Senior Consultant     0,50
    Consultant            0,20
  Aufgeschlüsselt         0,70
  Noch nicht aufgeschlüsselt
                          0,10
  ```

  Darunter je Rolle die Personenbesetzung ("Besetzt"/"Noch unbesetzt" statt
  `assigned_fte`/`allocation_gap`).

Beide Achsen nutzen dieselben Backend-Endpoints (`backend/app/routers/capacity.py`), keine
zweite API-Landschaft. `ResourceDemand.period` ist **immer** ein einzelner Monats-Bucket
(nicht nullable) — auch bei einer phasengebundenen Demand. Das Frontend setzt ihn beim
Anlegen einer Phasen-Demand einmalig auf den Monat von `PlanPhase.forecast_start`
(`PlanPhaseCapacityTab.defaultPeriod`); er hat für die Phasenachse **keine weitere fachliche
Bedeutung** (keine Monatsverteilung, keine Mehrfach-Perioden je Rolle) — die Phase selbst
trägt Start/Ende, nicht ihre Rollen-Demands. Das ist heute so, unabhängig von P18.

**`plan_fte` bleibt führend** (Abschnitt 3) — die Summe der `ResourceDemand.fte` einer Phase
kann von `plan_fte` abweichen (`open_fte` in der Reconciliation); das ist ein gültiger,
erwarteter Zustand, kein Fehler, der automatisch korrigiert wird.

**Personen auf der Grobachse (Level 3, Abschnitt 6a.5 (Historie 17.7)):** `ResourceAssignment` ist an keiner
Stelle im Code auf `plan_phase_id IS NOT NULL` beschränkt — `ResourceDemandGrid.tsx` bietet
bereits heute pro Grob-Zelle (Rolle × Monat) einen "Person zuordnen"-Block inkl.
Kandidaten-Vorschlägen (`GET /resource-demands/{id}/candidates`). Personen auf einer
projektweiten Grobplanung sind also **bereits unterstützt**, nicht nur eine Idee für P18.

#### L6.2 Available Capacity

`Nominal Capacity − Holiday − Absence − Internal Allocation = Available Capacity`
(`capacity_calc.compute_person_capacity`), primäre Quelle `WorkingTime`, Fallback
`ResourceProfile.weekly_hours`. `GET /people/{id}/capacity?period=`.

**Wichtige technische Grenze (P18-relevant, Abschnitt 6a.8 (Historie 17.7)):** `compute_person_capacity`
nimmt ausschließlich einen Monats-Bucket (`period: "Apr 26"`, via `constants.parse_period`)
entgegen, keinen beliebigen Datumsbereich. Ein `PlanPhase`-Zeitraum wie "20.10.–20.11." kann
damit heute **nicht direkt** an `compute_person_capacity` übergeben werden — dafür existiert
seit P18/B-4 die bereichsbasierte Erweiterung `compute_person_capacity_for_range` (Abschnitt
6.5/6.11). **Historische Anmerkung (Stand vor P18.1 Stabilization, Abschnitt 16.16):** bis
zu diesem Stabilization-Durchgang prüfte `GET /resource-demands/{id}/candidates` Kapazität
weiterhin nur für den einen Monat aus `ResourceDemand.period`, unabhängig von einer gesetzten
`plan_phase_id` — seit 16.16 nutzt dieser Endpoint bei gesetzter `plan_phase_id`
`compute_person_capacity_for_range` über die volle Phasen-Range, mit unverändertem
Perioden-Fallback für Legacy-Demands ohne `plan_phase_id`.

#### L6.3 Bekannte Aggregationslücke (aktueller Stand, kein P18-Vorschlag)

Diese Beobachtung beschreibt **heutiges** Verhalten, unabhängig davon, ob P18 je umgesetzt
wird — sie gehört hierher, weil sie beim P18-Audit gefunden wurde und sonst nirgends
dokumentiert war:

Alle heutigen Portfolio-/Cockpit-Aggregationen, die über `ResourceDemand` summieren, filtern
**nicht** nach `plan_phase_id`:

| Endpoint | Datei | Filter |
|---|---|---|
| `GET /controlling/capacity-heatmap` (via `capacity_calc.compute_capacity_gap`) | `capacity_calc.py` | `ResourceDemand.period == period` |
| `GET /controlling/allocation-gaps` | `routers/controlling.py` | `ResourceDemand.period == period` |
| `GET /controlling/roles` | `routers/controlling.py` | `ResourceDemand.resource_role_id == …, period == …` |
| `GET /gap-engine/capacity` | `capacity_calc.py` (dieselbe Funktion) | `ResourceDemand.period == period` |
| `GET /projects/{id}/cockpit` (`CockpitCapacity`) | `routers/health.py::_cockpit_capacity` | `ResourceDemand.project_id == …, period == …` |

Das heißt: existieren für dasselbe Projekt/Rolle/Monat sowohl eine Grob-Demand
(`plan_phase_id = NULL`) als auch eine Phasen-Demand (`plan_phase_id` gesetzt), werden **beide
FTE-Werte heute bereits addiert** — ohne dass es dafür eine fachliche Entscheidung gab. Das
widerspricht dem in Abschnitt 3 dokumentierten Grundsatz "keine Doppelzählung" und ist der
konkrete Auslöser für den P18-Audit (Abschnitt 6a). Zusätzlich hat `ResourceDemandGrid.tsx`
(Grobachse-UI) selbst keinen `plan_phase_id`-Filter: `listResourceDemands(projectId)` liefert
alle Demands des Projekts, `demandFor(roleId, period)` nimmt per `.find()` die erste
Demand mit passender Rolle/Periode — existiert für dieselbe Rolle/Periode zusätzlich eine
Phasen-Demand, kann das Grob-Raster versehentlich die Phasen-Demand anzeigen/editieren statt
eine neue Grob-Demand anzulegen. Beide Punkte sind Teil der P18-Implementierungspakete
(Abschnitt 6a.10 (Historie 17.7)), keine bestehende Regression, die vorher schon anders funktioniert hätte.

#### L6.4 Planstände und Kapazität

`BaselineSnapshot`/`BaselineEntry` frieren ausschließlich `PlanPhase`- und
`Milestone`-Felder ein (`baselines._SNAPSHOT_FIELDS`, siehe Abschnitt 5.3) — **niemals**
`ResourceDemand` (weder Grob- noch Phasenachse). Ein Planstand kann heute also keine
historische Kapazitätserwartung rekonstruieren. Siehe Abschnitt 6a.9 (Historie 17.7) für das P18-Zielbild.

---

Weitere technische Details (Setup, Verzeichnisstruktur, Entwicklungsworkflow) siehe
[`README.md`](README.md) und [`AGENTS.md`](AGENTS.md).
