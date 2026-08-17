# Kapazitätsplaner im plx.crew Portal — Konzept

**Status:** v0.15 — Projekt-Workspace, Kommunikation/Dokumentenablage, Controlling-Erweiterung sowie Phase 13–24 (Technisches Fundament, Personen/Organisation/Permissions, Semantic Knowledge Foundation, Activity & Blocker Core, Project Planning Core, Baseline Management, Capacity Planning Core, Real Capacity, GAP Engine, Project Control & Health, Controlling & Capacity Intelligence, Knowledge Experience) der Kapazitätsplaner-v2-Zielarchitektur umgesetzt (siehe Abschnitt 11 für den vollständigen Umsetzungsstand, Abschnitt 12 für die Zielarchitektur)
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
| `comments` | id, project_id, subproject_id, monat, phase_code, text, erstellt_am | Notizen/Diskussionen + Gantt-Zell-Kommentare |
| `plan_history` | id, project_id, subproject_id, bereich, monat, feld, alter_wert, neuer_wert, geaendert_am, kommentar_id, **batch_id** (neu, Revisionsgruppierung) | Änderungsprotokoll |
| `documents` | id, project_id, dateiname, speicherpfad, mimetype, groesse_bytes, hochgeladen_von, hochgeladen_am | neu — zentrale Dokumentenablage, siehe Abschnitt 6a |
| `document_links` | id, document_id, entity_type, entity_id, erstellt_am | neu — generische Verknüpfung Document ↔ comment/decision/risk/meeting_minutes |
| `tags` | id, name (unique, systemweit) | neu |
| `tag_links` | id, tag_id, entity_type, entity_id | neu — generische Verknüpfung Tag ↔ comment/decision/risk/meeting_minutes/document |
| `decisions` | id, project_id, titel, beschreibung, status, entschieden_von, entschieden_am, erstellt_am | neu (Kommunikation-Tab) |
| `risks` | id, project_id, titel, beschreibung, wahrscheinlichkeit, auswirkung, status, owner, faellig_am, erstellt_am, aktualisiert_am | neu (Kommunikation-Tab) |
| `meeting_minutes` | id, project_id, titel, datum, teilnehmer, text, erstellt_am | neu (Kommunikation-Tab) |
| `tasks` | id, project_id, titel, beschreibung, status, zustaendig, faellig_am, erstellt_am, aktualisiert_am | neu (Kommunikation-Tab) — löst den früheren "offene Aufgaben"-Alias auf dem Übersicht-Tab ab |

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
| **Übersicht** | Projektname, Status, Ampel (= Gap-Status aus `GET /gap/{id}`), Kunde, Projektleiter, Start/Ende, Auslastung (Hochrechnung/Soll in %), letzte Änderungen, letzte Notizen, offene Risiken/Entscheidungen ("offene Aufgaben") | neu (Schritt 8b) |
| **Planung** | Stammdaten, Gantt-Phasen + FTE-Tabelle (editierbar wie Excel), Team-Zuordnung, Teilprojekte | Projekt 01–12 Blätter |
| **Kommunikation** | Diskussionen (= bisherige Notizen, jetzt mit Tags + Dateianhängen), Aufgaben, Entscheidungen, Risiken, Meetingprotokolle, je mit Tags + Anhängen | Diskussionen: bestehend + erweitert (Phase 3); Entscheidungen/Risiken/Meetings neu (Phase 4); Aufgaben neu (Schritt 10) |
| **Dokumente** | **Zentrale Dokumentenablage des gesamten Projekts** — zeigt jede Datei, unabhängig davon ob sie hier direkt oder als Anhang in Kommunikation hochgeladen wurde, inkl. Suche/Tag-Filter/Typ-Filter und "Verwendet in"-Backlinks. Siehe Abschnitt 6a. | neu (Phase 3) |
| **Historie** | Automatisches Änderungsprotokoll (Audit), nach Datum/Revision gruppiert, nur Werte-Änderungen — keine Kommentare/Dateien | bestehend (`PlanHistory`), Gruppierung neu (Phase 3b) |
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

## 6a. Dokumente, Tags und Verknüpfungen

Drei Bereiche im Projekt-Workspace beantworten bewusst unterschiedliche Fragen und werden
nicht miteinander vermischt:

- **Historie** beantwortet: **WAS** wurde **WANN** von **WEM** geändert? (reiner Audit-Trail)
- **Kommunikation** beantwortet: **WARUM** wurde etwas gemacht/entschieden? (Diskussionen,
  Entscheidungen, Risiken, Meetingprotokolle)
- **Dokumente** beantwortet: **WELCHE** Unterlagen gehören dazu? (zentrale Dateiablage)

Die drei Bereiche sind untereinander verknüpfbar, aber jeweils fachlich eigenständig
verantwortlich.

### Zentrale Dokumentenablage statt separater Anhänge

**Es gibt keine getrennten Attachment-Systeme.** Jede Datei, die irgendwo im Projekt
hochgeladen wird — direkt im Dokumente-Tab oder als Anhang an eine Notiz/Entscheidung/
Risiko/Meetingprotokoll — läuft über denselben einen Endpoint (`POST
/projects/{id}/documents`, multipart) und wird physisch sowie als `documents`-Zeile
**genau einmal** angelegt. Andere Bereiche referenzieren die Datei nur über eine generische
Verknüpfungstabelle `document_links` (`document_id`, `entity_type`, `entity_id`,
`erstellt_am`) — analog zum ebenfalls generischen Tag-System (`tags` + `tag_links`, siehe
Abschnitt 3). Ein Dokument kann dadurch von mehreren Entitäten gleichzeitig referenziert
werden (z. B. dieselbe PDF sowohl an einer Notiz als auch an einem Meetingprotokoll), ohne
dass die Datei oder der Datensatz dupliziert wird.

`entity_type` ist ein offenes String-Feld, aktuell genutzt: `comment` (= Notizen/
Diskussionen — nur allgemeine, nicht die Gantt-Zell-Kommentare), `decision`, `risk`,
`meeting_minutes`, `task` (Aufgaben, siehe unten). `tags`/`tag_links` nutzen zusätzlich
`document` (Dokumente sind selbst taggbar). Bewusst offen gehalten für spätere Erweiterung
ohne Schema-Änderung, z. B. `milestone`, `revision`, `jira_issue`.

**Upload-Workflow** (z. B. eine Notiz mit zwei Anhängen):
1. Notiz wird über `POST /projects/{id}/comments` gespeichert (liefert die `id`).
2. Für jede Datei: `POST /projects/{id}/documents` mit `entity_type=comment`,
   `entity_id=<comment.id>` — legt Datei + `documents`-Zeile + `document_links`-Zeile in
   einem Aufruf an.
3. Die Datei erscheint sofort unter der Notiz **und** automatisch im Dokumente-Tab —
   derselbe Datensatz, keine Kopie.

Eine bereits vorhandene Datei zusätzlich an eine andere Entität hängen (kein Re-Upload):
`POST /document-links` (Body: `document_id`, `entity_type`, `entity_id`).

**Lösch-/Unlink-Semantik:**
- `DELETE /document-links/{id}` entfernt nur die Verknüpfung, nie die Datei.
- `DELETE /documents/{id}` löscht Datei + `documents`-Zeile + alle zugehörigen
  `document_links`/`tag_links`-Zeilen — das Frontend zeigt vorher die "Verwendet in"-Liste
  im Bestätigungsdialog.
- Löschen einer Notiz/Entscheidung/eines Risikos/Meetingprotokolls entfernt **nur** dessen
  eigene `tag_links`/`document_links`-Zeilen, nie die verknüpften `documents`-Zeilen selbst
  — die zentrale Ablage bleibt bestehen.
- Löschen eines Projekts räumt konsequent alle oben genannten Zeilen sowie die physischen
  Dateien unter `DOCUMENTS_DIR` auf (`routers/projects.py::delete_project`).

### Tags

Systemweit wiederverwendbar (nicht projektgebunden), `tags` + `tag_links` (`entity_type`,
`entity_id` — dasselbe Vokabular wie `document_links`, plus `document`). Zuweisbar an
Notizen, Dokumente, Entscheidungen, Risiken, Meetingprotokolle. Autocomplete über `GET
/tags?search=`, neue Tags werden bei Verwendung automatisch angelegt (kein separater
"Tag anlegen"-Schritt).

### Historie-Revisionen

`plan_history` bekommt eine zusätzliche, nullable `batch_id`-Spalte: Alle Änderungen eines
Speichern-Klicks in der Planung teilen sich eine (clientseitig per `crypto.randomUUID()`
erzeugte) `batch_id` und werden im Historie-Tab als eine "Revision" gruppiert dargestellt
(Datum → Revision → aufklappbare Detailliste). `kommentar_id` bleibt davon unabhängig die
optionale fachliche Begründung.

### Dateikategorien / E-Mails

Ein Typ-Filter (PDF/Mail/Excel/Word/Bild) im Dokumente-Tab wird **clientseitig** aus
`mimetype`/Dateiendung abgeleitet, es gibt keinen serverseitigen `type=`-Parameter oder
eine feste Mimetype-Taxonomie in der API. `.eml`-Dateien sind normale Dokumente;
`documents_storage.py` normalisiert das gespeicherte `mimetype` über
`mimetypes.guess_type()`, falls der Browser keinen sinnvollen `content_type` mitschickt —
eine strukturierte E-Mail-Vorschau (Absender/Betreff/Anhänge aus dem `.eml`-Inhalt geparst)
ist bewusst zurückgestellt, siehe Abschnitt 10.

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
7. **Zentrale Dokumentenablage + Tags:** `documents`/`document_links`/`tags`/`tag_links`,
   ein Upload-Pfad für das gesamte Projekt (siehe Abschnitt 6a) — Voraussetzung für Schritt 8
7b. **Historie-Revisionsgruppierung:** `plan_history.batch_id`, Datum-/Revision-gruppierte
   Historie-Ansicht — unabhängig von Schritt 7, parallelisierbar
8. **Kommunikation-Datenmodell:** Entscheidungen/Risiken/Meetingprotokolle, Notizen um
   Tags/Anhänge erweitert (setzt Schritt 7 voraus)
8b. **Übersicht-Tab:** Ampel/Auslastung/letzte Änderungen/letzte Notizen/offene Aufgaben
   als reine Aggregation bestehender Endpoints (setzt Schritt 2 + 8 voraus)
9. **Controlling-Erweiterung:** Auslastung/KPIs/Reporting
10. **Aufgaben-Datenmodell:** `Task` löst den MVP-Alias ("offene Aufgaben" = offene
    Risiken + offene Entscheidungen) auf dem Übersicht-Tab ab; fünfter Sub-Bereich im
    Kommunikation-Tab

---

## 10. Offene Punkte

- ~~Mapping Jira-Ticket → Kapa-Projekt: Component, Label oder Custom Field?~~ Entschieden: Component/Label über `projects.jira_component`, auf Projekt- statt Teilprojekt-Ebene (siehe Abschnitt 4).
- Jira-Projekt-Katalog: Browsing der Jira-Projekte inkl. Auswahl "wird geplant" + Status (aktiv/on hold/beendet) und Component/Label-Picker statt Freitext — noch nicht umgesetzt.
- Portal-Login/SSO-Anbindung technisch klären
- Hochrechnungsmethode: reicht Trendfortschreibung, oder wird Restaufwand-basierte Variante von Anfang an gebraucht?
- Datenhoheit Team-Kapazität: eigene Pflege im Tool oder Anbindung an Personal-/HR-Datenquelle? (aktuell: eigene Pflege im Tool, siehe Abschnitt 11)
- Periodischer Jira-Sync-Job (Cron/Scheduler) statt manuellem Auslösen über die UI
- ~~Kein Alembic/Migrationstool im Repo — Schemaänderungen an bestehenden (nicht-SQLite-frischen) Datenbanken erfordern aktuell manuelle Anpassung~~ Umgesetzt (Phase 13): Alembic eingeführt, siehe Abschnitt 12.1.
- Ebene 1 (Projektmanagement) / Ebene 2 (Controlling) ist reine Navigations-Gruppierung, keine Zugriffskontrolle — es gibt kein Rollen-/Login-System im Repo (siehe Abschnitt 7); wird hier bewusst festgehalten, damit das nicht spätestens beim nächsten KI-Prompt fälschlich als vorhandene RBAC angenommen wird
- Projektleiter (`projects.projektleiter`) ist bewusst ein Freitextfeld statt FK, da es kein Personen-/User-Verzeichnis im Repo gibt — spätere Ausbaustufe: FK auf ein Personen-Verzeichnis, sobald eines existiert
- ~~"Offene Aufgaben" auf dem Übersicht-Tab ist für die MVP bewusst ein Alias auf `offene Entscheidungen + offene Risiken` — es gibt (noch) kein eigenständiges Aufgaben-/Task-Modell~~ Umgesetzt (Schritt 10): echtes `tasks`-Modell, "Offene Aufgaben" zeigt jetzt echte offene Tasks zusätzlich zu Risiken/Entscheidungen (drei erkennbare Gruppen mit eigenem Icon). `zustaendig` ist bewusst Freitext (wie `Risk.owner`), kein FK auf `TeamMember` — konsistent zur Projektleiter-Entscheidung oben, da es kein Personen-/User-Verzeichnis für Zuweisungen gibt
- Milestones (Planung-Tab) sind bewusst kein eigenes Datenmodell, sondern der bestehende Gantt-Phasencode `?` (Meilenstein) — eine separate Milestone-Liste ist nicht geplant, solange der Phasencode ausreicht
- Reporting-MVP ist bewusst ein clientseitiger CSV-Export ohne neuen Backend-Endpoint; ein Portfolio-weiter PPTX-Export (analog zum bestehenden Projekt-PPTX-Export) ist als spätere Ausbaustufe zurückgestellt, nicht Teil des IA-Umbaus
- Notiz-/Kommentar-Karten zeigen bewusst **keinen Autor** — es gibt kein Auth-/User-System im Repo, ein Freitext-"Autor"-Feld würde nur eine echte Anmeldung vortäuschen; nur Zeitstempel wird angezeigt, bis ein User-System existiert
- Dokument-Typ-Filter (PDF/Mail/Excel/Word/Bild) im Dokumente-Tab ist bewusst clientseitig aus `mimetype`/Dateiendung abgeleitet statt einer serverseitigen Mimetype-Taxonomie
- "Verwendet in"-Backlinks im Dokumente-Tab verlinken auf den Kommunikation-Tab, aber (noch) nicht deep-scrollend zum konkreten Eintrag — MVP-Einschränkung
- Strukturierte E-Mail-Vorschau für `.eml`-Anhänge (Absender/Betreff/Anhänge aus dem Dateiinhalt geparst) ist zurückgestellt; MVP = Speichern + Download wie jedes andere Dokument, MIME-Type-Handling ist aber bereits darauf vorbereitet (siehe Abschnitt 6a)
- Auslastungsberechnung (`GET /team/utilization`) setzt 40 Wochenstunden als Referenz für "1.0 FTE" voraus (`VOLLZEIT_WOCHENSTUNDEN` in `backend/app/routers/team.py`) — passend zum bestehenden `TeamMember.wochenstunden`-Default, aber nicht konfigurierbar; falls unterschiedliche Referenz-Wochenstunden je Team/Standort gebraucht werden, ist das eine spätere Ausbaustufe
- Reporting-CSV nutzt `;` als Trennzeichen (Excel-DE-Konvention) und ein UTF-8-BOM für korrekte Umlaut-Darstellung beim Öffnen in Excel — bewusste Entscheidung, kein Standard-CSV mit `,`

---

## 11. Umsetzungsstand

Dieses Repo enthält:

1. **Schritt 1 (MVP):** Projekt-/FTE-Planung als Web-Formular inkl. Schulungsphase (`s`), PPTX-Export weiter nutzbar.
2. **Schritt 2 (Jira-Ist-Integration):** Worklog-Sync (`POST /jira/sync`) und Ist-FTE-Anzeige je Projekt/Monat (`GET /projects/{id}` liefert `ist` auf Projekt-Ebene, neben `fte` je Teilprojekt).
3. **Schritt 4 (Team-Kapazität):** MA-/Team-Stammdaten inkl. Jira-Account-Zuordnung und Zuordnung MA ↔ Projekt (`/team/*`), Voraussetzung für Schritt 2.
4. **Schritt 3 (Gap-Analyse + Hochrechnung):** `GET /gap` (Soll/Ist/Gap je Monat und Projekt, optional `?team_id=`) und `GET /forecast` (Kurzform: eine Zeile "Hochrechnung Jahresende/Projektende" je Projekt). Hochrechnung nach Variante 1 (Trendfortschreibung, Durchschnitt der letzten 3 Ist-Monate, siehe `backend/app/gap_analysis.py`). Frontend-View **Gap-Analyse** zeigt Soll/Ist/Hochrechnung als Chart je Projekt mit Team-Filter; Portfolio-Dashboard zeigt den Mini-Gap-Indikator (grün/gelb/rot/grau) je Projektkachel.
5. **Schritt 6 (IA-Umbau, Routing-Grundgerüst):** `/projekte/:id` ist jetzt ein Projekt-Workspace (`frontend/src/views/project/ProjectWorkspace.tsx`) mit nested Routes/Tab-Leiste statt einer einzelnen Detailseite. Die frühere `ProjectDetail.tsx` (1055 Zeilen) ist aufgeteilt in `ProjectPlanningTab` (Stammdaten/Gantt/FTE/Team-Zuordnung/Teilprojekte), `ProjectJiraTab`, `ProjectHistoryTab` (Verlauf, audit-only), `ProjectCommunicationTab` (Diskussionen = bisherige Notizen; Entscheidungen/Risiken/Meetingprotokolle wurden in Schritt 8 ergänzt, siehe unten). `ProjectOverviewTab` wurde in Schritt 8b fertiggestellt, `ProjectDocumentsTab` in Schritt 7. Top-Nav ist zweigeteilt (Projektmanagement/Controlling, `App.tsx`); `/jira-projekte` bleibt eigenständig.
6. **Schritt 2 (Einstellungen-Tab + Projektleiter):** `projects.projektleiter` (Freitext, siehe Abschnitt 3/10) über `ProjectUpdate`/`ProjectCreate` editierbar. `ProjectSettingsTab` bündelt jetzt Status-Lifecycle, Projektleiter und die Jira-Verknüpfung (Component/Label/Projekt-Auswahl) — das ist die einzige Stelle, an der die Jira-Verknüpfung *bearbeitet* wird. `ProjectJiraTab` ist entsprechend auf eine Lesesicht (aktuelle Verknüpfung, Ist-FTE-Tabelle, "Jetzt synchronisieren"-Button mit Link zurück zu Einstellungen) reduziert.
7. **Schritt 7 (Zentrale Dokumentenablage + Tags):** `documents`/`document_links`/`tags`/`tag_links`-Tabellen; einziger Upload-Pfad `POST /projects/{id}/documents` (multipart, optional `entity_type`+`entity_id` für atomare Verknüpfung beim Hochladen), `POST /document-links`/`DELETE /document-links/{id}` zum Verknüpfen/Entfernen ohne Re-Upload, `GET /projects/{id}/documents?search=&tag=`, `DELETE /documents/{id}` (räumt Datei + alle Verknüpfungen auf), `GET /tags?search=` (Autocomplete) — alles in `backend/app/routers/documents.py` + gemeinsamem Helper-Modul `backend/app/entity_links.py`. `Comment`/Notizen sind jetzt taggbar und können Dateien referenzieren (`CommentCreate.tags`, `CommentOut.documents`). Frontend: `ProjectDocumentsTab` voll funktionsfähig (Suche, Tag-Filter, clientseitiger Typ-Filter, "Verwendet in"-Backlinks, Löschen mit Verwendungs-Hinweis), `TagInput`/`AttachmentPicker`/`AttachmentList`-Komponenten, `NotesSection` als Kommentar-Karten mit Tags+Anhängen. `delete_project`/`delete_subproject`/`delete_comment` räumen die neuen Verknüpfungstabellen mit auf. Verifiziert: Upload→Verknüpfung→"Verwendet in" (Browser + curl), Mehrfachverknüpfung ohne Datei-Duplikat, Unlink vs. vollständiges Löschen, Cascade-Cleanup beim Löschen.
8. **Schritt 7b (Historie-Revisionsgruppierung):** `plan_history.batch_id` (nullable, Migration analog `projektleiter`); `ProjectPlanningTab.handleSave()` erzeugt pro Speichern-Klick einmalig `crypto.randomUUID()` und reicht sie durch `PhasenUpdate`/`FteUpdate`/`ProjectUpdate` an `_log_change()` weiter (`kommentar_id` bleibt davon unabhängig die optionale Begründung). `HistoryTimeline.tsx` (`frontend/src/views/project/components/`) gruppiert clientseitig nach Kalendertag (Heute/Gestern/Datum) und darin nach `batch_id` (Einträge ohne `batch_id` = eigene Einzel-Revision), zeigt eine generierte Stichpunkt-Zusammenfassung ("Projektname geändert", "3 Phasen geändert") mit aufklappbarer Detailliste (wiederverwendet `describeEntry()`/`formatTimestamp()`/`BEREICH_LABELS` aus `HistoryPanel.tsx`, jetzt exportiert). `ProjectHistoryTab` nutzt `HistoryTimeline` statt der flachen Liste, Bereich ist innerhalb scrollbar. Verifiziert per Playwright: mehrere Gantt-Zellen + Stammdaten in einem Speichern-Klick erscheinen als eine Revision mit korrekter Zusammenfassung; ein Bug in `_history_out()` (fehlendes `batch_id` in der Response) wurde dabei gefunden und behoben.
9. **Schritt 8 (Kommunikation: Entscheidungen/Risiken/Meetingprotokolle):** `decisions`/`risks`/`meeting_minutes`-Tabellen; CRUD unter `/projects/{id}/decisions`, `/projects/{id}/risks`, `/projects/{id}/meeting-minutes` (Update/Delete unter `/projects/decisions/{id}` etc., analog zum bestehenden `/projects/comments/{id}`-Muster) in `backend/app/routers/communication.py`, jede Out-Response inkl. `tags`+`documents` über `entity_links.py`. `ProjectCommunicationTab` hat jetzt vier echte Sub-Bereiche (`DecisionList`/`RiskList`/`MeetingMinutesList`/Diskussionen) mit gemeinsamer Suche (Volltext) und Tag-Filter-Leiste über alle Bereiche hinweg, Anzahl je Sub-Tab als Badge. Anhänge/Tags laufen über dieselbe Phase-7-Infrastruktur (`api.uploadDocument`/`TagInput`). Verifiziert per Playwright: Anlegen mit Tag+Anhang, Status-Änderung, Suche filtert nach Sub-Bereich, Tag-Filter wirkt bereichsübergreifend, Löschen eines Risikos lässt angehängtes Dokument im Dokumente-Tab bestehen.
10. **Schritt 8b (Übersicht-Tab):** `ProjectOverviewTab` aggregiert ausschließlich bestehende Endpoints, kein neuer Backend-Endpoint (`GET /gap/{id}` für Ampel + Auslastung als Hochrechnung/Soll in %, `GET /projects/{id}/history` für "letzte Änderungen", `GET /projects/{id}/comments` für "letzte Notizen", `GET /projects/{id}/risks`+`/decisions` für "offene Aufgaben" — offene Risiken plus offene Entscheidungen, wie in Abschnitt 10 als MVP-Alias festgelegt). Neuer API-Client-Endpoint `getProjectGap`. Verifiziert per Playwright: Ampel/Projektleiter/offene Aufgaben (inkl. korrektem Ausschluss bereits entschiedener Einträge) werden korrekt angezeigt.
11. **Schritt 9 (Controlling-Erweiterung: Forecast/Auslastung/KPIs/Reporting):** **Forecast** ist reines View-Reshuffle (`frontend/src/views/Forecast.tsx`, wrappt das bestehende `GET /forecast`). **Auslastung** ist eine neue Aggregation ohne neue Tabelle: `GET /team/utilization` (`backend/app/routers/team.py::compute_utilization`) berechnet je Teammitglied `kapazitaet_fte` (`wochenstunden / 40`, referenziert auf die bestehende Konvention aus `TeamMember`/`Assignment`) und `zugeordnet_fte` (Summe der `Assignment.fte`), daraus `auslastung_pct`. **KPIs** (`GET /kpis`, `backend/app/routers/kpis.py`) aggregiert Projektstatus-Verteilung (aus `gap_analysis.project_gap`), Ø Auslastung (wiederverwendet `compute_utilization`) sowie offene Risiken/Entscheidungen portfolioweit (dieselbe Zähllogik wie im Übersicht-Tab, jetzt über alle Projekte statt nur eines). **Reporting** (`frontend/src/views/Reporting.tsx`) ist MVP-mäßig ein rein clientseitiger CSV-Export (Blob/Object-URL) der Gap-/Forecast-/Auslastungs-/KPI-Daten, kein neuer Backend-Endpoint. Alle vier neuen Views sind unter `/forecast`, `/auslastung`, `/kpis`, `/reporting` in der Controlling-Nav-Gruppe verlinkt. Verifiziert per Playwright: Auslastungsberechnung stimmt (40 Wochenstunden = 1.0 FTE Kapazität, 0.6 FTE Zuordnung = 60 %), KPI-Zahlen konsistent zu Einzel-Endpoints, CSV-Download funktioniert.
12. **Schritt 10 (Aufgaben-Datenmodell):** `tasks`-Tabelle (`id, project_id, titel,
    beschreibung, status [offen/in_bearbeitung/erledigt], zustaendig, faellig_am,
    erstellt_am, aktualisiert_am`), CRUD unter `/projects/{id}/tasks` und
    `/projects/tasks/{id}` in `backend/app/routers/communication.py` (exakt das
    `Risk`-Muster kopiert), `entity_type="task"` im `entity_links.py`-Vokabular aktiviert.
    `ProjectCommunicationTab` hat jetzt einen fünften Sub-Bereich "Aufgaben"
    (`TaskList.tsx`, Vorbild `RiskList.tsx`) mit Tags/Anhängen über dieselbe
    Dokumentenablage-Infrastruktur. Löst den MVP-Alias aus Schritt 8b ab: der
    Übersicht-Tab zeigt unter "Offene Aufgaben" jetzt drei erkennbare Gruppen (☑ Aufgabe,
    ⚠ Risiko, ❓ Entscheidung) statt nur zwei; `KpiSummary` hat ein neues Feld
    `offene_aufgaben_gesamt`, `Kpis.tsx` eine neue Kachel dafür. `delete_project` räumt
    `Task`-Zeilen und ihre `TagLink`/`DocumentLink`-Verknüpfungen mit auf. Verifiziert per
    Playwright: Aufgabe mit Tag+Anhang anlegen, Status ändern, Anzeige auf Übersicht-Tab
    und in KPIs, keine Regressionen auf den bestehenden Tabs/Views.

13. **Phase 13 (Technisches Fundament, Kapazitätsplaner-v2-Zielarchitektur):** Alembic
    eingeführt (`backend/alembic/`) — Baseline-Migration `0001` bildet exakt das Schema ab,
    das vorher per `create_all()`+ad-hoc-`ALTER TABLE` in `main.py` erzeugt wurde; Folge-
    Migration `0002` ergänzt `tag_categories` und `entity_relations`. `backend/app/
    db_bootstrap.py` entscheidet beim App-Start automatisch zwischen "frische DB" (`alembic
    upgrade head` führt beide Migrationen real aus) und "bestehende, bereits befüllte DB"
    (einmaliges `alembic stamp 0001`, danach `upgrade head` nur für `0002` ff.) — verifiziert
    gegen eine simulierte Alt-DB mit Bestandsdaten (Daten blieben erhalten, kein Datenverlust).
    Neue Modelle: `TagCategory` (`tags.category_id` nullable FK, bestehende Tags bleiben ohne
    Kategorie gültig) und `EntityRelation` (gerichtete, typisierte Beziehung zwischen zwei
    beliebigen Entitäten, z.B. `decision` `resulted_in` `task` — folgt exakt dem bestehenden
    `TagLink`/`DocumentLink`-Muster aus Abschnitt 6a). Neue Endpunkte: `GET/POST
    /tag-categories`, `PATCH /tags/{id}`, `POST/GET/DELETE /entity-relations` (`backend/app/
    routers/documents.py` bzw. neuer Router `backend/app/routers/knowledge.py`); Helper
    `entity_links.create_relation`/`relations_for`/`delete_relations_for_entity`. Vokabular
    (`entity_type`, neu `relation_type`) zentral in `schemas.py` (`EntityType`/`RelationType`)
    statt eines separaten Moduls, da `EntityType` dort bereits die etablierte Konvention war.
    Verifiziert per curl gegen laufenden Server: Tag-Kategorie anlegen, Tag zuordnen, Relation
    zwischen Decision und Task anlegen/auflisten (auch von der Zielseite aus)/löschen,
    Duplikat-Konflikt (409) auf Kategorienamen, bestehende Endpunkte (`/projects`, `/gap`,
    `/tags`) weiterhin unverändert funktionsfähig. Kein Frontend-Umbau (siehe Abschnitt 12,
    "Phase 13 in diesem Durchgang"). Details zur Zielarchitektur und den Folgephasen siehe
    Abschnitt 12.

14. **Phase 14 (Personen, Organisation & Permissions, Kapazitätsplaner-v2-Zielarchitektur):**
    Migration `0003` (additiv, keine destruktive Änderung, siehe CONCEPT.md Abschnitt 12.3
    Frage 4). Neue Modelle: `Person` (kein Auth/Login, `source` ∈ {`LOCAL`,
    `ENTERPRISE_PLATFORM`}), `ResourceProfile` (höchstens eines je Person, macht sie
    kapazitätsplanbar), `ProjectRole`/`ProjectMembership` (Person ↔ Projekt mit Rolle,
    `unique(project_id, person_id)`), `Permission`/`AppRole`/`RolePermission` (App-Rolle
    bündelt Permissions, kein Auth-System im Repo — reine Vorbereitung für Phase 25/
    Enterprise-Integration). `Permission` wird per Migration mit dem Grundvokabular aus
    Master-MD Abschnitt 31 geseedet (`PROJECT_CREATE`, `PROJECT_EDIT`, `PLANNING_EDIT`,
    `CAPACITY_EDIT`, `TEAM_MANAGE`, `PERSON_MANAGE`, `TAG_MANAGE`, `TAXONOMY_MANAGE`,
    `TASK_MANAGE`, `DECISION_MANAGE`, `BLOCKER_MANAGE`, `ADMIN_ACCESS`) — keine Default-
    App-Rollen, da niemandem etwas zugewiesen werden kann. Additive Bridge-Spalten:
    `team_members.person_id`, `projects.projektleiter_person_id` (Freitextfelder
    `TeamMember.name`/`Project.projektleiter` bleiben unverändert bestehen). `teams` bekommt
    `external_id`/`source`/`active` (Master-MD Abschnitt 29).
    **Best-Effort-Datenmigration** (Teil derselben Alembic-Revision, läuft einmalig beim
    Hochziehen auf `0003`): für jedes bestehende `TeamMember` wird eine `Person`-Zeile
    angelegt und `person_id` verknüpft (`display_name` = `TeamMember.name`, `source=LOCAL`);
    für jedes `Project.projektleiter` (Freitext) wird `projektleiter_person_id` gesetzt, wenn
    genau eine Person mit exakt (case-insensitive, getrimmt) demselben Namen existiert —
    mehrdeutige oder fehlende Treffer bleiben bewusst `NULL`, der Freitext bleibt in jedem
    Fall die verbindliche Anzeige. Neue Endpunkte (`backend/app/routers/people.py`):
    `GET/POST /people`, `PUT /people/{id}`, `GET/POST/PUT /people/{id}/resource-profile`,
    `GET/POST /project-roles`, `GET/POST /projects/{id}/memberships`,
    `DELETE /project-memberships/{id}`, `GET /permissions`, `GET/POST /app-roles`,
    `POST/DELETE /app-roles/{id}/permissions/{permission_id}`. `ProjectCreate`/`ProjectUpdate`/
    `ProjectSummary`/`ProjectDetail` um `projektleiter_person_id` ergänzt (additiv, bestehende
    Frontend-Konsumenten ignorieren das neue Feld). Verifiziert per curl gegen laufenden
    Server (Person/ResourceProfile/ProjectRole/ProjectMembership/AppRole-CRUD inkl. 409-
    Konflikte, Berechtigungszuweisung) und per simulierter Alt-DB (zwei TeamMember, ein exakt
    passender und ein nicht passender Projektleiter-Freitext) — Migration erhält Bestandsdaten,
    Best-Effort-Mapping traf korrekt/verweigerte korrekt bei Mehrdeutigkeit. Kein
    Frontend-Umbau. Details siehe Abschnitt 12.4 (Phase 14 als erledigt markiert).

15. **Phase 15 (Semantic Knowledge Foundation, Kapazitätsplaner-v2-Zielarchitektur):**
    `TagCategory`/`EntityRelation`/Entity-/Relation-Type-Vokabular wurden bereits in Phase 13
    geliefert (Master-MD listet sie in Abschnitt 60 sowohl unter Phase 13 als auch Phase 15 —
    keine Doppelarbeit). Neu in diesem Durchgang: **Tag-AI-Metadata** (Migration `0004`,
    additiv) — `Tag` um `description`, `color`, `active` (NOT NULL mit `server_default`, da
    bestehende Zeilen befüllt sind), `ai_relevant`, `ai_description`, `synonyms` erweitert
    (Master-MD Abschnitt 43). `synonyms` wird kommagetrennt gespeichert (kein Array-Typ in
    SQLite) und als `list[str]` über `TagOut`/`TagUpdate` exponiert; `PATCH /tags/{id}`
    unterstützt jetzt alle neuen Felder (vorher nur `category_id`). Und der **Knowledge Query
    Layer** (Master-MD Abschnitt 46, `backend/app/routers/knowledge.py` erweitert, neue
    Helper in `entity_links.py`: `entity_summary`, `list_entity_summaries`,
    `search_entities`, öffentliches `ENTITY_TYPES`-Vokabular): `GET /knowledge/entities`
    (alle Entitäten eines Typs, optional projektgefiltert, inkl. Tags), `GET
    /knowledge/search` (Volltextsuche über Titel/Text aller taggable Entitäten **und** über
    Tag-Namen — ein Treffer auf einen Tag liefert die damit verknüpften Entitäten; noch kein
    Vector-RAG), `GET /knowledge/context` (Tags+Dokumente+Relationen einer einzelnen Entität
    an einem Ort — die "Wissenskarte", gedacht als Grundlage für spätere KI-
    Kontextassemblierung), `GET /knowledge/relations` (breitere Filterkombination als das
    Phase-13-`GET /entity-relations`, das genau eine Entität voraussetzt: `relation_type`/
    `entity_type`+`entity_id`/`project_id` beliebig kombinierbar), `GET
    /knowledge/project/{id}` (Wissenskontext-Aggregation: Entity-Counts je Typ, im Projekt
    tatsächlich verwendete Tags, alle Relationen, die Projekt-Entitäten betreffen).
    `/knowledge/tags` wurde bewusst **nicht** dupliziert — dafür existiert bereits `GET /tags`
    seit Phase 13. Verifiziert per curl: Tag-AI-Metadata setzen/lesen, Volltextsuche über
    Titel-Match und Tag-Match, Wissenskarte einer Entscheidung inkl. Relation zu einer
    Aufgabe, projektgefilterte Relations-Abfrage, Projekt-Aggregation (korrekte Counts/Tags/
    Relationen), 404 bei unbekannter Entität, 422 bei ungültigem `entity_type`. Migration
    gegen frische und simulierte bestehende DB (Tags ohne die neuen Spalten) getestet —
    bestehende Zeilen bekommen korrekte Defaults (`active=true`, `ai_relevant=false`), kein
    Datenverlust. Kein Frontend-Umbau. Details siehe Abschnitt 12.4 (Phase 15 als erledigt
    markiert).

16. **Phase 16 (Activity & Blocker Core, Kapazitätsplaner-v2-Zielarchitektur):** Migration
    `0005` (additiv). Neues Modell **`Blocker`** (`backend/app/models.py`, Master-MD Abschnitt
    37/38) — englische Feldnamen (`title`, `description`, `status`, `severity`,
    `active_since`, `caused_by_party`, `waiting_for_party`, `owner_person_id`,
    `owner_team_id`, `next_action`, `impact`) wie bei den Phase-14-Modellen: Zielarchitektur-
    native Entitäten übernehmen die Feldnamen 1:1 aus der Master-MD, während die aus dem
    Excel-Tool abgeleiteten Kommunikation-Tab-Modelle (Decision/Risk/Task/MeetingMinutes/
    Comment) bei ihrer bestehenden deutschen Namenskonvention bleiben — diese Konvention gilt
    ab jetzt projektweit. `caused_by_party`/`waiting_for_party` trennen bewusst "wer hat den
    Blocker verursacht" von "bei wem liegt aktuell der Ball" (`BlockerParty` = `INTERNAL`/
    `CUSTOMER`/`THIRD_PARTY`/`UNKNOWN`). CRUD unter `/projects/{id}/blockers` bzw.
    `/projects/blockers/{id}` (`backend/app/routers/communication.py`, exakt das
    Decision/Risk/Task-Muster kopiert), `owner_person_id`/`owner_team_id` werden gegen
    `Person`/`Team` validiert (404 bei unbekannter Referenz). Blocker ist taggbar,
    dokumentverknüpfbar, relationsfähig und im Knowledge Layer sichtbar (`EntityType` um
    `"blocker"` erweitert, `entity_links._ENTITY_REGISTRY`/`_ENTITY_LABEL_PREFIX` ergänzt).
    **Discussion Threading:** `Comment` bekommt ein nullable, selbstreferenzierendes
    `parent_id` (Master-MD Abschnitt 34) — `POST /projects/{id}/comments` validiert, dass
    `parent_id` zum selben Projekt gehört (sonst 422); löschen eines Elternkommentars nullt
    `parent_id` der Antworten statt den ganzen Thread zu löschen. **Decision Context:**
    `Decision` bekommt ein nullable `begruendung`-Feld, trennt WAS entschieden wurde
    (`beschreibung`) von WARUM (Master-MD Abschnitt 35: `decision_text` vs. `reason`).
    **Task Origins:** bewusst **keine** neue Spalte — die "fachliche Quelle" einer Aufgabe
    (aus Diskussion/Entscheidung/Meeting/Risiko/Blocker entstanden) wird über das bestehende
    `EntityRelation`-Modell ausgedrückt (z.B. `decision` `resulted_in` `task`, bereits in
    Phase 15 verifiziert) statt eine zweite, konkurrierende Source of Truth einzuführen.
    **Relations zwischen Activity-Objekten:** funktionieren jetzt vollständig, weil eine in
    Phase 13 offen gelassene Lücke geschlossen wurde (siehe Abschnitt 12.3 Frage 11):
    `entity_links.delete_relations_for_entity` wird jetzt in allen Lösch-Handlern
    (Decision/Risk/MeetingMinutes/Task/Comment/Blocker, einzeln und im Bulk-Delete von
    `delete_project`) aufgerufen, damit keine Waisen-Relationen auf gelöschte Entitäten
    zurückbleiben. **Activity Feed:** `GET /projects/{id}/activity` (`backend/app/routers/
    communication.py`) aggregiert Comment/Decision/Risk/MeetingMinutes/Task/Blocker
    chronologisch absteigend zu einem Feed (Master-MD Abschnitt 32) — reine Aggregation
    bestehender Endpunkte, keine neue Tabelle. Verifiziert per curl: Blocker-CRUD inkl.
    404-Validierung von `owner_person_id`/`owner_team_id`, Thread-Antwort erstellen und
    Cross-Projekt-`parent_id` ablehnen (422), Decision mit `begruendung`, Relation
    Task→`resolves`→Blocker im Knowledge-Context sichtbar und nach Task-Löschung korrekt
    entfernt, Activity Feed liefert alle sechs Entity-Typen chronologisch sortiert, Löschen
    eines Elternkommentars lässt die Antwort (mit genulltem `parent_id`) bestehen. Migration
    gegen frische und simulierte bestehende DB (mit Comments/Decisions ohne die neuen
    Spalten) getestet — kein Datenverlust. Kein Frontend-Umbau. Details siehe Abschnitt 12.4
    (Phase 16 als erledigt markiert).

17. **Phase 17 (Project Planning Core, Kapazitätsplaner-v2-Zielarchitektur):** Migration
    `0006` (additiv, zwei neue Tabellen `plan_phases`/`milestones`, keine Änderung an
    bestehenden Tabellen). Neue Modelle **`PlanPhase`** (`project_id`, `subproject_id`
    nullable, `phase_type` Freitext, `baseline_start`/`baseline_end`, `forecast_start`/
    `forecast_end`, `actual_start`/`actual_end`, `status`, `progress`, `owner_person_id`,
    `owner_team_id`) und **`Milestone`** (`project_id`, `subproject_id` nullable, `name`,
    `baseline_date`, `forecast_date`, `actual_date`, `status`, `owner_person_id`,
    `owner_team_id`) — Master-MD Abschnitt 8/9/10, englische Feldnamen wie die übrigen
    Zielarchitektur-nativen Entitäten. **Wichtig, wie in der Master-MD selbst gefordert
    (Abschnitt 8/9 "kein Big-Bang-Wechsel"):** Das bestehende Gantt-Grid
    (`GanttPhase`/`ProjectGanttPhase`, `routers/projects.py`) bleibt **unverändert** die
    Bedienoberfläche und einzige Quelle für die Monatsplanung im Frontend. `PlanPhase`/
    `Milestone` sind bewusst additiv und starten **leer** — es gibt in diesem Durchgang
    **keinen automatischen Sync** aus den bestehenden Gantt-Zellen, da dafür erst ein
    Migrationspfad (1-Zeichen-Phasencode+Monat → strukturierte Start-/End-Daten) definiert
    werden müsste, der laut CONCEPT.md Abschnitt 12.3 Frage 5 bewusst erst UI-getrieben in
    einer späteren Phase entschieden wird, nicht vorab. `PlanPhase`/`Milestone` sind ab sofort
    parallel nutzbar (z.B. für Projekte, die von Anfang an strukturiert geplant werden
    sollen), ohne dass eine zweite, konkurrierende Planungswahrheit für bestehende Projekte
    entsteht — bestehende Projekte haben schlicht keine `PlanPhase`/`Milestone`-Einträge, bis
    sie explizit angelegt werden. **Dependencies** zwischen PlanPhases/Milestones (auch
    projektübergreifend) laufen über das bestehende `EntityRelation`-Modell
    (`relation_type=depends_on`) — keine neue Modellierung, analog zur Task-Origins-
    Entscheidung aus Phase 16. Beide Entitäten sind taggbar/dokumentverknüpfbar und im
    Knowledge Layer sichtbar (`EntityType` um `"plan_phase"`/`"milestone"` erweitert,
    `entity_links`-Registry ergänzt — `/knowledge/*`-Endpunkte funktionieren automatisch ohne
    Codeänderung dort, da sie generisch über das Vokabular iterieren). CRUD unter
    `/projects/{id}/plan-phases` bzw. `/projects/{id}/milestones`
    (`backend/app/routers/planning.py`, neuer Router nach dem Decision/Risk/Task-Muster),
    `subproject_id` wird gegen das Projekt validiert (404 bei unbekanntem Teilprojekt, 422
    bei Teilprojekt eines anderen Projekts), `owner_person_id`/`owner_team_id` gegen
    Person/Team (404). Lösch-Kaskaden in `delete_project` (Bulk) und `delete_subproject`
    ergänzt (TagLink/DocumentLink/EntityRelation). Verifiziert per curl: PlanPhase/Milestone
    anlegen inkl. Owner/Tags, Cross-Projekt-`subproject_id` korrekt mit 422 abgelehnt,
    Relation Milestone→`depends_on`→PlanPhase im Knowledge-Context sichtbar und nach Löschung
    der PlanPhase korrekt entfernt, `/knowledge/project/{id}` zählt beide neuen Typen korrekt
    mit. Migration gegen frische DB und simulierte bestehende DB (mit befüllten
    `project_gantt_phases`) getestet — bestehende Gantt-Daten bleiben unverändert erhalten,
    kein Datenverlust, Downgrade/Upgrade-Round-Trip sauber. Bestehende Gantt-/GAP-/Activity-
    Feed-Endpunkte weiterhin regressionsfrei. Kein Frontend-Umbau. Details siehe Abschnitt
    12.4 (Phase 17 als erledigt markiert).

18. **Phase 18 (Baseline Management, Kapazitätsplaner-v2-Zielarchitektur):** Migration
    `0007` (additiv, zwei neue Tabellen `baseline_snapshots`/`baseline_entries`, keine
    Änderung an bestehenden Tabellen). Neue Modelle **`BaselineSnapshot`** (`project_id`,
    `name`, `created_at`, `created_by_person_id`) und **`BaselineEntry`** (`baseline_id`,
    `entity_type`, `entity_id`, `field`, `value`) — Master-MD Abschnitt 12, generisches
    Snapshot-Modell analog zu `TagLink`/`DocumentLink`/`EntityRelation`. Wichtiger
    Unterschied: `BaselineEntry.entity_id` ist bewusst **kein** Fremdschlüssel — ein Snapshot
    muss ein gültiger historischer Stand bleiben, auch wenn die referenzierte `PlanPhase`/
    `Milestone` später gelöscht wird (analog zu `PlanHistory`, das ebenfalls unabhängig vom
    Fortbestand der Quelle historisiert; verifiziert: nach Löschen einer `PlanPhase` blieben
    alle 11 zugehörigen `BaselineEntry`-Zeilen des Snapshots unverändert erhalten, nur
    `label`/`current_value` wurden korrekt `null`). `POST /projects/{id}/baselines`
    (`backend/app/routers/baselines.py`, neuer Router nach dem Planning/Communication-
    Muster) friert automatisch je `PlanPhase` des Projekts `phase_type, baseline_start,
    baseline_end, forecast_start, forecast_end, status, progress` und je `Milestone` `name,
    baseline_date, forecast_date, status` als `BaselineEntry`-Zeilen ein — bewusst nur
    `PlanPhase`/`Milestone` (Phase 17), keine strukturierte Baseline für das Legacy-Gantt-
    Grid (siehe Abschnitt 12.3 Frage 5). `GET /projects/{id}/baselines` (Liste),
    `GET`/`DELETE /projects/baselines/{id}` (Detail/Löschen). **Schedule-/Milestone-
    Deviations:** `GET /projects/baselines/{id}/deviations` vergleicht je eingefrorenem
    Datumsfeld den damaligen Wert mit dem aktuellen Live-Wert der referenzierten `PlanPhase`/
    `Milestone` (`entity_links.model_for`) und liefert die Differenz in Tagen
    (`delta_days`) — bewusst **kein** genereller Multi-Dimensions-GAP hier, das bleibt Phase
    21 (GAP Engine); dieser Endpoint deckt nur die in Phase 18 explizit genannten Termin-
    Abweichungen ab. `created_by_person_id` wird gegen `Person` validiert (404). Lösch-
    Kaskade in `delete_project` ergänzt (Entries vor Snapshots); bewusst **keine** Änderung
    an `delete_subproject`/`delete_plan_phase`/`delete_milestone` (Snapshots bleiben
    historischer Stand). Verifiziert per curl: Snapshot mit 11 Entries erstellt, danach
    Forecast einer `PlanPhase` (+8 Tage) und eines `Milestone` (+14 Tage) geändert —
    Deviations lieferten exakt `delta_days=8`/`14`, alle unveränderten Felder korrekt `0`;
    Snapshot überlebte das Löschen der zugehörigen `PlanPhase` vollständig; 404 bei
    unbekanntem `created_by_person_id`. Migration gegen frische DB und simulierte bestehende
    DB (mit befülltem `plan_phases`) getestet — kein Datenverlust, Downgrade/Upgrade-Round-
    Trip sauber. Bestehende Endpunkte (`/gap`, `/knowledge/*`, Activity Feed, Gantt)
    regressionsfrei. Kein Frontend-Umbau. Details siehe Abschnitt 12.4 (Phase 18 als erledigt
    markiert).

19. **Phase 19 (Capacity Planning Core, Kapazitätsplaner-v2-Zielarchitektur):** Migration
    `0008` (additiv, fünf neue Tabellen, keine Änderung an bestehenden Tabellen). Grundsatz
    **"Demand ≠ Assignment"** (Master-MD Abschnitt 14): Ressourcenbedarf wird zunächst
    unabhängig von konkreten Personen geplant, erst danach zugeordnet. Neue Modelle:
    **`ResourceRole`** (rollenbasierter Bedarf, z.B. Consulting/Development), **`Skill`** +
    **`PersonSkill`** (Rolle und Skill sind unterschiedliche Dimensionen, Master-MD Abschnitt
    16 — `level` bewusst Freitext, keine feste Werteliste vorgegeben), **`ResourceDemand`**
    (`project_id`, `plan_phase_id` nullable, `resource_role_id`, `period` im gleichen
    `"Apr 26"`-Format wie `GanttPhase.monat`/`FtePlan.monat` — "Capacity Bucket = MONTH" laut
    Master-MD Abschnitt 17 —, `fte`, `commitment_level` ∈ {`FIX`,`TENTATIVE`,`SCENARIO`}) und
    **`ResourceAssignment`** (`resource_demand_id`, `person_id`, `fte` — ordnet einen
    `ResourceDemand` konkreten Personen zu). **Bewusste Abgrenzung vom bestehenden
    `Assignment`-Modell** (`TeamMember`↔`Project`, direkter FTE-Wert, `routers/team.py`):
    keine Migration, keine Bridge, beide Systeme laufen komplett parallel — das ist exakt der
    geforderte Grundsatz, nicht ein Versehen. `ResourceRole`/`Skill`/`ResourceDemand`/
    `ResourceAssignment` sind bewusst **nicht** in `schemas.EntityType`/`entity_links`-Registry
    aufgenommen (keine Tag-/Relation-/Knowledge-Layer-Anbindung in diesem Durchgang) — anders
    als `PlanPhase`/`Milestone`/`Blocker` fehlt `ResourceDemand` ein natürliches
    Text-Label-Feld für das bestehende Registry-Muster, und es ist nicht Teil der expliziten
    Phase-19-Checkliste der Master-MD (analog zu `Team`, ebenfalls nicht im Vokabular). Neuer
    Router `backend/app/routers/capacity.py`: `GET/POST /resource-roles`, `GET/POST /skills`
    (je 409 bei Namens-Duplikat), `GET/POST /people/{id}/skills` + `DELETE
    /person-skills/{id}` (409 bei Duplikat), `GET/POST /projects/{id}/resource-demands` +
    `PUT/DELETE /projects/resource-demands/{id}` (`plan_phase_id` wird gegen das Projekt
    validiert, 404/422 analog `planning.py`), `GET/POST /resource-demands/{id}/assignments` +
    `DELETE /resource-assignments/{id}` (409 bei Duplikat-Zuordnung). `ResourceDemandOut`
    liefert zusätzlich `assigned_fte` (reine Summe der zugehörigen `ResourceAssignment.fte` —
    keine GAP-Berechnung, das bleibt Phase 21). Lösch-Kaskade in `delete_project` ergänzt
    (Assignments vor Demands); `ResourceRole`/`Skill`/`PersonSkill` sind projektunabhängige
    Stammdaten und bleiben beim Projekt-Löschen unangetastet (verifiziert). Verifiziert per
    curl: exakt das Master-MD-Beispiel nachgestellt (Consulting-Bedarf Oktober 0,8 FTE, Person
    A 0,5 + Person B 0,2 zugeordnet → `assigned_fte=0.7`), Namens-/Zuordnungs-Duplikate (409),
    unbekannte Rolle/Person/Skill (404), projektübergreifende `plan_phase_id` korrekt mit 422
    abgelehnt, Lösch-Kaskaden (Demand→Assignments, Projekt→Demands, Stammdaten bleiben
    bestehen). Migration gegen frische DB und simulierte bestehende DB (mit befülltem
    `plan_phases`) getestet — kein Datenverlust, Downgrade/Upgrade-Round-Trip sauber.
    Bestehende Endpunkte (`/team`, `/gap`, `/knowledge/*`, Activity Feed, `/people`)
    regressionsfrei. Kein Frontend-Umbau. Details siehe Abschnitt 12.4 (Phase 19 als erledigt
    markiert).

20. **Phase 20 (Real Capacity, Kapazitätsplaner-v2-Zielarchitektur):** Migration `0009`
    (additiv, fünf neue Tabellen, keine Änderung an bestehenden Tabellen). Grundformel
    (Master-MD Abschnitt 20): **Nominal Capacity − Holiday − Absence − Internal Allocation =
    Available Capacity**. Neue Modelle: **`CapacityCalendar`** (benannter Feiertagskalender,
    z.B. "Deutschland"), **`Holiday`** (Datum + Name je Kalender, `unique(calendar, date)`),
    **`WorkingTime`** (nominale Wochenstunden einer Person je Gültigkeitszeitraum
    `valid_from`/`valid_to` inkl. zugeordnetem Kalender — echte Zeitreihe, ergänzt
    `ResourceProfile.weekly_hours` aus Phase 14 additiv, keine Synchronisierung, gleiches
    Nicht-Sync-Prinzip wie bei `GanttPhase`/`PlanPhase`), **`Absence`** (Zeitraum +
    `absence_type`, Freitext wie `Blocker.severity`) und **`InternalAllocation`** (`period`
    im `"Apr 26"`-Format wie `ResourceDemand.period`, `fte`). `VOLLZEIT_WOCHENSTUNDEN` (bisher
    lokal in `routers/team.py`) nach `backend/app/constants.py` verschoben — einzige Quelle
    für die "40 Wochenstunden = 1.0 FTE"-Referenz, jetzt von `team.py` und dem neuen
    `real_capacity.py` gemeinsam genutzt. Neuer Helper `constants.parse_period()` kehrt
    `berechne_monate()` um (`"Apr 26"` → `(2026, 4)`), für die Kalendergrenzen-Bestimmung
    benötigt. Neuer Router `backend/app/routers/real_capacity.py`: CRUD für alle fünf Modelle
    (`/capacity-calendars`, `/capacity-calendars/{id}/holidays`, `/people/{id}/working-times`,
    `/people/{id}/absences`, `/people/{id}/internal-allocations`) sowie **`GET
    /people/{id}/capacity?period=...`**, das die Grundformel berechnet: Feiertage/
    Abwesenheiten werden über den Werktage-Anteil der Periode proportional in FTE
    umgerechnet (nur Wochentags-Termine zählen), `InternalAllocation` wird direkt in FTE
    abgezogen (bereits so gepflegt). Nominale Wochenstunden kommen aus dem für die Periode
    gültigen `WorkingTime`-Eintrag, ersatzweise aus `ResourceProfile.weekly_hours` (Phase 14)
    als MVP-Fallback ohne Kalenderbezug, falls kein `WorkingTime` gepflegt ist; 404, wenn
    keines von beidem existiert. Löschen eines `CapacityCalendar` löscht dessen `Holiday`-
    Zeilen und nullt `WorkingTime.capacity_calendar_id` (Zeitraum bleibt bestehen, verliert
    nur die Kalenderzuordnung). Personenbezogen und unabhängig von einem einzelnen Projekt —
    kein `delete_project`-Cascade nötig. Verifiziert per curl mit einem an das Master-MD-
    Beispiel angelehnten Szenario (40h/Woche, 5 Urlaubstage + 1 Feiertag in unterschiedlichen
    Monaten, `InternalAllocation` 0,10 FTE): Rechenergebnisse manuell nachgerechnet und exakt
    bestätigt (z.B. Oktober 2026: 22 Werktage, 5 Urlaubstage → `absence_fte=0.2273`,
    `available_fte=0.6727`); ein Feiertag am Wochenende wurde korrekt **nicht** abgezogen, ein
    Feiertag an einem Werktag korrekt anteilig (`1/21≈0.0476`); `ResourceProfile`-Fallback für
    Personen ohne `WorkingTime` sowie 404 ohne jegliche Kapazitätsdaten getestet;
    Namens-/Datums-Duplikate (409). Migration gegen frische DB und simulierte bestehende DB
    (mit befülltem `persons`/`resource_profiles`) getestet — kein Datenverlust, Downgrade/
    Upgrade-Round-Trip sauber. Bestehende Endpunkte (`/team`, `/gap`, `/projects`,
    `/resource-roles`) regressionsfrei. Kein Frontend-Umbau. Details siehe Abschnitt 12.4
    (Phase 20 als erledigt markiert).

21. **Phase 21 (GAP Engine, Kapazitätsplaner-v2-Zielarchitektur):** **Keine neue Migration**
    — die GAP Engine ist bewusst rein berechnend (Master-MD Abschnitt 21: "kein rein
    Reporting-Feature", aber auch keine neue Persistenz) und verbindet Projektplanung
    (`PlanPhase`/`Milestone`, Phase 17), Kapazitätsplanung (`ResourceDemand`, Phase 19;
    Available Capacity, Phase 20) und Ist-Daten (Jira, bestehend) zu den sechs in Master-MD
    Abschnitt 22 definierten GAP-Arten — "Bestehende Soll-/Ist-Logik wird nicht entfernt,
    sondern integriert" wörtlich umgesetzt: `gap_analysis.project_gap()` (seit Phase 3
    unverändert) wird 1:1 wiederverwendet, nicht neu gebaut. Refactoring vorab:
    `VOLLZEIT_WOCHENSTUNDEN` (bisher lokal in `routers/team.py`) nach `constants.py`
    verschoben (einzige FTE-Referenzquelle); die Available-Capacity-Berechnung aus Phase 20
    wurde aus `routers/real_capacity.py` in ein neues gemeinsames Modul
    `backend/app/capacity_calc.py` extrahiert (`compute_person_capacity()`, analog zu
    `entity_links.py` als Cross-Router-Helfer), damit `routers/gap_engine.py` sie
    mitverwenden kann, ohne router-übergreifend zu importieren.
    - **Allocation Gap** (`fte − assigned_fte`): direkt als neues Feld in
      `ResourceDemandOut.allocation_gap` (kein neuer Endpoint nötig, reine
      Pydantic-Erweiterung, keine Migration).
    - **Capacity Gap** (`GET /gap-engine/capacity?period=&resource_role_id=`, Available
      Capacity minus Resource Demand): **portfolioweit** über alle kapazitätsrelevanten
      Personen berechnet, `resource_role_id` filtert nur die Bedarfsseite — es gibt **keine
      Person↔ResourceRole-Zuordnung** im Datenmodell (weder in der Master-MD noch bisher
      hier eingeführt), eine rollenscharfe Kapazitätsseite wäre nicht belastbar berechenbar;
      diese Einschränkung ist bewusst und dokumentiert, keine vergessene Anforderung.
    - **Effort Gap** (`GET /projects/{id}/gaps/effort`): reiner Wrapper um
      `gap_analysis.project_gap()`, unverändert.
    - **Schedule Gap** (`GET /projects/{id}/gaps/schedule`): **live**, nicht auf einen
      `BaselineSnapshot` angewiesen (ergänzt, ersetzt nicht, die Snapshot-basierten
      Deviations aus Phase 18) — je `PlanPhase`/`Milestone` sowohl "Baseline vs Forecast" als
      auch "Forecast vs Actual" in Tagen.
    - **Progress Gap** (`GET /projects/{id}/gaps/progress`): Expected Progress (zeitlicher
      Anteil zwischen Forecast-/Baseline-Start und -Ende bis heute, 0–100 % geclamped) minus
      `PlanPhase.progress`, in Prozentpunkten.
    - **Utilization Gap** (`GET /people/{id}/gaps/utilization?period=`): zugeordnetes FTE
      (`ResourceAssignment`, Phase 19) im Verhältnis zu Available Capacity (Phase 20) gegen
      eine feste Ziel-Auslastung von 100 % (keine konfigurierbare Ziel-Auslastung in diesem
      Durchgang).
    - **Drill-down** (Master-MD Abschnitt 21/25): einfache Form über
      `GET /projects/{id}/gaps`, das Effort-/Schedule-/Progress-Gap eines Projekts an einer
      Stelle bündelt; der volle hierarchische Portfolio→Team→Projekt→Phase-Drill-down
      (Abschnitt 52) bleibt bewusst Controlling (Phase 22/23), nicht Teil dieses Durchgangs.
    - **`GapSnapshot`-Entscheidung** (in Phase 13 offen gelassen, siehe Abschnitt 12.3 Frage
      11): bleibt dormant/ungenutzt. Die GAP Engine rechnet konsequent **live** — wie bereits
      `gap_analysis.py`, die Phase-18-Deviations und die Phase-19/20-Aggregationen —, keine
      historisierten Snapshots. Eine Reaktivierung von `GapSnapshot` für GAP-Trendverläufe
      über Zeit bleibt eine mögliche spätere Controlling-Erweiterung (Phase 23), nicht Teil
      der GAP Engine selbst.
    Verifiziert per curl an einem durchgängigen Szenario: Allocation Gap (0,8 FTE Bedarf, 0,5
    zugeordnet → `allocation_gap=0.3`), Capacity Gap (0,8 FTE Bedarf ggü. 1,0 FTE verfügbarer
    Kapazität → `capacity_gap_fte=0.2`, mit und ohne `resource_role_id`-Filter identisch, wie
    erwartet), Utilization Gap (0,5/1,0 = 50 %, Ziel 100 % → `utilization_gap_pp=-50.0`),
    Schedule Gap (PlanPhase `baseline_end`→`forecast_end` +8 Tage, Milestone
    `baseline_date`→`forecast_date` +14 Tage, `forecast_vs_actual_days` korrekt berechnet),
    Progress Gap (heute vor Forecast-Start → `expected=0`, `actual=30` → `+30pp`), Effort-Gap-
    Wrapper und Bündel-Endpoint liefern konsistente Werte, 404 bei unbekanntem Projekt/Person.
    Regressionscheck: `/gap` (Legacy, unverändert), `/people/{id}/capacity` (nach Extraktion
    nach `capacity_calc.py` weiterhin identisches Ergebnis), `/team/utilization` (nach
    `VOLLZEIT_WOCHENSTUNDEN`-Verschiebung weiterhin korrekt) — alle regressionsfrei. Kein
    Frontend-Umbau. Details siehe Abschnitt 12.4 (Phase 21 als erledigt markiert).

22. **Phase 22 (Project Control & Health, Kapazitätsplaner-v2-Zielarchitektur):** Migration
    `0010` — genau eine neue Tabelle `health_thresholds` (konfigurierbare Schwellwerte,
    Master-MD Abschnitt 50: "Schwellwerte sollen konfigurierbar sein"), mit fünf
    Default-Zeilen geseedet (`schedule_days`, `capacity_fte`, `progress_pp`, `risk_score`,
    `blocker_severity`, je `yellow`/`red`). Mehrdimensionales Project Health (Master-MD
    Abschnitt 49) auf Basis der GAP-Engine (Phase 21) und bestehender Blocker-/Risk-/
    Milestone-Daten, rein berechnend bis auf die Schwellwert-Konfiguration selbst.
    Refactoring vorab: `_schedule_gap_entries`/`_progress_gap_entries` (bisher private
    Funktionen in `routers/gap_engine.py`) in ein neues gemeinsames Modul
    `backend/app/gap_calc.py` extrahiert (`schedule_gap_entries()`/`progress_gap_entries()`),
    analog zur `capacity_calc.py`-Extraktion in Phase 21 — `routers/gap_engine.py` und das
    neue `backend/app/health_calc.py` nutzen dieselbe Berechnung, ohne dass ein Router vom
    anderen importiert.
    - **Neun Health-Dimensionen** (`backend/app/health_calc.py`,
      `GET /projects/{id}/health`): `overall`, `schedule`, `capacity`, `effort`, `progress`,
      `risks`, `blockers`, `milestones`, `customer`, je als
      `{status: gruen|gelb|rot|grau, value, explanation}` — jede Bewertung ist damit direkt
      aus einer strukturierten Kennzahl erklärbar (Master-MD Abschnitt 49: "Jede Bewertung
      muss aus strukturierten Kennzahlen und fachlichen Daten erklärbar sein").
      `status="grau"` bedeutet "keine belastbare Datenbasis" (z.B. keine Milestones
      hinterlegt) und ist bewusst von `"gruen"` unterschieden — Abwesenheit von Daten ist
      keine positive Aussage. Bei Blocker/Risk/Customer ist die Abwesenheit *offener*
      Einträge dagegen genuin positiv, dort ist der leere Fall `"gruen"`.
      - **Schedule Health**: größter Verzug in Tagen über alle `PlanPhase`/`Milestone`
        (`forecast_vs_actual_days`, ersatzweise `baseline_vs_forecast_days`, aus
        `gap_calc.schedule_gap_entries()`) gegen `schedule_days`-Schwelle.
      - **Capacity Health**: `ResourceDemand` vs. zugeordnetes FTE **des Projekts** für die
        aktuelle Periode (`constants.current_period()`, neuer Helper "'Apr 26'-Format für
        heute") gegen `capacity_fte`-Schwelle — bewusst projektscharf, im Unterschied zum
        portfolioweiten Capacity Gap aus Phase 21 (`GET /gap-engine/capacity`), da das
        Cockpit-Beispiel der Master-MD (Abschnitt 6) eine Projekt-Kapazitätszeile zeigt.
      - **Effort Health**: **keine neue Logik** — übernimmt `status`/`gap_pct` direkt aus
        `gap_analysis.project_gap()` (bestehend seit Phase 3), nicht neu bewertet und nicht
        an `HealthThreshold` angebunden (siehe `models.HealthThreshold`-Docstring: bewusst
        keine Parallel-Konfiguration für bereits produktiv genutzte Schwellen
        `GAP_SCHWELLE_GELB`/`GAP_SCHWELLE_ROT`).
      - **Progress Health**: größter Rückstand in Prozentpunkten über alle `PlanPhase`
        (`progress_gap_pp` aus `gap_calc.progress_gap_entries()`) gegen `progress_pp`-Schwelle.
      - **Risk Health**: höchster offener `Risk`-Score (`wahrscheinlichkeit`+`auswirkung`,
        je niedrig/mittel/hoch = 1/2/3, Range 2–6) gegen `risk_score`-Schwelle; keine offenen
        Risiken → `gruen`.
      - **Blocker Health**: höchste Severity-Stufe offener `Blocker`
        (niedrig/mittel/hoch/kritisch = 1–4) gegen `blocker_severity`-Schwelle; keine offenen
        Blocker → `gruen`.
      - **Milestone Health**: nutzt direkt `Milestone.status` (`verpasst`→rot,
        `gefaehrdet`→gelb, sonst grün) statt eigener Datumsberechnung — das Statusfeld trägt
        diese Semantik bereits (Phase 17); keine Milestones → `grau`.
      - **Customer Health**: Teilmenge der offenen Blocker mit
        `caused_by_party=="CUSTOMER"` oder `waiting_for_party=="CUSTOMER"` (Phase 16), gegen
        dieselbe `blocker_severity`-Schwelle wie Blocker Health (identischer Wertebereich,
        keine eigene Konfigurationszeile) — Kunde hat den Blocker verursacht oder der Ball
        liegt aktuell bei ihm.
      - **Overall Health**: worst-of über alle Dimensionen mit belastbarer Datenbasis
        (`grau` ausgeklammert; sind alle `grau`, ist auch Overall `grau`). Die Master-MD gibt
        keinen konkreten Aggregationsalgorithmus vor (nur die Erklärbarkeits-Anforderung
        oben) — worst-of ist die einfachste, deterministische, vollständig erklärbare Wahl;
        bewusste Scope-Entscheidung, analog zur portfolioweiten Vereinfachung beim Capacity
        Gap in Phase 21.
    - **Konfigurierbare Schwellwerte** (`GET /health-thresholds`,
      `PUT /health-thresholds/{metric}`): `HealthThreshold`-Tabelle, geseedet mit den
      Default-Werten aus dem Master-MD-Beispiel (Abschnitt 50: Schedule Gap +14 Tage → ROT,
      Capacity Gap -0,3 FTE → GELB, Progress Gap -20 PP → ROT — alle drei Beispielwerte
      liegen exakt auf den gewählten Default-Schwellen). 404 bei unbekannter Metrik.
    - **Project Control Cockpit** (`GET /projects/{id}/cockpit`, Master-MD Abschnitt 6):
      bündelt Health, Projektleiter, aktuelle Phase (`PlanPhase.status=="laufend"`,
      ersatzweise die Phase, deren Forecast-Zeitraum heute umfasst), voraussichtliches Ende
      (spätestes bekanntes Forecast-Datum über `PlanPhase`/`Milestone` — Näherung für
      "Forecast GoLive" aus dem Cockpit-Beispiel, da kein Feld einen bestimmten Milestone als
      GoLive markiert), Milestone-Liste, Projekt-Kapazität (wie Capacity Health), Blocker-
      Zusammenfassung nach `caused_by_party` (Kunde/Intern/Dritte/Unbekannt, wie im
      Cockpit-Beispiel "Kunde 2 / Intern 1"), offene/überfällige `Task`s sowie "Aktuelle
      Themen": alle Tags, die an irgendeiner Entität des Projekts hängen (`Blocker`/
      `PlanPhase`/`Milestone`/`Task`/`Risk`/`Decision`/`MeetingMinutes`/`Comment`), aggregiert
      über den bestehenden Knowledge Query Layer
      (`entity_links.list_entity_summaries()`, Phase 15) — keine neue Tag-Abfrage gebaut.
    Verifiziert per curl an einem am Master-MD-Cockpit-Beispiel orientierten Szenario
    ("Spedition Frankenfeld"): PlanPhase "Testing" mit 19 Tagen Forecast-vs-Actual-Verzug und
    Progress 10 % ggü. erwarteten 100 % → Schedule/Progress Health beide `rot`; Milestone
    "GoLive" `verpasst` → Milestone Health `rot`; Risk hoch/hoch (Score 6) → Risk Health
    `rot`; zwei offene Blocker (kritisch/Kunde, mittel/Intern) → Blocker und Customer Health
    beide `rot`; ResourceDemand 2,4 FTE ggü. 2,1 FTE zugeordnet → Capacity Health `gelb` mit
    `allocation_gap_fte=-0.3` — **exakt der Master-MD-Beispielwert** (Abschnitt 6); Overall
    Health korrekt `rot` (worst-of). Cockpit liefert `current_phase="Testing"`,
    `forecast_end`, Blocker-Aufschlüsselung `{customer:1, internal:1}`, Tasks
    `{open_total:1, overdue:1}` und Tags `["Kunde","Schnittstelle","Testing"]` (aggregiert aus
    den beiden Blockern). Schwellwert-Update per `PUT` verifiziert, 404 bei unbekannter
    Metrik/unbekanntem Projekt. Migration gegen frische und simulierte bestehende SQLite-DB
    getestet (Downgrade/Upgrade-Round-Trip sauber, `alembic check` ohne Drift, Seed-Zeilen
    nach Re-Upgrade korrekt wiederhergestellt). Regressionscheck: `/projects/{id}/gaps/
    schedule` und `/projects/{id}/gaps/progress` liefern nach der `gap_calc.py`-Extraktion
    weiterhin identische Werte, `/team`, `/knowledge/search`, `/projects/{id}/activity`,
    `/projects/{id}/resource-demands` (inkl. `allocation_gap`) unverändert funktionsfähig.
    Kein Frontend-Umbau. Details siehe Abschnitt 12.4 (Phase 22 als erledigt markiert).

23. **Phase 23 (Controlling & Capacity Intelligence, Kapazitätsplaner-v2-Zielarchitektur):**
    **Keine neue Migration** — wie die GAP Engine (Phase 21) ist auch dieser Durchgang rein
    berechnend: er aggregiert die bereits bestehenden, projekt-/personenscharfen GAP-/Health-/
    Capacity-Berechnungen aus Phase 19–22 **portfolioweit** über alle Projekte/Perioden/Rollen
    hinweg (Master-MD Abschnitt 23), ohne eine der zugrunde liegenden Berechnungen zu
    verändern. Neuer Router `routers/controlling.py` (Prefix `/controlling`). Zwei
    Refactorings vorab, im selben Muster wie `capacity_calc.py`/`gap_calc.py` aus Phase
    21/22: die inline-Berechnung aus `routers/gap_engine.py:get_capacity_gap` wurde zu
    `capacity_calc.compute_capacity_gap(db, period, resource_role_id=None)` extrahiert (die
    Capacity Heatmap braucht dieselbe Berechnung über mehrere Perioden hinweg), und die
    inline-Berechnung aus `routers/baselines.py:get_baseline_deviations` wurde in ein neues
    gemeinsames Modul `backend/app/baseline_calc.py` (`latest_snapshot()`/
    `compute_deviations()`) ausgelagert. Neuer Helper `constants.periods_from(period, count)`
    (analog `berechne_monate()`, aber ausgehend von einem bereits im "Apr 26"-Format
    vorliegenden Startwert) für die Heatmap. Alle Endpunkte iterieren über die bestehende
    Portfolio-Projektliste `gap_analysis.projekte_fuer_team(db, None)` (on_hold/archiviert
    ausgeblendet, abgeschlossen bleibt sichtbar) statt einen neuen Filter zu erfinden.
    - **Capacity Heatmap / Demand vs Capacity** (`GET /controlling/capacity-heatmap?period=&
      periods=6&resource_role_id=`): Matrix über `periods` Folgeperioden, je Periode
      `capacity_calc.compute_capacity_gap()` — liefert dasselbe Schema
      (`schemas.CapacityGapOut`) wie der bereits bestehende Einzelperioden-Endpoint aus
      Phase 21, nur als Liste über die Zeit.
    - **Allocation Gap** (`GET /controlling/allocation-gaps?period=`): alle
      `ResourceDemand`-Zeilen projektübergreifend für eine Periode, mit `assigned_fte`/
      `allocation_gap`.
    - **Schedule Gap** (`GET /controlling/schedule-gaps`) / **Progress Gap**
      (`GET /controlling/progress-gaps`): `gap_calc.schedule_gap_entries()`/
      `progress_gap_entries()` je Projekt, geflattet mit Projektkontext.
    - **Baseline Deviations** (`GET /controlling/baseline-deviations`): je Projekt der
      neueste `BaselineSnapshot` (`baseline_calc.latest_snapshot()`), dessen Deviations
      (`baseline_calc.compute_deviations()`), nur Einträge mit berechenbarem `delta_days`;
      Projekte ohne Snapshot werden sauber übersprungen.
    - **Portfolio Health** (`GET /controlling/portfolio-health`): `health_calc.
      compute_project_health()` je Projekt, liefert exakt dasselbe `ProjectHealthOut` wie
      `GET /projects/{id}/health` (Phase 22), hier als Liste über alle Projekte.
    - **Blocker Portfolio** (`GET /controlling/blockers?party=&severity=`) /
      **Milestone Portfolio** (`GET /controlling/milestones?status=`): offene Blocker bzw.
      alle Milestones projektübergreifend, mit optionalen Filtern. Bewusst **schlanke**
      Portfolio-Schemas (`BlockerPortfolioEntry`/`MilestonePortfolioEntry`) statt der
      volleren `BlockerOut`/`MilestoneOut` — vermeidet N+1-Tag-/Dokument-Abfragen bei einer
      projektübergreifenden Liste, analog zu `CockpitMilestoneEntry` aus Phase 22.
    - **Team-/Rollenanalyse** (`GET /controlling/roles?period=`): `ResourceDemand`/
      `ResourceAssignment` gruppiert nach `resource_role_id` über alle Projekte einer
      Periode.
    - **Bewusst nicht neu gebaut** (Scope-Entscheidungen, analog zu den in Phase 21/22
      dokumentierten Vereinfachungen): **Effort Gap** portfolioweit ist bereits vollständig
      durch das bestehende `GET /gap` (unverändert seit Phase 3) abgedeckt — kein
      `/controlling/effort-gaps`-Alias, um keine zweite Quelle für dieselbe Berechnung zu
      schaffen. Der **volle hierarchische Drill-down** (Master-MD Abschnitt 52,
      Portfolio→Team→Projekt→Phase) wird nicht als neuer Endpoint gebaut — die
      Zielobjekte jeder Drill-down-Ebene existieren bereits (`/projects/{id}/cockpit`,
      `/projects/{id}/gaps`, `/projects/{id}/health`, `/projects/{id}/resource-demands`),
      Phase 23 liefert nur die bis dahin fehlende Portfolio-Einstiegsebene
      (`/controlling/portfolio-health` u.a.); der Rest ist UI-Komposition, kein
      Backend-Neubau.
    Verifiziert per curl an einem Zwei-Projekte-Szenario ("Spedition Frankenfeld" mit
    verzögerter PlanPhase/verpasstem Milestone/kritischem Kunden-Blocker/Risiko/
    Ressourcenbedarf/Baseline-Snapshot wie in Phase 22, plus "Logistik Muster AG" als
    schlankes zweites Projekt mit gefährdetem Milestone, internem Blocker und unzugeordnetem
    Ressourcenbedarf): Capacity Heatmap für "Aug 26" liefert `demand_fte=3.4` (2,4 + 1,0 aus
    beiden Projekten), identisch zur Summe der Allocation-Gap-Liste; Schedule-/Progress-Gap-
    Portfolio-Listen liefern exakt dieselben Werte wie die bereits verifizierten
    `/projects/{id}/gaps/schedule`/`/progress`; Portfolio Health liefert für Projekt 1
    exakt denselben `overall`-Status wie `/projects/1/health` (Regressionsvergleich, beide
    "rot"); Rollenanalyse aggregiert korrekt über beide Projekte (`demand_fte=3.4`,
    `assigned_fte=2.1`, `gap_fte=-1.3`); Baseline-Deviations überspringt das Projekt ohne
    Snapshot sauber (kein 404/500); Blocker-/Milestone-Portfolio-Filter (`party`, `severity`,
    `status`) korrekt getestet; Jahresüberlauf in der Heatmap (Dez 26 → Jan 27) korrekt.
    Regressionscheck: `/gap-engine/capacity` (nach `capacity_calc`-Extraktion identisch),
    `/projects/{id}/baselines/.../deviations` (nach `baseline_calc`-Extraktion identisch),
    `/gap`, `/kpis`, `/team/utilization`, `/projects/{id}/cockpit` unverändert
    funktionsfähig. `alembic check` bestätigt keine Drift (keine Modelländerung in diesem
    Durchgang). Kein Frontend-Umbau. Details siehe Abschnitt 12.4 (Phase 23 als erledigt
    markiert).

24. **Phase 24 (Knowledge Experience, Kapazitätsplaner-v2-Zielarchitektur):** **Keine neue
    Migration** — baut ausschließlich auf den seit Phase 13/15 bestehenden Tabellen
    (`tags`, `tag_categories`, `tag_links`, `entity_relations`) auf und erweitert den
    Knowledge Query Layer aus Phase 15 (`entity_links.py`, `routers/knowledge.py`) um die in
    Master-MD Abschnitt 44/40/46 beschriebenen Zugriffsmuster:
    - **Tag-Dossiers & kombinierte Tags** (`GET /knowledge/tags/dossier?tags=&mode=and|or&
      project_id=`, neu `entity_links.entities_by_tags()`): ein einzelner Tag
      (`tags=Schnittstelle`) liefert das Dossier-Beispiel aus Abschnitt 44 (Anzahl je
      Entitätstyp + die Entitäten selbst), eine Kombination (`tags=Kunde,GoLive&mode=and`)
      liefert nur Entitäten, die **alle** angegebenen Tags tragen (`mode=or` = irgendeinen).
      `project_id` filtert zusätzlich auf ein Projekt.
    - **Related Entities** (`entity_links.related_entities()`, neues Feld `related` auf
      `GET /knowledge/context`): andere Entitäten mit den meisten gemeinsamen Tags, mit den
      konkreten geteilten Tag-Namen (`shared_tags`) als Begründung — bewusst reine
      Tag-Overlap-Ähnlichkeit statt einer Vector-/Embedding-Schicht, siehe Abschnitt 46
      ("noch kein Vector-RAG").
    - **Semantische Suche** (`entity_links.search_entities()` erweitert): `GET
      /knowledge/search` matcht jetzt zusätzlich gegen `Tag.synonyms` und `Tag.ai_description`
      (Abschnitt 43, z.B. Tag "GoLive" mit Synonymen "Produktivstart"/"Livegang"/"Rollout") -
      der `match`-Wert unterscheidet dabei `tag:<Name>` (direkter Namenstreffer) von
      `tag_semantisch:<Name>` (nur über Synonym/AI-Beschreibung gefunden), damit der Treffer
      erklärbar bleibt (Entwicklungsprinzip 12). Dieselbe Namens-/Synonym-Auflösung
      (`entity_links.resolve_tag()`) wird auch von den Tag-Dossiers genutzt - ein Dossier für
      `tags=Livegang` findet damit denselben Tag wie `tags=GoLive`.
    - **Activity Integration**: `plan_phase`/`milestone` fehlten bisher in der
      Activity-Feed-Zeitstempel-Registry aus Phase 16 (nur `comment`/`decision`/`risk`/
      `meeting_minutes`/`task`/`blocker`), obwohl beide seit Phase 17 Tags/Relationen tragen
      können - dadurch tauchten sie nie im Activity Feed und nie in der `activity`-Liste
      eines Tag-Dossiers auf. Behoben durch Verschieben der Registry von
      `routers/communication.py` nach `entity_links.py` (`ACTIVITY_ENTITY_TYPES`/
      `timestamp_for()`, jetzt inkl. `plan_phase`/`milestone`) - eine gemeinsame Zeitbasis
      für `GET /projects/{id}/activity` (Phase 16) und die neue `activity`-Liste im
      Tag-Dossier statt einer zweiten, separat zu pflegenden Kopie.
    - **Bewusst nicht neu gebaut**: keine Vector-/Embedding-Suche (Abschnitt 55/62.15 -
      KI-Readiness heißt strukturierte, semantisch beschriebene Daten, nicht frühzeitig
      Embeddings/RAG bauen); kein Admin-UI für Tags/TagCategories (das ist Phase 25); kein
      Frontend für Tag-Dossiers/Related Entities (wie Phase 13–23 bleibt dieser Durchgang
      Backend-only, siehe unten).
    Verifiziert per curl gegen eine frische, isolierte SQLite-Testdatenbank (nicht die
    Dev-Datenbank) mit einem Projekt, einer getaggten Notiz (`#Kunde #Schnittstelle`), einer
    getaggten Aufgabe (`#Schnittstelle #GoLive`) und einem getaggten Milestone (`#Kunde
    #GoLive`), sowie Tag "GoLive" mit Synonymen "Produktivstart"/"Livegang"/"Rollout": Dossier
    `tags=Kunde,GoLive&mode=or` liefert alle drei Entitäten (`counts` `comment:1, task:1,
    milestone:1`), `mode=and` liefert korrekt nur den Milestone; Dossier per Synonym
    (`tags=Livegang`) findet dieselben Treffer wie `tags=GoLive`; `GET /knowledge/search?
    q=Produktivstart` liefert die Aufgabe/den Milestone mit `match="tag_semantisch:GoLive"`,
    während `q=GoLive` weiterhin `match="tag:GoLive"` liefert; `GET /knowledge/context` für
    die Aufgabe liefert `related` mit der Notiz (`shared_tags=["Schnittstelle"]`) und dem
    Milestone (`shared_tags=["GoLive"]`), zusätzlich zur unverändert funktionierenden
    `relations`-Liste (per `POST /entity-relations` angelegt); `GET /projects/{id}/activity`
    enthält jetzt den Milestone. Regressionscheck: reine Textsuche (`q=XML`), `GET
    /knowledge/relations`, `GET /knowledge/project/{id}`, `POST /entity-relations` unverändert
    funktionsfähig; zusätzlich per eigenständigem Python-Skript gegen eine In-Memory-SQLite-DB
    die AND/OR-/Projekt-Filter-/Synonym-Fallpfade von `entities_by_tags()` und
    `related_entities()` isoliert verifiziert (17 Einzelchecks). Kein Frontend-Umbau. Details
    siehe Abschnitt 12.4 (Phase 24 als erledigt markiert).
25. **Phase 25 (Administration UX, Kapazitätsplaner-v2-Zielarchitektur):** Eine globale
    Administrationsoberfläche bündelt Personen/Teams, Projekt- und App-Rollen inklusive
    Permission-Matrix, Resource Roles/Skills, Tags/Tag-Kategorien, Project-Health-
    Schwellwerte, Capacity-Kalender und Integrationsstatus. Sie verwendet direkt die APIs
    der Phasen 13–22; fehlende Update-Operationen wurden additiv ergänzt. Extern verwaltete
    Personen bleiben read-only, Jira/Tempo-Credentials bleiben in der Laufzeitumgebung.
    Details siehe Abschnitt 12.4 (Phase 25 als erledigt markiert).

Noch nicht umgesetzt: Restaufwand-basierte Hochrechnung (Variante 2), Portal-SSO, der Excel-Migrationslauf für Bestandsdaten, der offene Jira-Issues-Endpoint für den Jira-Tab, sowie der spätere Portfolio-PPTX-Export für Reporting. Siehe Abschnitt 10 für offene Entscheidungen. Damit sind alle in Abschnitt 9 geplanten Phasen inkl. Schritt 10 (Aufgaben-Datenmodell) sowie Phase 13–25 der Zielarchitektur (Abschnitt 12) umgesetzt.

---

## 12. Zielarchitektur v2

Ausgangspunkt dieses Abschnitts ist die vom Auftraggeber vorgegebene Master-Architektur
("Kapazitätsplaner v2 – Gesamtarchitektur- und Umsetzungsplan"). Sie beschreibt die
Weiterentwicklung dieses Tools zu einem integrierten Project-Control- und
Capacity-Management-System: Projektplanung, Kapazitätsplanung, eine Plan-/Ist-/
Forecast-GAP-Engine, Projektsteuerung (Aktivität/Blocker/Entscheidungen), eine semantische
Wissensbasis (Tags/Relationen als Knowledge Graph) und Controlling — alle auf denselben
fachlichen Daten, mit einem später folgenden KI-Agenten als letzter Ausbaustufe. Leitidee:

> Planen → Ressourcen absichern → Durchführung verfolgen → Abweichungen erkennen → Ursachen
> verstehen → Maßnahmen ableiten.

Die Master-MD selbst schreibt vor, nicht blind alle neuen Modelle zu implementieren, sondern
zuerst den bestehenden Code gegen dieses Zielbild zu spiegeln und das Ergebnis hier zu
dokumentieren — genau das leistet dieser Abschnitt, bevor mit Phase 13 begonnen wird.

### 12.1 Migrationsstrategie (Alembic)

Siehe Abschnitt 11 Punkt 13 für den vollständigen Umsetzungsstand. Kurzfassung der Strategie:

- Jede künftige Schemaänderung ist eine Alembic-Revision unter `backend/alembic/versions/` —
  **keine neuen ad-hoc `ALTER TABLE`-Anweisungen mehr** in `main.py` oder anderswo.
- `backend/alembic/env.py` liest `DATABASE_URL` aus `app.database` (keine doppelt gepflegte
  Connection-String-Quelle) und nutzt `Base.metadata` für Autogenerate — neue Modelle in
  `models.py` werden per `alembic revision --autogenerate -m "..."` erfasst.
- Baseline (`0001`) entspricht exakt dem Schema, das vor Phase 13 per `create_all()` +
  ad-hoc-`ALTER TABLE` erzeugt wurde (SQLite-Dev wie Postgres-Prod).
- `db_bootstrap.run_migrations()` (aufgerufen beim App-Start in `main.py`) unterscheidet drei
  Fälle: (a) DB kennt bereits `alembic_version` → normales `upgrade head`; (b) frische DB
  (weder `alembic_version` noch `projects` vorhanden) → `upgrade head` führt die Baseline real
  aus; (c) bestehende, bereits befüllte DB ohne `alembic_version` (heutiger Dev-/Prod-Stand)
  → einmaliges `stamp 0001`, danach `upgrade head` nur für die Migrationen ab `0002`. Damit
  bleibt der bisherige Betriebs-Workflow (`uvicorn app.main:app`, Docker-`CMD` unverändert)
  erhalten — die Migration läuft beim Start, wie zuvor `create_all()`.
- SQLite-Besonderheit: `ALTER TABLE ... ADD CONSTRAINT` wird von SQLite nicht unterstützt;
  entsprechende Migrationsschritte (z.B. `tags.category_id`-FK in `0002`) laufen über Alembics
  `batch_alter_table` (Copy-Move-Strategie), was unter Postgres identisch als normales
  `ALTER TABLE` funktioniert.

### 12.2 Mapping bestehender Code → Zielarchitektur (A/B/C/D)

Klassifikation nach dem A/B/C/D-Schema der Master-MD, hier konkret auf tatsächliche
Klassen/Dateien dieses Repos bezogen (nicht nur abstrakt aus der Master-MD übernommen):

**A — unverändert nutzbar:**
`Tag`/`TagLink`, `Document`/`DocumentLink` (bereits das generische
`entity_type`+`entity_id`-Verknüpfungsmuster, das die Master-MD für `EntityRelation`
vorschlägt — siehe Abschnitt 6a), `PlanHistory` (Audit-Trail), `Comment`, `Decision`, `Risk`,
`Task`, `MeetingMinutes`, die komplette Jira/Tempo-Integration (`jira_client.py`,
`tempo_client.py`, `jira_sync.py`, `JiraWorklogCache`).

**B — vorhanden, aber erweiterungsbedürftig (spätere Phasen, nicht Teil dieses Durchgangs):**
- `GanttPhase`/`ProjectGanttPhase` (1-Zeichen-Phasencode, reine Monatszellen) → `PlanPhase`
  existiert seit Phase 17 als strukturiertes Modell daneben (additiv, siehe Abschnitt 11
  Punkt 17), aber noch **ohne** Sync: Das Gantt-Grid bleibt weiterhin unverändert die
  Bedienoberfläche und einzige Quelle für bestehende Projekte; `PlanPhase` wird erst in einer
  späteren, UI-getriebenen Phase schrittweise zur befüllten fachlichen Source of Truth (siehe
  Frage 5 unten) — bewusst kein Sync-Automatismus ohne definierten Migrationspfad.
- `backend/app/gap_analysis.py` (Soll/Ist/Gap + Trendfortschreibung) → Basis für die künftige
  GAP-Engine mit getrennten GAP-Arten (Phase 21). Die heutige Logik wird nicht ersetzt,
  sondern als ein Fall (Capacity-/Effort-Gap) in das größere Modell integriert.
- `Assignment`/`FtePlan`/`ProjectFtePlan` (FTE direkt als Zahl, kein getrenntes
  Bedarf/Zuordnung-Konzept) → Basis für `ResourceDemand` + Assignment-Trennung (Phase 19).
- `Team`/`TeamMember` (siehe unten, Frage 4) → `Person`+`ResourceProfile` existieren seit
  Phase 14, `TeamMember` bleibt aber vorerst die für Assignment/Utilization maßgebliche
  Kapazitätsressource (additiv verknüpft über `person_id`, kein Ersatz).

**C — neu, davon umgesetzt:**
Phase 13: `TagCategory`, `EntityRelation`, Entity-/Relation-Type-Vokabular (siehe Abschnitt 11
Punkt 13). Phase 14: `Person`, `ResourceProfile`, `ProjectRole`, `ProjectMembership`,
`Permission`, `AppRole`, `RolePermission` (siehe Abschnitt 11 Punkt 14). Phase 15: Tag-AI-
Metadata (`description`/`color`/`active`/`ai_relevant`/`ai_description`/`synonyms`),
Knowledge Query Layer (`/knowledge/*`, siehe Abschnitt 11 Punkt 15). Phase 16: `Blocker`
(`caused_by_party`/`waiting_for_party`), `Comment.parent_id` (Discussion Threading),
`Decision.begruendung` (Decision Context), Activity Feed (siehe Abschnitt 11 Punkt 16). Phase
17: `PlanPhase`, `Milestone`, Dependencies über `EntityRelation` (siehe Abschnitt 11 Punkt
17). Phase 18: `BaselineSnapshot`, `BaselineEntry`, Schedule-/Milestone-Deviations (siehe
Abschnitt 11 Punkt 18). Phase 19: `ResourceRole`, `Skill`, `PersonSkill`, `ResourceDemand`,
`ResourceAssignment`, Commitment-Level (siehe Abschnitt 11 Punkt 19). Phase 20:
`CapacityCalendar`, `Holiday`, `WorkingTime`, `Absence`, `InternalAllocation`, Available-
Capacity-Berechnung (siehe Abschnitt 11 Punkt 20). Phase 21: GAP-Engine
(`routers/gap_engine.py`) mit Capacity-, Effort- (Wiederverwendung von `gap_analysis.py`),
Schedule-, Progress- und Utilization-Gap sowie einem Bündel-Endpoint `/projects/{id}/gaps`
(siehe Abschnitt 11 Punkt 21). Phase 22: `HealthThreshold`, mehrdimensionales Project Health
(`GET /projects/{id}/health`) mit neun Dimensionen, konfigurierbare Schwellwerte
(`/health-thresholds`), Project Control Cockpit (`GET /projects/{id}/cockpit`, siehe
Abschnitt 11 Punkt 22). Phase 23: `routers/controlling.py` mit Capacity Heatmap,
Allocation-/Schedule-/Progress-Gap und Baseline Deviations portfolioweit, Portfolio Health,
Blocker-/Milestone-Portfolio, Team-/Rollenanalyse (siehe Abschnitt 11 Punkt 23). Alle übrigen
aus der Master-MD (Administration-UI) bleiben für die jeweils zugeordnete spätere Phase
vorgemerkt (siehe Phasenplan unten) — **noch nicht umgesetzt**.

**D — bewusst später (unverändert aus der Master-MD):**
KI Project Agent, Vector-/Embedding-Layer, Enterprise-SSO, vollständiger Enterprise-Sync,
What-if-/Szenarioplanung, automatische Blocker-Erstellung, KI-basierte Restaufwandsschätzung,
automatische Ressourcenoptimierung.

### 12.3 Antworten auf die Prüffragen (Master-MD, "Nächster konkreter Schritt")

1. **Unverändert bleibende Modelle:** siehe A oben.
2. **Erweiterungsbedürftige Modelle:** siehe B oben.
3. **Tatsächlich notwendige neue Modelle (Phase 13):** `TagCategory`, `EntityRelation` — alle
   übrigen neuen Modelle der Master-MD werden erst in ihrer jeweiligen Phase notwendig, nicht
   vorab angelegt (Prinzip "keine destruktive/vorgezogene Migration ohne konkreten Bedarf").
4. **`TeamMember` → `Person` + `ResourceProfile`:** ✅ Umgesetzt in Phase 14 (Migration
   `0003`). `TeamMember` vermischte drei Konzepte (Person, Jira-Identität,
   Kapazitätsressource) — aufgelöst über ein schlankes `Person`-Modell (`id`, `external_id`,
   `display_name`, `email`, `source` ∈ {`LOCAL`,`ENTERPRISE_PLATFORM`}, `active`) plus
   optionales `ResourceProfile` (`person_id` unique, `team_id`, `weekly_hours`,
   `capacity_relevant`, `active`). `TeamMember` bleibt bestehen (nicht gelöscht, solange
   Assignment/Jira-Sync/Auslastungsberechnung noch darauf referenzieren), bekommt aber ein
   nullable `person_id`-FK. Best-Effort-Migration: pro bestehendem `TeamMember` wird
   **automatisch eine `Person`-Zeile** angelegt (Name → `display_name`, `source=LOCAL`) und
   verknüpft — bewusst **kein** automatisch angelegtes `ResourceProfile`, damit
   `TeamMember.wochenstunden` (weiterhin die für Assignment/Utilization maßgebliche Kapazität)
   nicht unbeobachtet mit einem zweiten `weekly_hours`-Wert auseinanderlaufen kann;
   `ResourceProfile` wird erst bei Bedarf explizit angelegt (`POST
   /people/{id}/resource-profile`). `jira_account_id` bleibt vorerst an `TeamMember`.
5. **`GanttPhase` → `PlanPhase` ohne zwei Sources of Truth:** ✅ Modell seit Phase 17
   umgesetzt (Baseline/Forecast/Actual-Start/-Ende statt nur Monat+Code), **Sync/UI-Wechsel
   bewusst noch offen**. Das bestehende Gantt-Grid bleibt unverändert die Bedienoberfläche und
   einzige Quelle für bestehende Projekte; `PlanPhase` startet leer. Der noch offene Schritt
   (spätere Phase, UI-getrieben): entweder ein Migrationsskript, das bestehende
   `GanttPhase`/`ProjectGanttPhase`-Zellen einmalig in `PlanPhase`-Zeilen überführt (Monat+Code
   → Start-/Enddatum-Bereich je zusammenhängendem Block), oder ein Umbau der Planung-Tab-UI,
   die direkt gegen `PlanPhase` schreibt und `GanttPhase` nur noch als abgeleitete
   Zellen-Darstellung berechnet. Beides ist bewusst nicht Teil von Phase 17, um keinen
   Sync-Automatismus ohne definierten UI-Bedarf zu bauen (Prinzip: Komplexität nur dort
   hinzufügen, wo sie konkrete Projektsteuerung verbessert).
6. **Bestehende Soll-/Ist-GAP-Logik in die künftige GAP-Engine:** `gap_analysis.project_gap()`
   liefert bereits Soll/Ist/Gap/Hochrechnung je Projekt/Monat — das entspricht in der
   GAP-Engine-Terminologie der Master-MD im Kern dem Capacity-/Effort-Gap. Phase 21 kapselt
   diese Funktion unverändert als eine von mehreren GAP-Arten (Capacity/Allocation/Effort/
   Schedule/Progress/Utilization-Gap) hinter einer gemeinsamen Fassade, statt sie zu ersetzen.
7. **Weiterverwendbare Jira-Berechnungen:** `jira_sync.berechne_ist_fte` (Stunden→FTE-
   Umrechnung) ist die Actual-Effort-Quelle der Master-MD (Abschnitt 23) und bleibt 1:1
   erhalten — neue Ist-Dimensionen (Actual Start/End einer `PlanPhase`, Actual Date eines
   `Milestone`) ergänzen sie in späteren Phasen, ersetzen sie nicht.
8. **Migrationen Phase 13–21:** Phase 13 (dieser Durchgang) = `0001` Baseline, `0002`
   TagCategory/EntityRelation. Phase 14 (Person/ResourceProfile/ProjectRole/Permission) und
   Phase 17–21 (PlanPhase/Milestone/Baseline/ResourceDemand/CapacityCalendar/GAP-Engine)
   folgen als weitere, additive Alembic-Revisionen — jeweils mit nullable FKs und
   Best-Effort-Mapping bestehender Daten, keine destruktiven Migrationen (siehe
   Entwicklungsprinzip 20 der Master-MD).
9. **APIs, die kompatibel bleiben müssen:** alle bestehenden Endpunkte unter `/projects`,
   `/team`, `/gap`, `/forecast`, `/kpis`, `/jira`, `/documents`, `/tags` — Phase 13 ändert an
   keinem davon das Response-Schema, `GET /tags` liefert lediglich zusätzlich `category_id`.
10. **Wiederverwendbare UI-Komponenten:** `TagInput`, `AttachmentPicker`/`AttachmentList`,
    `HistoryTimeline`, `Tabs` — alle bleiben unverändert nutzbar; für spätere Phasen (z.B.
    Tag-Kategorie-Auswahl, Relation-Anzeige) sind sie die erwarteten Anknüpfungspunkte statt
    neuer Parallel-Komponenten.
11. **Technische Schulden vor neuen Features:** Alembic fehlend war die größte offene Schuld
    (Abschnitt 10) — mit Phase 13 behoben. Verbleibend, aber bewusst nicht Teil dieses
    Durchgangs: `GapSnapshot`-Modell existiert, wird aber nirgends beschrieben (weder
    Endpunkt noch Job) — Entscheidung für Phase 18/21, ob es reaktiviert oder durch die neue
    GAP-Engine ersetzt wird; `EntityRelation`/`TagCategory` sind in Phase 13 bewusst noch
    nicht in Lösch-Kaskaden (z.B. `delete_project`) verdrahtet, um den Durchgang minimal-
    invasiv zu halten — nachzuholen, sobald eine Entität mit Relationen tatsächlich löschbar
    sein muss.

### 12.4 Phasenplan 13–26 (Ausblick)

Phase 13–25 sind umgesetzt (siehe Abschnitt 11 Punkt 13/14/15/16/17/18/19/20/21/22/23/24
und die nachfolgende Phase-25-Entscheidung). Phase 26 bleibt Ausblick auf Basis der Master-MD:

| Phase | Titel | Kerninhalt |
|---|---|---|
| 13 | Technisches Fundament | ✅ Alembic, TagCategory, EntityRelation |
| 14 | Personen, Organisation & Permissions | ✅ Person, ResourceProfile, ProjectRole, ProjectMembership, Permission, AppRole |
| 15 | Semantic Knowledge Foundation | ✅ Tag-AI-Metadata, Knowledge Query Layer (`/knowledge/*`) |
| 16 | Activity & Blocker Core | ✅ Blocker (caused_by/waiting_for), Discussion Threading, Decision Context, Activity Feed |
| 17 | Project Planning Core | ✅ PlanPhase, Milestone, Dependencies (Gantt bleibt unverändert UI) |
| 18 | Baseline Management | ✅ BaselineSnapshot, BaselineEntry, Baseline vs Forecast, Deviations |
| 19 | Capacity Planning Core | ✅ ResourceRole, Skill, PersonSkill, ResourceDemand, ResourceAssignment, Commitment-Level |
| 20 | Real Capacity | ✅ CapacityCalendar, WorkingTime, Holiday, Absence, InternalAllocation, Available Capacity |
| 21 | GAP Engine | ✅ Capacity/Allocation/Effort/Schedule/Progress/Utilization-Gap, Bündel-Endpoint |
| 22 | Project Control & Health | ✅ mehrdimensionales Project Health, konfigurierbare Schwellwerte, Project Control Cockpit |
| 23 | Controlling & Capacity Intelligence | ✅ Capacity Heatmap, Portfolio Health, Blocker-/Milestone-Portfolio, Rollenanalyse |
| 24 | Knowledge Experience | ✅ Tag-Dossiers, kombinierte Tags, semantische Suche (Synonyme/AI-Beschreibung), Related Entities, Activity Integration |
| 25 | Administration UX | ✅ zentrale UI für Personen/Teams, Rollen/Permissions, Resource Roles/Skills, Tags/Taxonomie, Health-Schwellwerte, Capacity-Konfiguration und Integrationsstatus |
| 26 | KI-Readiness Review | Prüfung vor KI-Agent-Implementierung |

**Phase-25-Architekturentscheidung:** Die Administration ist eine eigene globale Route
`/administration` und bündelt vorhandene fachliche Sources of Truth, statt Stammdaten im
Frontend zu duplizieren. Lokale Personen können angelegt und aktiviert/deaktiviert werden;
Enterprise-Personen werden sichtbar als extern verwaltet und bleiben read-only. App-Rollen
nutzen die geseedeten Permissions als Capability-Matrix. Resource Roles, Skills, Tags,
Tag-Kategorien, Health-Schwellwerte und Capacity-Kalender schreiben direkt in die Modelle
der Phasen 13–22. Team-Kapazitätsressourcen bleiben über die bestehende Teamverwaltung
erreichbar, solange `TeamMember` und `Person + ResourceProfile` parallel existieren.
Jira/Tempo-Zugangsdaten werden aus Sicherheitsgründen weiterhin ausschließlich über
Umgebungsvariablen konfiguriert; die Administration zeigt nur den Verbindungsstatus.
Blocker-Severity und Risikolevel bleiben vorerst systemverwaltetes Fachvokabular: Eigene
Kategorie-Modelle werden nicht allein für eine UI erfunden, bevor ihr Domänenverhalten und
ihre Migration entschieden sind.

Details zu Vision, Gesamtmodell und Steuerungskreislauf siehe die Master-Architektur-MD
("Kapazitätsplaner v2 – Gesamtarchitektur- und Umsetzungsplan").

---

Details zu Aufbau und lokalem Betrieb siehe [`README.md`](README.md).
