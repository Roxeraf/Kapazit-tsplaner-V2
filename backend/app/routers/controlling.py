"""Controlling & Capacity Intelligence (Phase 23, siehe CONCEPT.md Abschnitt 12 / Master-MD
Abschnitt 23). Aggregiert die bereits bestehenden, projekt-/personenscharfen GAP-/Health-/
Capacity-Berechnungen (Phase 19-22: capacity_calc.py, gap_calc.py, gap_analysis.py,
health_calc.py, baseline_calc.py) portfolioweit über alle Projekte/Perioden/Rollen hinweg -
rein berechnend, keine neuen Tabellen, keine Logikänderung an den zugrunde liegenden
Berechnungen. Router importiert absichtlich nicht von anderen Routern, nur von den
gemeinsamen Modulen.

Bewusst nicht Teil dieses Durchgangs (siehe CONCEPT.md für die Begründung):
- Effort Gap portfolioweit: bereits durch das bestehende GET /gap abgedeckt, kein Alias hier.
- Der volle hierarchische Portfolio->Team->Projekt->Phase-Drill-down (Master-MD Abschnitt 52):
  die Zielobjekte jeder Ebene existieren bereits (/projects/{id}/cockpit, /gaps, /health,
  /resource-demands) - dieser Router liefert nur die fehlende Portfolio-Einstiegsebene.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import baseline_calc, capacity_calc, constants, gap_analysis, gap_calc, health_calc, models, schemas
from ..database import get_db

router = APIRouter(prefix="/controlling", tags=["controlling"])


def _portfolio_projects(db: Session) -> list[models.Project]:
    """on_hold/archivierte Projekte ausgeblendet, abgeschlossene bleiben sichtbar - gleicher
    Filter wie gap_analysis.projekte_fuer_team(db, None), hier direkt wiederverwendet."""
    return gap_analysis.projekte_fuer_team(db, None)


# ---------------------------------------------------------------------------
# Capacity Heatmap / Demand vs Capacity
# ---------------------------------------------------------------------------


@router.get("/capacity-heatmap", response_model=list[schemas.CapacityGapOut])
def get_capacity_heatmap(
    period: str | None = None, periods: int = 6, resource_role_id: int | None = None, db: Session = Depends(get_db)
):
    start = period or constants.current_period()
    return [
        capacity_calc.compute_capacity_gap(db, p, resource_role_id)
        for p in constants.periods_from(start, periods)
    ]


# ---------------------------------------------------------------------------
# Allocation Gap (portfolioweit)
# ---------------------------------------------------------------------------


@router.get("/allocation-gaps", response_model=list[schemas.PortfolioAllocationGapEntry])
def get_allocation_gaps(period: str, db: Session = Depends(get_db)):
    # P18/B-4/B-5 (CONCEPT.md Abschnitt 6b.4): die interne Systemrolle "Ohne Rolle" ist keine
    # eigenständige, fachliche Rolle - sie wird aus dieser Rollen-Auswertung ausgeblendet statt
    # als gleichwertige Zeile neben echten Rollen (z.B. "Senior Consultant") zu erscheinen.
    demands = (
        db.query(models.ResourceDemand)
        .join(models.ResourceRole, models.ResourceRole.id == models.ResourceDemand.resource_role_id)
        .filter(models.ResourceDemand.period == period, models.ResourceRole.is_system_role.is_(False))
        .all()
    )
    entries = []
    for demand in demands:
        role = db.get(models.ResourceRole, demand.resource_role_id)
        project = db.get(models.Project, demand.project_id)
        assigned_fte = round(
            sum(
                a.fte
                for a in db.query(models.ResourceAssignment)
                .filter(models.ResourceAssignment.resource_demand_id == demand.id)
                .all()
            ),
            2,
        )
        entries.append(
            schemas.PortfolioAllocationGapEntry(
                project_id=demand.project_id,
                project_name=project.name if project else "",
                resource_demand_id=demand.id,
                resource_role_id=demand.resource_role_id,
                resource_role_name=role.name if role else "",
                period=demand.period,
                fte=demand.fte,
                assigned_fte=assigned_fte,
                allocation_gap=round(demand.fte - assigned_fte, 2),
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Schedule Gap / Progress Gap (portfolioweit) - Berechnung in gap_calc.py (Phase 22)
# ---------------------------------------------------------------------------


@router.get("/schedule-gaps", response_model=list[schemas.PortfolioScheduleGapEntry])
def get_schedule_gaps(db: Session = Depends(get_db)):
    entries = []
    for project in _portfolio_projects(db):
        for entry in gap_calc.schedule_gap_entries(db, project.id):
            entries.append(
                schemas.PortfolioScheduleGapEntry(project_id=project.id, project_name=project.name, entry=entry)
            )
    return entries


@router.get("/progress-gaps", response_model=list[schemas.PortfolioProgressGapEntry])
def get_progress_gaps(db: Session = Depends(get_db)):
    entries = []
    for project in _portfolio_projects(db):
        for entry in gap_calc.progress_gap_entries(db, project.id):
            entries.append(
                schemas.PortfolioProgressGapEntry(project_id=project.id, project_name=project.name, entry=entry)
            )
    return entries


# ---------------------------------------------------------------------------
# Baseline Deviations (portfolioweit, jeweils neuester Snapshot je Projekt)
# ---------------------------------------------------------------------------


@router.get("/baseline-deviations", response_model=list[schemas.PortfolioBaselineDeviationEntry])
def get_baseline_deviations(db: Session = Depends(get_db)):
    entries = []
    for project in _portfolio_projects(db):
        snapshot = baseline_calc.latest_snapshot(db, project.id)
        if snapshot is None:
            continue
        for deviation in baseline_calc.compute_deviations(db, snapshot.id):
            if deviation.delta_days is None:
                continue
            entries.append(
                schemas.PortfolioBaselineDeviationEntry(
                    project_id=project.id,
                    project_name=project.name,
                    baseline_id=snapshot.id,
                    baseline_name=snapshot.name,
                    deviation=deviation,
                )
            )
    return entries


# ---------------------------------------------------------------------------
# Portfolio Health - Berechnung in health_calc.py (Phase 22)
# ---------------------------------------------------------------------------


@router.get("/portfolio-health", response_model=list[schemas.ProjectHealthOut])
def get_portfolio_health(db: Session = Depends(get_db)):
    return [health_calc.compute_project_health(db, project) for project in _portfolio_projects(db)]


# ---------------------------------------------------------------------------
# Blocker Portfolio / Milestone Portfolio
# ---------------------------------------------------------------------------


@router.get("/blockers", response_model=list[schemas.BlockerPortfolioEntry])
def get_blocker_portfolio(party: str | None = None, severity: str | None = None, db: Session = Depends(get_db)):
    projects_by_id = {p.id: p for p in _portfolio_projects(db)}
    query = db.query(models.Blocker).filter(
        models.Blocker.project_id.in_(list(projects_by_id.keys())), models.Blocker.status != "geloest"
    )
    if severity is not None:
        query = query.filter(models.Blocker.severity == severity)
    if party is not None:
        query = query.filter(
            (models.Blocker.caused_by_party == party) | (models.Blocker.waiting_for_party == party)
        )
    return [
        schemas.BlockerPortfolioEntry(
            project_id=b.project_id,
            project_name=projects_by_id[b.project_id].name,
            id=b.id,
            title=b.title,
            status=b.status,
            severity=b.severity,
            caused_by_party=b.caused_by_party,
            waiting_for_party=b.waiting_for_party,
            active_since=b.active_since,
        )
        for b in query.all()
    ]


@router.get("/milestones", response_model=list[schemas.MilestonePortfolioEntry])
def get_milestone_portfolio(status: str | None = None, db: Session = Depends(get_db)):
    projects_by_id = {p.id: p for p in _portfolio_projects(db)}
    query = db.query(models.Milestone).filter(models.Milestone.project_id.in_(list(projects_by_id.keys())))
    if status is not None:
        query = query.filter(models.Milestone.status == status)
    return [
        schemas.MilestonePortfolioEntry(
            project_id=m.project_id,
            project_name=projects_by_id[m.project_id].name,
            id=m.id,
            name=m.name,
            baseline_date=m.baseline_date,
            forecast_date=m.forecast_date,
            actual_date=m.actual_date,
            status=m.status,
        )
        for m in query.all()
    ]


# ---------------------------------------------------------------------------
# Team-/Rollenanalyse
# ---------------------------------------------------------------------------


@router.get("/roles", response_model=list[schemas.RoleAnalysisEntry])
def get_role_analysis(period: str, db: Session = Depends(get_db)):
    # P18/B-4/B-5 (Abschnitt 6b.4): Systemrolle nie als eigenständige Rolle neben echten
    # Rollen reporten - dieselbe Governance-Regel wie bei get_allocation_gaps oben.
    roles = (
        db.query(models.ResourceRole)
        .filter(models.ResourceRole.is_system_role.is_(False))
        .order_by(models.ResourceRole.name)
        .all()
    )
    entries = []
    for role in roles:
        demands = (
            db.query(models.ResourceDemand)
            .filter(models.ResourceDemand.resource_role_id == role.id, models.ResourceDemand.period == period)
            .all()
        )
        if not demands:
            continue
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
        entries.append(
            schemas.RoleAnalysisEntry(
                resource_role_id=role.id,
                resource_role_name=role.name,
                period=period,
                demand_fte=demand_fte,
                assigned_fte=assigned_fte,
                gap_fte=round(assigned_fte - demand_fte, 2),
            )
        )
    return entries
