"""P18/B-1: Hierarchy Domain Foundation - PlanPhase-Baum, Milestone/PlanHistory-Verknuepfung,
interne Systemrolle.

Revision ID: 0005_p18_hierarchy_foundation
Revises: 0004_planning_consolidation
Create Date: 2026-08-21 00:00:00.000000

Additiv, nicht-destruktiv (siehe CONCEPT.md Abschnitt 12.1 Migrations-Policy). Reine
Schema-Grundlage fuer die PlanPhase-only-Zielarchitektur (CONCEPT.md Abschnitt 6b,
P18_ARCHITECTURE_RECONCILIATION_PASS2.md Abschnitt 35.5, Paket B-1) - KEINE Backend-Logik,
KEINE Datenmigration bestehender Subprojects/Grobplanung (folgt in B-2/B-5), KEINE
API-Aenderung (folgt in B-3/B-4):

1. plan_phases.parent_phase_id (nullable, self-referencing FK -> plan_phases.id, indiziert) -
   Grundlage der Phasen-Hierarchie (max. 3 Ebenen, wird in B-3 validiert). NULL = Top-Level.
2. plan_phases.reihenfolge (Integer, NOT NULL, default 0) - Sortierposition unter
   Geschwisterphasen, analog Project.reihenfolge/Subproject.reihenfolge.
3. milestones.plan_phase_id (nullable FK -> plan_phases.id, ON DELETE SET NULL, indiziert) -
   ersetzt subproject_id fachlich (CONCEPT.md Abschnitt 6b.8); subproject_id bleibt
   compat-only bestehen.
4. plan_history.plan_phase_id (nullable FK -> plan_phases.id, ON DELETE SET NULL, indiziert) -
   noetig fuer die Historisierung des plan_fte-Werts beim Leaf->Parent-Uebergang (CONCEPT.md
   Abschnitt 6b.1a/35.1).
5. resource_roles.is_system_role (Boolean, NOT NULL, default false) + Seed-Zeile "Ohne Rolle"
   (is_system_role=true) - technische Traegerschicht fuer direkte Personenzuordnung ohne
   erzwungene Rollenauswahl (CONCEPT.md Abschnitt 6b.4). Governance (nicht loeschbar, im
   Rollen-Picker ausgeblendet, kein Skill-Matching, keine eigene Rolle in Reporting) wird in
   B-3/B-4 im Code durchgesetzt - dieses Paket liefert nur das Flag und den Seed.

Technischer Hinweis (wie 0004_planning_consolidation): FK-Constraints werden bewusst benannt
(fk_<table>_<spalte>) und via create_foreign_key() angelegt, da SQLite batch_alter_table die
Tabelle fuer add_column+FK neu erstellen muss und dabei benannte Constraints benoetigt.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_p18_hierarchy_foundation"
down_revision: Union[str, Sequence[str], None] = "0004_planning_consolidation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SYSTEM_ROLE_NAME = "Ohne Rolle"
_SYSTEM_ROLE_DESCRIPTION = (
    "Interne Systemrolle (nicht loeschbar, im normalen Rollen-Picker ausgeblendet) - "
    "technische Traegerschicht fuer direkte Personenzuordnung ohne erzwungene "
    "Rollenauswahl (CONCEPT.md Abschnitt 6b.4)."
)


def upgrade() -> None:
    """Upgrade schema - rein additiv."""
    # 1) plan_phases.parent_phase_id (self-referencing FK, nullable, indiziert)
    #    + plan_phases.reihenfolge (NOT NULL, default 0)
    with op.batch_alter_table("plan_phases", schema=None) as batch_op:
        batch_op.add_column(sa.Column("parent_phase_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("reihenfolge", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_index("ix_plan_phases_parent_phase_id", ["parent_phase_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_plan_phases_parent_phase_id", "plan_phases", ["parent_phase_id"], ["id"]
        )

    # 2) milestones.plan_phase_id (FK -> plan_phases.id, ON DELETE SET NULL, indiziert)
    with op.batch_alter_table("milestones", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan_phase_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_milestones_plan_phase_id", ["plan_phase_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_milestones_plan_phase_id", "plan_phases", ["plan_phase_id"], ["id"], ondelete="SET NULL"
        )

    # 3) plan_history.plan_phase_id (FK -> plan_phases.id, ON DELETE SET NULL, indiziert)
    with op.batch_alter_table("plan_history", schema=None) as batch_op:
        batch_op.add_column(sa.Column("plan_phase_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_plan_history_plan_phase_id", ["plan_phase_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_plan_history_plan_phase_id", "plan_phases", ["plan_phase_id"], ["id"], ondelete="SET NULL"
        )

    # 4) resource_roles.is_system_role (NOT NULL, default false) + Seed "Ohne Rolle"
    with op.batch_alter_table("resource_roles", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    resource_roles = sa.table(
        "resource_roles",
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("active", sa.Boolean),
        sa.column("is_system_role", sa.Boolean),
    )
    op.get_bind().execute(
        sa.insert(resource_roles).values(
            name=_SYSTEM_ROLE_NAME,
            description=_SYSTEM_ROLE_DESCRIPTION,
            active=True,
            is_system_role=True,
        )
    )


def downgrade() -> None:
    """Downgrade schema - rein strukturell (Seed-Zeile wird mitentfernt, keine sonstige
    Datenwiederherstellung noetig, da alle neuen Spalten additiv/nullable bzw. default-belegt
    sind und keine bestehenden Daten veraendern)."""
    op.get_bind().execute(
        sa.text("DELETE FROM resource_roles WHERE name = :name AND is_system_role = 1"),
        {"name": _SYSTEM_ROLE_NAME},
    )

    with op.batch_alter_table("resource_roles", schema=None) as batch_op:
        batch_op.drop_column("is_system_role")

    with op.batch_alter_table("plan_history", schema=None) as batch_op:
        batch_op.drop_constraint("fk_plan_history_plan_phase_id", type_="foreignkey")
        batch_op.drop_index("ix_plan_history_plan_phase_id")
        batch_op.drop_column("plan_phase_id")

    with op.batch_alter_table("milestones", schema=None) as batch_op:
        batch_op.drop_constraint("fk_milestones_plan_phase_id", type_="foreignkey")
        batch_op.drop_index("ix_milestones_plan_phase_id")
        batch_op.drop_column("plan_phase_id")

    with op.batch_alter_table("plan_phases", schema=None) as batch_op:
        batch_op.drop_constraint("fk_plan_phases_parent_phase_id", type_="foreignkey")
        batch_op.drop_index("ix_plan_phases_parent_phase_id")
        batch_op.drop_column("reihenfolge")
        batch_op.drop_column("parent_phase_id")
