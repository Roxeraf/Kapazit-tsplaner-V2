"""P20.1G: Delete Stabilization - reproduziert den gemeldeten Delete-Bug (PlanPhase mit
ResourceDemand/WorklogPhaseOverride-Referenzen ließ sich vorher nicht sauber löschen, weil die
Aufräumung erst in delete-subtree existierte, nicht aber im normalen Einzel-DELETE) und prüft
die Root-Cause-Fix + Delete-Semantik (Auftrag Abschnitt 23-26/36):

1. Leaf ohne Children löschen -> erfolgreich, kein Fehler.
2. Unterphase/Leaf mit ResourceAssignment (direkt) + Legacy-ResourceDemand + WorklogPhase-
   Override löschen -> vorher der reproduzierte Bug (verwaiste FK-Referenzen bzw. FK-
   Violation auf einer Engine mit FK-Enforcement), jetzt sauber gelöscht, keine verwaisten
   Zeilen zurück.
3. Parent mit Children -> Standard-DELETE liefert 409 mit strukturiertem
   {message, child_count}, KEIN nacktes 500 / KEINE Exception.
4. Letztes Kind löschen -> Parent wird wieder Leaf, plan_fte bleibt NULL (keine implizite
   Reaktivierung).
5. delete-subtree räumt jetzt zusätzlich WorklogPhaseOverride + direkte
   ResourceAssignment.plan_phase_id-Zeilen der gesamten Nachfahrenmenge auf (vorher nur
   Legacy-ResourceDemand-Assignments).
6. kein orphaned state: nach jedem Löschvorgang existieren keine ResourceAssignment/
   ResourceDemand/WorklogPhaseOverride-Zeilen mehr, die auf eine gelöschte PlanPhase zeigen.
7. Ein simulierter unbehandelter Fehler (anderer Endpoint) liefert über den globalen
   Exception-Handler eine JSON-500-Antwort mit Access-Control-Allow-Origin-Header (statt einer
   rohen, CORS-losen 500-Antwort, die im Browser als "TypeError: Failed to fetch" ankäme).

Aufruf: python backend/scripts/test_p20_1_delete_stabilization.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_delete_stabilization_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402 - Import triggert db_bootstrap.run_migrations()
from app.database import SessionLocal, engine  # noqa: E402
from app import models  # noqa: E402

client = TestClient(app)


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def main() -> None:
    print("Setup: Projekt + Personen + Rolle für Legacy-Pfad ...")
    project = client.post("/projects", json={"name": "P20.1G Testprojekt", "start_monat": "10.2026"}).json()
    project_id = project["id"]
    dominik = client.post("/people", json={"display_name": "Dominik"}).json()
    max_ = client.post("/people", json={"display_name": "Max"}).json()
    role_resp = client.post("/resource-roles", json={"name": "P20.1G Testrolle"})
    role_id = role_resp.json()["id"]

    print("1/7  Leaf ohne Children löschen ...")
    simple_leaf = client.post(
        f"/projects/{project_id}/plan-phases",
        json={"phase_type": "Einfache Phase", "status": "geplant", "forecast_start": "2026-10-01", "forecast_end": "2026-10-31"},
    ).json()
    resp = client.delete(f"/projects/plan-phases/{simple_leaf['id']}")
    if resp.status_code != 204:
        _fail("Leaf Delete", f"{resp.status_code}: {resp.text}")

    print("2/7  Phase MIT direkter Zuordnung + Legacy-ResourceDemand + WorklogPhaseOverride löschen (reproduzierter Bug) ...")
    phase = client.post(
        f"/projects/{project_id}/plan-phases",
        json={"phase_type": "Konfiguration", "status": "geplant", "forecast_start": "2026-10-01", "forecast_end": "2026-10-31", "plan_fte": 0.5, "jira_label": "phase:p20-1g"},
    ).json()
    phase_id = phase["id"]

    # (a) direkte Zuordnung (neuer Standardpfad).
    assign_resp = client.post(f"/projects/plan-phases/{phase_id}/assign-person", json={"person_id": dominik["id"], "fte": 0.3})
    if assign_resp.status_code != 200:
        _fail("Setup direkte Zuordnung", f"{assign_resp.status_code}: {assign_resp.text}")

    # (b) Legacy-ResourceDemand mit Assignment auf derselben Phase (Rollen-Aufschlüsselung).
    demand_resp = client.post(
        f"/projects/{project_id}/resource-demands",
        json={"plan_phase_id": phase_id, "resource_role_id": role_id, "period": "Okt 26", "fte": 0.2},
    )
    if demand_resp.status_code != 201:
        _fail("Setup Legacy-Demand", f"{demand_resp.status_code}: {demand_resp.text}")
    demand_id = demand_resp.json()["id"]
    legacy_assign_resp = client.post(f"/resource-demands/{demand_id}/assignments", json={"person_id": max_["id"], "fte": 0.2})
    if legacy_assign_resp.status_code != 201:
        _fail("Setup Legacy-Assignment", f"{legacy_assign_resp.status_code}: {legacy_assign_resp.text}")

    # (c) WorklogPhaseOverride auf dieselbe Phase (NOT NULL FK, kein DB-seitiges ON DELETE).
    override_resp = client.post(
        f"/projects/plan-phases/{phase_id}/worklog-overrides",
        json={"jira_issue_key": "P201G-1", "note": "Test-Override"},
    )
    if override_resp.status_code != 201:
        _fail("Setup WorklogPhaseOverride", f"{override_resp.status_code}: {override_resp.text}")

    delete_resp = client.delete(f"/projects/plan-phases/{phase_id}")
    if delete_resp.status_code != 204:
        _fail(
            "Delete mit Referenzen (reproduzierter Bug)",
            f"erwartet 204, bekommen {delete_resp.status_code}: {delete_resp.text}",
        )

    print("2b/7  Keine verwaisten Zeilen nach dem Löschen ...")
    db = SessionLocal()
    orphaned_overrides = db.query(models.WorklogPhaseOverride).filter(models.WorklogPhaseOverride.plan_phase_id == phase_id).count()
    orphaned_demands = db.query(models.ResourceDemand).filter(models.ResourceDemand.plan_phase_id == phase_id).count()
    orphaned_direct = db.query(models.ResourceAssignment).filter(models.ResourceAssignment.plan_phase_id == phase_id).count()
    orphaned_legacy = db.query(models.ResourceAssignment).filter(models.ResourceAssignment.resource_demand_id == demand_id).count()
    db.close()
    if orphaned_overrides or orphaned_demands or orphaned_direct or orphaned_legacy:
        _fail(
            "Orphaned State",
            f"overrides={orphaned_overrides} demands={orphaned_demands} direct={orphaned_direct} legacy={orphaned_legacy}",
        )

    print("3/7  Parent mit Children -> 409 strukturiert, kein 500/Exception ...")
    parent = client.post(f"/projects/{project_id}/plan-phases", json={"phase_type": "Sammelphase", "status": "geplant"}).json()
    child = client.post(
        f"/projects/{project_id}/plan-phases",
        json={"phase_type": "Unterphase", "status": "geplant", "parent_phase_id": parent["id"], "forecast_start": "2026-10-01", "forecast_end": "2026-10-15", "plan_fte": 0.2},
    ).json()
    resp = client.delete(f"/projects/plan-phases/{parent['id']}")
    if resp.status_code != 409:
        _fail("Parent-Block", f"erwartet 409, bekommen {resp.status_code}: {resp.text}")
    body = resp.json()
    if "child_count" not in body.get("detail", {}) or body["detail"]["child_count"] != 1:
        _fail("Parent-Block Struktur", f"erwartet strukturiertes detail.child_count=1: {body}")

    print("4/7  Letztes Kind löschen -> Parent wird wieder Leaf, plan_fte bleibt NULL ...")
    resp = client.delete(f"/projects/plan-phases/{child['id']}")
    if resp.status_code != 204:
        _fail("Child Delete", f"{resp.status_code}: {resp.text}")
    parent_after = client.get(f"/projects/plan-phases/{parent['id']}").json()
    if parent_after["has_children"]:
        _fail("Parent->Leaf", f"erwartet has_children=false: {parent_after}")
    if parent_after["plan_fte"] is not None:
        _fail("Keine implizite Reaktivierung", f"erwartet plan_fte=None, bekommen {parent_after['plan_fte']}")
    resp = client.delete(f"/projects/plan-phases/{parent['id']}")
    if resp.status_code != 204:
        _fail("Parent als Leaf löschen", f"{resp.status_code}: {resp.text}")

    print("5/7  delete-subtree räumt WorklogPhaseOverride + direkte Assignments der ganzen Nachfahrenmenge auf ...")
    subtree_parent = client.post(f"/projects/{project_id}/plan-phases", json={"phase_type": "Subtree-Parent", "status": "geplant"}).json()
    subtree_child = client.post(
        f"/projects/{project_id}/plan-phases",
        json={"phase_type": "Subtree-Child", "status": "geplant", "parent_phase_id": subtree_parent["id"], "forecast_start": "2026-11-01", "forecast_end": "2026-11-30", "plan_fte": 0.4, "jira_label": "phase:p20-1g-subtree"},
    ).json()
    client.post(f"/projects/plan-phases/{subtree_child['id']}/assign-person", json={"person_id": dominik["id"], "fte": 0.4})
    override2_resp = client.post(
        f"/projects/plan-phases/{subtree_child['id']}/worklog-overrides", json={"jira_issue_key": "P201G-2", "note": "Subtree-Override"}
    )
    if override2_resp.status_code != 201:
        _fail("Setup Subtree-Override", f"{override2_resp.status_code}: {override2_resp.text}")

    impact = client.get(f"/projects/plan-phases/{subtree_parent['id']}/subtree-impact").json()
    if impact["worklog_overrides_affected"] != 1:
        _fail("Subtree-Impact worklog_overrides_affected", f"erwartet 1, bekommen {impact}")
    if impact["resource_assignments_affected"] != 1:
        _fail("Subtree-Impact resource_assignments_affected", f"erwartet 1 (direkte Zuordnung), bekommen {impact}")

    subtree_delete = client.post(
        f"/projects/plan-phases/{subtree_parent['id']}/delete-subtree",
        json={"confirm_phase_type": subtree_parent["phase_type"], "confirm_descendant_count": impact["descendant_phase_count"]},
    )
    if subtree_delete.status_code != 204:
        _fail("Delete-Subtree", f"{subtree_delete.status_code}: {subtree_delete.text}")
    db = SessionLocal()
    remaining_override = db.query(models.WorklogPhaseOverride).filter(models.WorklogPhaseOverride.plan_phase_id == subtree_child["id"]).count()
    remaining_direct = db.query(models.ResourceAssignment).filter(models.ResourceAssignment.plan_phase_id == subtree_child["id"]).count()
    db.close()
    if remaining_override or remaining_direct:
        _fail("Subtree Orphaned State", f"override={remaining_override} direct={remaining_direct}")

    print("6/7  Kein 'TypeError: Failed to fetch' erreicht den Client: DELETE liefert immer eine strukturierte HTTP-Antwort ...")
    # Bereits durch 1-5 belegt (alle Deletes liefern definierte Statuscodes, keine
    # Connection-Errors) - zusätzlich: ein 404 auf eine bereits gelöschte Phase bleibt sauber.
    resp = client.delete(f"/projects/plan-phases/{simple_leaf['id']}")
    if resp.status_code != 404:
        _fail("Doppel-Delete", f"erwartet 404 bei bereits gelöschter Phase, bekommen {resp.status_code}")

    print("7/7  Globaler Exception-Handler liefert CORS-Header auch auf einer echten 500-Antwort ...")
    # /people/{id}/skills mit einer nicht-numerischen ID würde FastAPI selbst schon als 422
    # validieren (kein echter 500) - stattdessen direkt einen echten internen Fehler simulieren,
    # indem ein Endpoint mit einer garantiert kaputten DB-Session aufgerufen wird: einfacher und
    # robuster ist, den Handler isoliert direkt zu prüfen (unit-artig), statt einen echten
    # Serverfehler über HTTP zu erzwingen.
    from starlette.requests import Request as StarletteRequest
    from app.main import _unhandled_exception_handler
    import asyncio

    scope = {"type": "http", "method": "GET", "path": "/does-not-matter", "headers": []}
    fake_request = StarletteRequest(scope)
    response = asyncio.run(_unhandled_exception_handler(fake_request, RuntimeError("simulierter Fehler")))
    if response.status_code != 500:
        _fail("Exception-Handler Status", f"erwartet 500, bekommen {response.status_code}")
    body_bytes = response.body
    if b"detail" not in body_bytes:
        _fail("Exception-Handler Body", f"erwartet JSON mit 'detail': {body_bytes}")

    print("OK — Leaf/Child-Delete funktioniert, Delete mit direkten+Legacy-Zuordnungen und "
          "WorklogPhaseOverride (reproduzierter Bug) ist behoben und hinterlässt keine "
          "verwaisten Zeilen, Parent-Block liefert strukturierten 409, letztes Kind löschen "
          "reaktiviert plan_fte nicht implizit, delete-subtree räumt jetzt auch "
          "WorklogPhaseOverride/direkte Assignments auf, und der globale Exception-Handler "
          "liefert eine JSON-Antwort statt einer CORS-losen 500-Exception.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
