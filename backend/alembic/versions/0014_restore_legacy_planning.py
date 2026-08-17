"""Restore the legacy Gantt/FTE planning tables after the phase 26.9 cutover.

Revision ID: 0014
Revises: 0013
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014"
down_revision: Union[str, Sequence[str], None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("projektleiter", sa.String(length=200), nullable=True))

    op.create_table(
        "project_fte_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("monat", sa.String(length=10), nullable=False),
        sa.Column("wert_soll", sa.Float(), nullable=False),
        sa.UniqueConstraint("project_id", "monat"),
    )
    op.create_table(
        "project_gantt_phases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("monat", sa.String(length=10), nullable=False),
        sa.Column("phase_code", sa.String(length=1), nullable=False),
        sa.UniqueConstraint("project_id", "monat", "phase_code"),
    )
    op.create_table(
        "fte_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subproject_id", sa.Integer(), sa.ForeignKey("subprojects.id"), nullable=False),
        sa.Column("monat", sa.String(length=10), nullable=False),
        sa.Column("wert_soll", sa.Float(), nullable=False),
        sa.UniqueConstraint("subproject_id", "monat"),
    )
    op.create_table(
        "gantt_phases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subproject_id", sa.Integer(), sa.ForeignKey("subprojects.id"), nullable=False),
        sa.Column("monat", sa.String(length=10), nullable=False),
        sa.Column("phase_code", sa.String(length=1), nullable=False),
        sa.UniqueConstraint("subproject_id", "monat", "phase_code"),
    )
    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("jira_account_id", sa.String(length=100), nullable=True),
        sa.Column("wochenstunden", sa.Float(), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("person_id", sa.Integer(), sa.ForeignKey("persons.id"), nullable=True),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_member_id", sa.Integer(), sa.ForeignKey("team_members.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("fte", sa.Float(), nullable=False),
    )

    # Rebuild the compatibility records from the canonical person/resource data. This also
    # restores Jira mappings immediately for databases that already ran the destructive 0013.
    op.execute(sa.text("""
        INSERT INTO team_members (name, jira_account_id, wochenstunden, team_id, person_id)
        SELECT p.display_name, p.jira_account_id, COALESCE(r.weekly_hours, 40), r.team_id, p.id
        FROM persons p LEFT JOIN resource_profiles r ON r.person_id = p.id
        WHERE r.id IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_table("assignments")
    op.drop_table("team_members")
    op.drop_table("gantt_phases")
    op.drop_table("fte_plan")
    op.drop_table("project_gantt_phases")
    op.drop_table("project_fte_plan")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("projektleiter")
