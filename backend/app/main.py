from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import export, gap, jira, projects, team  # noqa: F401 (registriert Modelle via projects/export)

Base.metadata.create_all(bind=engine)

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
