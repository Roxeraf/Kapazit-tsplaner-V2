"""Jira-Ist-Integration: Status, Account-Suche (MA-Zuordnung) und Worklog-Sync.

Siehe CONCEPT.md Abschnitt 4. Ohne JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN bleibt
der Sync deaktiviert (Projekt-/FTE-Planung funktioniert unabhängig davon weiter).
"""

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


@router.post("/sync", response_model=schemas.JiraSyncResult)
def sync(subproject_id: int | None = None, db: Session = Depends(get_db)):
    """Synchronisiert Worklogs für alle (oder ein) Teilprojekt(e) mit gesetzter Jira-Komponente."""
    if not jira_client.is_configured():
        raise HTTPException(status_code=409, detail="Jira ist nicht konfiguriert.")

    query = db.query(models.Subproject).filter(models.Subproject.jira_component.isnot(None))
    if subproject_id is not None:
        query = query.filter(models.Subproject.id == subproject_id)
    subprojects = query.all()

    ergebnisse = []
    for sp in subprojects:
        try:
            gespeichert, unzugeordnet = jira_sync.sync_subproject(db, sp)
            ergebnisse.append(
                schemas.JiraSyncResultItem(
                    subproject_id=sp.id,
                    subproject_name=sp.name,
                    jira_component=sp.jira_component,
                    worklogs_synced=gespeichert,
                    unzugeordnete_buchungen=unzugeordnet,
                )
            )
        except Exception as exc:  # noqa: BLE001 – ein fehlgeschlagenes TP darf den Sync nicht abbrechen
            ergebnisse.append(
                schemas.JiraSyncResultItem(
                    subproject_id=sp.id,
                    subproject_name=sp.name,
                    jira_component=sp.jira_component,
                    worklogs_synced=0,
                    unzugeordnete_buchungen=0,
                    error=str(exc),
                )
            )

    return schemas.JiraSyncResult(status="ok", ergebnisse=ergebnisse)
