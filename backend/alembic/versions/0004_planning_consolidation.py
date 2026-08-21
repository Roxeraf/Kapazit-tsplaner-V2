"""P1: Planning Consolidation - additive Spalten + baseline_snapshot EntityType.

Revision ID: 0004_planning_consolidation
Revises: 0003_phase26_legacy_cutover
Create Date: 2026-08-20 00:00:00.000000

Additiv, nicht-destruktiv (siehe CONCEPT.md Abschnitt 12.1 Migrations-Policy):

1. plan_phases.plan_fte (nullable Float) - geplanter FTE-Bedarf je Phase (Phase 19).
2. baseline_snapshots.reason (nullable String(500)) - Begründung des eingefrorenen Planstands.
3. comments/tasks/blockers/decisions.plan_phase_id (je nullable FK -> plan_phases.id,
   ON DELETE SET NULL, mit Index) - Verknüpfung der Kommunikations-Entitäten mit einer
   PlanPhase. ON DELETE SET NULL ist bewusst gewählt: wird eine PlanPhase gelöscht, bleiben
   Kommentar/Aufgabe/Blocker/Entscheidung erhalten (nur die Verknüpfung fällt weg) - kein
   Cascade-Delete von Kollaborationsinhalten. Dies ist die erste ondelete/index-Verwendung
   im Codebase (bewusster, gezielter Scope, kein generelles Retrofit-Muster).

   Technischer Hinweis: Die FK-Constraints werden bewusst benannt (fk_<table>_plan_phase_id)
   und via create_foreign_key() angelegt statt als inline sa.ForeignKey() in sa.Column().
   Grund: SQLite batch_alter_table muss die Tabelle für add_column+FK neu erstellen und
   benötigt dabei benannte Constraints. Der Modell-Code verwendet weiterhin unbenannte
   ForeignKey() (SQLAlchemy-Standard) - alembic check vergleicht FK-Spalten/Referent/ondelete,
   nicht Constraint-Namen, daher kein Drift.

Zeitgleich wird "baseline_snapshot" als EntityType im Tag-/Dokument-/Relations-Layer
registriert (entity_links.py, schemas.py, frontend types.ts) - NICHT im Activity Feed
(analog "document": ein eingefrorener Planstand ist keine Aktivität). Siehe
_ACTIVITY_TIMESTAMP_FIELD-Kommentar in entity_links.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_planning_consolidation"
down_revision: Union[str, Sequence[str], None] = "0003_phase26_legacy_cutover"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - rein additiv."""
    # 1) plan_phases.plan_fte (nullable Float, kein FK, kein Index)
    with op.batch_alter_table("plan_phases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan_fte", sa.Float(), nullable=True))

    # 2) baseline_snapshots.reason (nullable String(500), kein FK, kein Index)
    with op.batch_alter_table("baseline_snapshots", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reason", sa.String(length=500), nullable=True))

    # 3) comments.plan_phase_id (FK -> plan_phases.id, ON DELETE SET NULL, Index)
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan_phase_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_comments_plan_phase_id", ["plan_phase_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_comments_plan_phase_id", "plan_phases", ["plan_phase_id"], ["id"], ondelete="SET NULL"
        )

    # 4) tasks.plan_phase_id
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan_phase_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_tasks_plan_phase_id", ["plan_phase_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_tasks_plan_phase_id", "plan_phases", ["plan_phase_id"], ["id"], ondelete="SET NULL"
        )

    # 5) blockers.plan_phase_id
    with op.batch_alter_table("blockers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan_phase_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_blockers_plan_phase_id", ["plan_phase_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_blockers_plan_phase_id", "plan_phases", ["plan_phase_id"], ["id"], ondelete="SET NULL"
        )

    # 6) decisions.plan_phase_id
    with op.batch_alter_table("decisions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan_phase_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_decisions_plan_phase_id", ["plan_phase_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_decisions_plan_phase_id", "plan_phases", ["plan_phase_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    """Downgrade schema - rein strukturell (keine Datenwiederherstellung nötig, da alle
    neuen Spalten nullable sind und keine bestehenden Daten enthalten)."""
    # Reihenfolge umgekehrt zu upgrade. Benannte FK-Constraints und Indizes zuerst droppen,
    # dann die Spalte.
    with op.batch_alter_table("decisions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_decisions_plan_phase_id", type_="foreignkey")
        batch_op.drop_index("ix_decisions_plan_phase_id")
        batch_op.drop_column("plan_phase_id")

    with op.batch_alter_table("blockers", schema=None) as batch_op:
        batch_op.drop_constraint("fk_blockers_plan_phase_id", type_="foreignkey")
        batch_op.drop_index("ix_blockers_plan_phase_id")
        batch_op.drop_column("plan_phase_id")

    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_constraint("fk_tasks_plan_phase_id", type_="foreignkey")
        batch_op.drop_index("ix_tasks_plan_phase_id")
        batch_op.drop_column("plan_phase_id")

    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.drop_constraint("fk_comments_plan_phase_id", type_="foreignkey")
        batch_op.drop_index("ix_comments_plan_phase_id")
        batch_op.drop_column("plan_phase_id")

    with op.batch_alter_table("baseline_snapshots", schema=None) as batch_op:
        batch_op.drop_column("reason")

    with op.batch_alter_table("plan_phases", schema=None) as batch_op:
        batch_op.drop_column("plan_fte")
