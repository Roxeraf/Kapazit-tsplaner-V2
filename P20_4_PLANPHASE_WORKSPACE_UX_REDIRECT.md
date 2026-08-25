# P20.4 — PlanPhase Workspace UX Redesign

## 1. Executive Summary

Kein neuer Domain-Umbau — P18/P19/P20/P20.1/P20.2/P20.3 bleiben fachlich unverändert bestehen.
Dieser Durchgang macht ausschließlich den `PlanPhaseWorkspace`-Übersicht-Tab Projektleiter-
verständlich: eine große Formular-Card + eine permanent sichtbare "Ist-Daten"-Card mit rohem
`jira_label`-Freitextfeld + eine generische "Kennzahlen"-Card wurden durch vier fokussierte
Karten ersetzt (Basisdaten, Steuerung, Meilensteine, Verknüpfte Themen), Meilensteine wanderten
aus dem Aktivität-Tab in die Übersicht, "Zeitfortschritt" heißt jetzt "Zeit verstrichen", und
die vormals dauerhaft sichtbare Jira-Mapping-Eingabe ist eine einklappbare sekundäre Aktion.

Der Audit vor der Implementierung deckte einen echten Backend-Gap auf (nicht nur ein UI-
Problem): `_plan_phase_metrics` in `planning.py` lieferte für **jede** Parent-Phase
`plan_hours=None` und `time_progress_pct=None`, weil die Formeln direkt `p.plan_fte`/
`p.forecast_start`/`p.forecast_end` lasen — Felder, die eine Parent-Phase per Konstruktion nie
selbst trägt. Ohne Fix hätte die im Auftrag geforderte Parent-Übersicht ("Geplanter Aufwand:
Summe Leaf Planstunden") niemals befüllt werden können. Der Fix (Aggregation aus den
Leaf-Nachfahren, analog `derive_parent_capacity`/`parent_ist_hours`) ist Teil dieses
Durchgangs und per neuem Regressionstest sowie Playwright-Browserlauf verifiziert.

Zusätzlich wurde beim Bau des Meilenstein-Erstellungsflows ein zweiter Gap gefunden und
behoben: der "+ Meilenstein"-Anlage-Dialog hatte **kein** Datumsfeld — neu angelegte
Milestones entstanden ohne `forecast_date` und waren in der neuen kompakten Übersicht-Karte
nicht sinnvoll nach Datum sortierbar (Auftrag Abschnitt 14/16).

**Status: P20.4 COMPLETE** (Details/Nachweis Abschnitt 14–16).

## 2. Current UX Audit

Matrix, erhoben durch Lesen von `PlanPhaseWorkspace.tsx`, `PlanPhaseCapacityTab.tsx`,
`MilestoneList.tsx`, `PlanPhaseGantt.tsx`, `schemas.PhaseMetricsOut`/`PlanPhaseDetail`,
`phase_metrics_calc.py`, `worklog_actuals.py`, `planning.py` (`_plan_phase_metrics`) und
CONCEPT.md, **vor** jeder Code-Änderung:

| Bereich | aktuelle UI (vor P20.4) | fachlicher Zweck | Problem | Zielzustand (P20.4) |
|---|---|---|---|---|
| Name/Zeitraum | Große Formular-Card, Name-Input + Zeitraum-Inputs in eigenem `field-row` mit viel Leerraum | Sofort erkennen, was/wann | Wirkt wie ein Datenbank-Formular, nicht wie eine Zusammenfassung | Kompakte Basisdaten-Karte, gleiche Editierbarkeit, weniger Chrome |
| Status | Select im selben `field-row` wie das jetzt entfernte Plan-FTE-Echo | Aktueller Zustand der Phase | War an technische Nachbarfelder gekoppelt | Eigene Zeile in Basisdaten-Karte |
| Owner | `PersonPicker` **plus** ein zusätzlicher `<p>{people.get(...)}</p>`-Absatz mit demselben Namen darunter | Verantwortliche Person | Redundante Doppel-Anzeige (Auftrag Abschnitt 4: "keine doppelten Owner-Anzeigen") | Nur noch der `PersonPicker`-Chip (zeigt den Namen bereits selbst) |
| Parent | Select "Übergeordnete Phase" | Einordnung in Hierarchie | Unproblematisch, aber mitten in der Formular-Card | Bleibt erhalten, in Basisdaten-Karte |
| Tags | `TagInput` in der Formular-Card **und** dieselben Tags nochmal (oder "Noch keine Tags…") in der "Verknüpfte Themen"-Karte darunter | Freie Kategorisierung | Doppelte Darstellung derselben Information (Auftrag Abschnitt 21) | Nur im Header/Basisdaten, "Verknüpfte Themen" zeigt sie nicht mehr |
| Jira-Label/Ist-Zuordnung | Eigene, **permanent sichtbare** Card "Ist-Daten" mit Freitext+Datalist-Feld `jira_label`, Erklärtext, Mapping-Preview | Technische Integrationskonfiguration für den Worklog-Resolver | Ein Projektleiter sieht bei jedem Öffnen ein rohes Integrationsfeld, das er 95 % der Zeit nicht braucht (Auftrag Abschnitt 6) | Nur der resultierende Ist-Status in der Steuerung-Karte; Mapping-Editor hinter sekundärer Aktion "Ist-Zuordnung konfigurieren"/"anzeigen" |
| Kennzahlen | Card "Kennzahlen": Planstunden / Zeitfortschritt / Ist-Aufwand / Aufwandsverbrauch / Verbleibender Planaufwand / Überverbrauch als flache `<strong>Label:</strong> Wert`-Liste | Soll/Ist-Steuerung auf einen Blick | Technisch korrekt, aber wirkt wie ein Feld-Dump des Datenmodells, keine visuelle Vergleichbarkeit von Zeit vs. Aufwand | Card "Steuerung": Geplanter Aufwand, "Zeit verstrichen" als Balken, Ist-Aufwand, "Aufwand verbraucht" als gleich gestylter Balken (direkt vergleichbar, keine Ampel) |
| Zeitfortschritt-Begriff | Label "Zeitfortschritt:" + Klein-Hinweis, dass es kein Fortschrittswert sei | Reiner Datumsanteil | Der Begriff selbst suggeriert "X % fertig" — genau das Gegenteil des tatsächlichen Werts (Auftrag Abschnitt 10) | Label "Zeit verstrichen" |
| Milestones | Kompakte Karte, aber im **Aktivität**-Tab gemountet, zusammen mit Kommentaren/Aufgaben/Blockern | "Was ist wichtig" — wichtige Termine/Ziele der Phase | Ein Projektleiter, der die Phase öffnet, sieht Milestones nicht in der Übersicht, sondern muss erst in den Aktivität-Tab wechseln (Auftrag Abschnitt 14/15) | Eigene Karte im Übersicht-Tab, direkt unter Steuerung |
| Milestone-Anlage | "+ Meilenstein" öffnet Formular mit Name/Übergeordnete Phase/Owner/Tags/Anhänge — **kein Datumsfeld** | Ziel-/Ergebnispunkt zu einem Datum anlegen | Ein Kernattribut des Milestones (das Datum) fehlte im Anlage-Dialog komplett — Auftrag Abschnitt 16 fordert es explizit | Datumsfeld ergänzt; PlanPhase-Picker bei phasenscoped Aufruf ausgeblendet (bereits vorausgewählt) |
| Verknüpfte Themen | Card mit Tags (redundant, s.o.) + drei reinen Text-Zählern (Entscheidungen/Blocker/Dokumente), nicht klickbar | Schneller Überblick über offene Punkte | Zähler ohne Handlung — kein Sprung in den passenden Tab | Kompakt (nur Counts), klickbar → springt in Aktivität-/Dateien-Tab |
| Kapazität-Tab "Steuerung"-Karte | Eigene Card "Steuerung" mit **denselben** Rohmetriken wie die Übersicht-"Kennzahlen"-Karte (Ist-Aufwand/Aufwandsverbrauch/Zeitfortschritt/Rest/Überverbrauch) zusätzlich zum Personen-Drilldown | Kapazitätsspezifische Auswertung (wer hat gearbeitet) | Vollständige Duplikation zweier Karten im selben Drawer mit identischem Inhalt (Auftrag Abschnitt 24) | Umbenannt zu "Ist-Aufwand nach Person", nur noch Personen-Drilldown + Projekt-Coverage; generische Metriken nur noch in der Übersicht |
| Parent-Übersicht Aufwand/Zeit | `metrics.plan_hours`/`metrics.time_progress_pct` waren für **jede** Parent-Phase `None` (Backend-Bug, nicht nur UI) | "Geplanter Aufwand: Summe Leaf Planstunden" / "Zeit verstrichen: bezogen auf derived Parent-Zeitraum" (Auftrag Abschnitt 26) | Feature war strukturell unmöglich zu bauen, solange das Backend keine Daten lieferte | `_plan_phase_metrics` aggregiert für Parents jetzt aus den Leaf-Nachfahren (siehe Abschnitt 11) |
| PhaseMetricsOut (Schema) | Enthielt bereits alle nötigen Felder (`time_progress_pct`, `plan_hours`, `ist_hours`, `effort_consumption_pct`, `remaining_plan_hours`, `overrun_hours`) | — | Kein Schema-Problem, reines Berechnungsproblem für Parents | Unverändert, keine Schema-Änderung nötig |

## 3. Overview Information Architecture

Der Übersicht-Tab folgt jetzt vier klar getrennten Karten in fester Reihenfolge (siehe
`PlanPhaseWorkspace.tsx`):

1. **Basisdaten** — Name, Zeitraum, Status, Übergeordnete Phase, Owner, Tags.
2. **Steuerung** — Plan/Zeit/Ist/Verbrauch (Abschnitt 4).
3. **Meilensteine** — kompakte Liste + "+ Meilenstein" (Abschnitt 7).
4. **Verknüpfte Themen** — Blocker-/Entscheidungen-/Dokumente-Counts (Abschnitt 8).

Keine zusätzlichen technischen Konfigurationskarten dazwischen — insbesondere keine dauerhaft
sichtbare Jira-Mapping-Card mehr. Technische Feldnamen (`forecast_start`, `jira_label`,
`mapping_source`, `ResourceDemand`, `BaselineSnapshot`, …) erscheinen nirgends in der UI.

## 4. Steuerung UX

Ersetzt die vormalige "Kennzahlen"-Karte 1:1 an derselben Stelle im Layout, aber neu
strukturiert:

- **Geplanter Aufwand** — `metrics.plan_hours` (z. B. "98.8 h"), optional eine kleine Zeile
  darunter mit `plan_fte` als FTE-Referenz ("0.65 FTE über den Phasenzeitraum") — **keine**
  zweite Editierstelle, rein informativ (Plan-FTE bleibt exklusiv im Kapazität-Tab editierbar).
- **Zeit verstrichen** — `metrics.time_progress_pct` als Balken + Prozentzahl.
- **Ist-Aufwand** — Wert oder "Noch nicht eindeutig zugeordnet"; darunter bei vorhandenem Ist
  zusätzlich **Aufwand verbraucht** (`effort_consumption_pct`) als **gleich gestylter** Balken
  — Zeit- und Aufwandsbalken sind bewusst identisch (Farbe `var(--blau)`, Höhe, Radius)
  gestaltet, damit sie auf einen Blick vergleichbar sind, **ohne** dass daraus eine
  Bewertung/Ampel abgeleitet wird (BD-3 bleibt separat offen, keine rot/gelb/grün-Logik
  eingeführt).
- **Restlicher Planaufwand**/**Überverbrauch** — wie zuvor, nur wenn vorhanden.
- **Ist-Zuordnung** — sekundäre Aktion, siehe Abschnitt 6.

## 5. Time Progress Terminology

`time_progress_pct` heißt in der UI jetzt durchgehend **"Zeit verstrichen"**
(`PlanPhaseWorkspace.tsx` Steuerung-Karte; die vormals separate, jetzt entfernte
"Zeitfortschritt"-Zeile in `PlanPhaseCapacityTab.tsx` gab es kein zweites Vorkommen). Ein
projektweiter Grep nach `Zeitfortschritt` im Frontend-Quellcode findet nach der Änderung nur
noch einen erklärenden Code-Kommentar, der den Terminologiewechsel selbst dokumentiert — keine
UI-sichtbare Stelle mehr.

Berechnung unverändert (`gap_calc.expected_progress_pct`, von `phase_metrics_calc.time_progress`
durchgereicht): heute vor Start → 0 %, heute nach Ende → 100 %, Start == Ende → `None`
(dargestellt als "—", kein Crash, keine >100 %-Anzeige). Diese Edge Cases waren bereits vor
P20.4 korrekt implementiert und wurden in diesem Durchgang gegen den Auftrag geprüft, nicht neu
gebaut.

## 6. Jira Mapping UX

Die P20-Mapping-Logik selbst (Manual Override → Label-Match → Unmapped/Ambiguous,
`worklog_resolver.py`) ist **unverändert** — P20.4 ändert ausschließlich die UI-Platzierung
(Auftrag Abschnitt 28), Option C aus dem Auftrag ("kleine Aktion im Steuerungsbereich") wurde
umgesetzt:

- Ohne Mapping: Steuerung zeigt "Ist-Aufwand: Noch nicht eindeutig zugeordnet" + sekundäre
  Aktion **"Ist-Zuordnung konfigurieren"**.
- Mit Mapping: Steuerung zeigt den resultierenden Ist-Status (Stunden, Verbrauchsbalken);
  Mappingdetails (Jira-Label-Feld, Erklärtext, Mapping-Preview) erscheinen nur nach Klick auf
  **"Ist-Zuordnung anzeigen"/"ausblenden"**.
- `showMapping`-State wird bei jedem Phasenwechsel zurückgesetzt (kein versehentlich
  offenstehender Editor beim Navigieren zwischen Phasen).
- `ProjectJiraTab.tsx` verweist jetzt auf die neue Fundstelle ("Übersicht → Steuerung →
  Ist-Zuordnung konfigurieren") statt auf die entfernte "Ist-Daten"-Card.
- Nur auf Leaf-Phasen sichtbar (Parent-Phasen tragen nie ein eigenes `jira_label`, unverändert).

## 7. Milestone UX

Fachliche Abgrenzung (dokumentiert in CONCEPT.md Abschnitt 5.5): `PlanPhase` = Arbeitszeitraum,
`Milestone` = Ziel-/Ergebnis-/Freigabepunkt zu einem Datum, trägt keine `plan_fte`, ist keine
künstliche Mini-PlanPhase. Domainmodell unverändert.

UX-Änderungen:

- Die Meilensteine-Karte (`MilestoneList.tsx`, wiederverwendet, kein zweites Modell) liegt jetzt
  im Übersicht-Tab statt im Aktivität-Tab, für Leaf **und** Parent-Phasen.
- **Gap gefunden und behoben:** der Anlage-Dialog hatte kein Datumsfeld. Ergänzt: `forecastDate`-
  State, `<input type="date">` neben dem Namensfeld, `forecast_date` wird jetzt an
  `api.createMilestone` mitgesendet. Ohne diesen Fix wären neu angelegte Milestones nie sinnvoll
  nach Datum sortierbar gewesen (Auftrag Abschnitt 14 verlangt genau diese Sortierung).
- Der "Übergeordnete Phase"-Picker im Anlage-Dialog ist ausgeblendet, wenn die Komponente mit
  einer `planPhaseId`-Prop (phasenscoped, aus dem Workspace) aufgerufen wird — die Phase ist
  dann bereits fest vorausgewählt, kein technischer Doppel-Picker mehr nötig. Der projektweite
  Aufruf aus `ProjectPlanningTab.tsx` (ohne `planPhaseId`-Prop) behält den Picker unverändert.
- `ActivityFeed`s `onOpenSection`-Callback wurde angepasst: ein Klick auf ein Milestone-Ereignis
  im Aktivitäts-Feed springt jetzt in den Übersicht- statt in den Aktivität-Tab (sonst hätte der
  Klick ins Leere geführt, da die Karte dort nicht mehr existiert) — ohne diese Korrektur wäre
  das eine stille Regression gewesen.
- Projektweite Milestones (`plan_phase_id = NULL`) und Parent-Milestones bleiben unverändert
  möglich — keine Leaf-only-Restriktion eingeführt.

## 8. Linked Context UX

"Verknüpfte Themen" zeigt jetzt ausschließlich Blocker-/Entscheidungen-/Dokumente-Counts (keine
Tags mehr — die stehen bereits in den Basisdaten, kein doppeltes "Noch keine Tags"-Echo). Jeder
Count ist ein klickbarer Button, der über den bereits vorhandenen `setTab`-Mechanismus in den
zuständigen Tab springt (Blocker/Entscheidungen → Aktivität, Dokumente → Dateien) — keine neue
Knowledge-Engine, keine neuen Endpoints.

## 9. Leaf UX

Entspricht dem Zielbild aus dem Auftrag (Abschnitt 25): Basisdaten kompakt, Steuerung mit
Plan/Zeit/Ist/Verbrauch als Balken, Meilensteine direkt sichtbar, Verknüpfte Themen als reine
Counts. Verifiziert per Playwright gegen eine ungemappte ("Test", ohne `jira_label`) und eine
gemappte ("Konfiguration", mit `jira_label`) Leaf-Phase (Abschnitt 15).

## 10. Parent UX

Entspricht dem Zielbild aus Abschnitt 26: abgeleiteter Zeitraum ("Aggregiert aus N
Unterphasen"), Steuerung zeigt jetzt **echte aggregierte Werte** (Fix Abschnitt 11/2), keine
Plan-FTE-Eingabe, keine Personenbesetzung, keine "Ist-Zuordnung konfigurieren"-Aktion (Parent
trägt nie ein eigenes `jira_label`). Meilensteine und Verknüpfte Themen bleiben nutzbar. Der
Kapazität-Tab zeigt für Parents unverändert den aggregierten Sammelphasen-Hinweis statt eines
Zuweisungsformulars.

## 11. Frontend Changes

- `frontend/src/views/project/components/PlanPhaseWorkspace.tsx` — Übersicht-Tab komplett neu
  strukturiert (siehe Abschnitt 3–8); neue lokale `Bar`-Komponente (reiner Balken, keine
  Ampel-Farblogik); `showMapping`-State; `onOpenSection`-Fix für Milestone-Aktivitätsereignisse;
  Meilensteine-Mount aus dem Aktivität-Tab entfernt; ungenutzte Imports (`TagChip`,
  `usePeopleMap`) entfernt.
- `frontend/src/views/project/components/PlanPhaseCapacityTab.tsx` — "Steuerung"-Karte zu
  "Ist-Aufwand nach Person" umbenannt und auf Personen-Drilldown + Projekt-Coverage reduziert
  (keine Duplikation der Übersicht-Steuerung mehr).
- `frontend/src/views/project/ProjectJiraTab.tsx` — Verweistext auf die neue Mapping-Fundstelle
  aktualisiert.
- `frontend/src/views/project/components/MilestoneList.tsx` — Datumsfeld im Anlage-Dialog
  ergänzt (`forecastDate`-State, `forecast_date` im `createMilestone`-Payload), Phase-Picker im
  phasenscoped Aufruf ausgeblendet.

## 12. API Changes

Kein neuer Endpoint, kein Schema-Feld. Eine gezielte Berechnungskorrektur:

- `backend/app/routers/planning.py` (`_plan_phase_metrics`): für Parent-Phasen (`has_children`)
  werden `time_progress_pct` aus `planning_calc.derive_parent_bounds` (statt der stets-`None`
  eigenen `forecast_start`/`forecast_end`) und `plan_hours` als Summe der
  `phase_metrics_calc.plan_hours`-Werte aller Leaf-Nachfahren (statt des stets-`None` eigenen
  `plan_fte`) berechnet — analog zum bestehenden Muster `derive_parent_capacity`/
  `parent_ist_hours`. `None` bleibt `None`, wenn kein Leaf-Nachfahre gültige Werte hat (kein
  Leaf mit Zeitraum bzw. kein Leaf mit `plan_fte`), nie eine irreführende 0. Leaf-Verhalten
  (unverändert `p.plan_fte`/`p.forecast_start`/`p.forecast_end`) bleibt exakt wie zuvor. Betrifft
  sowohl `GET /projects/plan-phases/{id}` (`PlanPhaseDetail.metrics`) als auch
  `GET /projects/plan-phases/{id}/metrics` (dieselbe Funktion, ein Implementierungsort).

## 13. CONCEPT.md Changes

- Versions-Header (v0.27) und Änderungs-Absatz für P20.4.
- Neuer Abschnitt **16.30 "P20.4 — PlanPhase Workspace UX Redesign"** mit Audit-Kernfund,
  Umsetzung, Nicht-Scope, Gantt/Milestone-Hinweis (dokumentiert, nicht gebaut).
- Übersicht-Tab-Beschreibung (Abschnitt 10) komplett neu geschrieben: Leitfragen-Tabelle je Tab,
  Vier-Karten-Struktur, Parent-Übersicht-Absatz.
- Kapazität-Tab-Beschreibung aktualisiert: "Steuerung" → "Ist-Aufwand nach Person", keine
  Duplikation mehr dokumentiert.
- Terminologie-Bullet "Zeitfortschritt" → "Zeit verstrichen" (Abschnitt 3, Kernprinzipien).
- Feature-Tabelle (Abschnitt 6): Zeilen "Zeitfortschritt", "Planstunden", "Phase-Jira-Zuordnung"
  auf die neue UI-Platzierung/Terminologie aktualisiert.
- Milestones-Abschnitt (5.5): Kartenplatzierung korrigiert (Übersicht statt Aktivität) +
  expliziter Abgrenzungs-Absatz PlanPhase vs. Milestone (Auftrag Abschnitt 32).
- Keine Änderung an B-1–B-8-Status, BD-1/BD-3-Status, Historie-Abschnitten (P20.3 bleibt
  unangetastet, Auftrag Abschnitt 29).

## 14. Tests

Backend (`backend/scripts/test_*.py`, alle real gegen SQLite-TestClient ausgeführt, kein
Skip/Mock der Assertions):

| Suite | Ergebnis |
|---|---|
| Alle 17 bestehenden Regressionsskripte | **PASS**, unverändert |
| `test_p20_phase_actual_metrics.py`, neuer Fall 6/6 (Parent-Aggregation `plan_hours`/`time_progress_pct`) | **PASS** — 2 Leaf-Kinder 80h+40h=120h, leerer Parent → `None` |
| `check_migrations.py` | **PASS** — kein Drift, keine Schemaänderung, Roundtrip sauber (45 Tabellen) |

Frontend:

| Check | Ergebnis |
|---|---|
| `tsc -b` | **PASS**, keine Fehler |
| `oxlint` | **PASS**, nur vorbestehende, unveränderte Warnungen in nicht berührten Dateien |
| `vite build` | **PASS**, sauberer Production-Build |

Abgedeckte Szenarien (Auftrag Abschnitt 35, per Playwright gegen echten Dev-Stack statt reiner
Komponententests — siehe Abschnitt 15, im Repo existiert kein Vitest/Jest-Setup, etabliertes
Muster aus P20.1–P20.3 ist der echte Browserlauf): Leaf Overview (mit/ohne Mapping), Parent
Overview, Phase ohne/mit mehreren Milestones, projektweiter Milestone (Seed-Daten), Parent
Milestone (Seed-Daten), Tags (keine Dopplung), Blocker/Decision/Document Counts.

## 15. Playwright Results

Echter Headless-Chromium-Lauf (`/opt/pw-browsers/chromium-1194`) gegen den echten Vite-Dev-
Server (127.0.0.1:5173) + FastAPI/uvicorn (127.0.0.1:8000), frische SQLite-DB. Testdaten wurden
vor dem Browserlauf per echter HTTP-API angelegt (`seed.py`: 1 Projekt, Leaf-Phase ohne
Mapping, Leaf-Phase mit Mapping, Parent-Phase mit 2 Leaf-Kindern, 3 Milestones inkl. projektweit
und parent-gebunden) — kein DB-Direktzugriff, keine Mock-Responses. Navigation per bestehendem
Deep-Link `/projekte/{id}/planung?openPhase={phaseId}`.

**37/37 Checks PASS**, 0 unbehandelte Console-/Page-Errors:

1. Projekt/Planung-Tab lädt
2. Leaf-Phase-Drawer öffnet (Übersicht aktiv)
3. Header zeigt Phasenname
4. Kein permanent sichtbares Jira-Label-Feld
5. Kein "Kennzahlen"-Block mehr
6. "Steuerung"-Karte sichtbar
7. "Zeit verstrichen" sichtbar, "Zeitfortschritt" nicht mehr
8. "Geplanter Aufwand" mit Stundenwert sichtbar
9. Ist-Empty-State ("Noch nicht eindeutig zugeordnet") verständlich
10. Ist-Zuordnung über sekundäre Aktion erreichbar, Feld erscheint nach Klick
11. Meilensteine-Karte im Übersicht-Tab, vorab gesäter Milestone sichtbar
12–13. Zwei neue Milestones live über die UI erstellt, erscheinen sofort
14. Milestones korrekt nach Datum sortiert (28.08. → 04.09. → 10.09.)
15. Verknüpfte Themen kompakt, keine doppelte Tag-Anzeige
16. Kapazität-Tab weiterhin voll funktionsfähig, umbenannt, keine Duplikat-"Steuerung"
17. Aktivität-Tab weiterhin funktionsfähig, keine Meilensteine-Karte mehr dort
18. Dateien-Tab lädt
19. Gemappte Phase: Ist-Stundenwert statt Empty-State, Verbrauchsbalken sichtbar, Aktionslabel
    "Ist-Zuordnung anzeigen"
20. Parent-Phase öffnet, "Aggregiert aus 2 Unterphasen", Steuerung zeigt **echte** aggregierte
    Werte ("Geplanter Aufwand: 80 h", "Zeit verstrichen: 56.1 %" — vor dem Backend-Fix wäre
    dies "—"/leer gewesen)
21. Parent zeigt keine "Ist-Zuordnung konfigurieren"-Aktion, keine Plan-FTE-/
    Zuweisungsoberfläche in Kapazität
22. Keine unbehandelten Console-/Page-Errors während des gesamten Laufs

## 16. Remaining UX Risks

- **Verknüpfte-Themen-Klicks springen nur den Tab, nicht bis zum konkreten Objekt.** Der
  Auftrag erlaubt das explizit ("wenn vorhandene Navigation dies bereits erlaubt") — eine
  feingranulare Navigation bis zum einzelnen Blocker/zur einzelnen Entscheidung existiert im
  bestehenden Code nicht und wurde bewusst nicht neu gebaut (kein Scope-Zuwachs).
- **Milestones im Gantt bleiben unverändert nicht dargestellt** (Auftrag Abschnitt 19/34) — rein
  dokumentiert als späterer UX-Ausbau, kein Bestandteil dieses Durchgangs.
- **Kapazität-Tab-Kartenname "Ist-Aufwand nach Person"** ist neu und ersetzt "Steuerung" an
  dieser Stelle — sollte in einer künftigen UX-Iteration mit echten Nutzern gegengeprüft werden,
  ob der Name den Karteninhalt (Personen-Drilldown + Projekt-Coverage) intuitiv trifft.
- **Keine automatisierten Frontend-Komponententests** (kein Vitest/Jest im Repo, unverändert
  seit P18/P19/P20 — etabliertes Muster ist der echte Playwright-Browserlauf). Ein zukünftiges
  Setup würde die in Abschnitt 14/15 abgedeckten Szenarien zusätzlich isoliert regressionssicher
  machen, ist aber kein P20.4-Scope.
- **Balken-Farbe ist aktuell hart auf `var(--blau)` codiert** (keine Ampel, wie gefordert) — bei
  einer künftigen BD-3-Umsetzung (Health-Bewertung) müsste die `Bar`-Komponente um einen
  optionalen Farb-Parameter erweitert werden; heute bewusst ohne, um keine Bewertung zu
  suggerieren.

---

# P20.4 COMPLETE
