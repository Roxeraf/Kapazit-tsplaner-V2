"""Jira-Ist-Integration: Status, Account-Suche (MA-Zuordnung) und Worklog-Sync.

Siehe CONCEPT.md Abschnitt 4. Ohne JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN bleibt
der Sync deaktiviert (Projekt-/FTE-Planung funktioniert unabhängig davon weiter).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import jira_client, jira_sync, models, schemas
from ..database import get_db

router = APIRouter(prefix="/jira", tags=["jira"])


@router.get("/status", response_model=schemas.JiraStatus)
def jira_status():
    configured = jira_client.is_configured()
    return schemas.JiraStatus(
        configured=configured,
        base_url=jira_client.JIRA_BASE_URL if configured else None,
        hinweis=(
            "Jira-Verbindung konfiguriert."
            if configured
            else "JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN sind nicht gesetzt – Sync ist deaktiviert."
        ),
    )


@router.get("/lookup-account", response_model=list[schemas.JiraAccountMatch])
def lookup_account(query: str = Query(..., min_length=2)):
    """Sucht Jira-Nutzer per Name/E-Mail, um `team_members.jira_account_id` zu pflegen."""
    if not jira_client.is_configured():
        raise HTTPException(status_code=409, detail="Jira ist nicht konfiguriert.")
    try:
        users = jira_client.search_users(query)
    except Exception as exc:  # noqa: BLE001 – Jira-Fehlermeldung 1:1 durchreichen
        raise HTTPException(status_code=502, detail=f"Jira-Anfrage fehlgeschlagen: {exc}") from exc
    return [
        schemas.JiraAccountMatch(
            account_id=u["accountId"],
            display_name=u.get("displayName", u["accountId"]),
            email=u.get("emailAddress"),
        )
        for u in users
    ]


@router.get("/projects", response_model=list[schemas.JiraProjectOut])
def list_jira_projects(query: str | None = None, db: Session = Depends(get_db)):
    """Alle (oder per `query` gefilterte) Jira-Projekte, gemischt mit lokalem Katalog-Flag."""
    if not jira_client.is_configured():
        raise HTTPException(status_code=409, detail="Jira ist nicht konfiguriert.")
    try:
        jira_projects = jira_client.list_projects(query)
    except Exception as exc:  # noqa: BLE001 – Jira-Fehlermeldung 1:1 durchreichen
        raise HTTPException(status_code=502, detail=f"Jira-Anfrage fehlgeschlagen: {exc}") from exc

    catalog = {c.jira_project_key: c for c in db.query(models.JiraProjectCatalog).all()}
    return [
        schemas.JiraProjectOut(
            key=p["key"],
            name=p["name"],
            relevant=catalog[p["key"]].relevant if p["key"] in catalog else False,
            status=catalog[p["key"]].status if p["key"] in catalog else "aktiv",
        )
        for p in jira_projects
    ]


@router.put("/projects/{project_key}", response_model=schemas.JiraProjectOut)
def set_jira_project(project_key: str, payload: schemas.JiraProjectUpdate, db: Session = Depends(get_db)):
    """Markiert ein Jira-Projekt als "wird geplant" (oder nicht) und setzt den Status.

    Beim erstmaligen Aktivieren (relevant=true) wird automatisch ein Kapa-Projekt angelegt,
    damit das Jira-Projekt in der Portfolio-Ansicht auftaucht (siehe CONCEPT.md Abschnitt 10).
    """
    name = project_key
    if jira_client.is_configured():
        try:
            name = next((p["name"] for p in jira_client.list_projects() if p["key"] == project_key), project_key)
        except Exception:  # noqa: BLE001 – Name ist nur Anzeigesache, Katalog-Update darf trotzdem gelingen
            pass

    entry = db.get(models.JiraProjectCatalog, project_key)
    if entry is None:
        entry = models.JiraProjectCatalog(jira_project_key=project_key)
        db.add(entry)
    entry.relevant = payload.relevant
    entry.status = payload.status

    if payload.relevant:
        existing = db.query(models.Project).filter(models.Project.jira_project_key == project_key).first()
        if existing is None:
            heute = date.today()
            db.add(
                models.Project(
                    name=name,
                    start_monat=f"{heute.month:02d}.{heute.year}",
                    jira_project_key=project_key,
                )
            )

    db.commit()
    return schemas.JiraProjectOut(key=project_key, name=name, relevant=entry.relevant, status=entry.status)


@router.get("/projects/{project_key}/components", response_model=list[schemas.JiraComponentOut])
def list_jira_project_components(project_key: str):
    """Components eines Jira-Projekts, für den Component-Picker im Projekt-Detail."""
    if not jira_client.is_configured():
        raise HTTPException(status_code=409, detail="Jira ist nicht konfiguriert.")
    try:
        components = jira_client.list_components(project_key)
    except Exception as exc:  # noqa: BLE001 – Jira-Fehlermeldung 1:1 durchreichen
        raise HTTPException(status_code=502, detail=f"Jira-Anfrage fehlgeschlagen: {exc}") from exc
    return [schemas.JiraComponentOut(**c) for c in components]


@router.post("/sync", response_model=schemas.JiraSyncResult)
def sync(project_id: int | None = None, db: Session = Depends(get_db)):
    """Synchronisiert Worklogs für alle (oder ein) Projekt(e) mit gesetzter Jira-Komponente."""
    if not jira_client.is_configured():
        raise HTTPException(status_code=409, detail="Jira ist nicht konfiguriert.")

    query = db.query(models.Project).filter(models.Project.jira_component.isnot(None))
    if project_id is not None:
        query = query.filter(models.Project.id == project_id)
    projects = query.all()

    ergebnisse = []
    for p in projects:
        try:
            gespeichert, unzugeordnet = jira_sync.sync_project(db, p)
            ergebnisse.append(
                schemas.JiraSyncResultItem(
                    project_id=p.id,
                    project_name=p.name,
                    jira_component=p.jira_component,
                    worklogs_synced=gespeichert,
                    unzugeordnete_buchungen=unzugeordnet,
                )
            )
        except Exception as exc:  # noqa: BLE001 – ein fehlgeschlagenes Projekt darf den Sync nicht abbrechen
            ergebnisse.append(
                schemas.JiraSyncResultItem(
                    project_id=p.id,
                    project_name=p.name,
                    jira_component=p.jira_component,
                    worklogs_synced=0,
                    unzugeordnete_buchungen=0,
                    error=str(exc),
                )
            )

    return schemas.JiraSyncResult(status="ok", ergebnisse=ergebnisse)
