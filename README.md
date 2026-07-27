# Kapazitätsplaner (plx.crew Portal)

Web-App-Ablösung des Excel/VBA-Kapazitätsplaners — Planungslogik 1:1 aus dem
Excel-Tool übernommen (Gantt-Phasencodes, FTE-Raster), als Kachel im
BUILD-Bereich des plx.crew Portals. Konzept und Architektur: [`CONCEPT.md`](CONCEPT.md).

Dieses Repo enthält Projekt-/FTE-Planung als Web-Formular (inkl. Schulungsphase),
PPTX-Export über das bestehende Node-Skript, die Jira-Ist-Integration
(Worklog-Sync + Ist-FTE je Projekt), die Team-Kapazität (MA-/Team-Stammdaten,
Zuordnung MA ↔ Projekt) sowie die Soll-Ist-Gap-Analyse mit Hochrechnung
(Trendfortschreibung) je Projekt, inkl. Mini-Gap-Indikator im Portfolio-Dashboard
— siehe `CONCEPT.md` Abschnitt 11.

## Struktur

```
├── CONCEPT.md        # Architektur- und Konzeptdokument
├── frontend/          # React + Vite + TypeScript, Portal-CI-Design
├── backend/           # FastAPI, SQLAlchemy-Datenmodell, REST-API
├── export/            # PPTX-Export (PLX_generate_pptx.js, vom Backend aufgerufen)
├── migration/         # Einmal-Import bestehender .xlsm-Planungsdaten
└── legacy/             # Das ursprüngliche Excel/VBA-Tool (Referenz/Dokumentation)
```

## Lokal starten

### Mit Docker Compose (empfohlen)

```sh
docker compose up --build
```

- Backend: http://localhost:8000 (Swagger-UI unter `/docs`)
- Frontend: http://localhost:5173
- PostgreSQL: localhost:5432

### Manuell

**Backend** (Python 3.11+, standardmäßig SQLite unter `backend/kapazitaetsplaner.db`):

```sh
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Für PostgreSQL statt SQLite: `DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/db` setzen.

Für die Jira-Ist-Integration (optional, siehe `backend/.env.example`):
`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` setzen. Ohne diese Variablen
bleibt der Sync deaktiviert (`GET /jira/status` meldet `configured: false`),
die restliche Planung funktioniert unabhängig davon.

Wird in Jira mit **Tempo Timesheets** statt der nativen Jira-Zeitbuchung gearbeitet,
zusätzlich `TEMPO_API_TOKEN` setzen (Bearer-Token, erzeugt in Jira unter
Tempo → Einstellungen → API Integration). Grund: Bei Tempo-Nutzung zeigt der native
Jira-Worklog-Autor oft den Tempo-Systemaccount statt der echten Person — mit gesetztem
Token wird stattdessen direkt gegen die Tempo-API gesynct.

**Export-Skript-Abhängigkeiten** (wird vom Backend per `node` aufgerufen):

```sh
cd export
npm install
```

**Frontend** (Node 18+):

```sh
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE ggf. anpassen
npm run dev
```

## API (Kurzüberblick)

| Endpunkt | Beschreibung |
|---|---|
| `GET/POST /projects` | Projekte auflisten/anlegen |
| `GET/PUT/DELETE /projects/{id}` | Projekt lesen (inkl. `jira_component`, `ist`)/ändern/löschen |
| `POST /projects/{id}/subprojects` | Teilprojekt anlegen |
| `GET/PUT/DELETE /projects/subprojects/{id}` | Teilprojekt lesen/ändern/löschen |
| `GET /projects/subprojects/all` | Alle Teilprojekte flach (für die Zuordnung MA ↔ Teilprojekt) |
| `PUT /projects/subprojects/{id}/phasen` | Gantt-Phasencodes für einen Monat setzen (`p/k/t/s/g/?`) |
| `PUT /projects/subprojects/{id}/fte` | FTE-Soll-Wert für einen Monat setzen |
| `GET /projects/{id}/export/pptx` | Projekt als PPTX exportieren |
| `GET /projects/export/pptx/portfolio` | Alle Projekte als eine PPTX exportieren |
| `GET /team` | Teams inkl. Mitgliedern (Team-Kapazität-Übersicht) |
| `POST/PUT/DELETE /team/teams(/{id})` | Team anlegen/ändern/löschen |
| `GET/POST /team/members`, `PUT/DELETE /team/members/{id}` | MA-Stammdaten pflegen |
| `POST /team/members/{id}/assignments`, `DELETE /team/assignments/{id}` | MA ↔ Teilprojekt zuordnen/entfernen |
| `GET /jira/status` | Prüft, ob `JIRA_BASE_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` gesetzt sind |
| `GET /jira/lookup-account?query=` | Jira-Nutzersuche (für `team_members.jira_account_id`) |
| `POST /jira/sync` | Worklog-Sync für alle (oder ein) Projekt(e) mit gesetzter `jira_component` |
| `GET /gap` | Soll/Ist/Gap je Monat und Projekt inkl. Hochrechnung (Trendfortschreibung), optional `?team_id=` |
| `GET /gap/{project_id}` | Gap-Analyse für ein einzelnes Projekt |
| `GET /forecast` | Hochrechnung Jahresende/Projektende je Projekt (Kurzform von `/gap`), optional `?team_id=` |

## Migration bestehender Excel-Daten

```sh
cd migration
pip install -r requirements.txt
python import_excel.py /pfad/zur/bestehenden_datei.xlsm --api http://localhost:8000
```

`--dry-run` liest die Datei nur ein und gibt die geparsten Projekte aus, ohne
etwas in die API zu schreiben.

## Legacy-Tool

Das ursprüngliche Excel/VBA-Tool (`legacy/VBA.txt`, `export/PLX_generate_pptx.js`)
bleibt als Referenz und für den Übergangszeitraum nutzbar — Dokumentation dazu
in [`legacy/README.md`](legacy/README.md).
