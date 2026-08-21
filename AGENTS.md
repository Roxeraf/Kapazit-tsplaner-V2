# AGENTS.md

Kapazitätsplaner v2 (plx.crew Portal) — Web-Ablösung des Excel/VBA-Kapazitätsplaners.

**Maßgebliche Architektur-Dokumente:**

* [`CONCEPT.md`](CONCEPT.md) — insbesondere Abschnitt 11 = Umsetzungsstand und 12.1 = Migrations-Policy
* [`README.md`](README.md) — Setup und lokale Inbetriebnahme

Bei Widersprüchen gilt:

`CONCEPT.md` > `README.md`

Agenten dürfen Widersprüche zwischen Dokumentation und Implementierung nicht stillschweigend durch eigene Annahmen auflösen.

---

# 1. Projektstruktur

* `frontend/` — React 19 + Vite + TypeScript

  * kein UI-Framework
  * eigenes CSS in `src/theme.css`
  * Lint = oxlint

* `backend/` — FastAPI + SQLAlchemy + Alembic

  * Python 3.11+

* `export/` — PPTX-Export

  * `PLX_generate_pptx.js`
  * pptxgenjs
  * wird vom Backend per `node` aufgerufen

* `migration/` — Einmal-Import alter `.xlsm`-Dateien

* `legacy/` — altes Excel/VBA-Tool

  * ausschließlich Referenz
  * dort keine neue Funktionalität implementieren

---

# 2. Entwicklungsbefehle

## Backend

Default-Datenbank:

`backend/kapazitaetsplaner.db`

Installation:

```sh
cd backend
pip install -r requirements.txt
```

Lokaler Entwicklungsserver:

```sh
uvicorn app.main:app --reload --port 8000
```

WICHTIG:

Der Uvicorn-Entwicklungsserver ist ein langlebiger Prozess.

Agenten dürfen ihn NICHT als normalen blockierenden Validierungsschritt starten.

Siehe Abschnitt:

`Backend-Validierung und langlebige Prozesse`

---

## Frontend

```sh
cd frontend
npm install
cp .env.example .env

npm run dev
npm run build
npm run lint
```

Dev-Server:

`http://localhost:5173`

`npm run build` führt aus:

```sh
tsc -b && vite build
```

und ist damit gleichzeitig TypeScript-Typecheck und Produktions-Build.

Unter Windows kann bei blockierter PowerShell Execution Policy:

```sh
npm.cmd
```

statt:

```sh
npm
```

verwendet werden.

Bevorzugt unter Windows:

```sh
npm.cmd run lint
npm.cmd run build
```

---

## Export-Abhängigkeiten

Node.js muss installiert sein.

```sh
cd export
npm install
```

---

## Kompletter Stack

```sh
docker compose up --build
```

Auch dieser Befehl kann langlebig sein.

Er darf nicht als unbeschränkt blockierender Agent-Validierungsschritt verwendet werden.

---

## Migrations-Wächter

Vor jedem Commit bzw. Abschluss einer Implementierung mit Schema- oder Migrationsänderungen verpflichtend:

```sh
python backend/check_migrations.py
```

---

# 3. Umgebungsvariablen

Das Backend lädt aktuell keine `.env`-Datei.

`python-dotenv` ist zwar in `requirements.txt` vorhanden, wird aber nicht verwendet.

Jira-Variablen müssen deshalb in der Shell gesetzt werden:

* `JIRA_BASE_URL`
* `JIRA_EMAIL`
* `JIRA_API_TOKEN`
* optional `TEMPO_API_TOKEN`

Ohne diese Variablen bleibt der Jira-Sync deaktiviert.

Der restliche Kapazitätsplaner funktioniert weiterhin.

Frontend API Base:

```text
VITE_API_BASE
```

Default:

```text
http://localhost:8000
```

Es existiert kein Vite-Proxy.

---

# 4. Aktuelle Test- und Verifikationssituation

## Aktueller Stand

Im Repository existiert derzeit kein vollständiges automatisiertes Testframework.

Das bedeutet ausdrücklich NICHT, dass automatisierte Tests grundsätzlich unerwünscht sind.

Die Einführung eines Testframeworks wie:

* pytest
* Vitest
* Jest
* umfangreiche Playwright-Test-Suites

ist jedoch eine bewusste Projekt-/Architekturentscheidung und darf nicht beiläufig im Rahmen einer kleinen Änderung erfolgen.

Für bestehende Änderungen gilt die dokumentierte Verifikationspraxis aus `CONCEPT.md`.

Dazu gehören insbesondere:

* Python-Import-Smoke-Checks
* Router-Import-Checks
* gezielte Python-Prüfungen
* Migrationsprüfung
* bestehende curl-/API-Szenarien
* `npm run lint`
* `npm run build`
* bei relevanten UI-Änderungen Browser-/Playwright-Prüfungen

Agenten dürfen nicht eigenmächtig ein neues Testframework als Voraussetzung für eine kleine Änderung einführen.

---

# 5. Backend-Validierung und langlebige Prozesse

Dieser Abschnitt ist verbindlich.

## Grundregel

Agenten dürfen langlebige Serverprozesse nicht als unbeschränkt blockierenden Validierungsschritt starten.

Insbesondere vermeiden:

```sh
uvicorn app.main:app --reload
```

als normalen Validierungsschritt innerhalb eines Agents.

Ebenso vermeiden:

```sh
docker compose up
npm run dev
```

wenn der Prozess anschließend unbegrenzt weiterläuft.

---

## Bevorzugte Backend-Validierung

Bevorzugt werden kurze, deterministische und selbstbeendende Prüfungen.

Beispiele:

### App-Import

```powershell
.\.venv\Scripts\python.exe -c "import app; print('app import ok')"
```

oder aus dem passenden Backend-Verzeichnis:

```powershell
.\.venv\Scripts\python.exe -c "from app.main import app; print('app import ok')"
```

### Router-Import

Beispiel:

```powershell
.\.venv\Scripts\python.exe -c "from app.routers import communication, planning; print('routers import ok')"
```

Nur tatsächlich relevante Router prüfen.

### Gezielt Python-Funktionen prüfen

Wenn eine Business-Funktion ohne Server aufrufbar ist:

* direkt importieren
* mit kleinem reproduzierbarem Input ausführen
* Ergebnis prüfen

### Migration

Bei Schema-/Migrationsänderungen:

```powershell
python backend/check_migrations.py
```

---

## Live-Server-Validierung

Ein Live-Server darf nur verwendet werden, wenn:

* die gewünschte Prüfung ohne laufenden Server nicht sinnvoll möglich ist
* ein API-/HTTP-Verhalten tatsächlich geprüft werden muss
* der Server sicher gestartet und wieder beendet werden kann

Wenn ein Live-Server nicht sicher innerhalb eines begrenzten Agent-Schritts verwendet werden kann:

NICHT starten.

Stattdessen melden:

```text
LIVE_SERVER_REQUIRED
```

und ausgeben:

* warum der Live-Server benötigt wird
* exakter Startbefehl
* exakter Prüfbefehl
* erwartetes Ergebnis

---

## Keine unendlichen Waits

Kein Agent darf unbegrenzt auf:

* Uvicorn
* Vite
* Docker Compose
* Hintergrundprozess
* Socket
* Logdatei
* HTTP-Endpoint

warten.

Wenn eine Validierung nach angemessener Zeit keinen Fortschritt zeigt:

abbrechen bzw. als nicht vollständig verifiziert melden.

Richtwert:

* kurze Validierungsbefehle: wenige Minuten
* auf Prozessbereitschaft warten: maximal ca. 60 Sekunden ohne Fortschritt
* keine Endlosschleifen

---

## Hintergrundprozesse

Wenn ein Hintergrundprozess ausnahmsweise gestartet wird:

* PID erfassen
* Prozessbereitschaft mit begrenztem Timeout prüfen
* Validierung durchführen
* Prozess anschließend sicher beenden
* keine verwaisten Prozesse zurücklassen

Wenn dies nicht zuverlässig möglich ist:

`LIVE_SERVER_REQUIRED` melden.

---

# 6. Migrations-Policy

Diese Regeln sind verbindlich.

Siehe `CONCEPT.md`, Abschnitt 12.1.

## Schemaänderungen

Jede Schemaänderung benötigt eine neue Alembic-Revision unter:

```text
backend/alembic/versions/
```

Kein ad-hoc:

```sql
ALTER TABLE
```

außerhalb des definierten Migrationssystems.

---

## Aktuelle Migrationskette

Die tatsächliche aktuelle Kette ist aus dem Repository zu ermitteln.

Historisch begann die konsolidierte Kette mit:

```text
0001_consolidated
```

Agenten dürfen die aktuelle Migrationskette nicht ausschließlich aus dieser Datei ableiten, wenn inzwischen weitere Revisionen existieren.

Vor Schemaarbeit immer die tatsächlich vorhandenen Revisionen prüfen.

---

## Bestehende Revisionen

Referenzierte Revisionen niemals:

* löschen
* umbenennen
* ersetzen

Das kann den App-Start bestehender Datenbanken zerstören.

Historischer Referenzfall:

`0013`

---

## Destruktive Migrationen

Destruktive Migrationen dürfen nur durchgeführt werden, wenn notwendige Daten vorher sicher konvertiert oder migriert werden.

Kein Datenverlust durch `DROP` ohne vorherige Datenbehandlung.

---

## Automatische Migration

Migrationen laufen beim App-Start automatisch:

```text
main.py
  ↓
db_bootstrap.run_migrations()
```

Dabei wird zwischen:

* frischer Datenbank
* bestehender Datenbank

unterschieden.

---

## check_migrations.py

Der Migrations-Wächter prüft unter anderem:

* genau einen Alembic-Head
* korrekte Kette
* Drift
* Seeds
* Downgrade-/Upgrade-Roundtrip

Die Prüfung erfolgt auf einer Wegwerf-Datenbank.

### Wichtiger Gotcha

`DATABASE_URL` muss vor dem Import von:

```python
app.database
```

gesetzt sein.

Die Engine wird bereits beim Import gebunden.

---

# 7. Architektur-Fakten

## Source of Truth

Seit Phase 26.9-Cutover gelten folgende Modelle als Source of Truth.

### Planung

* `PlanPhase`
* `Milestone`
* `BaselineSnapshot`

### Kapazität

* `ResourceDemand`
* `ResourceAssignment`

### Personen

* `Person`
* `ResourceProfile`

---

## Legacy-Modelle

Folgende Modelle wurden real entfernt:

* `GanttPhase`
* `FtePlan`
* `TeamMember`
* `Assignment`

Sie dürfen nicht wieder eingeführt werden.

Neue Funktionalität muss auf der Zielarchitektur aufbauen.

`gap_analysis.py` liest Soll-Daten aus:

```text
ResourceDemand
```

---

# 8. Authentifizierung und Rollen

Im Repository existiert bewusst kein:

* Auth-System
* Rollen-System
* Login-System
* RBAC-System

Siehe `CONCEPT.md`.

Agenten dürfen keine Authentifizierungs- oder RBAC-Logik erfinden, sofern dies nicht explizit als neue Anforderung definiert wurde.

---

# 9. Naming-Konventionen

## Zielarchitektur-native Modelle

Beispiele:

* `Person`
* `PlanPhase`
* `Blocker`
* `ResourceDemand`

verwenden englische Feldnamen.

## Excel-abgeleitete Kommunikationsmodelle

Beispiele:

* `Decision`
* `Risk`
* `Task`
* `MeetingMinutes`
* `Comment`

verwenden deutsche Feldnamen.

Beispiele:

```text
beschreibung
wahrscheinlichkeit
```

Diese bestehende Trennung nicht beiläufig vereinheitlichen.

---

# 10. Cross-Router-Logik

Gemeinsam verwendete Business-Logik gehört in gemeinsame Module.

Aktuell insbesondere:

```text
backend/app/capacity_calc.py
backend/app/gap_calc.py
backend/app/baseline_calc.py
backend/app/health_calc.py
backend/app/entity_links.py
```

sowie weitere im Repository vorhandene gemeinsame Calculation-/Service-Module.

Keine Business-Logik durch Imports zwischen Routern koppeln.

Nicht:

```text
Router A
  ↓
Router B
```

sondern:

```text
Router A ─┐
          ├─ Shared Logic
Router B ─┘
```

---

# 11. EntityTypes

Neue EntityTypes müssen an allen relevanten Registry-/Schema-/Frontend-Typstellen ergänzt werden.

Insbesondere prüfen:

```text
backend/app/entity_links.py
backend/app/schemas.py
frontend/src/types.ts
```

Zusätzliche aktuelle Registry-/Meta-Dateien aus dem Repository ebenfalls berücksichtigen.

Nicht davon ausgehen, dass diese Liste für immer vollständig bleibt.

---

# 12. allocation_gap

Das Vorzeichen von `allocation_gap` ist dokumentiert inkonsistent.

Einige Endpoints verwenden:

```text
fte - assigned_fte
```

andere:

```text
assigned_fte - fte
```

Frontend-Verbraucher müssen auf die tatsächliche Formel des jeweiligen Endpoints abgestimmt werden.

Nicht blind dem Docstring vertrauen.

Diese Inkonsistenz nicht im Rahmen einer unabhängigen Änderung nebenbei beheben.

Eine Vereinheitlichung benötigt einen eigenen Task mit Prüfung aller Verbraucher.

---

# 13. Frontend-Speichermuster

PlanPhase/Milestone/Blocker/Risk/Task/Decision und vergleichbare Entitäten speichern entsprechend dem vorhandenen Pattern unmittelbar bzw. gemäß aktueller Implementierung.

Die Stammdaten-Karte verwendet Draft + `batch_id` zur PlanHistory-Revisionsgruppierung.

Bestehende unterschiedliche Speichermuster nicht beiläufig vereinheitlichen.

Vor Änderungen immer die aktuelle Implementierung prüfen.

---

# 14. Sprache und UI

UI-Sprache ist Deutsch.

Neue:

* GUI-Texte
* Labels
* Hilfetexte
* fachliche Kommentare

grundsätzlich auf Deutsch halten, sofern der bestehende Kontext nichts anderes vorgibt.

Interne technische Identifier folgen bestehenden Code-Konventionen.

Eine Änderung eines sichtbaren GUI-Namens bedeutet nicht automatisch, dass:

* Komponenten
* Dateien
* Imports
* Klassen
* interne Variablen
* Routes

ebenfalls umbenannt werden sollen.

---

# 15. Engineering-Scope

Agenten dürfen nur Änderungen durchführen, die für die aktuelle Anforderung notwendig sind.

Insbesondere:

* keine ungefragten Refactorings
* keine ungefragten Umbenennungen
* keine ungefragten Architekturänderungen
* keine Cleanup-Änderungen außerhalb des Scopes
* keine Erweiterung des Requirements aus eigener Initiative

Bestehende Patterns bevorzugen.

Neue Dependencies nur einführen, wenn die bestehende Architektur die Anforderung nicht sinnvoll lösen kann.

Bei unklaren fachlichen Anforderungen keine Fachlogik erfinden.

---

# 16. Minimal-Change-Prinzip

Implementierungen sollen die kleinste kohärente Änderung verwenden, die das Requirement korrekt erfüllt.

Bevorzugt:

```text
bestehendes Pattern
→ kleine Änderung
→ gezielte Validierung
```

statt:

```text
neue Abstraktion
→ großer Refactor
→ mehrere unabhängige Änderungen
```

---

# 17. Änderungsgröße

Große Anforderungen sollen in unabhängig implementierbare und validierbare Tasks zerlegt werden.

Ein Task sollte nicht unnötig gleichzeitig:

* Datenmodell
* Migration
* Backend
* API
* Frontend
* Export
* Architektur

verändern, wenn eine sinnvolle Zerlegung möglich ist.

---

# 18. Git-Sicherheit

Bestehende uncommittete Änderungen können vom Benutzer stammen.

Sie dürfen nicht ungefragt:

* verworfen
* überschrieben
* zurückgesetzt
* gestasht
* committed

werden.

Insbesondere keine destruktiven Befehle ohne ausdrückliche Benutzeranweisung:

```sh
git reset
git reset --hard
git checkout --
git restore
git clean
git push --force
```

oder funktional vergleichbare Aktionen.

Nicht automatisch:

* committen
* pushen
* mergen
* rebasen
* Branches löschen
* Pull Requests erstellen

sofern dies nicht explizit angefordert wurde.

---

# 19. Validierungsstrategie

Validierung muss proportional zur tatsächlichen Änderung erfolgen.

Nicht für jede Änderung unnötig den kompletten Stack starten.

---

## Frontend-only

Mindestens prüfen:

```powershell
npm.cmd run lint
npm.cmd run build
```

Bei relevanten UI-/Interaktionsänderungen zusätzlich gezielte Browserprüfung, wenn sinnvoll und verfügbar.

Keinen Dev-Server unbegrenzt als blockierenden Agent-Prozess laufen lassen.

---

## Backend ohne Schemaänderung

Bevorzugt:

1. relevanter Python-Import-Smoke
2. Router-Import
3. gezielte Funktions-/Schema-Prüfung
4. optional API-/HTTP-Prüfung, wenn sicher möglich

Kein Uvicorn-Start als Default-Validierung.

---

## Schema / Migration

Verpflichtend:

```powershell
python backend/check_migrations.py
```

Zusätzlich:

* relevante Imports
* ggf. gezielte Modell-/Schema-Prüfung

---

## Full-Stack

Nur tatsächlich relevante Gates kombinieren:

```text
Backend Imports
↓
Migration falls nötig
↓
Frontend lint
↓
Frontend build
↓
gezielte Integrationsprüfung
```

Live-Server nur wenn wirklich erforderlich.

---

# 20. Validierungs-Timeouts

Agenten dürfen nicht unbegrenzt auf einen Validierungsschritt warten.

Wenn ein Prozess:

* keine neue Ausgabe liefert
* nicht terminiert
* offensichtlich als Server dauerhaft läuft
* auf externe Interaktion wartet

muss die Prüfung begrenzt oder abgebrochen werden.

Richtwert:

```text
ca. 60 Sekunden ohne erkennbaren Fortschritt
```

bei Prozessbereitschaft oder Live-Server-Checks.

Normale Build-/Migration-Kommandos dürfen länger laufen, wenn sichtbar Fortschritt stattfindet.

Keine harte globale 60-Sekunden-Grenze für legitime Builds setzen.

---

# 21. Umgang mit Validierungsfehlern

Unterscheiden zwischen:

```text
NEW_FAILURE
```

und:

```text
PRE_EXISTING_FAILURE
```

Vorbestehende Warnungen oder Fehler nicht ungefragt beheben.

Wenn ein vorbestehender Fehler die vollständige Validierung verhindert:

* nennen
* Zusammenhang erklären
* nicht behaupten, dass vollständige Validierung erfolgreich war

---

# 22. Fix-Regeln

Validierungsregeln dürfen nicht abgeschwächt werden, nur damit eine fehlerhafte Implementierung erfolgreich erscheint.

Nicht:

```text
Code fehlerhaft
→ Check entfernen
→ grün
```

sondern:

```text
Code fehlerhaft
→ Ursache analysieren
→ Code korrigieren
→ erneut validieren
```

Keine Endlosschleifen.

Die Anzahl automatischer Fix-Versuche wird vom Orchestrator gesteuert.

---

# 23. Temporäre Validierungsartefakte

Temporäre Dateien aus Validierungen dürfen nicht ungefragt committed werden.

Beispiele:

```text
uvicorn_*.out
uvicorn_*.err
temporäre DB-Dateien
Testdatenbanken
Logs
Build-Artefakte
```

Nach Möglichkeit aufräumen.

Wenn eine Datei für Diagnose erhalten bleiben muss:

im Abschlussbericht nennen.

---

# 24. Review-Regeln

Beim Review immer den tatsächlichen finalen Diff gegen:

* Requirement
* Acceptance Criteria
* Architekturregeln
* relevante Dokumentation

prüfen.

Besonders:

* fachliche Korrektheit
* Scope
* Regressionen
* Architektur
* unnötige Komplexität
* Dependencies
* Datenmodell
* API
* Migrationen
* Security
* Dokumentation

---

# 25. Dokumentation

`CONCEPT.md` aktualisieren, wenn sich insbesondere ändert:

* Architektur
* verbindliche Fachlogik
* Source-of-Truth-Struktur
* Datenmodell
* API-Grundprinzipien
* Migrationsstrategie
* wesentliche Systemgrenzen
* relevanter dokumentierter Umsetzungsstand

`README.md` aktualisieren, wenn sich insbesondere ändert:

* Setup
* Installation
* Start
* Konfiguration
* lokale Entwicklungsumgebung
* Entwicklerbedienung

Keine Dokumentationsänderung für triviale interne Implementierungsdetails erzwingen.

---

# 26. Umgang mit CONCEPT.md

`CONCEPT.md` ist die fachlich-technische Source of Truth.

Sie muss nicht für jede triviale Änderung vollständig geladen werden.

Bei:

* neuen Features
* Architekturänderungen
* Datenmodelländerungen
* Business-Logik
* Migrationen
* größeren Refactorings

relevante Abschnitte berücksichtigen.

---

# 27. Definition of Done

Eine Implementierung ist nur abgeschlossen, wenn:

* die angeforderte Funktion fachlich umgesetzt wurde
* Acceptance Criteria erfüllt sind, sofern definiert
* der Diff auf den notwendigen Scope begrenzt ist
* keine fremden Änderungen überschrieben wurden
* relevante Validierungen durchgeführt wurden
* keine bekannten neuen Regressionen bestehen
* erforderliche Dokumentation aktualisiert wurde
* verbleibende Risiken transparent genannt wurden

Wenn ein notwendiger Live-Server-Test nicht ausgeführt werden konnte:

nicht vollständig PASS melden.

Stattdessen:

```text
PARTIALLY_VERIFIED
```

oder:

```text
LIVE_SERVER_REQUIRED
```

gemäß Agent-Workflow.

---

# 28. Abschlussbericht

Nach einer Implementierung berichten:

## Implementiert

Was wurde geändert?

## Geänderte Dateien

Welche Dateien wurden verändert?

## Validierung

Welche Prüfungen wurden tatsächlich ausgeführt?

Ergebnisse unterscheiden:

* PASS
* FAIL
* NOT_VERIFIED
* PRE_EXISTING_WARNING
* LIVE_SERVER_REQUIRED

## Review

Falls unabhängiges Review ausgeführt wurde:

Ergebnis nennen.

## Verbleibende Risiken

Bekannte Restrisiken nennen.

---

# 29. Agent-Verantwortung

Der Orchestrator:

* koordiniert
* liest/editiert nicht selbst
* führt keine Shell-Kommandos aus

Explorer:

* liest und untersucht
* ändert nichts

Planner:

* plant
* ändert nichts

Builder:

* implementiert
* führt nur sichere proportionale Validierung aus

Tester:

* validiert unabhängig
* ändert keinen Anwendungscode
* startet keine unbegrenzt laufenden Prozesse

Reviewer:

* reviewt
* ändert nichts

Expert:

* analysiert schwierige Root Causes
* implementiert nicht

---

# 30. Grundprinzip

Für dieses Repository gilt:

```text
Korrektheit
+
kleiner Scope
+
bestehende Architektur
+
deterministische Validierung
+
keine langlebigen blockierenden Agent-Prozesse
+
keine erfundene Fachlogik
```

vor:

```text
großen Refactorings
+
unnötigen Dependencies
+
breiten Änderungen
+
instabiler Live-Server-Automatisierung
```

Bestehenden Code verstehen.

Dann planen.

Dann minimal ändern.

Dann mit kurzen, reproduzierbaren Checks validieren.

Live-Server nur wenn wirklich notwendig.

