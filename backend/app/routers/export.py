import calendar
import json
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import gap_analysis, models
from ..constants import PHASE_LABELS, berechne_monate, parse_period
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["export"])

EXPORT_SCRIPT = Path(__file__).resolve().parents[3] / "export" / "PLX_generate_pptx.js"

# Rückrichtung von PHASE_LABELS (siehe constants.py) - PLX_generate_pptx.js hat eine feste
# Legende für genau diese fünf Phasenkürzel (Meilenstein "?" wird gesondert aus Milestone
# befüllt, siehe _plan_phasen_dict). PlanPhase.phase_type ist seit Phase 17 Freitext (nur per
# Datalist auf dieselben Bezeichnungen vorgeschlagen, siehe PlanPhaseList.tsx) - Werte
# außerhalb dieses Vokabulars können im PPTX nicht als Balken dargestellt werden und werden
# ausgelassen, statt das feste Kürzel-/Farbschema des Skripts zu brechen.
_CODE_BY_LABEL = {label: code for code, label in PHASE_LABELS.items() if code != "?"}


def _monat_bounds(monat_label: str) -> tuple[date, date]:
    """"Apr 26" -> (2026-04-01, 2026-04-30)."""
    jahr, monat = parse_period(monat_label)
    letzter_tag = calendar.monthrange(jahr, monat)[1]
    return date(jahr, monat, 1), date(jahr, monat, letzter_tag)


def _plan_phasen_dict(db: Session, project_id: int, monate: list[str], subproject_id: int | None) -> dict[str, str]:
    """Rekonstruiert das alte GanttPhase-Zellraster (Monat -> Phasenkürzel) aus PlanPhase
    (Zeitraum, per forecast_start/end bevorzugt vor baseline_start/end) und Milestone
    (Zieldatum als "?"-Marker) - Phase 26.9 Legacy Cutover."""
    query = db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id)
    if subproject_id is not None:
        query = query.filter(models.PlanPhase.subproject_id == subproject_id)

    grouped: dict[str, list[str]] = {}
    monat_bounds = {m: _monat_bounds(m) for m in monate}
    for pp in query.all():
        code = _CODE_BY_LABEL.get(pp.phase_type)
        if code is None:
            continue
        start = pp.forecast_start or pp.baseline_start
        end = pp.forecast_end or pp.baseline_end
        if not start or not end:
            continue
        for monat, (monat_start, monat_end) in monat_bounds.items():
            if start <= monat_end.isoformat() and end >= monat_start.isoformat():
                grouped.setdefault(monat, []).append(code)

    milestone_query = db.query(models.Milestone).filter(models.Milestone.project_id == project_id)
    if subproject_id is not None:
        milestone_query = milestone_query.filter(models.Milestone.subproject_id == subproject_id)
    for m in milestone_query.all():
        datum = m.forecast_date or m.baseline_date
        if not datum:
            continue
        for monat, (monat_start, monat_end) in monat_bounds.items():
            if monat_start.isoformat() <= datum <= monat_end.isoformat():
                grouped.setdefault(monat, []).append("?")

    # PLX_generate_pptx.js akzeptiert sowohl einen String als auch eine Liste je Monat.
    return {monat: (codes if len(codes) > 1 else codes[0]) for monat, codes in grouped.items()}


def _build_config(db: Session, projects: list[models.Project], monate: list[str]) -> dict:
    return {
        "titelseite": {
            "headline": "Portfolio Kapazitätsplanung",
            "subheadline": f"Übersicht FTE & Projektphasen {monate[0]} – {monate[-1]}" if monate else "",
            "praesentationFuer": "",
            "datum": "",
            "ersteller": "",
        },
        "monate": monate,
        "projekte": [
            {
                "name": p.name,
                # Projektweite Phasen (alle Teilprojekte vereint) — PLX_generate_pptx.js nutzt
                # das als Fallback, wenn keines der Teilprojekte befüllte Phasen hat (z.B.
                # Projekte ohne Teilprojekte, siehe CONCEPT.md Abschnitt 3).
                "phasen": _plan_phasen_dict(db, p.id, monate, None),
                "fte": gap_analysis.project_gap(db, p)["soll"],
                "teilprojekte": [
                    {
                        "name": sp.name,
                        "phasen": _plan_phasen_dict(db, p.id, monate, sp.id),
                        # ResourceDemand kennt keine Teilprojekt-Ebene mehr (Phase 26.9) - FTE
                        # wird nur noch projektweit geplant (siehe ResourceDemandGrid.tsx).
                        "fte": {},
                    }
                    for sp in sorted(p.subprojects, key=lambda s: s.reihenfolge)
                ],
            }
            for p in projects
        ],
    }


def _run_export(config: dict) -> Path:
    if not EXPORT_SCRIPT.exists():
        raise HTTPException(status_code=500, detail=f"Export-Skript nicht gefunden: {EXPORT_SCRIPT}")

    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.json"
        output_path = Path(tmp) / "kapazitaetsplanung.pptx"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        result = subprocess.run(
            ["node", str(EXPORT_SCRIPT), str(config_path), str(output_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0 or not output_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"PPTX-Export fehlgeschlagen: {result.stderr or result.stdout}",
            )

        # FileResponse braucht den Pfad über das Ende des `with`-Blocks hinaus.
        persistent = Path(tempfile.gettempdir()) / f"kapazitaetsplanung_{output_path.stat().st_mtime_ns}.pptx"
        persistent.write_bytes(output_path.read_bytes())
        return persistent


@router.get("/export/pptx/portfolio")
def export_portfolio_pptx(db: Session = Depends(get_db)):
    # Muss vor der dynamischen "/{project_id}/..."-Route registriert sein,
    # sonst versucht FastAPI "export" als project_id (int) zu parsen -> 422.
    projects = db.query(models.Project).order_by(models.Project.id).all()
    if not projects:
        raise HTTPException(status_code=404, detail="Keine Projekte vorhanden")

    monate = berechne_monate(projects[0].start_monat, max(p.anzahl_monate for p in projects))
    config = _build_config(db, projects, monate)
    output_path = _run_export(config)

    return FileResponse(
        path=output_path,
        filename="Portfolio_Kapazitaetsplanung.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.get("/{project_id}/export/pptx")
def export_project_pptx(project_id: int, db: Session = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")

    monate = berechne_monate(project.start_monat, project.anzahl_monate)
    config = _build_config(db, [project], monate)
    output_path = _run_export(config)

    filename = f"{project.name.replace(' ', '_')}_Kapazitaetsplanung.pptx"
    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )