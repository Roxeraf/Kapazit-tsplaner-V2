"""P20.3: additive PlanHistory-Identifikationsspalten.

Revision ID: 0008_p20_3_plan_history
Revises: 0007_p20_1_direct_assignment
Create Date: 2026-08-24 00:00:00.000000

Additiv, nicht-destruktiv (CONCEPT.md Abschnitt 12.1). Kein Drop von BaselineSnapshot/
BaselineEntry. Erweitert plan_history um optionale Spalten, damit ein History-Eintrag
entity_type/entity_id/entity_label/action/actor ausdruecken kann, ohne die bestehenden
Feld-Diff-Spalten (feld/alter_wert/neuer_wert/batch_id) zu ersetzen.

Bestehende Zeilen bleiben unveraendert lesbar (neue Spalten nullable). actor_person_id
ist bewusst nullable: das Repo hat kein Auth-System.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_p20_3_plan_history"
down_revision: Union[str, None] = "0007_p20_1_direct_assignment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - rein additiv."""
    with op.batch_alter_table("plan_history", schema=None) as batch_op:
        batch_op.add_column(sa.Column("entity_type", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("entity_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("entity_label", sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column("action", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("actor_person_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_plan_history_actor_person_id",
            "persons",
            ["actor_person_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema - rein strukturell, keine Datenwiederherstellung."""
    with op.batch_alter_table("plan_history", schema=None) as batch_op:
        batch_op.drop_constraint("fk_plan_history_actor_person_id", type_="foreignkey")
        batch_op.drop_column("actor_person_id")
        batch_op.drop_column("action")
        batch_op.drop_column("entity_label")
        batch_op.drop_column("entity_id")
        batch_op.drop_column("entity_type")
