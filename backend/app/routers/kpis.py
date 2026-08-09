"""Portfolio-KPIs für das Controlling (CONCEPT.md Abschnitt 6/9, Schritt 9). Reine
Aggregation über bestehende Datenquellen (Gap-Analyse, Team-Auslastung, Risk/Decision),
keine neue Tabelle."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import gap_analysis, models, schemas
from ..database import get_db
from .team import compute_utilization

router = APIRouter(tags=["kpis"])


@router.get("/kpis", response_model=schemas.KpiSummary)
def get_kpis(db: Session = Depends(get_db)):
    aktive_projekte = db.query(models.Project).filter(models.Project.status == "aktiv").count()

    gap_projekte = gap_analysis.projekte_fuer_team(db, None)
    status_counts = {"gruen": 0, "gelb": 0, "rot": 0, "grau": 0}
    for p in gap_projekte:
        status_counts[gap_analysis.project_gap(db, p)["status"]] += 1

    auslastungen = [u.auslastung_pct for u in compute_utilization(db) if u.auslastung_pct is not None]
    durchschnittliche_auslastung = round(sum(auslastungen) / len(auslastungen), 1) if auslastungen else None

    offene_risiken = db.query(models.Risk).filter(models.Risk.status != "geschlossen").count()
    offene_entscheidungen = db.query(models.Decision).filter(models.Decision.status == "offen").count()

    return schemas.KpiSummary(
        anzahl_projekte_aktiv=aktive_projekte,
        anzahl_projekte_gruen=status_counts["gruen"],
        anzahl_projekte_gelb=status_counts["gelb"],
        anzahl_projekte_rot=status_counts["rot"],
        anzahl_projekte_grau=status_counts["grau"],
        durchschnittliche_auslastung_pct=durchschnittliche_auslastung,
        offene_risiken_gesamt=offene_risiken,
        offene_entscheidungen_gesamt=offene_entscheidungen,
    )
