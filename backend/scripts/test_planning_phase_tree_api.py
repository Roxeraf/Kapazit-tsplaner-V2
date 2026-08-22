"""P18/B-3: Integrationstests für die PlanPhase-Tree-API (CONCEPT.md Abschnitt 6b, BD-10/
BD-11 CLOSED). Kein pytest im Repo (siehe check_migrations.py/
test_migrate_to_planphase_hierarchy.py als etabliertes Muster für eigenständige
Prüfskripte) - baut eine Wegwerf-SQLite-DB, startet die echte FastAPI-App per TestClient und
prüft gegen die tatsächlichen Endpunkte:

1. Hierarchie anlegen (3 Ebenen), Tiefe-4 wird abgelehnt (BD-10).
2. Zyklus (Phase als eigener Vorfahre) wird abgelehnt.
3. Projektfremder parent_phase_id wird abgelehnt.
4. Leaf->Parent-Übergang historisiert plan_fte und setzt es auf NULL (Abschnitt 6b.1a).
5. Standard-DELETE einer Parent-Phase mit Kindern -> 409 (BD-11).
6. reparent-children verschiebt Kinder korrekt, Phase wird danach wieder leaf und löschbar.
7. subtree-impact zeigt korrekte Zählungen; delete-subtree verlangt exakte Bestätigung (422
   bei falschem Wert) und löscht bei korrekter Bestätigung rekursiv, ohne Collaboration-
   Inhalte (Comment/Milestone) zu löschen - nur die Verknüpfung wird entfernt.

Aufruf: python backend/scripts/test_planning_phase_tree_api.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_phase_tree_api_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402 - Import triggert db_bootstrap.run_migrations()
from app.database import engine  # noqa: E402

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
    print("1/7  Hierarchie über 3 Ebenen anlegen ...")
    project_id = _create_project("Testprojekt B-3")

    phase_a = _create_phase(project_id, phase_type="Wareneingang", plan_fte=0.4)
    if phase_a["has_children"] is not False or phase_a["plan_fte"] != 0.4:
        _fail("Ebene 1", f"unerwarteter Ausgangszustand: {phase_a}")

    phase_b = _create_phase(project_id, phase_type="Schnittstellen", parent_phase_id=phase_a["id"])
    phase_c = _create_phase(project_id, phase_type="WE-Anmeldung", parent_phase_id=phase_b["id"])

    print("2/7  Ebene 4 wird abgelehnt (BD-10, max. 3 Ebenen) ...")
    resp = client.post(
        f"/projects/{project_id}/plan-phases",
        json={"phase_type": "Zu tief", "parent_phase_id": phase_c["id"], "status": "geplant"},
    )
    if resp.status_code != 422:
        _fail("Tiefe-4", f"erwartet 422, bekommen {resp.status_code}: {resp.text}")

    print("3/7  Zyklus wird abgelehnt (Phase als eigener Vorfahre) ...")
    resp = client.put(f"/projects/plan-phases/{phase_a['id']}", json={"parent_phase_id": phase_c["id"]})
    if resp.status_code != 422:
        _fail("Zyklus", f"erwartet 422, bekommen {resp.status_code}: {resp.text}")

    print("4/7  Projektfremder parent_phase_id wird abgelehnt ...")
    other_project_id = _create_project("Anderes Projekt")
    other_phase = _create_phase(other_project_id, phase_type="Fremdphase")
    resp = client.post(
        f"/projects/{project_id}/plan-phases",
        json={"phase_type": "Grenzverletzung", "parent_phase_id": other_phase["id"], "status": "geplant"},
    )
    if resp.status_code != 422:
        _fail("Projektfremder Parent", f"erwartet 422, bekommen {resp.status_code}: {resp.text}")

    print("5/7  Leaf->Parent-Übergang: plan_fte wird historisiert und auf NULL gesetzt ...")
    phase_a_detail = client.get(f"/projects/plan-phases/{phase_a['id']}").json()
    if phase_a_detail["plan_fte"] is not None:
        _fail("Leaf->Parent", f"plan_fte hätte NULL sein müssen, ist {phase_a_detail['plan_fte']}")
    if not phase_a_detail["has_children"] or len(phase_a_detail["children"]) != 1:
        _fail("Leaf->Parent", f"has_children/children unerwartet: {phase_a_detail}")
    history = client.get(f"/projects/{project_id}/history").json()
    historized = [
        h for h in history if h.get("plan_phase_id") == phase_a["id"] and h.get("feld") == "plan_fte"
    ]
    if not historized or historized[0]["alter_wert"] != "0.4":
        _fail("Leaf->Parent", f"PlanHistory-Eintrag fehlt oder falsch: {historized}")

    print("6/7  Standard-DELETE einer Parent-Phase mit Kindern -> 409 (BD-11) ...")
    resp = client.delete(f"/projects/plan-phases/{phase_a['id']}")
    if resp.status_code != 409:
        _fail("BD-11 Block", f"erwartet 409, bekommen {resp.status_code}: {resp.text}")
    if resp.json()["detail"]["child_count"] != 1:
        _fail("BD-11 Block", f"child_count falsch: {resp.json()}")

    print("7/7  reparent-children: Kind auf Top-Level verschieben, danach leaf und löschbar ...")
    resp = client.post(
        f"/projects/plan-phases/{phase_a['id']}/reparent-children", json={"new_parent_phase_id": None}
    )
    if resp.status_code != 200 or resp.json()["moved_count"] != 1:
        _fail("reparent-children", f"{resp.status_code}: {resp.text}")
    phase_b_after = client.get(f"/projects/plan-phases/{phase_b['id']}").json()
    if phase_b_after["parent_phase_id"] is not None:
        _fail("reparent-children", f"phase_b sollte Top-Level sein: {phase_b_after}")

    resp = client.delete(f"/projects/plan-phases/{phase_a['id']}")
    if resp.status_code != 204:
        _fail("Delete nach reparent", f"erwartet 204, bekommen {resp.status_code}: {resp.text}")
    phase_a_after = client.get(f"/projects/plan-phases/{phase_a['id']}")
    if phase_a_after.status_code != 404:
        _fail("Delete nach reparent", "phase_a existiert noch nach DELETE")

    print("    subtree-impact/delete-subtree: Assignments/Collaboration korrekt behandelt ...")
    role_resp = client.post("/resource-roles", json={"name": "Consultant B3-Test"})
    role_id = role_resp.json()["id"]
    parent_p = _create_phase(project_id, phase_type="Parent P")
    leaf_l = _create_phase(project_id, phase_type="Leaf L", parent_phase_id=parent_p["id"], plan_fte=0.3)

    demand_resp = client.post(
        f"/projects/{project_id}/resource-demands",
        json={
            "plan_phase_id": leaf_l["id"],
            "resource_role_id": role_id,
            "period": "Okt 26",
            "fte": 0.3,
            "commitment_level": "TENTATIVE",
        },
    )
    if demand_resp.status_code != 201:
        _fail("Setup Assignment", f"{demand_resp.status_code}: {demand_resp.text}")
    demand_id = demand_resp.json()["id"]

    person_resp = client.post("/people", json={"display_name": "Testperson B3"})
    person_id = person_resp.json()["id"]
    assignment_resp = client.post(
        f"/resource-demands/{demand_id}/assignments", json={"person_id": person_id, "fte": 0.3}
    )
    if assignment_resp.status_code != 201:
        _fail("Setup Assignment", f"{assignment_resp.status_code}: {assignment_resp.text}")

    comment_resp = client.post(
        f"/projects/{project_id}/comments", json={"text": "Kommentar an Leaf L", "plan_phase_id": leaf_l["id"]}
    )
    comment_id = comment_resp.json()["id"]

    impact = client.get(f"/projects/plan-phases/{parent_p['id']}/subtree-impact").json()
    if impact["descendant_phase_count"] != 1:
        _fail("subtree-impact", f"descendant_phase_count falsch: {impact}")
    if impact["resource_demands_affected"] != 1 or impact["resource_assignments_affected"] != 1:
        _fail("subtree-impact", f"Assignment-Zählung falsch: {impact}")
    if impact["comments_affected"] != 1:
        _fail("subtree-impact", f"Comment-Zählung falsch: {impact}")

    resp = client.post(
        f"/projects/plan-phases/{parent_p['id']}/delete-subtree",
        json={"confirm_phase_type": "FALSCH", "confirm_descendant_count": 1},
    )
    if resp.status_code != 422:
        _fail("delete-subtree Bestätigung", f"erwartet 422 bei falschem phase_type, bekommen {resp.status_code}")

    resp = client.post(
        f"/projects/plan-phases/{parent_p['id']}/delete-subtree",
        json={"confirm_phase_type": "Parent P", "confirm_descendant_count": 1},
    )
    if resp.status_code != 204:
        _fail("delete-subtree", f"erwartet 204, bekommen {resp.status_code}: {resp.text}")

    if client.get(f"/projects/plan-phases/{leaf_l['id']}").status_code != 404:
        _fail("delete-subtree", "leaf_l existiert noch nach delete-subtree")
    comment_after = client.get(f"/projects/{project_id}/comments").json()
    matching_comment = next((c for c in comment_after if c["id"] == comment_id), None)
    if matching_comment is None:
        _fail("delete-subtree", "Comment wurde fälschlich mitgelöscht (sollte nur entkoppelt werden)")
    if matching_comment["plan_phase_id"] is not None:
        _fail("delete-subtree", f"Comment.plan_phase_id hätte NULL sein müssen: {matching_comment}")

    print("OK — Phase-Tree-API: Tiefe/Zyklus/Projekt-Grenze validiert, Leaf->Parent-"
          "Historisierung korrekt, BD-11-Block/reparent-children/delete-subtree funktionieren "
          "wie spezifiziert, Collaboration-Inhalte bleiben bei delete-subtree erhalten.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
