# Kapazitätsplaner im plx.crew Portal — Konzept

**Status:** Entwurf v0.1
**Ablösung von:** Excel/VBA-Kapazitätsplaner (`PowerPointGenerator`, siehe [`legacy/`](legacy/))
**Ziel-Umgebung:** Integration als Kachel im BUILD-Bereich des plx.crew Portals (`crew-portal.pure-lox.com`)

---

## 1. Ziel

Das bestehende Excel/VBA-Tool bildet Gantt-Phasen und FTE-Planung pro Projekt ab und exportiert nach PPTX. Das reicht für die Präsentation, aber:

- Keine Mehrbenutzer-Fähigkeit (eine `.xlsm`-Datei, Windows-only)
- Kein Abgleich mit der Realität — reine Planung, kein Ist
- Keine Team-/Auslastungssicht über alle Projekte hinweg

Das neue Tool übernimmt die **Planungslogik 1:1** aus dem Excel (Struktur, Phasencodes, FTE-Raster), läuft aber als Web-App im Portal und ergänzt:

1. **Ist-Daten aus Jira** (Worklogs)
2. **Team-/MA-Stammdaten** mit Kapazität
3. **Soll-Ist-Gap-Analyse mit Hochrechnung**

---

## 2. Architektur (High-Level)

```
plx.crew Portal (crew-portal.pure-lox.com)
└── BUILD → Kapazitätsplaner (neue Kachel)
       │
       ├── Frontend  (React, Portal-CI: Navy #002F5E / Blau #007CC1 / Rot #B30F0B)
       │      Zwei-Ebenen-Navigation (siehe Abschnitt 6):
       │      Ebene 1 Projektmanagement: Portfolio-Dashboard →
       │              Projekt-Workspace (Übersicht·Planung·Kommunikation·
       │              Dokumente·Historie·Jira·Einstellungen)
       │      Ebene 2 Controlling: Gap-Analyse·Kapazität·Forecast·
       │              Auslastung·KPIs·Reporting
       │      Ebene 1/2 sind reine Navigations-Gruppierungen, keine
       │      Zugriffskontrolle — es existiert kein Rollen-/Login-System
       │      im Repo (siehe Abschnitt 7).
       │
       ├── Backend-API (FastAPI oder Node, analog bestehendem Stack)
       │      /projects  /subprojects  /fte-plan  /team  /gap  /forecast
       │
       ├── PostgreSQL  (Planungsdaten, Team-Stammdaten, Worklog-Cache)
       │
       └── Jira-Sync-Service (periodischer Job, z. B. stündlich/täglich)
              → Atlassian REST API: Worklogs pro Ticket/MA/Zeitraum
              → schreibt in `jira_worklogs_cache`
```

Die PPTX-Exportfunktion des Excel-Tools bleibt als **Export-Endpoint** erhalten (`pptxgenjs`-Logik serverseitig wiederverwendbar, da bereits in Node/JS vorhanden) — Reporting-Bedarf für Kunden/Leitung bleibt so gedeckt, nur der Dateneingabe-Weg ändert sich.

Repo-Vorschlag: bestehendes `kapazitaetsplaner`-Repo strukturieren als:

```
kapazitaetsplaner/
├── frontend/        # React, Portal-Design
├── backend/         # API, Datenmodell, Jira-Sync
├── export/          # PPTX-Export (Migration aus PLX_generate_pptx.js)
└── migration/        # Einmal-Import bestehender Excel-Planungsdaten
```

---

## 3. Datenmodell

Direkt aus der Excel-Struktur abgeleitet, nur normalisiert:

| Tabelle | Felder (Auszug) | Entspricht Excel |
|---|---|---|
| `projects` | id, name, kunde, start_monat, anzahl_monate, jira_component, status, projektleiter (Freitext, neu) | Projektblatt Kopf |
| `subprojects` | id, project_id, name, reihenfolge | 3 Teilprojekte je Blatt (reine Feinplanung, kein eigenes Jira-Mapping) |
| `gantt_phases` | id, subproject_id, monat, phase_code (`p/k/t/s/g/?`) | Gantt-Zellen |
| `fte_plan` | id, subproject_id, monat, wert_soll | FTE-Zeilen (Soll) |
| `team_members` | id, name, jira_account_id, wochenstunden, team_id | neu |
| `teams` | id, name (Team-Kapa) | neu |
| `assignments` | id, team_member_id, subproject_id, anteil (%) | neu — verknüpft MA ↔ Projekt |
| `jira_worklogs_cache` | id, jira_account_id, jira_issue_key, datum, stunden, projekt_mapping | Ist-Daten aus Jira |
| `gap_snapshots` | id, project_id, monat, soll, ist, gap, hochrechnung, erstellt_am | berechnet, historisiert |

**Phasencodes und FTE-Heatmap-Schwellen** werden 1:1 aus dem Excel übernommen (siehe Referenzdokument), damit die Optik/Farblogik für alle Beteiligten vertraut bleibt. Ergänzt um den Phasencode `s` (Schulung), der im Excel-Tool noch nicht existierte, aber für die Rollout-Planung (Pflichtenheft → Konfiguration → Test → Schulung → GoLive) benötigt wird.

---

## 4. Jira-Integration (Ist-Daten)

**Datenquelle:** Worklogs (gebuchte Zeit), nicht Ticket-Status.

Ablauf:

1. **Mapping MA → Jira:** `team_members.jira_account_id` wird über die Team-Kapazität-Ansicht gepflegt — Suche per `GET /jira/lookup-account?query=` (Jira-Nutzersuche über Name/E-Mail), Übernahme der `accountId` per Klick.
2. **Mapping Ticket → Projekt:** über `projects.jira_component` (Jira-Component oder -Label je Projekt), gepflegt im Projekt-Detail. Auf Projekt- statt Teilprojekt-Ebene, da Teilprojekte nur die Feinplanung (Gantt/FTE-Soll) innerhalb eines Projekts sind und kein eigenes Gegenstück in Jira haben. Entscheidung zur offenen Frage in Abschnitt 10: Component/Label statt Custom Field, da ohne Jira-seitiges Setup nutzbar.
3. **Sync-Job:** `POST /jira/sync` fragt für jedes Projekt mit gesetzter `jira_component` alle Issues der Component/des Labels ab (JQL) und lädt deren Worklogs; nur Buchungen von MA mit bekannter `jira_account_id` werden übernommen (sonst fehlen die Wochenstunden für die FTE-Umrechnung). Ergebnis wird in `jira_worklogs_cache` upgesertet (aktuell manuell auslösbar über die Team-Kapazität-Ansicht; ein periodischer Scheduler ist eine spätere Ausbaustufe).
4. **Umrechnung Stunden → FTE:** `Ist_FTE(Monat) = Summe_Stunden / (Wochenstunden_MA × Arbeitswochen_Monat)`, aggregiert je Projekt. `Arbeitswochen_Monat` wird pauschal mit 52/12 ≈ 4,33 angesetzt (siehe `backend/app/constants.py`).

Konfiguration über Umgebungsvariablen `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` (siehe `backend/.env.example`); ohne diese bleibt der Sync deaktiviert (`GET /jira/status`), die übrige Planung funktioniert unabhängig davon weiter.

---

## 5. Soll-Ist-Gap-Analyse mit Hochrechnung

Pro Teilprojekt/Monat:

- **Soll** = geplanter FTE-Wert aus `fte_plan` (wie im Excel eingetragen)
- **Ist** = aus Jira-Worklogs berechneter FTE-Wert (nur für vergangene/laufende Monate, da noch keine Buchungen für die Zukunft existieren)
- **Gap** = `Ist − Soll` (negativ = Unterauslastung/Verzug, positiv = Überlast)
- **Hochrechnung** (für die verbleibenden Monate des Planungszeitraums): zwei Varianten zur Auswahl, je nach Datenlage —
  1. **Trendfortschreibung:** Durchschnitt der Ist-Werte der letzten 3 Monate wird auf die Restmonate projiziert
  2. **Restaufwand-basiert:** offene Jira-Tickets (Restschätzung/Story Points) werden auf verbleibende Monate verteilt — genauer, aber abhängig von sauberer Schätzpflege in Jira

Empfehlung für MVP: **Variante 1 (Trendfortschreibung)**, da sie ohne zusätzliche Jira-Datenpflege auskommt. Variante 2 als Ausbaustufe.

Ergebnis pro Projekt: eine Zeile "Hochrechnung Jahresende/Projektende" — zeigt, ob das Projekt bei aktuellem Buchungsverhalten voraussichtlich über oder unter Plan liegt.

---

## 6. UI/UX-Konzept (Views)

Stand v0.2: aus der ursprünglich flachen 4-View-Navigation (Portfolio-Dashboard /
Projekt-Detail / Team-Kapazität / Gap-Analyse) ist mit wachsendem Funktionsumfang der
Projekt-Detail-Seite (Notizen, Verlauf, Jira-Verknüpfung, Team-Zuordnung — alles auf
einer Seite) eine Zwei-Ebenen-Struktur mit Projekt-Workspace geworden. Portfolio bleibt
Einstiegspunkt; jedes Projekt ist ein eigener Workspace mit Tab-Leiste statt einer
einzelnen, immer weiter wachsenden Detailseite.

### Ebene 1 — Projektmanagement

Portfolio-Dashboard (unverändert: alle Projekte als Kacheln, Mini-Gap-Indikator
grün/gelb/rot/grau) → Klick auf ein Projekt öffnet dessen Workspace mit sieben Tabs:

| Tab | Inhalt | Entspricht |
|---|---|---|
| **Übersicht** | Projektname, Status, Ampel (= Gap-Status), Kunde, Projektleiter, Start/Ende, Auslastung, letzte Änderungen, letzte Notizen, offene Risiken/Entscheidungen | neu (Phase 5) |
| **Planung** | Stammdaten, Gantt-Phasen + FTE-Tabelle (editierbar wie Excel), Team-Zuordnung, Teilprojekte | Projekt 01–12 Blätter |
| **Kommunikation** | Diskussionen (= bisherige Notizen), Entscheidungen, Risiken, Meetingprotokolle, je mit Tags | Diskussionen: bestehend; Rest neu (Phase 4) |
| **Dokumente** | Datei-Upload/-Liste je Projekt, Suche, Tags | neu (Phase 3) |
| **Historie** | Automatisches Änderungsprotokoll (Audit), nur Werte-Änderungen — keine Kommentare/Dateien | bestehend (`PlanHistory`) |
| **Jira** | Jira-Komponente/Label, Sync-Status, letzter Sync, offene Jira-Issues | bestehend, um offene Issues erweitert |
| **Einstellungen** | Status-Lifecycle, Projektleiter, Jira-Verknüpfung bearbeiten | neu (Phase 2) |

### Ebene 2 — Controlling

| View | Inhalt | Basis |
|---|---|---|
| **Gap-Analyse** | Soll/Ist/Hochrechnung als Chart je Projekt, Filterung nach Team/Zeitraum | bestehend |
| **Kapazität** | MA-Liste, Teams, Auslastung über alle zugeordneten Projekte (bisher "Team-Kapazität") | bestehend |
| **Forecast** | Hochrechnung Jahresende/Projektende je Projekt | nur neue Sicht auf bestehenden `GET /forecast` |
| **Auslastung** | Auslastungsgrad je Teammitglied/Team (zugeordnetes FTE / Kapazitäts-FTE) | neue Aggregation, bestehende Datenquellen |
| **KPIs** | Portfolio-Kennzahlen: Projektstatus-Verteilung, Ø Auslastung, offene Risiken/Entscheidungen gesamt | neue Aggregation, teilweise abhängig von Kommunikation-Datenmodell |
| **Reporting** | Export (MVP: clientseitiger CSV-Export der Gap/Forecast/KPI-Daten) | clientseitiger Export, kein neuer Endpoint; Portfolio-PPTX-Export ist spätere Ausbaustufe |

`/jira-projekte` (Jira-Projekt-Katalog, "wird geplant"-Verwaltung) bleibt als eigene,
projektübergreifende Verwaltungsseite außerhalb der zwei Ebenen bestehen.

---

## 7. Rollen & Rechte

- **MA:** sieht eigene gebuchte Zeit und zugeordnete Projekte
- **Projekt-/Teamleitung:** sieht Planung + Ist + Gap für eigene Projekte/Team
- **Management:** Portfolio-Sicht über alle Projekte
- Anbindung an bestehendes Portal-Login (kein separates Auth nötig, falls Portal-SSO vorhanden — technisch zu prüfen)

---

## 8. Migration

- Einmaliger Import-Skript liest bestehende `.xlsm`-Dateien (openpyxl oder ähnlich) und befüllt `projects`, `subprojects`, `gantt_phases`, `fte_plan` — damit keine historische Planung verloren geht.
- Bestehendes Node-Skript `PLX_generate_pptx.js` wird als PPTX-Export-Funktion in `export/` weiterverwendet, nur die Datenquelle wechselt von JSON-Datei-Export aus VBA zu direktem DB-Query.

---

## 9. Phasenplan (Vorschlag)

1. **MVP:** Projekt-/FTE-Planung als Web-Formular (Ersatz Excel-Eingabe), PPTX-Export weiter nutzbar
2. **Jira-Ist-Integration:** Worklog-Sync + Ist-Anzeige je Projekt
3. **Gap-Analyse + Hochrechnung:** Dashboard-View, Trendfortschreibung
4. **Team-Kapazität:** MA-Stammdaten, teamübergreifende Auslastungssicht
5. **Rollout & Excel-Migration:** historische Daten importieren, altes Tool ablösen
6. **IA-Umbau:** Projekt-Workspace mit Tabs (Übersicht/Planung/Kommunikation/Dokumente/
   Historie/Jira/Einstellungen) + Zwei-Ebenen-Navigation (Projektmanagement/Controlling),
   Routing-Grundgerüst ohne neue Datenmodelle
7. **Kommunikation-Datenmodell:** Entscheidungen/Risiken/Meetingprotokolle/Tags
8. **Dokumente-Datenmodell:** Datei-Upload/-Storage je Projekt
9. **Controlling-Erweiterung:** Auslastung/KPIs/Reporting

---

## 10. Offene Punkte

- ~~Mapping Jira-Ticket → Kapa-Projekt: Component, Label oder Custom Field?~~ Entschieden: Component/Label über `projects.jira_component`, auf Projekt- statt Teilprojekt-Ebene (siehe Abschnitt 4).
- Jira-Projekt-Katalog: Browsing der Jira-Projekte inkl. Auswahl "wird geplant" + Status (aktiv/on hold/beendet) und Component/Label-Picker statt Freitext — noch nicht umgesetzt.
- Portal-Login/SSO-Anbindung technisch klären
- Hochrechnungsmethode: reicht Trendfortschreibung, oder wird Restaufwand-basierte Variante von Anfang an gebraucht?
- Datenhoheit Team-Kapazität: eigene Pflege im Tool oder Anbindung an Personal-/HR-Datenquelle? (aktuell: eigene Pflege im Tool, siehe Abschnitt 11)
- Periodischer Jira-Sync-Job (Cron/Scheduler) statt manuellem Auslösen über die UI
- Kein Alembic/Migrationstool im Repo — Schemaänderungen an bestehenden (nicht-SQLite-frischen) Datenbanken erfordern aktuell manuelle Anpassung
- Ebene 1 (Projektmanagement) / Ebene 2 (Controlling) ist reine Navigations-Gruppierung, keine Zugriffskontrolle — es gibt kein Rollen-/Login-System im Repo (siehe Abschnitt 7); wird hier bewusst festgehalten, damit das nicht spätestens beim nächsten KI-Prompt fälschlich als vorhandene RBAC angenommen wird
- Projektleiter (`projects.projektleiter`) ist bewusst ein Freitextfeld statt FK, da es kein Personen-/User-Verzeichnis im Repo gibt — spätere Ausbaustufe: FK auf ein Personen-Verzeichnis, sobald eines existiert
- "Offene Aufgaben" auf dem Übersicht-Tab ist für die MVP bewusst ein Alias auf `offene Entscheidungen + offene Risiken` — es gibt (noch) kein eigenständiges Aufgaben-/Task-Modell
- Milestones (Planung-Tab) sind bewusst kein eigenes Datenmodell, sondern der bestehende Gantt-Phasencode `?` (Meilenstein) — eine separate Milestone-Liste ist nicht geplant, solange der Phasencode ausreicht
- Reporting-MVP ist bewusst ein clientseitiger CSV-Export ohne neuen Backend-Endpoint; ein Portfolio-weiter PPTX-Export (analog zum bestehenden Projekt-PPTX-Export) ist als spätere Ausbaustufe zurückgestellt, nicht Teil des IA-Umbaus

---

## 11. Umsetzungsstand

Dieses Repo enthält:

1. **Schritt 1 (MVP):** Projekt-/FTE-Planung als Web-Formular inkl. Schulungsphase (`s`), PPTX-Export weiter nutzbar.
2. **Schritt 2 (Jira-Ist-Integration):** Worklog-Sync (`POST /jira/sync`) und Ist-FTE-Anzeige je Projekt/Monat (`GET /projects/{id}` liefert `ist` auf Projekt-Ebene, neben `fte` je Teilprojekt).
3. **Schritt 4 (Team-Kapazität):** MA-/Team-Stammdaten inkl. Jira-Account-Zuordnung und Zuordnung MA ↔ Projekt (`/team/*`), Voraussetzung für Schritt 2.
4. **Schritt 3 (Gap-Analyse + Hochrechnung):** `GET /gap` (Soll/Ist/Gap je Monat und Projekt, optional `?team_id=`) und `GET /forecast` (Kurzform: eine Zeile "Hochrechnung Jahresende/Projektende" je Projekt). Hochrechnung nach Variante 1 (Trendfortschreibung, Durchschnitt der letzten 3 Ist-Monate, siehe `backend/app/gap_analysis.py`). Frontend-View **Gap-Analyse** zeigt Soll/Ist/Hochrechnung als Chart je Projekt mit Team-Filter; Portfolio-Dashboard zeigt den Mini-Gap-Indikator (grün/gelb/rot/grau) je Projektkachel.
5. **Schritt 6 (IA-Umbau, Routing-Grundgerüst):** `/projekte/:id` ist jetzt ein Projekt-Workspace (`frontend/src/views/project/ProjectWorkspace.tsx`) mit nested Routes/Tab-Leiste statt einer einzelnen Detailseite. Die frühere `ProjectDetail.tsx` (1055 Zeilen) ist aufgeteilt in `ProjectPlanningTab` (Stammdaten/Gantt/FTE/Team-Zuordnung/Teilprojekte), `ProjectJiraTab`, `ProjectHistoryTab` (Verlauf, audit-only), `ProjectCommunicationTab` (Diskussionen = bisherige Notizen; Entscheidungen/Risiken/Meetingprotokolle sind Platzhalter bis Schritt 7). `ProjectOverviewTab`, `ProjectDocumentsTab` sind Platzhalter (Schritt 5/8). Top-Nav ist zweigeteilt (Projektmanagement/Controlling, `App.tsx`); `/jira-projekte` bleibt eigenständig.
6. **Schritt 2 (Einstellungen-Tab + Projektleiter):** `projects.projektleiter` (Freitext, siehe Abschnitt 3/10) über `ProjectUpdate`/`ProjectCreate` editierbar. `ProjectSettingsTab` bündelt jetzt Status-Lifecycle, Projektleiter und die Jira-Verknüpfung (Component/Label/Projekt-Auswahl) — das ist die einzige Stelle, an der die Jira-Verknüpfung *bearbeitet* wird. `ProjectJiraTab` ist entsprechend auf eine Lesesicht (aktuelle Verknüpfung, Ist-FTE-Tabelle, "Jetzt synchronisieren"-Button mit Link zurück zu Einstellungen) reduziert.

Details zu Aufbau und lokalem Betrieb siehe [`README.md`](README.md).

Noch nicht umgesetzt: Restaufwand-basierte Hochrechnung (Variante 2), Portal-SSO, der Excel-Migrationslauf für Bestandsdaten, sowie die Schritte 7/8/9 aus Abschnitt 9 (Kommunikation-/Dokumente-Datenmodell, Controlling-Erweiterung) und der offene Jira-Issues-Endpoint für den Jira-Tab. Siehe Abschnitt 10 für offene Entscheidungen.
