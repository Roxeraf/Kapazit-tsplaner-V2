"""P20.4: Tests für die Phase-Ist-Metriken (worklog_actuals.py, phase_metrics_calc.py,
PhaseMetricsOut), siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 15/16/28.
Kein pytest im Repo (siehe test_planning_phase_tree_api.py als etabliertes Muster).
Worklog-Zeilen werden direkt in jira_worklogs_cache eingefügt (kein echter Jira/Tempo-
Netzwerkzugriff in diesen Skripten):

1. AT1 (Happy Path): Konfiguration, Planstunden 80h, drei Personen eindeutig gemappt
   (32h+20h+8h=60h) -> ist_hours=60, effort_consumption_pct=75%, remaining_plan_hours=20h,
   overrun_hours=0, keine Doppelzählung.
2. Überverbrauch: 95h Ist bei 80h Plan -> overrun_hours=15h, remaining_plan_hours=0
   (gekappt, nicht negativ).
3. AT7 (Kein Mapping): Phase ohne jira_label liefert ist_hours=None (nicht 0.0) und
   effort_consumption_pct=None - "noch nicht zugeordnet" statt einer irreführenden 0%.
4. AT6 (Parent-Aggregation): Wareneingang (Parent) mit Child 1 (20h Ist) + Child 2 (40h Ist)
   -> Parent ist_hours=60h, keine doppelte Speicherung/Zählung.
5. Parent ohne jegliches gemapptes Kind liefert ist_hours=None (nicht 0.0), analog zu
   planning_calc.derive_parent_capacity für plan_fte.
6. P20.4 (Parent-Übersicht): plan_hours und time_progress_pct einer Parent-Phase werden aus
   den Leaf-Nachfahren abgeleitet (derive_parent_bounds/Summe der Leaf-Planstunden) statt aus
   den stets-None eigenen forecast_start/forecast_end/plan_fte-Feldern der Parent-Phase.

Aufruf: python backend/scripts/test_p20_phase_actual_metrics.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_phase_metrics_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from fastapi.testclient import TestClient  # noqa: E402

from app import jira_sync, models  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402 - Import triggert db_bootstrap.run_migrations()

client = TestClient(app)


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def _create_project(name: str) -> int:
    resp = client.post("/projects", json={"name": name, "start_monat": "10.2026", "anzahl_monate": 3})
    if resp.status_code != 201:
        _fail("Projekt anlegen", f"{resp.status_code}: {resp.text}")
    return resp.json()["id"]


def _create_phase(project_id: int, **kwargs) -> dict:
    payload = {"phase_type": "Phase", "status": "geplant", **kwargs}
    resp = client.post(f"/projects/{project_id}/plan-phases", json=payload)
    if resp.status_code != 201:
        _fail("PlanPhase anlegen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def _add_worklog(project_id: int, issue_key: str, account_id: str, datum: str, stunden: float) -> None:
    db = SessionLocal()
    try:
        db.add(
            models.JiraWorklogCache(
                jira_account_id=account_id,
                jira_issue_key=issue_key,
                datum=datum,
                stunden=stunden,
                projekt_mapping=str(project_id),
            )
        )
        db.commit()
    finally:
        db.close()


def _cache_issue(project_id: int, issue_key: str, labels: list[str]) -> None:
    db = SessionLocal()
    try:
        project = db.get(models.Project, project_id)
        jira_sync._upsert_issue_cache(
            db, project, [{"key": issue_key, "id": issue_key, "labels": labels, "component": None, "summary": None}]
        )
        db.commit()
    finally:
        db.close()


def _get_metrics(plan_phase_id: int) -> dict:
    resp = client.get(f"/projects/plan-phases/{plan_phase_id}/metrics")
    if resp.status_code != 200:
        _fail("Metrics abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def main() -> None:
    print("1/6  AT1 — Happy Path: 80h Plan, 60h eindeutig gemappt -> 75% Verbrauch, 20h Rest ...")
    project_id = _create_project("Testprojekt P20.4")
    # 80h Plan: 0.5 FTE * 20 Werktage (Okt 2026) * 8h/Tag = 80h.
    phase = _create_phase(
        project_id,
        phase_type="Konfiguration",
        jira_label="phase:configuration",
        plan_fte=0.5,
        forecast_start="2026-10-01",
        forecast_end="2026-10-28",
    )
    _cache_issue(project_id, "WMX-100", ["phase:configuration"])
    _add_worklog(project_id, "WMX-100", "acc-dominik", "2026-10-05", 32)
    _add_worklog(project_id, "WMX-100", "acc-max", "2026-10-06", 20)
    _add_worklog(project_id, "WMX-100", "acc-anna", "2026-10-07", 8)

    metrics = _get_metrics(phase["id"])
    if metrics["plan_hours"] != 80:
        _fail("AT1 plan_hours", f"erwartet 80, bekam {metrics}")
    if metrics["ist_hours"] != 60:
        _fail("AT1 ist_hours", f"erwartet 60 (32+20+8, keine Doppelzählung), bekam {metrics}")
    if metrics["effort_consumption_pct"] != 75:
        _fail("AT1 effort_consumption_pct", f"erwartet 75, bekam {metrics}")
    if metrics["remaining_plan_hours"] != 20:
        _fail("AT1 remaining_plan_hours", f"erwartet 20, bekam {metrics}")
    if metrics["overrun_hours"] != 0:
        _fail("AT1 overrun_hours", f"erwartet 0, bekam {metrics}")

    print("2/6  Überverbrauch: 95h Ist bei 80h Plan -> 15h Overrun, Rest gekappt bei 0 ...")
    _add_worklog(project_id, "WMX-100", "acc-dominik", "2026-10-08", 35)  # 60 + 35 = 95h
    metrics = _get_metrics(phase["id"])
    if metrics["ist_hours"] != 95:
        _fail("Overrun ist_hours", f"erwartet 95, bekam {metrics}")
    if metrics["overrun_hours"] != 15:
        _fail("Overrun overrun_hours", f"erwartet 15, bekam {metrics}")
    if metrics["remaining_plan_hours"] != 0:
        _fail("Overrun remaining_plan_hours", f"erwartet 0 (gekappt, nicht negativ), bekam {metrics}")

    print("3/6  AT7 — Kein Mapping: ist_hours ist None, nicht 0.0 ...")
    phase_unmapped = _create_phase(
        project_id, phase_type="Testing", plan_fte=0.2, forecast_start="2026-10-01", forecast_end="2026-10-28"
    )
    metrics = _get_metrics(phase_unmapped["id"])
    if metrics["ist_hours"] is not None:
        _fail("AT7 ist_hours", f"erwartet None (kein jira_label), bekam {metrics}")
    if metrics["effort_consumption_pct"] is not None:
        _fail("AT7 effort_consumption_pct", f"erwartet None, bekam {metrics}")
    if metrics["remaining_plan_hours"] is not None or metrics["overrun_hours"] is not None:
        _fail("AT7 remaining/overrun", f"erwartet beide None, bekam {metrics}")

    print("4/6  AT6 — Parent-Aggregation: Child 1 (20h) + Child 2 (40h) -> Parent 60h ...")
    parent = _create_phase(project_id, phase_type="Wareneingang")
    child1 = _create_phase(
        project_id, phase_type="Schnittstellen", parent_phase_id=parent["id"], jira_label="phase:schnittstellen"
    )
    child2 = _create_phase(
        project_id, phase_type="WE-Anmeldung", parent_phase_id=parent["id"], jira_label="phase:we-anmeldung"
    )
    _cache_issue(project_id, "WMX-200", ["phase:schnittstellen"])
    _cache_issue(project_id, "WMX-201", ["phase:we-anmeldung"])
    _add_worklog(project_id, "WMX-200", "acc-dominik", "2026-10-10", 20)
    _add_worklog(project_id, "WMX-201", "acc-max", "2026-10-11", 40)

    metrics_child1 = _get_metrics(child1["id"])
    metrics_child2 = _get_metrics(child2["id"])
    if metrics_child1["ist_hours"] != 20 or metrics_child2["ist_hours"] != 40:
        _fail("AT6 Child-Ist", f"erwartet 20/40, bekam {metrics_child1}/{metrics_child2}")

    metrics_parent = _get_metrics(parent["id"])
    if metrics_parent["ist_hours"] != 60:
        _fail("AT6 Parent-Ist", f"erwartet 60 (20+40, keine doppelte Speicherung), bekam {metrics_parent}")

    print("5/6  Parent ohne jegliches gemapptes Kind -> ist_hours None (nicht 0.0) ...")
    empty_parent = _create_phase(project_id, phase_type="Leere Sammelphase")
    _create_phase(project_id, phase_type="Kind ohne Label", parent_phase_id=empty_parent["id"])
    metrics_empty_parent = _get_metrics(empty_parent["id"])
    if metrics_empty_parent["ist_hours"] is not None:
        _fail("Leerer Parent", f"erwartet None, bekam {metrics_empty_parent}")

    print("6/6  P20.4 — Parent-Übersicht: plan_hours/time_progress_pct aus Leaf-Nachfahren ...")
    # Child 1: 0.5 FTE * 20 Werktage (Okt 2026) * 8h/Tag = 80h. Child 2: 0.25 FTE * 20 * 8 = 40h.
    parent2 = _create_phase(project_id, phase_type="Testphase")
    _create_phase(
        project_id,
        phase_type="Integrationstest",
        parent_phase_id=parent2["id"],
        plan_fte=0.5,
        forecast_start="2026-10-01",
        forecast_end="2026-10-28",
    )
    _create_phase(
        project_id,
        phase_type="UAT",
        parent_phase_id=parent2["id"],
        plan_fte=0.25,
        forecast_start="2026-10-15",
        forecast_end="2026-11-11",
    )
    metrics_parent2 = _get_metrics(parent2["id"])
    if metrics_parent2["plan_hours"] != 120:
        _fail("P20.4 Parent plan_hours", f"erwartet 120 (80+40, Summe Leaf-Planstunden), bekam {metrics_parent2}")
    if metrics_parent2["time_progress_pct"] is None:
        _fail(
            "P20.4 Parent time_progress_pct",
            f"erwartet einen Wert (abgeleiteter Parent-Zeitraum 01.10.–11.11.2026), bekam {metrics_parent2}",
        )

    empty_parent2 = _create_phase(project_id, phase_type="Leere Sammelphase 2")
    _create_phase(project_id, phase_type="Kind ohne Zeitraum/FTE", parent_phase_id=empty_parent2["id"])
    metrics_empty_parent2 = _get_metrics(empty_parent2["id"])
    if metrics_empty_parent2["plan_hours"] is not None:
        _fail("P20.4 Parent plan_hours (leer)", f"erwartet None, bekam {metrics_empty_parent2}")
    if metrics_empty_parent2["time_progress_pct"] is not None:
        _fail("P20.4 Parent time_progress_pct (leer)", f"erwartet None, bekam {metrics_empty_parent2}")

    print(
        "OK — P20.4: AT1 (Happy Path 75%/20h Rest), Überverbrauch (15h Overrun, Rest gekappt), "
        "AT7 (kein Mapping -> None statt 0h), AT6 (Parent-Aggregation 20h+40h=60h), leerer "
        "Parent (None) und Parent-Übersicht (plan_hours/time_progress_pct aus Leaf-Nachfahren "
        "abgeleitet) funktionieren wie spezifiziert."
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
