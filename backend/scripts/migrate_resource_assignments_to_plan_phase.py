"""P20.1: Migrationstooling ResourceAssignment -> direkte PlanPhase-Zuordnung
(CONCEPT.md Abschnitt 12/6c, Auftrag Abschnitt 3/13/34).

Reines Daten-Migrationsskript, KEIN Alembic-Bestandteil - setzt die additive Schema-Grundlage
(0007_p20_1_direct_plan_phase_assignment: resource_assignments.plan_phase_id) voraus.

Analysiert jede bestehende ResourceAssignment-Zeile mit gesetztem resource_demand_id und noch
leerem plan_phase_id:

  ResourceAssignment -> ResourceDemand -> plan_phase_id

Ist diese Kette eindeutig auflösbar und würde die neue Zuordnung keinen bestehenden direkten
Assignment-Datensatz derselben Phase/Person duplizieren, wird
`ResourceAssignment.plan_phase_id` GESETZT (nicht ERSETZT - `resource_demand_id` bleibt
unverändert als Compat-Verweis stehen, siehe Auftrag Abschnitt 3 Schritt 3/4: "resource_demand_id
zunächst Compat/nullable erhalten"). Kein Zeile wird geraten oder gelöscht - uneindeutige
Fälle werden nur reportet:

  - legacy_unmapped: ResourceDemand existiert, aber ohne plan_phase_id (alte projektweite
    Grobplanung, siehe ResourceDemandGrid.tsx) - kann nicht automatisch einer Phase zugeordnet
    werden.
  - conflicts: die Ziel-Kombination (plan_phase_id, person_id) existiert bereits als direkte
    Zuordnung (uq_resource_assignments_phase_person) - würde diese Migration angewendet, gäbe
    es zwei Datensätze für dieselbe Person auf derselben Phase. Wird übersprungen, nicht
    zusammengeführt (keine stille Datenkorrektur, Auftrag Abschnitt 13).
  - orphans: resource_demand_id verweist auf keine (mehr) existierende ResourceDemand-Zeile
    (Dateninkonsistenz, sollte durch die FK normalerweise nicht vorkommen).
  - already_direct: plan_phase_id war bereits gesetzt (macht den Lauf idempotent - ein
    zweiter Aufruf gegen bereits migrierte Daten migriert nichts erneut).

WICHTIG - Sicherheitsdefault: Ohne --apply läuft dieses Skript ausschließlich als Dry-Run -
alle Änderungen werden im Speicher berechnet und reportet, am Ende steht ein expliziter
ROLLBACK (keine Zeile wird geschrieben). Nur mit --apply wird tatsächlich committet. Es gibt
KEINEN automatischen Produktivlauf (CONCEPT.md Migrations-Policy, Abschnitt 12.1) - Ausführung
gegen echte Produktivdaten erfordert eine gesonderte Freigabe außerhalb dieses Pakets.

Aufruf (aus dem Repo-Root oder `backend/`):

    python backend/scripts/migrate_resource_assignments_to_plan_phase.py                # Dry-Run
    python backend/scripts/migrate_resource_assignments_to_plan_phase.py --apply         # schreibt wirklich
    python backend/scripts/migrate_resource_assignments_to_plan_phase.py --database-url sqlite:///pfad.db
    python backend/scripts/migrate_resource_assignments_to_plan_phase.py --report-file report.json

Beendet sich mit Exit-Code 0 bei Erfolg (Report ohne Diskrepanzen), sonst 1.
"""

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConflictEntry:
    assignment_id: int
    person_id: int
    plan_phase_id: int
    reason: str


@dataclass
class MigrationReport:
    dry_run: bool
    assignments_total: int = 0
    migrated_to_plan_phase: int = 0
    already_direct: int = 0
    legacy_unmapped: int = 0
    conflicts: int = 0
    orphans: int = 0
    conflict_details: list[ConflictEntry] = field(default_factory=list)

    @property
    def has_discrepancies(self) -> bool:
        # Erfolgreicher Lauf = alle eligiblen Zeilen sind entweder migriert oder schlüssig
        # kategorisiert (legacy_unmapped/conflicts/orphans/already_direct) - die Summe muss
        # exakt der Gesamtzahl entsprechen, sonst wäre eine Zeile "verschwunden".
        accounted = (
            self.migrated_to_plan_phase
            + self.already_direct
            + self.legacy_unmapped
            + self.conflicts
            + self.orphans
        )
        return accounted != self.assignments_total


def migrate(db, apply: bool) -> MigrationReport:
    from app import models

    report = MigrationReport(dry_run=not apply)

    assignments = db.query(models.ResourceAssignment).order_by(models.ResourceAssignment.id).all()
    report.assignments_total = len(assignments)

    # Bereits vergebene (plan_phase_id, person_id)-Kombinationen VORAB einsammeln (inkl.
    # bereits direkter Zuordnungen), damit die Konfliktprüfung nicht versehentlich zwei frisch
    # migrierte Zeilen im selben Lauf gegeneinander laufen lässt.
    taken_phase_person: set[tuple[int, int]] = {
        (a.plan_phase_id, a.person_id) for a in assignments if a.plan_phase_id is not None
    }

    for assignment in assignments:
        if assignment.plan_phase_id is not None:
            report.already_direct += 1
            continue
        if assignment.resource_demand_id is None:
            # Durch ck_resource_assignments_has_target ausgeschlossen, defensiv trotzdem
            # behandelt statt eine Exception zu riskieren.
            report.orphans += 1
            continue

        demand = db.get(models.ResourceDemand, assignment.resource_demand_id)
        if demand is None:
            report.orphans += 1
            continue
        if demand.plan_phase_id is None:
            report.legacy_unmapped += 1
            continue

        target = (demand.plan_phase_id, assignment.person_id)
        if target in taken_phase_person:
            report.conflicts += 1
            report.conflict_details.append(
                ConflictEntry(
                    assignment_id=assignment.id,
                    person_id=assignment.person_id,
                    plan_phase_id=demand.plan_phase_id,
                    reason="uq_resource_assignments_phase_person würde verletzt (Person bereits "
                    "direkt dieser Phase zugeordnet)",
                )
            )
            continue

        assignment.plan_phase_id = demand.plan_phase_id
        assignment.aktualisiert_am = _now()
        taken_phase_person.add(target)
        report.migrated_to_plan_phase += 1

    db.flush()

    if apply:
        db.commit()
    else:
        db.rollback()

    return report


def _print_report(report: MigrationReport) -> None:
    mode = "DRY-RUN (keine Zeile geschrieben, Rollback ausgeführt)" if report.dry_run else "APPLY (committet)"
    print(f"=== ResourceAssignment -> PlanPhase Migrationsreport [{mode}] ===")
    print(f"assignments_total:      {report.assignments_total}")
    print(f"migrated_to_plan_phase: {report.migrated_to_plan_phase}")
    print(f"already_direct:         {report.already_direct}")
    print(f"legacy_unmapped:        {report.legacy_unmapped}")
    print(f"conflicts:              {report.conflicts}")
    print(f"orphans:                {report.orphans}")
    if report.conflict_details:
        print("\nKonflikte (nicht migriert, manuell prüfen):")
        for c in report.conflict_details:
            print(f"  - assignment_id={c.assignment_id} person_id={c.person_id} plan_phase_id={c.plan_phase_id}: {c.reason}")
    print(f"\nDiskrepanzen gefunden: {report.has_discrepancies}")


def _write_report_file(report: MigrationReport, path: Path) -> None:
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
        help="Pfad, unter dem der vollständige Report zusätzlich als JSON gespeichert wird.",
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
