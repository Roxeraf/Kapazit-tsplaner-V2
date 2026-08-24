"""P20.1: Jira/Tempo Mapping Domain - PlanPhase.jira_label, JiraIssueCache,
WorklogPhaseOverride.

Revision ID: 0006_p20_jira_phase_mapping
Revises: 0005_p18_hierarchy_foundation
Create Date: 2026-08-24 00:00:00.000000

Additiv, nicht-destruktiv (siehe CONCEPT.md Abschnitt 12.1 Migrations-Policy). Schema-
Grundlage fuer den Worklog->PlanPhase-Resolver (siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md, BD-1A/B CLOSED) - KEINE Resolver-Logik (folgt
in P20.2), KEIN Backfill bestehender Projekte (kein Migrations-Skript raet ein Mapping fuer
Altprojekte, siehe Abschnitt 27 dort):

1. plan_phases.jira_label (nullable String(200)) - Pendant zu Project.jira_component auf
   Phasenebene, nur auf Leaf-Phasen gepflegt (Backend-Guard analog plan_fte, siehe
   routers/planning.py _maybe_historize_parent_fte). Kein Index (Projektgroesse macht ihn
   nicht noetig, analog Project.jira_component/plan_fte).
2. jira_issue_cache (neue Tabelle) - Issue-Metadaten (Labels/Component/Summary), die der
   Sync bereits abfragt, aber bislang sofort verwarf (CONCEPT.md Abschnitt 4). PK ist der
   Issue-Key selbst (kein Autoincrement noetig, ein Issue existiert genau einmal).
3. worklog_phase_overrides (neue Tabelle) - manuelle Worklog->PlanPhase-Korrektur auf
   Issue-Key-Ebene (BD-1B CLOSED), UNIQUE auf jira_issue_key (ein Override pro Issue, nicht
   pro Worklog-Zeile). Aendert niemals Jira/Tempo-Originaldaten.

Technischer Hinweis (wie 0004/0005): FK-Constraints fuer add_column auf einer bestehenden
Tabelle werden explizit benannt (fk_<table>_<spalte>), da SQLite batch_alter_table die
Tabelle dafuer neu erstellen muss. Fuer brandneue Tabellen (jira_issue_cache,
worklog_phase_overrides) genuegen unbenannte ForeignKeyConstraint (Standardmuster aus
0001_consolidated_baseline) - plan_phases selbst wird nur um eine nullable Spalte ohne FK
erweitert, dafuer reicht ein einfaches add_column ohne FK-Namensproblem.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_p20_jira_phase_mapping"
down_revision: Union[str, Sequence[str], None] = "0005_p18_hierarchy_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - rein additiv."""
    with op.batch_alter_table("plan_phases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("jira_label", sa.String(length=200), nullable=True))

    op.create_table(
        "jira_issue_cache",
        sa.Column("jira_issue_key", sa.String(length=50), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("labels", sa.String(length=1000), nullable=True),
        sa.Column("component", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=True),
        sa.Column("last_synced_at", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("jira_issue_key"),
    )
    op.create_index(
        "ix_jira_issue_cache_project_id", "jira_issue_cache", ["project_id"], unique=False
    )

    op.create_table(
        "worklog_phase_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("jira_issue_key", sa.String(length=50), nullable=False),
        sa.Column("plan_phase_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_by_person_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["created_by_person_id"], ["persons.id"]),
        sa.ForeignKeyConstraint(["plan_phase_id"], ["plan_phases.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jira_issue_key"),
    )
    op.create_index(
        "ix_worklog_phase_overrides_plan_phase_id",
        "worklog_phase_overrides",
        ["plan_phase_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema - rein strukturell, keine Datenwiederherstellung noetig (alle neuen
    Spalten/Tabellen sind additiv, keine bestehenden Daten wurden veraendert)."""
    op.drop_index("ix_worklog_phase_overrides_plan_phase_id", table_name="worklog_phase_overrides")
    op.drop_table("worklog_phase_overrides")

    op.drop_index("ix_jira_issue_cache_project_id", table_name="jira_issue_cache")
    op.drop_table("jira_issue_cache")

    with op.batch_alter_table("plan_phases", schema=None) as batch_op:
        batch_op.drop_column("jira_label")
