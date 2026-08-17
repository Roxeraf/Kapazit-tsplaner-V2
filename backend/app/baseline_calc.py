"""Baseline-Deviation-Berechnung (Phase 18, siehe CONCEPT.md Abschnitt 12 / Master-MD
Abschnitt 12). Aus routers/baselines.py extrahiert, damit routers/controlling.py (Phase 23,
Baseline Deviations portfolioweit) dieselbe Berechnung ohne Cross-Router-Import nutzen kann -
analog zu capacity_calc.py/gap_calc.py aus Phase 21/22."""

from datetime import date

from sqlalchemy.orm import Session

from . import entity_links, models, schemas

# Datumsfelder, für die Deviations (Tages-Differenz aktueller Wert vs. eingefrorener Wert)
# berechnet werden können.
DATE_FIELDS = {"baseline_start", "baseline_end", "forecast_start", "forecast_end", "baseline_date", "forecast_date"}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def latest_snapshot(db: Session, project_id: int) -> models.BaselineSnapshot | None:
    return (
        db.query(models.BaselineSnapshot)
        .filter(models.BaselineSnapshot.project_id == project_id)
        .order_by(models.BaselineSnapshot.created_at.desc())
        .first()
    )


def compute_deviations(db: Session, baseline_id: int) -> list[schemas.BaselineDeviationOut]:
    """Schedule-/Milestone-Abweichungen: vergleicht die eingefrorenen Datumsfelder mit dem
    aktuellen Live-Wert der referenzierten PlanPhase/Milestone (Master-MD Phase 18). Kein
    generischer Multi-Dimensions-GAP - das bleibt Phase 21 (GAP Engine)."""
    entries = (
        db.query(models.BaselineEntry)
        .filter(models.BaselineEntry.baseline_id == baseline_id, models.BaselineEntry.field.in_(DATE_FIELDS))
        .all()
    )
    deviations = []
    for entry in entries:
        model = entity_links.model_for(entry.entity_type)
        if model is None:
            continue
        row = db.get(model, entry.entity_id)
        current_value = getattr(row, entry.field, None) if row is not None else None
        baseline_date = _parse_date(entry.value)
        current_date = _parse_date(current_value)
        delta_days = (current_date - baseline_date).days if baseline_date and current_date else None
        summary = entity_links.entity_summary(db, entry.entity_type, entry.entity_id)
        deviations.append(
            schemas.BaselineDeviationOut(
                entity_type=entry.entity_type,
                entity_id=entry.entity_id,
                label=summary["label"] if summary else None,
                field=entry.field,
                baseline_value=entry.value,
                current_value=current_value,
                delta_days=delta_days,
            )
        )
    return deviations
