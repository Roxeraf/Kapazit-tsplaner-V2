from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .database import Base, engine
from .routers import export, gap, jira, projects, team  # noqa: F401 (registriert Modelle via projects/export)

Base.metadata.create_all(bind=engine)

# Leichtgewichtige Migration für bestehende SQLite-DBs: create_all legt nur fehlende Tabellen an,
# keine fehlenden Spalten an bestehenden Tabellen (kein Alembic im Repo, siehe CONCEPT.md Abschnitt 8).
_inspector = inspect(engine)
if "projects" in _inspector.get_table_names():
    _columns = {col["name"] for col in _inspector.get_columns("projects")}
    if "reihenfolge" not in _columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE projects ADD COLUMN reihenfolge INTEGER DEFAULT 0"))
            conn.execute(
                text(
                    "UPDATE projects SET reihenfolge = "
                    "(SELECT COUNT(*) FROM projects p2 WHERE p2.id <= projects.id) - 1"
                )
            )
    if "status" not in _columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE projects ADD COLUMN status VARCHAR(20) DEFAULT 'aktiv'"))

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


@app.get("/health")
def health():
    return {"status": "ok"}
