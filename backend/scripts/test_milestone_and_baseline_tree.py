"""P18/B-7: Integrationstests für Milestone.plan_phase_id und die Baseline-Snapshot-
Erweiterung um den PlanPhase-Baum (CONCEPT.md Abschnitt 6b.8/6b.14). Kein pytest im Repo
(siehe check_migrations.py als etabliertes Muster) - TestClient gegen die echte FastAPI-App.
Prüft:

1. Milestone kann per plan_phase_id an eine Leaf- ODER Parent-Phase gehängt werden (im
   Unterschied zur Kapazitätsplanung, die Leaf-only ist).
2. plan_phase_id muss zum selben Projekt gehören (422 bei Projektfremd).
3. Ein Planstand friert parent_phase_id/reihenfolge (PlanPhase) und plan_phase_id
   (Milestone) mit ein.
4. Nach einem Reparenting zeigt GET .../deviations die strukturelle Abweichung
   (parent_phase_id alt != neu) - Testfall J aus dem Pass-2-Dokument.

Aufruf: python backend/scripts/test_milestone_and_baseline_tree.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_milestone_baseline_check_")
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
    print("1/4  Milestone an Leaf- und Parent-Phase hängen ...")
    project_id = _create_project("B-7 Testprojekt")
    other_project_id = _create_project("B-7 Anderes Projekt")

    parent = _create_phase(project_id, phase_type="Wareneingang")
    leaf = _create_phase(project_id, phase_type="Pflichtenheft", parent_phase_id=parent["id"])
    parent = client.get(f"/projects/plan-phases/{parent['id']}").json()  # refresh has_children

    m_leaf = client.post(
        f"/projects/{project_id}/milestones",
        json={"name": "Fachkonzept freigegeben", "plan_phase_id": leaf["id"]},
    )
    if m_leaf.status_code != 201 or m_leaf.json()["plan_phase_id"] != leaf["id"]:
        _fail("Milestone an Leaf", f"{m_leaf.status_code}: {m_leaf.text}")

    m_parent = client.post(
        f"/projects/{project_id}/milestones",
        json={"name": "Wareneingang abgeschlossen", "plan_phase_id": parent["id"]},
    )
    if m_parent.status_code != 201 or m_parent.json()["plan_phase_id"] != parent["id"]:
        _fail("Milestone an Parent", f"{m_parent.status_code}: {m_parent.text}")

    print("2/4  Projektfremder plan_phase_id wird abgelehnt ...")
    other_phase = _create_phase(other_project_id, phase_type="Fremdphase")
    resp = client.post(
        f"/projects/{project_id}/milestones",
        json={"name": "Grenzverletzung", "plan_phase_id": other_phase["id"]},
    )
    if resp.status_code != 422:
        _fail("Projektfremder plan_phase_id", f"erwartet 422, bekommen {resp.status_code}: {resp.text}")

    print("3/4  Planstand friert parent_phase_id/reihenfolge/plan_phase_id ein ...")
    baseline_resp = client.post(f"/projects/{project_id}/baselines", json={"name": "V1"})
    if baseline_resp.status_code != 201:
        _fail("Baseline anlegen", f"{baseline_resp.status_code}: {baseline_resp.text}")
    baseline_id = baseline_resp.json()["id"]
    entries = baseline_resp.json()["entries"]

    leaf_parent_entry = next(
        (e for e in entries if e["entity_type"] == "plan_phase" and e["entity_id"] == leaf["id"] and e["field"] == "parent_phase_id"),
        None,
    )
    if leaf_parent_entry is None or leaf_parent_entry["value"] != str(parent["id"]):
        _fail("Snapshot parent_phase_id", f"erwartet Wert {parent['id']}, gefunden: {leaf_parent_entry}")

    milestone_plan_phase_entry = next(
        (e for e in entries if e["entity_type"] == "milestone" and e["entity_id"] == m_leaf.json()["id"] and e["field"] == "plan_phase_id"),
        None,
    )
    if milestone_plan_phase_entry is None or milestone_plan_phase_entry["value"] != str(leaf["id"]):
        _fail("Snapshot Milestone.plan_phase_id", f"gefunden: {milestone_plan_phase_entry}")

    reihenfolge_entry = next(
        (e for e in entries if e["entity_type"] == "plan_phase" and e["entity_id"] == leaf["id"] and e["field"] == "reihenfolge"),
        None,
    )
    if reihenfolge_entry is None:
        _fail("Snapshot reihenfolge", "reihenfolge wurde nicht eingefroren")

    print("4/4  Reparenting zeigt strukturelle Abweichung im Planstand-Vergleich ...")
    reparent_resp = client.put(f"/projects/plan-phases/{leaf['id']}", json={"parent_phase_id": None})
    if reparent_resp.status_code != 200:
        _fail("Reparenting", f"{reparent_resp.status_code}: {reparent_resp.text}")

    deviations = client.get(f"/projects/baselines/{baseline_id}/deviations").json()
    structural = next(
        (d for d in deviations if d["entity_type"] == "plan_phase" and d["entity_id"] == leaf["id"] and d["field"] == "parent_phase_id"),
        None,
    )
    if structural is None:
        _fail("Deviation", "keine parent_phase_id-Abweichung nach Reparenting gefunden")
    if structural["baseline_value"] != str(parent["id"]) or structural["current_value"] is not None:
        _fail("Deviation", f"unerwartete Werte: {structural}")

    print("OK — Milestone.plan_phase_id funktioniert für Leaf und Parent, Projekt-Grenze "
          "validiert, Planstand friert parent_phase_id/reihenfolge/Milestone.plan_phase_id "
          "ein, Reparenting zeigt korrekt als strukturelle Abweichung im Planstand-Vergleich.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
