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

P18.1 Stabilization (CONCEPT.md Abschnitt 16.16, ehem. Audit-Defekt #1, Abschnitt 16.15)
zusätzlich:

5. Nach Snapshot neu angelegte PlanPhase erscheint als type="added"-Deviation mit
   Phasennamen (kein Roh-Feld-Delta).
6. Nach Snapshot gelöschte PlanPhase erscheint als type="removed"-Deviation, Name aus den
   eingefrorenen Snapshot-Daten rekonstruiert (kein "#<id>"-Fallback), keine zusätzlichen
   Feld-Deltas für dieselbe entfernte Phase.
7. plan_fte-Änderung und Forecast-Datumsänderung bleiben unverändert als type="changed"
   erkennbar (Regression).
8. Unveränderter Baum liefert keine strukturellen Deviations.

Aufruf: python backend/scripts/test_milestone_and_baseline_tree.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import re
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

    # -----------------------------------------------------------------------
    # P18.1 Stabilization: Planstand erkennt strukturelle Tree-Änderungen
    # (CONCEPT.md Abschnitt 16.16, ehem. Audit-Defekt #1, Abschnitt 16.15).
    # -----------------------------------------------------------------------
    print("5/8  Planstand V2 als sauberer Ausgangspunkt ...")
    stable_leaf = _create_phase(project_id, phase_type="Feinkonzept", plan_fte=0.4, forecast_start="2026-11-01", forecast_end="2026-11-30")
    v2_resp = client.post(f"/projects/{project_id}/baselines", json={"name": "V2"})
    if v2_resp.status_code != 201:
        _fail("Baseline V2 anlegen", f"{v2_resp.status_code}: {v2_resp.text}")
    v2_id = v2_resp.json()["id"]

    print("6/8  Unveränderter Baum liefert keine strukturellen Deviations ...")
    v2_devs = client.get(f"/projects/baselines/{v2_id}/deviations").json()
    if any(d["type"] in ("added", "removed") for d in v2_devs):
        _fail("Deviation V2 baseline", f"unerwartete strukturelle Deviation direkt nach Snapshot: {v2_devs}")

    print("7/8  Neu angelegte Phase erscheint als 'added', gelöschte als 'removed' ...")
    new_phase = _create_phase(project_id, phase_type="Neue Migrationsphase")
    del_resp = client.delete(f"/projects/plan-phases/{stable_leaf['id']}")
    if del_resp.status_code != 204:
        _fail("Phase löschen", f"{del_resp.status_code}: {del_resp.text}")

    v2_devs = client.get(f"/projects/baselines/{v2_id}/deviations").json()

    added = next((d for d in v2_devs if d["type"] == "added" and d["entity_id"] == new_phase["id"]), None)
    if added is None:
        _fail("Deviation added", f"keine 'added'-Deviation für neue Phase gefunden: {v2_devs}")
    if added["label"] != "Neue Migrationsphase" or added["entity_type"] != "plan_phase":
        _fail("Deviation added label", f"unerwarteter Wert: {added}")

    removed = next((d for d in v2_devs if d["type"] == "removed" and d["entity_id"] == stable_leaf["id"]), None)
    if removed is None:
        _fail("Deviation removed", f"keine 'removed'-Deviation für gelöschte Phase gefunden: {v2_devs}")
    if removed["label"] != "Feinkonzept":
        _fail("Deviation removed label", f"Name der gelöschten Phase nicht rekonstruierbar: {removed}")
    for d in v2_devs:
        label = d.get("label")
        if label is not None and re.fullmatch(r"#\d+", label):
            _fail("Roh-ID im Deviation-Label", f"unerwartete rohe ID: {d}")
    # keine zusätzlichen Feld-Deltas mehr für dieselbe entfernte Phase (kein Doppel-Reporting)
    stray_field_devs = [
        d for d in v2_devs if d["entity_id"] == stable_leaf["id"] and d["type"] == "changed"
    ]
    if stray_field_devs:
        _fail("Doppeltes Removed-Reporting", f"unerwartete Feld-Deltas für entfernte Phase: {stray_field_devs}")

    print("8/8  plan_fte-/Forecast-Änderung bleibt als 'changed' erkennbar (Regression) ...")
    fte_leaf = _create_phase(project_id, phase_type="Umsetzung", plan_fte=0.5, forecast_start="2026-12-01", forecast_end="2026-12-31")
    v3_resp = client.post(f"/projects/{project_id}/baselines", json={"name": "V3"})
    v3_id = v3_resp.json()["id"]
    upd = client.put(
        f"/projects/plan-phases/{fte_leaf['id']}",
        json={"plan_fte": 0.8, "forecast_start": "2026-12-08", "forecast_end": "2027-01-05"},
    )
    if upd.status_code != 200:
        _fail("plan_fte/Forecast Update", f"{upd.status_code}: {upd.text}")

    v3_devs = client.get(f"/projects/baselines/{v3_id}/deviations").json()
    fte_dev = next((d for d in v3_devs if d["entity_id"] == fte_leaf["id"] and d["field"] == "plan_fte"), None)
    if fte_dev is None or fte_dev["type"] != "changed" or fte_dev["baseline_value"] != "0.5" or fte_dev["current_value"] != "0.8":
        _fail("plan_fte Deviation", f"unerwartet: {fte_dev}")
    start_dev = next((d for d in v3_devs if d["entity_id"] == fte_leaf["id"] and d["field"] == "forecast_start"), None)
    if start_dev is None or start_dev["type"] != "changed" or start_dev["delta_days"] != 7:
        _fail("forecast_start Deviation", f"unerwartet: {start_dev}")

    print("OK — Planstand erkennt Phase hinzugefügt/entfernt strukturell mit sprechendem "
          "Namen (kein Roh-ID-Leck), unveränderter Baum bleibt deviation-frei, plan_fte-/"
          "Forecast-Änderungen bleiben unverändert als 'changed' erkennbar.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
