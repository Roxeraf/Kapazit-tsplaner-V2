# Kapazitätsplaner im plx.crew Portal — Konzept

**Version:** v0.18 (P11 — Planungs-/Kapazitätskonsolidierung: CONCEPT.md-Bereinigung)
**Stand:** Alle in Abschnitt 16 gelisteten Phasen sind umgesetzt, inklusive Phase 26.9
(Legacy Cutover) und der Planungs-/Kapazitätskonsolidierung (P1–P11, Abschnitt 16.1).
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

**Abschnitt 15 (Offene Business Decisions)** und **Abschnitt 16 (Umsetzungsstand)** sind das
Bindeglied zwischen Ist und Soll.

**Abschnitt 17 (Historie)** enthält alles, was fachlich überholt, aber historisch
dokumentationswürdig ist — insbesondere die ursprüngliche Excel-Herkunft und den Legacy
Cutover. Aussagen aus Abschnitt 17 sind **niemals** aktuelle Anforderungen, auch wenn sie
technisch klingen.

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

- Projektplanung (PlanPhase, Milestone, Teilprojekte, Planstände, Gantt-Visualisierung)
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
gegen diese Liste prüfen:

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

---

## 4. Aktuelles Datenmodell

Nur die aktuell gültigen, führenden Tabellen. Entfernte/historische Modelle stehen in
Abschnitt 17.3, nicht hier.

| Tabelle | Zweck |
|---|---|
| `projects` | Projektstammdaten (Name, Kunde, Startmonat, Anzahl Monate, Status, Jira-Verknüpfung, `projektleiter_person_id`) |
| `subprojects` | Optionale Teilprojekte (reine Gruppierung für Phasen/Milestones, kein eigenes Jira-Mapping) |
| `plan_phases` | **Die** Planungseinheit — tagegenau, siehe Abschnitt 5 |
| `milestones` | Eigenständige Milestone-Entität, projektweit oder teilprojektbezogen |
| `baseline_snapshots` / `baseline_entries` | Planstände (eingefrorene Feldwerte je PlanPhase/Milestone) |
| `resource_roles`, `skills`, `person_skills` | Rollen-/Skill-Vokabular für Kapazitätsplanung |
| `resource_demands` | Bedarf (Rolle × Periode × FTE, optional `plan_phase_id`) |
| `resource_assignments` | Personenbesetzung eines `ResourceDemand` |
| `capacity_calendars`, `holidays`, `working_times`, `absences`, `internal_allocations` | Available-Capacity-Berechnung je Person/Periode |
| `people`, `resource_profiles` | Personenstammdaten + Kapazitätsplanbarkeit (`weekly_hours`, `team_id`) |
| `teams` | Team-Stammdaten (Kapazitätsgruppierung) |
| `project_roles`, `project_memberships` | Person ↔ Projekt mit Rolle (≠ Assignment, siehe Abschnitt 3) |
| `permissions`, `app_roles`, `role_permissions` | Vorbereitung für künftiges Rollen-/Rechtesystem (kein Auth im Repo) |
| `comments` (inkl. `parent_id` für Threading), `tasks`, `blockers`, `decisions`, `risks`, `meeting_minutes` | Zusammenarbeit — alle taggbar, dokumentverknüpfbar, relationsfähig; alle außer `risks`/`meeting_minutes` zusätzlich `plan_phase_id`-verknüpfbar |
| `documents`, `document_links` | Zentrale Dokumentenablage (Abschnitt 8) |
| `tags`, `tag_links`, `tag_categories` | Tag-System inkl. AI-Metadaten (`ai_relevant`, `ai_description`, `synonyms`) |
| `entity_relations` | Generische, typisierte Beziehung zwischen zwei beliebigen Entitäten (z. B. `resulted_in`, `depends_on`, `resolves`) |
| `health_thresholds` | Admin-konfigurierbare Schwellen für die neun Health-Dimensionen |
| `jira_worklogs_cache` | Ist-Daten-Cache aus Jira/Tempo |
| `gap_snapshots` | Modell existiert, wird aktuell nicht befüllt — GAP Engine rechnet live (siehe Abschnitt 9) |
| `plan_history` | Änderungsprotokoll (Audit-Trail), gruppiert über `batch_id` |

Entfernt (Phase 26.9, siehe Abschnitt 17.3): `gantt_phases`, `project_gantt_phases`,
`fte_plan`, `project_fte_plan`, `team_members`, `assignments`, `projects.projektleiter`
(Freitext).

---

## 5. Projektplanung

### 5.1 PlanPhase — verbindliches Zielbild

`PlanPhase` ist die zentrale Einheit der konkreten Projektplanung, **tagegenau** geplant
(Beispiel: "Pflichtenheft, 01.10.2026–17.10.2026", nicht "Oktober = Pflichtenheft").

Der User plant eine PlanPhase über: Name (`phase_type`, Freitext mit Vorschlägen aus den
ehemaligen Gantt-Phasencodes), Start, Ende, Status, optionales Teilprojekt, Owner, Tags,
Plan-FTE.

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

### 5.4 Teilprojekte

Teilprojekte bleiben optional (`PlanPhase.subproject_id`/`Milestone.subproject_id`
nullable). `NULL` = projektweit, gesetzt = teilprojektbezogen. Listenansicht und Gantt
gruppieren konsequent: "Projektweit" zuerst, dann Teilprojekte in Reihenfolge. Projekte ohne
Teilprojekte zeigen einfach nur die "Projektweit"-Gruppe (kein Sonderfall/Leerlauf-UI nötig).

### 5.5 Milestones

Milestones sind echte Entitäten (`Milestone`-Tabelle seit Phase 17), kein Rückfall auf den
ehemaligen Gantt-Phasencode `?`. Projektweit oder teilprojektbezogen (nullable
`subproject_id`, analog PlanPhase). Dieselbe UX-Regel wie bei PlanPhase gilt: das normale
Datumsfeld heißt schlicht "Datum" (= `forecast_date`), `baseline_date` ist compat-only,
`actual_date` sekundär mit expliziter Korrektur-Aktion ("Ist-Datum korrigieren").

### 5.6 Gantt

Gantt ist **ausschließlich Visualisierung**. Source of Truth bleiben `PlanPhase`/`Milestone`.
Gantt liest `forecast_start`/`forecast_end`, zeigt sie aber als normale Plan-Zeiträume (ein
Balken pro Phase, keine technisch benannten Baseline-/Forecast-/Ist-Balken nebeneinander).

Gantt darf: PlanPhases tagegenau darstellen, nach Teilprojekten gruppieren (inkl.
"Projektweit"), Tag/Woche/Monat/Quartal zoomen (aktuell: Monatsraster), Phase anklickbar
machen → öffnet den PlanPhaseWorkspace-Drawer.

Gantt soll **nicht**: primäre Planungsoberfläche sein, eigene Planungsdaten speichern,
Drag&Drop oder Resize als notwendigen Workflow erzwingen (beides deferred, Abschnitt 15).
Milestones im Gantt darstellen ist ebenfalls deferred (bewusster Scope-Cut aus P8).

---

## 6. Kapazitätsplanung

Zwei sauber getrennte Achsen:

- **Portfolio-/Monatsachse:** `ResourceDemand` mit `plan_phase_id = NULL`, `period` im
  "Apr 26"-Format (`constants.berechne_monate`/`parse_period`). UI: `ResourceDemandGrid`
  (Rolle × Periode-Raster) im Planning-Tab, projektweit über den gesamten Planungszeitraum.
- **Phasenachse:** `ResourceDemand` mit gesetztem `plan_phase_id`, im
  `PlanPhaseWorkspace`-Drawer, Tab "Kapazität". Zeigt Plan-FTE + Planstunden der Phase, dann
  die Rollen-Aufschlüsselung in Fachsprache (nicht "ResourceDemand"/"ResourceAssignment" als
  UI-Begriffe):

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
zweite API-Landschaft.

**`plan_fte` bleibt führend** (Abschnitt 3) — die Summe der `ResourceDemand.fte` einer Phase
kann von `plan_fte` abweichen (`open_fte` in der Reconciliation); das ist ein gültiger,
erwarteter Zustand, kein Fehler, der automatisch korrigiert wird.

**Available Capacity** je Person/Periode: `Nominal Capacity − Holiday − Absence − Internal
Allocation` (`capacity_calc.compute_person_capacity`), primäre Quelle `WorkingTime`, Fallback
`ResourceProfile.weekly_hours`. `GET /people/{id}/capacity?period=`.

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
/gap`/`GET /forecast`). **Phase-Level-Ist ist deferred (BD-1):** es gibt aktuell kein
belastbares Mapping Tempo-Worklog → einzelne `PlanPhase`. `PhaseMetricsOut.ist_hours`/
`effort_consumption_pct` liefern deshalb konsequent `null`, nie eine Datumsheuristik oder ein
Fake-Ist.

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

**"Aus Objekt erstellen":** aus einem Kommentar (oder einer Decision/einem Blocker) kann
über eine kontextuelle Aktion ein fachliches Folgeobjekt entstehen (z. B. `+ Aufgabe`), das
per `EntityRelation(relation_type="resulted_in")` mit dem Ursprung verknüpft wird — keine
neue Source-of-Truth-Spalte für "Origin", `EntityRelation` reicht.

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

**PlanPhase-Workspace (Drawer):** die primäre Detail-/Bearbeitungsoberfläche, vier Tabs:

- **Übersicht** — editierbar: Name, Start/Ende (= "Zeitraum"), Status, Owner, Teilprojekt,
  Tags, Plan-FTE, alles sofort speichernd (kein Batch-/Grund-Workflow, siehe unten).
  Read-only/berechnet: Planstunden, Zeitfortschritt, Ist-Aufwand (aktuell "noch nicht
  eindeutig zugeordnet", BD-1). Sekundär: "Tatsächlicher Verlauf" (Gestartet/Abgeschlossen),
  mit Aktion "Ist-Daten korrigieren" für die seltene manuelle Nachpflege.
- **Kapazität** — Plan-FTE/Planstunden-Kopfzeile, Rollen-Aufschlüsselung + Personenbesetzung
  in Fachsprache (siehe Abschnitt 6).
- **Aktivität** — Activity Feed + Kommentare (inkl. Threading/"aus Objekt erstellen"),
  Aufgaben, Entscheidungen, Blocker im Phasenkontext.
- **Dateien** — phasenbezogene Ansicht der zentralen Dokumentenablage (Upload, Liste,
  Löschen).

**Speichern-Paradigma:** Der Planung-Tab ist konsequent Sofort-Speichern (jede Änderung im
Drawer/in der Liste wird direkt persistiert) — **kein** globales "Grund für diese
Änderung"-Feld mehr auf diesem Tab. Der Batch-/Grund-Speichern-Workflow
(`PlanHistory.batch_id`, optionaler `kommentar_id`) bleibt als Audit-Trail-Mechanismus
bestehen, ist aber auf die vier Projektstammdaten-Felder im Einstellungen-Tab beschränkt
(siehe P11, Abschnitt 16.1) — dort ändert sich selten mehr als ein Feld auf einmal, ein
expliziter "Speichern"-Klick mit Begründung passt fachlich. Zwei konkurrierende
Speicherparadigmen auf derselben Seite (Planung) wurden damit aufgelöst, ohne den
Audit-Trail-Mechanismus selbst zu entfernen.

**Milestones, Ressourcen (Portfolio-Achse), Planstände, Teilprojekt-Verwaltung** liegen als
eigene Karten unterhalb der PlanPhase-Liste, jeweils mit Sofort-Speichern.

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
| Ist-Aufwand (Phase) | — | — | Tempo/Jira, Mapping offen | **deferred (BD-1)**, liefert `null` |
| Zeitfortschritt | berechnet (`phase_metrics_calc.time_progress`) | nicht editierbar | Datumsanteil | aktuell |
| Progress (%) | `PlanPhase.progress` | nirgends (deprecatet) | — | **deprecated**, compat-only |
| Status | `PlanPhase.status`/`Milestone.status` (Freitext) | Drawer/Liste, Zielvokabular in Dropdown | — | aktuell; historische Werte lesbar, siehe Abschnitt 16.1 |
| Tags | `Tag`/`TagLink` | überall wo taggbar | — | aktuell |
| Available Capacity | berechnet (`capacity_calc.compute_person_capacity`) | nicht editierbar | `WorkingTime`/`ResourceProfile` − `Holiday` − `Absence` − `InternalAllocation` | aktuell |
| Gantt-Balken | — | nicht editierbar (read-only Visualisierung) | `PlanPhase.forecast_start/end` | aktuell |

---

## 14. Open Business Decisions

| ID | Frage | Status |
|---|---|---|
| BD-1 | Tempo/Jira-Worklog → PlanPhase-Mapping: welches Kriterium (Datum, Ticket-Feld, manuelle Zuordnung)? | offen — `effort_consumption_pct`/`ist_hours` liefern bis dahin konsequent `null`, keine Heuristik |
| BD-3 | Bewertungs-Thresholds für Phasenmetriken (🟢/🟡/🔴 auf `plan_hours`/`time_progress_pct`/Reconciliation)? | offen — Metriken werden aktuell ohne Ampel gezeigt |
| BD-4 | Feiertags-Handling für Planstunden (aktuell Mo–Fr ohne Feiertagsabzug) | offen, dokumentierter Scope-Cut, keine stille Baseline-Änderung |
| BD-5 | `ResourceAssignment` mit Teil-Zeiträumen (Sub-Ranges) statt einer FTE über die ganze Demand-Periode? | offen |
| BD-6 | `allocation_gap`-Vorzeichenkonvention vereinheitlichen (siehe Abschnitt 9, bekannte Inkonsistenz zwischen `ResourceDemandOut` und `CockpitCapacity`) | offen, bewusst nicht rückwirkend angefasst |

**Aufgelöst mit P11 (nicht mehr offen):** Status-Normalisierung (vormals BD-2) — Zielvokabular
Geplant/In Arbeit/Abgeschlossen/Entfällt ist definiert und über eine Frontend-Mapping-Schicht
umgesetzt (Details Abschnitt 16.1). Die Backend-Spalte bleibt bewusst Freitext (keine
destruktive Migration), Governance ist damit vollständig für dieses Konsolidierungsziel.

---

## 15. Deferred Features

- Tempo→PlanPhase-Mapping (BD-1)
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

---

## 16. Umsetzungsstand

### 16.1 P1–P11 — Planungs- und Kapazitätskonsolidierung (dieser Durchgang)

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

---

Weitere technische Details (Setup, Verzeichnisstruktur, Entwicklungsworkflow) siehe
[`README.md`](README.md) und [`AGENTS.md`](AGENTS.md).
