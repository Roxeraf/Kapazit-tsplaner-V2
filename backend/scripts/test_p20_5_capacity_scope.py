"""P20.5: Capacity Scope - Tests für die Trennung Project/Jira Total Actual vs. Capacity
Actual (siehe P20_5_PHASE_ACTUALS_AND_TIME_CONTROL.md Abschnitt 3/4/7/9/10/12, Testfälle
Abschnitt 53/54). Kein pytest im Repo (siehe test_planning_phase_tree_api.py als etabliertes
Muster). Worklog-Zeilen werden direkt in jira_worklogs_cache eingefügt (kein echter Jira/
Tempo-Netzwerkzugriff):

1. Testfall Abschnitt 53 (Developer ausfiltern): Consultant A (40h) + Consultant B (20h,
   beide kapazitätsplanbar) + Developer X (100h, KEINE lokale Person) + Developer Y (80h,
   Person existiert, aber capacity_relevant=False) -> Capacity Actual = 60h (nicht 240h),
   Aufwandsverbrauch 75% (nicht 300%). Project/Jira Total Actual bleibt bei 240h
   (GET .../actuals-coverage, unverändert).
2. Testfall Abschnitt 54 (Unplanned Consultant): nur Dominik eingeplant, Christian bucht
   trotzdem 10h ohne Assignment -> beide zählen zum Capacity Actual (40h gesamt), Christian
   erscheint im Drilldown als "nicht eingeplant" (planned=False).
3. Outside-Scope-Transparenz (Abschnitt 9): Developer-Stunden verschwinden nicht, sondern
   erscheinen als outside_scope (Stunden + Autorenanzahl) auf Phase/Person-Actuals-Endpoint.
4. Zeitraum-Aufschlüsselung (Abschnitt 6-8/39): before/within/after gegen den aktuellen Plan
   (kein Commitment vorhanden) - Summe == ist_hours, Worklogs vor/nach dem Zeitraum werden
   NICHT abgeschnitten (bleiben Teil von ist_hours).

Aufruf: python backend/scripts/test_p20_5_capacity_scope.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_5_capacity_scope_check_")
# KAPA_TEST_DB_URL: optionales Override fuer eine echte PostgreSQL-Instanz (P20.5 Auftrag
# Abschnitt 59 - "nicht nur SQLite testen"), Default bleibt eine Wegwerf-SQLite-Datei.
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("KAPA_TEST_DB_URL")
    or ("sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")),
)
os.environ["JIRA_AUTOSYNC_ENABLED"] = "false"

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


def _create_capacity_person(display_name: str, account_id: str) -> int:
    resp = client.post("/people", json={"display_name": display_name, "jira_account_id": account_id})
    if resp.status_code != 201:
        _fail("Person anlegen", f"{resp.status_code}: {resp.text}")
    person_id = resp.json()["id"]
    resp = client.post(f"/people/{person_id}/resource-profile", json={"weekly_hours": 40, "capacity_relevant": True})
    if resp.status_code != 201:
        _fail("ResourceProfile anlegen", f"{resp.status_code}: {resp.text}")
    return person_id


def _create_non_capacity_person(display_name: str, account_id: str) -> int:
    """Person existiert, ist aber NICHT kapazitätsplanbar (capacity_relevant=False) - z.B.
    ein externer Entwickler, der zwar im Tool angelegt ist, aber nicht Teil des
    Kapazitätsplaners (Abschnitt 3)."""
    resp = client.post("/people", json={"display_name": display_name, "jira_account_id": account_id})
    if resp.status_code != 201:
        _fail("Person anlegen", f"{resp.status_code}: {resp.text}")
    person_id = resp.json()["id"]
    resp = client.post(
        f"/people/{person_id}/resource-profile", json={"weekly_hours": 40, "capacity_relevant": False}
    )
    if resp.status_code != 201:
        _fail("ResourceProfile anlegen", f"{resp.status_code}: {resp.text}")
    return person_id


def _add_worklog(project_id: int, issue_key: str, account_id: str, datum: str, stunden: float) -> None:
    db = SessionLocal()
    try:
        db.add(
            models.JiraWorklogCache(
                jira_account_id=account_id, jira_issue_key=issue_key, datum=datum, stunden=stunden,
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


def _get_time_control(plan_phase_id: int) -> dict:
    resp = client.get(f"/projects/plan-phases/{plan_phase_id}/time-control")
    if resp.status_code != 200:
        _fail("Time-Control abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def _get_person_actuals(plan_phase_id: int) -> dict:
    resp = client.get(f"/projects/plan-phases/{plan_phase_id}/person-actuals")
    if resp.status_code != 200:
        _fail("Person-Actuals abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def _get_coverage(project_id: int) -> dict:
    resp = client.get(f"/projects/{project_id}/actuals-coverage")
    if resp.status_code != 200:
        _fail("Actuals-Coverage abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def _assign(plan_phase_id: int, person_id: int, fte: float) -> None:
    resp = client.post(
        f"/projects/plan-phases/{plan_phase_id}/assign-person", json={"person_id": person_id, "fte": fte}
    )
    if resp.status_code != 200:
        _fail("Person zuweisen", f"{resp.status_code}: {resp.text}")


def main() -> None:
    print("1/4  Testfall Abschnitt 53 — Developer ausfiltern (Capacity Actual 60h statt 240h) ...")
    project_id = _create_project("Testprojekt P20.5 Capacity Scope")
    # 80h Plan: 0.5 FTE * 20 Werktage (Okt 2026) * 8h/Tag = 80h.
    phase = _create_phase(
        project_id, phase_type="Konfiguration", jira_label="phase:configuration",
        plan_fte=0.5, forecast_start="2026-10-01", forecast_end="2026-10-28",
    )
    _create_capacity_person("Consultant A", "acc-consultant-a")
    _create_capacity_person("Consultant B", "acc-consultant-b")
    _create_non_capacity_person("Developer Y", "acc-developer-y")
    # Developer X hat GAR KEINE lokale Person - simuliert einen unbekannten Jira-Autor.
    _cache_issue(project_id, "WMX-100", ["phase:configuration"])
    _add_worklog(project_id, "WMX-100", "acc-consultant-a", "2026-10-05", 40)
    _add_worklog(project_id, "WMX-100", "acc-consultant-b", "2026-10-06", 20)
    _add_worklog(project_id, "WMX-100", "acc-developer-x", "2026-10-07", 100)
    _add_worklog(project_id, "WMX-100", "acc-developer-y", "2026-10-08", 80)

    metrics = _get_metrics(phase["id"])
    if metrics["ist_hours"] != 60:
        _fail("Capacity Actual", f"erwartet 60h (40+20, Developer ausgefiltert), bekam {metrics}")
    if metrics["effort_consumption_pct"] != 75:
        _fail("Aufwandsverbrauch", f"erwartet 75% (nicht 300%), bekam {metrics}")

    coverage = _get_coverage(project_id)
    if coverage["project_ist_total"] != 240:
        _fail("Project/Jira Total Actual", f"erwartet 240h (unverändert, ALLE Autoren), bekam {coverage}")

    print("2/4  Testfall Abschnitt 54 — Unplanned Consultant (Christian ohne Assignment zählt trotzdem) ...")
    project_id2 = _create_project("Testprojekt P20.5 Unplanned")
    phase2 = _create_phase(
        project_id2, phase_type="Umsetzung", jira_label="phase:umsetzung",
        plan_fte=0.3, forecast_start="2026-10-01", forecast_end="2026-10-28",
    )
    dominik_id = _create_capacity_person("Dominik", "acc-dominik")
    _create_capacity_person("Christian", "acc-christian")
    _assign(phase2["id"], dominik_id, 0.2)
    _cache_issue(project_id2, "WMX-200", ["phase:umsetzung"])
    _add_worklog(project_id2, "WMX-200", "acc-dominik", "2026-10-05", 30)
    _add_worklog(project_id2, "WMX-200", "acc-christian", "2026-10-06", 10)

    metrics2 = _get_metrics(phase2["id"])
    if metrics2["ist_hours"] != 40:
        _fail("Unplanned Capacity Actual", f"erwartet 40h (30+10), bekam {metrics2}")
    data2 = _get_person_actuals(phase2["id"])
    planned_by_name = {p["display_name"]: p["planned"] for p in data2["persons"]}
    if planned_by_name.get("Dominik") is not True or planned_by_name.get("Christian") is not False:
        _fail("Planned/unplanned", f"erwartet Dominik=True/Christian=False, bekam {data2}")

    print("3/4  Outside-Scope-Transparenz: Developer-Stunden bleiben sichtbar, getrennt gezählt ...")
    outside = data2.get("outside_scope")
    if outside is None or outside["hours"] != 0:
        _fail("Outside-Scope Projekt 2 (keine Developer)", str(data2))
    data1 = _get_person_actuals(phase["id"])
    outside1 = data1.get("outside_scope")
    if outside1 is None or outside1["hours"] != 180 or outside1["author_count"] != 2:
        _fail("Outside-Scope Projekt 1", f"erwartet 180h/2 Autoren (Developer X+Y), bekam {data1}")
    names_in_persons = {p["display_name"] for p in data1["persons"]}
    if "Developer Y" in names_in_persons or any("developer" in n.lower() for n in names_in_persons):
        _fail("Developer sollte NICHT im primären Drilldown erscheinen", str(data1))

    print("4/4  Zeitraum-Aufschlüsselung (before/within/after) gegen aktuellen Plan ...")
    project_id3 = _create_project("Testprojekt P20.5 Breakdown")
    phase3 = _create_phase(
        project_id3, phase_type="Rollout", jira_label="phase:rollout",
        plan_fte=0.2, forecast_start="2026-10-01", forecast_end="2026-10-17",
    )
    _create_capacity_person("Consultant C", "acc-consultant-c")
    _cache_issue(project_id3, "WMX-300", ["phase:rollout"])
    _add_worklog(project_id3, "WMX-300", "acc-consultant-c", "2026-09-28", 3)  # vor dem Plan
    _add_worklog(project_id3, "WMX-300", "acc-consultant-c", "2026-10-10", 12)  # im Plan
    _add_worklog(project_id3, "WMX-300", "acc-consultant-c", "2026-10-20", 5)  # nach dem Plan

    tc = _get_time_control(phase3["id"])
    breakdown = tc["breakdown"]
    if breakdown["before_hours"] != 3 or breakdown["within_hours"] != 12 or breakdown["after_hours"] != 5:
        _fail("Breakdown", f"erwartet 3/12/5, bekam {breakdown}")
    metrics3 = _get_metrics(phase3["id"])
    if metrics3["ist_hours"] != 20:
        _fail("Ist-Aufwand trotz Zeitraum-Überschreitung", f"erwartet 20h (3+12+5, nicht abgeschnitten), bekam {metrics3}")

    print(
        "OK — P20.5 Capacity Scope: Developer-Ausfilterung (75% statt 300%), Project/Jira "
        "Total unverändert (240h), Unplanned Consultant zählt zum Capacity Actual, "
        "Outside-Scope-Transparenz und before/within/after-Aufschlüsselung (ohne "
        "Zeitraum-Kappung) funktionieren wie spezifiziert."
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
