"""P20.5: Phase Actuals, Time Control & Jira/Tempo Auto-Sync.

Revision ID: 0009_p20_5_phase_actuals
Revises: 0008_p20_3_plan_history
Create Date: 2026-08-25 00:00:00.000000

Additiv, nicht-destruktiv (CONCEPT.md Abschnitt 12.1). Zwei Änderungen:

1. `plan_phases` erhält vier neue, nullable Spalten für das automatisch eingefrorene Start
   Commitment (Referenzplan zum Zeitpunkt des tatsächlichen Phasenbeginns, siehe
   P20_5_PHASE_ACTUALS_AND_TIME_CONTROL.md Abschnitt 13) - `actual_start`/`actual_end`
   existieren bereits (P18) und werden nicht strukturell verändert, nur fachlich
   umgewidmet (system-gepflegt statt manuell editierbar, siehe schemas.py).
2. Neue Tabelle `jira_sync_status` (eine Zeile je Projekt) für den Sync-Freshness-Status des
   automatischen Background-Syncs (Abschnitt 8/9).

Revision-ID bewusst < 32 Zeichen (siehe P20_2_REGRESSION_RECOVERY_REPORT.md Abschnitt 2.1 -
Alembics `alembic_version.version_num` ist standardmäßig VARCHAR(32), PostgreSQL erzwingt das
strikt anders als SQLite).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_p20_5_phase_actuals"
down_revision: Union[str, None] = "0008_p20_3_plan_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - rein additiv."""
    with op.batch_alter_table("plan_phases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("commitment_start", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("commitment_end", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("commitment_plan_fte", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("commitment_captured_at", sa.String(length=40), nullable=True))

    op.create_table(
        "jira_sync_status",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.String(length=40), nullable=True),
        sa.Column("last_success_at", sa.String(length=40), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("last_error_at", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_jira_sync_status_project_id"),
        sa.PrimaryKeyConstraint("project_id"),
    )


def downgrade() -> None:
    """Downgrade schema - rein strukturell, keine Datenwiederherstellung."""
    op.drop_table("jira_sync_status")
    with op.batch_alter_table("plan_phases", schema=None) as batch_op:
        batch_op.drop_column("commitment_captured_at")
        batch_op.drop_column("commitment_plan_fte")
        batch_op.drop_column("commitment_end")
        batch_op.drop_column("commitment_start")
