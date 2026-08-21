"""Schedule-/Progress-Gap-Berechnung, gemeinsam genutzt von routers/gap_engine.py (Phase 21)
und health_calc.py (Phase 22, siehe CONCEPT.md Abschnitt 12). Aus routers/gap_engine.py
extrahiert, analog zur capacity_calc.py-Extraktion in Phase 21 - Router importieren
absichtlich nicht voneinander, nur von gemeinsamen Modulen."""

from datetime import date

from sqlalchemy.orm import Session

from . import models, schemas


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def schedule_gap_entries(db: Session, project_id: int) -> list[schemas.ScheduleGapEntry]:
    entries: list[schemas.ScheduleGapEntry] = []
    for pp in db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id).all():
        baseline = parse_date(pp.baseline_end) or parse_date(pp.baseline_start)
        forecast = parse_date(pp.forecast_end) or parse_date(pp.forecast_start)
        actual = parse_date(pp.actual_end) or parse_date(pp.actual_start)
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
        baseline = parse_date(m.baseline_date)
        forecast = parse_date(m.forecast_date)
        actual = parse_date(m.actual_date)
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


def expected_progress_pct(start: date | None, end: date | None) -> float | None:
    if start is None or end is None or end <= start:
        return None
    today = date.today()
    if today <= start:
        return 0.0
    if today >= end:
        return 100.0
    return round((today - start).days / (end - start).days * 100, 1)


def progress_gap_entries(db: Session, project_id: int) -> list[schemas.ProgressGapEntry]:
    """Berechnet den Fortschritts-Gap (erwarteter vs. tatsächlicher Fortschritt) je
    PlanPhase. Wird verwendet von /projects/{id}/gaps/progress, /controlling/progress-gaps
    und /projects/{id}/gaps und bleibt voll funktional.

    HINWEIS (P6, Planungs- und Kapazitätskonsolidierung): Die Fortschritts-Dimension
    ist für das Project-Health-Scoring deprecatet. Diese Funktion wird von
    health_calc._progress_health nicht mehr für die Bewertung herangezogen (diese
    gibt nun statisch 'grau' zurück). Die Gap-Reporting-Endpoints bleiben unverändert."""
    entries: list[schemas.ProgressGapEntry] = []
    for pp in db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id).all():
        start = parse_date(pp.forecast_start) or parse_date(pp.baseline_start)
        end = parse_date(pp.forecast_end) or parse_date(pp.baseline_end)
        expected = expected_progress_pct(start, end)
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
