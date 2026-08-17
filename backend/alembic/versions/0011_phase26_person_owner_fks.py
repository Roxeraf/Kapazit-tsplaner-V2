"""phase26.1: Decision/Risk/Task Freitext-Owner -> Person-FK

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-17 00:00:00.000000

Ersetzt die Freitext-Felder Decision.entschieden_von, Risk.owner, Task.zustaendig durch
nullable FKs auf persons (Personenverzeichnis existiert seit Phase 14, siehe CONCEPT.md
Abschnitt 10/12.4 Phase 26). Projekt befindet sich noch in aktiver Entwicklung - bestehende
Freitextwerte werden bewusst NICHT migriert (kein Best-Effort-Namensabgleich wie bei
Project.projektleiter_person_id in 0003), sondern die alten Spalten direkt entfernt.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, Sequence[str], None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('decisions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entschieden_von_person_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_decisions_entschieden_von_person_id_persons', 'persons', ['entschieden_von_person_id'], ['id']
        )
        batch_op.drop_column('entschieden_von')

    with op.batch_alter_table('risks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_person_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_risks_owner_person_id_persons', 'persons', ['owner_person_id'], ['id'])
        batch_op.drop_column('owner')

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('zustaendig_person_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_tasks_zustaendig_person_id_persons', 'persons', ['zustaendig_person_id'], ['id']
        )
        batch_op.drop_column('zustaendig')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('zustaendig', sa.String(length=200), nullable=True))
        batch_op.drop_constraint('fk_tasks_zustaendig_person_id_persons', type_='foreignkey')
        batch_op.drop_column('zustaendig_person_id')

    with op.batch_alter_table('risks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner', sa.String(length=200), nullable=True))
        batch_op.drop_constraint('fk_risks_owner_person_id_persons', type_='foreignkey')
        batch_op.drop_column('owner_person_id')

    with op.batch_alter_table('decisions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('entschieden_von', sa.String(length=200), nullable=True))
        batch_op.drop_constraint('fk_decisions_entschieden_von_person_id_persons', type_='foreignkey')
        batch_op.drop_column('entschieden_von_person_id')
