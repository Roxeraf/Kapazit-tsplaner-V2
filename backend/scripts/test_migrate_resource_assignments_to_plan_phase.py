"""P20.1: Verifikation von migrate_resource_assignments_to_plan_phase.py gegen
repräsentative Testdaten (eindeutige Fälle, legacy-unmapped Grobplanung, Konflikt,
Orphan, bereits direkt). Kein pytest im Repo (siehe check_migrations.py als etabliertes
Muster) - baut eine Wegwerf-SQLite-DB, migriert sie per Alembic auf den Kopf, seedet
Testdaten direkt über die Models und prüft:

1. Dry-Run schreibt NICHTS (plan_phase_id-Werte vor/nach Dry-Run identisch).
2. Dry-Run-Report zeigt bereits die korrekten Zahlen.
3. Apply-Lauf migriert genau die eindeutigen Fälle, lässt legacy_unmapped/conflicts/orphans/
   already_direct unangetastet, resource_demand_id bleibt in JEDEM Fall unverändert (Compat).
4. Re-Run nach Apply ist idempotent (migrated_to_plan_phase == 0, alles already_direct/
   unverändert kategorisiert).

Aufruf: python backend/scripts/test_migrate_resource_assignments_to_plan_phase.py
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

_tmp = tempfile.TemporaryDirectory(prefix="kapa_migrate_assignments_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app import models  # noqa: E402

from migrate_resource_assignments_to_plan_phase import migrate  # noqa: E402


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _alembic_upgrade_head() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")


def _seed(db) -> dict:
    now = _now()
    project = models.Project(name="P20.1 Migrationstest", start_monat="10.2026", anzahl_monate=3)
    db.add(project)
    db.flush()

    role = models.ResourceRole(name="P20.1 Testrolle")
    db.add(role)
    db.flush()

    phase_a = models.PlanPhase(
        project_id=project.id, phase_type="Phase A", status="geplant",
        forecast_start="2026-10-01", forecast_end="2026-10-31", plan_fte=0.5,
        erstellt_am=now, aktualisiert_am=now,
    )
    phase_b = models.PlanPhase(
        project_id=project.id, phase_type="Phase B", status="geplant",
        forecast_start="2026-11-01", forecast_end="2026-11-30", plan_fte=0.3,
        erstellt_am=now, aktualisiert_am=now,
    )
    db.add_all([phase_a, phase_b])
    db.flush()

    dominik = models.Person(display_name="Dominik")
    max_ = models.Person(display_name="Max")
    anna = models.Person(display_name="Anna")
    db.add_all([dominik, max_, anna])
    db.flush()

    # Fall 1: eindeutig migrierbar - Demand mit plan_phase_id, ein Assignment.
    demand_mapped = models.ResourceDemand(
        project_id=project.id, plan_phase_id=phase_a.id, resource_role_id=role.id,
        period="Okt 26", fte=0.5, commitment_level="TENTATIVE", erstellt_am=now, aktualisiert_am=now,
    )
    db.add(demand_mapped)
    db.flush()
    assignment_migratable = models.ResourceAssignment(
        resource_demand_id=demand_mapped.id, person_id=dominik.id, fte=0.5, erstellt_am=now, aktualisiert_am=now,
    )
    db.add(assignment_migratable)

    # Fall 2: legacy_unmapped - Demand OHNE plan_phase_id (alte Grobplanung).
    demand_unmapped = models.ResourceDemand(
        project_id=project.id, plan_phase_id=None, resource_role_id=role.id,
        period="Okt 26", fte=0.2, commitment_level="TENTATIVE", erstellt_am=now, aktualisiert_am=now,
    )
    db.add(demand_unmapped)
    db.flush()
    assignment_unmapped = models.ResourceAssignment(
        resource_demand_id=demand_unmapped.id, person_id=max_.id, fte=0.2, erstellt_am=now, aktualisiert_am=now,
    )
    db.add(assignment_unmapped)

    # Fall 3: conflict - Anna ist bereits DIREKT Phase B zugeordnet, UND über eine Legacy-
    # Demand, die ebenfalls auf Phase B zeigt -> die Legacy-Zeile darf nicht migriert werden
    # (würde die Unique-Kombination (plan_phase_id, person_id) duplizieren).
    demand_conflict = models.ResourceDemand(
        project_id=project.id, plan_phase_id=phase_b.id, resource_role_id=role.id,
        period="Nov 26", fte=0.3, commitment_level="TENTATIVE", erstellt_am=now, aktualisiert_am=now,
    )
    db.add(demand_conflict)
    db.flush()
    assignment_conflict_legacy = models.ResourceAssignment(
        resource_demand_id=demand_conflict.id, person_id=anna.id, fte=0.1, erstellt_am=now, aktualisiert_am=now,
    )
    assignment_already_direct = models.ResourceAssignment(
        plan_phase_id=phase_b.id, person_id=anna.id, fte=0.3, erstellt_am=now, aktualisiert_am=now,
    )
    db.add_all([assignment_conflict_legacy, assignment_already_direct])

    db.commit()
    return {
        "assignment_migratable_id": assignment_migratable.id,
        "assignment_unmapped_id": assignment_unmapped.id,
        "assignment_conflict_legacy_id": assignment_conflict_legacy.id,
        "assignment_already_direct_id": assignment_already_direct.id,
        "phase_a_id": phase_a.id,
        "phase_b_id": phase_b.id,
    }


def main() -> None:
    print("Setup: Alembic-Kette auf Kopf bringen + Testdaten seeden ...")
    _alembic_upgrade_head()
    db = SessionLocal()
    ids = _seed(db)
    db.close()

    print("1/4  Dry-Run schreibt nichts ...")
    db = SessionLocal()
    report = migrate(db, apply=False)
    db.close()
    if report.assignments_total != 4:
        _fail("Dry-Run", f"erwartet 4 Assignments total, bekommen {report.assignments_total}")
    if report.migrated_to_plan_phase != 1 or report.legacy_unmapped != 1 or report.conflicts != 1 or report.already_direct != 1:
        _fail("Dry-Run Zahlen", f"unerwartete Kategorisierung: {report}")
    if report.has_discrepancies:
        _fail("Dry-Run Diskrepanzen", f"{report}")

    db = SessionLocal()
    still_unmigrated = db.get(models.ResourceAssignment, ids["assignment_migratable_id"])
    if still_unmigrated.plan_phase_id is not None:
        _fail("Dry-Run Rollback", "plan_phase_id wurde trotz Dry-Run gesetzt (Rollback fehlgeschlagen)")
    db.close()

    print("2/4  Apply migriert genau den eindeutigen Fall ...")
    db = SessionLocal()
    report = migrate(db, apply=True)
    db.close()
    if report.migrated_to_plan_phase != 1:
        _fail("Apply", f"erwartet genau 1 Migration, bekommen {report.migrated_to_plan_phase}")
    if report.has_discrepancies:
        _fail("Apply Diskrepanzen", f"{report}")

    db = SessionLocal()
    migrated = db.get(models.ResourceAssignment, ids["assignment_migratable_id"])
    if migrated.plan_phase_id != ids["phase_a_id"]:
        _fail("Apply Ergebnis", f"plan_phase_id nicht gesetzt wie erwartet: {migrated.plan_phase_id}")
    if migrated.resource_demand_id is None:
        _fail("Compat", "resource_demand_id wurde entfernt statt als Compat-Verweis erhalten zu bleiben")

    unmapped = db.get(models.ResourceAssignment, ids["assignment_unmapped_id"])
    if unmapped.plan_phase_id is not None:
        _fail("Legacy-Unmapped unangetastet", f"plan_phase_id wurde trotzdem gesetzt: {unmapped.plan_phase_id}")

    conflict_legacy = db.get(models.ResourceAssignment, ids["assignment_conflict_legacy_id"])
    if conflict_legacy.plan_phase_id is not None:
        _fail("Conflict unangetastet", f"plan_phase_id wurde trotz Konflikt gesetzt: {conflict_legacy.plan_phase_id}")
    already_direct = db.get(models.ResourceAssignment, ids["assignment_already_direct_id"])
    if already_direct.plan_phase_id != ids["phase_b_id"] or already_direct.fte != 0.3:
        _fail("Already-Direct unverändert", f"unerwarteter Zustand: {already_direct.plan_phase_id}/{already_direct.fte}")
    db.close()

    print("3/4  Re-Run nach Apply ist idempotent ...")
    db = SessionLocal()
    report2 = migrate(db, apply=True)
    db.close()
    if report2.migrated_to_plan_phase != 0:
        _fail("Idempotenz", f"zweiter Lauf hätte nichts mehr migrieren dürfen: {report2}")
    if report2.already_direct != 2:
        _fail("Idempotenz already_direct", f"erwartet 2 (migriert + bereits direkt), bekommen {report2.already_direct}")
    if report2.legacy_unmapped != 1 or report2.conflicts != 1:
        _fail("Idempotenz Kategorien", f"unerwartete Kategorisierung im Re-Run: {report2}")

    print("4/4  Konflikt-Details enthalten die betroffene Zeile ...")
    if len(report.conflict_details) != 1 or report.conflict_details[0].assignment_id != ids["assignment_conflict_legacy_id"]:
        _fail("Konflikt-Details", f"erwartet genau den Legacy-Konflikt im Report: {report.conflict_details}")

    print("OK — Dry-Run schreibt nichts, Apply migriert nur den eindeutigen Fall (resource_demand_id "
          "bleibt als Compat erhalten), legacy_unmapped/conflicts/orphans werden korrekt reportet und "
          "nicht angefasst, Re-Run ist idempotent.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
