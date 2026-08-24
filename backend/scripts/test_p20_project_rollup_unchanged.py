"""P20.7: Verifiziert, dass Projekt-/Portfolio-Rollup (GET /projects/{id}, GET /gap,
GET /forecast) durch die Phase-Mapping-Domain (P20.1-P20.6) UNVERÄNDERT bleibt, siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 20/22/28 ("Project Actual bleibt
führend", "Forecast Assessment bleibt unverändert"). Kein pytest im Repo (siehe
test_planning_phase_tree_api.py als etabliertes Muster):

1. `project.ist` (`GET /projects/{id}`) ist identisch, ob eine Leaf-Phase ein `jira_label`
   trägt oder nicht - Phase-Mapping ist eine zusätzliche Aufschlüsselung derselben
   `jira_worklogs_cache`-Zeilen, kein Ersatz (Abschnitt 20).
2. Dieselbe Invarianz für `GET /gap` (`ist`/`gap`/`gap_pct`) und `GET /forecast`.
3. Coverage < 100 % (Ambiguous/Unmapped-Anteil vorhanden) ändert an 1./2. nichts - Projekt-
   Ist wird nie aus den Phasen zurückgerechnet.

Aufruf: python backend/scripts/test_p20_project_rollup_unchanged.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_rollup_unchanged_check_")
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
    resp = client.post(
        "/projects",
        json={"name": name, "start_monat": "10.2026", "anzahl_monate": 3, "jira_component": "DEMO"},
    )
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


def _create_person(display_name: str, jira_account_id: str) -> None:
    resp = client.post("/people", json={"display_name": display_name, "jira_account_id": jira_account_id})
    if resp.status_code != 201:
        _fail("Person anlegen", f"{resp.status_code}: {resp.text}")


def main() -> None:
    print("1/3  Ausgangszustand (alle Worklogs vorhanden, aber KEIN PlanPhase-Mapping konfiguriert) erfassen ...")
    project_id = _create_project("Testprojekt P20.7")
    _create_person("Dominik", "acc-dominik")
    _create_person("Anna", "acc-anna")
    # Alle Worklog-Zeilen VOR dem "Vorher"-Snapshot anlegen - Schritt 2 darf danach nur noch
    # Mapping-Konfiguration (PlanPhase.jira_label/JiraIssueCache/Override) ändern, keine
    # jira_worklogs_cache-Zeilen mehr, sonst würde ein legitim geänderter Ist-Wert
    # fälschlich als Regression erscheinen.
    _add_worklog(project_id, "WMX-100", "acc-dominik", "2026-10-05", 32)
    _add_worklog(project_id, "WMX-101", "acc-anna", "2026-10-06", 8)
    _add_worklog(project_id, "WMX-102", "acc-dominik", "2026-10-07", 20)

    project_before = client.get(f"/projects/{project_id}").json()
    gap_before = client.get(f"/gap/{project_id}").json()
    forecast_before = client.get("/forecast").json()
    forecast_entry_before = next(f for f in forecast_before if f["project_id"] == project_id)

    if project_before["ist"] == {}:
        _fail("Ausgangszustand", "project.ist sollte bereits Buchungen zeigen (Vorbedingung)")

    print("2/3  Volle Phase-Mapping-Domain aktivieren (Label, Override, Ambiguous, Unmapped) ...")
    phase_a = _create_phase(project_id, phase_type="Konfiguration", jira_label="phase:configuration")
    phase_b = _create_phase(project_id, phase_type="Testing", jira_label="phase:testing")
    _cache_issue(project_id, "WMX-100", ["phase:configuration"])
    # WMX-101 bekommt zwei widersprüchliche Phase-Labels -> AMBIGUOUS (Coverage < 100%).
    _cache_issue(project_id, "WMX-101", ["phase:configuration", "phase:testing"])
    # Zusätzliches, komplett unzugeordnetes Issue (Worklog dazu existiert bereits seit Schritt 1).
    _cache_issue(project_id, "WMX-102", ["irrelevant"])

    resp = client.post(
        f"/projects/plan-phases/{phase_b['id']}/worklog-overrides", json={"jira_issue_key": "WMX-999"}
    )
    if resp.status_code != 201:
        _fail("Override anlegen", f"{resp.status_code}: {resp.text}")

    coverage = client.get(f"/projects/{project_id}/actuals-coverage").json()
    if coverage["coverage_pct"] is None or coverage["coverage_pct"] >= 100:
        _fail("Vorbedingung Coverage < 100%", str(coverage))
    if coverage["ambiguous_total"] <= 0:
        _fail("Vorbedingung Ambiguous > 0", str(coverage))
    print(f"    Coverage jetzt {coverage['coverage_pct']}% (Ambiguous {coverage['ambiguous_total']}h) - Rollup wird trotzdem geprüft.")

    print("3/3  Projekt-Ist/GAP/Forecast vergleichen - müssen byte-identisch bleiben ...")
    project_after = client.get(f"/projects/{project_id}").json()
    gap_after = client.get(f"/gap/{project_id}").json()
    forecast_after = client.get("/forecast").json()
    forecast_entry_after = next(f for f in forecast_after if f["project_id"] == project_id)

    if project_before["ist"] != project_after["ist"]:
        _fail("project.ist verändert", f"vorher={project_before['ist']} nachher={project_after['ist']}")
    for key in ("ist", "gap", "gap_pct", "soll", "hochrechnung", "soll_gesamt", "projiziert_gesamt", "gap_gesamt", "status"):
        if gap_before[key] != gap_after[key]:
            _fail(f"GAP-Feld '{key}' verändert", f"vorher={gap_before[key]} nachher={gap_after[key]}")
    if forecast_entry_before != forecast_entry_after:
        _fail("Forecast-Eintrag verändert", f"vorher={forecast_entry_before} nachher={forecast_entry_after}")

    print(
        "OK — P20.7: GET /projects/{id} (ist), GET /gap und GET /forecast bleiben byte-"
        "identisch, obwohl PlanPhase-Mapping (Label, Override, Ambiguous, Unmapped, "
        "Coverage < 100%) vollständig konfiguriert ist - Projekt-Ist bleibt führend "
        "(Abschnitt 20), keine Rückrechnung aus den Phasen."
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
