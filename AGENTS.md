# AGENTS.md

Kapazitätsplaner v2 (plx.crew Portal) — Web-Ablösung des Excel/VBA-Kapazitätsplaners.

**Maßgebliche Architektur-Dokumente:**

* [`CONCEPT.md`](CONCEPT.md) — insbesondere Abschnitt 11 = Umsetzungsstand und 12.1 = Migrations-Policy
* [`README.md`](README.md) — Setup und lokale Inbetriebnahme

Beide Dokumente sind auf Deutsch und aktuell.

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
  * keine neue Funktionalität dort implementieren

---

# 2. Entwicklungsbefehle

## Backend

Default-Datenbank:

`backend/kapazitaetsplaner.db`

```sh
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

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

Beispiel:

```sh
npm.cmd run lint
npm.cmd run build
```

## Export-Abhängigkeiten

Node.js muss installiert sein.

```sh
cd export
npm install
```

## Kompletter Stack

```sh
docker compose up --build
```

## Migrations-Wächter

Vor jedem Commit mit Schema- oder Migrationsänderungen verpflichtend:

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

Im Repository existiert derzeit kein automatisiertes Testframework.

Das bedeutet ausdrücklich **nicht**, dass automatisierte Tests grundsätzlich unerwünscht sind.

Die Einführung eines Testframeworks wie:

* pytest
* Vitest
* Jest
* Playwright-Test-Suites

ist jedoch eine bewusste Projekt-/Architekturentscheidung und darf nicht beiläufig im Rahmen einer kleinen Änderung erfolgen.

Für bestehende Änderungen gilt die dokumentierte Verifikationspraxis aus `CONCEPT.md`.

Dazu gehören insbesondere:

* curl-Szenarien gegen den laufenden Backend-Server
* `npm run lint`
* `npm run build`
* bei relevanten UI-Änderungen Browser-/Playwright-Prüfungen gegen den Dev-Server

Agenten dürfen nicht eigenmächtig ein neues Testframework als Voraussetzung für eine kleine Änderung einführen.

---

# 5. Migrations-Policy

Diese Regeln sind verbindlich.

Siehe auch `CONCEPT.md`, Abschnitt 12.1.

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

## Aktuelle Migrationskette

```text
0001_consolidated
    ↓
0002_align_project_nullable
    ↓
0003_phase26_legacy_cutover
```

`0001_consolidated` ist die Squash-Baseline.

## Bestehende Revisionen

Referenzierte Revisionen niemals:

* löschen
* umbenennen
* ersetzen

Das kann den App-Start bestehender Datenbanken zerstören.

Historischer Referenzfall:

`0013`

## Destruktive Migrationen

Destruktive Migrationen dürfen nur durchgeführt werden, wenn notwendige Daten vorher sicher konvertiert oder migriert werden.

Kein Datenverlust durch:

```text
DROP
```

ohne vorherige Datenbehandlung.

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

## check_migrations.py

Der Migrations-Wächter prüft:

* genau einen Alembic-Head
* korrekte Kette ab der Baseline
* `alembic check`
* Drift gegen `models.py`
* Seeds
* Downgrade-/Upgrade-Roundtrip

Die Prüfung erfolgt auf einer Wegwerf-SQLite-Datenbank.

### Wichtiger Gotcha

`DATABASE_URL` muss vor dem Import von:

```python
app.database
```

gesetzt sein.

Die Engine wird bereits beim Import gebunden.

Siehe:

```text
check_migrations.py
```

---

# 6. Architektur-Fakten

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

# 7. Authentifizierung und Rollen

Im Repository existiert bewusst kein:

* Auth-System
* Rollen-System
* Login-System
* RBAC-System

Siehe `CONCEPT.md`, Abschnitte 7 und 10.

Agenten dürfen keine Authentifizierungs- oder RBAC-Logik erfinden, sofern dies nicht explizit als neue Anforderung definiert wurde.

---

# 8. Naming-Konventionen

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

Diese bestehende Trennung nicht beiläufig vereinheitlichen oder refactoren.

---

# 9. Cross-Router-Logik

Gemeinsam verwendete Business-Logik gehört in gemeinsame Module.

Aktuell insbesondere:

```text
backend/app/capacity_calc.py
backend/app/gap_calc.py
backend/app/baseline_calc.py
backend/app/health_calc.py
backend/app/entity_links.py
```

Keine Business-Logik durch Imports zwischen Routern koppeln.

Also nicht:

```text
Router A
   ↓ import
Router B
```

sondern:

```text
Router A ─┐
          ├─ gemeinsame Logik
Router B ─┘
```

Bestehende Architektur bevorzugen.

---

# 10. EntityTypes

Neue EntityTypes für:

* Tags
* Dokumente
* Relationen
* Knowledge

müssen an drei Stellen ergänzt werden:

```text
backend/app/entity_links.py
```

Registry

```text
backend/app/schemas.py
```

`EntityType`

```text
frontend/src/types.ts
```

`EntityType`

Keine dieser Stellen vergessen.

---

# 11. allocation_gap

Das Vorzeichen von `allocation_gap` ist aktuell inkonsistent.

Dies ist ein dokumentierter Bestandsfehler.

## capacity.py / controlling.py

Berechnung:

```text
fte - assigned_fte
```

Damit gilt:

```text
positiv = Unterdeckung
```

## health.py Cockpit

Berechnung:

```text
assigned_fte - fte
```

Damit gilt:

```text
negativ = Unterdeckung
```

Frontend-Verbraucher müssen auf die tatsächliche Formel des jeweiligen Endpoints abgestimmt werden.

Nicht blind dem Docstring vertrauen.

Diese Inkonsistenz nicht im Rahmen einer fachlich unabhängigen Änderung nebenbei beheben.

Eine Vereinheitlichung benötigt einen eigenen Task mit Prüfung aller Verbraucher.

---

# 12. Frontend-Speichermuster

Folgende Entitäten speichern unmittelbar pro Feldänderung:

* PlanPhase
* Milestone
* Blocker
* Risk
* Task
* Decision
* weitere vergleichbare Entitäten

Die Stammdaten-Karte verwendet dagegen:

```text
Draft
+
batch_id
```

zur PlanHistory-Revisionsgruppierung.

Diese unterschiedlichen Speichermuster sind beabsichtigt.

Nicht beiläufig vereinheitlichen.

---

# 13. Sprache und UI

UI-Sprache ist Deutsch.

Bestehende Routen bleiben deutsch bzw. entsprechen der vorhandenen Routing-Konvention.

Beispiele:

```text
/projekte/:id/planung
/gap
```

Neue:

* GUI-Texte
* Labels
* Hilfetexte
* fachliche Kommentare

grundsätzlich auf Deutsch halten, sofern der bestehende Kontext nichts anderes vorgibt.

Interne technische Identifier folgen dagegen den bestehenden Code-Konventionen.

Eine Änderung eines sichtbaren GUI-Namens bedeutet nicht automatisch, dass:

* Komponenten
* Dateien
* Imports
* Klassen
* interne Variablen
* Routes

ebenfalls umbenannt werden sollen.

---

# 14. Engineering-Scope

Agenten dürfen nur Änderungen durchführen, die für die aktuelle Anforderung notwendig sind.

Insbesondere:

* keine ungefragten Refactorings
* keine ungefragten Umbenennungen
* keine ungefragten Architekturänderungen
* keine Cleanup-Änderungen außerhalb des Scopes
* keine Erweiterung des Requirements aus eigener Initiative

Bestehende Patterns bevorzugen, bevor neue Abstraktionen eingeführt werden.

Neue Dependencies nur einführen, wenn die bestehende Architektur die Anforderung nicht sinnvoll lösen kann.

Bei unklaren fachlichen Anforderungen keine neue Fachlogik erfinden.

Wenn eine fachlich relevante Entscheidung nicht aus:

* Requirement
* Code
* `CONCEPT.md`
* `README.md`

ableitbar ist, muss die Unsicherheit transparent gemacht werden.

---

# 15. Minimal-Change-Prinzip

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

Ein Agent darf Code nicht nur deshalb refactoren, weil eine alternative Struktur subjektiv schöner wäre.

---

# 16. Änderungsgröße

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

Wenn ein Requirement mehrere unabhängig lieferbare Features enthält, zuerst eine Task-Zerlegung vorschlagen.

Große unkontrollierte Multi-Modul-Diffs vermeiden.

---

# 17. Git-Sicherheit

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

Agenten dürfen keine fremden Änderungen zurücksetzen, nur weil sie die eigene Implementierung behindern.

Wenn bestehende Änderungen einen sicheren Eingriff verhindern:

* stoppen
* Konflikt erklären
* betroffene Dateien nennen

Nicht automatisch:

* committen
* pushen
* mergen
* Branches löschen
* Pull Requests erstellen

sofern dies nicht explizit angefordert wurde.

---

# 18. Validierungsstrategie

Validierung muss proportional zur tatsächlichen Änderung erfolgen.

Nicht für jede Änderung unnötig den kompletten Stack starten.

## Frontend-only

Mindestens prüfen:

```sh
npm run lint
npm run build
```

Unter Windows bei Bedarf:

```sh
npm.cmd run lint
npm.cmd run build
```

Bei relevanten UI- oder Interaktionsänderungen zusätzlich gezielte Browser-/Playwright-Prüfung, sofern verfügbar und sinnvoll.

## Backend

Je nach Änderung:

* Import-Smoke-Test
* App-Start
* relevante API-/curl-Szenarien
* fachlich passende Backend-Prüfung

Keine erfundenen Prüfkommandos verwenden.

## Schema / Migration

Verpflichtend:

```sh
python backend/check_migrations.py
```

Zusätzlich relevante Backend-Prüfungen durchführen.

## Full-Stack

Nur die tatsächlich relevanten Gates kombinieren.

Beispielsweise:

```text
Backend
   ↓
API
   ↓
Frontend lint
   ↓
Frontend build
   ↓
ggf. UI Smoke
```

---

# 19. Umgang mit Validierungsfehlern

Validierungsfehler zunächst klassifizieren.

Unterscheiden zwischen:

```text
durch aktuelle Änderung verursacht
```

und:

```text
bereits vorbestehend / unabhängig
```

Vorbestehende Warnungen oder Fehler nicht ungefragt beheben.

Wenn ein vorbestehender Fehler die Validierung der aktuellen Änderung verhindert:

* Fehler nennen
* Zusammenhang erklären
* nicht behaupten, dass vollständige Validierung erfolgreich war

Eine Änderung gilt nicht automatisch als fehlerhaft, nur weil ein unabhängiger vorbestehender Fehler existiert.

---

# 20. Fix-Regeln

Tests oder Validierungsregeln dürfen nicht abgeschwächt werden, nur damit eine fehlerhafte Implementierung erfolgreich erscheint.

Nicht:

```text
Implementierung fehlerhaft
→ Test entfernen
→ grün
```

sondern:

```text
Implementierung fehlerhaft
→ Root Cause
→ Implementierung korrigieren
→ erneut validieren
```

Keine Endlosschleifen.

Die konkrete Anzahl automatischer Fix-Versuche wird vom Engineering-Orchestrator gesteuert.

---

# 21. Review-Regeln

Bei einem Review immer die tatsächliche Implementierung bzw. den finalen Diff gegen:

* Requirement
* Acceptance Criteria
* Architekturregeln
* relevante Dokumentation

prüfen.

Nicht nur bewerten, ob der Code syntaktisch plausibel aussieht.

Besonders prüfen:

* fachliche Korrektheit
* Scope
* Regressionen
* Architektur
* unnötige Komplexität
* neue Dependencies
* Datenmodell-Auswirkungen
* API-Auswirkungen
* Migrationsauswirkungen
* Security-Auswirkungen
* Dokumentationsbedarf

Review-Findings nicht durch Änderungen außerhalb des Requirements vorsorglich lösen.

---

# 22. Dokumentation

`CONCEPT.md` aktualisieren, wenn sich insbesondere ändert:

* Architektur
* verbindliche Fachlogik
* Source-of-Truth-Struktur
* Datenmodell
* API-Grundprinzipien
* Migrationsstrategie
* wesentliche Systemgrenzen
* dokumentierter Umsetzungsstand, sofern relevant

`README.md` aktualisieren, wenn sich insbesondere ändert:

* Setup
* Installation
* Start
* Konfiguration
* lokale Entwicklungsumgebung
* Bedienung für Entwickler

Keine Dokumentationsänderung für triviale interne Implementierungsdetails erzwingen.

Bei Widersprüchen:

```text
CONCEPT.md
    >
README.md
```

---

# 23. Umgang mit CONCEPT.md

`CONCEPT.md` ist die fachlich-technische Source of Truth.

Sie muss jedoch nicht für jede triviale Änderung vollständig gelesen werden.

Bei kleinen lokalen Änderungen nur relevante Dokumentation laden.

Bei:

* neuen Features
* Architekturänderungen
* Datenmodelländerungen
* Business-Logik
* Migrationen
* größeren Refactorings

müssen die relevanten Abschnitte aus `CONCEPT.md` berücksichtigt werden.

Dadurch wird unnötiger Kontext- und Tokenverbrauch vermieden.

---

# 24. Definition of Done

Eine Implementierung ist nur abgeschlossen, wenn:

* die angeforderte Funktion fachlich umgesetzt wurde
* Acceptance Criteria erfüllt sind, sofern definiert
* der Diff auf den notwendigen Scope begrenzt ist
* keine fremden Änderungen überschrieben wurden
* relevante Validierungen durchgeführt wurden
* keine bekannten neuen Regressionen bestehen
* erforderliche Dokumentation aktualisiert wurde
* verbleibende Risiken transparent genannt wurden

Bei vollständigen Engineering-Workflows gelten zusätzlich die vom Orchestrator definierten Review- und Verification-Gates.

---

# 25. Abschlussbericht

Nach einer Implementierung kurz und konkret berichten:

## Implementiert

Was wurde fachlich geändert?

## Geänderte Dateien

Welche Dateien wurden verändert und warum?

## Validierung

Welche Prüfungen wurden tatsächlich ausgeführt?

Ergebnisse klar unterscheiden:

* erfolgreich
* fehlgeschlagen
* Warnungen
* vorbestehende Probleme

## Review

Wenn ein unabhängiges Review durchgeführt wurde:

Ergebnis nennen.

Wenn bei einem QUICK-Workflow bewusst kein unabhängiger Reviewer verwendet wurde:

dies transparent angeben.

## Verbleibende Risiken

Bekannte Restrisiken nennen.

Wenn keine bekannt sind:

```text
Keine bekannten neuen Risiken durch diese Änderung.
```

---

# 26. Grundprinzip

Für dieses Repository gilt:

```text
Korrektheit
    +
kleiner Scope
    +
bestehende Architektur
    +
gezielte Validierung
    +
keine erfundene Fachlogik
```

vor:

```text
großen Refactorings
+
neuen Abstraktionen
+
unnötigen Dependencies
+
breiten Änderungen außerhalb des Requirements
```

Bestehenden Code zuerst verstehen.

Dann planen.

Dann minimal ändern.

Dann gezielt validieren.
