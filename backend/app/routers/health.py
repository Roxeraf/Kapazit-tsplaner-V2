"""Project Control & Health (Phase 22, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt
6/49/50). Mehrdimensionales Project Health (health_calc.py) plus Project Control Cockpit
(Master-MD Abschnitt 6) - bündelt bestehende GAP-Engine-/Blocker-/Milestone-/Tag-Daten zu
einer Projektübersicht. Konfigurierbare Schwellwerte über HealthThreshold."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import constants, entity_links, health_calc, models, schemas
from ..database import get_db

router = APIRouter(tags=["health"])


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


# ---------------------------------------------------------------------------
# Konfigurierbare Schwellwerte (Master-MD Abschnitt 50: "Schwellwerte sollen konfigurierbar
# sein"). Effort Health bleibt bewusst außen vor (siehe models.HealthThreshold-Docstring).
# ---------------------------------------------------------------------------


@router.get("/health-thresholds", response_model=list[schemas.HealthThresholdOut])
def list_health_thresholds(db: Session = Depends(get_db)):
    thresholds = {row.metric: row for row in db.query(models.HealthThreshold).all()}
    return [
        thresholds.get(metric) or models.HealthThreshold(metric=metric, yellow=yellow, red=red)
        for metric, (yellow, red) in health_calc.DEFAULT_THRESHOLDS.items()
    ]


@router.put("/health-thresholds/{metric}", response_model=schemas.HealthThresholdOut)
def update_health_threshold(metric: str, payload: schemas.HealthThresholdUpdate, db: Session = Depends(get_db)):
    if metric not in health_calc.DEFAULT_THRESHOLDS:
        raise HTTPException(status_code=404, detail="Unbekannte Health-Metrik")
    threshold = db.query(models.HealthThreshold).filter(models.HealthThreshold.metric == metric).first()
    if threshold is None:
        threshold = models.HealthThreshold(metric=metric, yellow=payload.yellow, red=payload.red)
        db.add(threshold)
    else:
        threshold.yellow = payload.yellow
        threshold.red = payload.red
    db.commit()
    db.refresh(threshold)
    return threshold


# ---------------------------------------------------------------------------
# Project Health
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/health", response_model=schemas.ProjectHealthOut)
def get_project_health(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    return health_calc.compute_project_health(db, project)


# ---------------------------------------------------------------------------
# Project Control Cockpit (Master-MD Abschnitt 6)
# ---------------------------------------------------------------------------


def _current_phase(db: Session, project_id: int) -> str | None:
    today = date.today().isoformat()
    laufend = (
        db.query(models.PlanPhase)
        .filter(models.PlanPhase.project_id == project_id, models.PlanPhase.status == "laufend")
        .first()
    )
    if laufend is not None:
        return laufend.phase_type
    im_zeitraum = (
        db.query(models.PlanPhase)
        .filter(
            models.PlanPhase.project_id == project_id,
            models.PlanPhase.forecast_start <= today,
            models.PlanPhase.forecast_end >= today,
        )
        .first()
    )
    return im_zeitraum.phase_type if im_zeitraum else None


def _forecast_end(db: Session, project_id: int) -> str | None:
    """Spätestes bekanntes Forecast-Ende über PlanPhase und Milestone hinweg - Näherung für
    'Forecast GoLive' aus dem Master-MD-Cockpit-Beispiel (Abschnitt 6). Es gibt kein Flag,
    das einen bestimmten Milestone als GoLive markiert, daher das späteste Forecast-Datum
    als projektweites voraussichtliches Ende."""
    ends = [
        pp.forecast_end
        for pp in db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id).all()
        if pp.forecast_end
    ]
    ends += [
        m.forecast_date
        for m in db.query(models.Milestone).filter(models.Milestone.project_id == project_id).all()
        if m.forecast_date
    ]
    return max(ends) if ends else None


def _cockpit_capacity(db: Session, project_id: int) -> schemas.CockpitCapacity:
    period = constants.current_period()
    demands = (
        db.query(models.ResourceDemand)
        .filter(models.ResourceDemand.project_id == project_id, models.ResourceDemand.period == period)
        .all()
    )
    demand_fte = round(sum(d.fte for d in demands), 2)
    demand_ids = [d.id for d in demands]
    assigned_fte = round(
        sum(
            a.fte
            for a in db.query(models.ResourceAssignment)
            .filter(models.ResourceAssignment.resource_demand_id.in_(demand_ids))
            .all()
        ),
        2,
    )
    return schemas.CockpitCapacity(
        period=period,
        demand_fte=demand_fte,
        assigned_fte=assigned_fte,
        allocation_gap_fte=round(assigned_fte - demand_fte, 2),
    )


def _cockpit_blockers(db: Session, project_id: int) -> schemas.CockpitBlockers:
    open_blockers = (
        db.query(models.Blocker)
        .filter(models.Blocker.project_id == project_id, models.Blocker.status != "geloest")
        .all()
    )
    by_party = {"CUSTOMER": 0, "INTERNAL": 0, "THIRD_PARTY": 0, "UNKNOWN": 0}
    for b in open_blockers:
        by_party[b.caused_by_party] = by_party.get(b.caused_by_party, 0) + 1
    return schemas.CockpitBlockers(
        open_total=len(open_blockers),
        customer=by_party["CUSTOMER"],
        internal=by_party["INTERNAL"],
        third_party=by_party["THIRD_PARTY"],
        unknown=by_party["UNKNOWN"],
    )


def _cockpit_tasks(db: Session, project_id: int) -> schemas.CockpitTasks:
    today = date.today().isoformat()
    open_tasks = (
        db.query(models.Task)
        .filter(models.Task.project_id == project_id, models.Task.status != "erledigt")
        .all()
    )
    overdue = sum(1 for t in open_tasks if t.faellig_am and t.faellig_am < today)
    return schemas.CockpitTasks(open_total=len(open_tasks), overdue=overdue)


def _project_tags(db: Session, project_id: int) -> list[str]:
    """Tags aller taggable Entitäten des Projekts (Blocker/PlanPhase/Milestone/Task/Risk/
    Decision/MeetingMinutes/Comment) - 'Aktuelle Themen' im Cockpit (Master-MD Abschnitt 6).
    Nutzt den bestehenden Knowledge Query Layer (entity_links.py, Phase 15) statt eigener
    Tag-Abfragen."""
    names: set[str] = set()
    for entity_type in entity_links.ENTITY_TYPES:
        for summary in entity_links.list_entity_summaries(db, entity_type, project_id):
            names.update(summary["tags"])
    return sorted(names)


@router.get("/projects/{project_id}/cockpit", response_model=schemas.ProjectControlCockpitOut)
def get_project_cockpit(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    milestones = (
        db.query(models.Milestone)
        .filter(models.Milestone.project_id == project_id)
        .order_by(models.Milestone.baseline_date, models.Milestone.id)
        .all()
    )
    projektleiter_person = (
        db.get(models.Person, project.projektleiter_person_id) if project.projektleiter_person_id else None
    )
    return schemas.ProjectControlCockpitOut(
        project_id=project.id,
        project_name=project.name,
        kunde=project.kunde,
        projektleiter=projektleiter_person.display_name if projektleiter_person else None,
        health=health_calc.compute_project_health(db, project),
        current_phase=_current_phase(db, project_id),
        forecast_end=_forecast_end(db, project_id),
        milestones=[
            schemas.CockpitMilestoneEntry(
                id=m.id,
                name=m.name,
                baseline_date=m.baseline_date,
                forecast_date=m.forecast_date,
                actual_date=m.actual_date,
                status=m.status,
            )
            for m in milestones
        ],
        capacity=_cockpit_capacity(db, project_id),
        blockers=_cockpit_blockers(db, project_id),
        tasks=_cockpit_tasks(db, project_id),
        tags=_project_tags(db, project_id),
    )
