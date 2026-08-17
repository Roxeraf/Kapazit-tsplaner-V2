"""PlanPhase & Milestone (Project Planning Core, Phase 17, siehe CONCEPT.md Abschnitt 12 /
Master-MD Abschnitt 8/9/10). Seit dem Legacy Cutover (Phase 26.9) die alleinige
Planungswahrheit - das ehemals parallele Gantt-Grid (GanttPhase/ProjectGanttPhase) ist
entfallen. Folgt demselben CRUD-Muster wie routers/communication.py."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import entity_links, models, schemas
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["planning"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


def _check_subproject(db: Session, project_id: int, subproject_id: int | None) -> None:
    if subproject_id is None:
        return
    sp = db.get(models.Subproject, subproject_id)
    if sp is None:
        raise HTTPException(status_code=404, detail="Teilprojekt nicht gefunden")
    if sp.project_id != project_id:
        raise HTTPException(status_code=422, detail="subproject_id muss zum selben Projekt gehören")


def _check_owner(db: Session, owner_person_id: int | None, owner_team_id: int | None) -> None:
    if owner_person_id is not None and db.get(models.Person, owner_person_id) is None:
        raise HTTPException(status_code=404, detail="Person (owner_person_id) nicht gefunden")
    if owner_team_id is not None and db.get(models.Team, owner_team_id) is None:
        raise HTTPException(status_code=404, detail="Team (owner_team_id) nicht gefunden")


# ---------------------------------------------------------------------------
# PlanPhase
# ---------------------------------------------------------------------------


def _plan_phase_out(db: Session, p: models.PlanPhase) -> schemas.PlanPhaseOut:
    return schemas.PlanPhaseOut(
        id=p.id,
        project_id=p.project_id,
        subproject_id=p.subproject_id,
        phase_type=p.phase_type,
        baseline_start=p.baseline_start,
        baseline_end=p.baseline_end,
        forecast_start=p.forecast_start,
        forecast_end=p.forecast_end,
        actual_start=p.actual_start,
        actual_end=p.actual_end,
        status=p.status,
        progress=p.progress,
        owner_person_id=p.owner_person_id,
        owner_team_id=p.owner_team_id,
        erstellt_am=p.erstellt_am,
        aktualisiert_am=p.aktualisiert_am,
        tags=entity_links.tags_for(db, "plan_phase", p.id),
        documents=entity_links.documents_for(db, "plan_phase", p.id),
    )


def _get_plan_phase_or_404(db: Session, plan_phase_id: int) -> models.PlanPhase:
    p = db.get(models.PlanPhase, plan_phase_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Planphase nicht gefunden")
    return p


@router.get("/{project_id}/plan-phases", response_model=list[schemas.PlanPhaseOut])
def list_plan_phases(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.PlanPhase)
        .filter(models.PlanPhase.project_id == project_id)
        .order_by(models.PlanPhase.baseline_start, models.PlanPhase.id)
        .all()
    )
    return [_plan_phase_out(db, p) for p in rows]


@router.post("/{project_id}/plan-phases", response_model=schemas.PlanPhaseOut, status_code=201)
def create_plan_phase(project_id: int, payload: schemas.PlanPhaseCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    _check_subproject(db, project_id, payload.subproject_id)
    _check_owner(db, payload.owner_person_id, payload.owner_team_id)
    now = _now()
    plan_phase = models.PlanPhase(
        project_id=project_id,
        subproject_id=payload.subproject_id,
        phase_type=payload.phase_type,
        baseline_start=payload.baseline_start,
        baseline_end=payload.baseline_end,
        forecast_start=payload.forecast_start,
        forecast_end=payload.forecast_end,
        actual_start=payload.actual_start,
        actual_end=payload.actual_end,
        status=payload.status,
        progress=payload.progress,
        owner_person_id=payload.owner_person_id,
        owner_team_id=payload.owner_team_id,
        erstellt_am=now,
        aktualisiert_am=now,
    )
    db.add(plan_phase)
    db.flush()
    if payload.tags:
        entity_links.sync_tags(db, "plan_phase", plan_phase.id, payload.tags)
    db.commit()
    db.refresh(plan_phase)
    return _plan_phase_out(db, plan_phase)


@router.put("/plan-phases/{plan_phase_id}", response_model=schemas.PlanPhaseOut)
def update_plan_phase(plan_phase_id: int, payload: schemas.PlanPhaseUpdate, db: Session = Depends(get_db)):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"tags"})
    if "subproject_id" in changes:
        _check_subproject(db, plan_phase.project_id, changes["subproject_id"])
    _check_owner(db, changes.get("owner_person_id"), changes.get("owner_team_id"))
    if changes:
        for field, value in changes.items():
            setattr(plan_phase, field, value)
        plan_phase.aktualisiert_am = _now()
    if payload.tags is not None:
        entity_links.sync_tags(db, "plan_phase", plan_phase.id, payload.tags)
    db.commit()
    db.refresh(plan_phase)
    return _plan_phase_out(db, plan_phase)


@router.delete("/plan-phases/{plan_phase_id}", status_code=204)
def delete_plan_phase(plan_phase_id: int, db: Session = Depends(get_db)):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    entity_links.delete_links_for_entity(db, "plan_phase", plan_phase_id)
    entity_links.delete_relations_for_entity(db, "plan_phase", plan_phase_id)
    db.delete(plan_phase)
    db.commit()


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------


def _milestone_out(db: Session, m: models.Milestone) -> schemas.MilestoneOut:
    return schemas.MilestoneOut(
        id=m.id,
        project_id=m.project_id,
        subproject_id=m.subproject_id,
        name=m.name,
        baseline_date=m.baseline_date,
        forecast_date=m.forecast_date,
        actual_date=m.actual_date,
        status=m.status,
        owner_person_id=m.owner_person_id,
        owner_team_id=m.owner_team_id,
        erstellt_am=m.erstellt_am,
        aktualisiert_am=m.aktualisiert_am,
        tags=entity_links.tags_for(db, "milestone", m.id),
        documents=entity_links.documents_for(db, "milestone", m.id),
    )


def _get_milestone_or_404(db: Session, milestone_id: int) -> models.Milestone:
    m = db.get(models.Milestone, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone nicht gefunden")
    return m


@router.get("/{project_id}/milestones", response_model=list[schemas.MilestoneOut])
def list_milestones(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.Milestone)
        .filter(models.Milestone.project_id == project_id)
        .order_by(models.Milestone.baseline_date, models.Milestone.id)
        .all()
    )
    return [_milestone_out(db, m) for m in rows]


@router.post("/{project_id}/milestones", response_model=schemas.MilestoneOut, status_code=201)
def create_milestone(project_id: int, payload: schemas.MilestoneCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    _check_subproject(db, project_id, payload.subproject_id)
    _check_owner(db, payload.owner_person_id, payload.owner_team_id)
    now = _now()
    milestone = models.Milestone(
        project_id=project_id,
        subproject_id=payload.subproject_id,
        name=payload.name,
        baseline_date=payload.baseline_date,
        forecast_date=payload.forecast_date,
        actual_date=payload.actual_date,
        status=payload.status,
        owner_person_id=payload.owner_person_id,
        owner_team_id=payload.owner_team_id,
        erstellt_am=now,
        aktualisiert_am=now,
    )
    db.add(milestone)
    db.flush()
    if payload.tags:
        entity_links.sync_tags(db, "milestone", milestone.id, payload.tags)
    db.commit()
    db.refresh(milestone)
    return _milestone_out(db, milestone)


@router.put("/milestones/{milestone_id}", response_model=schemas.MilestoneOut)
def update_milestone(milestone_id: int, payload: schemas.MilestoneUpdate, db: Session = Depends(get_db)):
    milestone = _get_milestone_or_404(db, milestone_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"tags"})
    if "subproject_id" in changes:
        _check_subproject(db, milestone.project_id, changes["subproject_id"])
    _check_owner(db, changes.get("owner_person_id"), changes.get("owner_team_id"))
    if changes:
        for field, value in changes.items():
            setattr(milestone, field, value)
        milestone.aktualisiert_am = _now()
    if payload.tags is not None:
        entity_links.sync_tags(db, "milestone", milestone.id, payload.tags)
    db.commit()
    db.refresh(milestone)
    return _milestone_out(db, milestone)


@router.delete("/milestones/{milestone_id}", status_code=204)
def delete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    milestone = _get_milestone_or_404(db, milestone_id)
    entity_links.delete_links_for_entity(db, "milestone", milestone_id)
    entity_links.delete_relations_for_entity(db, "milestone", milestone_id)
    db.delete(milestone)
    db.commit()
