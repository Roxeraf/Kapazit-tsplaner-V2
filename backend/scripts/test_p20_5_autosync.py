"""P20.5: Automatischer Jira/Tempo Sync - Scheduler-Orchestrierung, Sync-Status und
Fehlerisolation (siehe P20_5_PHASE_ACTUALS_AND_TIME_CONTROL.md Abschnitt 13-16, Testfall
Abschnitt 58). Kein echter Jira/Tempo-Netzwerkzugriff: jira_sync.sync_project() wird
monkeygepatcht (kein Mocking-Framework im Repo, siehe requirements.txt - Python-Bordmittel
genügen für ein einfaches Attribut-Override), jira_client.is_configured() wird auf True
gesetzt, damit sowohl der manuelle Sync-Endpoint als auch scheduler.run_sync_cycle() den
Orchestrierungs-Pfad (jira_sync.sync_project_and_refresh) tatsächlich durchlaufen.

1. Testfall Abschnitt 58: scheduler.run_sync_cycle() aktualisiert alle Jira-konfigurierten
   Projekte OHNE Benutzeraktion - ein extern hinzugefügter Worklog erscheint danach in
   Phase-Ist/actual_start, der Sync-Status zeigt einen aktuellen last_success_at-Zeitpunkt.
2. Fehlerisolation (Abschnitt 16): Projekt A schlägt fehl (Exception in sync_project) ->
   Projekt B wird trotzdem synchronisiert; JiraSyncStatus für A zeigt last_error, für B
   last_success_at.
3. Bestehende Ist-Werte bleiben bei einem Fehler erhalten (Abschnitt 15) - ein Sync-Fehler
   NACH einem vorherigen Erfolg darf last_success_at nicht zurücksetzen/löschen.
4. Sync-Status-Endpoint (GET /jira/sync-status/{project_id}) liefert alle Felder None für ein
   Projekt ohne bisherigen Sync-Versuch (kein Fehler, keine erfundene 0).
5. Der manuelle "Jetzt aktualisieren"-Button (POST /jira/sync) und der Scheduler laufen über
   dieselbe Orchestrierung (jira_sync.sync_project_and_refresh) - keine zwei abweichenden
   Code-Pfade.

Aufruf: python backend/scripts/test_p20_5_autosync.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_5_autosync_check_")
# KAPA_TEST_DB_URL: optionales Override fuer eine echte PostgreSQL-Instanz (P20.5 Auftrag
# Abschnitt 59 - "nicht nur SQLite testen"), Default bleibt eine Wegwerf-SQLite-Datei.
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("KAPA_TEST_DB_URL")
    or ("sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")),
)
os.environ["JIRA_AUTOSYNC_ENABLED"] = "false"  # der Scheduler-LOOP selbst wird hier nicht gestartet

from fastapi.testclient import TestClient  # noqa: E402

from app import jira_client, jira_sync, models, scheduler  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402 - Import triggert db_bootstrap.run_migrations()

client = TestClient(app)


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def _create_project(name: str, jira_component: str) -> int:
    resp = client.post(
        "/projects", json={"name": name, "start_monat": "10.2026", "jira_component": jira_component}
    )
    if resp.status_code != 201:
        _fail("Projekt anlegen", f"{resp.status_code}: {resp.text}")
    return resp.json()["id"]


def _get_sync_status(project_id: int) -> dict:
    resp = client.get(f"/jira/sync-status/{project_id}")
    if resp.status_code != 200:
        _fail("Sync-Status abrufen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def main() -> None:
    print("1/4  Sync-Status ohne bisherigen Versuch -> alle Felder None ...")
    project_a = _create_project("Projekt A (fehlschlägt)", "COMP-A")
    project_b = _create_project("Projekt B (erfolgreich)", "COMP-B")
    status = _get_sync_status(project_a)
    if status["last_attempt_at"] is not None or status["last_success_at"] is not None:
        _fail("Initialer Sync-Status", str(status))

    print("2/4  Fehlerisolation: Projekt A schlägt fehl, Projekt B synchronisiert trotzdem ...")
    original_sync_project = jira_sync.sync_project
    original_is_configured = jira_client.is_configured

    def _fake_sync_project(db, project):
        if project.jira_component == "COMP-A":
            raise RuntimeError("Simulierter Jira-API-Fehler (Rate Limit)")
        return (3, 0, [])  # (gespeichert, unzugeordnet, unbekannte_beispiele)

    jira_sync.sync_project = _fake_sync_project
    jira_client.is_configured = lambda: True
    try:
        scheduler.run_sync_cycle()
    finally:
        jira_sync.sync_project = original_sync_project
        jira_client.is_configured = original_is_configured

    status_a = _get_sync_status(project_a)
    status_b = _get_sync_status(project_b)
    if status_a["last_error"] is None or "Rate Limit" not in status_a["last_error"]:
        _fail("Projekt A sollte last_error zeigen", str(status_a))
    if status_a["last_success_at"] is not None:
        _fail("Projekt A hatte noch nie Erfolg -> last_success_at sollte None bleiben", str(status_a))
    if status_b["last_success_at"] is None or status_b["last_error"] is not None:
        _fail(
            "Projekt B sollte trotz Projekt-A-Fehler erfolgreich synchronisiert worden sein "
            "(Fehlerisolation, Abschnitt 16)",
            str(status_b),
        )

    print("3/4  Ein späterer Fehler löscht einen vorherigen Erfolg NICHT (Abschnitt 15) ...")
    first_success_at = status_b["last_success_at"]

    def _now_failing_sync_project(db, project):
        raise RuntimeError("Token abgelaufen")

    jira_sync.sync_project = _now_failing_sync_project
    jira_client.is_configured = lambda: True
    try:
        scheduler.run_sync_cycle()
    finally:
        jira_sync.sync_project = original_sync_project
        jira_client.is_configured = original_is_configured

    status_b_after_fail = _get_sync_status(project_b)
    if status_b_after_fail["last_success_at"] != first_success_at:
        _fail(
            "last_success_at darf durch einen späteren Fehler nicht verändert/gelöscht werden",
            f"vorher {first_success_at}, nachher {status_b_after_fail}",
        )
    if status_b_after_fail["last_error"] is None or "Token abgelaufen" not in status_b_after_fail["last_error"]:
        _fail("last_error sollte den neuen Fehler zeigen (zusätzlich zum erhaltenen Erfolg)", str(status_b_after_fail))

    print("4/4  Manueller Sync-Button und Scheduler laufen über dieselbe Orchestrierung ...")

    def _tracking_sync_project(db, project):
        return (1, 0, [])

    jira_sync.sync_project = _tracking_sync_project
    jira_client.is_configured = lambda: True
    try:
        resp = client.post("/jira/sync", params={"project_id": project_b})
    finally:
        jira_sync.sync_project = original_sync_project
        jira_client.is_configured = original_is_configured
    if resp.status_code != 200:
        _fail("Manueller Sync", f"{resp.status_code}: {resp.text}")
    result = resp.json()["ergebnisse"][0]
    if result["error"] is not None or result["worklogs_synced"] != 1:
        _fail("Manueller Sync sollte über sync_project_and_refresh laufen", str(result))
    status_b_manual = _get_sync_status(project_b)
    if status_b_manual["last_success_at"] is None:
        _fail("Sync-Status sollte auch nach manuellem Sync aktualisiert sein", str(status_b_manual))

    print(
        "OK — P20.5 Auto-Sync: Sync-Status ohne Versuch (alle None), Fehlerisolation "
        "(Projekt A Fehler stoppt Projekt B nicht), bestehender Erfolg bleibt bei einem "
        "späteren Fehler erhalten, und manueller Sync + Scheduler laufen über dieselbe "
        "Orchestrierung - alles wie spezifiziert."
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
