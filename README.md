# Kapazitätsplaner (plx.crew Portal)

Web-App-Ablösung des Excel/VBA-Kapazitätsplaners — Planungslogik 1:1 aus dem
Excel-Tool übernommen (Gantt-Phasencodes, FTE-Raster), als Kachel im
BUILD-Bereich des plx.crew Portals. Konzept und Architektur: [`CONCEPT.md`](CONCEPT.md).

Dieses Repo enthält den **MVP** aus Abschnitt 9 des Konzepts: Projekt-/FTE-Planung
als Web-Formular, PPTX-Export weiter nutzbar über das bestehende Node-Skript.
Spätere Phasen (Jira-Ist-Integration, Gap-Analyse, Team-Kapazität) sind im
Datenmodell vorbereitet, aber noch nicht funktional — siehe `CONCEPT.md`
Abschnitt 11.

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
| `GET/PUT/DELETE /projects/{id}` | Projekt lesen/ändern/löschen |
| `POST /projects/{id}/subprojects` | Teilprojekt anlegen |
| `PUT /projects/subprojects/{id}/phasen` | Gantt-Phasencodes für einen Monat setzen |
| `PUT /projects/subprojects/{id}/fte` | FTE-Soll-Wert für einen Monat setzen |
| `GET /projects/{id}/export/pptx` | Projekt als PPTX exportieren |
| `GET /projects/export/pptx/portfolio` | Alle Projekte als eine PPTX exportieren |
| `GET /team`, `/gap`, `/forecast` | Platzhalter für spätere Phasen (siehe CONCEPT.md) |

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
