"""Capacity Planning Core (Phase 19, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt
14-19). Grundsatz "Demand ≠ Assignment": ResourceDemand wird zunächst unabhängig von
konkreten Personen geplant, erst ResourceAssignment ordnet ihn Personen zu.
Folgt demselben CRUD-Muster wie routers/people.py/planning.py."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import capacity_calc, models, schemas
from ..database import get_db

router = APIRouter(tags=["capacity"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


def _get_person_or_404(db: Session, person_id: int) -> models.Person:
    person = db.get(models.Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person nicht gefunden")
    return person


# ---------------------------------------------------------------------------
# ResourceRole
# ---------------------------------------------------------------------------


@router.get("/resource-roles", response_model=list[schemas.ResourceRoleOut])
def list_resource_roles(db: Session = Depends(get_db)):
    return db.query(models.ResourceRole).order_by(models.ResourceRole.name).all()


@router.post("/resource-roles", response_model=schemas.ResourceRoleOut, status_code=201)
def create_resource_role(payload: schemas.ResourceRoleCreate, db: Session = Depends(get_db)):
    existing = db.query(models.ResourceRole).filter(models.ResourceRole.name == payload.name).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ressourcenrolle mit diesem Namen existiert bereits")
    role = models.ResourceRole(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.put("/resource-roles/{role_id}", response_model=schemas.ResourceRoleOut)
def update_resource_role(role_id: int, payload: schemas.ResourceRoleUpdate, db: Session = Depends(get_db)):
    role = db.get(models.ResourceRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Ressourcenrolle nicht gefunden")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return role


# ---------------------------------------------------------------------------
# Skill & PersonSkill
# ---------------------------------------------------------------------------


@router.get("/skills", response_model=list[schemas.SkillOut])
def list_skills(db: Session = Depends(get_db)):
    return db.query(models.Skill).order_by(models.Skill.name).all()


@router.post("/skills", response_model=schemas.SkillOut, status_code=201)
def create_skill(payload: schemas.SkillCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Skill).filter(models.Skill.name == payload.name).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Skill mit diesem Namen existiert bereits")
    skill = models.Skill(**payload.model_dump())
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.put("/skills/{skill_id}", response_model=schemas.SkillOut)
def update_skill(skill_id: int, payload: schemas.SkillUpdate, db: Session = Depends(get_db)):
    skill = db.get(models.Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill nicht gefunden")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(skill, field, value)
    db.commit()
    db.refresh(skill)
    return skill


def _person_skill_out(ps: models.PersonSkill, skill_name: str) -> schemas.PersonSkillOut:
    return schemas.PersonSkillOut(
        id=ps.id, person_id=ps.person_id, skill_id=ps.skill_id, skill_name=skill_name, level=ps.level
    )


@router.get("/people/{person_id}/skills", response_model=list[schemas.PersonSkillOut])
def list_person_skills(person_id: int, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    rows = (
        db.query(models.PersonSkill, models.Skill.name)
        .join(models.Skill, models.Skill.id == models.PersonSkill.skill_id)
        .filter(models.PersonSkill.person_id == person_id)
        .order_by(models.Skill.name)
        .all()
    )
    return [_person_skill_out(ps, skill_name) for ps, skill_name in rows]


@router.post("/people/{person_id}/skills", response_model=schemas.PersonSkillOut, status_code=201)
def add_person_skill(person_id: int, payload: schemas.PersonSkillCreate, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    skill = db.get(models.Skill, payload.skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill nicht gefunden")
    existing = (
        db.query(models.PersonSkill)
        .filter(models.PersonSkill.person_id == person_id, models.PersonSkill.skill_id == payload.skill_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Person hat diesen Skill bereits")
    person_skill = models.PersonSkill(person_id=person_id, skill_id=payload.skill_id, level=payload.level)
    db.add(person_skill)
    db.commit()
    db.refresh(person_skill)
    return _person_skill_out(person_skill, skill.name)


@router.delete("/person-skills/{person_skill_id}", status_code=204)
def delete_person_skill(person_skill_id: int, db: Session = Depends(get_db)):
    person_skill = db.get(models.PersonSkill, person_skill_id)
    if person_skill is None:
        raise HTTPException(status_code=404, detail="Person-Skill-Zuordnung nicht gefunden")
    db.delete(person_skill)
    db.commit()


# ---------------------------------------------------------------------------
# ResourceDemand
# ---------------------------------------------------------------------------


def _resource_demand_out(db: Session, demand: models.ResourceDemand) -> schemas.ResourceDemandOut:
    role = db.get(models.ResourceRole, demand.resource_role_id)
    assignments = (
        db.query(models.ResourceAssignment)
        .filter(models.ResourceAssignment.resource_demand_id == demand.id)
        .all()
    )
    assigned_fte = round(sum(a.fte for a in assignments), 2)
    return schemas.ResourceDemandOut(
        id=demand.id,
        project_id=demand.project_id,
        plan_phase_id=demand.plan_phase_id,
        resource_role_id=demand.resource_role_id,
        resource_role_name=role.name if role else "",
        period=demand.period,
        fte=demand.fte,
        commitment_level=demand.commitment_level,
        erstellt_am=demand.erstellt_am,
        aktualisiert_am=demand.aktualisiert_am,
        assigned_fte=assigned_fte,
        allocation_gap=round(demand.fte - assigned_fte, 2),
    )


def _get_resource_demand_or_404(db: Session, demand_id: int) -> models.ResourceDemand:
    demand = db.get(models.ResourceDemand, demand_id)
    if demand is None:
        raise HTTPException(status_code=404, detail="Ressourcenbedarf nicht gefunden")
    return demand


def _check_plan_phase(db: Session, project_id: int, plan_phase_id: int | None) -> None:
    if plan_phase_id is None:
        return
    plan_phase = db.get(models.PlanPhase, plan_phase_id)
    if plan_phase is None:
        raise HTTPException(status_code=404, detail="Planphase nicht gefunden")
    if plan_phase.project_id != project_id:
        raise HTTPException(status_code=422, detail="plan_phase_id muss zum selben Projekt gehören")


def _check_resource_role(db: Session, resource_role_id: int) -> None:
    if db.get(models.ResourceRole, resource_role_id) is None:
        raise HTTPException(status_code=404, detail="Ressourcenrolle nicht gefunden")


@router.get("/projects/{project_id}/resource-demands", response_model=list[schemas.ResourceDemandOut])
def list_resource_demands(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.ResourceDemand)
        .filter(models.ResourceDemand.project_id == project_id)
        .order_by(models.ResourceDemand.period, models.ResourceDemand.id)
        .all()
    )
    return [_resource_demand_out(db, d) for d in rows]


@router.post("/projects/{project_id}/resource-demands", response_model=schemas.ResourceDemandOut, status_code=201)
def create_resource_demand(project_id: int, payload: schemas.ResourceDemandCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    _check_plan_phase(db, project_id, payload.plan_phase_id)
    _check_resource_role(db, payload.resource_role_id)
    now = _now()
    demand = models.ResourceDemand(
        project_id=project_id,
        plan_phase_id=payload.plan_phase_id,
        resource_role_id=payload.resource_role_id,
        period=payload.period,
        fte=payload.fte,
        commitment_level=payload.commitment_level,
        erstellt_am=now,
        aktualisiert_am=now,
    )
    db.add(demand)
    db.commit()
    db.refresh(demand)
    return _resource_demand_out(db, demand)


@router.put("/projects/resource-demands/{demand_id}", response_model=schemas.ResourceDemandOut)
def update_resource_demand(demand_id: int, payload: schemas.ResourceDemandUpdate, db: Session = Depends(get_db)):
    demand = _get_resource_demand_or_404(db, demand_id)
    changes = payload.model_dump(exclude_unset=True)
    if "plan_phase_id" in changes:
        _check_plan_phase(db, demand.project_id, changes["plan_phase_id"])
    if "resource_role_id" in changes:
        _check_resource_role(db, changes["resource_role_id"])
    if changes:
        for field, value in changes.items():
            setattr(demand, field, value)
        demand.aktualisiert_am = _now()
    db.commit()
    db.refresh(demand)
    return _resource_demand_out(db, demand)


@router.delete("/projects/resource-demands/{demand_id}", status_code=204)
def delete_resource_demand(demand_id: int, db: Session = Depends(get_db)):
    _get_resource_demand_or_404(db, demand_id)
    db.query(models.ResourceAssignment).filter(models.ResourceAssignment.resource_demand_id == demand_id).delete()
    db.query(models.ResourceDemand).filter(models.ResourceDemand.id == demand_id).delete()
    db.commit()


# ---------------------------------------------------------------------------
# ResourceAssignment
# ---------------------------------------------------------------------------


def _resource_assignment_out(a: models.ResourceAssignment, person_name: str) -> schemas.ResourceAssignmentOut:
    return schemas.ResourceAssignmentOut(
        id=a.id,
        resource_demand_id=a.resource_demand_id,
        person_id=a.person_id,
        person_name=person_name,
        fte=a.fte,
        erstellt_am=a.erstellt_am,
        aktualisiert_am=a.aktualisiert_am,
    )


@router.get("/resource-demands/{demand_id}/assignments", response_model=list[schemas.ResourceAssignmentOut])
def list_resource_assignments(demand_id: int, db: Session = Depends(get_db)):
    _get_resource_demand_or_404(db, demand_id)
    rows = (
        db.query(models.ResourceAssignment, models.Person.display_name)
        .join(models.Person, models.Person.id == models.ResourceAssignment.person_id)
        .filter(models.ResourceAssignment.resource_demand_id == demand_id)
        .all()
    )
    return [_resource_assignment_out(a, name) for a, name in rows]


@router.post("/resource-demands/{demand_id}/assignments", response_model=schemas.ResourceAssignmentOut, status_code=201)
def create_resource_assignment(demand_id: int, payload: schemas.ResourceAssignmentCreate, db: Session = Depends(get_db)):
    _get_resource_demand_or_404(db, demand_id)
    person = _get_person_or_404(db, payload.person_id)
    existing = (
        db.query(models.ResourceAssignment)
        .filter(
            models.ResourceAssignment.resource_demand_id == demand_id,
            models.ResourceAssignment.person_id == payload.person_id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Person ist diesem Ressourcenbedarf bereits zugeordnet")
    now = _now()
    assignment = models.ResourceAssignment(
        resource_demand_id=demand_id, person_id=payload.person_id, fte=payload.fte, erstellt_am=now, aktualisiert_am=now
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _resource_assignment_out(assignment, person.display_name)


@router.delete("/resource-assignments/{assignment_id}", status_code=204)
def delete_resource_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.get(models.ResourceAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Ressourcenzuordnung nicht gefunden")
    db.delete(assignment)
    db.commit()


# ---------------------------------------------------------------------------
# Kandidaten (Phase 26.3): Personen mit freier Kapazität für einen ResourceDemand -
# einzige echte neue Backend-Logik der Phase 26, sonst reine Wiederverwendung bestehender
# CRUD-Endpunkte. Keine Rollen-/Skill-Filterung möglich (siehe CandidatePersonOut-Docstring).
# ---------------------------------------------------------------------------


@router.get("/resource-demands/{demand_id}/candidates", response_model=list[schemas.CandidatePersonOut])
def list_resource_demand_candidates(demand_id: int, db: Session = Depends(get_db)):
    demand = _get_resource_demand_or_404(db, demand_id)

    already_assigned = {
        a.person_id
        for a in db.query(models.ResourceAssignment.person_id)
        .filter(models.ResourceAssignment.resource_demand_id == demand_id)
        .all()
    }

    # Gleiche Grundmenge wie capacity_calc.compute_capacity_gap: aktive, kapazitätsrelevante
    # Personen mit ResourceProfile.
    persons = (
        db.query(models.Person)
        .join(models.ResourceProfile, models.ResourceProfile.person_id == models.Person.id)
        .filter(models.Person.active.is_(True), models.ResourceProfile.capacity_relevant.is_(True))
        .all()
    )

    candidates: list[schemas.CandidatePersonOut] = []
    for person in persons:
        if person.id in already_assigned:
            continue
        capacity = capacity_calc.compute_person_capacity(db, person.id, demand.period)
        if capacity is None or capacity.available_fte <= 0:
            continue
        skill_rows = (
            db.query(models.Skill.name)
            .join(models.PersonSkill, models.PersonSkill.skill_id == models.Skill.id)
            .filter(models.PersonSkill.person_id == person.id)
            .order_by(models.Skill.name)
            .all()
        )
        candidates.append(
            schemas.CandidatePersonOut(
                person_id=person.id,
                display_name=person.display_name,
                available_fte=capacity.available_fte,
                skills=[name for (name,) in skill_rows],
            )
        )

    candidates.sort(key=lambda c: c.available_fte, reverse=True)
    return candidates
