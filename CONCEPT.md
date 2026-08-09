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
| `comments` | id, project_id, subproject_id, monat, phase_code, text, erstellt_am | Notizen/Diskussionen + Gantt-Zell-Kommentare |
| `plan_history` | id, project_id, subproject_id, bereich, monat, feld, alter_wert, neuer_wert, geaendert_am, kommentar_id, **batch_id** (neu, Revisionsgruppierung) | Änderungsprotokoll |
| `documents` | id, project_id, dateiname, speicherpfad, mimetype, groesse_bytes, hochgeladen_von, hochgeladen_am | neu — zentrale Dokumentenablage, siehe Abschnitt 6a |
| `document_links` | id, document_id, entity_type, entity_id, erstellt_am | neu — generische Verknüpfung Document ↔ comment/decision/risk/meeting_minutes |
| `tags` | id, name (unique, systemweit) | neu |
| `tag_links` | id, tag_id, entity_type, entity_id | neu — generische Verknüpfung Tag ↔ comment/decision/risk/meeting_minutes/document |
| `decisions` | id, project_id, titel, beschreibung, status, entschieden_von, entschieden_am, erstellt_am | neu (Kommunikation-Tab) |
| `risks` | id, project_id, titel, beschreibung, wahrscheinlichkeit, auswirkung, status, owner, faellig_am, erstellt_am, aktualisiert_am | neu (Kommunikation-Tab) |
| `meeting_minutes` | id, project_id, titel, datum, teilnehmer, text, erstellt_am | neu (Kommunikation-Tab) |

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
| **Kommunikation** | Diskussionen (= bisherige Notizen, jetzt mit Tags + Dateianhängen), Entscheidungen, Risiken, Meetingprotokolle, je mit Tags + Anhängen | Diskussionen: bestehend + erweitert (Phase 3); Entscheidungen/Risiken/Meetings neu (Phase 4) |
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
`meeting_minutes`. `tags`/`tag_links` nutzen zusätzlich `document` (Dokumente sind selbst
taggbar). Bewusst offen gehalten für spätere Erweiterung ohne Schema-Änderung, z. B. `task`,
`milestone`, `revision`, `jira_issue`.

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
- Notiz-/Kommentar-Karten zeigen bewusst **keinen Autor** — es gibt kein Auth-/User-System im Repo, ein Freitext-"Autor"-Feld würde nur eine echte Anmeldung vortäuschen; nur Zeitstempel wird angezeigt, bis ein User-System existiert
- Dokument-Typ-Filter (PDF/Mail/Excel/Word/Bild) im Dokumente-Tab ist bewusst clientseitig aus `mimetype`/Dateiendung abgeleitet statt einer serverseitigen Mimetype-Taxonomie
- "Verwendet in"-Backlinks im Dokumente-Tab verlinken auf den Kommunikation-Tab, aber (noch) nicht deep-scrollend zum konkreten Eintrag — MVP-Einschränkung
- Strukturierte E-Mail-Vorschau für `.eml`-Anhänge (Absender/Betreff/Anhänge aus dem Dateiinhalt geparst) ist zurückgestellt; MVP = Speichern + Download wie jedes andere Dokument, MIME-Type-Handling ist aber bereits darauf vorbereitet (siehe Abschnitt 6a)

---

## 11. Umsetzungsstand

Dieses Repo enthält:

1. **Schritt 1 (MVP):** Projekt-/FTE-Planung als Web-Formular inkl. Schulungsphase (`s`), PPTX-Export weiter nutzbar.
2. **Schritt 2 (Jira-Ist-Integration):** Worklog-Sync (`POST /jira/sync`) und Ist-FTE-Anzeige je Projekt/Monat (`GET /projects/{id}` liefert `ist` auf Projekt-Ebene, neben `fte` je Teilprojekt).
3. **Schritt 4 (Team-Kapazität):** MA-/Team-Stammdaten inkl. Jira-Account-Zuordnung und Zuordnung MA ↔ Projekt (`/team/*`), Voraussetzung für Schritt 2.
4. **Schritt 3 (Gap-Analyse + Hochrechnung):** `GET /gap` (Soll/Ist/Gap je Monat und Projekt, optional `?team_id=`) und `GET /forecast` (Kurzform: eine Zeile "Hochrechnung Jahresende/Projektende" je Projekt). Hochrechnung nach Variante 1 (Trendfortschreibung, Durchschnitt der letzten 3 Ist-Monate, siehe `backend/app/gap_analysis.py`). Frontend-View **Gap-Analyse** zeigt Soll/Ist/Hochrechnung als Chart je Projekt mit Team-Filter; Portfolio-Dashboard zeigt den Mini-Gap-Indikator (grün/gelb/rot/grau) je Projektkachel.
5. **Schritt 6 (IA-Umbau, Routing-Grundgerüst):** `/projekte/:id` ist jetzt ein Projekt-Workspace (`frontend/src/views/project/ProjectWorkspace.tsx`) mit nested Routes/Tab-Leiste statt einer einzelnen Detailseite. Die frühere `ProjectDetail.tsx` (1055 Zeilen) ist aufgeteilt in `ProjectPlanningTab` (Stammdaten/Gantt/FTE/Team-Zuordnung/Teilprojekte), `ProjectJiraTab`, `ProjectHistoryTab` (Verlauf, audit-only), `ProjectCommunicationTab` (Diskussionen = bisherige Notizen; Entscheidungen/Risiken/Meetingprotokolle sind Platzhalter bis Schritt 7). `ProjectOverviewTab`, `ProjectDocumentsTab` sind Platzhalter (Schritt 5/8). Top-Nav ist zweigeteilt (Projektmanagement/Controlling, `App.tsx`); `/jira-projekte` bleibt eigenständig.
6. **Schritt 2 (Einstellungen-Tab + Projektleiter):** `projects.projektleiter` (Freitext, siehe Abschnitt 3/10) über `ProjectUpdate`/`ProjectCreate` editierbar. `ProjectSettingsTab` bündelt jetzt Status-Lifecycle, Projektleiter und die Jira-Verknüpfung (Component/Label/Projekt-Auswahl) — das ist die einzige Stelle, an der die Jira-Verknüpfung *bearbeitet* wird. `ProjectJiraTab` ist entsprechend auf eine Lesesicht (aktuelle Verknüpfung, Ist-FTE-Tabelle, "Jetzt synchronisieren"-Button mit Link zurück zu Einstellungen) reduziert.
7. **Schritt 7 (Zentrale Dokumentenablage + Tags):** `documents`/`document_links`/`tags`/`tag_links`-Tabellen; einziger Upload-Pfad `POST /projects/{id}/documents` (multipart, optional `entity_type`+`entity_id` für atomare Verknüpfung beim Hochladen), `POST /document-links`/`DELETE /document-links/{id}` zum Verknüpfen/Entfernen ohne Re-Upload, `GET /projects/{id}/documents?search=&tag=`, `DELETE /documents/{id}` (räumt Datei + alle Verknüpfungen auf), `GET /tags?search=` (Autocomplete) — alles in `backend/app/routers/documents.py` + gemeinsamem Helper-Modul `backend/app/entity_links.py`. `Comment`/Notizen sind jetzt taggbar und können Dateien referenzieren (`CommentCreate.tags`, `CommentOut.documents`). Frontend: `ProjectDocumentsTab` voll funktionsfähig (Suche, Tag-Filter, clientseitiger Typ-Filter, "Verwendet in"-Backlinks, Löschen mit Verwendungs-Hinweis), `TagInput`/`AttachmentPicker`/`AttachmentList`-Komponenten, `NotesSection` als Kommentar-Karten mit Tags+Anhängen. `delete_project`/`delete_subproject`/`delete_comment` räumen die neuen Verknüpfungstabellen mit auf. Verifiziert: Upload→Verknüpfung→"Verwendet in" (Browser + curl), Mehrfachverknüpfung ohne Datei-Duplikat, Unlink vs. vollständiges Löschen, Cascade-Cleanup beim Löschen.

Details zu Aufbau und lokalem Betrieb siehe [`README.md`](README.md).

Noch nicht umgesetzt: Restaufwand-basierte Hochrechnung (Variante 2), Portal-SSO, der Excel-Migrationslauf für Bestandsdaten, Schritt 7b (Historie-Revisionsgruppierung), Schritt 8 (Entscheidungen/Risiken/Meetingprotokolle) und Schritt 9 (Controlling-Erweiterung) aus Abschnitt 9, sowie der offene Jira-Issues-Endpoint für den Jira-Tab. Siehe Abschnitt 10 für offene Entscheidungen.
