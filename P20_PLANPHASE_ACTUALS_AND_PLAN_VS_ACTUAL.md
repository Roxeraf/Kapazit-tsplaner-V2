# P20 — PlanPhase Actuals, Tempo/Jira-Mapping & Plan-vs-Actual Control

**Status:** Concept-Fix + Codebase-Audit + fachliche Entscheidung + Implementation Plan.
**NICHT IMPLEMENTIERT** — dieser Durchgang liefert ausschließlich die fachliche/technische
Grundlage für eine spätere Umsetzung (P20.1–P20.8). Kein Code außer den zwei
CONCEPT.md-Wortlaut-Fixes in Abschnitt 2 wurde in diesem Durchgang verändert.

**Ausgangslage:** Ein früherer P20-Durchgang (`260061b`, gemerged als PR #45) hat dieselbe
fachliche Frage bereits einmal bearbeitet und die Empfehlung Option F (Hybrid:
Label-Match + manueller Override) getroffen. Dieser Durchgang **bestätigt** diese
Empfehlung nach erneuter Codeverifikation (der Code hat sich seither nicht verändert — kein
`jira_label`, keine `JiraIssueCache`, keine `WorklogPhaseOverride` im aktuellen Schema,
`phase_metrics_calc.effort_consumption()` ist weiterhin ein reiner `None`-Stub), schärft sie
um die in diesem Auftrag zusätzlich geforderten Bausteine (Konfliktprüfung beim Speichern,
Mapping-Preview-Mechanik, geschlossene Codebase-Validation-Matrix, BD-1 exakt in die
verlangten Teilfragen A–D zerlegt, zwei zusätzliche Testfälle) und schließt die im Auftrag
neu benannten Concept-Consistency-Punkte.

---

## 1. Executive Summary

Die Planungsarchitektur (P18/P19) ist stabil und wird durch P20 **nicht** angetastet:
`PlanPhase` (Baum) ist die alleinige operative Planungseinheit, `plan_fte` die alleinige
Kapazitäts-Source-of-Truth, Planstunden werden zentral berechnet
(`phase_metrics_calc.plan_hours`), Kapazität wird ausschließlich im Kapazität-Tab bearbeitet
(Abschnitt 2 unten). Die Ist-Seite (Tempo/Jira) endet heute strukturell auf **Projektebene**:
`JiraWorklogCache.projekt_mapping` verknüpft einen Worklog mit genau einem `Project`, nicht
mit einer `PlanPhase`. Es gibt **keinen** Code-Pfad, der einen Worklog mit einer `PlanPhase`
verknüpft — `PlanPhase` besitzt heute kein Jira-Feld. `phase_metrics_calc.effort_consumption()`
ist ein bewusster, dokumentierter Stub, der immer `None` liefert (BD-1, verifiziert
`phase_metrics_calc.py:112-117`). Das ist korrekt: keine Datumsheuristik, keine Fake-Ist-Werte.

Der einzige vorhandene Soll/Ist-Vergleich (`gap_analysis.project_gap`, `GET /gap`,
`GET /forecast`) ist zusätzlich bewusst von der `PlanPhase`-Architektur entkoppelt — er
vergleicht Legacy-`ResourceDemand` (Grobplanung) gegen Ist-FTE, nicht `PlanPhase.plan_fte`.
Dokumentierte, bewusste Trennung (CONCEPT.md Abschnitt 16.15 Punkt 6: "Secondary Consumer
Assessment"), kein Bug, von P20 unberührt.

P20 schließt die fehlende Verbindung **additiv**:

- **Ein neues, nullable Feld `PlanPhase.jira_label`** (nur auf Leaf-Phasen gültig) matcht
  gegen Issue-Labels innerhalb des bereits projektweit gecachten Worklog-Bestands.
- **Eine neue Tabelle `JiraIssueCache`**, die Issue-Metadaten (Labels/Component/Summary)
  hält, die der Sync heute abfragt, aber sofort verwirft.
- **Eine neue Tabelle `WorklogPhaseOverride`** für manuelle Korrektur pro Issue-Key —
  Jira/Tempo-Originaldaten bleiben unverändert.
- **Ein deterministischer Resolver** (Override → Label-Match → sonst unmapped/ambiguous)
  füllt `ist_hours`/`effort_consumption_pct` erstmals mit echten Werten.
- **Konfliktprüfung beim Speichern** verhindert, dass zwei Leaf-Phasen desselben Projekts
  denselben `jira_label`-Wert tragen (strukturell nutzlose Doppelbelegung).
- **Mapping-Preview** vor dem Speichern zeigt Treffer aus dem bereits vorhandenen Cache,
  ohne zusätzliche Jira-API-Last.
- **Keine Datumsheuristik, keine Doppelzählung, keine verlorenen Stunden.** Coverage macht
  Mapping-Vollständigkeit sichtbar statt sie zu verstecken.

**Ergebnis dieses Durchgangs: READY FOR P20 IMPLEMENTATION** (Begründung Abschnitt 36) —
mit einer benannten organisatorischen (nicht technischen) Restfrage in Abschnitt 28.

---

## 2. CONCEPT Consistency Fixes

Zwei vom Auftrag benannte Punkte geprüft, bevor der eigentliche P20-Audit beginnt.

**A) Abschnitt 2 ("Fachlicher Scope") — Teilprojekte als normaler Bestandteil.**

Real geprüft: `CONCEPT.md` Zeile 120 listete bislang
`"Projektplanung (PlanPhase, Milestone, Teilprojekte, Planstände, Gantt-Visualisierung)"` —
Teilprojekte gleichrangig neben PlanPhase/Milestone/Planstände/Gantt aufgeführt. Das
widerspricht dem übrigen Dokument: Abschnitt 5.1 sagt explizit *"'Optionales Teilprojekt'
(`subproject_id`) ist kein primäres Planungsfeld mehr"*, Abschnitt 5.4 trägt bereits den
Titel *"Teilprojekte (Legacy/IST-Hinweis)"* und dokumentiert, dass die Tabelle nur noch
compat-only bis B-8 besteht (Backend-Endpoints `@deprecated`). Reale
Fachfeld-Editierbarkeit im Code (`PlanPhaseCreateModal.tsx`) bietet nur noch den
"Übergeordnete Phase"-Picker, keinen Teilprojekt-Picker als primären Struktur-Mechanismus.

**Fix (angewendet, committed in diesem Durchgang):**

```diff
- Projektplanung (PlanPhase, Milestone, Teilprojekte, Planstände, Gantt-Visualisierung)
+ Projektplanung (PlanPhase-Baum, Milestone, Planstände, Gantt-Visualisierung;
+ Teilprojekte nur noch Legacy/Compat bis B-8, siehe Abschnitt 5.4)
```

**B) Abschnitt 5.1 — doppelte Editierquelle Plan-FTE (Übersicht vs. Kapazität)?**

Real im Frontend geprüft (nicht nur CONCEPT.md gelesen):
`PlanPhaseWorkspace.tsx` definiert `type Tab = "uebersicht" | "kapazitaet" | "aktivitaet" |
"dateien"` (Zeile 54). Der einzige editierbare `<input>` für `plan_fte`
(`"Geplanter Ressourcenbedarf (FTE)"`, `onBlur` → `update({ plan_fte: ... })`) liegt in
Zeile 371–385, **innerhalb** des `tab === "uebersicht"`-Blocks (296–507). Der
`PlanPhaseCapacityTab`-Aufruf (Kapazität-Tab) beginnt erst bei Zeile 508/522 und übergibt
`planFte={detail.plan_fte}` nur als **Anzeigewert** — `PlanPhaseCapacityTab.tsx` rendert ihn
ausschließlich als `<strong>Bedarf:</strong> {fmtFte(summary.plan_fte)}` (Zeile 365), kein
Eingabefeld. **Es gibt im realen Code genau eine Editierquelle (Übersicht-Tab), Kapazität
zeigt Plan-FTE nur read-only als Kopfzeile.**

CONCEPT.md dokumentiert das bereits korrekt: Abschnitt "Planung-Tab im Detail" listet unter
"Übersicht — editierbar: ... Plan-FTE" und unter "Kapazität — Plan-FTE/Planstunden-
**Kopfzeile**" (nicht "editierbar"). **Kein Fix nötig** — reale Codeprüfung bestätigt, dass
CONCEPT.md keine doppelte Editierquelle dokumentiert, weil es real keine gibt. Keine
CONCEPT-Neustrukturierung vorgenommen (Auftragsvorgabe eingehalten).

---

## 3. Existing Jira/Tempo Architecture

Real gegen die Dateien verifiziert (nicht aus CONCEPT.md übernommen):

| Datei | Zeilen | Rolle |
|---|---|---|
| `backend/app/jira_client.py` | 172 | Dünner REST-Client für native Jira-API v3 (Basic-Auth). `list_projects`, `list_components`, `list_labels`, `search_users`, `get_user`, `search_issues_for_component`, `fetch_worklogs_for_component` (Fallback ohne Tempo). Suche paginiert über `/rest/api/3/search/jql` (Nachfolger des abgeschalteten `/search`, `nextPageToken`-basiert). |
| `backend/app/tempo_client.py` | 98 | Separater Client für Tempo-Cloud-API v4 (Bearer-Token) — nötig, weil native Jira-Worklogs bei Tempo-Buchung den Tempo-Systemaccount statt der echten Person zeigen. `fetch_worklogs_for_issues`, paginiert über `metadata.next`. |
| `backend/app/jira_sync.py` | 154 | `sync_project()` (Fetch + Cache-Upsert), `berechne_ist_fte()` (Cache → Ist-FTE/Monat, projektweit, gruppiert). |
| `backend/app/routers/jira.py` | 174 | `GET /jira/status`, `GET /jira/lookup-account`, `GET/PUT /jira/projects[...]`, `GET /jira/projects/{key}/components`, `GET /jira/projects/{key}/labels`, `POST /jira/sync`. |
| `backend/app/models.py:191-220` | — | `JiraWorklogCache`, `JiraProjectCatalog`, `UnassignedJiraAuthor`. |
| `backend/app/gap_analysis.py` | 109 | `project_gap()` — Soll (Legacy `ResourceDemand`) vs. Ist (`jira_sync.berechne_ist_fte`) je Monat + Trendhochrechnung. Genutzt von `GET /gap`, `GET /forecast`. |
| `backend/app/phase_metrics_calc.py` | 118 | `time_progress`, `plan_hours`, `monthly_distribution`, `reconcile`, `assignment_summary`, **`effort_consumption` — verifiziert Zeile 112-117: Stub, gibt unbedingt `None` zurück, Docstring nennt explizit BD-1 als Blocker.** |
| `backend/app/health_calc.py` | 257 | `_effort_health()` konsumiert `project_gap()` — projektweite Health-Dimension, nicht phasenscoped. |
| `frontend/src/views/project/ProjectJiraTab.tsx` | 121 | Projektweiter Jira-Tab: Verknüpfungsanzeige, Ist-FTE-Tabelle je Monat, "Jetzt synchronisieren"-Button, Anzeige unzugeordneter Buchungen (Personen, nicht Stunden). |
| `frontend/src/views/JiraProjects.tsx` | — | Katalogseite `/jira-projekte`. |
| `backend/app/models.py:265-301` | — | `PlanHistory` — generisches Änderungsprotokoll (siehe Abschnitt 14/24 unten, Wiederverwendungsprüfung für Override-Audit). |

**Wichtigster Befund (Zeile für Zeile bestätigt, nicht angenommen):** Es existiert **kein**
Code-Pfad, der einen Worklog mit einer `PlanPhase` verknüpft. `PlanPhase` hat kein
Jira-Feld (`grep plan_phase_id backend/app/models.py` findet nur `Comment`, `Task`,
`Blocker`, `Decision`, `Document`, `PlanHistory`, `ResourceDemand` — keine Jira-Tabelle).
Konsistent mit `PhaseMetricsOut.ist_hours = None`/`effort_consumption_pct = None`.

### Codebase Validation Matrix

| Bereich | Realer Code | Aktuelle CONCEPT.md | Ziel P20 | Status | Gap |
|---|---|---|---|---|---|
| Project Mapping (Worklog → Project) | `Project.jira_component` → JQL (Component ODER Label) → `JiraWorklogCache.projekt_mapping` | Abschnitt 2/7 dokumentiert korrekt | unverändert | **CONFIRMED** | keiner |
| Person Mapping (Worklog → Person) | `Person.jira_account_id`, genutzt in `berechne_ist_fte`-Gruppierung, projektweit/Monat | dokumentiert | zusätzliche Dimension: Gruppierung je Phase | **PARTIAL** | Phasenscope fehlt (P20.7) |
| Worklog Cache | `JiraWorklogCache(jira_account_id, jira_issue_key, datum, stunden, projekt_mapping)`, kein `plan_phase_id` | dokumentiert `ist_hours=null` als bewusst | Resolver-Ebene ergänzen, Cache-Schema unverändert | **CONFIRMED** (Ist-Zustand), **MISSING** (Ziel) | Resolver + zwei neue Tabellen (P20.1/P20.2) |
| Verfügbare Worklog-Felder | Nur 4 Felder extrahiert (`issue_key`, `author_account_id`, `started`, `stunden`); Labels/Component/Summary/Epic/Description/Tempo-Attribute technisch verfügbar, aber nicht abgefragt | nicht dokumentiert | `fields`-Set erweitern, in `JiraIssueCache` cachen | **PARTIAL** | Sync-Erweiterung nötig (P20.1) |
| Phase Mapping | existiert nicht | Abschnitt 5.2 nennt BD-1 offen | `PlanPhase.jira_label` | **MISSING** | neues Feld (P20.1) |
| Resolver | existiert nicht | — | Override → Label-Match → unmapped/ambiguous | **MISSING** | neues Modul (P20.2) |
| Manual Override | existiert nicht (kein Schreibzugriff auf Jira/Tempo im gesamten Code — beide Clients sind read-only, keine `PUT`/`POST` gegen Worklogs) | — | `WorklogPhaseOverride`, Issue-Key-Ebene | **MISSING** | neue Tabelle (P20.1) |
| Unmapped | implizit vorhanden (jeder Worklog ohne Phase-Treffer), aber nicht als eigenes UI-/API-Konzept exponiert | — | explizite Coverage-Kennzahl, nie stilles Verschwinden | **PARTIAL** | Aggregation + UI (P20.3) |
| Ambiguous | existiert nicht (kein Resolver, also auch keine Mehrdeutigkeit messbar) | — | eigener Zustand, keine Doppelzählung | **MISSING** | Resolver-Logik (P20.2) |
| Phase Actual (`ist_hours`) | `effort_consumption()` Stub, immer `None` (verifiziert) | Abschnitt 5.2 korrekt als "BD-1 offen" dokumentiert | echte Werte, `null` nur ohne Mapping | **CONFIRMED** (Stub korrekt), **MISSING** (Ziel) | Implementierung (P20.4) |
| Parent Actual | `planning_calc.leaf_descendants()` existiert bereits (Plan-Aggregation), aber nicht für Ist verdrahtet | — | rekursive Summe über `leaf_descendants` | **PARTIAL** | Wiederverwendung + Verdrahtung (P20.4) |
| Person Actual (je Phase) | nur projektweit (`berechne_ist_fte`) | — | Gruppierung je Phase auf denselben Rohdaten | **MISSING** | neue Aggregation (P20.7) |
| Effort Consumption | Stub, `None` | Abschnitt 5.2 korrekt | `ist_hours / plan_hours × 100` | **CONFIRMED** (Stub), **MISSING** (Ziel) | Implementierung (P20.4) |
| Remaining Hours | existiert nicht | — | `max(plan_hours - ist_hours, 0)` | **MISSING** | neues Feld (P20.4) |
| Coverage | existiert nicht | — | `mapped / total × 100`, dritter Zustand `ambiguous` | **MISSING** | neuer Endpoint (P20.3) |
| Project Rollup | `berechne_ist_fte`, alleinige Quelle für `GET /gap`/`GET /forecast` | dokumentiert | **unverändert**, Phase-Mapping ist additive Aufschlüsselung derselben Zeilen | **CONFIRMED** | keiner (bewusst) |
| Portfolio | `PortfolioHealth.tsx` existiert, aber keine Jira-Ist-Drilldown-Ebene je Phase | — | spätere Erweiterung möglich, kein P20-Paket | **MISSING** (bewusst außerhalb Scope) | keiner in P20 |
| Forecast | `gap_analysis._hochrechnung`, `GET /forecast`, projektweit, Trendfortschreibung | Abschnitt 16.15 Punkt 6 dokumentiert bewusste Trennung | unverändert | **CONFIRMED** | keiner |
| Health | `health_calc._effort_health`, konsumiert `project_gap`, projektweit | dokumentiert | unverändert, keine neue Phase-Ampel | **CONFIRMED** | keiner (bewusst) |

---

## 4. Worklog Data Inventory

Verifiziert im Code (`tempo_client.py:83-97`, `jira_client.py:133-172,89-101`), nicht
angenommen:

| Feld | verfügbar? | Quelle | zuverlässig? | Mapping-tauglich? |
|---|---|---|---|---|
| Worklog-ID | von Jira/Tempo geliefert, aber **nicht extrahiert** (weder `tempo_client` noch `jira_client` lesen `wl["tempoWorklogId"]`/`wl["id"]`) | Tempo-Response/Jira-Response | ja, falls ergänzt | nur für Idempotenz/Dedupe relevant, nicht für Phase-Mapping |
| Issue-Key | **verfügbar, extrahiert** (`issue_key`) | beide Clients | ja | ja — Basis für Override (Abschnitt 14) |
| Issue-ID (numerisch) | **verfügbar, extrahiert** (nur in `search_issues_for_component`, nicht im finalen Worklog-Objekt) | `jira_client.search_issues_for_component` | ja | indirekt (via Key) |
| Summary | **verfügbar in Jira, nicht abgefragt** (`fields`-Parameter fragt nur `"key"` bzw. `"labels"` an, nie beides zusammen mit Worklogs) | Jira Issue-Suche | ja, falls ergänzt | nur UI-Anzeige ("Matched Issues"-Preview), kein Matching-Kriterium |
| Jira-Projekt (Key) | verfügbar über Issue-Key-Präfix, nicht separat gecacht | Issue-Key | ja | indirekt nutzbar, nicht nötig (Projekt-Scope kommt bereits aus `projekt_mapping`) |
| Component(s) | **verfügbar in Jira, nicht gecacht über den Sync-Zeitpunkt hinaus** (`list_components` fragt sie nur für den Picker ab) | Jira Issue-Metadaten | ja, aber max. 1 String im heutigen `Project.jira_component`-Feld (kein Array) | Option A (verworfen, Abschnitt 6) |
| Labels | **verfügbar in Jira (`list_labels` funktioniert bereits), nicht pro Issue im Worklog-Sync gecacht** | Jira Issue-Metadaten | ja — global freitextig, aber pro Issue explizit von Menschen gepflegt | **Option B (empfohlen)** |
| Issue-Type | verfügbar in Jira, nicht abgefragt | Jira Issue-Metadaten | ja | nicht empfohlen als primäres Kriterium (zu grob, keine Phasenfeinheit) |
| Epic-Link/Parent | verfügbar in Jira, nicht abgefragt | Jira Issue-Metadaten | mittel — nicht jedes Team nutzt Epics 1:1 mit Phasen | Option C (Escape-Hatch, nicht Standard) |
| Author Account-ID | **verfügbar, extrahiert** (`author_account_id`) | beide Clients | ja | Basis Personen-Drilldown (Abschnitt 17) |
| Author Display-Name | **verfügbar in Jira-Fallback (echter Klarname), bei Tempo nur Account-ID** (`tempo_client.py:93`: `"author_display_name": wl["author"]["accountId"]` — Tempo liefert keinen Namen) | jeweiliger Client | Jira-Fallback ja, Tempo nein (Klarname kommt über `Person.jira_account_id`-Join) | nicht mapping-relevant, nur Anzeige |
| Worklog-Datum (`started`) | **verfügbar, extrahiert** | beide Clients | ja | **explizit NICHT primär** (Auftrag Abschnitt 6) — höchstens Plausibilitätswarnung |
| Stunden (`stunden`) | **verfügbar, extrahiert** (aus `timeSpentSeconds / 3600`) | beide Clients | ja | Basis jeder Metrik |
| Tempo Account (Kostenstelle) | in Tempo-API vorhanden (`attributes`), **nicht gelesen** — `tempo_client.py:89-97` extrahiert nur vier Felder aus dem Rohobjekt | Tempo-Response | unbekannt (nicht geprüft, ob konsequent gepflegt) | Option E — nicht empfohlen, siehe Abschnitt 6 |
| Worklog Attributes (Custom Fields) | in Tempo-API vorhanden, nicht gelesen | Tempo-Response | unbekannt | nicht empfohlen (Auftrag schließt generische Regelmaschine aus, Abschnitt 8/24 des Auftrags) |
| Description | im Tempo-Response vorhanden, nicht gelesen | Tempo-Response | unbekannt (Freitext) | nicht mapping-tauglich (Freitext, kein strukturiertes Matching) |

**Konsequenz für P20:** Jede Mapping-Option, die auf Labels/Component/Epic basiert, braucht
eine Erweiterung der Sync-Pipeline um zusätzliche Issue-Metadaten-Felder — sie fehlen nicht,
weil sie in Jira nicht existieren, sondern weil sie nie abgefragt/gecached wurden. Der
technische Aufwand dafür ist gering: derselbe `_search_issues`-Aufruf mit einem breiteren
`fields`-Parameter, kein zusätzlicher API-Round-Trip.

---

## 5. Current Project Mapping

Exakter Ablauf (verifiziert):

1. `Project.jira_component` (nullable String, **kein Unique-Constraint** — im Gegensatz zu
   `jira_project_key`, das `unique=True` ist) — ein einzelner String pro Kapa-Projekt.
2. `jira_client.search_issues_for_component(component, since)` baut JQL:
   `(component = "X" OR labels = "X") AND worklogDate >= "since"` — **ein String matcht
   sowohl Component als auch Label**, keine Unterscheidung im Datenmodell zwischen "das ist
   eine Component" und "das ist ein Label". **Wichtig, real geprüft:** Diese JQL enthält
   **keine** `project = "..."`-Klausel — sie ist projektübergreifend über die gesamte
   Jira-Instanz formuliert. Das ist unkritisch, solange Component/Label-Strings faktisch
   eindeutig sind (Components sind technisch an ein Jira-Projekt gebunden), wird aber
   **potenziell riskanter bei generischen Label-Strings** (siehe Risiko-Anmerkung in
   Abschnitt 34).
3. Treffer-Issues (nur `key`+`id`) werden an Tempo (falls konfiguriert) oder den nativen
   Jira-Worklog-Endpoint übergeben.
4. Rückgabe wird in `JiraWorklogCache` upserted mit `projekt_mapping = str(project.id)`.

**Geprüfte Randfälle:**

| Randfall | Befund |
|---|---|
| Mehrere Projekte mit gleicher Component/Label | **Nicht verhindert** — kein Unique-Constraint auf `Project.jira_component`. Zwei Kapa-Projekte könnten denselben String eintragen → derselbe Worklog würde in beiden Projekten separat gesynct. Bestehende Lücke, nicht P20-Scope, aber für P20 relevant (Abschnitt 34). |
| Mehrere Components je Projekt | Nicht unterstützt — einzelner String, kein Array. |
| Fehlende Component | `sync_project` wird für Projekte ohne `jira_component` gar nicht aufgerufen; `berechne_ist_fte` liefert `{}`. |
| Worklog auf Epic/Task/Subtask | JQL filtert nicht nach Issue-Type — alle Typen matchen gleich. |
| Jira-Projekt vs. Component | Getrennte Konzepte: `jira_project_key` (Katalog-Herkunft, 1:1) vs. `jira_component` (Such-Scope) — ein Kapa-Projekt kann ersteres gesetzt haben, ohne dass Sync läuft. |
| Labels | Identisch zu Components behandelt (kein getrenntes Feld). |
| Tempo Accounts | Nicht ausgelesen/genutzt (Abschnitt 4). |

---

## 6. Phase Mapping Options

| Option | Aufwand (Backend) | Jira-Prozessaufwand | Determinismus | Migrationssicherheit | Parallelphasenfähig | Useraufwand | Bewertung |
|---|---|---|---|---|---|---|---|
| **A — Component pro PlanPhase** | Mittel (JQL-Erweiterung) | **Hoch** — Components sind meist projektweit von Jira-Admins verwaltet, nicht für granulare Phasen gedacht; Liste wüchse mit jeder Phase | Hoch | Neutral | Ja | Hoch (Admin-Rechte pro neuem Wert) | Technisch sauber, organisatorisch schwer skalierbar |
| **B — Label pro PlanPhase** | Mittel (Sync-Erweiterung um Label-Fetch) | **Niedrig** — jeder Nutzer kann ein Label setzen, kein Admin-Recht nötig | Hoch, sofern 1 Label pro Issue eindeutig einer Phase zugeordnet ist | Sehr gut — additiv, Alt-Tickets bleiben unmapped bis gelabelt | Ja (Datum spielt keine Rolle) | Niedrig | **Empfohlen als Kernmechanismus** |
| **C — Epic/Issue/JQL-Mapping** | Hoch (JQL-Editor, Freitext-Validierung) | Mittel | Hoch bei sauberer Epic-Struktur, aber JQL-Freitext fehleranfällig | Neutral | Ja | Mittel–Hoch | Als Ausnahme-Escape-Hatch denkbar, kein Standard |
| **D — konfigurierbare Regel (Component+Label+Type+Epic kombinierbar)** | Sehr hoch — generisches Regel-Datenmodell, genau die vom Auftrag ausgeschlossene Rule-Engine | Niedrig–mittel | Hoch, aber UX-Komplexität hoch | Neutral | Ja | Hoch (Regel-Verständnis) | **Verworfen** — Overengineering |
| **E — Tempo Account** | Niedrig (Feld existiert in der API), aber ungeprüfte Datenqualität | Unklar/Hoch (Kostenstellen-Pflege ist ein anderer Prozess als Phasenzuordnung) | Unklar (nicht verifizierbar ohne echte Tempo-Instanz-Daten) | Neutral | Ja | Unklar | **Nicht empfohlen** als Kernmechanismus — Datenqualität nicht bestätigbar, fachlich zweckentfremdet (Kostenstelle ≠ Planphase) |
| **F — Hybrid (B + manueller Override)** | Summe aus B + Override-Tabelle, kein zusätzliches Regelmodell | Niedrig (nur Label-Pflege, Override nur für Ausnahmen) | Hoch, mit definierter Priorität (Abschnitt 8) | Sehr gut | Ja | Niedrig | **Empfohlen** |

---

## 7. Recommended Mapping Architecture

**Empfehlung: Option F — Option B (Label pro Leaf-PlanPhase) als deterministischer
Automatik-Mechanismus + manueller Override je Issue-Key als Korrekturmechanismus.**
Kein Component-pro-Phase (zu Jira-Admin-lastig), kein voller JQL/Epic-Editor (zu
fehleranfällig), kein Tempo-Account (Datenqualität nicht bestätigt, fachlich
zweckentfremdet), keine generische Regelmaschine (vom Auftrag explizit ausgeschlossen).

**Warum das die geforderten Kriterien am besten erfüllt:**

- **Deterministisch:** Ein Issue hat eine feste Menge an Labels zu einem Zeitpunkt; Matching
  ist eine reine Mengen-Operation (Issue-Labels ∩ Phase-Labels desselben Projekts), keine
  Heuristik, kein Datum.
- **Erklärbar:** "Dieses Ticket trägt das Label `phase:configuration`, deshalb zählt sein
  Worklog zur Phase 'Konfiguration'" ist ohne Jira-Kenntnisse verständlich.
- **Wartbar:** Ein Label ändern/entfernen ist eine Ein-Klick-Aktion in Jira, kein
  Schema-Change, kein Ticket an die Jira-Administration.
- **Parallelphasenfähig:** Matching hängt nie von `worklog_date` ab, nur von Issue-Labels —
  unterstützt beliebig viele gleichzeitig aktive Phasen direkt.
- **Manuell korrigierbar:** `WorklogPhaseOverride` fängt jede Ausnahme ohne
  Jira/Tempo-Schreibzugriff auf.
- **Migrationssicher:** Additiv, nullable, kein Alt-Projekt bricht.

**Bewusst nicht gewählt:** Ein zusätzlicher automatischer Component-Fallback wurde geprüft
und verworfen — zwei parallele automatische Matching-Wege ohne fachlichen Zusatznutzen
widersprechen dem Ziel "genau eine Prioritätskette" (Abschnitt 8).

---

## 8. Resolver Priority

**BD-1A (siehe Abschnitt 28): genau eine Kette, keine konkurrierenden Mechanismen:**

```
1. Manual Override   (WorklogPhaseOverride, Issue-Key-Ebene)   → höchste Priorität
2. Label-Match        (Issue-Labels ∩ PlanPhase.jira_label, Scope = dieses Projekt)
3. kein Treffer        → UNMAPPED   (Projekt-Ist bleibt vollständig, Abschnitt 12)
   mehrere Treffer     → AMBIGUOUS  (Abschnitt 13)
```

**Resolver-Pseudocode (fachlich, keine Implementierung):**

```
for worklog in project_worklogs:                      # bereits projekt-gescoped (Abschnitt 20)
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
Issue-Labels (Automatik). Kein Worklog kann durch diese Kette gleichzeitig zwei Phasen
zugerechnet werden (Abschnitt 10 des Auftrags: keine stille Mehrfachzuordnung).

---

## 9. Mapping Configuration UX

Position: PlanPhase-Workspace → Übersicht-Tab, neue kompakte Zeile ("Ist-Daten"), analog
zum bestehenden Component/Label-Picker-Muster im projektweiten Einstellungen-Tab
(`GET /jira/projects/{key}/labels` existiert bereits und liefert genau die Werte für ein
Dropdown):

```
IST-DATEN
Jira-Label   [phase:configuration ▾]     Matched Issues: 24   [Details ▾]
```

**Dropdown statt Freitext** — befüllt aus den Labels, die im Component-Scope des Projekts
tatsächlich vorkommen (Wiederverwendung des bereits vorhandenen `list_labels`-Aufrufs, kein
neuer Jira-API-Endpoint nötig). Keine JSON-/Regex-/JQL-Eingabe als Standardpfad. Nur auf
Leaf-Phasen sichtbar/editierbar — analog zum bestehenden `plan_fte`-Feld, das beim
Parent-Übergang serverseitig auf `NULL` gesetzt wird (gleicher Lifecycle, kein neuer
Code-Pfad, Abschnitt 15).

---

## 10. Mapping Preview

**Design-Entscheidung: Preview liest ausschließlich den bereits vorhandenen lokalen Cache
(`JiraIssueCache`/`JiraWorklogCache`), keine Live-Jira-Abfrage.** Begründung: Der
projektweite Sync (`POST /jira/sync`) hat bereits alle relevanten Issues inkl. Labels
geladen (nach der in Abschnitt 4/22 beschriebenen Sync-Erweiterung). Eine zweite,
Ad-hoc-Jira-Abfrage bei jedem Tastendruck im Label-Dropdown wäre unnötige API-Last und ein
zweiter Wahrheits-Pfad neben dem Sync. Stattdessen:

```
GET /plan-phases/{id}/jira-matches?label=phase:configuration
→ rein lesend gegen JiraIssueCache (WHERE project_id = ... AND label IN labels)
  JOIN JiraWorklogCache (SUM stunden je Issue)

Antwort:
  matched_issues: 24
  matched_worklogs: 128
  total_hours: 310.0
  sample_issue_keys: ["WMX-123", "WMX-147", "WMX-150"]
  as_of: <last_synced_at aus JiraIssueCache>   # Transparenz: Stand des letzten Syncs
```

**Wichtig, Transparenz-Prinzip (Auftrag: keine Fake-Daten):** Die Preview zeigt explizit
*"Stand: letzter Sync am DD.MM. HH:MM"* — sie ist kein Live-Ergebnis, sondern der Stand zum
Zeitpunkt des letzten `POST /jira/sync`. Bei Bedarf kann der User vor dem Konfigurieren
zuerst synchronisieren (Button bereits vorhanden, `ProjectJiraTab.tsx`). Bestehende APIs
ermöglichen das effizient: keine neue Jira-Abfrage, nur ein zusätzlicher indizierter
DB-Query auf bereits vorhandene/neu eingeführte Tabellen.

---

## 11. Conflict Detection

Beim Speichern von `PlanPhase.jira_label` (`PUT /plan-phases/{id}`):

```
IF exists LeafPlanPhase p2
   WHERE p2.project_id == this.project_id
     AND p2.jira_label == new_value
     AND p2.id != this.id
THEN reject (409) mit Meldung:
   "Das Label 'phase:configuration' ist bereits Phase 'Konfiguration Alt' (#42)
    zugeordnet. Ein Label darf pro Projekt nur einer Leaf-Phase zugeordnet sein."
```

**Bewusst harter Block, keine bloße Warnung.** Begründung: Zwei Leaf-Phasen desselben
Projekts mit identischem `jira_label` können strukturell **niemals** ein eindeutiges
Ergebnis liefern — jedes matchende Issue würde für **beide** Phasen zutreffen und wäre damit
laut Resolver (Abschnitt 8) automatisch `AMBIGUOUS`. Das ist kein seltener Datenqualitäts-
Grenzfall (wie ein Issue mit zwei unterschiedlichen Phase-Labels, Abschnitt 13), sondern
eine bei der Konfiguration selbst vermeidbare Fehlkonfiguration — anders als bei der
Issue-Ebene gibt es hier keinen legitimen Anwendungsfall für die Doppelbelegung. Ein Block
mit klarer Fehlermeldung (inkl. Verweis auf die kollidierende Phase) ist nutzerfreundlicher
als eine Warnung, die ignoriert werden kann und danach durchgehend Ambiguous-Rauschen
erzeugt. Scope der Prüfung: **nur Leaf-Phasen desselben Projekts** — Parent-Phasen können
laut Lifecycle (Abschnitt 15) ohnehin kein `jira_label` tragen, projektübergreifende
Kollisionen sind kein Thema, da der Resolver nie projektübergreifend matcht (Abschnitt 20).

---

## 12. Unmapped Worklogs

Kein neues Konzept nötig, additive Auswertung auf vorhandenem `JiraWorklogCache`. Ein
Worklog ohne Override und ohne Label-Treffer bleibt Teil der Projekt-Ist-Summe
(`jira_sync.berechne_ist_fte`, unverändert), zählt aber in keiner Phase mit. UI zeigt
explizit `Nicht zugeordnet: X h` — niemals stilles Verschwinden. Datenmodell: keine neue
Tabelle, "unmapped" ist der Resolver-Zustand "keine Override-Zeile, kein Label-Treffer" —
wird zur Anzeigezeit berechnet, nicht persistiert.

---

## 13. Ambiguous Worklogs

Tritt auf, wenn ein Issue Labels trägt, die zu **mehr als einer** `PlanPhase` desselben
Projekts passen (z.B. Issue hat Labels `phase:schnittstellen` und `phase:testing`, beide
sind als `jira_label` unterschiedlicher, gültig konfigurierter Phasen eingetragen — die
Konfliktprüfung aus Abschnitt 11 verhindert nur *identische* Label-Werte auf zwei Phasen,
nicht dass ein einzelnes Issue mehrere unterschiedliche Phase-Labels gleichzeitig trägt,
was ein legitimer, nicht vermeidbarer Grenzfall bleibt). Der Worklog wird **einmal** in die
Kategorie `AMBIGUOUS` gezählt, **nicht** doppelt in beide Phasen. UI zeigt
`X h nicht eindeutig zugeordnet (Issue ABC-123: Labels passen zu "Schnittstellen" und
"Testing")` mit direktem Link zu einem Override, um die Mehrdeutigkeit sofort aufzulösen.

Ambiguous-Worklogs zählen weder zu einer Phase noch zu "unmapped" — eigene dritte Kategorie
in der Coverage-Anzeige (Abschnitt 19), damit die Coverage-Kennzahl nicht fälschlich 100%
suggeriert, obwohl eine Zuordnung tatsächlich unklar ist.

---

## 14. Manual Overrides

Overrides sind erlaubt und nötig, aber bewusst **grobkörnig auf Issue-Key-Ebene**, nicht auf
einzelne Worklog-Zeilen (Datum+Person) — ein Ticket gehört im Regelfall fachlich zu genau
einer Phase über seine gesamte Laufzeit; eine zeilenscharfe Override-UI wäre unnötige
Bedienlast ohne fachlichen Zusatznutzen für den Normalfall. Die seltene Ausnahme ("ABC-123
wechselte fachlich die Phase") wird durch Bearbeiten/Löschen des Overrides gelöst.

**Vorhandene Infrastruktur geprüft, bevor ein neues Modell vorgeschlagen wird:**
`EntityRelation` (generische `source_entity_type/id → target_entity_type/id`-Verknüpfung,
`models.py:393-415`) wurde geprüft. **Nicht passend:** `EntityRelation` verknüpft zwei
Entitäten **innerhalb** dieser Datenbank (beide Seiten haben eine lokale `id`); ein
Jira-Issue-Key ist ein externer String ohne lokale Entität. Eine künstliche "JiraIssue"-
Entität nur für diesen Zweck anzulegen wäre Overengineering gegenüber einer simplen
Zwei-Spalten-Tabelle. **Entscheidung: neue, schlanke Tabelle `WorklogPhaseOverride`**
(Abschnitt 22), kein Missbrauch von `EntityRelation`.

Override verändert **niemals** Jira/Tempo-Originaldaten — nur lokale Zuordnungsinformation,
exakt wie `projekt_mapping` in `JiraWorklogCache` heute bereits verfährt (kein
Schreibzugriff auf Jira/Tempo existiert im gesamten Code, verifiziert: beide Clients sind
read-only).

---

## 15. Leaf/Parent Actual Semantics

`PlanPhase.jira_label` ist **nur auf Leaf-Phasen sinnvoll** — analog zu `plan_fte`, das bei
Parent-Phasen auf `NULL` gesetzt wird, sobald die Phase Kinder erhält. Gleiche Regel für
`jira_label`: **wird eine Leaf-Phase zum Parent (erstes Kind), wird ihr `jira_label`
serverseitig auf `NULL` gesetzt** (identischer Lifecycle-Mechanismus wie `plan_fte`, kein
neuer Code-Pfad). Ist-Stunden einer Parent-Phase sind **immer** die rekursive Summe ihrer
Leaf-Nachfahren:

```
ist_hours(parent) = SUM( ist_hours(leaf) für leaf in planning_calc.leaf_descendants(parent) )
```

`planning_calc.leaf_descendants()` existiert bereits (Wiederverwendung für die
Kapazitätsaggregation) — **keine neue Traversal-Logik**.

**Explizit erlaubte Ausnahme:** "Projektmanagement"/"Steuerung"/"allgemeine Workshops" sind
selbst **Leaf-Phasen** wie jede andere operative Phase — kein Sonderfall im Modell, sie
bekommen einfach ein eigenes `jira_label` (z.B. `phase:pm`). Kein Worklog landet direkt auf
einem aggregierenden Parent, weil Parents per Definition kein `jira_label` (mehr) tragen
können — der Resolver kann sie strukturell gar nicht treffen. Kein Worklog wird physisch auf
Parent und Leaf gleichzeitig gespeichert (eine `JiraWorklogCache`-Zeile, der Resolver
bestimmt bei Bedarf nur die zugehörige Leaf-Phase; Parent-Werte werden immer live
aggregiert, nie persistiert).

---

## 16. Phase Actual Metrics

`phase_metrics_calc.effort_consumption()` wird implementiert (heute Stub, Abschnitt 3):

```
ist_hours(leaf)   = SUM(stunden) über alle JiraWorklogCache-Zeilen, deren Issue laut
                    Resolver (Abschnitt 8) genau dieser Phase zugeordnet ist
ist_hours(parent) = SUM(ist_hours(leaf)) über leaf_descendants (Abschnitt 15)

plan_hours         = plan_fte × Werktage × 8h   (UNVERÄNDERT, kein Tempo-Einfluss)
effort_consumption_pct = ist_hours / plan_hours × 100
remaining_plan_hours   = max(plan_hours - ist_hours, 0)
overrun_hours           = ist_hours - plan_hours   (nur wenn ist_hours > plan_hours)
```

`ist_hours`/`effort_consumption_pct` liefern damit erstmals reale Werte für Phasen mit
Mapping; für Phasen **ohne** `jira_label` **und ohne** zugehörige gemappte Worklogs bleibt
es weiterhin explizit `null` mit dem UI-Text "Ist-Aufwand noch nicht eindeutig zugeordnet" —
**nicht** `0.0`, da `0.0` fälschlich "sicher keine Arbeit" suggerieren würde. Keine
Forecast-Heuristik aus `remaining_plan_hours`/`overrun_hours` abgeleitet — reine
Subtraktion, kein Burn-Rate-Modell.

---

## 17. Person Actuals

`Person.jira_account_id` existiert bereits und ist laut Modellkommentar die alleinige Quelle
für die Jira-/Tempo-Worklog-Zuordnung — für den Personen-Drilldown je Phase reicht eine
zusätzliche Gruppierung der ohnehin schon Resolver-zugeordneten `JiraWorklogCache`-Zeilen
nach `jira_account_id` → `Person`, exakt wie `jira_sync.berechne_ist_fte` es heute bereits
projektweit nach Monat gruppiert. **Kein neues Modell, keine neue Capacity-Quelle** — reine
zusätzliche Aggregationsdimension auf denselben Rohdaten.

```
ist_hours_je_person(phase) = SUM(stunden) gruppiert nach jira_account_id → Person.display_name,
                              über dieselben gemappten Worklog-Zeilen wie Abschnitt 16
```

Beispiel (Auftrag Abschnitt 23): Dominik 32h, Max 20h, Anna 8h → Summe 60h, identisch zu
`ist_hours(phase)`.

---

## 18. Planned vs Actual Resources

Direkt ableitbar, ohne neue Tabelle: `planned persons` kommt aus `ResourceAssignment` (Join
über `ResourceDemand.plan_phase_id`), `actual persons` aus Abschnitt 17. Eine Person
erscheint als "ungeplant, aber tatsächlich aktiv", wenn sie in der Ist-Gruppierung auftaucht,
aber in keinem `ResourceAssignment` dieser Phase; umgekehrt "eingeplant, bisher kein Ist",
wenn sie ein Assignment hat, aber in der Ist-Gruppierung nicht vorkommt. **Nur
Datenverfügbarkeit wird hergestellt** — keine Health-Regel, kein automatisches Werturteil,
keine automatische Assignment-Änderung.

```
unplanned_actual_hours(phase) = SUM(ist_hours_je_person) für Personen ohne
                                 ResourceAssignment auf dieser Phase
```

Nur implementiert, wenn eindeutig aus bestehenden Daten berechenbar — das ist hier der Fall,
da beide Seiten (`ResourceAssignment.person_id`, `JiraWorklogCache.jira_account_id` →
`Person`) bereits vorhanden sind.

---

## 19. Mapping Coverage

Zentrale Vertrauens-Kennzahl:

```
project_ist_total   = SUM(alle JiraWorklogCache-Zeilen dieses Projekts)   [unverändert,
                       berechne_ist_fte-Quelle]
phase_mapped_total  = SUM(ist_hours über alle Leaf-Phasen des Projekts, Abschnitt 16)
ambiguous_total     = SUM(Worklogs im AMBIGUOUS-Zustand, Abschnitt 13)
unmapped_total       = project_ist_total - phase_mapped_total - ambiguous_total
coverage_pct         = phase_mapped_total / project_ist_total × 100
                        (bei project_ist_total == 0: undefiniert/null, nicht 0 oder 100)
```

UI (Auftrag Abschnitt 13):

```
IST-ZUORDNUNG
Gesamt                          120 h
Zu PlanPhasen zugeordnet         95 h
Nicht zugeordnet                 25 h
Coverage                       79,2 %
                          [25 h prüfen]
```

Kein Plan-vs-Ist-Urteil, wenn Coverage sehr niedrig ist — die Kennzahl macht das sichtbar,
bewertet es aber nicht automatisch.

---

## 20. Project Rollup

Projekt-Ist ändert sich durch P20 **nicht** — `jira_sync.berechne_ist_fte` bleibt exakt wie
heute die alleinige Quelle für `Project`-Ebene und `GET /gap`/`GET /forecast`. Phase-Mapping
ist eine **zusätzliche, optionale Aufschlüsselung** derselben `JiraWorklogCache`-Zeilen, kein
Ersatz. Strukturell ausgeschlossen, dass unvollständiges Phasen-Mapping das Projekt-Ist
sinken lässt:

```
Project Actual Hours = SUM(alle JiraWorklogCache-Zeilen, projekt_mapping = project.id)
                      [unverändert — niemals nur die gemappten Stunden]
                      = mapped phase actuals + unmapped + ambiguous
```

Projekt-Ist wird **nie** aus den Phasen zurückberechnet, solange Coverage < 100% — die
Projekt-Ebene bleibt die primäre Quelle, die Phase-Ebene ist abgeleitet, nicht umgekehrt.
`PlanPhase`-Resolver scannt niemals global — nur Worklogs, die bereits über
`Project.jira_component` in `JiraWorklogCache` gelandet sind (Abschnitt 5), werden dem
Phase-Resolver überhaupt vorgelegt.

---

## 21. Portfolio Rollup

Keine neue Ist-Engine — Tempo/Jira bleibt einzige Quelle. Ein späterer Portfolio-Drilldown
(Projekt → Phase → Personen) kann die in Abschnitt 16/17/19 definierten Bausteine direkt
wiederverwenden, ist aber **nicht Teil der P20-Pakete** — explizit als mögliche Folgearbeit
vermerkt, kein eigenes Paket.

---

## 22. Forecast Assessment

Bestehende Forecast-Engine (`gap_analysis._hochrechnung`, `GET /forecast`) bleibt
**unverändert** — sie arbeitet auf Projekt-Monats-Ebene mit Trendfortschreibung
(Durchschnitt der letzten Ist-Monate). P20 ersetzt sie nicht. Phase-Level-Ist liefert
lediglich `remaining_plan_hours`/`overrun_hours` (Abschnitt 16, einfache Subtraktion, keine
Hochrechnung). Kein Burn-Rate-Forecast, kein Estimate-to-Complete-Feld auf Phasenebene in
P20 — bewusst zurückgestellt, bis belastbares Ist vorliegt. Mögliche spätere Erweiterung
(z.B. "Phase endet voraussichtlich am X basierend auf Burn-Rate") dokumentiert, aber nicht
Teil dieses Pakets — nur implementieren, wenn fachlich eindeutig gefordert.

---

## 23. Health Assessment

`health_calc._effort_health` (projektweit, konsumiert `gap_analysis.project_gap`) bleibt
**unverändert** — bereits laut CONCEPT.md bewusst von der `PlanPhase`-Architektur getrennt
(andere fachliche Frage: "wird so gearbeitet wie geplant" vs. "wie viel Kapazität ist
verplant"). P20 fügt **keine neue Health-Dimension/Ampel** hinzu — liefert nur die
Rohmetriken (`time_progress_pct`, `plan_hours`, `ist_hours`, `effort_consumption_pct`,
`remaining_plan_hours`, `mapping_coverage_pct`), aus denen eine spätere, eigenständig zu
entscheidende Phasen-Health-Logik entstehen könnte (BD-3, bereits offen, unverändert offen,
außerhalb P20-Scope solange BD-3 nicht separat geschlossen wird).

---

## 24. Data Model

Geprüft vor Neuvorschlag: `PlanPhase`, `Project`, `JiraWorklogCache`, `EntityRelation`,
`PlanHistory`, `ProjectMembership`, `ResourceAssignment`, `Person.jira_account_id`,
`Project.jira_component`/`jira_project_key`. Ergebnis: zwei neue, schlanke Tabellen + ein
neues Feld sind nötig, keine generische Regelmaschine.

**Zusätzliche Prüfung `PlanHistory` als Audit-Infrastruktur für Overrides** (Auftrag
Abschnitt 16: "Bestehende Audit-Infrastruktur prüfen. Keine unnötige zweite Audit Engine").
`PlanHistory` (`models.py:265-301`) ist ein generisches Änderungsprotokoll
(`project_id`, `subproject_id`, `plan_phase_id`, `bereich`, `monat`, `feld`, `alter_wert`,
`neuer_wert`, `geaendert_am`, `kommentar_id`, `batch_id`), geschrieben über `_log_change()`
in `routers/projects.py`. **Wichtiger Befund: `PlanHistory` trackt kein "geändert von"
(kein `person_id`/User-Feld) — real geprüft, im gesamten Backend existiert kein
Auth-/Session-/Current-User-Mechanismus** (keine Treffer für
`current_user`/`get_current_user`/Auth-Dependency im gesamten `backend/app`). "Wer" wird im
gesamten Produkt durchgängig über einen manuell gewählten Personen-Picker abgebildet (z.B.
"Owner", `kommentar_id`-Autor), nie automatisch aus einer Session. `WorklogPhaseOverride`
folgt demselben, bereits etablierten Muster: `created_by_person_id` ist ein manuell
gewählter, nullable Verweis auf `Person`, keine neue Auth-Anforderung. **`PlanHistory`
selbst wird nicht wiederverwendet** — es ist strukturell an `bereich`/`monat`/`feld`
(Planungswerte) gebunden und würde für "vorheriger Mapping-Status → neue PlanPhase" ein
unpassendes Datenmodell erzwingen (kein Issue-Key-Feld, kein natürlicher `feld`-Wert für
"Mapping"). `WorklogPhaseOverride` trägt Audit-Felder direkt (`created_by_person_id`,
`created_at`), analog zu `Comment`/`Task` — **keine zweite generische Audit-Engine**, nur
konsistente Wiederverwendung des bestehenden "Wer/Wann direkt am Datensatz"-Musters.

**1. `PlanPhase.jira_label`** (additiv, nullable `String(200)`) — analog zum bestehenden
Muster `Project.jira_component`. Nur auf Leaf-Phasen gültig (Abschnitt 15), serverseitig auf
`NULL` gesetzt beim Parent-Übergang, gleicher Lifecycle wie `plan_fte`.

**2. `JiraIssueCache`** (neu) — hält pro Issue die für das Mapping nötigen Metadaten, die der
Sync heute verwirft (Abschnitt 4):

```
jira_issue_key    String(50), PRIMARY KEY
project_id         FK → projects.id  (Scope, aus dem Component-Match beim Sync bekannt)
labels             Text (kommagetrennt/JSON-Array — einfache Liste, kein Regelwerk)
component          String(200), nullable
summary            String(500), nullable  (nur UI-Anzeige "Matched Issues", Abschnitt 10)
last_synced_at      String(40)
```

Wird bei jedem `jira_sync.sync_project()`-Lauf für alle Treffer-Issues aktualisiert
(zusätzlicher `fields`-Parameter `"labels,components,summary"` an den bereits vorhandenen
`_search_issues`-Call, keine neue API-Anfrage nötig).

**3. `WorklogPhaseOverride`** (neu) — manuelle Korrektur, issue-scoped:

```
id                    PRIMARY KEY
project_id            FK → projects.id
jira_issue_key        String(50), UNIQUE  (ein Override pro Issue, nicht pro Worklog-Zeile)
plan_phase_id         FK → plan_phases.id
previous_status        String(20), nullable  ("unmapped" | "ambiguous" | "<phase_id>" — Snapshot
                        des Zustands vor dem Override, für Audit-Nachvollziehbarkeit, Auftrag
                        Abschnitt 16: "vorheriger Mapping-Status")
note                    String(500), nullable
created_by_person_id   FK → persons.id, nullable
created_at             String(40)
```

**Kein Constraint-Fix für Abschnitt 5 (mehrere Projekte, gleiche Component)** in P20 —
dokumentiert als Rand-Risiko (Abschnitt 34), außerhalb des P20-Auftrags, aber
`JiraIssueCache.project_id` reduziert das Risiko für die neue Phase-Ebene bereits
strukturell (ein Issue kann nur im Scope des Projekts gematcht werden, für das es beim Sync
gefunden wurde).

---

## 25. API Changes

Alle additiv, keine Breaking Changes:

- `PlanPhaseOut`/`PlanPhaseDetail`: neues Feld `jira_label: str | None`.
- `PUT /plan-phases/{id}`: akzeptiert `jira_label` wie jedes andere editierbare Feld
  (bestehender Sofort-Speichern-Pfad). Backend setzt es serverseitig auf `NULL` zurück, falls
  die Phase bereits Kinder hat (Guard analog zum `plan_fte`-Parent-Guard); prüft die
  Konfliktregel aus Abschnitt 11 vor dem Speichern (409 bei Kollision).
- `GET /plan-phases/{id}/jira-matches?label=...` (neu) — Mapping-Preview (Abschnitt 10), rein
  lesend gegen `JiraIssueCache`/`JiraWorklogCache`.
- `PhaseMetricsOut`: `ist_hours`/`effort_consumption_pct` liefern jetzt echte Werte statt
  immer `None`; zusätzlich `remaining_plan_hours: float | None`, `overrun_hours: float |
  None`, `person_actuals: list[PersonActualOut]`, `unplanned_actual_hours: float | None`
  (alle neu, Abschnitt 16-18).
- `GET /projects/{id}/actuals-coverage` (neu) — liefert die Coverage-Kennzahl (Abschnitt 19):
  `project_ist_total`, `phase_mapped_total`, `ambiguous_total`, `unmapped_total`,
  `coverage_pct`.
- `POST/DELETE /plan-phases/{id}/worklog-overrides` (neu) — CRUD für
  `WorklogPhaseOverride`, gescoped auf die Phase (Issue-Key im Body).
- `GET /jira/status`, `POST /jira/sync`, `GET /gap`, `GET /forecast`: **unverändert**.

---

## 26. Frontend Changes

- `ProjectJiraTab.tsx`: neue Coverage-Zeile (Abschnitt 19/25), keine Struktur-Änderung.
- `PlanPhaseWorkspace.tsx` → Übersicht-Tab: neue "Ist-Daten"-Zeile mit Label-Picker + Matched
  Issues + Konflikt-Fehlermeldung (Abschnitt 9/10/11).
- `PlanPhaseWorkspace.tsx` → Kapazität-Tab (`PlanPhaseCapacityTab.tsx`): neue Karte
  "Steuerung" additiv unterhalb der bestehenden Plan-FTE/Besetzung-Karte:

```
STEUERUNG
Planstunden                80 h
Ist-Aufwand                60 h        [Details ▾]
Aufwandsverbrauch          75 %
Zeitfortschritt             50 %
Verbleibender Planaufwand  20 h

Ist-Zuordnung              95 %  (4 h nicht zugeordnet)
```

  "Details ▾" klappt den Personen-Drilldown (Abschnitt 17) und ggf. eine Hinweiszeile
  "15 h durch nicht eingeplante Ressourcen" (Abschnitt 18) auf. Bei fehlendem Mapping:
  "Ist-Aufwand: noch nicht zugeordnet [Jira-Zuordnung konfigurieren]" statt einer Zahl.
  **Keine Ampel** (BD-3 nicht Teil von P20).
- Neue kompakte, wiederverwendbare Komponente `WorklogMappingBadge`
  (unmapped/ambiguous-Hinweis mit "[prüfen]"-Link zu einem kleinen Override-Dialog) —
  zwischen Projekt-Jira-Tab und Phase-Kapazität-Tab geteilt.
- Kein neuer Tab, kein neues `ResourceDemandGrid`, kein neues Subproject-UI, keine neue
  Gantt-Ansicht.

---

## 27. Migration / Compatibility

Bestehende Projekte ohne `PlanPhase.jira_label`-Pflege funktionieren identisch zu heute
weiter — `ist_hours`/`effort_consumption_pct` bleiben `None`/"nicht zugeordnet", bis ein
Projektleiter aktiv ein Label einträgt. Kein Migrations-Skript rät automatisch ein Mapping
(keine automatisierte, potenziell falsche Zuordnung für Altprojekte). `JiraIssueCache`
startet leer und füllt sich beim nächsten regulären `POST /jira/sync` — kein Backfill-Zwang,
kein Blocker für B-8. Bestehende Projekte ohne Jira-Anbindung (`jira_component` nicht
gesetzt) sind komplett unberührt (Resolver läuft nur auf bereits projektgescopten Worklogs).

---

## 28. Business Decisions

BD-1 wird in diesem Durchgang **geschlossen** und exakt in die vom Auftrag verlangten
Teilfragen zerlegt:

| ID | Frage | Entscheidung |
|---|---|---|
| **BD-1A** | Welche Jira-/Tempo-Metadaten definieren eine Phase? | **CLOSED** — Issue-Labels, gematcht gegen `PlanPhase.jira_label` (ein Label pro Leaf-Phase, ein Wert pro Feld). Kein Component-, Epic-, Issue-Type- oder Tempo-Account-basiertes Matching als zusätzlicher Automatik-Kanal (Abschnitt 6/7). |
| **BD-1B** | Sind manuelle Worklog-Overrides erlaubt? | **CLOSED** — ja, auf Issue-Key-Ebene (nicht Worklog-Zeile), höchste Priorität in der Resolver-Kette, neue Tabelle `WorklogPhaseOverride`, Original-Jira/Tempo-Daten bleiben unverändert (Abschnitt 8/14). |
| **BD-1C** | Wie werden ambiguous Worklogs behandelt? | **CLOSED** — eigener `AMBIGUOUS`-Zustand, keine Doppelzählung, keine automatische Auflösung; nur ein Override löst auf (Abschnitt 13). |
| **BD-1D** | Wie werden unmapped Worklogs im UI behandelt? | **CLOSED** — nie stillschweigend auf `0h`, immer explizit als "Nicht zugeordnet: Xh" mit direktem Link zur Prüfung/Zuordnung; Projekt-Ist bleibt davon unberührt (Abschnitt 12/19). |

**Zusätzlich geschlossen, da für die Umsetzbarkeit notwendig, aber nicht in A–D benannt:**

| ID | Frage | Entscheidung |
|---|---|---|
| BD-1E | Verhalten bei Parent/Leaf-Übergang? | **CLOSED** — `jira_label` folgt demselben Lifecycle wie `plan_fte` (`NULL` bei Parent-Übergang); Ist-Aggregation rein rekursiv über `leaf_descendants` (Abschnitt 15). |
| BD-1F | Ändert sich die Projekt-Ist-Berechnung? | **CLOSED** — nein, `berechne_ist_fte`/`GET /gap`/`GET /forecast` bleiben unverändert; Phase-Mapping ist rein additive Aufschlüsselung (Abschnitt 20/22). |
| BD-1G | Konflikt bei Label-Doppelbelegung zweier Leaf-Phasen? | **CLOSED** — harter Block (409) beim Speichern, keine Warnung (Abschnitt 11). |

**Verbleibende, nicht neu geöffnete Business Decisions** (aus CONCEPT.md, von P20
unberührt): BD-3 (Health-Schwellen), BD-4 (Feiertags-Handling Planstunden), BD-5
(Sub-Range-Assignments), BD-6 (`allocation_gap`-Vorzeichen) — keiner davon wird durch P20
tangiert oder muss vor der P20-Umsetzung geklärt werden.

**Eine organisatorische, keine technische Restfrage:** Die Label-Konvention
(`phase:<name>`) muss von den Jira-nutzenden Teams tatsächlich gepflegt werden, sonst bleibt
Coverage niedrig. Kein Blocker für die Implementierung (P20.1–P20.4 sind unabhängig davon
baubar und liefern von Tag 1 an korrekte "nicht zugeordnet"-Werte statt falscher Daten), aber
der Product Owner sollte den Rollout (Label-Schulung/-Konvention) bewusst einplanen.

---

## 29. CONCEPT.md Changes

Nach Umsetzung von P20.1–P20.8 sind folgende Bereiche zu aktualisieren (nicht in diesem
Durchgang, da "NOCH NICHT IMPLEMENTIEREN" — hier nur die Änderungsliste für P20.8):

- **Kernprinzipien:** Mapping-Strategie (Label + Override), Resolver-Priorität als neues,
  explizit dokumentiertes Prinzip neben "keine Datumsheuristik" ergänzen.
- **Datenmodell:** `PlanPhase.jira_label`, `JiraIssueCache`, `WorklogPhaseOverride`
  dokumentieren; BD-1 als CLOSED markieren mit Verweis auf dieses Dokument (historische
  BD-1-Herleitung bleibt erhalten, nicht löschen — Muster identisch zu bereits als "obsolet"
  markierten historischen Business Decisions).
- **Phase Metrics (Abschnitt 5.2):** `ist_hours`/`effort_consumption_pct`-Beschreibung von
  "deferred (BD-1), liefert null" auf "aktuell, Resolver-basiert, null nur ohne Mapping oder
  ohne gemappte Worklogs" ändern; `remaining_plan_hours`/`overrun_hours` ergänzen.
- **Tempo/Jira-Abschnitt:** Mapping-Kette, `JiraIssueCache`, `WorklogPhaseOverride`,
  Resolver-Priorität, Konfliktprüfung, Mapping-Preview-Mechanik dokumentieren.
- **GAP/Control:** Klarstellen, dass `GET /gap`/`GET /forecast` weiterhin projektweit auf
  Legacy-`ResourceDemand` basieren und **nicht** die neue Phase-Ist-Quelle nutzen (bewusste
  Trennung, Abschnitt 20/22 hier).
- **Cockpit/Workspace:** neue Kapazität-Tab-Karte "Steuerung", neue Übersicht-Tab-Zeile
  "Ist-Daten" ergänzen.
- **Source-of-Truth-Matrix:** neue Zeilen `PlanPhase.jira_label`, `JiraIssueCache`,
  `WorklogPhaseOverride`, `Mapping Coverage`.
- **Deferred/Business Decisions:** BD-1 CLOSED mit Verweis auf dieses Dokument; BD-3 bleibt
  ausdrücklich offen und unverändert referenziert.

---

## 30. Implementation Packages P20.1–P20.8

| Paket | Inhalt | Abhängig von |
|---|---|---|
| **P20.1 — Jira/Tempo Mapping Domain** | `PlanPhase.jira_label` (Migration + Parent-Guard-Erweiterung + Konfliktprüfung beim Speichern, Abschnitt 11), `JiraIssueCache`-Tabelle + Sync-Erweiterung (`fields`-Set erweitern, Abschnitt 4/24), `WorklogPhaseOverride`-Tabelle + CRUD-Endpoints | — |
| **P20.2 — Worklog → PlanPhase Resolver** | Resolver-Modul (Abschnitt 8), reine Funktion `resolve_phase_for_worklog(...)`, keine Seiteneffekte, isoliert testbar | P20.1 |
| **P20.3 — Unmapped / Ambiguous / Coverage** | Coverage-Berechnung (Abschnitt 19), `GET /projects/{id}/actuals-coverage` | P20.2 |
| **P20.4 — Phase Actual Metrics** | `phase_metrics_calc.effort_consumption()` implementieren, `ist_hours`/`remaining_plan_hours`/`overrun_hours` in `PhaseMetricsOut`, Parent-Aggregation via `leaf_descendants` (Abschnitt 15/16) | P20.2 |
| **P20.5 — Plan-vs-Actual Workspace UX** | Kapazität-Tab-Karte "Steuerung", Übersicht-Tab Label-Picker + Mapping-Preview (Abschnitt 9/10/26) | P20.4 |
| **P20.6 — Person Actual Drilldown / Planned vs. Actual** | Personen-Gruppierung (Abschnitt 17), Assignment-vs-Actual-Vergleich (Abschnitt 18) | P20.4 |
| **P20.7 — Project/Portfolio Rollup & Coverage UI** | `ProjectJiraTab.tsx`-Coverage-Anzeige (Abschnitt 26), Verifikation, dass Projekt-Ist unverändert bleibt (Abschnitt 20) | P20.3 |
| **P20.8 — Regression / CONCEPT / E2E** | CONCEPT.md-Update (Abschnitt 29), alle Testfälle (Abschnitt 33) als automatisierte Tests, Regressionscheck `GET /gap`/`GET /forecast`/`health_calc` unverändert (Abschnitt 22/23) | P20.1–P20.7 |

---

## 31. Dependency Graph

```
P20.1 (Datenmodell + Sync-Erweiterung + Konfliktprüfung)
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
   │        (Workspace UX) (Person/Planned-vs-Actual)
   ▼              │      │
P20.7 ◄────────────┴──────┘
(Project/Portfolio Rollup)
   │
   ▼
P20.8 (Regression/CONCEPT/E2E)
```

---

## 32. Parallel Agent Plan

Nach P20.1+P20.2 (müssen sequenziell zuerst fertig sein, da alles andere auf dem Resolver
aufbaut) können folgende Pakete **parallel** bearbeitet werden, da sie unterschiedliche
Dateien/Layer berühren und nur lesend auf denselben Resolver-Output zugreifen:

- **Track A:** P20.3 (Coverage-Berechnung, `gap_analysis.py`-Nachbarmodul) → P20.7
  (Coverage-UI im bestehenden `ProjectJiraTab.tsx`).
- **Track B:** P20.4 (`phase_metrics_calc.py`-Erweiterung) → danach P20.5 (Workspace-UX,
  inkl. Mapping-Preview-Endpoint) und P20.6 (Person-Drilldown/Planned-vs-Actual) parallel
  zueinander, da beide nur lesend auf die in P20.4 neu befüllten `PhaseMetricsOut`-Felder
  zugreifen und unterschiedliche UI-Komponenten betreffen.

P20.8 (Regression/E2E/CONCEPT) läuft erst, wenn alle anderen Pakete gemerged sind — kein
Parallelisierungspotenzial, da es genau die Integration aller vorherigen Pakete prüft.

---

## 33. Test Strategy

Die Testfälle aus dem Auftrag werden 1:1 zu automatisierten Tests in P20.8:

| Test | Prüft | Paket |
|---|---|---|
| AT1 — Einfach (Konfiguration 80h Plan, Dominik 32h/Max 20h/Anna 8h, alle eindeutig gemappt) | Resolver + Aggregation + Personen-Drilldown, keine Doppelzählung → Ist 60h, Verbrauch 75%, Rest 20h | P20.2/P20.4/P20.6 |
| AT2 — Unmapped (120h Projekt, 100h gemappt, 20h unmapped) | Projekt-Ist bleibt 120h, Phase-Ist-Summe 100h, Coverage 83,33%, keine verlorenen Stunden | P20.3/P20.7 |
| AT3 — Ambiguous (8h matcht Phase A und B) | Einmalige Zählung als `AMBIGUOUS`, nicht A+8/B+8, Projekt-Ist bleibt 8h | P20.2/P20.3 |
| AT4 — Manual Override (8h unmapped → User ordnet Konfiguration zu) | Konfiguration +8h, Coverage steigt, Original-Tempo-Datensatz unverändert, `previous_status` im Override korrekt gesetzt | P20.1/P20.2 |
| AT5 — Parallele Phasen (Phase A und B identischer Zeitraum 01.10.–31.10.) | Trennung ausschließlich über Label, Datum irrelevant, keine Datumsheuristik greift | P20.2 |
| AT6 — Parent-Aggregation (Wareneingang: Child A 20h + Child B 40h) | `leaf_descendants`-Summe = 60h, keine doppelte Speicherung | P20.4 |
| AT7 — Kein Mapping | UI zeigt "Ist-Aufwand noch nicht zugeordnet", nicht `0h` | P20.4/P20.5 |
| AT8 — Planned vs. Actual Person (geplant: Dominik+Max; ist: Dominik+Anna) | UI erkennt "Anna nicht eingeplant" / "Max eingeplant, bisher kein Ist", keine automatische Assignment-Änderung | P20.6 |

Zusätzlich: Regressionstest, dass `GET /gap`/`GET /forecast`/`health_calc.compute_project_health`
nach P20 **byte-identische** Ergebnisse liefern wie vor P20 — Nicht-Vermischung von
Effort-Soll (Phase) und Capacity-Soll (`GET /gap`), bereits als Prinzip in CONCEPT.md
etabliert.

---

## 34. Risks

| Risiko | Einschätzung | Gegenmaßnahme |
|---|---|---|
| Teams pflegen Labels nicht konsequent → niedrige Coverage | Mittel, organisatorisch | Coverage-Kennzahl (Abschnitt 19) macht das sofort sichtbar statt es zu verstecken; Prozess-/Schulungsfrage beim Rollout, kein technischer Fix nötig |
| `Project.jira_component`-JQL ohne `project=`-Klausel (Abschnitt 5) — generische Label-Strings könnten global in anderen Jira-Projekten kollidieren | Niedrig–Mittel, vorbestehende Lücke auf Projektebene, durch P20 nicht verschärft (Phase-Resolver arbeitet nur auf bereits projekt-gescopten Zeilen) | Außerhalb P20-Scope (gehört zu Abschnitt 5, nicht zu BD-1); dokumentiert als Beobachtungspunkt für den Product Owner bei der Wahl generischer Component/Label-Strings auf Projektebene |
| `Project.jira_component` fehlendes Unique-Constraint erbt sich strukturell in die Phase-Ebene | Niedrig, vorbestehende Lücke | `JiraIssueCache.project_id` scoped Issues bereits auf das Projekt, das sie beim Sync gefunden hat; volle Lösung (Unique-Constraint) ist expliziter Nicht-Scope von P20 |
| Sync-Erweiterung (breiteres `fields`-Set) erhöht Jira-API-Last | Niedrig — derselbe API-Call, nur mehr Felder im Response, kein zusätzlicher Round-Trip | Verifiziert an `_search_issues`-Signatur (Abschnitt 24) |
| Override-Tabelle wird zur Schatten-Wahrheit, wenn Label sich später ändert | Niedrig | Override hat explizit höchste Priorität (Abschnitt 8) — bewusst so gewählt, damit ein Override nie durch ein nachträglich gesetztes Label "überschrieben" wird; UI zeigt Override-Status transparent an |
| Verwechslung Effort-Soll (Phase) mit Capacity-Soll (`GET /gap`) durch spätere Entwickler | Mittel — bereits einmal in P18 als Risiko erkannt | CONCEPT.md-Update (Abschnitt 29) hält die Trennung explizit fest, Regressionstest (Abschnitt 33) erzwingt sie technisch |
| Mapping-Preview zeigt veralteten Stand (Abschnitt 10), wenn User lange nicht synchronisiert hat | Niedrig | "Stand: letzter Sync"-Anzeige, kein Fake-Live-Ergebnis; bestehender "Jetzt synchronisieren"-Button bleibt der Weg zur Aktualisierung |

---

## 35. Rebuild Safety Assessment

Alle vorgeschlagenen Änderungen sind **additiv**:

- Zwei neue Tabellen (`JiraIssueCache`, `WorklogPhaseOverride`), kein Schema-Bruch.
- Ein neues nullable Feld (`PlanPhase.jira_label`), kein Pflichtfeld, keine Backfill-Pflicht.
- Kein bestehender Endpoint ändert sein Response-Schema in einer Breaking-Weise (nur neue
  optionale Felder in `PhaseMetricsOut`/`PlanPhaseOut`).
- `GET /gap`, `GET /forecast`, `health_calc.compute_project_health` bleiben unverändert
  (Abschnitt 20/22/23, mit Regressionstest abgesichert).
- Keine Berührung von B-8 (Legacy Cutover), `ResourceDemandGrid`, Subproject-Schema —
  verifiziert: keines der vorgeschlagenen P20-Pakete berührt
  `resource_demands.plan_phase_id IS NULL`-Zeilen oder die Legacy-Compat-UI.
- Migrationsreihenfolge unkritisch: `JiraIssueCache`/`WorklogPhaseOverride` können vor oder
  nach `PlanPhase.jira_label` angelegt werden, keine Zirkelabhängigkeit.
- `PlanHistory` wird nicht verändert (Abschnitt 24) — kein Risiko für bestehende
  Audit-Historie.

---

## 36. Implementation Readiness

**Alle in Abschnitt 28 aufgeführten Teilentscheidungen (BD-1A–BD-1G) sind in diesem
Durchgang geschlossen.** Datenmodell (Abschnitt 24), Resolver (Abschnitt 8), Konfliktprüfung
(Abschnitt 11), Mapping-Preview (Abschnitt 10), API (Abschnitt 25), UX (Abschnitt 9/26),
Implementierungspakete (Abschnitt 30) und Testabdeckung (Abschnitt 33) sind vollständig
spezifiziert und gegen den realen Code verifiziert (Zeile-für-Zeile-Verifikation, nicht nur
CONCEPT.md-Annahmen — inkl. erneuter Bestätigung, dass sich seit dem vorherigen P20-Durchgang
(PR #45) nichts am Code geändert hat). Keine offene technische Unsicherheit blockiert den
Start von P20.1.

Die einzige verbleibende Voraussetzung ist **organisatorisch, nicht technisch**: Der Product
Owner sollte bestätigen, dass die Label-Konvention (`phase:<name>`) im Jira-Tagesgeschäft der
Teams eingeführt werden kann — das beeinflusst die **Coverage nach Rollout**, nicht die
**Machbarkeit der Implementierung**. P20.1–P20.4 liefern von Tag 1 an korrekte Ergebnisse
auch bei Coverage 0% (durchgängig "nicht zugeordnet" statt falscher Werte).

---

# READY FOR P20 IMPLEMENTATION
