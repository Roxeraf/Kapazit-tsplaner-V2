from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import jira_sync, models, schemas
from ..constants import PHASE_CODES, berechne_monate
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


def _phasen_dict(gantt_phases) -> dict[str, list[str]]:
    phasen: dict[str, list[str]] = {}
    for gp in gantt_phases:
        phasen.setdefault(gp.monat, []).append(gp.phase_code)
    return phasen


def _subproject_detail(sp: models.Subproject) -> schemas.SubprojectDetail:
    fte = {f.monat: f.wert_soll for f in sp.fte_plan}
    return schemas.SubprojectDetail(
        id=sp.id,
        name=sp.name,
        reihenfolge=sp.reihenfolge,
        phasen=_phasen_dict(sp.gantt_phases),
        fte=fte,
    )


def _project_phasen(p: models.Project) -> dict[str, list[str]]:
    """Gantt-Phasen auf Projekt-Ebene.

    Hat das Projekt Teilprojekte, ist die Projekt-Zeile die Zusammenfassung daraus (ein Monat
    zeigt Phase X, wenn mindestens ein Teilprojekt sie hat) statt einer eigenen, unabhängigen
    Eintragung — konsistent zur FTE-Summe in _project_fte(). Ohne Teilprojekte bleibt die direkt
    am Projekt gepflegte Phasenliste (project_gantt_phases) maßgeblich.
    """
    if p.subprojects:
        union: dict[str, set[str]] = {}
        for sp in p.subprojects:
            for gp in sp.gantt_phases:
                union.setdefault(gp.monat, set()).add(gp.phase_code)
        return {monat: sorted(codes) for monat, codes in union.items()}
    return _phasen_dict(p.gantt_phases)


def _project_fte(p: models.Project) -> dict[str, float]:
    """FTE-Soll auf Projekt-Ebene.

    Hat das Projekt Teilprojekte (Feinplanung), ist die Projekt-Zeile die Summe daraus statt
    eines eigenen manuellen Werts — sonst könnten Projekt- und Teilprojekt-Ebene auseinanderlaufen.
    Ohne Teilprojekte bleibt der manuell auf Projekt-Ebene eingetragene Wert (project_fte_plan)
    maßgeblich (siehe PUT /projects/{id}/fte).
    """
    if p.subprojects:
        summe: dict[str, float] = {}
        for sp in p.subprojects:
            for f in sp.fte_plan:
                summe[f.monat] = summe.get(f.monat, 0) + f.wert_soll
        return {monat: round(wert, 2) for monat, wert in summe.items()}
    return {f.monat: f.wert_soll for f in p.fte_plan}


def _project_detail(db: Session, p: models.Project) -> schemas.ProjectDetail:
    return schemas.ProjectDetail(
        id=p.id,
        name=p.name,
        kunde=p.kunde,
        start_monat=p.start_monat,
        anzahl_monate=p.anzahl_monate,
        monate=berechne_monate(p.start_monat, p.anzahl_monate),
        jira_component=p.jira_component,
        jira_project_key=p.jira_project_key,
        phasen=_project_phasen(p),
        fte=_project_fte(p),
        aus_teilprojekten=bool(p.subprojects),
        ist=jira_sync.berechne_ist_fte(db, p),
        subprojects=[_subproject_detail(sp) for sp in p.subprojects],
    )


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


def _get_subproject_or_404(db: Session, subproject_id: int) -> models.Subproject:
    sp = db.get(models.Subproject, subproject_id)
    if sp is None:
        raise HTTPException(status_code=404, detail="Teilprojekt nicht gefunden")
    return sp


@router.get("", response_model=list[schemas.ProjectSummary])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.id).all()
    return [
        schemas.ProjectSummary(
            id=p.id,
            name=p.name,
            kunde=p.kunde,
            start_monat=p.start_monat,
            anzahl_monate=p.anzahl_monate,
            monate=berechne_monate(p.start_monat, p.anzahl_monate),
        )
        for p in projects
    ]


@router.post("", response_model=schemas.ProjectDetail, status_code=201)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    project = models.Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_detail(db, project)


@router.get("/{project_id}", response_model=schemas.ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    return _project_detail(db, project)


@router.put("/{project_id}", response_model=schemas.ProjectDetail)
def update_project(project_id: int, payload: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return _project_detail(db, project)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()


@router.put("/{project_id}/phasen", response_model=schemas.ProjectDetail)
def set_project_phasen(project_id: int, payload: schemas.PhasenUpdate, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)

    invalid = [c for c in payload.codes if c not in PHASE_CODES]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Ungültige Phasencodes: {invalid}")

    db.query(models.ProjectGanttPhase).filter(
        models.ProjectGanttPhase.project_id == project_id,
        models.ProjectGanttPhase.monat == payload.monat,
    ).delete()
    for code in dict.fromkeys(payload.codes):  # dedupe, Reihenfolge erhalten
        db.add(models.ProjectGanttPhase(project_id=project_id, monat=payload.monat, phase_code=code))
    db.commit()
    db.refresh(project)
    return _project_detail(db, project)


@router.put("/{project_id}/fte", response_model=schemas.ProjectDetail)
def set_project_fte(project_id: int, payload: schemas.FteUpdate, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)

    entry = (
        db.query(models.ProjectFtePlan)
        .filter(models.ProjectFtePlan.project_id == project_id, models.ProjectFtePlan.monat == payload.monat)
        .first()
    )
    if entry is None:
        entry = models.ProjectFtePlan(project_id=project_id, monat=payload.monat, wert_soll=payload.wert_soll)
        db.add(entry)
    else:
        entry.wert_soll = payload.wert_soll
    db.commit()
    db.refresh(project)
    return _project_detail(db, project)


@router.get("/subprojects/all", response_model=list[schemas.SubprojectListItem])
def list_all_subprojects(db: Session = Depends(get_db)):
    """Flache Liste aller Teilprojekte (für die Zuordnung MA <-> Teilprojekt, siehe /team)."""
    rows = (
        db.query(models.Subproject)
        .join(models.Project)
        .order_by(models.Project.name, models.Subproject.reihenfolge)
        .all()
    )
    return [
        schemas.SubprojectListItem(
            id=sp.id, name=sp.name, project_id=sp.project_id, project_name=sp.project.name
        )
        for sp in rows
    ]


@router.post("/{project_id}/subprojects", response_model=schemas.SubprojectDetail, status_code=201)
def create_subproject(project_id: int, payload: schemas.SubprojectCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    sp = models.Subproject(project_id=project_id, **payload.model_dump())
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return _subproject_detail(sp)


@router.put("/subprojects/{subproject_id}", response_model=schemas.SubprojectDetail)
def update_subproject(subproject_id: int, payload: schemas.SubprojectUpdate, db: Session = Depends(get_db)):
    sp = _get_subproject_or_404(db, subproject_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sp, field, value)
    db.commit()
    db.refresh(sp)
    return _subproject_detail(sp)


@router.delete("/subprojects/{subproject_id}", status_code=204)
def delete_subproject(subproject_id: int, db: Session = Depends(get_db)):
    sp = _get_subproject_or_404(db, subproject_id)
    db.delete(sp)
    db.commit()


@router.put("/subprojects/{subproject_id}/phasen", response_model=schemas.SubprojectDetail)
def set_phasen(subproject_id: int, payload: schemas.PhasenUpdate, db: Session = Depends(get_db)):
    sp = _get_subproject_or_404(db, subproject_id)

    invalid = [c for c in payload.codes if c not in PHASE_CODES]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Ungültige Phasencodes: {invalid}")

    db.query(models.GanttPhase).filter(
        models.GanttPhase.subproject_id == subproject_id,
        models.GanttPhase.monat == payload.monat,
    ).delete()
    for code in dict.fromkeys(payload.codes):  # dedupe, Reihenfolge erhalten
        db.add(models.GanttPhase(subproject_id=subproject_id, monat=payload.monat, phase_code=code))
    db.commit()
    db.refresh(sp)
    return _subproject_detail(sp)


@router.put("/subprojects/{subproject_id}/fte", response_model=schemas.SubprojectDetail)
def set_fte(subproject_id: int, payload: schemas.FteUpdate, db: Session = Depends(get_db)):
    sp = _get_subproject_or_404(db, subproject_id)

    entry = (
        db.query(models.FtePlan)
        .filter(models.FtePlan.subproject_id == subproject_id, models.FtePlan.monat == payload.monat)
        .first()
    )
    if entry is None:
        entry = models.FtePlan(subproject_id=subproject_id, monat=payload.monat, wert_soll=payload.wert_soll)
        db.add(entry)
    else:
        entry.wert_soll = payload.wert_soll
    db.commit()
    db.refresh(sp)
    return _subproject_detail(sp)
