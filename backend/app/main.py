from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db_bootstrap
from .routers import baselines, capacity, communication, controlling, documents, export, gap, gap_engine, health, jira, knowledge, kpis, people, planning, projects, real_capacity, team  # noqa: F401

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
