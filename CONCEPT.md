# Kapazitätsplaner im plx.crew Portal — Konzept

**Version:** v0.20 (P18 Pass 2 — PlanPhase-only/hierarchische Phasen: Design & Spezifikation,
löst P18 Pass 1 fachlich ab)
**Stand:** Alle in Abschnitt 16 gelisteten Phasen bis P17 sind umgesetzt. **P18 ist weiterhin
ein reiner Design-/Spezifikations-Durchgang — noch nicht implementiert**, jetzt in zwei
Durchgängen: **Pass 1** (Abschnitt 6a, Grob-/Feinplanung + Reconciliation) und **Pass 2**
(Abschnitt 6b, PlanPhase-only/hierarchische Phasen,
[`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)). **Pass
2 ist die aktuell empfohlene Zielarchitektur und löst Pass 1 fachlich ab** (Abschnitt 6a bleibt
zu Dokumentationszwecken/Nachvollziehbarkeit im Dokument stehen, ist aber **superseded** — bei
Widerspruch zwischen 6a und 6b gilt 6b). Kein Code, keine Migration, keine Frontend-Änderung
wurde für P18 (weder Pass 1 noch Pass 2) vorgenommen; bis zur Umsetzung gilt technisch
unverändert das in Abschnitt 6 beschriebene Verhalten (inkl. der dort dokumentierten, bereits
heute bestehenden Doppelzählungs-Lücke in der Portfolio-Aggregation, die durch Pass 2
strukturell — nicht nur per Filter-Fix — aufgelöst würde, siehe Abschnitt 6b).
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
Code hat Vorrang, aber meldet es als Doku-Bug. **Ausnahme: Abschnitt 6a** ist explizit als
P18-Design markiert (Kopfzeile "noch nicht implementiert") — dort gilt bei Widerspruch zu
Code **nicht** "Code hat Vorrang", sondern Abschnitt 6 (aktuelles Verhalten) bleibt
maßgeblich, bis Abschnitt 16.4/BD-7/8/9 als umgesetzt markiert sind.

**Abschnitt 14 (Offene Business Decisions)** und **Abschnitt 16 (Umsetzungsstand)** sind das
Bindeglied zwischen Ist und Soll.

**Ausnahme innerhalb der Ausnahme:** Abschnitt 6a (P18 Pass 1) und Abschnitt 6b (P18 Pass 2)
sind beide als Design markiert, widersprechen sich aber teilweise (Pass 2 schlägt eine andere
Zielarchitektur vor als Pass 1). Bei Widerspruch zwischen 6a und 6b gilt **6b** — 6a bleibt nur
aus Nachvollziehbarkeit über den Entscheidungsweg im Dokument (kein stilles Löschen einer
bereits durchgeführten, sauberen Analyse), ist aber fachlich **nicht mehr** die empfohlene
Richtung.

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
- **Grobplanung (`ResourceDemand.plan_phase_id = NULL`) und Feinplanung (`PlanPhase` +
  phasengebundener `ResourceDemand`) sind zwei Konkretisierungsgrade derselben
  Projektplanung, keine additiven Bedarfe.** Sie werden **nicht addiert**. Für Portfolio-/
  Team-Kapazität gilt je Projekt/Monat `Konsumption = max(Grobplanstunden, Feinplanstunden)`
  (Design, P18, Abschnitt 6a — **Umsetzung hängt von BD-7 ab**, aktuelle Aggregationen
  summieren beide Achsen noch ungefiltert, siehe Abschnitt 6.4).
- **`plan_fte` bleibt auch für die Grob-/Fein-Reconciliation die Quelle für Feinplanstunden**
  einer Phase (nicht die Rollen-Aufschlüsselung) — konsistent mit dem bereits geltenden
  Grundsatz, dass `ResourceDemand` keine zweite Source of Truth für den Phasenaufwand ist.

---

## 4. Aktuelles Datenmodell

Nur die aktuell gültigen, führenden Tabellen. Entfernte/historische Modelle stehen in
Abschnitt 17.3, nicht hier.

| Tabelle | Zweck |
|---|---|
| `projects` | Projektstammdaten (Name, Kunde, Startmonat, Anzahl Monate, Status, Jira-Verknüpfung, `projektleiter_person_id`) |
| `subprojects` | Optionale Teilprojekte (reine Gruppierung für Phasen/Milestones, kein eigenes Jira-Mapping). **P18 Pass 2 (Abschnitt 6b.7, Design):** wird fachlich durch hierarchische `PlanPhase` (`parent_phase_id`) abgelöst — Tabelle bliebe dabei zunächst compat-only bestehen, keine Codeänderung in diesem Durchgang. |
| `plan_phases` | **Die** Planungseinheit — tagegenau, siehe Abschnitt 5. **P18 Pass 2 (Abschnitt 6b, Design):** zusätzliches, noch nicht implementiertes Feld `parent_phase_id` (self-referencing, nullable) für eine hierarchische Struktur. |
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

**P18 Pass 2 (Abschnitt 6b.7, Design, noch nicht implementiert):** `Subproject` ist fachlich
nicht mehr als eine PlanPhase-Gruppierung (bestätigt per Codebase-Audit) und würde durch eine
hierarchische Parent-`PlanPhase` (`parent_phase_id`) ersetzt — mit denselben Vorteilen plus
abgeleiteten Zeiträumen/Kapazität und mehr als einer Gruppierungsebene. Diese Beschreibung
(Abschnitt 5.4) bleibt bis zur Umsetzung der aktuelle, gültige Ist-Zustand.

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

### 6.1 Zwei Achsen — aktueller Stand

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

**Personen auf der Grobachse (Level 3, Abschnitt 6a.5):** `ResourceAssignment` ist an keiner
Stelle im Code auf `plan_phase_id IS NOT NULL` beschränkt — `ResourceDemandGrid.tsx` bietet
bereits heute pro Grob-Zelle (Rolle × Monat) einen "Person zuordnen"-Block inkl.
Kandidaten-Vorschlägen (`GET /resource-demands/{id}/candidates`). Personen auf einer
projektweiten Grobplanung sind also **bereits unterstützt**, nicht nur eine Idee für P18.

### 6.2 Available Capacity

`Nominal Capacity − Holiday − Absence − Internal Allocation = Available Capacity`
(`capacity_calc.compute_person_capacity`), primäre Quelle `WorkingTime`, Fallback
`ResourceProfile.weekly_hours`. `GET /people/{id}/capacity?period=`.

**Wichtige technische Grenze (P18-relevant, Abschnitt 6a.8):** `compute_person_capacity`
nimmt ausschließlich einen Monats-Bucket (`period: "Apr 26"`, via `constants.parse_period`)
entgegen, keinen beliebigen Datumsbereich. Ein `PlanPhase`-Zeitraum wie "20.10.–20.11." kann
damit heute **nicht direkt** an die Available-Capacity-Berechnung übergeben werden — jeder
Aufrufer (inkl. `GET /resource-demands/{id}/candidates`) prüft Kapazität faktisch nur für den
einen Monat, der in `ResourceDemand.period` steht (siehe 6.1), nicht für den vollen
Phasenzeitraum.

### 6.3 Bekannte Aggregationslücke (aktueller Stand, kein P18-Vorschlag)

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
(Abschnitt 6a.10), keine bestehende Regression, die vorher schon anders funktioniert hätte.

### 6.4 Planstände und Kapazität

`BaselineSnapshot`/`BaselineEntry` frieren ausschließlich `PlanPhase`- und
`Milestone`-Felder ein (`baselines._SNAPSHOT_FIELDS`, siehe Abschnitt 5.3) — **niemals**
`ResourceDemand` (weder Grob- noch Phasenachse). Ein Planstand kann heute also keine
historische Kapazitätserwartung rekonstruieren. Siehe Abschnitt 6a.9 für das P18-Zielbild.

---

## 6a. Grob-/Feinplanung & Capacity Reconciliation (P18 Pass 1 — Design, SUPERSEDED durch 6b)

> ⚠️ **Dieser Abschnitt ist superseded.** P18 Pass 2 (Abschnitt 6b) hat die hier beschriebene
> Zwei-Achsen-Architektur (Grobplanung/Feinplanung + Reconciliation-Formel) erneut geprüft und
> durch eine hierarchische `PlanPhase`-only-Architektur ersetzt, die dieselbe fachliche
> Anforderung (frühe grobe Kapazitätssicht, schrittweise Konkretisierung, keine Doppelzählung)
> ohne eine zweite Planungsebene erfüllt (siehe
> [`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)
> Abschnitt 2 für die Begründung). Dieser Abschnitt bleibt **ausschließlich aus
> Nachvollziehbarkeit** im Dokument stehen (der Analysedurchgang war real und sauber
> durchgeführt) — er ist **keine** gültige Umsetzungsgrundlage mehr. BD-7/BD-8/BD-9 (unten)
> sind durch Abschnitt 6b obsolet. Bei jedem Widerspruch zu Abschnitt 6b gilt 6b.

**Status dieses Abschnitts:** Fachlich vollständig spezifiziert und gegen Code/CONCEPT
geprüft (Codebase Validation Matrix siehe separates
[`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md`](P18_DESIGN_AND_IMPLEMENTATION_PLAN.md)). **Nicht
implementiert** — und nach Pass 2 auch nicht mehr zur Implementierung vorgesehen. Beschreibt
ein geprüftes, aber nicht mehr empfohlenes Zielverhalten. Ist-Zustand bleibt weiterhin
Abschnitt 6 (aktuelles Verhalten) bis zur Umsetzung von Pass 2.

### 6a.1 Warum zwei Ebenen — fachliche Begründung

Ein Projekt wird nicht an einem Tag vollständig tagegenau planbar. Es durchläuft typischerweise:

1. **Kapazitätsrelevant, aber noch nicht strukturiert:** Der Projektleiter weiß "im Oktober
   brauchen wir ca. 1,5 FTE", aber noch keine Phasen, Rollen oder Personen.
2. **Zunehmend konkretisiert:** Phasen entstehen, zunächst grob befüllt (nur `plan_fte`),
   dann mit Rollen-Aufschlüsselung, dann mit Personenbesetzung.
3. **Vollständig fein geplant:** Jede relevante Kapazität steckt in tagegenauen `PlanPhase`s.

**Grobplanung** (Abschnitt 6.1, Portfolio-/Monatsachse) beantwortet: *"Wie viel Kapazität
erwarten wir ungefähr für dieses Projekt in diesem Monat?"* — Zweck: Portfolio-/
Teamplanung kann kommende Projekte berücksichtigen, bevor sie strukturiert planbar sind.

**Feinplanung** (Abschnitt 5, tagegenaue `PlanPhase`s + Phasenachse) beantwortet: *"Wann
benötigen wir wie viel Kapazität für welche konkrete Projektphase, später welche
Rollen/Personen?"*

Beide sind **Konkretisierungsgrade derselben Planung**, keine unabhängigen Bedarfe — ein
Projekt plant nicht zweimal Kapazität, es beschreibt denselben erwarteten Aufwand mit
zunehmender Präzision.

### 6a.2 Keine neue Tabelle, keine neue Engine

Grobplanung ist **kein neues Modell**. Sie ist exakt das bereits existierende
`ResourceDemand` mit `plan_phase_id = NULL` (Abschnitt 6.1) — hier nur erstmals fachlich
benannt und mit einer expliziten Reconciliation zur Feinplanung versehen. Es wird **kein**
neues `gross_plan_fte`-Feld, keine zweite `ResourceDemand`-Tabelle und keine zweite
Available-Capacity-Berechnung eingeführt (Abschnitt 20 der Auftragsvorgabe, verbindlich).

Rollenbedarf innerhalb der Grobplanung (Abschnitt 17 der Auftragsvorgabe, "Level 2": z. B.
Oktober → Senior Consultant 0,80 + Consultant 0,70) ist bereits heute möglich: mehrere
`ResourceDemand`-Zeilen mit `plan_phase_id = NULL`, unterschiedlichem `resource_role_id`,
demselben `period`. Kein neues Feld nötig — `ResourceDemandGrid` bildet das bereits als
Rolle-Zeile ab.

### 6a.3 Definitionen

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

### 6a.4 Plan-FTE- und Planstunden-Semantik geschärft

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

### 6a.5 Reifegrade der Grobplanung (Level 1–4)

Bereits heute technisch abbildbar, ohne neue Architektur:

| Level | Beispiel | Modell |
|---|---|---|
| 1 — nur Gesamt-FTE | "Oktober ca. 1,5 FTE" | eine `ResourceDemand`-Zeile mit einer generischen/Default-Rolle, `plan_phase_id = NULL` |
| 2 — Rollen | "0,8 Senior + 0,7 Consultant" | mehrere `ResourceDemand`-Zeilen, `plan_phase_id = NULL`, unterschiedliche `resource_role_id` |
| 3 — Personen | "Dominik 0,5, Max 0,3" | `ResourceAssignment` auf einer Grob-`ResourceDemand` (bereits ohne Einschränkung im Code möglich, Abschnitt 6.1) |
| 4 — Feinplanung | tagegenaue `PlanPhase`s, ggf. mit eigener Rollen-/Personen-Aufschlüsselung | `PlanPhase` + phasengebundene `ResourceDemand`/`ResourceAssignment` |

Level 1–3 sind kein neues Datenmodell — nur eine neue fachliche Lesart des bereits
existierenden `ResourceDemand`/`ResourceAssignment`. **Keine BD nötig für Level 1–3.**

### 6a.6 Monatsverteilungsalgorithmus (Feinplanstunden)

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
6.1). `plan_fte` bleibt die einzige Quelle für Feinplanstunden, identisch zum bestehenden
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

### 6a.7 Konkretisierungsgrad ("Planungsreife") — keine Ampel, kein Fortschritt

`Konkretisierungsgrad(Monat) = Feinplanstunden(Monat) / Grobplanstunden(Monat) × 100`, nur
wenn `Grobplanstunden(Monat) > 0` (sonst nicht definiert/`null`, nicht 0 % — "keine
Grobplanung" ist ein anderer Zustand als "0 % konkretisiert", siehe Abschnitt 6a.9 Edge
Case "keine Grobplanung"). UI-Label: **"Planung konkretisiert X %"**, ausdrücklich **nicht**
"Fortschritt" (Verwechslungsgefahr mit `PlanPhase.progress`, das ohnehin deprecatet ist,
Abschnitt 3) und **keine 🟢/🟡/🔴-Bewertung** (konsistent mit BD-3, das dieselbe
Zurückhaltung für alle Phasenmetriken bereits festlegt).

### 6a.8 Available Capacity im Planungsfluss (Personenbesetzung prüfen)

Ziel: bei einer `ResourceAssignment` (Grob- oder Phasenachse) soll der Projektleiter sehen,
ob die Person im relevanten Zeitraum tatsächlich Kapazität hat — **ohne neue
Capacity-Engine** (Abschnitt 20 der Auftragsvorgabe).

- **Grobachse:** unverändert `compute_person_capacity(db, person_id, demand.period)` —
  passt bereits, weil eine Grob-Demand ohnehin genau einen Monat trägt (Abschnitt 6.1).
- **Phasenachse:** heute geprüft nur gegen den einen in `ResourceDemand.period` gespeicherten
  Monat (Abschnitt 6.2), nicht gegen den vollen `PlanPhase`-Zeitraum. **Minimal-invasiver
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
  `compute_person_capacity` bereits tun (Abschnitt 6.2) — **keine idealisierte Formel**, keine
  neue HR-Integration, kein Personio (Abschnitt 21 der Auftragsvorgabe).

### 6a.9 Planstände (Baseline) und Grobplanung

Heute friert ein `BaselineSnapshot` keine `ResourceDemand`-Werte ein (Abschnitt 6.4). Damit
lässt sich nicht rekonstruieren "im Oktober hatten wir ursprünglich 1,5 FTE grob geplant,
später waren es 1,8 FTE." Der generische `BaselineEntry`-Mechanismus
(`entity_type`/`entity_id`/`field`, Abschnitt 4) ist dafür bereits ausreichend generisch —
`entity_type = "resource_demand"`, `field = "fte"` wäre ohne Schemaänderung möglich. Die
fachliche Frage ist nicht die Technik, sondern der Umfang: friert man jede einzelne
Grob-`ResourceDemand`-Zeile ein (granular, aber ein Planstand kann dann sehr viele Zeilen
erzeugen) oder nur die aggregierten Grobplanstunden je Monat (kompakter, aber keine
Rollen-Historie mehr)? **Offen — BD-8.**

### 6a.10 Capacity Consumption Source-of-Truth-Matrix

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
ändert das **heutige** (in 6.3 dokumentierte, ungefilterte Summen-)Verhalten der
Portfolio-Endpoints. Das ist eine Verhaltensänderung an produktiv sichtbaren Zahlen
(Portfolio-Dashboard, Cockpit, Controlling), kein reiner Bugfix im technischen Sinn — daher
Business-Freigabe vor Umsetzung nötig, auch wenn die fachliche Analyse eindeutig für die
`max()`-Formel spricht.

### 6a.11 Teilprojekte

Grobplanung bleibt **projektweit** (`ResourceDemand` hat kein `subproject_id`-Feld, Abschnitt
4) — keine neue Dimension. Feinplanung kann bereits heute optional über
`PlanPhase.subproject_id` auf Teilprojekte verteilt werden (Abschnitt 5.4). Die
Monatsverteilung (6a.6) rechnet Feinplanstunden je Projekt/Monat unabhängig davon, ob eine
Phase einem Teilprojekt zugeordnet ist — eine teilprojektscharfe Reconciliation (Grob vs.
Fein je Teilprojekt) ist **kein Bestandteil von P18**, da Grobplanung dafür keine
Teilprojekt-Dimension hat und keine bekannte fachliche Notwendigkeit dafür vorliegt (kein
neuer Bedarf identifiziert, daher keine neue Dimension eingeführt).

### 6a.12 Edge Cases

| Fall | Verhalten |
|---|---|
| Keine Grobplanung, nur Feinplanung | Gültiger Zustand (kleines Projekt, Phasen sofort bekannt). `Grobplanstunden(Monat) = 0` → Konkretisierungsgrad `null` (nicht 0 %, Abschnitt 6a.7), Konsumption = Feinplanstunden. Keine künstliche Grobplanung wird erzeugt. |
| Nur Grobplanung, keine Feinplanung | Gültiger Zustand (Projekt in früher Phase). `Feinplanstunden(Monat) = 0` → Konkretisierungsgrad 0 %, Konsumption = Grobplanstunden. Hauptzweck der Grobplanung (Abschnitt 6a.1). |
| Feinplanung > Grobplanung | Kein Fehler, keine automatische Anpassung der Grobplanung. UI zeigt "Grob geplant 1,50 FTE / Konkret geplant 1,80 FTE / Abweichung +0,30 FTE" als Planungsabweichung. Konsumption = Feinplanstunden (Formel 6a.10). |
| Feinplanung < Grobplanung | Erwarteter Zwischenzustand während der Konkretisierung. "Noch grob" > 0 (6a.3). Konsumption = Grobplanstunden. |
| Phase über Monatsgrenze | Monatsverteilungsalgorithmus 6a.6 (werktage-anteilig, kein 50/50). |
| Projektstart/-ende mitten im Monat | Deckt sich automatisch mit 6a.6, da `count_weekdays_in_range` nur den tatsächlichen Überlappungszeitraum zählt — kein Sonderfall nötig. |
| Vollständig fein geplantes Projekt | Historische Grobplanung bleibt in der DB erhalten (kein Auto-Löschen, Abschnitt 11 der Auftragsvorgabe) — wertvoll als ursprüngliche Kapazitätserwartung/Portfolio-Vergleich/Planungsreife-Indikator, zählt aber operativ nicht mehr zusätzlich (Konsumption = Feinplanstunden, sobald diese ≥ Grobplanstunden). |
| Person ohne `ResourceProfile`/`WorkingTime` | `compute_person_capacity` liefert `None` (bestehendes Verhalten, Abschnitt 6.2) — Aufrufer blendet die Person in Kandidatenlisten aus, keine Kapazitätsprüfung möglich, kein Fehler. |
| Urlaub/Krankheit (`Absence`) | Fließt bereits heute in `compute_person_capacity` über `absence_fte` ein (Abschnitt 6.2), unverändert für 6a.8. |
| Feiertag (`Holiday`) | Fließt bereits heute in `compute_person_capacity` über `holiday_fte` ein — **nur** dort (personenbezogene Available Capacity). Für Planstunden/Monatsverteilung (6a.6) gilt weiterhin BD-4 (kein Feiertagsabzug) — zwei unterschiedliche, bereits heute bestehende Konventionen, die P18 nicht vereinheitlicht. |
| Interne Allokation | Fließt bereits heute über `internal_fte` in `compute_person_capacity` ein, unverändert. |
| Überbuchte Person | `available_fte` kann negativ werden (keine Untergrenze in der Formel) — bereits heute möglich, P18 ändert daran nichts; UI zeigt Unterdeckung (Abschnitt 22 der Auftragsvorgabe: "Benötigt 0,50 / Verfügbar 0,31 / Unterdeckung 0,19"). |

### 6a.13 API (bestehend vs. Zielbild)

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

### 6a.14 UX-Zielbild (Entwurf, nicht implementiert)

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
Abschnitt 6.1, keine neuen Elemente vorgesehen — die Reconciliation ist eine
Projekt-/Monatssicht, keine Phasensicht.

### 6a.15 User Flows (Zielbild)

1. **Neues zukünftiges Projekt grob planen:** Projekt anlegen → Planning-Tab →
   `ResourceDemandGrid` → je Monat eine Zeile (Default-Rolle) mit FTE befüllen. Keine
   `PlanPhase` nötig.
2. **Rollen grob planen:** In `ResourceDemandGrid` weitere Rollen-Zeile hinzufügen, je Monat
   befüllen (Level 2, Abschnitt 6a.5).
3. **Personen grob reservieren:** Zelle anklicken → bestehendes "Person zuordnen"-Panel
   (bereits vorhanden, Abschnitt 6.1) nutzen (Level 3).
4. **Erste `PlanPhase` erstellen:** Planning-Tab → "+ Phase hinzufügen" → Start/Ende/Plan-FTE.
   Reconciliation-Block (6a.14) aktualisiert sich automatisch (Feinplanstunden > 0).
5. **Weitere Phasen konkretisieren:** Weitere Phasen anlegen, bis der Monat vollständig
   abgedeckt ist ("Noch grob" nähert sich 0).
6. **Grob-vs-Fein prüfen:** Reconciliation-Block ansehen, "Planung konkretisiert X %" pro
   Monat.
7. **Phase mit Rollen aufschlüsseln:** `PlanPhaseWorkspace` → Tab "Kapazität" →
   Rollen-Aufschlüsselung wie Abschnitt 6.1 (unverändert).
8. **Personen zuordnen:** Wie 7, "Person zuordnen" je Rollen-Demand (unverändert).
9. **Unterdeckung erkennen:** Kandidatenliste/Available-Capacity-Anzeige (Abschnitt 6a.8)
   zeigt "Unterdeckung X FTE", wenn `available_fte < benötigtes FTE`.
10. **Grobplan anpassen:** Zurück zu `ResourceDemandGrid`, FTE-Wert eines Monats ändern —
    unabhängig von bereits existierenden Phasen (keine automatische Kopplung, Abschnitt 6.2
    der Auftragsvorgabe: keine doppelte Source of Truth).

---

## 6b. PlanPhase-only Zielarchitektur (P18 Pass 2 — Design, empfohlene Zielarchitektur, noch
nicht implementiert)

**Status dieses Abschnitts:** Fachlich vollständig spezifiziert und gegen Code geprüft
(Codebase Validation Matrix siehe separates
[`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)).
**Nicht implementiert** — abhängig von BD-10/BD-11/BD-12/BD-13 (Abschnitt 14). **Löst Abschnitt
6a (P18 Pass 1) fachlich ab** (Begründung: Abschnitt 2 des Pass-2-Dokuments). Beschreibt
Zielverhalten, kein Ist-Zustand — bis zur Umsetzung gilt technisch unverändert Abschnitt 6.

### 6b.1 Kernidee

`PlanPhase` wird die **einzige** Planungseinheit — für Kapazität **und** für Strukturierung
(löst damit gleichzeitig die Grob-/Feinplanungs-Frage aus Abschnitt 6a **und** die
Subproject-Frage aus Abschnitt 5.4 ab). `PlanPhase` bekommt ein neues, additives, nullable Feld
`parent_phase_id` (self-referencing FK, max. 3 Ebenen tief, Business Decision BD-10). Eine
Phase **ohne** Kinder ("Leaf") trägt operative Kapazität (`plan_fte`, Zeitraum) wie heute. Eine
Phase **mit** Kindern ("Parent"/Sammelphase) aggregiert ausschließlich aus ihren Kindern — sie
verliert dabei nicht ihren alten `plan_fte`-Wert (kein Auto-Clear, keine Datenlöschung), er wird
nur ab dem Moment, in dem Kinder existieren, nicht mehr operativ gelesen.

**Kein neues Statusfeld:** Leaf/Parent wird nicht gespeichert, sondern query-seitig berechnet
(`has_children = EXISTS(child mit parent_phase_id = diese Phase)`). Löscht man alle Kinder,
wird eine Phase augenblicklich wieder Leaf, ihr alter `plan_fte`-Wert wird augenblicklich
wieder sichtbar — ohne Zusatzlogik.

### 6b.2 Lifecycle: Zeitraum → Kapazität → Personen → Konkretisierung

1. **Zeitraum:** `+ Phase hinzufügen` → Name, Start, Ende, optional `parent_phase_id` (leer =
   Top-Level-Phase des Projekts). Bereits ein gültiger, vollständiger Planungszustand.
2. **Kapazität:** `plan_fte` setzen — unverändert wie heute (Abschnitt 5.2).
3. **Personen:** `[+ Mitarbeiter zuweisen]` direkt auf der Phase, **ohne** erzwungene
   Rollenauswahl (Abschnitt 6b.4). `[Rollen aufschlüsseln]` bleibt optional verfügbar.
4. **Konkretisierung statt zweiter Planungsebene:** `[+ Unterphase hinzufügen]` — sobald die
   erste Unterphase existiert, wird die Elternphase automatisch zur Sammelphase (Abschnitt
   6b.1). Dieselbe Sequenz beginnt für jede neue Unterphase von vorn, bis zur Tiefenbegrenzung
   (BD-10).

Damit entfällt die in Abschnitt 6a beschriebene zweite, projektweite Monatsachse
(`ResourceDemand.plan_phase_id = NULL`) vollständig — eine anfangs grobe, noch nicht
aufgeteilte Phase **ist** bereits die Grobplanung, kein separates Werkzeug nötig. Die
Rolle-×-Monat-Grobplanungsoberfläche (`ResourceDemandGrid`, Abschnitt 6.1) entfällt damit
ersatzlos.

### 6b.3 Leaf-/Parent-Semantik im Detail

| Bereich | Leaf | Parent |
|---|---|---|
| Zeitraum | direkt editierbar | read-only, abgeleitet: `MIN(child.forecast_start)`/`MAX(child.forecast_end)`, rekursiv |
| `plan_fte` | direkt editierbar, operative Quelle | nicht editierbar im normalen Fluss; UI zeigt "Aggregiert aus N Unterphasen" |
| `ResourceDemand`/`ResourceAssignment` | wie heute, optional (Abschnitt 6b.4) | nicht sinnvoll — Kapazität wird nicht doppelt (Parent UND Leaf) geplant, UI blendet den Editier-Pfad aus |
| Monatsverteilung/Portfolio-Aggregation | fließt ein | fließt **nicht** ein — nur Leaf-Nachfahren zählen (Abschnitt 6b.6) |
| Comment/Task/Blocker/Decision | erlaubt (wie heute) | erlaubt — bereits heute technisch uneingeschränkt möglich, da diese Modelle nur `plan_phase_id` prüfen, nicht Leaf/Parent-Status |
| Milestone | erlaubt | erlaubt (z. B. "Fachkonzept freigegeben" am Ende einer Sammelphase) |
| Gantt | eigener Balken | aggregierte Hüllkurve, ein-/ausklappbar, optionaler Summary-Balken |

### 6b.4 Rollen-Aufschlüsselung bleibt optional (ohne neues Modell)

`ResourceDemand.resource_role_id` ist heute NOT NULL — bereits jetzt, unabhängig von Grob/Fein.
Damit ein Projektleiter eine Person direkt mit FTE zuordnen kann, ohne vorher eine Rolle zu
wählen: eine System-`ResourceRole` ("Ohne Rolle"/"Allgemein", per Migration geseedet) wird von
der UI transparent verwendet — Backend legt bei Bedarf automatisch eine generische
`ResourceDemand` an und hängt das `ResourceAssignment` daran. Kein neues Modell, keine
Aufweichung von Demand≠Assignment (Kernprinzip, Abschnitt 3) — reine UX-Abstraktion über dem
bestehenden Modell. `[Rollen aufschlüsseln]` bleibt als expliziter, optionaler Button
verfügbar.

### 6b.5 Available Capacity

Unverändert gegenüber Abschnitt 6.2/6a.8 — identische Erweiterung um eine bereichsbasierte
Variante von `compute_person_capacity` bleibt nötig, unabhängig von Grob/Fein vs. Hierarchie,
da sie ausschließlich mit Leaf-Zeiträumen arbeitet. Keine neue Capacity-Engine.

### 6b.6 Monatsaggregation ohne zweite Achse

```
Projektkapazität(Monat) = SUM( monthly_distribution(leaf.plan_fte, leaf.forecast_start,
                                leaf.forecast_end)[Monat] für alle Leaf-Nachfahren des Projekts )
```

Identischer werktage-anteiliger Verteilungsschlüssel wie Abschnitt 6a.6 (kein 50/50, kein
Feiertagsabzug, BD-4-konform) — der einzige Unterschied: **eine** Quelle statt zwei, daher keine
`max()`-Formel, kein "Noch grob", keine Konkretisierungsgrad-Kennzahl mehr nötig (BD-13). Die
in Abschnitt 6.3 dokumentierte Aggregationslücke (heutige Portfolio-Endpoints summieren
`ResourceDemand` ohne `plan_phase_id`-Filter) löst sich **strukturell** auf, sobald die
Migration (Abschnitt 6b.9) abgeschlossen ist — es gibt dann keine `plan_phase_id = NULL`-Zeilen
mehr, über die fälschlich mit-addiert werden könnte. Kein Filter-Bugfix an
`compute_capacity_gap`/`get_allocation_gaps`/`get_role_analysis`/`_cockpit_capacity` nötig.

### 6b.7 Subproject wird durch Parent-PlanPhase ersetzt

`Subproject` ist heute technisch nur `{id, name, reihenfolge, project_id}` — keine Zeiträume,
keine Kapazität, feste Tiefe von genau 1 Ebene (Codebase-Audit, Pass-2-Dokument Abschnitt 3.1).
Eine Parent-`PlanPhase` leistet alles, was `Subproject` leistet, zusätzlich mit abgeleiteten
Zeiträumen/Kapazität und beliebiger Tiefe (bis BD-10). Migration: pro `Subproject` eine neue
Top-Level-`PlanPhase` anlegen, bestehende `PlanPhase`/`Milestone`/`Comment` dieses Teilprojekts
auf `parent_phase_id`/`plan_phase_id` umhängen (Details:
[`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)
Abschnitt 22). `subprojects`-Tabelle/`subproject_id`-Spalten bleiben zunächst compat-only
bestehen (kein Drop-and-Pray, analog zum Legacy Cutover Phase 26.9).

### 6b.8 Milestones

`Milestone.subproject_id` → `Milestone.plan_phase_id` (nullable). `NULL` bleibt "projektweiter
Meilenstein". Ein gesetzter Wert kann sowohl auf eine Leaf- als auch auf eine Parent-Phase
zeigen (im Unterschied zur Kapazitätsplanung, die Leaf-only ist) — ein Meilenstein schließt oft
eine Sammelphase ab, nicht eine einzelne Detailphase.

### 6b.9 Migration bestehender Daten

Zwei bestehende, potenziell befüllte Konzepte müssen migriert werden, additiv und ohne
Informationsverlust (vollständiges Vorgehen:
[`P18_ARCHITECTURE_RECONCILIATION_PASS2.md`](P18_ARCHITECTURE_RECONCILIATION_PASS2.md)
Abschnitt 20-22):

- **Bestehende Grobplanung** (`ResourceDemand.plan_phase_id = NULL`): pro Projekt eine neue
  Top-Level-Leaf-Phase "Grobplanung (migriert)" mit Zeitraum = Spanne aller vorhandenen
  Perioden; bestehende `ResourceDemand`-Zeilen werden auf diese Phase umgehängt (Perioden
  bleiben unverändert, eine Leaf-Phase darf mehrere `ResourceDemand`-Zeilen mit
  unterschiedlichen Perioden tragen — technisch bereits heute nicht ausgeschlossen). `plan_fte`
  der neuen Phase bleibt bewusst `NULL` (keine automatische Befüllung aus der
  Rollen-Aufschlüsselung, konsistent mit Abschnitt 3) — Projektleiter bestätigt/setzt den Wert
  einmalig nach der Migration.
- **Bestehende Subprojects:** siehe 6b.7.
- Beide Migrationen sind einmalige, deterministische Skripte mit Vorher-/Nachher-Zahlenreport
  (FTE-Summen, Assignment-Anzahl, Milestone-Anzahl unverändert) — kein Datenverlust.

### 6b.10 Was unverändert aus Abschnitt 6a übernommen wird

Nicht jede Pass-1-Überlegung wird verworfen — folgende Teile sind unabhängig von der
Grundsatzentscheidung gültig und werden 1:1 übernommen: die Formel für `plan_hours`/
`monthly_distribution` (Abschnitt 5.2/6a.6, werktage-anteilig, kein Feiertagsabzug, BD-4), die
`compute_person_capacity_for_range`-Erweiterung (Abschnitt 6a.8/6.2), das Prinzip "`plan_fte`
bleibt führend, keine automatische Synchronisierung aus der Rollen-Aufschlüsselung"
(Abschnitt 3).

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
| Grobplanung (Monats-FTE) | `ResourceDemand` mit `plan_phase_id = NULL` | Planning-Tab → `ResourceDemandGrid` | — | aktuell (Abschnitt 6.1); **noch nicht** von Feinplanung abgegrenzt in Portfolio-Aggregationen (Abschnitt 6.3, Lücke) |
| Grobplanstunden/Feinplanstunden/Konsumption/Konkretisierungsgrad | berechnet (P18 Pass 1-Vorschlag, **superseded**) | nicht editierbar | `ResourceDemand`(Grob)/`PlanPhase.plan_fte`(Fein) × Werktage-Monatsverteilung | **P18 Pass 1 — Design, superseded durch Pass 2** (Abschnitt 6a.3/6a.6/6a.10) |
| Projektmonatskapazität (unter P18 Pass 2) | berechnet (P18-Pass-2-Vorschlag) | nicht editierbar | `SUM` über `monthly_distribution` aller Leaf-`PlanPhase`s | **P18 Pass 2 — Design, nicht implementiert** (Abschnitt 6b.6) |

---

## 14. Open Business Decisions

| ID | Frage | Status |
|---|---|---|
| BD-1 | Tempo/Jira-Worklog → PlanPhase-Mapping: welches Kriterium (Datum, Ticket-Feld, manuelle Zuordnung)? | offen — `effort_consumption_pct`/`ist_hours` liefern bis dahin konsequent `null`, keine Heuristik |
| BD-3 | Bewertungs-Thresholds für Phasenmetriken (🟢/🟡/🔴 auf `plan_hours`/`time_progress_pct`/Reconciliation)? | offen — Metriken werden aktuell ohne Ampel gezeigt |
| BD-4 | Feiertags-Handling für Planstunden (aktuell Mo–Fr ohne Feiertagsabzug) | offen, dokumentierter Scope-Cut, keine stille Baseline-Änderung |
| BD-5 | `ResourceAssignment` mit Teil-Zeiträumen (Sub-Ranges) statt einer FTE über die ganze Demand-Periode? | offen |
| BD-6 | `allocation_gap`-Vorzeichenkonvention vereinheitlichen (siehe Abschnitt 9, bekannte Inkonsistenz zwischen `ResourceDemandOut` und `CockpitCapacity`) | offen, bewusst nicht rückwirkend angefasst |
| BD-7 | *(P18 Pass 1)* Capacity-Consumption-Formel `max(Grobplanstunden, Feinplanstunden)` (Abschnitt 6a.10)? | **obsolet** — Pass 2 (Abschnitt 6b) hat keine zwei Achsen mehr, die reconciliert werden müssten (siehe Pass-2-Dokument Abschnitt 28) |
| BD-8 | *(P18 Pass 1)* Soll `BaselineSnapshot` Grobplanung einfrieren, granular oder aggregiert (Abschnitt 6a.9)? | **obsolet** — unter Pass 2 gibt es nur noch eine Kapazitätsquelle je Phase, kein Granularitäts-Dilemma mehr (Abschnitt 6b.9, Pass-2-Dokument Abschnitt 16) |
| BD-9 | *(P18 Pass 1)* Rollout additiv vs. direkt (Abschnitt 6a.13)? | **obsolet** — ersetzt durch die Migrationsreihenfolge in Abschnitt 6b.9/Pass-2-Dokument Abschnitt 27 |
| BD-10 | *(P18 Pass 2)* Maximale `PlanPhase`-Hierarchietiefe: 2 oder 3 Ebenen (Abschnitt 6b.1)? | offen — Empfehlung: 3 Ebenen (Pass-2-Dokument Abschnitt 9.3/28) |
| BD-11 | *(P18 Pass 2)* Löschverhalten einer Parent-Phase mit Kindern: kaskadierend (wie heute bei `Subproject`) vs. blockieren vs. Reparenting? | offen — Empfehlung: kaskadierend mit Bestätigungsdialog, konsistent mit heutigem `delete_subproject`-Verhalten (Pass-2-Dokument Abschnitt 28) |
| BD-12 | *(P18 Pass 2)* Migrationsstrategie für bestehende `Subproject`-/Grobplanungs-Daten: automatisiertes Skript vs. manuelle Nachplanung? | offen — Empfehlung: automatisiertes, deterministisches Skript mit Vorher-/Nachher-Report (Pass-2-Dokument Abschnitt 20/22/28) |
| BD-13 | *(P18 Pass 2)* Soll "Konkretisierungsgrad"/Planungsreife als Kennzahl in neuer Form weiterleben oder ersatzlos entfallen (Abschnitt 6b.6)? | offen — Empfehlung: ersatzlos streichen (Pass-2-Dokument Abschnitt 28) |

**Aufgelöst mit P11 (nicht mehr offen):** Status-Normalisierung (vormals BD-2) — Zielvokabular
Geplant/In Arbeit/Abgeschlossen/Entfällt ist definiert und über eine Frontend-Mapping-Schicht
umgesetzt (Details Abschnitt 16.1). Die Backend-Spalte bleibt bewusst Freitext (keine
destruktive Migration), Governance ist damit vollständig für dieses Konsolidierungsziel.

**Nicht als BD aufgenommen (P18-Audit, weil Code/Analyse bereits eindeutig sind):**
Rollenbedarf/Personen auf der Grobachse (Level 1–3, Abschnitt 6a.5) — bereits heute technisch
unterschränkt möglich, keine offene Frage. Teilprojekt-scharfe Grobplanung (Abschnitt 6a.11)
— kein identifizierter fachlicher Bedarf, daher keine BD, sondern bewusst außerhalb des
Scopes. Monatsverteilungsschlüssel (Abschnitt 6a.6) — eindeutig aus bestehender
Werktage-Logik ableitbar, keine offene Frage.

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
- Planstand-Relations-UX (Planstand ↔ Blocker/Decision/Comment über `EntityRelation`
  verknüpfen) — geprüft in P13.6, keine bestehende generische Auswahl-UX dafür wiederverwendbar,
  nicht künstlich gebaut (siehe Abschnitt 16.3)
- **P18 Pass 1 (Grob-/Feinplanung-Reconciliation, Abschnitt 6a)** — fachlich fertig
  spezifiziert, aber **superseded durch P18 Pass 2** (Abschnitt 6b); BD-7/BD-8/BD-9 obsolet.
- **P18 Pass 2 (PlanPhase-only/hierarchische Phasen, Abschnitt 6b)** — fachlich fertig
  spezifiziert, aktuell empfohlene Zielarchitektur, Umsetzung wartet auf
  BD-10/BD-11/BD-12/BD-13 (Abschnitt 14). Die in Abschnitt 6.3 dokumentierte Aggregationslücke
  (Doppelzählung Grob+Fein in Portfolio-/Cockpit-Endpoints) besteht bis zur Umsetzung
  unverändert fort.

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
(Grobplanung) vs. Phasenachse (Feinplanung, Abschnitt 6.1) war technisch korrekt getrennt,
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
  Grob+Fein-Summierung in allen Portfolio-/Cockpit-Aggregationen, Abschnitt 6.3, und die
  Monats-only-Beschränkung von `compute_person_capacity`, Abschnitt 6.2) sowie in der
  Codebase Validation Matrix im separaten
  [`P18_DESIGN_AND_IMPLEMENTATION_PLAN.md`](P18_DESIGN_AND_IMPLEMENTATION_PLAN.md).
- **Fachliches Zielbild:** Grobplanung/Feinplanung als zwei Konkretisierungsgrade derselben
  Planung (nicht additiv), Planstunden als gemeinsame Vergleichsbasis, werktage-anteiliger
  Monatsverteilungsalgorithmus für phasenübergreifende Zeiträume, Konkretisierungsgrad als
  reine Kennzahl (keine Ampel, kein Fortschritt) — vollständig in Abschnitt 6a
  spezifiziert, inkl. durchgerechnetem Zahlenbeispiel (6a.6).
- **Keine neue Architektur:** Grobplanung bleibt exakt `ResourceDemand` mit
  `plan_phase_id = NULL` (bereits existierend, nur erstmals benannt). Kein neues Feld, keine
  zweite Available-Capacity-Berechnung, keine zweite Planning Engine (Abschnitt 6a.2). Level
  1–3 der Grobplanungs-Reifegrade (Gesamt-FTE/Rollen/Personen, Abschnitt 6a.5) sind bereits
  heute ohne Codeänderung nutzbar.
- **Drei neue offene Business Decisions** (Abschnitt 14): BD-7 (Konsumptions-Formel für
  Portfolio-Sichten), BD-8 (Grobplanung Teil eines Planstands?), BD-9 (Rollout-Strategie:
  bestehende Endpoints umstellen vs. additiv neuer Endpoint zuerst). Bewusst **keine** BD für
  Fragen, die Code/Analyse bereits eindeutig beantworten (Abschnitt 14, Liste "nicht als BD
  aufgenommen").
- **Nicht umgesetzt (wartet auf BD-7/8/9):** neuer Endpoint
  `GET /projects/{id}/capacity/reconciliation` (Abschnitt 6a.13), UI-Block "Planungsstand
  Kapazität" (Abschnitt 6a.14), `phase_metrics_calc.monthly_distribution()`, Fix der unter
  Abschnitt 6.3 dokumentierten Aggregationslücke, Erweiterung von
  `compute_person_capacity` um Datumsbereich-Unterstützung (Abschnitt 6a.8).
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
  Abschnitt 6b). Kein neues Leaf/Parent-Statusfeld (`has_children` wird berechnet, nicht
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
