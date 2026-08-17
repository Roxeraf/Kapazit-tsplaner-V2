"""Baseline Management (Phase 18, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 12).
Friert die aktuellen PlanPhase-/Milestone-Felder eines Projekts als benannten BaselineSnapshot
ein, damit spätere Forecasts dagegen verglichen werden können (Schedule-/Milestone-
Abweichungen). Folgt demselben CRUD-Muster wie routers/planning.py/communication.py."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import baseline_calc, models, schemas
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["baselines"])

# Welche Felder je entity_type beim Erstellen eines Snapshots eingefroren werden (Master-MD
# Abschnitt 9/10: Baseline/Forecast/Status/Progress je PlanPhase, Baseline/Forecast/Status je
# Milestone). Nur PlanPhase/Milestone sind baseline-fähig, siehe CONCEPT.md Abschnitt 12.3
# Frage 5 - keine strukturierte Baseline für das Legacy-Gantt-Grid.
_SNAPSHOT_FIELDS: dict[str, list[str]] = {
    "plan_phase": ["phase_type", "baseline_start", "baseline_end", "forecast_start", "forecast_end", "status", "progress"],
    "milestone": ["name", "baseline_date", "forecast_date", "status"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


def _get_baseline_or_404(db: Session, baseline_id: int) -> models.BaselineSnapshot:
    snapshot = db.get(models.BaselineSnapshot, baseline_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Baseline nicht gefunden")
    return snapshot


def _entry_out(e: models.BaselineEntry) -> schemas.BaselineEntryOut:
    return schemas.BaselineEntryOut(id=e.id, entity_type=e.entity_type, entity_id=e.entity_id, field=e.field, value=e.value)


def _snapshot_out(db: Session, s: models.BaselineSnapshot) -> schemas.BaselineSnapshotOut:
    entries = db.query(models.BaselineEntry).filter(models.BaselineEntry.baseline_id == s.id).all()
    return schemas.BaselineSnapshotOut(
        id=s.id,
        project_id=s.project_id,
        name=s.name,
        created_at=s.created_at,
        created_by_person_id=s.created_by_person_id,
        entries=[_entry_out(e) for e in entries],
    )


@router.get("/{project_id}/baselines", response_model=list[schemas.BaselineSnapshotSummary])
def list_baselines(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    snapshots = (
        db.query(models.BaselineSnapshot)
        .filter(models.BaselineSnapshot.project_id == project_id)
        .order_by(models.BaselineSnapshot.created_at.desc())
        .all()
    )
    result = []
    for s in snapshots:
        entry_count = (
            db.query(models.BaselineEntry).filter(models.BaselineEntry.baseline_id == s.id).count()
        )
        result.append(
            schemas.BaselineSnapshotSummary(
                id=s.id,
                project_id=s.project_id,
                name=s.name,
                created_at=s.created_at,
                created_by_person_id=s.created_by_person_id,
                entry_count=entry_count,
            )
        )
    return result


@router.post("/{project_id}/baselines", response_model=schemas.BaselineSnapshotOut, status_code=201)
def create_baseline(project_id: int, payload: schemas.BaselineSnapshotCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    if payload.created_by_person_id is not None and db.get(models.Person, payload.created_by_person_id) is None:
        raise HTTPException(status_code=404, detail="Person (created_by_person_id) nicht gefunden")

    snapshot = models.BaselineSnapshot(
        project_id=project_id, name=payload.name, created_at=_now(), created_by_person_id=payload.created_by_person_id
    )
    db.add(snapshot)
    db.flush()

    plan_phases = db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id).all()
    for plan_phase in plan_phases:
        for field in _SNAPSHOT_FIELDS["plan_phase"]:
            value = getattr(plan_phase, field)
            db.add(
                models.BaselineEntry(
                    baseline_id=snapshot.id,
                    entity_type="plan_phase",
                    entity_id=plan_phase.id,
                    field=field,
                    value=str(value) if value is not None else None,
                )
            )

    milestones = db.query(models.Milestone).filter(models.Milestone.project_id == project_id).all()
    for milestone in milestones:
        for field in _SNAPSHOT_FIELDS["milestone"]:
            value = getattr(milestone, field)
            db.add(
                models.BaselineEntry(
                    baseline_id=snapshot.id,
                    entity_type="milestone",
                    entity_id=milestone.id,
                    field=field,
                    value=str(value) if value is not None else None,
                )
            )

    db.commit()
    db.refresh(snapshot)
    return _snapshot_out(db, snapshot)


@router.get("/baselines/{baseline_id}", response_model=schemas.BaselineSnapshotOut)
def get_baseline(baseline_id: int, db: Session = Depends(get_db)):
    snapshot = _get_baseline_or_404(db, baseline_id)
    return _snapshot_out(db, snapshot)


@router.delete("/baselines/{baseline_id}", status_code=204)
def delete_baseline(baseline_id: int, db: Session = Depends(get_db)):
    _get_baseline_or_404(db, baseline_id)
    db.query(models.BaselineEntry).filter(models.BaselineEntry.baseline_id == baseline_id).delete()
    db.query(models.BaselineSnapshot).filter(models.BaselineSnapshot.id == baseline_id).delete()
    db.commit()


@router.get("/baselines/{baseline_id}/deviations", response_model=list[schemas.BaselineDeviationOut])
def get_baseline_deviations(baseline_id: int, db: Session = Depends(get_db)):
    """Berechnung in baseline_calc.py (Phase 23, dort auch von routers/controlling.py für die
    portfolioweiten Baseline Deviations genutzt)."""
    _get_baseline_or_404(db, baseline_id)
    return baseline_calc.compute_deviations(db, baseline_id)
