"""P20.3: Tests für die Mapping-Coverage (app/actuals_coverage.py,
GET /projects/{id}/actuals-coverage), siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md
Abschnitt 12/13/19/28 (BD-1C/D CLOSED). Kein pytest im Repo (siehe
test_planning_phase_tree_api.py als etabliertes Muster). Worklog-Zeilen werden direkt in
jira_worklogs_cache eingefügt (kein echter Jira/Tempo-Netzwerkzugriff in diesen Skripten,
identisch zum Vorgehen der bestehenden Testskripte):

1. AT2 (Unmapped): Projekt-Ist bleibt vollständig (120h), obwohl nur ein Teil eindeutig
   gemappt ist - unmapped Stunden verschwinden nie, Coverage macht die Lücke sichtbar statt
   sie zu verstecken.
2. AT3 (Ambiguous): ein Issue mit widersprüchlichen Phasen-Labels zählt EINMAL als ambiguous,
   nicht doppelt in beide Phasen - Projekt-Ist bleibt exakt die Summe aller Worklog-Zeilen.
3. Manueller Override löst eine Ambiguous-Zuordnung auf und erhöht die Coverage (AT4-Vorstufe
   für P20.3 - der eigentliche "Konfiguration +8h"-Effekt auf Phasenebene folgt erst mit der
   PhaseMetricsOut-Verdrahtung in P20.4, hier wird nur geprüft, dass der Coverage-Topf wechselt).
4. Kein Worklog im Projekt -> coverage_pct ist None (nicht 0 oder 100, Abschnitt 19).

Aufruf: python backend/scripts/test_p20_actuals_coverage.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_coverage_check_")
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


def _get_coverage(project_id: int) -> dict:
    resp = client.get(f"/projects/{project_id}/actuals-coverage")
    if resp.status_code != 200:
        _fail("Coverage abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def main() -> None:
    print("1/4  AT2 — Unmapped: Projekt-Ist bleibt vollständig, Lücke sichtbar ...")
    project_id = _create_project("Testprojekt P20.3")
    phase_config = _create_phase(project_id, phase_type="Konfiguration", jira_label="phase:configuration")

    db = SessionLocal()
    try:
        project = db.get(models.Project, project_id)
        jira_sync._upsert_issue_cache(
            db,
            project,
            [
                {"key": "WMX-100", "id": "1", "labels": ["phase:configuration"], "component": None, "summary": None},
                {"key": "WMX-103", "id": "2", "labels": [], "component": None, "summary": None},
            ],
        )
        db.commit()
    finally:
        db.close()

    _add_worklog(project_id, "WMX-100", "acc-dominik", "2026-10-05", 60)  # eindeutig gemappt
    _add_worklog(project_id, "WMX-103", "acc-max", "2026-10-06", 20)  # kein Label, kein Override

    coverage = _get_coverage(project_id)
    if coverage["project_ist_total"] != 80:
        _fail("AT2 project_ist_total", f"erwartet 80, bekam {coverage}")
    if coverage["mapped_total"] != 60:
        _fail("AT2 mapped_total", f"erwartet 60, bekam {coverage}")
    if coverage["unmapped_total"] != 20:
        _fail("AT2 unmapped_total", f"erwartet 20, bekam {coverage}")
    if coverage["ambiguous_total"] != 0:
        _fail("AT2 ambiguous_total", f"erwartet 0, bekam {coverage}")
    expected_pct = round(60 / 80 * 100, 2)
    if coverage["coverage_pct"] != expected_pct:
        _fail("AT2 coverage_pct", f"erwartet {expected_pct}, bekam {coverage}")

    print("2/4  AT3 — Ambiguous: ein Issue mit zwei Phasen-Labels zählt einmal, nicht doppelt ...")
    phase_testing = _create_phase(project_id, phase_type="Testing", jira_label="phase:testing")
    db = SessionLocal()
    try:
        project = db.get(models.Project, project_id)
        jira_sync._upsert_issue_cache(
            db,
            project,
            [
                {
                    "key": "WMX-101",
                    "id": "3",
                    "labels": ["phase:configuration", "phase:testing"],
                    "component": None,
                    "summary": None,
                }
            ],
        )
        db.commit()
    finally:
        db.close()
    _add_worklog(project_id, "WMX-101", "acc-anna", "2026-10-07", 8)

    coverage = _get_coverage(project_id)
    if coverage["project_ist_total"] != 88:  # 80 + 8, keine Verdopplung
        _fail("AT3 project_ist_total", f"erwartet 88 (keine Doppelzählung), bekam {coverage}")
    if coverage["ambiguous_total"] != 8:
        _fail("AT3 ambiguous_total", f"erwartet 8, bekam {coverage}")
    if coverage["mapped_total"] != 60:
        _fail("AT3 mapped_total (unverändert)", f"erwartet weiterhin 60, bekam {coverage}")
    if coverage["unmapped_total"] != 20:
        _fail("AT3 unmapped_total (unverändert)", f"erwartet weiterhin 20, bekam {coverage}")

    print("3/4  Manueller Override löst Ambiguous auf, Coverage steigt (AT4-Vorstufe) ...")
    resp = client.post(
        f"/projects/plan-phases/{phase_testing['id']}/worklog-overrides",
        json={"jira_issue_key": "WMX-101", "previous_status": "ambiguous"},
    )
    if resp.status_code != 201:
        _fail("Override für WMX-101 anlegen", f"{resp.status_code}: {resp.text}")

    coverage = _get_coverage(project_id)
    if coverage["ambiguous_total"] != 0:
        _fail("Override löst Ambiguous auf", f"erwartet ambiguous_total 0, bekam {coverage}")
    if coverage["mapped_total"] != 68:  # 60 + 8, jetzt eindeutig via Override
        _fail("Override erhöht mapped_total", f"erwartet 68, bekam {coverage}")
    if coverage["project_ist_total"] != 88:
        _fail("Override ändert Projekt-Ist nicht", f"erwartet weiterhin 88, bekam {coverage}")

    print("4/4  Projekt ohne Worklogs -> coverage_pct ist None (nicht 0 oder 100) ...")
    empty_project_id = _create_project("Leeres Projekt (kein Ist)")
    coverage = _get_coverage(empty_project_id)
    if coverage["project_ist_total"] != 0 or coverage["coverage_pct"] is not None:
        _fail("Leeres Projekt", f"erwartet project_ist_total=0 und coverage_pct=None, bekam {coverage}")

    print(
        "OK — P20.3: Unmapped bleibt sichtbar und im Projekt-Ist enthalten (AT2), Ambiguous "
        "zählt einmal ohne Doppelzählung (AT3), Override erhöht die Coverage ohne das "
        "Projekt-Ist zu verändern, leeres Projekt liefert coverage_pct=None statt 0/100."
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
