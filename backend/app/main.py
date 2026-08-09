from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .database import Base, engine
from .routers import communication, documents, export, gap, jira, projects, team  # noqa: F401

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
    if "projektleiter" not in _columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE projects ADD COLUMN projektleiter VARCHAR(200)"))

if "plan_history" in _inspector.get_table_names():
    _plan_history_columns = {col["name"] for col in _inspector.get_columns("plan_history")}
    if "batch_id" not in _plan_history_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE plan_history ADD COLUMN batch_id VARCHAR(36)"))

# erstellt_am/geaendert_am wurden zunächst mit VARCHAR(30) angelegt, datetime.isoformat() mit
# Mikrosekunden + UTC-Offset kann aber bis zu 32 Zeichen lang werden (z.B.
# "2026-07-28T10:05:52.407714+00:00") - unter Postgres (anders als SQLite, das Spaltenlängen
# nicht durchsetzt) führte das zu "value too long for type character varying(30)". Nur unter
# Postgres nötig: SQLite unterstützt kein ALTER COLUMN ... TYPE.
if engine.dialect.name == "postgresql":
    def _widen_if_needed(table: str, column: str, min_length: int) -> None:
        if table not in _inspector.get_table_names():
            return
        col = next((c for c in _inspector.get_columns(table) if c["name"] == column), None)
        if col is not None and getattr(col["type"], "length", None) is not None and col["type"].length < min_length:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR({min_length})"))

    _widen_if_needed("comments", "erstellt_am", 40)
    _widen_if_needed("plan_history", "geaendert_am", 40)

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


@app.get("/health")
def health():
    return {"status": "ok"}
