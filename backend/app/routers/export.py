import json
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models
from ..constants import berechne_monate
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["export"])

EXPORT_SCRIPT = Path(__file__).resolve().parents[3] / "export" / "PLX_generate_pptx.js"


def _build_config(projects: list[models.Project], monate: list[str]) -> dict:
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
                "teilprojekte": [
                    {
                        "name": sp.name,
                        "phasen": _phasen_dict(sp),
                        "fte": {f.monat: f.wert_soll for f in sp.fte_plan},
                    }
                    for sp in sorted(p.subprojects, key=lambda s: s.reihenfolge)
                ],
            }
            for p in projects
        ],
    }


def _phasen_dict(sp: models.Subproject) -> dict[str, str]:
    grouped: dict[str, list[str]] = {}
    for gp in sp.gantt_phases:
        grouped.setdefault(gp.monat, []).append(gp.phase_code)
    # PLX_generate_pptx.js akzeptiert sowohl einen String als auch eine Liste je Monat.
    return {monat: (codes if len(codes) > 1 else codes[0]) for monat, codes in grouped.items()}


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
    config = _build_config(projects, monate)
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
    config = _build_config([project], monate)
    output_path = _run_export(config)

    filename = f"{project.name.replace(' ', '_')}_Kapazitaetsplanung.pptx"
    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
