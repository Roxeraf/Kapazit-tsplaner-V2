"""Team-Kapazität: MA-Stammdaten, Teams und Zuordnung MA <-> Projekt.

Voraussetzung für die Jira-Ist-Integration (siehe ../jira_sync.py): nur MA mit
gepflegtem `jira_account_id` werden bei der FTE-Umrechnung berücksichtigt.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..constants import VOLLZEIT_WOCHENSTUNDEN
from ..database import get_db

router = APIRouter(prefix="/team", tags=["team"])

# Assignment.fte ist bereits in FTE-Einheiten (nicht Prozent, siehe dortiger Docstring). Für
# die Auslastungsberechnung wird die individuelle Kapazität eines Teammitglieds daher als
# wochenstunden / VOLLZEIT_WOCHENSTUNDEN (siehe ../constants.py) ausgedrückt.


def _assignment_out(a: models.Assignment) -> schemas.AssignmentOut:
    return schemas.AssignmentOut(
        id=a.id,
        project_id=a.project_id,
        project_name=a.project.name,
        fte=a.fte,
    )


def _member_out(m: models.TeamMember) -> schemas.TeamMemberOut:
    return schemas.TeamMemberOut(
        id=m.id,
        name=m.name,
        jira_account_id=m.jira_account_id,
        wochenstunden=m.wochenstunden,
        team_id=m.team_id,
        team_name=m.team.name if m.team else None,
        assignments=[_assignment_out(a) for a in m.assignments],
    )


def _get_team_or_404(db: Session, team_id: int) -> models.Team:
    team = db.get(models.Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team nicht gefunden")
    return team


def _get_member_or_404(db: Session, member_id: int) -> models.TeamMember:
    member = db.get(models.TeamMember, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Teammitglied nicht gefunden")
    return member


@router.get("", response_model=list[schemas.TeamWithMembers])
def list_teams(db: Session = Depends(get_db)):
    teams = db.query(models.Team).order_by(models.Team.name).all()
    result = [
        schemas.TeamWithMembers(id=t.id, name=t.name, members=[_member_out(m) for m in t.members])
        for t in teams
    ]
    unassigned = db.query(models.TeamMember).filter(models.TeamMember.team_id.is_(None)).all()
    if unassigned:
        result.append(
            schemas.TeamWithMembers(id=0, name="Ohne Team", members=[_member_out(m) for m in unassigned])
        )
    return result


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
    """Löscht das Team, aber nicht dessen Mitglieder — die werden auf "ohne Team" gesetzt."""
    team = _get_team_or_404(db, team_id)
    for member in team.members:
        member.team_id = None
    db.delete(team)
    db.commit()


@router.get("/unassigned-authors", response_model=list[schemas.UnassignedAuthorOut])
def list_unassigned_authors(db: Session = Depends(get_db)):
    """Personen, die laut Jira/Tempo-Worklogs schon gebucht haben, aber noch kein Teammitglied
    sind (siehe jira_sync.sync_project) — zum Team-Aufbau per Klick statt manueller Suche."""
    bereits_mitglied = {
        row[0]
        for row in db.query(models.TeamMember.jira_account_id).filter(
            models.TeamMember.jira_account_id.isnot(None)
        )
    }
    rows = db.query(models.UnassignedJiraAuthor).order_by(models.UnassignedJiraAuthor.display_name).all()
    return [
        schemas.UnassignedAuthorOut(account_id=r.jira_account_id, display_name=r.display_name)
        for r in rows
        if r.jira_account_id not in bereits_mitglied
    ]


@router.get("/members", response_model=list[schemas.TeamMemberOut])
def list_members(db: Session = Depends(get_db)):
    members = db.query(models.TeamMember).order_by(models.TeamMember.name).all()
    return [_member_out(m) for m in members]


@router.post("/members", response_model=schemas.TeamMemberOut, status_code=201)
def create_member(payload: schemas.TeamMemberCreate, db: Session = Depends(get_db)):
    member = models.TeamMember(**payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return _member_out(member)


@router.put("/members/{member_id}", response_model=schemas.TeamMemberOut)
def update_member(member_id: int, payload: schemas.TeamMemberUpdate, db: Session = Depends(get_db)):
    member = _get_member_or_404(db, member_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return _member_out(member)


@router.delete("/members/{member_id}", status_code=204)
def delete_member(member_id: int, db: Session = Depends(get_db)):
    member = _get_member_or_404(db, member_id)
    db.delete(member)
    db.commit()


@router.post("/members/{member_id}/assignments", response_model=schemas.TeamMemberOut, status_code=201)
def create_assignment(member_id: int, payload: schemas.AssignmentCreate, db: Session = Depends(get_db)):
    member = _get_member_or_404(db, member_id)
    project = db.get(models.Project, payload.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    db.add(models.Assignment(team_member_id=member_id, project_id=payload.project_id, fte=payload.fte))
    db.commit()
    db.refresh(member)
    return _member_out(member)


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.get(models.Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Zuordnung nicht gefunden")
    db.delete(assignment)
    db.commit()


def compute_utilization(db: Session) -> list[schemas.MemberUtilizationOut]:
    """Auslastungsgrad je Teammitglied: zugeordnetes FTE (Summe über alle Projekt-
    Zuordnungen) im Verhältnis zur individuellen Kapazität (siehe VOLLZEIT_WOCHENSTUNDEN).
    Reine Aggregation aus TeamMember/Assignment, keine neue Tabelle. Auch von
    routers/kpis.py für die durchschnittliche Auslastung wiederverwendet."""
    members = db.query(models.TeamMember).order_by(models.TeamMember.name).all()
    result = []
    for m in members:
        kapazitaet_fte = round(m.wochenstunden / VOLLZEIT_WOCHENSTUNDEN, 2) if m.wochenstunden else 0.0
        zugeordnet_fte = round(sum(a.fte for a in m.assignments), 2)
        auslastung_pct = round(zugeordnet_fte / kapazitaet_fte * 100, 1) if kapazitaet_fte > 0 else None
        result.append(
            schemas.MemberUtilizationOut(
                member_id=m.id,
                member_name=m.name,
                team_id=m.team_id,
                team_name=m.team.name if m.team else None,
                kapazitaet_fte=kapazitaet_fte,
                zugeordnet_fte=zugeordnet_fte,
                auslastung_pct=auslastung_pct,
            )
        )
    return result


@router.get("/utilization", response_model=list[schemas.MemberUtilizationOut])
def get_utilization(db: Session = Depends(get_db)):
    return compute_utilization(db)
