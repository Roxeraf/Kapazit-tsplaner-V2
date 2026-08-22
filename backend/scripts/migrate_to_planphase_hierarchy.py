"""P18/B-2: Migrationstooling PlanPhase-only-Hierarchie (CONCEPT.md Abschnitt 6b.7/6b.12,
P18_ARCHITECTURE_RECONCILIATION_PASS2.md Abschnitt 22/35.2, Paket B-2).

Reines Daten-Migrationsskript, KEIN Alembic-Bestandteil - setzt Paket B-1 (additive
Schema-Grundlage: PlanPhase.parent_phase_id/reihenfolge, Milestone.plan_phase_id) voraus.

Migriert je Projekt, additiv und ohne Informationsverlust:

  (a) Subprojects  -> je eine neue Top-Level-Parent-PlanPhase (phase_type = Subproject.name,
      reihenfolge = Subproject.reihenfolge). Bestehende PlanPhase-Kinder (subproject_id = sp.id)
      werden reparented (parent_phase_id = neue Phase), Milestones umgehängt
      (plan_phase_id = neue Phase), bislang unverknüpfte Comments (subproject_id = sp.id,
      plan_phase_id IS NULL) ebenfalls. subprojects/subproject_id bleiben unverändert bestehen
      (compat-only, kein Schema-Drop).
  (b) Grobplanung  -> neue Top-Level-Parent-PlanPhase "Grobplanung (migriert)" pro Projekt mit
      mindestens einer ResourceDemand(plan_phase_id IS NULL)-Zeile, plus eine Monats-Leaf-
      PlanPhase je distinkter Periode ("Grobplanung <Monat> <Jahr>", Zeitraum = Kalendermonat).
      plan_fte der Leaf-Phase wird EINMALIG (nur für diesen Migrationsschritt, keine neue
      Laufzeitregel) aus SUM(ResourceDemand.fte) dieser Periode abgeleitet. Alle
      ResourceDemand-Zeilen dieser Periode werden auf die neue Leaf-Phase umgehängt
      (plan_phase_id gesetzt, period bleibt unverändert).
  (c) ResourceAssignment bleibt vollständig unberührt - hängt nur an resource_demand_id, nicht
      an plan_phase_id (Abschnitt 21).
  (d) PlanHistory-Zeilen (Audit-Log) werden NICHT rückwirkend umgeschrieben.

WICHTIG - Sicherheitsdefault: Ohne --apply läuft dieses Skript ausschließlich als Dry-Run -
alle Änderungen werden im Speicher berechnet und reportet, am Ende steht ein expliziter
ROLLBACK (keine Zeile wird geschrieben). Nur mit --apply wird tatsächlich committet. Es gibt
KEINEN automatischen Produktivlauf (CONCEPT.md Migrations-Policy, Abschnitt 12.1) -
Ausführung gegen echte Produktivdaten erfordert eine gesonderte Freigabe außerhalb dieses
Pakets (B-2 Definition of Done).

Aufruf (aus dem Repo-Root oder `backend/`):

    python backend/scripts/migrate_to_planphase_hierarchy.py                  # Dry-Run (Default)
    python backend/scripts/migrate_to_planphase_hierarchy.py --apply          # schreibt wirklich
    python backend/scripts/migrate_to_planphase_hierarchy.py --database-url sqlite:///pfad.db

Beendet sich mit Exit-Code 0 bei Erfolg (Report ohne Diskrepanzen), sonst 1.
"""

import argparse
import calendar
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


_MONAT_VOLLNAME = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProjectMigrationEntry:
    project_id: int
    project_name: str
    subprojects_migrated: int = 0
    subproject_children_reparented: int = 0
    subproject_milestones_relinked: int = 0
    subproject_comments_relinked: int = 0
    grobplanung_phase_created: bool = False
    grobplanung_month_leaves_created: int = 0
    resource_demands_reassigned: int = 0
    resource_assignments_on_reassigned_demands: int = 0
    fte_sum_before: float = 0.0
    fte_sum_after: float = 0.0
    orphan_resource_demands_after: int = 0
    milestones_before: int = 0
    milestones_after: int = 0
    comments_relinked_total_before: int = 0
    # P18.1 Stabilization (CONCEPT.md Abschnitt 16.16, Migration Realistic Dry-Run
    # Preparation, Auftrag Abschnitt 6/7): ResourceAssignment hängt nur an resource_demand_id
    # (siehe Klassendoku oben, Punkt c) und wird durch die Migration nie direkt verändert -
    # Anzahl UND FTE-Summe müssen vor/nach der Migration exakt identisch sein. Ergänzt die
    # bisherige "resource_assignments_on_reassigned_demands"-Zählung (nur die migrierten
    # Demands) um eine vollständige Vorher/Nachher-Prüfung über ALLE Assignments des Projekts.
    assignments_count_before: int = 0
    assignments_count_after: int = 0
    assignments_fte_sum_before: float = 0.0
    assignments_fte_sum_after: float = 0.0


@dataclass
class MigrationReport:
    dry_run: bool
    projects: list[ProjectMigrationEntry] = field(default_factory=list)
    hierarchy_depth_violations: list[str] = field(default_factory=list)

    @property
    def has_discrepancies(self) -> bool:
        if self.hierarchy_depth_violations:
            return True
        for p in self.projects:
            if p.orphan_resource_demands_after != 0:
                return True
            if round(p.fte_sum_before, 4) != round(p.fte_sum_after, 4):
                return True
            if p.assignments_count_before != p.assignments_count_after:
                return True
            if round(p.assignments_fte_sum_before, 4) != round(p.assignments_fte_sum_after, 4):
                return True
            if p.milestones_before != p.milestones_after:
                return True
        return False


def _migrate_subprojects(db, project, entry: "ProjectMigrationEntry") -> None:
    from app import models

    subprojects = (
        db.query(models.Subproject)
        .filter(models.Subproject.project_id == project.id)
        .order_by(models.Subproject.reihenfolge)
        .all()
    )
    for sp in subprojects:
        # Kinder VOR dem Anlegen der neuen Phase einsammeln, damit die neue Parent-Phase
        # selbst nicht versehentlich in die eigene Reparenting-Query gerät. Gefiltert auf
        # "noch nicht reparented/relinked" (parent_phase_id/plan_phase_id IS NULL) - das
        # macht den Lauf idempotent: ein zweiter Aufruf gegen bereits migrierte Daten findet
        # nichts mehr und legt keine doppelte Parent-Phase an.
        child_phase_ids = [
            row[0]
            for row in db.query(models.PlanPhase.id)
            .filter(
                models.PlanPhase.subproject_id == sp.id,
                models.PlanPhase.parent_phase_id.is_(None),
            )
            .all()
        ]
        milestone_ids = [
            row[0]
            for row in db.query(models.Milestone.id)
            .filter(
                models.Milestone.subproject_id == sp.id,
                models.Milestone.plan_phase_id.is_(None),
            )
            .all()
        ]
        comment_ids = [
            row[0]
            for row in db.query(models.Comment.id)
            .filter(
                models.Comment.subproject_id == sp.id,
                models.Comment.plan_phase_id.is_(None),
            )
            .all()
        ]
        if not child_phase_ids and not milestone_ids and not comment_ids:
            continue  # bereits vollständig migriert (idempotent) - nichts zu tun

        now = _now()
        parent_phase = models.PlanPhase(
            project_id=project.id,
            subproject_id=None,
            parent_phase_id=None,
            reihenfolge=sp.reihenfolge,
            phase_type=sp.name,
            forecast_start=None,
            forecast_end=None,
            status="geplant",
            plan_fte=None,
            erstellt_am=now,
            aktualisiert_am=now,
        )
        db.add(parent_phase)
        db.flush()

        if child_phase_ids:
            db.query(models.PlanPhase).filter(models.PlanPhase.id.in_(child_phase_ids)).update(
                {"parent_phase_id": parent_phase.id}, synchronize_session=False
            )
        if milestone_ids:
            db.query(models.Milestone).filter(models.Milestone.id.in_(milestone_ids)).update(
                {"plan_phase_id": parent_phase.id, "aktualisiert_am": now}, synchronize_session=False
            )
        if comment_ids:
            db.query(models.Comment).filter(models.Comment.id.in_(comment_ids)).update(
                {"plan_phase_id": parent_phase.id}, synchronize_session=False
            )

        entry.subprojects_migrated += 1
        entry.subproject_children_reparented += len(child_phase_ids)
        entry.subproject_milestones_relinked += len(milestone_ids)
        entry.subproject_comments_relinked += len(comment_ids)


def _migrate_grobplanung(db, project, entry: "ProjectMigrationEntry") -> None:
    from app import models
    from app.constants import parse_period

    periods = sorted(
        {
            row[0]
            for row in db.query(models.ResourceDemand.period)
            .filter(
                models.ResourceDemand.project_id == project.id,
                models.ResourceDemand.plan_phase_id.is_(None),
            )
            .distinct()
            .all()
        },
        key=parse_period,
    )
    if not periods:
        return

    now = _now()
    parent_phase = models.PlanPhase(
        project_id=project.id,
        subproject_id=None,
        parent_phase_id=None,
        reihenfolge=0,
        phase_type="Grobplanung (migriert)",
        forecast_start=None,
        forecast_end=None,
        status="geplant",
        plan_fte=None,
        erstellt_am=now,
        aktualisiert_am=now,
    )
    db.add(parent_phase)
    db.flush()
    entry.grobplanung_phase_created = True

    for idx, period in enumerate(periods):
        year, month = parse_period(period)
        _, days_in_month = calendar.monthrange(year, month)
        month_start = f"{year:04d}-{month:02d}-01"
        month_end = f"{year:04d}-{month:02d}-{days_in_month:02d}"

        demand_rows = (
            db.query(models.ResourceDemand)
            .filter(
                models.ResourceDemand.project_id == project.id,
                models.ResourceDemand.plan_phase_id.is_(None),
                models.ResourceDemand.period == period,
            )
            .all()
        )
        sum_fte = round(sum(d.fte for d in demand_rows), 2)
        assignment_count = (
            db.query(models.ResourceAssignment)
            .filter(
                models.ResourceAssignment.resource_demand_id.in_([d.id for d in demand_rows])
            )
            .count()
            if demand_rows
            else 0
        )

        leaf_phase = models.PlanPhase(
            project_id=project.id,
            subproject_id=None,
            parent_phase_id=parent_phase.id,
            reihenfolge=idx,
            phase_type=f"Grobplanung {_MONAT_VOLLNAME[month - 1]} {year}",
            forecast_start=month_start,
            forecast_end=month_end,
            status="geplant",
            plan_fte=sum_fte,
            erstellt_am=now,
            aktualisiert_am=now,
        )
        db.add(leaf_phase)
        db.flush()

        demand_ids = [d.id for d in demand_rows]
        if demand_ids:
            db.query(models.ResourceDemand).filter(models.ResourceDemand.id.in_(demand_ids)).update(
                {"plan_phase_id": leaf_phase.id, "aktualisiert_am": now}, synchronize_session=False
            )

        entry.grobplanung_month_leaves_created += 1
        entry.resource_demands_reassigned += len(demand_ids)
        entry.resource_assignments_on_reassigned_demands += assignment_count
        entry.fte_sum_after += sum_fte


def _compute_hierarchy_depth_violations(db) -> list[str]:
    """Wandert für jede PlanPhase die parent_phase_id-Kette hoch und meldet jede Phase mit
    Tiefe > 3 (BD-10, CLOSED) sowie jeden Zyklus. Generischer Check über den gesamten
    Datenbestand, nicht nur die in diesem Lauf neu angelegten Phasen (BD-12: Hierarchietiefe-
    Checks als Teil des Migrationsreports)."""
    from app import models

    rows = db.query(models.PlanPhase.id, models.PlanPhase.parent_phase_id).all()
    parent_of = {pid: parent_id for pid, parent_id in rows}
    violations: list[str] = []
    for pid in parent_of:
        seen: set[int] = set()
        current = pid
        depth = 1
        while parent_of.get(current) is not None:
            current = parent_of[current]
            if current in seen:
                violations.append(f"PlanPhase {pid}: Zyklus in parent_phase_id-Kette entdeckt")
                break
            seen.add(current)
            depth += 1
            if depth > 3:
                violations.append(f"PlanPhase {pid}: Hierarchietiefe {depth} > 3 (BD-10)")
                break
    return violations


def _project_assignment_stats(db, project_id: int) -> tuple[int, float]:
    """Anzahl und FTE-Summe aller ResourceAssignments eines Projekts (über den Join auf
    ResourceDemand, da ResourceAssignment keinen eigenen project_id-FK trägt) - für den
    Vorher/Nachher-Vergleich in migrate() (Auftrag Abschnitt 7: "Assignments preserved")."""
    from app import models

    rows = (
        db.query(models.ResourceAssignment.fte)
        .join(models.ResourceDemand, models.ResourceDemand.id == models.ResourceAssignment.resource_demand_id)
        .filter(models.ResourceDemand.project_id == project_id)
        .all()
    )
    return len(rows), round(sum(row[0] for row in rows), 4)


def migrate(db, apply: bool) -> MigrationReport:
    from app import models

    report = MigrationReport(dry_run=not apply)
    projects = db.query(models.Project).order_by(models.Project.id).all()

    for project in projects:
        entry = ProjectMigrationEntry(project_id=project.id, project_name=project.name)

        entry.milestones_before = (
            db.query(models.Milestone).filter(models.Milestone.project_id == project.id).count()
        )
        grobplanung_fte_before = [
            row[0]
            for row in db.query(models.ResourceDemand.fte)
            .filter(
                models.ResourceDemand.project_id == project.id,
                models.ResourceDemand.plan_phase_id.is_(None),
            )
            .all()
        ]
        entry.fte_sum_before = round(sum(grobplanung_fte_before), 4)
        entry.assignments_count_before, entry.assignments_fte_sum_before = _project_assignment_stats(db, project.id)

        has_subprojects = (
            db.query(models.Subproject).filter(models.Subproject.project_id == project.id).count() > 0
        )
        has_grobplanung = (
            db.query(models.ResourceDemand)
            .filter(
                models.ResourceDemand.project_id == project.id,
                models.ResourceDemand.plan_phase_id.is_(None),
            )
            .count()
            > 0
        )
        if not has_subprojects and not has_grobplanung:
            continue  # nichts zu migrieren fuer dieses Projekt - kein Report-Eintrag noetig

        if has_subprojects:
            _migrate_subprojects(db, project, entry)
        if has_grobplanung:
            _migrate_grobplanung(db, project, entry)

        entry.orphan_resource_demands_after = (
            db.query(models.ResourceDemand)
            .filter(
                models.ResourceDemand.project_id == project.id,
                models.ResourceDemand.plan_phase_id.is_(None),
            )
            .count()
        )
        entry.milestones_after = (
            db.query(models.Milestone).filter(models.Milestone.project_id == project.id).count()
        )
        entry.assignments_count_after, entry.assignments_fte_sum_after = _project_assignment_stats(db, project.id)
        if entry.subprojects_migrated == 0 and not entry.grobplanung_phase_created:
            continue  # has_subprojects/has_grobplanung war True, aber bereits vollständig
            # migriert (idempotent Re-Run) - kein Report-Eintrag, da keine Aktion stattfand.
        report.projects.append(entry)

    db.flush()
    report.hierarchy_depth_violations = _compute_hierarchy_depth_violations(db)

    if apply:
        db.commit()
    else:
        db.rollback()

    return report


def _print_report(report: MigrationReport) -> None:
    mode = "DRY-RUN (keine Zeile geschrieben, Rollback ausgeführt)" if report.dry_run else "APPLY (committet)"
    print(f"=== Migrationsreport [{mode}] ===")
    if not report.projects:
        print("Keine Projekte mit migrationsbedürftigen Subprojects/Grobplanung gefunden.")
    for p in report.projects:
        print(f"\nProjekt {p.project_id} — {p.project_name}")
        print(
            f"  Subprojects migriert: {p.subprojects_migrated} "
            f"(Kinder reparented: {p.subproject_children_reparented}, "
            f"Milestones umgehängt: {p.subproject_milestones_relinked}, "
            f"Comments umgehängt: {p.subproject_comments_relinked})"
        )
        print(
            f"  Grobplanung migriert: {p.grobplanung_phase_created} "
            f"({p.grobplanung_month_leaves_created} Monats-Leaf-Phasen, "
            f"{p.resource_demands_reassigned} ResourceDemands umgehängt, "
            f"{p.resource_assignments_on_reassigned_demands} ResourceAssignments unberührt "
            f"mitgewandert)"
        )
        print(f"  FTE-Summe (Grobplanung) vorher/nachher: {p.fte_sum_before} / {p.fte_sum_after}")
        print(f"  Milestones vorher/nachher: {p.milestones_before} / {p.milestones_after}")
        print(f"  Verwaiste ResourceDemands (plan_phase_id IS NULL) danach: {p.orphan_resource_demands_after}")
        print(
            f"  ResourceAssignments vorher/nachher: {p.assignments_count_before}/{p.assignments_count_after} "
            f"Zeilen, {p.assignments_fte_sum_before}/{p.assignments_fte_sum_after} FTE-Summe"
        )
    if report.hierarchy_depth_violations:
        print("\nHierarchietiefe-/Zyklus-Verstöße:")
        for v in report.hierarchy_depth_violations:
            print(f"  - {v}")
    print(f"\nDiskrepanzen gefunden: {report.has_discrepancies}")


def _write_report_file(report: MigrationReport, path: Path) -> None:
    """P18.1 Stabilization (CONCEPT.md Abschnitt 16.16, Auftrag Abschnitt 6 Step 4: "Report
    speichern") - JSON-Serialisierung des vollständigen Reports (dataclasses.asdict), damit
    ein realistischer Dry-Run-Lauf gegen eine Produktivkopie ein archivierbares Artefakt
    hinterlässt statt nur Stdout-Text."""
    import dataclasses
    import json

    payload = dataclasses.asdict(report)
    payload["generated_at"] = _now()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Schreibt die Migration wirklich (committet). Ohne dieses Flag: reiner Dry-Run.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy-Connection-String. Default: DATABASE_URL-Umgebungsvariable bzw. "
        "app.database-Default (kapazitaetsplaner.db).",
    )
    parser.add_argument(
        "--report-file",
        default=None,
        help="Pfad, unter dem der vollständige Report zusätzlich als JSON gespeichert wird "
        "(P18.1 Stabilization, Migration Realistic Dry-Run Preparation Step 4).",
    )
    args = parser.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    from app.database import SessionLocal  # noqa: E402 - Import erst nach DATABASE_URL-Setup

    db = SessionLocal()
    try:
        report = migrate(db, apply=args.apply)
    finally:
        db.close()

    _print_report(report)
    if args.report_file:
        _write_report_file(report, Path(args.report_file))
        print(f"\nReport gespeichert unter: {args.report_file}")
    sys.exit(1 if report.has_discrepancies else 0)


if __name__ == "__main__":
    main()
