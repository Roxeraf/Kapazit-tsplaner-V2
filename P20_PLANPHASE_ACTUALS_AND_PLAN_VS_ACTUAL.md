# P20 — PlanPhase Actuals, Tempo-Mapping & Plan-vs-Actual Control

**Status:** Audit + Architecture/Implementation Plan. **NICHT IMPLEMENTIERT** — dieser
Durchgang liefert ausschließlich die fachliche/technische Grundlage für eine spätere
Umsetzung (P20.1–P20.8).

**Vorbedingung erfüllt:** P19 Final Consistency Audit (Abschnitt 2) — drei echte
Inkonsistenzen korrigiert, keine Neustrukturierung.

**Kernaussage vorab:** Es gibt heute **kein** Mapping zwischen einem Tempo/Jira-Worklog und
einer einzelnen `PlanPhase`. `JiraWorklogCache` kennt nur `(jira_account_id, jira_issue_key,
datum, stunden, projekt_mapping)` — projekt_mapping ist die `Project.id`, es gibt kein
`plan_phase_id`-Feld und keine Tabelle, die Issue-Metadaten (Component/Label/Summary/Epic)
über den Sync-Zeitpunkt hinaus aufbewahrt. `phase_metrics_calc.effort_consumption()` ist ein
bewusster Stub, der immer `None` liefert; das ist laut Code-Kommentar und CONCEPT.md
korrekt und beabsichtigt (BD-1). Dieses Dokument schließt BD-1, indem es das Mapping,
den Resolver, die Datenmodelländerungen und die Implementierungspakete definiert.

---

## 1. Executive Summary

Die Soll-Seite (P18/P19) ist stabil: `PlanPhase` ist die alleinige operative
Planungseinheit, Kapazität läuft über `plan_fte` → `phase_metrics_calc.plan_hours()` →
Personenbesetzung → derived monthly/portfolio capacity. Die Ist-Seite (Tempo/Jira) endet
heute strukturell auf **Projektebene**: `JiraWorklogCache.projekt_mapping` verknüpft einen
Worklog mit genau einem `Project`, nicht mit einer `PlanPhase`. Der einzige vorhandene
Soll/Ist-Vergleich (`gap_analysis.project_gap`, `GET /gap`, `GET /forecast`) ist zusätzlich
bewusst von der `PlanPhase`-Architektur entkoppelt — er vergleicht Legacy-`ResourceDemand`
(Grobplanung) gegen Ist-FTE, nicht `PlanPhase.plan_fte`. Das ist eine dokumentierte,
bewusste Trennung (CONCEPT.md, Abschnitt 16.15 Punkt 6: "Secondary Consumer Assessment"),
kein Bug.

P20 schließt die fehlende Verbindung **additiv**, ohne die bestehende Architektur, den
Forecast-Trend oder die Health-Engine zu ersetzen:

- **Ein neues, nullable Feld `PlanPhase.jira_label`** verfeinert das bereits vorhandene
  `Project.jira_component`-Mapping innerhalb eines Projekts (Option B, siehe Abschnitt 6/7).
- **Eine neue Tabelle `JiraIssueCache`** hält die pro Issue nötigen Metadaten (Labels,
  Component, Summary) — heute wird das beim Sync verworfen, siehe Abschnitt 3/22.
- **Eine neue Tabelle `WorklogPhaseOverride`** erlaubt manuelle Korrektur pro Issue, ohne
  Jira/Tempo-Originaldaten zu verändern (Option E als Ausnahmemechanismus, Abschnitt 10).
- **Ein deterministischer Resolver** (Override → Label-Match → sonst unmapped/ambiguous,
  Abschnitt 8) füllt `PhaseMetricsOut.ist_hours`/`effort_consumption_pct` erstmals mit echten
  Werten — für Phasen ohne Mapping bleibt es explizit "nicht zugeordnet", nie `0`.
- **Keine Datumsheuristik, keine Doppelzählung, keine verlorenen Stunden** — Coverage
  (Abschnitt 16) macht Mapping-Vollständigkeit sichtbar statt sie zu verstecken.

**Empfehlung (Abschnitt 7):** Option F (Hybrid: Label-Match + manueller Override), mit BD-1
in fünf geschlossene Teilentscheidungen zerlegt (Abschnitt 26). **Ergebnis dieses
Durchgangs: READY FOR P20 IMPLEMENTATION** (Abschnitt 34) — vorbehaltlich der in Abschnitt 26
dokumentierten Bestätigung durch den Product Owner, dass Jira-Teams künftig
Phase-Labels pflegen (organisatorische Voraussetzung, keine technische Unsicherheit mehr).

---

## 2. P19 Final Consistency Fixes

Vor P20 wurden Abschnitte 1–14 von CONCEPT.md gegen den realen Code geprüft (kein
Neustrukturieren, nur echte Inkonsistenzen). Ergebnis: **drei von vier geprüften Punkten
hatten bereits den korrekten Ziel-Stand**, ein Punkt wurde jetzt korrigiert.

| # | Prüfpunkt | Befund | Aktion |
|---|---|---|---|
| 1 | Abschnitt 6.1 Zukunftssprache ("PlanPhase **wird** die einzige Planungseinheit") | Bestätigt inkonsistent — Zeile 439 nutzte noch Futur, obwohl Zeile 190 (Executive Summary) bereits korrekt "**ist** die einzige operative Planungseinheit" sagt und der Stand seit B-1–B-7 CONFIRMED implementiert ist | **FIXED** — Abschnitt 6.1 auf "ist die einzige operative Planungseinheit" umgestellt |
| 2 | Systemrolle "Ohne Rolle" — Löschbarkeit: fachliche Regel vs. technischer Enforcement-Stand | Abschnitt 6.4 vermischte beides in einem Satz ("Backend lehnt den Löschversuch ab") — das ist ungenau: es gibt **keinen** `DELETE /resource-roles/{id}`-Endpoint überhaupt (405 für alle Rollen), nicht nur eine gezielte Ablehnung für die Systemrolle. Der eigentliche Guard (`ensure_role_deletable`, `routers/capacity.py`) ist vorhanden, aber an keinem Endpoint verdrahtet — das steht bereits korrekt in Abschnitt 16.15 Punkt 5, war aber nicht in Abschnitt 6.4 verlinkt/übernommen | **FIXED** — Abschnitt 6.4 unterscheidet jetzt explizit fachliche Regel (nicht löschbar) und aktuellen technischen Stand (kein Löschpfad existiert; Guard bereit, aber ungenutzt) mit Verweis auf 16.15 Punkt 5 |
| 3 | P19-Workspace: CONCEPT muss dem implementierten UI entsprechen (Übersicht/Kapazität/Activity/Dateien) | **Bereits korrekt.** Abschnitt 10 ("Projekt-Workspace-Tabs" / "PlanPhase-Workspace (Drawer)") beschreibt exakt die vier Tabs mit den geforderten Inhalten: Übersicht = Kontext/Zeitraum/Owner/Teilprojekt/Tags + Breadcrumb, Kapazität = Plan-FTE/Planstunden/Besetzung, Aktivität = Activity Feed/Kommentare/Tasks/Blocker/Decisions/Milestones, Dateien = zentrale Dokumentenkomponente phasengefiltert. "Projektkapazität nach Monat" ist explizit als read-only markiert ("keine neue Berechnung, keine Ampel-/Erfüllungsbewertung") | Kein Fix nötig |
| 4 | Kein aktueller Abschnitt darf `ResourceDemandGrid` als normale Planungsoberfläche darstellen | **Bereits korrekt.** `ResourceDemandGrid` erscheint in Abschnitt 10 nur im ausdrücklich als sekundär markierten, eingeklappten "Legacy-Kapazitätsplanung"-Block (Verweis auf 6.15/17.8) | Kein Fix nötig |

Abschnitte 1–14 sind damit **rebuild-safe aktueller Zustand**. Beide Fixes sind in
`CONCEPT.md` committed (dieser Branch).

---

## 3. Existing Jira/Tempo Architecture

Realer Code (nicht aus CONCEPT.md übernommen, sondern gegen die Dateien verifiziert):

| Datei | Zeilen | Rolle |
|---|---|---|
| `backend/app/jira_client.py` | 172 | Dünner REST-Client für native Jira-API v3 (Basic-Auth). `list_projects`, `list_components`, `list_labels`, `search_users`, `get_user`, `search_issues_for_component`, `fetch_worklogs_for_component` (Fallback ohne Tempo). |
| `backend/app/tempo_client.py` | 98 | Separater Client für Tempo-Cloud-API v4 (Bearer-Token), weil native Jira-Worklogs bei Tempo-Buchung den Tempo-Systemaccount statt der echten Person zeigen. `fetch_worklogs_for_issues`. |
| `backend/app/jira_sync.py` | 154 | `sync_project()` (Fetch + Cache), `berechne_ist_fte()` (Cache → Ist-FTE/Monat, projektweit). |
| `backend/app/routers/jira.py` | 174 | `GET /jira/status`, `GET /jira/lookup-account`, `GET/PUT /jira/projects[...]`, `GET /jira/projects/{key}/components`, `GET /jira/projects/{key}/labels`, `POST /jira/sync`. |
| `backend/app/models.py:191-220` | — | `JiraWorklogCache`, `JiraProjectCatalog`, `UnassignedJiraAuthor`. |
| `backend/app/gap_analysis.py` | 109 | `project_gap()` — Soll (Legacy `ResourceDemand`) vs. Ist (`jira_sync.berechne_ist_fte`) je Monat + Trendhochrechnung. Genutzt von `GET /gap`, `GET /forecast`. |
| `backend/app/phase_metrics_calc.py` | 118 | `time_progress`, `plan_hours`, `monthly_distribution`, `reconcile`, `assignment_summary`, **`effort_consumption` (Stub, immer `None`, BD-1)**. |
| `backend/app/health_calc.py` | 257 | `_effort_health()` konsumiert `project_gap()` — projektweite Health-Dimension, nicht phasenscoped. |
| `frontend/src/views/project/ProjectJiraTab.tsx` | 121 | Projektweiter Jira-Tab: Verknüpfungsanzeige, Ist-FTE-Tabelle je Monat, "Jetzt synchronisieren"-Button, Anzeige unzugeordneter Buchungen (Personen, nicht Stunden). |
| `frontend/src/views/JiraProjects.tsx` | — | Katalogseite `/jira-projekte` (welche Jira-Projekte werden geplant). |

**Wichtigster Befund:** Es existiert **kein** Code-Pfad, der einen Worklog mit einer
`PlanPhase` verknüpft. `PlanPhase` hat kein Jira-Feld. Das ist konsistent mit
`PhaseMetricsOut.ist_hours = None`/`effort_consumption_pct = None` — kein Fake-Ist, keine
Datumsheuristik, wie in CONCEPT.md (BD-1) dokumentiert.

---

## 4. Worklog Data Available

Verifiziert im Code, nicht angenommen:

**Was `tempo_client.fetch_worklogs_for_issues()` tatsächlich zurückgibt** (Zeile 83-97):
`issue_key`, `author_account_id`, `author_display_name` (= Account-ID, Tempo liefert keinen
Namen), `started` (Datum), `stunden`. **Sonst nichts** — kein Description-Feld, kein
Tempo-Account/Team, keine Issue-Metadaten.

**Was `jira_client.fetch_worklogs_for_component()`** (nativer Fallback, Zeile 133-172)
zurückgibt: `issue_key`, `author_account_id`, `author_display_name` (echter Klarname aus
Jira), `started`, `stunden`. Ebenfalls keine Issue-Metadaten im Worklog-Objekt selbst.

**Was tatsächlich in Jira/Tempo verfügbar wäre, aber aktuell nicht abgefragt/gecached
wird:**
- Issue-Metadaten: Summary, Component(s) (mehrere möglich), Labels (mehrere möglich),
  Issue-Type, Epic-Link/Parent, Status — `jira_client._search_issues()` fragt bewusst nur
  das `fields`-Set an, das der jeweilige Aufrufer braucht (`"key"` bei
  `search_issues_for_component`, `"labels"` bei `list_labels`) — es gibt keinen
  Aufrufer, der Issue-Metadaten zusammen mit Worklogs abfragt und persistiert.
- Tempo-spezifische Felder: Tempo kennt "Tempo Accounts" (Kostenstellen) und
  "Worklog Attributes" (custom fields) — die API liefert sie im `/worklogs`-Response
  (`attributes`), werden hier aber nicht gelesen (`tempo_client.py:89-97` extrahiert nur
  vier Felder aus dem Rohobjekt).
- `description`-Feld des Worklogs selbst — im Tempo-Response vorhanden, wird nicht gelesen.

**Konsequenz für P20:** Jede Mapping-Option, die auf Component/Label/Epic/Issue-Type basiert
(Optionen A–D), braucht eine **Erweiterung des Sync-Pipelines**, um diese Felder pro Issue
zusätzlich abzufragen und zu cachen — sie sind heute nicht verloren, weil sie fehlen,
sondern weil sie nie abgefragt wurden.

---

## 5. Current Project Mapping

Exakter Ablauf (verifiziert):

1. `Project.jira_component` (nullable String) — ein einzelner String pro Kapa-Projekt, per
   UI im Einstellungen-Tab gesetzt (Picker aus `jira_client.list_components`/`list_labels`).
2. `jira_client.search_issues_for_component(component, since)` baut JQL:
   `(component = "X" OR labels = "X") AND worklogDate >= "since"` — **ein String matcht
   sowohl Component als auch Label**, es gibt keine Unterscheidung zwischen "das ist eine
   Component" und "das ist ein Label" im Datenmodell. Das ist bewusst pragmatisch (ein Feld
   für beide Jira-Organisationsstile), aber macht das Projekt-Mapping selbst schon
   nicht-triviial nachvollziehbar.
3. Treffer-Issues (nur `key`+`id`) werden an Tempo (falls konfiguriert) oder den nativen
   Jira-Worklog-Endpoint übergeben.
4. Rückgabe wird in `JiraWorklogCache` upserted mit `projekt_mapping = str(project.id)`.

**Geprüfte Randfälle (Code-Verifikation, nicht nur Doku-Annahme):**

| Randfall | Befund |
|---|---|
| Mehrere Projekte mit gleicher Component/Label | **Nicht verhindert.** `Project.jira_component` hat **kein** Unique-Constraint (im Gegensatz zu `jira_project_key`, das `unique=True` ist, Zeile 32). Zwei Kapa-Projekte könnten denselben String eintragen → derselbe Worklog würde in beiden Projekten separat gesynct (kein Constraint verhindert es, kein Code erkennt es). **Bestehende Lücke, nicht P20-Scope, aber für P20 relevant**, da Phase-Level-Mapping dieselbe Schwäche erben würde ohne expliziten Fix (siehe Abschnitt 29). |
| Mehrere Components je Projekt | Nicht unterstützt — `jira_component` ist ein einzelner String, kein Array. |
| Fehlende Component | `sync_project` wird für Projekte ohne `jira_component` gar nicht aufgerufen (`routers/jira.py:143`, Filter `isnot(None)`); `berechne_ist_fte` liefert `{}` (Zeile 118-119). |
| Worklog auf Epic/Task/Subtask | JQL filtert nicht nach Issue-Type — alle Typen mit passender Component/Label matchen gleich. |
| Jira-Projekt vs. Component | Getrennte Konzepte im Code: `jira_project_key` (Katalog-Herkunft, 1:1 mit Kapa-Projekt) vs. `jira_component` (Such-Scope für Worklogs) — ein Kapa-Projekt kann `jira_project_key` gesetzt haben, ohne dass `jira_component` gesetzt ist (dann kein Sync). |
| Labels | Werden identisch zu Components behandelt (siehe JQL oben) — kein getrenntes Feld. |
| Tempo Accounts (Kostenstellen) | Nicht ausgelesen/genutzt (siehe Abschnitt 4). |

---

## 6. Phase Mapping Options

Bewertung aller sechs Optionen aus dem Auftrag, gegen den realen Code-Stand:

| Option | Aufwand (Backend) | Jira-Prozessaufwand | Determinismus | Migrationssicherheit | Bewertung |
|---|---|---|---|---|---|
| **A — Component pro PlanPhase** | Mittel (JQL-Erweiterung) | **Hoch** — Jira-Components sind meist projektweit verwaltet (Admin-Rechte nötig), nicht für granulare Phasen gedacht; Component-Liste würde mit jeder neuen Phase wachsen | Hoch | Neutral | Technisch sauber, aber organisatorisch schwer skalierbar — Components sind ein Jira-Projektadmin-Artefakt, keine Tagging-Konvention für Sachbearbeiter |
| **B — Label pro PlanPhase** | Mittel (Sync-Erweiterung um Label-Fetch, siehe Abschnitt 4) | **Niedrig** — jeder Jira-Nutzer kann ein Label auf ein Ticket setzen, kein Admin-Recht nötig; Label-Konvention (`phase:configuration`) ist selbsterklärend und bereits im Auftrag als Beispiel vorgeschlagen | Hoch, sofern 1 Label pro Issue eindeutig zur Phase passt | Sehr gut — additiv, kein Alt-Ticket muss migriert werden, alte Tickets bleiben einfach unmapped bis gelabelt | **Empfohlen als Kernmechanismus** |
| **C — Epic/Issue/JQL-Mapping** | Hoch (JQL-Editor, Freitext-Validierung, potenziell fehleranfällige Nutzereingabe) | Mittel — Epics sind eine natürliche Gruppierung, aber nicht jedes Team nutzt Epics 1:1 mit Planphasen | Hoch bei sauberer Epic-Struktur, aber JQL-Freitext ist eine Fehlerquelle (Tippfehler, ungültige Syntax) | Neutral | Zu mächtig/fehleranfällig als Standard; als Ausnahme-Escape-Hatch (spezifische Issue-Keys) sinnvoll, aber kein voller JQL-Editor |
| **D — konfigurierbare Mapping-Regel (Component+Label+Type+Epic kombinierbar)** | Sehr hoch — braucht ein generisches Regel-Datenmodell (genau die "generische JSON-Regelmaschine", die der Auftrag explizit ausschließt, Abschnitt 24) | Niedrig bis mittel | Hoch, aber UX-Komplexität hoch (Nutzer muss verstehen, wie Regeln kombiniert werden — UND/ODER?) | Neutral | **Verworfen** — Overengineering für den tatsächlichen Bedarf; 2-3 klare Felder reichen (Auftrag Abschnitt 24) |
| **E — rein manuelle Zuordnung** | Niedrig (nur Override-Tabelle) | Keiner | Hoch (explizit) | Sehr gut | Nicht **allein** tragfähig — skaliert nicht (jeder Worklog einzeln zuordnen), aber unverzichtbar als Korrekturmechanismus für Ausnahmen (Projektmanagement/Steuerung-Buchungen, falsch gelabelte Tickets) |
| **F — Hybrid (B + E)** | Summe aus B + E, aber kein zusätzliches Regel-Datenmodell | Niedrig (nur Label-Pflege, Overrides nur für Ausnahmen) | Hoch, mit definierter Priorität (Abschnitt 8) | Sehr gut | **Empfohlen** |

---

## 7. Recommended Mapping Architecture

**Empfehlung: Option F (Hybrid) = Option B (Label pro PlanPhase) als deterministischer
Automatik-Mechanismus + Option E (manueller Override je Issue) als Korrekturmechanismus.**
Kein Component-pro-Phase (zu Jira-Admin-lastig), kein voller JQL/Epic-Editor (zu
fehleranfällig, zu viel UI-Komplexität für den Nutzen), keine generische Regelmaschine
(Auftrag schließt das explizit aus).

**Warum das die geforderten Kriterien (Abschnitt 35 des Auftrags) am besten erfüllt:**

- **Deterministisch:** Ein Issue hat eine feste Menge an Labels zu einem Zeitpunkt; das
  Matching ist eine reine Mengen-Operation (Issue-Labels ∩ Phase-Labels des Projekts),
  keine Heuristik.
- **Erklärbar:** "Dieses Ticket hat das Label `phase:configuration`, deshalb zählt sein
  Worklog zur Phase 'Konfiguration'" ist ohne Jira-Kenntnisse verständlich — im Gegensatz zu
  Component-IDs oder JQL.
- **Manuell korrigierbar:** `WorklogPhaseOverride` (Abschnitt 10) fängt jede Ausnahme ohne
  Jira/Tempo-Schreibzugriff auf.
- **Ohne Datumsheuristik:** Das Matching hängt nie vom `worklog_date` ab, nur von
  Issue-Labels — unterstützt parallele Phasen direkt (Abschnitt 12).
- **Migrationssicher:** Additiv, nullable, kein Alt-Projekt bricht (Abschnitt 25).
- **Jira-Aufwand niedrig:** Labels sind das einzige Jira-Konzept, das ein Sachbearbeiter
  ohne Admin-Rechte pflegen kann — entscheidend für Akzeptanz im Tagesgeschäft.

**Bewusst nicht gewählt:** Ein Fallback auf Component-pro-Phase zusätzlich zu Label wurde
geprüft und verworfen — zwei parallele automatische Matching-Wege ohne zwingenden Grund
widersprechen Abschnitt 11 des Auftrags ("nicht mehrere konkurrierende
Mapping-Mechanismen ohne Priorität"; hier gäbe es keinen fachlichen Grund für zwei
gleichwertige Automatik-Kanäle, nur zusätzliche Komplexität).

---

## 8. Mapping Priority / Resolver

**BD-1A (CLOSED): Resolver-Priorität**, exakt eine Kette, keine konkurrierenden
Mechanismen:

```
1. Manual Override        (WorklogPhaseOverride, Issue-Key-Ebene)  → höchste Priorität
2. Label-Match             (Issue-Labels ∩ PlanPhase.jira_label im Projekt)
3. kein Treffer            → UNMAPPED (Projekt-Ist bleibt vollständig, siehe Abschnitt 9)
   (mehrere Treffer)       → AMBIGUOUS (siehe Abschnitt 10 der Vorlage / Abschnitt 10 unten)
```

**Resolver-Pseudocode (fachlich, keine Implementierung):**

```
for worklog in project_worklogs:
    if exists WorklogPhaseOverride(issue_key=worklog.issue_key):
        phase = override.plan_phase_id
    else:
        matching_phases = PlanPhase.filter(
            project_id == worklog.project_id,
            jira_label != null,
            jira_label in JiraIssueCache[worklog.issue_key].labels,
        )
        if len(matching_phases) == 0:
            phase = UNMAPPED
        elif len(matching_phases) == 1:
            phase = matching_phases[0]
        else:
            phase = AMBIGUOUS
```

Datum spielt an **keiner** Stelle eine Rolle — nur Issue-Identität (Override) und
Issue-Labels (Automatik).

---

## 9. Unmapped Worklogs

**Kein neues Konzept nötig, additive Auswertung auf vorhandenem `JiraWorklogCache`.**
Ein Worklog ohne Override und ohne Label-Treffer bleibt Teil der Projekt-Ist-Summe
(`jira_sync.berechne_ist_fte`, unverändert), zählt aber in keiner Phase mit. UI zeigt
explizit `Nicht zugeordnet: X h` (Abschnitt 8/16 des Auftrags, Acceptance Test 2) —
niemals stilles Verschwinden. Datenmodell: keine neue Tabelle, "unmapped" ist der
Resolver-Zustand "keine Zeile in `WorklogPhaseOverride`, keine passende
`PlanPhase.jira_label`" — muss nicht persistiert werden, wird zur Anzeigezeit berechnet.

---

## 10. Ambiguous Worklogs

Tritt auf, wenn ein Issue Labels trägt, die zu **mehr als einer** `PlanPhase` desselben
Projekts passen (z.B. Issue hat Labels `phase:schnittstellen` und `phase:testing`, beide
sind als `jira_label` unterschiedlicher Phasen im selben Projekt eingetragen). Der
Worklog wird **einmal** in die Kategorie `AMBIGUOUS` gezählt, **nicht** doppelt in beide
Phasen (Acceptance Test 3). UI zeigt `X h nicht eindeutig zugeordnet (Issue ABC-123:
Labels passen zu "Schnittstellen" und "Testing")` mit direktem Link zu einem
Override, um die Mehrdeutigkeit sofort aufzulösen.

**BD-1B (CLOSED):** Ambiguous-Worklogs zählen weder zu einer Phase noch zu "unmapped" —
eigene dritte Kategorie in der Coverage-Anzeige (Abschnitt 16), damit die
Coverage-Kennzahl nicht fälschlich 100% suggeriert, obwohl eine Zuordnung tatsächlich
unklar ist.

---

## 11. Manual Overrides

**BD-1C (CLOSED): Overrides sind erlaubt und nötig**, aber bewusst **grobkörnig auf
Issue-Key-Ebene**, nicht auf einzelne Worklog-Zeilen (Datum+Person) — Begründung: ein
Ticket gehört im Regelfall fachlich zu genau einer Phase über seine gesamte Laufzeit;
eine zeilenscharfe Override-UI (jede einzelne Buchung einzeln zuordnen) wäre unnötige
Bedienlast ohne fachlichen Zusatznutzen für den Normalfall. Die seltene Ausnahme
("ABC-123 wechselte fachlich die Phase") wird durch Bearbeiten/Löschen des Overrides
gelöst, nicht durch feinere Granularität.

**Vorhandene Infrastruktur geprüft, bevor ein neues Modell vorgeschlagen wird:**
`EntityRelation` (generische `source_entity_type/id → target_entity_type/id`-Verknüpfung,
`models.py:393-415`) wurde als Wiederverwendungskandidat geprüft. **Nicht passend:**
`EntityRelation` verknüpft zwei Entitäten **innerhalb** dieser Datenbank (beide Seiten
haben eine lokale `id`); ein Jira-Issue-Key ist aber ein externer String ohne lokale
Entität. Eine künstliche "JiraIssue"-Entität nur für diesen Zweck anzulegen wäre
Overengineering gegenüber einer simplen Zwei-Spalten-Tabelle. **Entscheidung: neue,
schlanke Tabelle `WorklogPhaseOverride`** (siehe Abschnitt 22), kein Missbrauch von
`EntityRelation`.

**Wichtig (Auftrag Abschnitt 10):** Override verändert **niemals** Jira/Tempo-Originaldaten
— nur lokale Zuordnungsinformation, exakt wie `projekt_mapping` in `JiraWorklogCache`
heute bereits verfährt (kein Schreibzugriff auf Jira/Tempo existiert im gesamten Code,
verifiziert: beide Clients sind read-only, kein `PUT`/`POST` gegen Jira/Tempo-Worklogs).

---

## 12. Parent/Leaf Actual Semantics

**BD-1D (CLOSED):** `PlanPhase.jira_label` ist **nur auf Leaf-Phasen sinnvoll** — analog zu
`plan_fte`, das laut Abschnitt 6.1a bei Parent-Phasen auf `NULL` gesetzt wird, sobald die
Phase Kinder erhält. Gleiche Regel für `jira_label`: **wird eine Leaf-Phase zum Parent
(erstes Kind), wird ihr `jira_label` serverseitig auf `NULL` gesetzt** (identischer
Lifecycle-Mechanismus wie `plan_fte`, kein neuer Code-Pfad, nur dasselbe Feld
mitbehandelt in `_promote_to_parent`/Äquivalent). Ist-Stunden einer Parent-Phase sind
**immer** die rekursive Summe ihrer Leaf-Nachfahren:

```
ist_hours(parent) = SUM( ist_hours(leaf) für leaf in planning_calc.leaf_descendants(parent) )
```

`planning_calc.leaf_descendants()` existiert bereits (`planning_calc.py:60`) und wird für
die Kapazitätsaggregation verwendet — **keine neue Traversal-Logik**, reine
Wiederverwendung.

**Explizit erlaubte Ausnahme (Auftrag Abschnitt 7):** "Projektmanagement"/"Steuerung"/
"allgemeine Workshops" sind selbst **Leaf-Phasen** (wie jede andere operative Phase) —
kein Sonderfall im Modell, sie bekommen einfach ein eigenes `jira_label` wie
`phase:pm`. Kein Worklog landet direkt auf einem aggregierenden Parent, weil Parents per
Definition kein `jira_label` (mehr) tragen können — der Resolver kann sie strukturell gar
nicht treffen.

---

## 13. Phase Actual Metrics

Nach Mapping wird `phase_metrics_calc.effort_consumption()` implementiert (heute Stub,
Abschnitt 3):

```
ist_hours(leaf) = SUM(stunden) über alle JiraWorklogCache-Zeilen, deren Issue laut Resolver
                  (Abschnitt 8) genau dieser Phase zugeordnet ist
ist_hours(parent) = SUM(ist_hours(leaf)) über leaf_descendants (Abschnitt 12)
effort_consumption_pct = ist_hours / plan_hours × 100   (unverändert wie bereits in
                          phase_metrics_calc.py dokumentiert, nur die None-Rückgabe entfällt)
```

`PhaseMetricsOut.ist_hours`/`effort_consumption_pct` liefern damit erstmals reale Werte für
Phasen mit Mapping; für Phasen ohne `jira_label` **und** ohne zugehörige gemappte Worklogs
bleibt es weiterhin explizit `null` mit dem UI-Text "Ist-Aufwand noch nicht zugeordnet"
(Acceptance Test 6) — **nicht** `0.0`, da `0.0` fälschlich "sicher keine Arbeit" suggerieren
würde.

---

## 14. Person Actuals

`Person.jira_account_id` existiert bereits und ist laut Modellkommentar "Alleinige Quelle
für die Jira-/Tempo-Worklog-Zuordnung" (`models.py:96-98`) — für den Personen-Drilldown
je Phase reicht eine zusätzliche Gruppierung der ohnehin schon Resolver-zugeordneten
`JiraWorklogCache`-Zeilen nach `jira_account_id` → `Person`, exakt wie
`jira_sync.berechne_ist_fte` es heute bereits projektweit nach Monat gruppiert
(`jira_sync.py:141-154`). **Kein neues Modell, keine neue Capacity-Quelle** — reine
zusätzliche Aggregationsdimension auf denselben Rohdaten.

```
ist_hours_je_person(phase) = SUM(stunden) gruppiert nach jira_account_id → Person.display_name,
                              über dieselben gemappten Worklog-Zeilen wie Abschnitt 13
```

---

## 15. Assignment vs. Actual

Datenmodell-/API-seitig ist das direkt ableitbar, ohne neue Tabelle: `planned persons`
kommt aus `ResourceAssignment` (join über `ResourceDemand.plan_phase_id`), `actual persons`
aus Abschnitt 14. Eine Person erscheint als "ungeplant, aber tatsächlich aktiv", wenn sie
in der Ist-Gruppierung auftaucht, aber in keinem `ResourceAssignment` dieser Phase. **Nur
Datenverfügbarkeit wird hier hergestellt** (P20.6, Abschnitt 28) — keine Health-Regel, kein
automatisches Werturteil, wie vom Auftrag gefordert (Abschnitt 17: "nicht zwangsläufig
direkt eine Health-Regel bauen").

```
unplanned_actual_hours(phase) = SUM(ist_hours_je_person) für Personen ohne
                                 ResourceAssignment auf dieser Phase
```

Nur wenn eindeutig aus bestehenden Daten berechenbar (Abschnitt 18 des Auftrags) — das ist
hier der Fall, da beide Seiten (`ResourceAssignment.person_id`,
`JiraWorklogCache.jira_account_id` → `Person`) bereits vorhanden sind.

---

## 16. Mapping Coverage

Zentrale Vertrauens-Kennzahl (Auftrag Abschnitt 28, wichtiger als eine Ampel):

```
project_ist_total   = SUM(alle JiraWorklogCache-Zeilen dieses Projekts)   [unverändert,
                       berechne_ist_fte-Quelle]
phase_mapped_total  = SUM(ist_hours über alle Leaf-Phasen des Projekts, Abschnitt 13)
ambiguous_total     = SUM(Worklogs im AMBIGUOUS-Zustand, Abschnitt 10)
unmapped_total      = project_ist_total - phase_mapped_total - ambiguous_total
coverage_pct        = phase_mapped_total / project_ist_total × 100  (bei project_ist_total
                       == 0: undefiniert/null, nicht 0 oder 100)
```

Erfüllt Acceptance Test 2 exakt: 120h Projekt, 100h gemappt, 20h unmapped → Projekt-Ist
bleibt 120h, Coverage 83,3%, keine Stunde verschwindet.

---

## 17. Plan-vs-Actual UX

Erweiterung des bestehenden Kapazität-Tabs im PlanPhase-Workspace (Abschnitt 10
CONCEPT.md, "Kapazität"-Tab, unverändert vier Tabs) um eine neue Karte, **kein neuer Tab**:

```
KAPAZITÄT / STEUERUNG

Geplanter Ressourcenbedarf     0,50 FTE
Planstunden                    80 h

Ist-Aufwand                    60 h        [Details ▾]
Aufwandsverbrauch              75 %
Zeitfortschritt                50 %
Restbudget                     20 h
```

"Details ▾" klappt den Personen-Drilldown (Abschnitt 14) und ggf. eine Hinweiszeile
"15 h durch nicht eingeplante Ressourcen" (Abschnitt 15) auf. Bei fehlendem Mapping:
"Ist-Aufwand: noch nicht zugeordnet [Jira-Zuordnung konfigurieren]" statt einer Zahl.
**Keine Ampel** (Auftrag Abschnitt 15/21 — explizit ausgeschlossen für P20).

**Neue Konfigurations-UX** (Auftrag Abschnitt 26), im Übersicht-Tab der Phase als
kompakte Zeile, analog zum bestehenden Component/Label-Picker-Muster aus dem
projektweiten Einstellungen-Tab (`jira_client.list_labels`, bereits als Endpoint
vorhanden):

```
IST-DATEN
Jira-Label   [phase:configuration ▾]     Matched Issues: 24
```

Dropdown statt Freitext — befüllt aus `GET /jira/projects/{key}/labels` (existiert
bereits), gefiltert auf Labels, die im Component-Scope des Projekts tatsächlich
vorkommen. Keine Regex-/JQL-Eingabe als Standardpfad (Auftrag Abschnitt 26).

---

## 18. Project Rollup

**BD-1E (CLOSED):** Projekt-Ist ändert sich durch P20 **nicht** — `jira_sync.berechne_ist_fte`
bleibt exakt wie heute die alleinige Quelle für `Project`-Ebene und `GET /gap`/`GET
/forecast` (Abschnitt 20). Phase-Mapping ist eine **zusätzliche, optionale Aufschlüsselung**
derselben `JiraWorklogCache`-Zeilen, kein Ersatz. Damit ist strukturell ausgeschlossen, dass
unvollständiges Phasen-Mapping das Projekt-Ist sinken lässt (Auftrag Abschnitt 22):

```
Project Actual Hours = SUM(alle JiraWorklogCache-Zeilen, projekt_mapping = project.id)
                      [unverändert — niemals nur die gemappten Stunden]
```

---

## 19. Portfolio Rollup

Keine neue Ist-Engine (Auftrag Abschnitt 23 — Tempo/Jira bleibt einzige Quelle). Ein
späterer Portfolio-Drilldown (Projekt → Phase → Personen) kann die in Abschnitt 13/14/16
definierten Bausteine direkt wiederverwenden, ist aber **nicht Teil der P20-Pakete**
(Abschnitt 28) — explizit als mögliche Folgearbeit vermerkt, kein eigenes Paket, da der
Auftrag hier ausdrücklich "kann später" sagt, nicht "muss jetzt".

---

## 20. Forecast Assessment

Bestehende Forecast-Engine (`gap_analysis._hochrechnung`, `GET /forecast`) bleibt
**unverändert** — sie arbeitet auf Projekt-Monats-Ebene mit Trendfortschreibung
(Durchschnitt der letzten 3 Ist-Monate). P20 ersetzt sie nicht (Auftrag Abschnitt 20,
Variante C: "nur Plan vs. Ist, kein Forecast" für die neue Phase-Ebene). Phase-Level-Ist
(Abschnitt 13) liefert lediglich `remaining_plan_hours` (Abschnitt 19 des Auftrags,
einfache Subtraktion, keine Hochrechnung):

```
remaining_plan_hours = max(plan_hours - ist_hours, 0)
```

Kein Burn-Rate-Forecast, kein Estimate-to-Complete-Feld auf Phasenebene in P20 — bewusst
zurückgestellt, bis belastbares Ist vorliegt (Auftrag: "erst belastbares Ist, keine
künstliche Forecast-Genauigkeit").

---

## 21. Health Assessment

`health_calc._effort_health` (projektweit, konsumiert `gap_analysis.project_gap`) bleibt
**unverändert** — sie ist bereits laut CONCEPT.md (16.15 Punkt 6) bewusst von der
`PlanPhase`-Architektur getrennt (andere fachliche Frage: "wird so gearbeitet wie
geplant" vs. "wie viel Kapazität ist verplant"). P20 fügt **keine neue
Health-Dimension/Ampel** hinzu (Auftrag Abschnitt 21) — liefert nur die Rohdaten
(`time_progress_pct`, `plan_hours`, `ist_hours`, `effort_consumption_pct`,
`remaining_plan_hours`), aus denen eine spätere, eigenständig zu entscheidende
Phasen-Health-Logik entstehen könnte (BD-3, bereits offen, unverändert offen).

---

## 22. Data Model Changes

Geprüft vor Neuvorschlag (Auftrag Abschnitt 24): `PlanPhase`, `Project`,
`JiraWorklogCache`, `EntityRelation`, `ProjectMembership`, `ResourceAssignment`,
bestehende Jira-Config-Felder (`Project.jira_component`, `Project.jira_project_key`,
`Person.jira_account_id`). Ergebnis: zwei neue, schlanke Tabellen + ein neues Feld sind
nötig, keine generische Regelmaschine.

**1. `PlanPhase.jira_label`** (additiv, nullable `String(200)`) — analog exakt zum
bestehenden Muster `Project.jira_component` (Zeile 29). Nur auf Leaf-Phasen gültig
(Abschnitt 12), serverseitig auf `NULL` gesetzt beim Parent-Übergang, gleicher
Lifecycle wie `plan_fte`.

**2. `JiraIssueCache`** (neu) — hält pro Issue die für das Mapping nötigen Metadaten,
die der Sync heute verwirft (Abschnitt 4):

```
jira_issue_key   String(50), PRIMARY KEY
project_id        FK → projects.id  (welchem Kapa-Projekt das Issue laut Component-Scope
                   zuzuordnen ist — für den Fall gleicher Issue-Keys über Projekt-Grenzen
                   hinweg theoretisch nicht nötig, da Issue-Keys global eindeutig sind,
                   aber erleichtert Coverage-Queries ohne Re-Join über JiraWorklogCache)
labels            Text (kommagetrennt oder JSON-Array — einfache Liste, kein Regelwerk)
component         String(200), nullable
summary           String(500), nullable  (nur für UI-Anzeige "Matched Issues", Abschnitt 17)
last_synced_at     String(40)
```

Wird bei jedem `jira_sync.sync_project()`-Lauf für alle Treffer-Issues aktualisiert
(zusätzlicher `fields`-Parameter `"labels,components,summary"` an den bereits
vorhandenen `_search_issues`-Call in `search_issues_for_component`, keine neue
API-Anfrage nötig, nur ein breiteres `fields`-Set).

**3. `WorklogPhaseOverride`** (neu) — manuelle Korrektur, issue-scoped (Abschnitt 11):

```
id                 PRIMARY KEY
project_id         FK → projects.id
jira_issue_key     String(50), UNIQUE  (ein Override pro Issue, nicht pro Worklog-Zeile)
plan_phase_id      FK → plan_phases.id
note               String(500), nullable
created_by_person_id  FK → persons.id, nullable
created_at         String(40)
```

**Kein Constraint-Fix für Abschnitt 5 (mehrere Projekte, gleiche Component)** in P20 —
dokumentiert als Rand-Risiko (Abschnitt 32), da außerhalb des eigentlichen P20-Auftrags
(Projekt-Mapping bleibt unverändert), aber `JiraIssueCache.project_id` reduziert das
Risiko für die neue Phase-Ebene bereits strukturell (ein Issue kann nur im Scope des
Projekts gematcht werden, für das es beim Sync gefunden wurde).

---

## 23. API Changes

Alle additiv, keine Breaking Changes:

- `PlanPhaseOut`/`PlanPhaseDetail`: neues Feld `jira_label: str | None`.
- `PUT /plan-phases/{id}`: akzeptiert `jira_label` wie jedes andere editierbare Feld
  (bestehender Sofort-Speichern-Pfad, kein neuer Endpoint nötig) — Backend setzt es
  serverseitig auf `NULL` zurück, falls die Phase zu diesem Zeitpunkt bereits Kinder hat
  (Guard analog zum `plan_fte`-Parent-Guard).
- `GET /plan-phases/{id}/jira-matches` (neu) — liefert `Matched Issues: N` für die
  Konfigurations-UX (Abschnitt 17), rein lesend gegen `JiraIssueCache`.
- `PhaseMetricsOut`: `ist_hours`/`effort_consumption_pct` liefern jetzt echte Werte statt
  immer `None`; zusätzlich `remaining_plan_hours: float | None` (neu), `person_actuals:
  list[PersonActualOut]` (neu, Abschnitt 14), `unplanned_actual_hours: float | None` (neu,
  Abschnitt 15).
- `GET /projects/{id}/actuals-coverage` (neu) — liefert die Coverage-Kennzahl (Abschnitt
  16): `project_ist_total`, `phase_mapped_total`, `ambiguous_total`, `unmapped_total`,
  `coverage_pct`.
- `POST/DELETE /plan-phases/{id}/worklog-overrides` (neu) — CRUD für
  `WorklogPhaseOverride`, gescoped auf die Phase (Issue-Key im Body).
- `GET /jira/status`, `GET /jira/sync`, `GET /gap`, `GET /forecast`: **unverändert**.

---

## 24. Frontend Changes

- `ProjectJiraTab.tsx`: neue Coverage-Zeile (Abschnitt 16/23), keine Struktur-Änderung.
- `PlanPhaseWorkspace` → Übersicht-Tab: neue "Ist-Daten"-Zeile mit Label-Picker + Matched
  Issues (Abschnitt 17).
- `PlanPhaseWorkspace` → Kapazität-Tab: neue Karte "Kapazität/Steuerung" (Abschnitt 17)
  additiv unterhalb der bestehenden Plan-FTE/Besetzung-Karte — **kein neuer Tab**, wie vom
  Auftrag (Abschnitt 15) vorgegeben.
- Neue kompakte Komponente `WorklogMappingBadge` (unmapped/ambiguous-Hinweis mit
  "[prüfen]"-Link zu einem kleinen Override-Dialog) — wiederverwendbar zwischen
  Projekt-Jira-Tab und Phase-Kapazität-Tab.
- Kein neues ResourceDemandGrid, kein neues Subproject-UI, keine neue Gantt-Ansicht
  (Auftrag Abschnitt 44).

---

## 25. Migration / Compatibility

Bestehende Projekte ohne `PlanPhase.jira_label`-Pflege funktionieren identisch zu heute
weiter — `ist_hours`/`effort_consumption_pct` bleiben `None`/"nicht zugeordnet", bis ein
Projektleiter aktiv ein Label einträgt (Auftrag Abschnitt 25/42, Acceptance Test 6). Kein
Migrations-Skript rät automatisch ein Mapping (keine automatisierte falsche Zuordnung für
Altprojekte). `JiraIssueCache` startet leer und füllt sich beim nächsten regulären
`POST /jira/sync` — kein Backfill-Zwang, kein Blocker für B-8 (Abschnitt 32).

---

## 26. Business Decisions

BD-1 aus CONCEPT.md wird in diesem Durchgang **geschlossen** und in fünf benannte
Teilentscheidungen zerlegt, jede mit Empfehlung:

| ID | Frage | Entscheidung |
|---|---|---|
| **BD-1A** | Resolver-Priorität? | **CLOSED** — Override > Label-Match > unmapped/ambiguous (Abschnitt 8). Kein Component-, Epic- oder JQL-Match als zusätzlicher Automatik-Kanal. |
| **BD-1B** | Umgang mit mehrdeutigen Worklogs? | **CLOSED** — eigener `AMBIGUOUS`-Zustand, keine Doppelzählung, keine automatische Auflösung; Override löst auf (Abschnitt 10). |
| **BD-1C** | Sind manuelle Overrides erlaubt, auf welcher Granularität? | **CLOSED** — ja, Issue-Key-Ebene (nicht Worklog-Zeile), neue Tabelle `WorklogPhaseOverride` (Abschnitt 11/22). |
| **BD-1D** | Wie verhält sich Mapping bei Parent/Leaf-Übergang? | **CLOSED** — `jira_label` folgt demselben Lifecycle wie `plan_fte` (NULL bei Parent-Übergang), Ist-Aggregation rein rekursiv über `leaf_descendants` (Abschnitt 12). |
| **BD-1E** | Ändert sich die Projekt-Ist-Berechnung? | **CLOSED** — nein, `berechne_ist_fte`/`GET /gap`/`GET /forecast` bleiben unverändert; Phase-Mapping ist rein additive Aufschlüsselung (Abschnitt 18/20). |

**Verbleibende, nicht neu geöffnete Business Decisions** (aus CONCEPT.md, von P20
unberührt, hier nur zur Vollständigkeit referenziert): BD-3 (Health-Schwellen), BD-4
(Feiertags-Handling Planstunden), BD-5 (Sub-Range-Assignments), BD-6
(`allocation_gap`-Vorzeichen) — keiner davon wird durch P20 tangiert oder muss vor der
P20-Umsetzung geklärt werden.

**Eine organisatorische, keine technische Restfrage:** Die Label-Konvention
(`phase:<name>`) muss von den Jira-nutzenden Teams tatsächlich gepflegt werden, sonst
bleibt Coverage niedrig. Das ist kein Blocker für die Implementierung (P20.1–P20.8 sind
unabhängig davon baubar und liefern von Tag 1 an korrekte "nicht zugeordnet"-Werte), aber
der Product Owner sollte den Rollout (Label-Schulung/-Konvention) bewusst einplanen.

---

## 27. CONCEPT.md Changes

Nach Umsetzung von P20.1–P20.8 sind folgende Abschnitte zu aktualisieren (nicht in diesem
Durchgang, da "NOCH NICHT IMPLEMENTIEREN" — hier nur die Änderungsliste für das
Umsetzungspaket P20.8):

- **Abschnitt 4 (Jira)**: Mapping-Kette, `JiraIssueCache`, `WorklogPhaseOverride`,
  Resolver-Priorität dokumentieren; BD-1 als CLOSED markieren mit Verweis auf dieses
  Dokument.
- **Abschnitt 5.2/13 (Phase Metrics / Source-of-Truth-Matrix)**: `ist_hours`/
  `effort_consumption_pct`-Zeile von "deferred (BD-1), liefert null" auf "aktuell,
  Resolver-basiert, null nur ohne Mapping" ändern.
- **Abschnitt 9 (GAP)**: Klarstellen, dass `GET /gap`/`GET /forecast` weiterhin
  projektweit auf Legacy-`ResourceDemand` basieren und **nicht** die neue
  Phase-Ist-Quelle nutzen (bewusste Trennung, Abschnitt 18/20 hier).
- **Abschnitt 10 (Workspace)**: neue Kapazität-Tab-Karte, neue Übersicht-Tab-Zeile
  (Abschnitt 17/24 hier) ergänzen.
- **Abschnitt 13 (Source-of-Truth-Matrix)**: neue Zeilen `PlanPhase.jira_label`,
  `JiraIssueCache`, `WorklogPhaseOverride`, `Mapping Coverage`.
- **Historische BD-1-Herleitung bleibt erhalten** (nicht löschen, nur als CLOSED
  markieren und auf dieses Dokument verweisen) — Muster identisch zu BD-7/BD-8/BD-9
  ("obsolet"-Markierung mit Verweis), wie in Abschnitt 14 bereits etabliert.

---

## 28. Implementation Packages P20.1–P20.8

Grenzen an den tatsächlichen Codeaudit angepasst (Abschnitt 3/22/23):

| Paket | Inhalt | Abhängig von |
|---|---|---|
| **P20.1 — Jira/Tempo Mapping Domain** | `PlanPhase.jira_label` (Migration + Parent-Guard-Erweiterung), `JiraIssueCache`-Tabelle + Sync-Erweiterung (`fields`-Set erweitern, Abschnitt 4/22), `WorklogPhaseOverride`-Tabelle + CRUD-Endpoints | — |
| **P20.2 — Worklog → PlanPhase Resolver** | Resolver-Modul (Abschnitt 8), reine Funktion `resolve_phase_for_worklog(...)`, keine Seiteneffekte, testbar isoliert | P20.1 |
| **P20.3 — Unmapped / Ambiguous Handling** | Coverage-Berechnung (Abschnitt 16), `GET /projects/{id}/actuals-coverage` | P20.2 |
| **P20.4 — Phase Actual Metrics** | `phase_metrics_calc.effort_consumption()` implementieren, `ist_hours`/`remaining_plan_hours` in `PhaseMetricsOut`, Parent-Aggregation via `leaf_descendants` (Abschnitt 12/13) | P20.2 |
| **P20.5 — Plan-vs-Actual Workspace UX** | Kapazität-Tab-Karte, Übersicht-Tab Label-Picker (Abschnitt 17/24) | P20.4 |
| **P20.6 — Person Actual Drilldown** | Personen-Gruppierung (Abschnitt 14), Assignment-vs-Actual-Vergleich (Abschnitt 15) | P20.4 |
| **P20.7 — Project/Portfolio Rollup & Coverage** | `ProjectJiraTab.tsx`-Coverage-Anzeige (Abschnitt 24), Verifikation, dass Projekt-Ist unverändert bleibt (Abschnitt 18, Acceptance Test 2) | P20.3 |
| **P20.8 — Regression / CONCEPT / E2E** | CONCEPT.md-Update (Abschnitt 27), alle 6 Acceptance Tests (Abschnitt 31) als automatisierte Tests, Regressionscheck `GET /gap`/`GET /forecast` unverändert (Abschnitt 20) | P20.1–P20.7 |

---

## 29. Dependency Graph

```
P20.1 (Datenmodell + Sync-Erweiterung)
   │
   ▼
P20.2 (Resolver)
   │
   ├──────────────┬──────────────┐
   ▼              ▼              │
P20.3          P20.4             │
(Coverage)   (Phase Metrics)     │
   │              │              │
   │              ├──────┬───────┘
   │              ▼      ▼
   │           P20.5   P20.6
   │         (Workspace UX) (Person Drilldown)
   ▼              │      │
P20.7 ◄────────────┴──────┘
(Project/Portfolio Rollup)
   │
   ▼
P20.8 (Regression/CONCEPT/E2E)
```

---

## 30. Parallel Agent Plan

Nach P20.1+P20.2 (müssen sequenziell zuerst fertig sein, da alles andere auf dem Resolver
aufbaut) können folgende Pakete **parallel** bearbeitet werden, da sie unterschiedliche
Dateien/Layer berühren und nur lesend auf denselben Resolver-Output zugreifen:

- **Track A:** P20.3 (Coverage-Berechnung, `gap_analysis.py`-Nachbarmodul) + P20.7
  (Coverage-UI im bestehenden `ProjectJiraTab.tsx`)
- **Track B:** P20.4 (`phase_metrics_calc.py`-Erweiterung) → danach P20.5
  (Workspace-UX) und P20.6 (Person-Drilldown) parallel zueinander, da beide nur lesend
  auf die in P20.4 neu befüllten `PhaseMetricsOut`-Felder zugreifen und unterschiedliche
  UI-Komponenten betreffen.

P20.8 (Regression/E2E/CONCEPT) läuft erst, wenn alle anderen Pakete gemerged sind — kein
Parallelisierungspotenzial, da es genau die Integration aller vorherigen Pakete prüft.

---

## 31. Test Strategy

Die sechs Acceptance Tests aus dem Auftrag werden 1:1 zu automatisierten Tests in P20.8:

| Test | Prüft | Paket |
|---|---|---|
| AT1 — Eindeutiges Mapping (Konfiguration, 3 Personen, 60h) | Resolver + Aggregation + Personen-Drilldown, keine Doppelzählung | P20.2/P20.4/P20.6 |
| AT2 — Unmapped (120h Projekt, 100h Phasen, 20h unmapped) | Projekt-Ist bleibt 120h, Coverage 83,3%, keine verlorenen Stunden | P20.3/P20.7 |
| AT3 — Ambiguous (8h matcht 2 Phasen) | Einmalige Zählung, `AMBIGUOUS`-Status, Projekt-Ist bleibt 8h | P20.2/P20.3 |
| AT4 — Parallele Phasen (identischer Zeitraum) | Trennung ausschließlich über Label, Datum irrelevant | P20.2 |
| AT5 — Parent-Aggregation (Wareneingang = 20h + 40h) | `leaf_descendants`-Summe, keine doppelte Speicherung | P20.4/P20.12 |
| AT6 — Kein Mapping | UI zeigt "nicht zugeordnet", nicht `0h` | P20.4/P20.5 |

Zusätzlich: Regressionstest, dass `GET /gap`/`GET /forecast`/`health_calc._effort_health`
nach P20 **byte-identische** Ergebnisse liefern wie vor P20 (Abschnitt 18/20/21 —
Nicht-Vermischung von Effort-Soll und Capacity-Soll, bereits als Prinzip in CONCEPT.md
16.15 Punkt 6 etabliert).

---

## 32. Risks

| Risiko | Einschätzung | Gegenmaßnahme |
|---|---|---|
| Teams pflegen Labels nicht konsequent → niedrige Coverage | Mittel, organisatorisch | Coverage-Kennzahl (Abschnitt 16) macht das sofort sichtbar statt es zu verstecken; kein technischer Fix nötig, sondern Prozess-/Schulungsfrage beim Rollout |
| `Project.jira_component` fehlendes Unique-Constraint (Abschnitt 5) erbt sich strukturell in die Phase-Ebene | Niedrig, vorbestehende Lücke, nicht durch P20 verschärft | `JiraIssueCache.project_id` scoped Issues bereits auf das Projekt, das sie beim Sync gefunden hat; volle Lösung (Unique-Constraint auf `jira_component`) ist expliziter Nicht-Scope von P20 (gehört zu Abschnitt 5, nicht zu BD-1) |
| Sync-Erweiterung (breiteres `fields`-Set) erhöht Jira-API-Last | Niedrig — derselbe API-Call, nur mehr Felder im Response, keine zusätzliche Anfrage | Kein zusätzlicher Round-Trip, verifiziert an `_search_issues`-Signatur (Abschnitt 22) |
| Override-Tabelle wird zur Schatten-Wahrheit, wenn Label sich später ändert | Niedrig | Override hat explizit höchste Priorität (Abschnitt 8) — bewusst so gewählt, damit ein Override niemals durch ein nachträglich gesetztes Label "überschrieben" wird; UI zeigt Override-Status transparent an |
| Verwechslung Effort-Soll (Phase) mit Capacity-Soll (`GET /gap`) durch spätere Entwickler | Mittel — bereits einmal in P18 als Risiko erkannt (16.15 Punkt 6) | CONCEPT.md-Update (Abschnitt 27) hält die Trennung explizit fest, Regressionstest (Abschnitt 31) erzwingt sie technisch |

---

## 33. Rebuild Safety Assessment

Alle vorgeschlagenen Änderungen sind **additiv**:
- Zwei neue Tabellen (`JiraIssueCache`, `WorklogPhaseOverride`), kein Schema-Bruch.
- Ein neues nullable Feld (`PlanPhase.jira_label`), kein Pflichtfeld, keine Backfill-Pflicht.
- Kein bestehender Endpoint ändert sein Response-Schema in einer Breaking-Weise (nur neue
  optionale Felder in `PhaseMetricsOut`/`PlanPhaseOut`).
- `GET /gap`, `GET /forecast`, `health_calc.compute_project_health` bleiben unverändert
  (Abschnitt 18/20/21, mit Regressionstest abgesichert).
- Keine Berührung von B-8 (Legacy Cutover), `ResourceDemandGrid`, Subproject-Schema
  (Auftrag Abschnitt 32/44) — verifiziert: keines der vorgeschlagenen P20-Pakete berührt
  `resource_demands.plan_phase_id IS NULL`-Zeilen oder die Legacy-Compat-UI.
- Migrationsreihenfolge unkritisch: `JiraIssueCache`/`WorklogPhaseOverride` können vor
  oder nach `PlanPhase.jira_label` angelegt werden, keine Zirkelabhängigkeit.

---

## 34. Implementation Readiness

**Alle in Abschnitt 26 aufgeführten Teilentscheidungen (BD-1A–BD-1E) sind in diesem
Durchgang geschlossen.** Datenmodell (Abschnitt 22), Resolver (Abschnitt 8), API
(Abschnitt 23), UX (Abschnitt 17/24), Implementierungspakete (Abschnitt 28) und
Testabdeckung (Abschnitt 31) sind vollständig spezifiziert und gegen den realen Code
verifiziert (nicht nur gegen CONCEPT.md-Annahmen). Keine offene technische Unsicherheit
blockiert den Start von P20.1.

Die einzige verbleibende Voraussetzung ist **organisatorisch, nicht technisch**: Der
Product Owner sollte bestätigen, dass die Label-Konvention (`phase:<name>`) im
Jira-Tagesgeschäft der Teams eingeführt werden kann — das beeinflusst die
**Coverage nach Rollout**, nicht die **Machbarkeit der Implementierung**. P20.1–P20.4
liefern von Tag 1 an korrekte Ergebnisse auch bei Coverage 0% (durchgängig "nicht
zugeordnet" statt falscher Werte).

---

# READY FOR P20 IMPLEMENTATION
