"""Gap-Analyse mit Hochrechnung (CONCEPT.md Abschnitt 5, Phasenplan-Schritt 3).

Setzt die Jira-Ist-Integration (Schritt 2, ../jira_sync.py) voraus: ohne Ist-Daten
liefern die Endpunkte weiterhin Soll-Werte, aber Status "grau" statt einer belastbaren
Gap-Aussage.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import gap_analysis, models, schemas
from ..database import get_db

router = APIRouter(tags=["gap-analyse"])


@router.get("/gap", response_model=list[schemas.GapAnalysis])
def gap(team_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    """Soll/Ist/Gap je Monat und Projekt, optional gefiltert auf ein Team (CONCEPT.md Abschnitt 6)."""
    projekte = gap_analysis.projekte_fuer_team(db, team_id)
    return [gap_analysis.project_gap(db, p) for p in projekte]


@router.get("/gap/{project_id}", response_model=schemas.GapAnalysis)
def gap_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return gap_analysis.project_gap(db, project)


@router.get("/forecast", response_model=list[schemas.ForecastSummary])
def forecast(team_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    """Hochrechnung Jahresende/Projektende je Projekt (Trendfortschreibung, CONCEPT.md Abschnitt 5)."""
    projekte = gap_analysis.projekte_fuer_team(db, team_id)
    ergebnisse = [gap_analysis.project_gap(db, p) for p in projekte]
    return [
        schemas.ForecastSummary(
            project_id=e["project_id"],
            project_name=e["project_name"],
            soll_gesamt=e["soll_gesamt"],
            projiziert_gesamt=e["projiziert_gesamt"],
            gap_gesamt=e["gap_gesamt"],
            gap_pct=e["gap_pct"],
            status=e["status"],
        )
        for e in ergebnisse
    ]
