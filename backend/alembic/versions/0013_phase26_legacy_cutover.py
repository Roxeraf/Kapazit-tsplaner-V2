"""phase26.9: Legacy Cutover - Gantt/FTE-Grid und TeamMember/Assignment entfernen

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-17 00:00:00.000000

Entfernt die alten Excel-abgeleiteten Parallelmodelle, die durch die Kapazitätsplaner-v2-
Zielarchitektur (Phase 13-25) funktional vollständig abgelöst wurden (siehe CONCEPT.md
Abschnitt 11 Punkt 26, Unterschritte 26.1-26.9):
- gantt_phases/project_gantt_phases (Phasenraster) -> PlanPhase (Phase 17, seit 26.2 UI)
- fte_plan/project_fte_plan (FTE-Soll-Raster) -> ResourceDemand (Phase 19, seit 26.3 UI)
- assignments/team_members (MA<->Projekt-FTE ohne Rolle/Periode) -> ResourceAssignment
  (Phase 19, seit 26.3 UI) bzw. Person/ResourceProfile (Phase 14, seit 26.9 UI)
- projects.projektleiter (Freitext) -> projektleiter_person_id (seit 26.1 alleinige Quelle)

Nutzerentscheidung (siehe CONCEPT.md): Datenverlust in der aktuellen Entwicklungsphase ist
ausdrücklich akzeptabel, kein Konvertierungsskript für Bestandsdaten. jira_sync.py,
gap_analysis.py, capacity_calc.py, routers/team.py, routers/kpis.py, routers/export.py und
das Frontend (TeamCapacity.tsx, Utilization.tsx, ProjectPlanningTab.tsx) sind vor dieser
Migration bereits auf die neuen Modelle umgestellt.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: Union[str, Sequence[str], None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Abhängigkeitsreihenfolge: assignments referenziert team_members, daher zuerst.
    op.drop_table('assignments')
    op.drop_table('team_members')
    op.drop_table('gantt_phases')
    op.drop_table('fte_plan')
    op.drop_table('project_gantt_phases')
    op.drop_table('project_fte_plan')

    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('projektleiter')


def downgrade() -> None:
    """Downgrade schema. Rein strukturell - keine Datenwiederherstellung (siehe Docstring)."""
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('projektleiter', sa.String(length=200), nullable=True))

    op.create_table(
        'project_fte_plan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('monat', sa.String(length=10), nullable=False),
        sa.Column('wert_soll', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'monat'),
    )
    op.create_table(
        'project_gantt_phases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('monat', sa.String(length=10), nullable=False),
        sa.Column('phase_code', sa.String(length=1), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'monat', 'phase_code'),
    )
    op.create_table(
        'fte_plan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subproject_id', sa.Integer(), nullable=False),
        sa.Column('monat', sa.String(length=10), nullable=False),
        sa.Column('wert_soll', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['subproject_id'], ['subprojects.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subproject_id', 'monat'),
    )
    op.create_table(
        'gantt_phases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subproject_id', sa.Integer(), nullable=False),
        sa.Column('monat', sa.String(length=10), nullable=False),
        sa.Column('phase_code', sa.String(length=1), nullable=False),
        sa.ForeignKeyConstraint(['subproject_id'], ['subprojects.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subproject_id', 'monat', 'phase_code'),
    )
    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('jira_account_id', sa.String(length=100), nullable=True),
        sa.Column('wochenstunden', sa.Float(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_member_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('fte', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['team_member_id'], ['team_members.id']),
        sa.PrimaryKeyConstraint('id'),
    )
