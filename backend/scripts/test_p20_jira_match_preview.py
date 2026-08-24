"""P20.5: Tests für die Mapping-Preview (GET /projects/plan-phases/{id}/jira-matches), siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 10. Kein pytest im Repo (siehe
test_planning_phase_tree_api.py als etabliertes Muster):

1. Label ohne Treffer -> matched_issues=0, sample_issue_keys=[], as_of=None.
2. Label mit zwei Treffer-Issues -> korrekte matched_issues/matched_worklogs/total_hours,
   as_of = Stand des letzten Syncs (nicht None).
3. Preview ist unabhängig davon, ob die Phase das Label bereits gespeichert hat (reine
   Vorschau vor dem Speichern).

Aufruf: python backend/scripts/test_p20_jira_match_preview.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_jira_match_preview_check_")
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
                jira_account_id=account_id, jira_issue_key=issue_key, datum=datum, stunden=stunden,
                projekt_mapping=str(project_id),
            )
        )
        db.commit()
    finally:
        db.close()


def main() -> None:
    print("1/3  Label ohne Treffer -> leeres Ergebnis ...")
    project_id = _create_project("Testprojekt P20.5")
    phase = _create_phase(project_id, phase_type="Konfiguration")

    resp = client.get(f"/projects/plan-phases/{phase['id']}/jira-matches", params={"label": "phase:nirgends"})
    if resp.status_code != 200:
        _fail("Preview abrufen (leer)", f"{resp.status_code}: {resp.text}")
    data = resp.json()
    if data["matched_issues"] != 0 or data["sample_issue_keys"] != [] or data["as_of"] is not None:
        _fail("Leere Preview", str(data))

    print("2/3  Label mit zwei Treffer-Issues -> korrekte Zählung ...")
    db = SessionLocal()
    try:
        project = db.get(models.Project, project_id)
        jira_sync._upsert_issue_cache(
            db,
            project,
            [
                {"key": "WMX-100", "id": "1", "labels": ["phase:configuration"], "component": None, "summary": "A"},
                {"key": "WMX-101", "id": "2", "labels": ["phase:configuration", "sonstiges"], "component": None, "summary": "B"},
                {"key": "WMX-102", "id": "3", "labels": ["anderes-label"], "component": None, "summary": "C"},
            ],
        )
        db.commit()
    finally:
        db.close()
    _add_worklog(project_id, "WMX-100", "acc-a", "2026-10-05", 10)
    _add_worklog(project_id, "WMX-100", "acc-b", "2026-10-06", 5)
    _add_worklog(project_id, "WMX-101", "acc-a", "2026-10-07", 3)
    _add_worklog(project_id, "WMX-102", "acc-a", "2026-10-08", 99)  # anderes Label, darf nicht mitzählen

    resp = client.get(f"/projects/plan-phases/{phase['id']}/jira-matches", params={"label": "phase:configuration"})
    if resp.status_code != 200:
        _fail("Preview abrufen (Treffer)", f"{resp.status_code}: {resp.text}")
    data = resp.json()
    if data["matched_issues"] != 2:
        _fail("matched_issues", str(data))
    if data["matched_worklogs"] != 3:
        _fail("matched_worklogs", str(data))
    if data["total_hours"] != 18:  # 10+5+3, NICHT die 99h des anderen Labels
        _fail("total_hours", str(data))
    if set(data["sample_issue_keys"]) != {"WMX-100", "WMX-101"}:
        _fail("sample_issue_keys", str(data))
    if data["as_of"] is None:
        _fail("as_of", str(data))

    print("3/3  Preview funktioniert unabhängig vom gespeicherten jira_label der Phase ...")
    # Phase hat noch KEIN jira_label gespeichert - Preview greift trotzdem (Vorschau vor dem Speichern).
    detail = client.get(f"/projects/plan-phases/{phase['id']}").json()
    if detail["jira_label"] is not None:
        _fail("Ausgangszustand", f"Phase sollte noch kein jira_label haben: {detail}")

    print(
        "OK — P20.5: Mapping-Preview liefert 0 Treffer für ein unbekanntes Label, korrekte "
        "Zählung/Summe für ein Label mit mehreren Issues (ohne fremde Labels mitzuzählen) "
        "und funktioniert unabhängig vom bereits gespeicherten jira_label der Phase."
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
