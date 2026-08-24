import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import db_bootstrap
from .routers import baselines, capacity, communication, controlling, documents, export, gap, gap_engine, health, jira, knowledge, kpis, people, planning, projects, real_capacity, team  # noqa: F401

logger = logging.getLogger(__name__)

# Schema-Aufbau/-Änderungen laufen über Alembic (siehe CONCEPT.md Abschnitt 12.1) statt über
# create_all()+ad-hoc-ALTER-TABLE. Deckt sowohl frische Dev-SQLite-DBs als auch bestehende,
# bereits befüllte DBs (Stamping der Baseline) ab.
db_bootstrap.run_migrations()

app = FastAPI(
    title="Kapazitätsplaner API",
    description="Backend für den Kapazitätsplaner (BUILD-Kachel im plx.crew Portal). Siehe CONCEPT.md.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: auf Portal-Origin einschränken, sobald SSO/Deploy-Domain feststeht
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """P20.1G (Delete Stabilization, Auftrag Abschnitt 23/26): globales Sicherheitsnetz gegen
    den bekannten FastAPI/Starlette-Fallstrick "500-Antwort ohne CORS-Header". Ohne einen
    registrierten Exception-Handler läuft eine unbehandelte Exception aus einer Route an
    CORSMiddleware VORBEI direkt in Starlettes ServerErrorMiddleware (die äußerste,
    automatisch vorhandene Schicht) - die von DORT generierte 500-Antwort durchläuft
    CORSMiddlewares Response-Verarbeitung nicht mehr und trägt deshalb KEINE CORS-Header. Im
    Browser wird eine Cross-Origin-Antwort ohne CORS-Header als Netzwerkfehler behandelt -
    fetch() wirft "TypeError: Failed to fetch" statt den eigentlichen 500-Status erkennbar zu
    machen (das war der Kern des reproduzierten Delete-Bugs, siehe
    capacity_calc.cleanup_phase_resource_dependencies-Docstring für den Auslöser selbst).

    Ein hier registrierter `@app.exception_handler(Exception)` fängt die Exception INNERHALB
    des FastAPI-Handlings ab, BEVOR sie zu einer echten unbehandelten Exception eskaliert - die
    resultierende Response durchläuft dadurch den normalen ASGI-Stack (inkl. CORSMiddleware)
    wie jede andere Response auch. Bewusst app-weit (nicht nur für die PlanPhase-Delete-Routen):
    dieselbe CORS-Header-Lücke kann bei JEDER unerwarteten 500-Exception auftreten, nicht nur
    beim Delete-Pfad. Ändert an der Fehlerbehandlung selbst nichts (kein Schlucken von Fehlern,
    kein verändertes HTTP-Statusverhalten für bereits behandelte HTTPException-Fälle - die
    laufen weiterhin über FastAPIs eigenen HTTPException-Handler, dieser Handler greift nur bei
    echten unerwarteten Exceptions) - nur die Antwort bekommt jetzt zuverlässig CORS-Header."""
    logger.exception("Unbehandelte Exception bei %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Interner Serverfehler. Bitte erneut versuchen oder Administration kontaktieren."},
    )

app.include_router(projects.router)
app.include_router(export.router)
app.include_router(team.router)
app.include_router(jira.router)
app.include_router(gap.router)
app.include_router(documents.router)
app.include_router(communication.router)
app.include_router(kpis.router)
app.include_router(knowledge.router)
app.include_router(people.router)
app.include_router(planning.router)
app.include_router(baselines.router)
app.include_router(capacity.router)
app.include_router(real_capacity.router)
app.include_router(gap_engine.router)
app.include_router(health.router)
app.include_router(controlling.router)


@app.get("/health")
def health():
    return {"status": "ok"}
