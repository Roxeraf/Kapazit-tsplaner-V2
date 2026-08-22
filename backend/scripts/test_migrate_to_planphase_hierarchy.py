"""P18/B-2: Verifikation von migrate_to_planphase_hierarchy.py gegen repräsentative
Testdaten (Subprojects + parallele Grobplanung, mehrere Perioden/Rollen). Kein pytest im
Repo (siehe check_migrations.py als etabliertes Muster für eigenständige Prüfskripte) - dieses
Skript baut eine Wegwerf-SQLite-DB, migriert sie per Alembic auf den Kopf (inkl. B-1-Schema),
seedet Testdaten direkt über die Models und prüft:

1. Dry-Run schreibt NICHTS (Zeilenzahlen vor/nach Dry-Run identisch).
2. Dry-Run-Report zeigt bereits die korrekten Zahlen (0 Diskrepanzen), obwohl nichts committet
   wurde.
3. Apply-Lauf erzeugt genau die erwartete Struktur (Parent-Phase pro Subproject, Parent +
   Monats-Leafs für Grobplanung), FTE-Summen/Assignment-/Milestone-/Comment-Anzahlen bleiben
   erhalten (kein Datenverlust, BD-12).
4. Re-Run nach Apply findet nichts mehr zu migrieren (idempotent: Projekt hat danach weder
   Subprojects-mit-Kindern-ohne-Parent noch ResourceDemand(plan_phase_id IS NULL) mehr).

Aufruf: python backend/scripts/test_migrate_to_planphase_hierarchy.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.TemporaryDirectory(prefix="kapa_migrate_planphase_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app import models  # noqa: E402

from migrate_to_planphase_hierarchy import migrate  # noqa: E402


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def _alembic_upgrade_head() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")


def _seed_test_project(db) -> models.Project:
    project = models.Project(name="Testprojekt B-2", start_monat="10.2026", anzahl_monate=3)
    db.add(project)
    db.flush()

    # --- Subproject "Wareneingang" mit zwei bestehenden PlanPhase-Kindern ---
    sp = models.Subproject(project_id=project.id, name="Wareneingang", reihenfolge=0)
    db.add(sp)
    db.flush()

    now = "2026-08-21T00:00:00+00:00"
    child1 = models.PlanPhase(
        project_id=project.id, subproject_id=sp.id, phase_type="Pflichtenheft",
        forecast_start="2026-10-01", forecast_end="2026-10-17", plan_fte=0.4,
        erstellt_am=now, aktualisiert_am=now,
    )
    child2 = models.PlanPhase(
        project_id=project.id, subproject_id=sp.id, phase_type="Konfiguration",
        forecast_start="2026-10-20", forecast_end="2026-11-20", plan_fte=0.8,
        erstellt_am=now, aktualisiert_am=now,
    )
    db.add_all([child1, child2])
    db.flush()

    milestone = models.Milestone(
        project_id=project.id, subproject_id=sp.id, name="Fachkonzept freigegeben",
        forecast_date="2026-10-17", erstellt_am=now, aktualisiert_am=now,
    )
    comment = models.Comment(
        project_id=project.id, subproject_id=sp.id, text="Kickoff durchgeführt", erstellt_am=now,
    )
    db.add_all([milestone, comment])

    # --- Grobplanung: 2 Perioden, je 2 Rollen ---
    role_senior = models.ResourceRole(name="Senior Consultant")
    role_consultant = models.ResourceRole(name="Consultant")
    db.add_all([role_senior, role_consultant])
    db.flush()

    for period, senior_fte, consultant_fte in (("Okt 26", 0.8, 0.7), ("Nov 26", 1.0, 0.5)):
        d1 = models.ResourceDemand(
            project_id=project.id, plan_phase_id=None, resource_role_id=role_senior.id,
            period=period, fte=senior_fte, erstellt_am=now, aktualisiert_am=now,
        )
        d2 = models.ResourceDemand(
            project_id=project.id, plan_phase_id=None, resource_role_id=role_consultant.id,
            period=period, fte=consultant_fte, erstellt_am=now, aktualisiert_am=now,
        )
        db.add_all([d1, d2])
        db.flush()
        person = db.query(models.Person).filter(models.Person.display_name == "Dominik").first()
        if person is None:
            person = models.Person(display_name="Dominik")
            db.add(person)
            db.flush()
        db.add(
            models.ResourceAssignment(
                resource_demand_id=d1.id, person_id=person.id, fte=senior_fte,
                erstellt_am=now, aktualisiert_am=now,
            )
        )

    db.commit()
    return project


def main() -> None:
    print("1/4  Alembic-Upgrade auf head (inkl. B-1-Schema) ...")
    _alembic_upgrade_head()

    print("2/4  Testdaten seeden (Subproject + Grobplanung, 2 Perioden) ...")
    db = SessionLocal()
    project = _seed_test_project(db)
    project_id = project.id

    milestones_before = db.query(models.Milestone).filter(models.Milestone.project_id == project_id).count()
    comments_before = db.query(models.Comment).filter(models.Comment.project_id == project_id).count()
    assignments_before = db.query(models.ResourceAssignment).count()
    demands_before = db.query(models.ResourceDemand).filter(models.ResourceDemand.project_id == project_id).count()
    phases_before = db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id).count()

    print("3/4  Dry-Run ausführen und Nicht-Schreiben verifizieren ...")
    report = migrate(db, apply=False)
    if report.has_discrepancies:
        _fail("Dry-Run", f"Report zeigt Diskrepanzen: {report.projects}")
    entry = next((p for p in report.projects if p.project_id == project_id), None)
    if entry is None:
        _fail("Dry-Run", "Testprojekt fehlt im Report")
    if entry.subprojects_migrated != 1:
        _fail("Dry-Run", f"subprojects_migrated={entry.subprojects_migrated}, erwartet 1")
    if entry.subproject_children_reparented != 2:
        _fail("Dry-Run", f"subproject_children_reparented={entry.subproject_children_reparented}, erwartet 2")
    if entry.grobplanung_month_leaves_created != 2:
        _fail("Dry-Run", f"grobplanung_month_leaves_created={entry.grobplanung_month_leaves_created}, erwartet 2")
    if entry.resource_demands_reassigned != 4:
        _fail("Dry-Run", f"resource_demands_reassigned={entry.resource_demands_reassigned}, erwartet 4")
    if round(entry.fte_sum_before, 4) != round(0.8 + 0.7 + 1.0 + 0.5, 4):
        _fail("Dry-Run", f"fte_sum_before={entry.fte_sum_before}, erwartet 3.0")

    phases_after_dry_run = db.query(models.PlanPhase).filter(models.PlanPhase.project_id == project_id).count()
    if phases_after_dry_run != phases_before:
        _fail(
            "Dry-Run-Isolation",
            f"PlanPhase-Anzahl änderte sich trotz Dry-Run: {phases_before} -> {phases_after_dry_run}",
        )
    demands_still_unassigned = (
        db.query(models.ResourceDemand)
        .filter(models.ResourceDemand.project_id == project_id, models.ResourceDemand.plan_phase_id.is_(None))
        .count()
    )
    if demands_still_unassigned != 4:
        _fail(
            "Dry-Run-Isolation",
            f"ResourceDemands mit plan_phase_id IS NULL nach Dry-Run: {demands_still_unassigned}, erwartet 4",
        )

    print("4/4  Apply-Lauf ausführen und Invarianten prüfen ...")
    report = migrate(db, apply=True)
    if report.has_discrepancies:
        _fail("Apply", f"Report zeigt Diskrepanzen: {report.projects}")

    milestones_after = db.query(models.Milestone).filter(models.Milestone.project_id == project_id).count()
    comments_after = db.query(models.Comment).filter(models.Comment.project_id == project_id).count()
    assignments_after = db.query(models.ResourceAssignment).count()
    demands_after = db.query(models.ResourceDemand).filter(models.ResourceDemand.project_id == project_id).count()
    orphan_demands_after = (
        db.query(models.ResourceDemand)
        .filter(models.ResourceDemand.project_id == project_id, models.ResourceDemand.plan_phase_id.is_(None))
        .count()
    )

    if milestones_after != milestones_before:
        _fail("Apply", f"Milestones vorher/nachher: {milestones_before} -> {milestones_after}")
    if comments_after != comments_before:
        _fail("Apply", f"Comments vorher/nachher: {comments_before} -> {comments_after}")
    if assignments_after != assignments_before:
        _fail("Apply", f"ResourceAssignments vorher/nachher: {assignments_before} -> {assignments_after}")
    if demands_after != demands_before:
        _fail("Apply", f"ResourceDemands vorher/nachher: {demands_before} -> {demands_after} (Zeilen dürfen nicht verloren gehen)")
    if orphan_demands_after != 0:
        _fail("Apply", f"Verwaiste ResourceDemands nach Migration: {orphan_demands_after}, erwartet 0")

    # Subproject-Kinder müssen jetzt einen Parent haben, dessen Zeitraum sich aus ihnen ableiten
    # ließe (hier nur strukturell geprüft: parent_phase_id gesetzt, kein NULL mehr).
    unparented_children = (
        db.query(models.PlanPhase)
        .filter(models.PlanPhase.project_id == project_id, models.PlanPhase.subproject_id.isnot(None))
        .filter(models.PlanPhase.parent_phase_id.is_(None))
        .count()
    )
    if unparented_children != 0:
        _fail("Apply", f"{unparented_children} PlanPhase(s) mit subproject_id, aber ohne parent_phase_id")

    milestone_reparented = (
        db.query(models.Milestone)
        .filter(models.Milestone.project_id == project_id, models.Milestone.plan_phase_id.isnot(None))
        .count()
    )
    if milestone_reparented != 1:
        _fail("Apply", f"Milestone.plan_phase_id gesetzt bei {milestone_reparented}, erwartet 1")

    comment_reparented = (
        db.query(models.Comment)
        .filter(models.Comment.project_id == project_id, models.Comment.plan_phase_id.isnot(None))
        .count()
    )
    if comment_reparented != 1:
        _fail("Apply", f"Comment.plan_phase_id gesetzt bei {comment_reparented}, erwartet 1")

    print("    Re-Run nach Apply: nichts mehr zu migrieren ...")
    rerun_report = migrate(db, apply=True)
    rerun_entry = next((p for p in rerun_report.projects if p.project_id == project_id), None)
    if rerun_entry is not None:
        _fail("Idempotenz", "Testprojekt taucht nach erfolgreicher Migration erneut im Report auf")

    db.close()
    print(f"OK — Dry-Run isoliert, Apply verlustfrei ({phases_before} Phasen vorher, "
          f"kein Datenverlust bei Milestones/Comments/Assignments/Demands), Re-Run idempotent.")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()
        _tmp.cleanup()
