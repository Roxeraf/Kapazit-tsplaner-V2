"""P20.6: Tests für den Personen-Drilldown + Planned-vs-Actual-Vergleich
(GET /projects/plan-phases/{id}/person-actuals), siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 17/18/24/25/28. Kein pytest im Repo
(siehe test_planning_phase_tree_api.py als etabliertes Muster):

1. AT1-Personen: Dominik 32h, Max 20h, Anna 8h -> drei Zeilen, Summe 60h == ist_hours,
   keine Doppelzählung.
2. AT8 (Planned vs. Actual): geplant Dominik+Max, Ist Dominik+Anna -> Anna erscheint als
   "nicht eingeplant" (planned=False), Max als "eingeplant, bisher kein Ist"
   (planned_without_actual), Dominik in beiden (planned=True in persons).
3. Unplanned Actual Hours: Summe der Ist-Stunden von Personen ohne Assignment.
4. Kein Mapping -> ist_hours und unplanned_actual_hours beide None, persons leer.
5. Parent-Aggregation: Personen-Stunden aus zwei Kind-Phasen werden korrekt zusammengeführt.
6. Unbekannter Jira-Account (kein Person.jira_account_id-Treffer) erscheint trotzdem mit
   Account-ID als Anzeigename, planned=False (keine Assignment-Zuordnung möglich).

Aufruf: python backend/scripts/test_p20_person_actuals.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_person_actuals_check_")
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


def _create_person(display_name: str, jira_account_id: str) -> int:
    """P20.5: eine über /people angelegte Person ist noch NICHT automatisch
    kapazitätsplanbar (kein ResourceProfile) - für den Personen-Drilldown (Capacity Actual)
    wird hier zusätzlich ein ResourceProfile mit capacity_relevant=True angelegt, sonst
    zählen ihre Worklogs seit P20.5 nur noch als "außerhalb Kapazitätsscope"."""
    resp = client.post("/people", json={"display_name": display_name, "jira_account_id": jira_account_id})
    if resp.status_code != 201:
        _fail("Person anlegen", f"{resp.status_code}: {resp.text}")
    person_id = resp.json()["id"]
    resp = client.post(f"/people/{person_id}/resource-profile", json={"weekly_hours": 40, "capacity_relevant": True})
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


def _get_person_actuals(plan_phase_id: int) -> dict:
    resp = client.get(f"/projects/plan-phases/{plan_phase_id}/person-actuals")
    if resp.status_code != 200:
        _fail("Person-Actuals abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def _assign(plan_phase_id: int, person_id: int, fte: float) -> None:
    resp = client.post(f"/projects/plan-phases/{plan_phase_id}/assign-person", json={"person_id": person_id, "fte": fte})
    if resp.status_code != 200:
        _fail("Person zuweisen", f"{resp.status_code}: {resp.text}")


def main() -> None:
    print("1/6  AT1-Personen: Dominik 32h, Max 20h, Anna 8h -> Summe 60h, keine Doppelzählung ...")
    project_id = _create_project("Testprojekt P20.6")
    phase = _create_phase(
        project_id, phase_type="Konfiguration", jira_label="phase:configuration",
        plan_fte=0.5, forecast_start="2026-10-01", forecast_end="2026-10-28",
    )
    dominik_id = _create_person("Dominik", "acc-dominik")
    _create_person("Max", "acc-max")
    anna_id = _create_person("Anna", "acc-anna")
    # Eigene Person für den "eingeplant, aber bisher kein Ist"-Fall (Max hat in diesem
    # Testprojekt bereits Ist-Stunden aus Schritt 1 - AT1 und AT8 sind fachlich unabhängige
    # Beispiele aus dem Auftrag, hier bewusst mit eigenen Personen nachgebildet, damit sich
    # die beiden Szenarien nicht widersprechen).
    lisa_id = _create_person("Lisa", "acc-lisa")

    _cache_issue(project_id, "WMX-100", ["phase:configuration"])
    _add_worklog(project_id, "WMX-100", "acc-dominik", "2026-10-05", 32)
    _add_worklog(project_id, "WMX-100", "acc-max", "2026-10-06", 20)
    _add_worklog(project_id, "WMX-100", "acc-anna", "2026-10-07", 8)

    data = _get_person_actuals(phase["id"])
    if data["ist_hours"] != 60:
        _fail("ist_hours", str(data))
    hours_by_name = {p["display_name"]: p["hours"] for p in data["persons"]}
    if hours_by_name != {"Dominik": 32, "Max": 20, "Anna": 8}:
        _fail("Personen-Stunden", str(data))
    if round(sum(hours_by_name.values()), 2) != data["ist_hours"]:
        _fail("Summe == ist_hours", str(data))

    print("2/6  AT8 — Planned vs. Actual: Dominik+Lisa geplant, Dominik+Anna Ist ...")
    _assign(phase["id"], dominik_id, 0.3)
    _assign(phase["id"], lisa_id, 0.2)
    data = _get_person_actuals(phase["id"])
    planned_by_name = {p["display_name"]: p["planned"] for p in data["persons"]}
    if planned_by_name.get("Dominik") is not True:
        _fail("Dominik sollte planned=True sein", str(data))
    if planned_by_name.get("Anna") is not False:
        _fail("Anna sollte planned=False sein (nicht eingeplant)", str(data))
    if [p["person_name"] for p in data["planned_without_actual"]] != ["Lisa"]:
        _fail("Lisa sollte in planned_without_actual stehen (eingeplant, bisher kein Ist)", str(data))

    print("3/6  Unplanned Actual Hours: Summe der Ist-Stunden ungeplanter Personen (Anna 8h + Max 20h) ...")
    if data["unplanned_actual_hours"] != 28:
        _fail("unplanned_actual_hours", str(data))

    print("4/6  Kein Mapping -> ist_hours/unplanned_actual_hours None, persons leer ...")
    phase_unmapped = _create_phase(project_id, phase_type="Testing", plan_fte=0.2)
    data = _get_person_actuals(phase_unmapped["id"])
    if data["ist_hours"] is not None or data["unplanned_actual_hours"] is not None:
        _fail("Kein-Mapping-Zustand", str(data))
    if data["persons"] != []:
        _fail("persons sollte leer sein ohne Mapping", str(data))

    print("5/6  Parent-Aggregation: Personen-Stunden aus zwei Kind-Phasen zusammenführen ...")
    parent = _create_phase(project_id, phase_type="Wareneingang")
    child1 = _create_phase(project_id, phase_type="Schnittstellen", parent_phase_id=parent["id"], jira_label="phase:schnittstellen")
    child2 = _create_phase(project_id, phase_type="WE-Anmeldung", parent_phase_id=parent["id"], jira_label="phase:we-anmeldung")
    _cache_issue(project_id, "WMX-200", ["phase:schnittstellen"])
    _cache_issue(project_id, "WMX-201", ["phase:we-anmeldung"])
    _add_worklog(project_id, "WMX-200", "acc-dominik", "2026-10-10", 15)
    _add_worklog(project_id, "WMX-201", "acc-dominik", "2026-10-11", 5)  # dieselbe Person, zwei Kinder
    _add_worklog(project_id, "WMX-201", "acc-max", "2026-10-12", 10)

    data = _get_person_actuals(parent["id"])
    if data["ist_hours"] != 30:
        _fail("Parent ist_hours", str(data))
    hours_by_name = {p["display_name"]: p["hours"] for p in data["persons"]}
    if hours_by_name != {"Dominik": 20, "Max": 10}:  # 15+5 zusammengeführt, keine getrennten Zeilen
        _fail("Parent Personen-Stunden (zusammengeführt über Kinder)", str(data))

    print("6/6  P20.5 — Unbekannter Jira-Account: NICHT im primären Drilldown, sondern outside_scope ...")
    # Abschnitt 3/9: ein Jira-Autor ohne kapazitätsplanbare lokale Person zählt nicht zum
    # Capacity Actual - seine Stunden bleiben sichtbar, aber getrennt (outside_scope), nicht
    # länger als reguläre Zeile in `persons` (das wäre vor P20.5 der Fall gewesen).
    _add_worklog(project_id, "WMX-200", "acc-unbekannt", "2026-10-13", 4)
    data = _get_person_actuals(parent["id"])
    unknown = next((p for p in data["persons"] if p["jira_account_id"] == "acc-unbekannt"), None)
    if unknown is not None:
        _fail("Unbekannter Account sollte NICHT in persons erscheinen (P20.5 Capacity Scope)", str(unknown))
    if data["ist_hours"] != 30:
        _fail("ist_hours darf durch den unbekannten Account nicht verändert werden", str(data))
    if data["outside_scope"] is None or data["outside_scope"]["hours"] != 4 or data["outside_scope"]["author_count"] != 1:
        _fail("outside_scope sollte 4h/1 Autor zeigen", str(data))

    print(
        "OK — P20.6/P20.5: Personen-Drilldown (AT1: 32/20/8=60h), Planned-vs-Actual (AT8: Anna "
        "nicht eingeplant, Lisa eingeplant ohne Ist), Unplanned Actual Hours, Kein-Mapping-"
        "Zustand, Parent-Aggregation über Personen hinweg und Capacity-Scope-Filterung "
        "(unbekannte Accounts landen in outside_scope, nicht mehr im primären Drilldown) "
        "funktionieren wie spezifiziert."
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
