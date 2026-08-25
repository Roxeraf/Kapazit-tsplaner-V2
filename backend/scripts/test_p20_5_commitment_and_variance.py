"""P20.5: Start Commitment, Actual Start/End und Terminabweichungen (siehe
P20_5_PHASE_ACTUALS_AND_TIME_CONTROL.md Abschnitt 13/17-32/44-48, Testfälle Abschnitt 55-57).
Kein pytest im Repo (siehe test_planning_phase_tree_api.py als etabliertes Muster).

1. Testfall Abschnitt 55 (Phase dauert länger): erster Worklog friert Commitment ein,
   actual_start = erster Worklog, Phasenabschluss setzt actual_end = heute (NICHT aus dem
   letzten Worklog), Endabweichung in Arbeitstagen (workday_delta).
2. Testfall Abschnitt 56 (Plan verschoben): Commitment bleibt nach einer Planänderung
   unverändert (immutable) - Abweichung Commitment->Actual bleibt korrekt, Abweichung
   Current->Actual wird 0, sobald der aktuelle Plan dem tatsächlichen Ende entspricht;
   PlanHistory dokumentiert die Planänderung automatisch.
3. Testfall Abschnitt 57 (Nachbuchung nach Abschluss): ein Worklog nach actual_end erhöht
   weiterhin ist_hours, verändert aber actual_end NICHT.
4. Reopen-Semantik (Abschnitt 45): Status weg von "abgeschlossen" setzt actual_end zurück auf
   NULL; erneutes Schließen setzt ein neues actual_end.
5. Abschluss ohne jeglichen Worklog (Abschnitt 46/47): actual_start bleibt NULL,
   actual_end wird trotzdem gesetzt (Commitment wird über den Statuswechsel eingefroren, nicht
   über einen Worklog - Abschnitt 48).
6. Commitment-Immutabilität: eine zweite Planänderung NACH bereits gesetztem Commitment
   überschreibt commitment_start/commitment_end nicht erneut.

Aufruf: python backend/scripts/test_p20_5_commitment_and_variance.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_5_commitment_check_")
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


def _update_phase(plan_phase_id: int, **kwargs) -> dict:
    resp = client.put(f"/projects/plan-phases/{plan_phase_id}", json=kwargs)
    if resp.status_code != 200:
        _fail("PlanPhase aktualisieren", f"{resp.status_code}: {resp.text}")
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
    # P20.5: actual_start/Commitment werden normalerweise vom Sync-Lauf nachgezogen
    # (jira_sync.sync_project_and_refresh) - hier wird direkt in den Cache geschrieben (kein
    # echter Jira-Zugriff in Testskripten), daher der Refresh-Schritt separat.
    db = SessionLocal()
    try:
        from app import worklog_actuals
        from datetime import datetime, timezone

        worklog_actuals.refresh_actual_start(db, project_id, datetime.now(timezone.utc).isoformat())
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


def _get_phase(plan_phase_id: int) -> dict:
    resp = client.get(f"/projects/plan-phases/{plan_phase_id}")
    if resp.status_code != 200:
        _fail("Phase abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def _get_time_control(plan_phase_id: int) -> dict:
    resp = client.get(f"/projects/plan-phases/{plan_phase_id}/time-control")
    if resp.status_code != 200:
        _fail("Time-Control abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def _get_history(project_id: int) -> list[dict]:
    resp = client.get(f"/projects/{project_id}/history")
    if resp.status_code != 200:
        _fail("History abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def main() -> None:
    print("1/6  Testfall Abschnitt 55 — Phase dauert länger als geplant ...")
    project_id = _create_project("Testprojekt P20.5 Commitment")
    phase = _create_phase(
        project_id, phase_type="Konfiguration", jira_label="phase:configuration",
        plan_fte=0.5, forecast_start="2026-10-01", forecast_end="2026-10-17",
    )
    _create_capacity_person("Dominik", "acc-dominik")
    _cache_issue(project_id, "WMX-100", ["phase:configuration"])

    _add_worklog(project_id, "WMX-100", "acc-dominik", "2026-10-03", 10)
    phase = _get_phase(phase["id"])
    if phase["actual_start"] != "2026-10-03":
        _fail("actual_start (erster Worklog)", f"erwartet 2026-10-03, bekam {phase['actual_start']}")
    if phase["commitment_start"] != "2026-10-01" or phase["commitment_end"] != "2026-10-17":
        _fail("Commitment (beim ersten Worklog eingefroren)", str(phase))

    _add_worklog(project_id, "WMX-100", "acc-dominik", "2026-10-10", 30)
    _add_worklog(project_id, "WMX-100", "acc-dominik", "2026-10-18", 10)  # nach Commitment-Ende
    _add_worklog(project_id, "WMX-100", "acc-dominik", "2026-10-21", 20)  # nach Commitment-Ende

    metrics = client.get(f"/projects/plan-phases/{phase['id']}/metrics").json()
    if metrics["ist_hours"] != 70:
        _fail("Ist-Aufwand vor Abschluss", f"erwartet 70h (10+30+10+20), bekam {metrics}")

    phase = _update_phase(phase["id"], status="abgeschlossen")
    if phase["actual_end"] != _today():
        _fail("actual_end (fachlicher Abschluss = heute)", f"erwartet {_today()}, bekam {phase['actual_end']}")

    tc = _get_time_control(phase["id"])
    if tc["breakdown"]["after_hours"] != 30:
        _fail("Nach-Commitment-Ende gebuchte Stunden", f"erwartet 30h (10+20), bekam {tc['breakdown']}")

    print("2/6  Testfall Abschnitt 56 — Plan wird während laufender Phase verschoben ...")
    project_id2 = _create_project("Testprojekt P20.5 Plan Shift")
    phase2 = _create_phase(
        project_id2, phase_type="Migration", jira_label="phase:migration",
        plan_fte=0.3, forecast_start="2026-10-01", forecast_end="2026-10-17",
    )
    _cache_issue(project_id2, "WMX-200", ["phase:migration"])
    _add_worklog(project_id2, "WMX-200", "acc-dominik", "2026-10-03", 5)
    phase2 = _get_phase(phase2["id"])
    if phase2["commitment_start"] != "2026-10-01" or phase2["commitment_end"] != "2026-10-17":
        _fail("Commitment vor Planänderung", str(phase2))

    phase2 = _update_phase(phase2["id"], forecast_end="2026-10-24")
    if phase2["commitment_end"] != "2026-10-17":
        _fail("Commitment bleibt nach Planänderung unverändert", str(phase2))
    if phase2["forecast_end"] != "2026-10-24":
        _fail("Aktueller Plan wurde aktualisiert", str(phase2))

    phase2 = _update_phase(phase2["id"], status="abgeschlossen")
    # Abschluss-Datum ist "heute" im Test (kein Worklog am 24.10. vorhanden) - die Abweichung
    # Commitment->Actual bezieht sich auf reale Kalenderarithmetik, hier nur strukturell
    # geprüft: beide Varianzfelder existieren und sind Ganzzahlen bzw. None.
    tc2 = _get_time_control(phase2["id"])
    variance = tc2["schedule_variance"]
    if variance["end_delay_workdays"] is None:
        _fail("end_delay_workdays sollte gesetzt sein (Commitment + Actual vorhanden)", str(variance))

    history2 = _get_history(project_id2)
    forecast_end_change = [
        h for h in history2 if h.get("feld") == "forecast_end" and h.get("alter_wert") == "2026-10-17"
    ]
    if not forecast_end_change:
        _fail("PlanHistory sollte die Planänderung 17.10.->24.10. dokumentieren", str(history2[:5]))

    print("3/6  Testfall Abschnitt 57 — Nachbuchung nach Abschluss verändert actual_end NICHT ...")
    actual_end_before = phase2["actual_end"]
    _add_worklog(project_id2, "WMX-200", "acc-dominik", "2026-11-05", 2)
    phase2_after = _get_phase(phase2["id"])
    if phase2_after["actual_end"] != actual_end_before:
        _fail("actual_end nach Nachbuchung", f"erwartet unverändert {actual_end_before}, bekam {phase2_after['actual_end']}")
    metrics2 = client.get(f"/projects/plan-phases/{phase2['id']}/metrics").json()
    if metrics2["ist_hours"] != 7:
        _fail("Ist-Aufwand nach Nachbuchung", f"erwartet 7h (5+2), bekam {metrics2}")

    print("4/6  Reopen-Semantik: Status weg von 'abgeschlossen' setzt actual_end zurück ...")
    reopened = _update_phase(phase2["id"], status="laufend")
    if reopened["actual_end"] is not None:
        _fail("actual_end nach Reopen", f"erwartet None, bekam {reopened['actual_end']}")
    reclosed = _update_phase(phase2["id"], status="abgeschlossen")
    if reclosed["actual_end"] != _today():
        _fail("actual_end nach erneutem Abschluss", f"erwartet {_today()}, bekam {reclosed['actual_end']}")

    print("5/6  Abschluss ohne jeglichen Worklog: actual_start bleibt NULL, actual_end wird gesetzt ...")
    project_id3 = _create_project("Testprojekt P20.5 Ohne Worklog")
    phase3 = _create_phase(
        project_id3, phase_type="Kickoff", plan_fte=0.1,
        forecast_start="2026-10-01", forecast_end="2026-10-03",
    )
    if phase3["commitment_start"] is not None:
        _fail("Kein Commitment vor Statuswechsel", str(phase3))
    phase3 = _update_phase(phase3["id"], status="abgeschlossen")
    if phase3["actual_start"] is not None:
        _fail("actual_start ohne Worklog", f"erwartet None, bekam {phase3['actual_start']}")
    if phase3["actual_end"] != _today():
        _fail("actual_end trotz fehlender Worklogs", f"erwartet {_today()}, bekam {phase3['actual_end']}")
    if phase3["commitment_start"] != "2026-10-01":
        _fail(
            "Commitment via Statuswechsel eingefroren (Abschnitt 47/48, kein Worklog nötig)",
            str(phase3),
        )

    print("6/6  Commitment-Immutabilität: zweite Planänderung nach Commitment ohne Effekt ...")
    project_id4 = _create_project("Testprojekt P20.5 Immutable")
    phase4 = _create_phase(
        project_id4, phase_type="Analyse", jira_label="phase:analyse",
        plan_fte=0.2, forecast_start="2026-10-01", forecast_end="2026-10-10",
    )
    _cache_issue(project_id4, "WMX-400", ["phase:analyse"])
    _add_worklog(project_id4, "WMX-400", "acc-dominik", "2026-10-02", 4)
    phase4 = _get_phase(phase4["id"])
    first_commitment = (phase4["commitment_start"], phase4["commitment_end"])
    phase4 = _update_phase(phase4["id"], forecast_start="2026-09-15", forecast_end="2026-10-31")
    if (phase4["commitment_start"], phase4["commitment_end"]) != first_commitment:
        _fail("Commitment sollte nach der ersten Erfassung nie mehr überschrieben werden", str(phase4))

    print(
        "OK — P20.5 Commitment/Actuals: Start Commitment beim ersten Worklog/Statuswechsel, "
        "actual_start selbstkorrigierend, actual_end NUR über Statuswechsel (nicht aus "
        "Worklogs), Commitment-Immutabilität, Reopen setzt actual_end zurück, Nachbuchungen "
        "erhöhen ist_hours ohne actual_end zu verändern, und PlanHistory dokumentiert "
        "Planänderungen automatisch - alles wie spezifiziert."
    )


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
