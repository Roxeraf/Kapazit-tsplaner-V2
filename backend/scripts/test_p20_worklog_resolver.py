"""P20.2: Tests für den Worklog->PlanPhase-Resolver (app/worklog_resolver.py), siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 8/28 (BD-1A/B/C CLOSED). Kein pytest im
Repo (siehe test_planning_phase_tree_api.py als etabliertes Muster):

1. resolve_issue() (reine Funktion, kein DB-Zugriff): UNMAPPED ohne Treffer, MATCHED bei
   genau einem Label-Treffer, AMBIGUOUS bei mehreren unterschiedlichen Phasen-Treffern
   (keine Doppelzählung - genau ein Status, keine zwei Phasen gleichzeitig), MATCHED über
   Override unabhängig von (sogar widersprüchlichen) Labels - Override hat Vorrang.
2. resolve_project_issues() (Integration gegen echte DB-Zeilen): kombiniert Label-Match,
   Override, Ambiguous und Unmapped über mehrere Issues eines Projekts; Override für ein
   Issue, das noch nicht im JiraIssueCache steht, löst trotzdem MATCHED auf; ein zweites
   Projekt mit identischen Labels beeinflusst die Auflösung nicht (Projekt-Scope).
3. Parallele Phasen mit identischem Zeitraum (AT5): Resolver unterscheidet ausschließlich
   über Labels, `forecast_start`/`forecast_end` werden nie gesetzt und nie konsultiert.

Aufruf: python backend/scripts/test_p20_worklog_resolver.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_resolver_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from fastapi.testclient import TestClient  # noqa: E402

from app import jira_sync, models, worklog_resolver  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402 - Import triggert db_bootstrap.run_migrations()
from app.worklog_resolver import ResolutionStatus  # noqa: E402

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


def main() -> None:
    print("1/3  resolve_issue() (reine Funktion) — Unmapped/Matched/Ambiguous/Override ...")
    phases_by_label = {"phase:configuration": [1], "phase:testing": [2]}

    r = worklog_resolver.resolve_issue("WMX-1", [], None, phases_by_label)
    if r.status is not ResolutionStatus.UNMAPPED or r.plan_phase_id is not None:
        _fail("Unmapped (keine Labels)", str(r))

    r = worklog_resolver.resolve_issue("WMX-2", ["irrelevant"], None, phases_by_label)
    if r.status is not ResolutionStatus.UNMAPPED:
        _fail("Unmapped (kein passendes Label)", str(r))

    r = worklog_resolver.resolve_issue("WMX-3", ["phase:configuration"], None, phases_by_label)
    if r.status is not ResolutionStatus.MATCHED or r.plan_phase_id != 1 or r.mapping_source != "jira_label":
        _fail("Matched (ein Label)", str(r))

    r = worklog_resolver.resolve_issue(
        "WMX-4", ["phase:configuration", "phase:testing"], None, phases_by_label
    )
    if r.status is not ResolutionStatus.AMBIGUOUS or r.plan_phase_id is not None:
        _fail("Ambiguous (zwei Phasen-Labels)", str(r))
    if r.candidate_phase_ids != (1, 2):
        _fail("Ambiguous candidate_phase_ids", str(r))

    # Override hat Vorrang, sogar wenn die Labels für sich genommen ambiguous wären.
    r = worklog_resolver.resolve_issue(
        "WMX-5", ["phase:configuration", "phase:testing"], 99, phases_by_label
    )
    if r.status is not ResolutionStatus.MATCHED or r.plan_phase_id != 99 or r.mapping_source != "manual_override":
        _fail("Override sticht Ambiguous", str(r))

    print("2/3  resolve_project_issues() — Integration gegen echte DB-Zeilen ...")
    project_id = _create_project("Testprojekt P20.2")
    other_project_id = _create_project("Anderes Projekt (gleiche Labels)")

    phase_config = _create_phase(project_id, phase_type="Konfiguration", jira_label="phase:configuration")
    phase_testing = _create_phase(project_id, phase_type="Testing", jira_label="phase:testing")
    # Zweites Projekt mit identischem Label - darf die Auflösung des ersten nicht beeinflussen.
    other_phase = _create_phase(other_project_id, phase_type="Konfiguration", jira_label="phase:configuration")

    db = SessionLocal()
    try:
        project = db.get(models.Project, project_id)
        other_project = db.get(models.Project, other_project_id)
        jira_sync._upsert_issue_cache(
            db,
            project,
            [
                {"key": "WMX-100", "id": "1", "labels": ["phase:configuration"], "component": None, "summary": None},
                {"key": "WMX-101", "id": "2", "labels": ["phase:configuration", "phase:testing"], "component": None, "summary": None},
                {"key": "WMX-102", "id": "3", "labels": ["unbekanntes-label"], "component": None, "summary": None},
            ],
        )
        jira_sync._upsert_issue_cache(
            db, other_project, [{"key": "WMX-200", "id": "4", "labels": ["phase:configuration"], "component": None, "summary": None}]
        )
        db.commit()
    finally:
        db.close()

    # Manueller Override für WMX-102 (sonst UNMAPPED) - direkt über die P20.1-API angelegt.
    resp = client.post(
        f"/projects/plan-phases/{phase_testing['id']}/worklog-overrides",
        json={"jira_issue_key": "WMX-102", "previous_status": "unmapped"},
    )
    if resp.status_code != 201:
        _fail("Override für WMX-102 anlegen", f"{resp.status_code}: {resp.text}")
    # Override für ein Issue, das (noch) nicht im JiraIssueCache steht.
    resp = client.post(
        f"/projects/plan-phases/{phase_config['id']}/worklog-overrides", json={"jira_issue_key": "WMX-999"}
    )
    if resp.status_code != 201:
        _fail("Override für ungecachtes Issue anlegen", f"{resp.status_code}: {resp.text}")

    db = SessionLocal()
    try:
        resolution = worklog_resolver.resolve_project_issues(db, project_id)
    finally:
        db.close()

    if resolution["WMX-100"].status is not ResolutionStatus.MATCHED or resolution["WMX-100"].plan_phase_id != phase_config["id"]:
        _fail("WMX-100 (eindeutiges Label)", str(resolution.get("WMX-100")))
    if resolution["WMX-101"].status is not ResolutionStatus.AMBIGUOUS:
        _fail("WMX-101 (zwei Phasen-Labels)", str(resolution.get("WMX-101")))
    if set(resolution["WMX-101"].candidate_phase_ids) != {phase_config["id"], phase_testing["id"]}:
        _fail("WMX-101 candidate_phase_ids", str(resolution.get("WMX-101")))
    if (
        resolution["WMX-102"].status is not ResolutionStatus.MATCHED
        or resolution["WMX-102"].plan_phase_id != phase_testing["id"]
        or resolution["WMX-102"].mapping_source != "manual_override"
    ):
        _fail("WMX-102 (Override sticht unbekanntes Label)", str(resolution.get("WMX-102")))
    if (
        resolution["WMX-999"].status is not ResolutionStatus.MATCHED
        or resolution["WMX-999"].plan_phase_id != phase_config["id"]
    ):
        _fail("WMX-999 (Override ohne Cache-Eintrag)", str(resolution.get("WMX-999")))
    if len(resolution) != 4:
        _fail("Ergebnis-Umfang", f"erwartet genau 4 Issues (100/101/102/999), bekam: {list(resolution)}")

    # Projekt-Scope: das zweite Projekt mit identischem Label wird komplett getrennt aufgelöst.
    db = SessionLocal()
    try:
        other_resolution = worklog_resolver.resolve_project_issues(db, other_project_id)
    finally:
        db.close()
    if other_resolution["WMX-200"].plan_phase_id != other_phase["id"]:
        _fail("Projekt-Scope", f"WMX-200 haette auf das andere Projekt aufloesen muessen: {other_resolution}")

    print("3/3  Parallele Phasen mit identischem Zeitraum (AT5) — keine Datumsheuristik ...")
    resp = client.put(
        f"/projects/plan-phases/{phase_config['id']}",
        json={"forecast_start": "2026-10-01", "forecast_end": "2026-10-31"},
    )
    if resp.status_code != 200:
        _fail("Phase A Zeitraum setzen", f"{resp.status_code}: {resp.text}")
    resp = client.put(
        f"/projects/plan-phases/{phase_testing['id']}",
        json={"forecast_start": "2026-10-01", "forecast_end": "2026-10-31"},
    )
    if resp.status_code != 200:
        _fail("Phase B Zeitraum setzen", f"{resp.status_code}: {resp.text}")
    # Identischer Zeitraum auf beiden Phasen geaendert - WMX-100 (nur phase:configuration-Label)
    # muss weiterhin eindeutig auf Phase A aufloesen, rein ueber das Label.
    db = SessionLocal()
    try:
        resolution_after = worklog_resolver.resolve_project_issues(db, project_id)
    finally:
        db.close()
    if resolution_after["WMX-100"].plan_phase_id != phase_config["id"]:
        _fail("Parallele Phasen (identischer Zeitraum)", str(resolution_after.get("WMX-100")))

    print(
        "OK — P20.2: resolve_issue() (Unmapped/Matched/Ambiguous/Override-Vorrang) und "
        "resolve_project_issues() (Projekt-Scope, Override ohne Cache-Eintrag, parallele "
        "Phasen ohne Datumseinfluss) funktionieren wie spezifiziert."
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
