"""Project Health (Phase 22, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 6/49/50).
Mehrdimensionales Project Health auf Basis der GAP-Engine (Phase 21: gap_calc.py,
capacity_calc.py, gap_analysis.py) und bestehender Daten (Blocker/Risk/Milestone). Rein
berechnend, keine Logikänderung an den zugrunde liegenden GAP-Berechnungen - dieses Modul
bewertet sie nur gegen konfigurierbare Schwellwerte (HealthThreshold). Gemeinsam genutzt von
routers/health.py; folgt dem in Phase 21 etablierten Muster (capacity_calc.py/gap_calc.py):
Router importieren nur von gemeinsamen Modulen, nicht voneinander."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import constants, gap_analysis, gap_calc, models, schemas

# Rang je Ausprägung, für die "badness"-Berechnung (je höher desto schlechter).
SEVERITY_RANK = {"niedrig": 1, "mittel": 2, "hoch": 3, "kritisch": 4}
RISK_RANK = {"niedrig": 1, "mittel": 2, "hoch": 3}

# Default-Schwellwerte je Metrik (yellow, red) - greifen, solange keine HealthThreshold-Zeile
# in der DB existiert (Migration seedet sie, das ist nur ein defensiver Fallback). Effort
# Health ist bewusst NICHT hier: sie verwendet unverändert GAP_SCHWELLE_GELB/ROT aus
# gap_analysis.py (siehe models.HealthThreshold-Docstring).
DEFAULT_THRESHOLDS: dict[str, tuple[float, float]] = {
    "schedule_days": (7, 14),
    "capacity_fte": (0.2, 0.5),
    "progress_pp": (10, 20),
    "risk_score": (3, 5),
    "blocker_severity": (1, 3),
}


def _thresholds(db: Session) -> dict[str, tuple[float, float]]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    for row in db.query(models.HealthThreshold).all():
        thresholds[row.metric] = (row.yellow, row.red)
    return thresholds


def _status(badness: float, yellow: float, red: float) -> str:
    if badness >= red:
        return "rot"
    if badness >= yellow:
        return "gelb"
    return "gruen"


def _schedule_health(db: Session, project_id: int, thresholds: dict[str, tuple[float, float]]) -> schemas.HealthDimension:
    entries = gap_calc.schedule_gap_entries(db, project_id)
    deltas = [
        e.forecast_vs_actual_days if e.forecast_vs_actual_days is not None else e.baseline_vs_forecast_days
        for e in entries
    ]
    deltas = [d for d in deltas if d is not None]
    if not deltas:
        return schemas.HealthDimension(
            status="grau", value=None, explanation="Keine Termine mit Baseline/Forecast/Actual hinterlegt."
        )
    worst = max(deltas)
    badness = max(0.0, float(worst))
    yellow, red = thresholds["schedule_days"]
    return schemas.HealthDimension(
        status=_status(badness, yellow, red),
        value=badness,
        explanation=f"Größter Verzug {worst:+d} Tage (Forecast-vs-Actual, ersatzweise Baseline-vs-Forecast, über alle Planphasen/Milestones).",
    )


def _capacity_health(db: Session, project_id: int, thresholds: dict[str, tuple[float, float]]) -> schemas.HealthDimension:
    period = constants.current_period()
    demands = (
        db.query(models.ResourceDemand)
        .filter(models.ResourceDemand.project_id == project_id, models.ResourceDemand.period == period)
        .all()
    )
    if not demands:
        return schemas.HealthDimension(
            status="grau", value=None, explanation=f"Kein Ressourcenbedarf für die aktuelle Periode ({period})."
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
    gap = round(assigned_fte - demand_fte, 2)
    badness = max(0.0, -gap)
    yellow, red = thresholds["capacity_fte"]
    return schemas.HealthDimension(
        status=_status(badness, yellow, red),
        value=badness,
        explanation=f"Bedarf {demand_fte} FTE, zugeordnet {assigned_fte} FTE, Allocation Gap {gap:+.2f} FTE ({period}).",
    )


def _effort_health(gap: dict) -> schemas.HealthDimension:
    status = gap["status"]
    gap_pct = gap["gap_pct"]
    if status == "grau" or gap_pct is None:
        return schemas.HealthDimension(
            status="grau", value=None, explanation="Kein Soll oder keine Ist-Daten für eine belastbare Aussage."
        )
    return schemas.HealthDimension(
        status=status,
        value=abs(gap_pct),
        explanation=f"Projizierte Gesamtabweichung {gap_pct:+.1%} ggü. Soll ({gap['projiziert_gesamt']} von {gap['soll_gesamt']} FTE).",
    )


def _progress_health(db: Session, project_id: int, thresholds: dict[str, tuple[float, float]]) -> schemas.HealthDimension:
    """Fortschritts-Dimension ist deprecatet (P6, Planungs- und Kapazitätskonsolidierung).
    Die Dimension wird nicht mehr bewertet und immer als 'grau' zurückgegeben. Die
    zugrunde liegende Gap-Berechnung (gap_calc.progress_gap_entries) bleibt für die
    Endpoints /gaps/progress und /controlling/progress-gaps voll funktional. Signatur
    bleibt aus Kompatibilität mit compute_project_health unverändert."""
    return schemas.HealthDimension(
        status="grau",
        value=None,
        explanation="Fortschritts-Dimension ist deprecatet und wird nicht mehr bewertet.",
    )


def _risk_health(db: Session, project_id: int, thresholds: dict[str, tuple[float, float]]) -> schemas.HealthDimension:
    risks = (
        db.query(models.Risk)
        .filter(models.Risk.project_id == project_id, models.Risk.status != "geschlossen")
        .all()
    )
    if not risks:
        return schemas.HealthDimension(status="gruen", value=0.0, explanation="Keine offenen Risiken.")
    badness = float(max(RISK_RANK.get(r.wahrscheinlichkeit, 2) + RISK_RANK.get(r.auswirkung, 2) for r in risks))
    yellow, red = thresholds["risk_score"]
    return schemas.HealthDimension(
        status=_status(badness, yellow, red),
        value=badness,
        explanation=f"{len(risks)} offene Risiken, höchster Score {badness:.0f} (Wahrscheinlichkeit+Auswirkung, je 1-3).",
    )


def _blocker_health(db: Session, project_id: int, thresholds: dict[str, tuple[float, float]]) -> schemas.HealthDimension:
    blockers = (
        db.query(models.Blocker)
        .filter(models.Blocker.project_id == project_id, models.Blocker.status != "geloest")
        .all()
    )
    if not blockers:
        return schemas.HealthDimension(status="gruen", value=0.0, explanation="Keine offenen Blocker.")
    badness = float(max(SEVERITY_RANK.get(b.severity, 2) for b in blockers))
    yellow, red = thresholds["blocker_severity"]
    return schemas.HealthDimension(
        status=_status(badness, yellow, red),
        value=badness,
        explanation=f"{len(blockers)} offene Blocker, höchste Severity-Stufe {badness:.0f} (niedrig=1...kritisch=4).",
    )


def _milestone_health(db: Session, project_id: int) -> schemas.HealthDimension:
    milestones = db.query(models.Milestone).filter(models.Milestone.project_id == project_id).all()
    if not milestones:
        return schemas.HealthDimension(status="grau", value=None, explanation="Keine Milestones hinterlegt.")
    verpasst = [m for m in milestones if m.status == "verpasst"]
    gefaehrdet = [m for m in milestones if m.status == "gefaehrdet"]
    if verpasst:
        return schemas.HealthDimension(
            status="rot", value=float(len(verpasst)), explanation=f"{len(verpasst)} verpasste Milestone(s)."
        )
    if gefaehrdet:
        return schemas.HealthDimension(
            status="gelb", value=float(len(gefaehrdet)), explanation=f"{len(gefaehrdet)} gefährdete Milestone(s)."
        )
    return schemas.HealthDimension(
        status="gruen", value=0.0, explanation=f"Alle {len(milestones)} Milestone(s) im Plan."
    )


def _customer_health(db: Session, project_id: int, thresholds: dict[str, tuple[float, float]]) -> schemas.HealthDimension:
    """Kundenbezogene offene Blocker: Kunde hat den Blocker verursacht oder der Ball liegt
    aktuell beim Kunden (waiting_for_party/caused_by_party == CUSTOMER, Phase 16). Nutzt
    dieselbe Severity-Schwelle wie Blocker Health (eigene Skala, keine eigene Konfiguration
    für einen ohnehin identischen Wertebereich)."""
    blockers = (
        db.query(models.Blocker)
        .filter(
            models.Blocker.project_id == project_id,
            models.Blocker.status != "geloest",
            or_(models.Blocker.waiting_for_party == "CUSTOMER", models.Blocker.caused_by_party == "CUSTOMER"),
        )
        .all()
    )
    if not blockers:
        return schemas.HealthDimension(status="gruen", value=0.0, explanation="Keine offenen, kundenbezogenen Blocker.")
    badness = float(max(SEVERITY_RANK.get(b.severity, 2) for b in blockers))
    yellow, red = thresholds["blocker_severity"]
    return schemas.HealthDimension(
        status=_status(badness, yellow, red),
        value=badness,
        explanation=f"{len(blockers)} offene, kundenbezogene Blocker, höchste Severity-Stufe {badness:.0f}.",
    )


_STATUS_RANK = {"rot": 3, "gelb": 2, "gruen": 1}


def _overall_health(dims: dict[str, schemas.HealthDimension]) -> schemas.HealthDimension:
    """Worst-of über alle Dimensionen mit belastbarer Datenbasis (grau wird ausgeklammert).
    Die Master-MD gibt keinen konkreten Aggregationsalgorithmus für Overall vor (Abschnitt
    49: 'muss aus strukturierten Kennzahlen erklärbar sein') - worst-of ist die einfachste,
    deterministische und vollständig erklärbare Wahl (bewusste Scope-Entscheidung, analog zur
    portfolioweiten Capacity-Gap-Vereinfachung in Phase 21)."""
    considered = {k: v for k, v in dims.items() if v.status != "grau"}
    if not considered:
        return schemas.HealthDimension(status="grau", value=None, explanation="Keine Dimension mit belastbarer Datenbasis.")
    worst_key = max(considered, key=lambda k: _STATUS_RANK[considered[k].status])
    worst = considered[worst_key]
    return schemas.HealthDimension(
        status=worst.status, value=None, explanation=f"Schlechteste Einzeldimension: {worst_key} ({worst.status})."
    )


def compute_project_health(db: Session, project: models.Project) -> schemas.ProjectHealthOut:
    thresholds = _thresholds(db)
    schedule = _schedule_health(db, project.id, thresholds)
    capacity = _capacity_health(db, project.id, thresholds)
    effort = _effort_health(gap_analysis.project_gap(db, project))
    progress = _progress_health(db, project.id, thresholds)
    risks = _risk_health(db, project.id, thresholds)
    blockers = _blocker_health(db, project.id, thresholds)
    milestones = _milestone_health(db, project.id)
    customer = _customer_health(db, project.id, thresholds)
    overall = _overall_health(
        {
            "schedule": schedule,
            "capacity": capacity,
            "effort": effort,
            "progress": progress,
            "risks": risks,
            "blockers": blockers,
            "milestones": milestones,
            "customer": customer,
        }
    )
    return schemas.ProjectHealthOut(
        project_id=project.id,
        project_name=project.name,
        overall=overall,
        schedule=schedule,
        capacity=capacity,
        effort=effort,
        progress=progress,
        risks=risks,
        blockers=blockers,
        milestones=milestones,
        customer=customer,
    )
