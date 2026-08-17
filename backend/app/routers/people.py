"""Personen, Organisation & Permissions (Phase 14 der Kapazitätsplaner-v2-Zielarchitektur,
siehe CONCEPT.md Abschnitt 12). Person ist bewusst schlank (kein Auth/Login) und getrennt von
TeamMember (Kapazitätsressource, siehe routers/team.py) - Migrationspfad TeamMember->Person
ist Best-Effort und additiv (siehe alembic/versions/0003_*.py), keine der beiden Tabellen
wird hier ersetzt."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(tags=["people"])


def _get_person_or_404(db: Session, person_id: int) -> models.Person:
    person = db.get(models.Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person nicht gefunden")
    return person


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


# ---------------------------------------------------------------------------
# Person
# ---------------------------------------------------------------------------


@router.get("/people", response_model=list[schemas.PersonOut])
def list_people(active: bool | None = None, search: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Person)
    if active is not None:
        query = query.filter(models.Person.active == active)
    if search:
        query = query.filter(models.Person.display_name.ilike(f"%{search}%"))
    return query.order_by(models.Person.display_name).all()


@router.post("/people", response_model=schemas.PersonOut, status_code=201)
def create_person(payload: schemas.PersonCreate, db: Session = Depends(get_db)):
    person = models.Person(**payload.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.put("/people/{person_id}", response_model=schemas.PersonOut)
def update_person(person_id: int, payload: schemas.PersonUpdate, db: Session = Depends(get_db)):
    person = _get_person_or_404(db, person_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(person, field, value)
    db.commit()
    db.refresh(person)
    return person


# ---------------------------------------------------------------------------
# ResourceProfile (höchstens eines je Person)
# ---------------------------------------------------------------------------


@router.get("/people/{person_id}/resource-profile", response_model=schemas.ResourceProfileOut | None)
def get_resource_profile(person_id: int, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    return db.query(models.ResourceProfile).filter(models.ResourceProfile.person_id == person_id).first()


@router.post("/people/{person_id}/resource-profile", response_model=schemas.ResourceProfileOut, status_code=201)
def create_resource_profile(person_id: int, payload: schemas.ResourceProfileCreate, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    existing = db.query(models.ResourceProfile).filter(models.ResourceProfile.person_id == person_id).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Person hat bereits ein ResourceProfile")
    profile = models.ResourceProfile(person_id=person_id, **payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/people/{person_id}/resource-profile", response_model=schemas.ResourceProfileOut)
def update_resource_profile(person_id: int, payload: schemas.ResourceProfileUpdate, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    profile = db.query(models.ResourceProfile).filter(models.ResourceProfile.person_id == person_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="ResourceProfile nicht gefunden")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# ProjectRole
# ---------------------------------------------------------------------------


@router.get("/project-roles", response_model=list[schemas.ProjectRoleOut])
def list_project_roles(db: Session = Depends(get_db)):
    return db.query(models.ProjectRole).order_by(models.ProjectRole.name).all()


@router.post("/project-roles", response_model=schemas.ProjectRoleOut, status_code=201)
def create_project_role(payload: schemas.ProjectRoleCreate, db: Session = Depends(get_db)):
    existing = db.query(models.ProjectRole).filter(models.ProjectRole.name == payload.name).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Projektrolle mit diesem Namen existiert bereits")
    role = models.ProjectRole(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.put("/project-roles/{role_id}", response_model=schemas.ProjectRoleOut)
def update_project_role(role_id: int, payload: schemas.ProjectRoleUpdate, db: Session = Depends(get_db)):
    role = db.get(models.ProjectRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Projektrolle nicht gefunden")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return role


# ---------------------------------------------------------------------------
# ProjectMembership
# ---------------------------------------------------------------------------


def _membership_out(m: models.ProjectMembership) -> schemas.ProjectMembershipOut:
    return schemas.ProjectMembershipOut(
        id=m.id,
        project_id=m.project_id,
        person_id=m.person_id,
        person_name=m.person.display_name,
        project_role_id=m.project_role_id,
        project_role_name=m.project_role.name,
    )


@router.get("/projects/{project_id}/memberships", response_model=list[schemas.ProjectMembershipOut])
def list_project_memberships(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    memberships = (
        db.query(models.ProjectMembership).filter(models.ProjectMembership.project_id == project_id).all()
    )
    return [_membership_out(m) for m in memberships]


@router.post("/projects/{project_id}/memberships", response_model=schemas.ProjectMembershipOut, status_code=201)
def create_project_membership(
    project_id: int, payload: schemas.ProjectMembershipCreate, db: Session = Depends(get_db)
):
    _get_project_or_404(db, project_id)
    _get_person_or_404(db, payload.person_id)
    if db.get(models.ProjectRole, payload.project_role_id) is None:
        raise HTTPException(status_code=404, detail="Projektrolle nicht gefunden")
    existing = (
        db.query(models.ProjectMembership)
        .filter(
            models.ProjectMembership.project_id == project_id,
            models.ProjectMembership.person_id == payload.person_id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Person ist diesem Projekt bereits zugeordnet")
    membership = models.ProjectMembership(
        project_id=project_id, person_id=payload.person_id, project_role_id=payload.project_role_id
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return _membership_out(membership)


@router.delete("/project-memberships/{membership_id}", status_code=204)
def delete_project_membership(membership_id: int, db: Session = Depends(get_db)):
    membership = db.get(models.ProjectMembership, membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Projektzuordnung nicht gefunden")
    db.delete(membership)
    db.commit()


# ---------------------------------------------------------------------------
# Permission (read-only, per Migration geseedet - siehe Master-MD Abschnitt 31) & AppRole
# ---------------------------------------------------------------------------


@router.get("/permissions", response_model=list[schemas.PermissionOut])
def list_permissions(db: Session = Depends(get_db)):
    return db.query(models.Permission).order_by(models.Permission.name).all()


def _app_role_out(db: Session, role: models.AppRole) -> schemas.AppRoleOut:
    permission_names = (
        db.query(models.Permission.name)
        .join(models.RolePermission, models.RolePermission.permission_id == models.Permission.id)
        .filter(models.RolePermission.role_id == role.id)
        .order_by(models.Permission.name)
        .all()
    )
    return schemas.AppRoleOut(
        id=role.id, name=role.name, description=role.description, permissions=[p[0] for p in permission_names]
    )


@router.get("/app-roles", response_model=list[schemas.AppRoleOut])
def list_app_roles(db: Session = Depends(get_db)):
    roles = db.query(models.AppRole).order_by(models.AppRole.name).all()
    return [_app_role_out(db, r) for r in roles]


@router.post("/app-roles", response_model=schemas.AppRoleOut, status_code=201)
def create_app_role(payload: schemas.AppRoleCreate, db: Session = Depends(get_db)):
    existing = db.query(models.AppRole).filter(models.AppRole.name == payload.name).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="App-Rolle mit diesem Namen existiert bereits")
    role = models.AppRole(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return _app_role_out(db, role)


@router.put("/app-roles/{role_id}", response_model=schemas.AppRoleOut)
def update_app_role(role_id: int, payload: schemas.AppRoleUpdate, db: Session = Depends(get_db)):
    role = db.get(models.AppRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="App-Rolle nicht gefunden")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return _app_role_out(db, role)


@router.post("/app-roles/{role_id}/permissions/{permission_id}", response_model=schemas.AppRoleOut, status_code=201)
def add_permission_to_role(role_id: int, permission_id: int, db: Session = Depends(get_db)):
    role = db.get(models.AppRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="App-Rolle nicht gefunden")
    if db.get(models.Permission, permission_id) is None:
        raise HTTPException(status_code=404, detail="Permission nicht gefunden")
    existing = (
        db.query(models.RolePermission)
        .filter(models.RolePermission.role_id == role_id, models.RolePermission.permission_id == permission_id)
        .first()
    )
    if existing is None:
        db.add(models.RolePermission(role_id=role_id, permission_id=permission_id))
        db.commit()
    return _app_role_out(db, role)


@router.delete("/app-roles/{role_id}/permissions/{permission_id}", response_model=schemas.AppRoleOut)
def remove_permission_from_role(role_id: int, permission_id: int, db: Session = Depends(get_db)):
    role = db.get(models.AppRole, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="App-Rolle nicht gefunden")
    db.query(models.RolePermission).filter(
        models.RolePermission.role_id == role_id, models.RolePermission.permission_id == permission_id
    ).delete()
    db.commit()
    return _app_role_out(db, role)
