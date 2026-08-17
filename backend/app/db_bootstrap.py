"""Alembic-Bootstrap beim App-Start (löst main.py:create_all()+ad-hoc-ALTER-TABLE ab, siehe
CONCEPT.md Abschnitt 12.1).

- Frische DB (keine `alembic_version`-Tabelle, keine bekannten Alt-Tabellen): normales
  `alembic upgrade head` führt alle Migrationen inkl. Baseline real aus.
- Bestehende, bereits befüllte DB (kein `alembic_version`, aber `projects` existiert schon -
  Stand vor Einführung von Alembic): einmalig `alembic stamp 0001` (Baseline entspricht exakt
  dem heutigen Schema dieser DBs), danach `alembic upgrade head` für alle Migrationen ab 0002.
- DB kennt bereits `alembic_version`: normales `alembic upgrade head`.

Keine neuen ad-hoc `ALTER TABLE`-Migrationen mehr - jede künftige Schemaänderung ist eine
Alembic-Revision unter `backend/alembic/versions/`.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from .database import DATABASE_URL, engine

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_BASELINE_REVISION = "0001"


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg


def run_migrations() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    cfg = _alembic_config()

    if "alembic_version" not in table_names and "projects" in table_names:
        command.stamp(cfg, _BASELINE_REVISION)

    command.upgrade(cfg, "head")
