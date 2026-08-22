"""P18/B-4: Integrationstests für Direct Assignment ohne Rollen-Zwang und die
Range-basierte Available-Capacity-Erweiterung (CONCEPT.md Abschnitt 6b.4/6b.5/6b.10/6b.11).
Kein pytest im Repo (siehe check_migrations.py als etabliertes Muster) - TestClient gegen die
echte FastAPI-App. Prüft:

1. compute_person_capacity_for_range über eine Monatsgrenze hinweg liefert ein werktage-
   gewichtetes Ergebnis (keine neue Holiday-/Absence-Query - reine Gewichtung bestehender
   Monatswerte).
2. GET /resource-roles blendet die interne Systemrolle "Ohne Rolle" standardmäßig aus,
   include_system_roles=true zeigt sie.
3. POST /plan-phases/{id}/assign-person ordnet eine Person OHNE Rollenauswahl zu, legt dafür
   genau eine ResourceDemand mit der Systemrolle an (idempotent bei einer zweiten Person auf
   derselben Phase - keine zweite Demand-Zeile).
4. Bedarf/Besetzt/Offen entspricht exakt dem Beispiel aus der Aufgabenstellung (Abschnitt 8):
   plan_fte bleibt unverändert 0.40, auch bei Überbesetzung (Summe > plan_fte).
5. Direkte Zuordnung auf einer Parent-Phase (has_children) wird abgelehnt (422).
6. assignment-candidates nutzt die Range-Capacity und schließt bereits zugeordnete Personen
   aus.

Aufruf: python backend/scripts/test_direct_assignment_and_capacity_range.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_direct_assignment_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402 - Import triggert db_bootstrap.run_migrations()
from app.database import SessionLocal, engine  # noqa: E402
from app import capacity_calc, models  # noqa: E402

client = TestClient(app)


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def main() -> None:
    print("1/6  compute_person_capacity_for_range über eine Monatsgrenze hinweg ...")
    db = SessionLocal()
    person = models.Person(display_name="Range-Testperson")
    db.add(person)
    db.flush()
    db.add(models.WorkingTime(person_id=person.id, valid_from="2020-01-01", weekly_hours=40))
    db.commit()
    person_id = person.id
    db.close()

    range_capacity = capacity_calc.compute_person_capacity_for_range(
        SessionLocal(), person_id, date(2026, 10, 20), date(2026, 11, 20)
    )
    if range_capacity is None:
        _fail("Range-Capacity", "compute_person_capacity_for_range lieferte None")
    # Erwarteter Wert exakt nach der spezifizierten Formel (Abschnitt 6a.8/6b.5): Oktober hat
    # 22 Werktage insgesamt (9 davon im Bereich 20.10.-31.10.), November hat 21 Werktage
    # insgesamt (15 davon im Bereich 01.11.-20.11.) - die Gewichte summieren sich bei
    # unterschiedlich langen Monaten bewusst NICHT exakt auf 1.0 (dokumentiertes, akzeptiertes
    # Verhalten der werktage-anteiligen Gewichtung, keine zweite Rundungskonvention).
    expected_nominal = round(9 / 22 + 15 / 21, 4)
    if abs(range_capacity.nominal_fte - expected_nominal) > 0.001:
        _fail("Range-Capacity", f"nominal_fte={range_capacity.nominal_fte}, erwartet {expected_nominal}")
    if range_capacity.working_days != 24:  # count_weekdays_in_range(20.10.-20.11.2026)
        _fail("Range-Capacity", f"working_days unerwartet: {range_capacity.working_days}")

    print("2/6  GET /resource-roles blendet die Systemrolle standardmäßig aus ...")
    resp = client.get("/resource-roles")
    if any(r["name"] == "Ohne Rolle" for r in resp.json()):
        _fail("Rollen-Picker", "Systemrolle 'Ohne Rolle' erscheint im Standard-Rollen-Picker")
    resp_all = client.get("/resource-roles", params={"include_system_roles": True})
    if not any(r["name"] == "Ohne Rolle" for r in resp_all.json()):
        _fail("Rollen-Picker", "Systemrolle fehlt trotz include_system_roles=true")

    print("3/6  Direkte Zuordnung ohne Rollenauswahl ...")
    project_resp = client.post("/projects", json={"name": "B-4 Testprojekt", "start_monat": "10.2026"})
    project_id = project_resp.json()["id"]
    phase_resp = client.post(
        f"/projects/{project_id}/plan-phases",
        json={
            "phase_type": "Konfiguration",
            "status": "geplant",
            "forecast_start": "2026-10-01",
            "forecast_end": "2026-10-31",
            "plan_fte": 0.4,
        },
    )
    phase_id = phase_resp.json()["id"]

    dominik = client.post("/people", json={"display_name": "Dominik"}).json()
    max_ = client.post("/people", json={"display_name": "Max"}).json()

    resp = client.post(
        f"/projects/plan-phases/{phase_id}/assign-person", json={"person_id": dominik["id"], "fte": 0.2}
    )
    if resp.status_code != 200:
        _fail("assign-person", f"{resp.status_code}: {resp.text}")
    summary = resp.json()
    if summary["plan_fte"] != 0.4 or summary["assigned_fte"] != 0.2 or summary["open_fte"] != 0.2:
        _fail("assign-person", f"Bedarf/Besetzt/Offen falsch nach 1. Zuordnung: {summary}")

    demands = client.get(f"/projects/{project_id}/resource-demands").json()
    demands_for_phase = [d for d in demands if d["plan_phase_id"] == phase_id]
    if len(demands_for_phase) != 1:
        _fail("assign-person", f"erwartet genau 1 Carrier-Demand, gefunden {len(demands_for_phase)}")

    print("4/6  Zweite Person, dann Überbesetzung - plan_fte bleibt unverändert ...")
    resp = client.post(
        f"/projects/plan-phases/{phase_id}/assign-person", json={"person_id": max_["id"], "fte": 0.2}
    )
    summary = resp.json()
    if summary["assigned_fte"] != 0.4 or summary["open_fte"] != 0.0:
        _fail("assign-person", f"Bedarf/Besetzt/Offen falsch nach 2. Zuordnung: {summary}")
    if len(summary["assignments"]) != 2:
        _fail("assign-person", f"erwartet 2 Assignments: {summary}")

    resp = client.post(
        f"/projects/plan-phases/{phase_id}/assign-person", json={"person_id": max_["id"], "fte": 0.3}
    )
    summary = resp.json()
    if summary["plan_fte"] != 0.4:
        _fail("Überbesetzung", f"plan_fte hätte unverändert 0.4 bleiben müssen: {summary}")
    if summary["assigned_fte"] != 0.5 or summary["open_fte"] != -0.1:
        _fail("Überbesetzung", f"erwartet assigned_fte=0.5/open_fte=-0.1: {summary}")

    demands_for_phase_after = [
        d for d in client.get(f"/projects/{project_id}/resource-demands").json() if d["plan_phase_id"] == phase_id
    ]
    if len(demands_for_phase_after) != 1:
        _fail("Idempotenz Carrier-Demand", f"erwartet weiterhin 1 Demand: {demands_for_phase_after}")

    print("5/6  Direkte Zuordnung auf einer Parent-Phase wird abgelehnt ...")
    child_resp = client.post(
        f"/projects/{project_id}/plan-phases",
        json={"phase_type": "Unterphase", "status": "geplant", "parent_phase_id": phase_id},
    )
    if child_resp.status_code != 201:
        _fail("Setup Parent", f"{child_resp.status_code}: {child_resp.text}")
    resp = client.post(
        f"/projects/plan-phases/{phase_id}/assign-person", json={"person_id": dominik["id"], "fte": 0.1}
    )
    if resp.status_code != 422:
        _fail("Parent-Block", f"erwartet 422 auf Parent-Phase, bekommen {resp.status_code}: {resp.text}")

    print("6/6  assignment-candidates nutzt Range-Capacity und schließt Zugeordnete aus ...")
    solo = client.post("/people", json={"display_name": "Solo-Kandidat"}).json()
    db = SessionLocal()
    db.add(models.WorkingTime(person_id=solo["id"], valid_from="2020-01-01", weekly_hours=40))
    db.add(models.ResourceProfile(person_id=solo["id"], weekly_hours=40, capacity_relevant=True))
    db.add(models.ResourceProfile(person_id=dominik["id"], weekly_hours=40, capacity_relevant=True))
    db.commit()
    db.close()

    candidates = client.get(f"/projects/plan-phases/{phase_id}/assignment-candidates").json()
    candidate_ids = {c["person_id"] for c in candidates}
    if dominik["id"] in candidate_ids:
        _fail("assignment-candidates", "bereits zugeordnete Person taucht trotzdem als Kandidat auf")
    if solo["id"] not in candidate_ids:
        _fail("assignment-candidates", f"Solo-Kandidat mit freier Kapazität fehlt: {candidates}")

    unassign_resp = client.delete(f"/projects/plan-phases/{phase_id}/assign-person/{dominik['id']}")
    if unassign_resp.status_code != 200 or unassign_resp.json()["assigned_fte"] != 0.3:
        _fail("unassign", f"{unassign_resp.status_code}: {unassign_resp.text}")

    print("OK — Range-Capacity werktage-gewichtet korrekt, Rollen-Picker blendet Systemrolle "
          "aus, Direct Assignment ohne Rollenauswahl funktioniert (idempotente Carrier-Demand, "
          "plan_fte unverändert auch bei Überbesetzung), Parent-Block und Candidates korrekt.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
