"""Align projects.reihenfolge/status auf das Modell (NOT NULL).

Revision ID: 0002_align_project_nullable
Revises: 0001_consolidated
Create Date: 2026-08-17 23:40:00.000000

Bestandsschiefstand aus der Zeit vor dem Migrations-Check: Die bestehende DEV-/Comp-
PG-Datenbank hat `projects.reihenfolge` und `projects.status` als nullable angelegt,
während `models.py` beiden Spalten NOT NULL verlangt (Mapped[int] ohne | None). Auf
frischen DBs (konsolidierte Baseline) trat der Unterschied nie auf; `alembic check`
auf der Alt-DB meldete den modifizierten Drift. Diese Revision gleicht die Alt-DB an
und ist auf frischen DBs ein No-Op.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_align_project_nullable"
down_revision: Union[str, Sequence[str], None] = "0001_consolidated"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Gleiche die Alt-DB an: beide Spalten sind im Modell NOT NULL."""
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.alter_column(
            "reihenfolge", existing_type=sa.Integer(), existing_nullable=True, nullable=False
        )
        batch_op.alter_column(
            "status", existing_type=sa.String(length=20), existing_nullable=True, nullable=False
        )


def downgrade() -> None:
    """Rückgängig: Spalten wieder nullable (kein Daten-Reset nötig)."""
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.alter_column(
            "reihenfolge", existing_type=sa.Integer(), existing_nullable=False, nullable=True
        )
        batch_op.alter_column(
            "status", existing_type=sa.String(length=20), existing_nullable=False, nullable=True
        )