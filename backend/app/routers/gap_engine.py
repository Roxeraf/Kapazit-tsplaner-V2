"""GAP Engine (Phase 21, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 21/22).
Verbindet Projektplanung (PlanPhase/Milestone, Phase 17) + Kapazitätsplanung (ResourceDemand,
Phase 19; Available Capacity, Phase 20) + Ist-Daten (Jira, bestehend) + Forecast zu den in der
Master-MD Abschnitt 22 definierten GAP-Arten. Rein berechnete Endpunkte, keine neuen Tabellen
- die bestehende Soll-/Ist-Logik (gap_analysis.py) wird für den Effort Gap wiederverwendet,
nicht ersetzt ("Bestehende Soll-/Ist-Logik wird nicht entfernt, sondern integriert.")."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import capacity_calc, gap_analysis, gap_calc, models, schemas
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


# ---------------------------------------------------------------------------
# Capacity Gap = Available Capacity - Resource Demand
# ---------------------------------------------------------------------------


@router.get("/gap-engine/capacity", response_model=schemas.CapacityGapOut)
def get_capacity_gap(period: str, resource_role_id: int | None = None, db: Session = Depends(get_db)):
    """Portfolioweit über alle kapazitätsrelevanten Personen, da es keine
    Person<->ResourceRole-Zuordnung im Datenmodell gibt - resource_role_id filtert nur die
    Bedarfsseite. Berechnung in capacity_calc.py (Phase 23, dort auch von
    routers/controlling.py für die Capacity Heatmap genutzt)."""
    return capacity_calc.compute_capacity_gap(db, period, resource_role_id)


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
# Live-Sicht ohne BaselineSnapshot. Berechnung in gap_calc.py (Phase 22, dort auch von
# health_calc.py für die Schedule Health genutzt).
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/gaps/schedule", response_model=list[schemas.ScheduleGapEntry])
def get_schedule_gap(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    return gap_calc.schedule_gap_entries(db, project_id)


# ---------------------------------------------------------------------------
# Progress Gap = Expected Progress - Actual Progress (Prozentpunkte). Berechnung in
# gap_calc.py (Phase 22, dort auch von health_calc.py für die Progress Health genutzt).
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/gaps/progress", response_model=list[schemas.ProgressGapEntry])
def get_progress_gap(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    return gap_calc.progress_gap_entries(db, project_id)


# ---------------------------------------------------------------------------
# Utilization Gap = zugeordnetes FTE (ResourceAssignment, Phase 19) ggü. Available Capacity
# (Phase 20), verglichen mit einer fixen Ziel-Auslastung von 100%.
# ---------------------------------------------------------------------------


@router.get("/people/{person_id}/gaps/utilization", response_model=schemas.UtilizationGapOut)
def get_utilization_gap(person_id: int, period: str, db: Session = Depends(get_db)):
    _get_person_or_404(db, person_id)
    # P20.1: über BEIDE Ressourcenwege summiert (Legacy ResourceDemand + direkte
    # PlanPhase-Assignments), siehe capacity_calc.assigned_fte_for_person_period.
    assigned_fte = capacity_calc.assigned_fte_for_person_period(db, person_id, period)
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
        schedule=gap_calc.schedule_gap_entries(db, project_id),
        progress=gap_calc.progress_gap_entries(db, project_id),
    )
