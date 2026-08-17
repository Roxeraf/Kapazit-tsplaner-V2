"""phase26.9: Person.jira_account_id (Bridge vor Legacy Cutover)

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-17 00:00:00.000000

Additive Vorbereitung für den Legacy Cutover (Phase 26.9, siehe CONCEPT.md Abschnitt 11
Punkt 26): TeamMember/Assignment werden in Migration 0013 entfernt. jira_sync.py muss vorher
auf Person.jira_account_id umgestellt sein - dieses Feld wird hier ergänzt und aus den noch
vorhandenen team_members befüllt (jeder TeamMember hat seit Migration 0003 bereits eine
verknüpfte Person über person_id, daher reicht ein einfaches UPDATE FROM, kein
Fuzzy-Namensabgleich nötig).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: Union[str, Sequence[str], None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('jira_account_id', sa.String(length=100), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE persons
            SET jira_account_id = (
                SELECT tm.jira_account_id FROM team_members tm
                WHERE tm.person_id = persons.id AND tm.jira_account_id IS NOT NULL
            )
            WHERE EXISTS (
                SELECT 1 FROM team_members tm
                WHERE tm.person_id = persons.id AND tm.jira_account_id IS NOT NULL
            )
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.drop_column('jira_account_id')
