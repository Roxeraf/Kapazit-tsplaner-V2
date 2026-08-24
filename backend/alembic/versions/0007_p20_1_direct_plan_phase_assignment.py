"""P20.1: Direct ResourceAssignment Foundation - resource_assignments.plan_phase_id.

Revision ID: 0007_p20_1_direct_plan_phase_assignment
Revises: 0006_p20_jira_phase_mapping
Create Date: 2026-08-24 00:00:00.000000

Additiv, nicht-destruktiv (siehe CONCEPT.md Abschnitt 12.1 Migrations-Policy). Reine
Schema-Grundlage fuer den P20.1-Zielzustand "ResourceAssignment haengt direkt an der Leaf
PlanPhase" (Auftrag Abschnitt 3): KEINE Backend-Logik-Aenderung, KEINE Datenmigration
bestehender Assignments (siehe scripts/migrate_resource_assignments_to_plan_phase.py, ein
separates, idempotentes Skript - explizit NICHT hier im Upgrade-Pfad ausgefuehrt, um keine
stille Produktivmigration zu erzwingen, Auftrag Abschnitt 34):

1. resource_assignments.plan_phase_id (nullable, FK -> plan_phases.id, ON DELETE CASCADE,
   indiziert) - neuer Standardpfad fuer eine direkte Personenzuordnung ohne ResourceDemand/
   ResourceRole als technische Zwischenebene.
2. resource_assignments.resource_demand_id wird nullable (vorher NOT NULL) - Legacy/Compat,
   ein Assignment traegt ab jetzt GENAU EINEN der beiden FKs (CHECK-Constraint unten).
3. uq_resource_assignments_phase_person (plan_phase_id, person_id) - analog zur bestehenden
   Eindeutigkeit je Demand.
4. ck_resource_assignments_has_target - mindestens einer der beiden FKs muss gesetzt sein
   (nie beide leer).

ON DELETE CASCADE wird hier bewusst NUR fuer die NEUE Spalte gesetzt (frisch angelegter
Constraint, keine Namens-/Dialekt-Fallstricke). Die bestehenden FKs resource_demands.
plan_phase_id und worklog_phase_overrides.plan_phase_id bleiben unveraendert ohne
DB-seitiges ON DELETE (Alt-Constraints ohne Namen aus 0001/0006, ein dialektsicheres
Nachruesten wuerde SQLite-Batch-Rebuild vs. Postgres-Constraint-Rename auseinanderlaufen
lassen) - die eigentliche Delete-Stabilisierung (P20.1G) raeumt diese Zeilen stattdessen
explizit auf Anwendungsebene auf (dialektunabhaengig, identisches Verhalten in SQLite-Tests
und Postgres, siehe Auftrag Abschnitt 25 "keine zufaelligen Unterschiede"), BEVOR eine
PlanPhase geloescht wird - das schliesst den Delete-Bug unabhaengig vom DB-seitigen
ON DELETE-Verhalten.

Technischer Hinweis (wie 0004/0005): FK-Constraints werden bewusst benannt und via
create_foreign_key() angelegt, da SQLite batch_alter_table die Tabelle fuer add_column+FK neu
erstellen muss und dabei benannte Constraints benoetigt.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_p20_1_direct_plan_phase_assignment"
down_revision: Union[str, Sequence[str], None] = "0006_p20_jira_phase_mapping"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - rein additiv."""
    with op.batch_alter_table("resource_assignments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan_phase_id", sa.Integer(), nullable=True))
        batch_op.alter_column("resource_demand_id", existing_type=sa.Integer(), nullable=True)
        batch_op.create_index("ix_resource_assignments_plan_phase_id", ["plan_phase_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_resource_assignments_plan_phase_id",
            "plan_phases",
            ["plan_phase_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_resource_assignments_phase_person", ["plan_phase_id", "person_id"]
        )
        batch_op.create_check_constraint(
            "ck_resource_assignments_has_target",
            "(resource_demand_id IS NOT NULL) OR (plan_phase_id IS NOT NULL)",
        )


def downgrade() -> None:
    """Downgrade schema - rein strukturell. Zeilen, die ausschliesslich plan_phase_id tragen
    (kein resource_demand_id), wuerden nach dem Downgrade die NOT-NULL-Constraint auf
    resource_demand_id verletzen - werden defensiv vor dem Downgrade entfernt (kein
    produktiver Downgrade-Pfad erwartet, analog zu anderen additiven Migrationen dieser
    Kette)."""
    op.get_bind().execute(sa.text("DELETE FROM resource_assignments WHERE resource_demand_id IS NULL"))

    with op.batch_alter_table("resource_assignments", schema=None) as batch_op:
        batch_op.drop_constraint("ck_resource_assignments_has_target", type_="check")
        batch_op.drop_constraint("uq_resource_assignments_phase_person", type_="unique")
        batch_op.drop_constraint("fk_resource_assignments_plan_phase_id", type_="foreignkey")
        batch_op.drop_index("ix_resource_assignments_plan_phase_id")
        batch_op.alter_column("resource_demand_id", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_column("plan_phase_id")
