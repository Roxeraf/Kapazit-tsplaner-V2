"""P20.1D: Capacity Consumer Rewiring - prüft, dass Portfolio Utilization, Cockpit-Kapazität
und Utilization Gap (gap-engine) jetzt auch direkte PlanPhase-Assignments (ohne
ResourceDemand) berücksichtigen, ohne migrierte Zeilen (beide FKs gesetzt) doppelt zu zählen,
und dass Derived Monthly/Portfolio Capacity weiterhin AUSSCHLIESSLICH aus plan_fte kommt
(Regression Gate, Auftrag Abschnitt 28: "NICHT: SUM(ResourceAssignments)").

Aufruf: python backend/scripts/test_p20_1_capacity_consumer_rewiring.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_capacity_rewiring_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app import capacity_calc, models  # noqa: E402

client = TestClient(app)


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    print("Setup: Projekt, Person mit WorkingTime/ResourceProfile, Rolle, direkte + Legacy-Zuordnung ...")
    db = SessionLocal()
    person = models.Person(display_name="Rewiring-Testperson")
    db.add(person)
    db.flush()
    db.add(models.WorkingTime(person_id=person.id, valid_from="2020-01-01", weekly_hours=40))
    db.add(models.ResourceProfile(person_id=person.id, weekly_hours=40, capacity_relevant=True))
    person_id = person.id
    db.commit()
    db.close()

    project = client.post("/projects", json={"name": "P20.1D Testprojekt", "start_monat": "10.2026"}).json()
    project_id = project["id"]

    # Direkte Zuordnung (neuer Standardpfad) - 0.3 FTE, Oktober 2026.
    direct_phase = client.post(
        f"/projects/{project_id}/plan-phases",
        json={"phase_type": "Direkt", "status": "geplant", "forecast_start": "2026-10-01", "forecast_end": "2026-10-31", "plan_fte": 0.3},
    ).json()
    assign_resp = client.post(
        f"/projects/plan-phases/{direct_phase['id']}/assign-person", json={"person_id": person_id, "fte": 0.3}
    )
    if assign_resp.status_code != 200:
        _fail("Setup direkte Zuordnung", f"{assign_resp.status_code}: {assign_resp.text}")

    # Legacy-Zuordnung über eine ResourceDemand OHNE plan_phase_id (alte Grobplanung),
    # ebenfalls Oktober 2026, 0.2 FTE - muss weiterhin mitgezählt werden.
    role_resp = client.post("/resource-roles", json={"name": "P20.1D Testrolle"})
    role_id = role_resp.json()["id"]
    legacy_demand_resp = client.post(
        f"/projects/{project_id}/resource-demands",
        json={"resource_role_id": role_id, "period": "Okt 26", "fte": 0.2},
    )
    if legacy_demand_resp.status_code != 201:
        _fail("Setup Legacy-Demand", f"{legacy_demand_resp.status_code}: {legacy_demand_resp.text}")
    legacy_demand_id = legacy_demand_resp.json()["id"]
    legacy_assign_resp = client.post(
        f"/resource-demands/{legacy_demand_id}/assignments", json={"person_id": person_id, "fte": 0.2}
    )
    if legacy_assign_resp.status_code != 201:
        _fail("Setup Legacy-Assignment", f"{legacy_assign_resp.status_code}: {legacy_assign_resp.text}")

    print("1/5  assigned_fte_for_person_period summiert BEIDE Wege ohne Dopplung ...")
    db = SessionLocal()
    total = capacity_calc.assigned_fte_for_person_period(db, person_id, "Okt 26")
    db.close()
    if abs(total - 0.5) > 0.001:
        _fail("assigned_fte_for_person_period", f"erwartet 0.5 (0.3 direkt + 0.2 legacy), bekommen {total}")

    print("2/5  Eine MIGRIERTE Zeile (beide FKs gesetzt) zählt trotzdem nur einmal ...")
    db = SessionLocal()
    direct_row = (
        db.query(models.ResourceAssignment)
        .filter(models.ResourceAssignment.plan_phase_id == direct_phase["id"], models.ResourceAssignment.person_id == person_id)
        .first()
    )
    # Simuliert das Ergebnis von migrate_resource_assignments_to_plan_phase.py: beide FKs
    # gesetzt (resource_demand_id zusätzlich zum bereits vorhandenen plan_phase_id) - eine
    # EIGENE Demand, damit die (resource_demand_id, person_id)-Unique-Kombination nicht mit
    # der bereits bestehenden Legacy-Zuordnung kollidiert.
    migration_sim_demand = models.ResourceDemand(
        project_id=project_id, plan_phase_id=direct_phase["id"], resource_role_id=role_id,
        period="Okt 26", fte=0.3, commitment_level="TENTATIVE", erstellt_am=_now(), aktualisiert_am=_now(),
    )
    db.add(migration_sim_demand)
    db.flush()
    direct_row.resource_demand_id = migration_sim_demand.id
    direct_row_id = direct_row.id
    db.commit()
    db.close()
    db = SessionLocal()
    total_after_merge = capacity_calc.assigned_fte_for_person_period(db, person_id, "Okt 26")
    db.close()
    if abs(total_after_merge - 0.5) > 0.001:
        _fail(
            "Keine Dopplung bei migrierten Zeilen",
            f"erwartet weiterhin 0.5 (nicht 0.8 durch Doppelzählung), bekommen {total_after_merge}",
        )
    # Zustand für die folgenden Schritte zurücksetzen (nicht Teil des Migrations-Szenarios).
    db = SessionLocal()
    direct_row = db.get(models.ResourceAssignment, direct_row_id)
    direct_row.resource_demand_id = None
    db.commit()
    db.close()

    print("3/5  Portfolio Utilization (routers/team.py -> capacity_calc.compute_portfolio_utilization) ...")
    utilization = client.get("/team/utilization", params={"period": "Okt 26"}).json()
    entry = next((e for e in utilization if e["person_id"] == person_id), None)
    if entry is None:
        _fail("Portfolio Utilization", f"Person fehlt in der Auslastungsliste: {utilization}")
    if abs(entry["zugeordnet_fte"] - 0.5) > 0.001:
        _fail("Portfolio Utilization", f"erwartet zugeordnet_fte=0.5, bekommen {entry['zugeordnet_fte']}")

    print("4/5  Utilization Gap (gap-engine) berücksichtigt direkte Zuordnung ...")
    gap = client.get(f"/people/{person_id}/gaps/utilization", params={"period": "Okt 26"}).json()
    if abs(gap["assigned_fte"] - 0.5) > 0.001:
        _fail("Utilization Gap", f"erwartet assigned_fte=0.5, bekommen {gap}")

    print("5/5  Derived Monthly Capacity bleibt AUSSCHLIESSLICH plan_fte-basiert (Regression Gate) ...")
    monthly = client.get(f"/projects/{project_id}/capacity/monthly", params={"periods": ["Okt 26"]}).json()
    okt = next(m for m in monthly if m["period"] == "Okt 26")
    # plan_fte=0.3 über den ganzen Oktober - NICHT die Assignment-Summe (0.5 FTE-äquivalent).
    from datetime import date
    weekdays_okt = capacity_calc.count_weekdays_in_range(date(2026, 10, 1), date(2026, 10, 31))
    expected_hours = round(0.3 * weekdays_okt * 8, 2)
    if abs(okt["hours"] - expected_hours) > 0.5:
        _fail(
            "Derived Monthly Capacity Regression",
            f"erwartet ~plan_fte-basiert ({expected_hours}h), bekommen {okt['hours']}h - "
            "SUM(ResourceAssignments) wäre 0.5 FTE-äquivalent, das darf NICHT die Quelle sein",
        )

    print("OK — assigned_fte_for_person_period/compute_portfolio_utilization/Utilization Gap "
          "berücksichtigen jetzt direkte PlanPhase-Assignments zusätzlich zu Legacy-"
          "ResourceDemand-Assignments, migrierte Zeilen (beide FKs) zählen nicht doppelt, und "
          "Derived Monthly Capacity bleibt unverändert ausschließlich plan_fte-basiert.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
