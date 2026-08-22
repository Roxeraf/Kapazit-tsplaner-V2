"""P18/B-5: Integrationstests für "Derived Monthly & Portfolio Capacity" (CONCEPT.md
Abschnitt 6b.6, Abschnitt 13 der Aufgabenstellung - NICHT "Monthly Planning"). Kein pytest im
Repo (siehe check_migrations.py als etabliertes Muster). Prüft:

1. phase_metrics_calc.monthly_distribution gegen das vollständig durchgerechnete Beispiel aus
   CONCEPT.md Abschnitt 6a.6 (Projekt "Red Bull WMS Rollout").
2. capacity_calc.compute_project_monthly_capacity summiert korrekt über mehrere Leaf-Phasen
   und ignoriert eine Parent-Phase (plan_fte immer None) automatisch.
3. GET /projects/{id}/capacity/monthly liefert Stunden + FTE-Äquivalent (read-only
   Auswertung).
4. GET /projects/{id}/cockpit (Capacity-Block) liest jetzt aus PlanPhase.plan_fte statt einer
   ResourceDemand-Summe - eine bewusst falsche ResourceDemand.fte im aktuellen Monat darf das
   Ergebnis NICHT verfälschen.
5. GET /controlling/allocation-gaps und GET /controlling/roles blenden die interne
   Systemrolle "Ohne Rolle" aus, eine echte Rolle bleibt sichtbar.

Aufruf: python backend/scripts/test_derived_monthly_capacity.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_derived_monthly_capacity_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402 - Import triggert db_bootstrap.run_migrations()
from app.database import SessionLocal, engine  # noqa: E402
from app import capacity_calc, constants, models, phase_metrics_calc  # noqa: E402

client = TestClient(app)


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def main() -> None:
    print("1/5  monthly_distribution gegen das Red-Bull-WMS-Beispiel (CONCEPT.md 6a.6) ...")
    pflichtenheft = phase_metrics_calc.monthly_distribution(0.50, "2026-10-01", "2026-10-17")
    konfiguration = phase_metrics_calc.monthly_distribution(0.80, "2026-10-19", "2026-11-13")
    test_phase = phase_metrics_calc.monthly_distribution(1.20, "2026-11-16", "2026-11-27")

    if pflichtenheft != {"Okt 26": 48.0}:
        _fail("monthly_distribution Pflichtenheft", f"{pflichtenheft}")
    if konfiguration != {"Okt 26": 64.0, "Nov 26": 64.0}:
        _fail("monthly_distribution Konfiguration", f"{konfiguration}")
    if test_phase != {"Nov 26": 96.0}:
        _fail("monthly_distribution Test", f"{test_phase}")

    okt_total = pflichtenheft["Okt 26"] + konfiguration["Okt 26"]
    nov_total = konfiguration["Nov 26"] + test_phase["Nov 26"]
    if okt_total != 112.0 or nov_total != 160.0:
        _fail("monthly_distribution Summe", f"Okt={okt_total}, Nov={nov_total}, erwartet 112.0/160.0")

    print("2/5  compute_project_monthly_capacity summiert über Leaf-Phasen, Parent trägt 0 bei ...")
    project_resp = client.post("/projects", json={"name": "Red Bull WMS Rollout", "start_monat": "10.2026"})
    project_id = project_resp.json()["id"]

    parent_resp = client.post(
        f"/projects/{project_id}/plan-phases", json={"phase_type": "Wareneingang", "status": "geplant"}
    )
    parent_id = parent_resp.json()["id"]
    client.post(
        f"/projects/{project_id}/plan-phases",
        json={
            "phase_type": "Pflichtenheft", "status": "geplant", "parent_phase_id": parent_id,
            "forecast_start": "2026-10-01", "forecast_end": "2026-10-17", "plan_fte": 0.50,
        },
    )
    client.post(
        f"/projects/{project_id}/plan-phases",
        json={
            "phase_type": "Konfiguration", "status": "geplant", "parent_phase_id": parent_id,
            "forecast_start": "2026-10-19", "forecast_end": "2026-11-13", "plan_fte": 0.80,
        },
    )
    client.post(
        f"/projects/{project_id}/plan-phases",
        json={
            "phase_type": "Test", "status": "geplant", "parent_phase_id": parent_id,
            "forecast_start": "2026-11-16", "forecast_end": "2026-11-27", "plan_fte": 1.20,
        },
    )

    db = SessionLocal()
    monthly = capacity_calc.compute_project_monthly_capacity(db, project_id, periods=["Okt 26", "Nov 26", "Dez 26"])
    db.close()
    if monthly != {"Okt 26": 112.0, "Nov 26": 160.0, "Dez 26": 0.0}:
        _fail("compute_project_monthly_capacity", f"{monthly}")

    print("3/5  GET /projects/{id}/capacity/monthly liefert Stunden + FTE-Äquivalent ...")
    resp = client.get(f"/projects/{project_id}/capacity/monthly", params={"periods": ["Okt 26", "Nov 26"]})
    if resp.status_code != 200:
        _fail("capacity/monthly", f"{resp.status_code}: {resp.text}")
    entries = {e["period"]: e for e in resp.json()}
    if entries["Okt 26"]["hours"] != 112.0:
        _fail("capacity/monthly", f"Okt-Stunden falsch: {entries}")
    # 112h / (22 Werktage * 8h) = 0.6364 (Werktage Okt 2026 = 22, siehe CONCEPT.md-Beispiel)
    if abs(entries["Okt 26"]["fte_equivalent"] - round(112 / (22 * 8), 4)) > 0.0001:
        _fail("capacity/monthly", f"Okt-FTE-Äquivalent falsch: {entries['Okt 26']}")

    print("4/5  Cockpit-Kapazität liest aus PlanPhase, ignoriert falsche ResourceDemand.fte ...")
    today = date.today()
    month_start = today.replace(day=1)
    month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    current_period = constants.current_period()

    cockpit_project_resp = client.post(
        "/projects", json={"name": "Cockpit-Testprojekt", "start_monat": f"{today.month:02d}.{today.year}"}
    )
    cockpit_project_id = cockpit_project_resp.json()["id"]
    client.post(
        f"/projects/{cockpit_project_id}/plan-phases",
        json={
            "phase_type": "Laufende Phase", "status": "laufend",
            "forecast_start": month_start.isoformat(), "forecast_end": month_end.isoformat(), "plan_fte": 1.0,
        },
    )
    role_resp = client.post("/resource-roles", json={"name": "Cockpit-Test-Rolle"})
    role_id = role_resp.json()["id"]
    client.post(
        f"/projects/{cockpit_project_id}/resource-demands",
        json={"resource_role_id": role_id, "period": current_period, "fte": 999.0, "commitment_level": "TENTATIVE"},
    )

    cockpit = client.get(f"/projects/{cockpit_project_id}/cockpit").json()
    reported_demand = cockpit["capacity"]["demand_fte"]
    if abs(reported_demand - 999.0) < 1:
        _fail("Cockpit", f"demand_fte scheint noch aus der ResourceDemand-Summe zu kommen: {reported_demand}")
    if reported_demand <= 0 or reported_demand > 2:
        _fail("Cockpit", f"demand_fte unplausibel für 1.0 plan_fte über den ganzen Monat: {reported_demand}")

    print("5/5  Systemrolle wird aus Rollen-Reporting ausgeblendet ...")
    dominik = client.post("/people", json={"display_name": "Dominik R5"}).json()
    phase_for_assign_resp = client.post(
        f"/projects/{cockpit_project_id}/plan-phases",
        json={
            "phase_type": "Direktzuordnung", "status": "geplant",
            "forecast_start": month_start.isoformat(), "forecast_end": month_end.isoformat(), "plan_fte": 0.3,
        },
    )
    phase_for_assign_id = phase_for_assign_resp.json()["id"]
    client.post(
        f"/projects/plan-phases/{phase_for_assign_id}/assign-person", json={"person_id": dominik["id"], "fte": 0.3}
    )

    allocation_gaps = client.get("/controlling/allocation-gaps", params={"period": current_period}).json()
    if any(e["resource_role_name"] == "Ohne Rolle" for e in allocation_gaps):
        _fail("allocation-gaps", "Systemrolle 'Ohne Rolle' taucht in der Rollen-Auswertung auf")
    if not any(e["resource_role_name"] == "Cockpit-Test-Rolle" for e in allocation_gaps):
        _fail("allocation-gaps", "echte Rolle fehlt in der Auswertung")

    role_analysis = client.get("/controlling/roles", params={"period": current_period}).json()
    if any(e["resource_role_name"] == "Ohne Rolle" for e in role_analysis):
        _fail("role-analysis", "Systemrolle 'Ohne Rolle' taucht in GET /controlling/roles auf")

    print("OK — monthly_distribution/compute_project_monthly_capacity exakt nach dem CONCEPT.md-"
          "Beispiel, /capacity/monthly liefert Stunden+FTE-Äquivalent, Cockpit-Kapazität kommt "
          "aus PlanPhase statt ResourceDemand-Summe, Systemrolle bleibt aus dem Rollen-Reporting "
          "ausgeblendet.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
