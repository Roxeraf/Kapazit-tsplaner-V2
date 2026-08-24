"""P20.1: Integrationstests für die Jira/Tempo-Mapping-Domain (PlanPhase.jira_label,
JiraIssueCache, WorklogPhaseOverride), siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md
Abschnitt 24/28/30. Kein pytest im Repo (siehe test_planning_phase_tree_api.py als etabliertes
Muster) - baut eine Wegwerf-SQLite-DB, startet die echte FastAPI-App per TestClient und prüft
gegen die tatsächlichen Endpunkte:

1. jira_label kann bei Create/Update auf einer Leaf-Phase gesetzt werden.
2. Konfliktprüfung (BD-1G): identisches Label auf zwei Leaf-Phasen desselben Projekts wird mit
   409 abgelehnt, sowohl beim Anlegen als auch beim Aktualisieren.
3. Leaf->Parent-Übergang setzt jira_label (wie plan_fte) serverseitig auf NULL und
   historisiert den alten Wert in PlanHistory (BD-1E) - danach ist der Wert für andere Phasen
   wieder frei.
4. WorklogPhaseOverride-CRUD: Anlegen, Upsert (Verschieben auf eine andere Phase über
   denselben jira_issue_key), Löschen, 404 bei nicht existierendem Override.
5. jira_sync._upsert_issue_cache befüllt JiraIssueCache korrekt (Labels kommagetrennt) und ist
   idempotent (zweiter Lauf aktualisiert dieselbe Zeile, keine Duplikate) - ohne echten
   Jira-API-Call, da die Funktion die bereits aufgelösten Issues entgegennimmt.

Aufruf: python backend/scripts/test_p20_jira_phase_mapping.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_jira_mapping_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from fastapi.testclient import TestClient  # noqa: E402

from app import jira_sync, models  # noqa: E402 - nach DATABASE_URL-Setzung importieren
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
    return resp


def main() -> None:
    print("1/5  jira_label bei Create/Update auf einer Leaf-Phase setzen ...")
    project_id = _create_project("Testprojekt P20.1")

    resp = _create_phase(project_id, phase_type="Konfiguration", jira_label="phase:configuration")
    if resp.status_code != 201:
        _fail("Phase mit jira_label anlegen", f"{resp.status_code}: {resp.text}")
    phase_a = resp.json()
    if phase_a["jira_label"] != "phase:configuration":
        _fail("jira_label beim Anlegen", f"unerwarteter Wert: {phase_a}")

    resp = _create_phase(project_id, phase_type="Testing")
    if resp.status_code != 201:
        _fail("Phase ohne jira_label anlegen", f"{resp.status_code}: {resp.text}")
    phase_b = resp.json()
    if phase_b["jira_label"] is not None:
        _fail("jira_label Default", f"sollte None sein: {phase_b}")

    resp = client.put(f"/projects/plan-phases/{phase_b['id']}", json={"jira_label": "phase:testing"})
    if resp.status_code != 200 or resp.json()["jira_label"] != "phase:testing":
        _fail("jira_label per Update setzen", f"{resp.status_code}: {resp.text}")

    print("2/5  Konfliktprüfung (BD-1G): identisches Label auf zwei Leaf-Phasen -> 409 ...")
    resp = _create_phase(project_id, phase_type="Konfiguration Alt", jira_label="phase:configuration")
    if resp.status_code != 409:
        _fail("Konflikt beim Anlegen", f"erwartet 409, bekam {resp.status_code}: {resp.text}")
    if "phase:configuration" not in resp.json()["detail"] or "Konfiguration" not in resp.json()["detail"]:
        _fail("Konflikt-Fehlermeldung", f"unerwarteter Detail-Text: {resp.json()}")

    resp = client.put(f"/projects/plan-phases/{phase_b['id']}", json={"jira_label": "phase:configuration"})
    if resp.status_code != 409:
        _fail("Konflikt beim Update", f"erwartet 409, bekam {resp.status_code}: {resp.text}")
    # Phase B behaelt ihr eigenes Label - der abgelehnte Update-Versuch darf nichts geaendert haben.
    resp = client.get(f"/projects/plan-phases/{phase_b['id']}")
    if resp.json()["jira_label"] != "phase:testing":
        _fail("Konflikt-Rollback", f"jira_label haette unveraendert bleiben muessen: {resp.json()}")

    # Ein Update, das denselben (bereits eigenen) Wert erneut setzt, ist kein Konflikt mit sich selbst.
    resp = client.put(f"/projects/plan-phases/{phase_a['id']}", json={"jira_label": "phase:configuration"})
    if resp.status_code != 200:
        _fail("Selbst-Update ohne Aenderung", f"{resp.status_code}: {resp.text}")

    print("3/5  Leaf->Parent-Übergang setzt jira_label auf NULL (wie plan_fte, BD-1E) ...")
    resp = _create_phase(project_id, phase_type="Konfiguration Detail", parent_phase_id=phase_a["id"])
    if resp.status_code != 201:
        _fail("Kind-Phase anlegen", f"{resp.status_code}: {resp.text}")
    child = resp.json()

    resp = client.get(f"/projects/plan-phases/{phase_a['id']}")
    parent_after = resp.json()
    if parent_after["jira_label"] is not None:
        _fail("Parent-Uebergang jira_label", f"haette NULL sein muessen: {parent_after}")
    if parent_after["plan_fte"] is not None:
        _fail("Parent-Uebergang plan_fte", f"haette (unveraendert) NULL sein muessen: {parent_after}")

    db = SessionLocal()
    try:
        history = (
            db.query(models.PlanHistory)
            .filter(models.PlanHistory.plan_phase_id == phase_a["id"], models.PlanHistory.feld == "jira_label")
            .all()
        )
        if len(history) != 1 or history[0].alter_wert != "phase:configuration" or history[0].neuer_wert is not None:
            _fail("PlanHistory jira_label", f"unerwartete Historisierung: {[h.__dict__ for h in history]}")
    finally:
        db.close()

    # Das freigewordene Label ist jetzt wieder vergebbar - auch von einer voellig anderen Phase.
    resp = client.put(f"/projects/plan-phases/{child['id']}", json={"jira_label": "phase:configuration"})
    if resp.status_code != 200:
        _fail("Freigewordenes Label neu vergeben", f"{resp.status_code}: {resp.text}")

    print("4/5  WorklogPhaseOverride-CRUD (Anlegen, Upsert/Verschieben, Löschen, 404) ...")
    resp = client.post(
        f"/projects/plan-phases/{phase_b['id']}/worklog-overrides",
        json={"jira_issue_key": "WMX-1", "note": "manuell zugeordnet", "previous_status": "unmapped"},
    )
    if resp.status_code != 201:
        _fail("Override anlegen", f"{resp.status_code}: {resp.text}")
    override = resp.json()
    if override["plan_phase_id"] != phase_b["id"] or override["previous_status"] != "unmapped":
        _fail("Override-Inhalt", f"unerwartet: {override}")

    resp = client.get(f"/projects/plan-phases/{phase_b['id']}/worklog-overrides")
    if resp.status_code != 200 or len(resp.json()) != 1:
        _fail("Override-Liste (Phase B)", f"{resp.status_code}: {resp.text}")

    # Upsert: derselbe jira_issue_key, andere Ziel-Phase -> verschiebt den Override statt eines Duplikats.
    resp = client.post(
        f"/projects/plan-phases/{child['id']}/worklog-overrides",
        json={"jira_issue_key": "WMX-1"},
    )
    if resp.status_code != 201:
        _fail("Override-Upsert (verschieben)", f"{resp.status_code}: {resp.text}")
    if resp.json()["id"] != override["id"]:
        _fail("Override-Upsert Identitaet", f"erwartet dieselbe Zeile (id={override['id']}): {resp.json()}")

    resp = client.get(f"/projects/plan-phases/{phase_b['id']}/worklog-overrides")
    if resp.status_code != 200 or len(resp.json()) != 0:
        _fail("Override-Liste nach Verschieben (Phase B)", f"sollte leer sein: {resp.status_code}: {resp.text}")
    resp = client.get(f"/projects/plan-phases/{child['id']}/worklog-overrides")
    if resp.status_code != 200 or len(resp.json()) != 1:
        _fail("Override-Liste nach Verschieben (Child)", f"{resp.status_code}: {resp.text}")

    resp = client.delete(f"/projects/plan-phases/{child['id']}/worklog-overrides/WMX-1")
    if resp.status_code != 204:
        _fail("Override löschen", f"{resp.status_code}: {resp.text}")
    resp = client.delete(f"/projects/plan-phases/{child['id']}/worklog-overrides/WMX-1")
    if resp.status_code != 404:
        _fail("Override erneut löschen", f"erwartet 404, bekam {resp.status_code}: {resp.text}")

    print("5/5  jira_sync._upsert_issue_cache befüllt JiraIssueCache korrekt und idempotent ...")
    db = SessionLocal()
    try:
        project = db.get(models.Project, project_id)
        jira_sync._upsert_issue_cache(
            db,
            project,
            [
                {"key": "WMX-100", "id": "1", "labels": ["phase:configuration", "kunde-a"], "component": "Core", "summary": "Erstes Ticket"},
                {"key": "WMX-101", "id": "2", "labels": [], "component": None, "summary": None},
            ],
        )
        db.commit()

        cached = db.get(models.JiraIssueCache, "WMX-100")
        if cached is None or cached.labels != "phase:configuration,kunde-a" or cached.component != "Core":
            _fail("JiraIssueCache Inhalt", f"unerwartet: {cached.__dict__ if cached else None}")
        cached_empty = db.get(models.JiraIssueCache, "WMX-101")
        if cached_empty is None or cached_empty.labels is not None:
            _fail("JiraIssueCache leere Labels", f"sollte None sein: {cached_empty.__dict__ if cached_empty else None}")

        first_synced_at = cached.last_synced_at
        jira_sync._upsert_issue_cache(
            db,
            project,
            [{"key": "WMX-100", "id": "1", "labels": ["phase:testing"], "component": "Core", "summary": "Geaendert"}],
        )
        db.commit()
        count = db.query(models.JiraIssueCache).filter(models.JiraIssueCache.jira_issue_key == "WMX-100").count()
        if count != 1:
            _fail("JiraIssueCache Idempotenz", f"erwartet genau 1 Zeile, gefunden {count}")
        updated = db.get(models.JiraIssueCache, "WMX-100")
        if updated.labels != "phase:testing" or updated.summary != "Geaendert":
            _fail("JiraIssueCache Update", f"unerwartet: {updated.__dict__}")
        if updated.last_synced_at < first_synced_at:
            _fail("JiraIssueCache last_synced_at", "haette nicht frueher sein duerfen")
    finally:
        db.close()

    print(
        "OK — P20.1: jira_label (Create/Update/Konflikt/Parent-Uebergang), "
        "WorklogPhaseOverride-CRUD (Anlegen/Upsert/Loeschen/404) und JiraIssueCache-Upsert "
        "(inkl. Idempotenz) funktionieren wie spezifiziert."
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
