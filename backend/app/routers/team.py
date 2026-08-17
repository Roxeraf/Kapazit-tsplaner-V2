"""Team-Kapazität: Team-Stammdaten und portfolioweite Auslastung.

Mitgliederverwaltung (Person/ResourceProfile) lebt seit Phase 26.9 (Legacy Cutover) in
routers/people.py - TeamMember/Assignment sind entfallen, "Mitglied eines Teams" wird über
ResourceProfile.team_id ausgedrückt. Voraussetzung für die Jira-Ist-Integration (siehe
../jira_sync.py): nur Personen mit gepflegtem `jira_account_id` werden bei der
FTE-Umrechnung berücksichtigt.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import capacity_calc, models, schemas
from ..constants import current_period
from ..database import get_db

router = APIRouter(prefix="/team", tags=["team"])


def _get_team_or_404(db: Session, team_id: int) -> models.Team:
    team = db.get(models.Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team nicht gefunden")
    return team


@router.get("", response_model=list[schemas.TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.query(models.Team).order_by(models.Team.name).all()


@router.post("/teams", response_model=schemas.TeamOut, status_code=201)
def create_team(payload: schemas.TeamCreate, db: Session = Depends(get_db)):
    team = models.Team(**payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.put("/teams/{team_id}", response_model=schemas.TeamOut)
def update_team(team_id: int, payload: schemas.TeamUpdate, db: Session = Depends(get_db)):
    team = _get_team_or_404(db, team_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return team


@router.delete("/teams/{team_id}", status_code=204)
def delete_team(team_id: int, db: Session = Depends(get_db)):
    """Löscht das Team, aber nicht dessen Mitglieder — deren ResourceProfile wird auf
    "ohne Team" gesetzt."""
    team = _get_team_or_404(db, team_id)
    for profile in db.query(models.ResourceProfile).filter(models.ResourceProfile.team_id == team_id).all():
        profile.team_id = None
    db.delete(team)
    db.commit()


@router.get("/unassigned-authors", response_model=list[schemas.UnassignedAuthorOut])
def list_unassigned_authors(db: Session = Depends(get_db)):
    """Personen, die laut Jira/Tempo-Worklogs schon gebucht haben, aber noch keine bekannte
    Jira-Account-ID an ihrer Person hinterlegt ist (siehe jira_sync.sync_project) - zum
    Team-Aufbau per Klick statt manueller Suche."""
    bereits_bekannt = {
        row[0]
        for row in db.query(models.Person.jira_account_id).filter(models.Person.jira_account_id.isnot(None))
    }
    rows = db.query(models.UnassignedJiraAuthor).order_by(models.UnassignedJiraAuthor.display_name).all()
    return [
        schemas.UnassignedAuthorOut(account_id=r.jira_account_id, display_name=r.display_name)
        for r in rows
        if r.jira_account_id not in bereits_bekannt
    ]


@router.get("/utilization", response_model=list[schemas.PortfolioUtilizationEntry])
def get_utilization(period: str | None = None, db: Session = Depends(get_db)):
    return capacity_calc.compute_portfolio_utilization(db, period or current_period())
