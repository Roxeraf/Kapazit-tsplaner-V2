"""GAP Engine (Phase 21, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 21/22).
Verbindet Projektplanung (PlanPhase/Milestone, Phase 17) + Kapazitätsplanung (ResourceDemand,
Phase 19; Available Capacity, Phase 20) + Ist-Daten (Jira, bestehend) + Forecast zu den in der
Master-MD Abschnitt 22 definierten GAP-Arten. Rein berechnete Endpunkte, keine neuen Tabellen
- die bestehende Soll-/Ist-Logik (gap_analysis.py) wird für den Effort Gap wiederverwendet,
nicht ersetzt ("Bestehende Soll-/Ist-Logik wird nicht entfernt, sondern integriert.")."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import capacity_calc, gap_analysis, models, schemas
from ..database import get_db

router = APIRouter(tags=["gap-engine"])


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


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Capacity Gap = Available Capacity - Resource Demand
# ---------------------------------------------------------------------------


@router.get("/gap-engine/capacity", response_model=schemas.CapacityGapOut)
def get_capacity_gap(period: str, resource_role_id: int | None = None, db: Session = Depends(get_db)):
    """Portfolioweit über alle kapazitätsrelevanten Personen, da es keine
    Person<->ResourceRole-Zuordnung im Datenmodell gibt - resource_role_id filtert nur die
    Bedarfsseite (siehe schemas.CapacityGapOut)."""
    demand_query = db.query(models.ResourceDemand).filter(models.ResourceDemand.period == period)
    if resource_role_id is not None:
        demand_query = demand_query.filter(models.ResourceDemand.resource_role_id == resource_role_id)
    demand_fte = round(sum(d.fte for d in demand_query.all()), 2)

    persons = (
        db.query(models.Person)
        .join(models.ResourceProfile, models.ResourceProfile.person_id == models.Person.id)
        .filter(models.Person.active.is_(True), models.ResourceProfile.capacity_relevant.is_(True))
        .all()
    )
    available_fte = 0.0
    considered = 0
    for person in persons:
        result = capacity_calc.compute_person_capacity(db, person.id, period)
        if result is not None:
            available_fte += result.available_fte
            considered += 1

    return schemas.CapacityGapOut(
        period=period,
        resource_role_id=resource_role_id,
        demand_fte=demand_fte,
        available_fte=round(available_fte, 2),
        capacity_gap_fte=round(available_fte - demand_fte, 2),
        persons_considered=considered,
    )


# ---------------------------------------------------------------------------
# Effort Gap = bestehende Soll-/Ist-Logik (gap_analysis.py), hier nur unter der GAP-Engine-
# Terminologie zugänglich gemacht - keine Logikänderung.
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/gaps/effort", response_model=schemas.GapAnalysis)
def get_effort_gap(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    return gap_analysis.project_gap(db, project)


# ---------------------------------------------------------------------------
# Schedule Gap (live) = Baseline vs Forecast vs Actual je PlanPhase/Milestone. Ergänzt die
# Snapshot-basierten Deviations aus Phase 18 (backend/app/routers/baselines.py) um eine
# Live-Sicht ohne BaselineSnapshot.
# ---------------------------------------------------------------------------


def _schedule_gap_entries(db: Session, project_id: int) -> list[schemas.ScheduleGapEntry]:
    entries: list[schemas.ScheduleGapEntry] = []
    for pp in db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id).all():
        baseline = _parse_date(pp.baseline_end) or _parse_date(pp.baseline_start)
        forecast = _parse_date(pp.forecast_end) or _parse_date(pp.forecast_start)
        actual = _parse_date(pp.actual_end) or _parse_date(pp.actual_start)
        entries.append(
            schemas.ScheduleGapEntry(
                entity_type="plan_phase",
                entity_id=pp.id,
                label=pp.phase_type,
                baseline_date=pp.baseline_end or pp.baseline_start,
                forecast_date=pp.forecast_end or pp.forecast_start,
                actual_date=pp.actual_end or pp.actual_start,
                baseline_vs_forecast_days=(forecast - baseline).days if baseline and forecast else None,
                forecast_vs_actual_days=(actual - forecast).days if forecast and actual else None,
            )
        )
    for m in db.query(models.Milestone).filter(models.Milestone.project_id == project_id).all():
        baseline = _parse_date(m.baseline_date)
        forecast = _parse_date(m.forecast_date)
        actual = _parse_date(m.actual_date)
        entries.append(
            schemas.ScheduleGapEntry(
                entity_type="milestone",
                entity_id=m.id,
                label=m.name,
                baseline_date=m.baseline_date,
                forecast_date=m.forecast_date,
                actual_date=m.actual_date,
                baseline_vs_forecast_days=(forecast - baseline).days if baseline and forecast else None,
                forecast_vs_actual_days=(actual - forecast).days if forecast and actual else None,
            )
        )
    return entries


@router.get("/projects/{project_id}/gaps/schedule", response_model=list[schemas.ScheduleGapEntry])
def get_schedule_gap(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    return _schedule_gap_entries(db, project_id)


# ---------------------------------------------------------------------------
# Progress Gap = Expected Progress - Actual Progress (Prozentpunkte)
# ---------------------------------------------------------------------------


def _expected_progress_pct(start: date | None, end: date | None) -> float | None:
    if start is None or end is None or end <= start:
        return None
    today = date.today()
    if today <= start:
        return 0.0
    if today >= end:
        return 100.0
    return round((today - start).days / (end - start).days * 100, 1)


def _progress_gap_entries(db: Session, project_id: int) -> list[schemas.ProgressGapEntry]:
    entries: list[schemas.ProgressGapEntry] = []
    for pp in db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id).all():
        start = _parse_date(pp.forecast_start) or _parse_date(pp.baseline_start)
        end = _parse_date(pp.forecast_end) or _parse_date(pp.baseline_end)
        expected = _expected_progress_pct(start, end)
        actual = pp.progress
        gap = round(actual - expected, 1) if expected is not None and actual is not None else None
        entries.append(
            schemas.ProgressGapEntry(
                plan_phase_id=pp.id,
                label=pp.phase_type,
                expected_progress_pct=expected,
                actual_progress_pct=actual,
                progress_gap_pp=gap,
            )
        )
    return entries


@router.get("/projects/{project_id}/gaps/progress", response_model=list[schemas.ProgressGapEntry])
def get_progress_gap(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    return _progress_gap_entries(db, project_id)


# ---------------------------------------------------------------------------
# Utilization Gap = zugeordnetes FTE (ResourceAssignment, Phase 19) ggü. Available Capacity
# (Phase 20), verglichen mit einer fixen Ziel-Auslastung von 100%.
# ---------------------------------------------------------------------------


@router.get("/people/{person_id}/gaps/utilization", response_model=schemas.UtilizationGapOut)
def get_utilization_gap(person_id: int, period: str, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    assigned_fte = round(
        sum(
            a.fte
            for a in db.query(models.ResourceAssignment)
            .join(models.ResourceDemand, models.ResourceDemand.id == models.ResourceAssignment.resource_demand_id)
            .filter(models.ResourceAssignment.person_id == person_id, models.ResourceDemand.period == period)
            .all()
        ),
        2,
    )
    capacity = capacity_calc.compute_person_capacity(db, person_id, period)
    available_fte = capacity.available_fte if capacity is not None else 0.0
    utilization_pct = round(assigned_fte / available_fte * 100, 1) if available_fte else None
    target_pct = 100.0
    utilization_gap_pp = round(utilization_pct - target_pct, 1) if utilization_pct is not None else None

    return schemas.UtilizationGapOut(
        person_id=person_id,
        period=period,
        assigned_fte=assigned_fte,
        available_fte=available_fte,
        utilization_pct=utilization_pct,
        target_pct=target_pct,
        utilization_gap_pp=utilization_gap_pp,
    )


# ---------------------------------------------------------------------------
# Bündel-Endpoint (einfache Form des Drill-downs, Master-MD Abschnitt 21/25) - der volle
# hierarchische Portfolio-Drill-down (Abschnitt 52) bleibt Controlling (Phase 22/23).
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/gaps", response_model=schemas.ProjectGapsOut)
def get_project_gaps(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    return schemas.ProjectGapsOut(
        project_id=project_id,
        effort=gap_analysis.project_gap(db, project),
        schedule=_schedule_gap_entries(db, project_id),
        progress=_progress_gap_entries(db, project_id),
    )
