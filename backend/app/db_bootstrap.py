"""Alembic-Bootstrap beim App-Start (löst main.py:create_all()+ad-hoc-ALTER-TABLE ab, siehe
CONCEPT.md Abschnitt 12.1).

Die Migrationskette wurde auf eine konsolidierte Baseline verdichtet (`0001_consolidated`,
Squash der Historie 0001–0014, siehe CONCEPT.md Abschnitt 12.1 Migrations-Policy). Diese
Datei entscheidet beim Start über den Zustand der Ziel-DB:

- Frische DB (keine `alembic_version`-Tabelle): normales `alembic upgrade head` — führt
  die konsolidierte Baseline inkl. Seeds (Permissions, Health-Thresholds) real aus.
- DB auf Retired-Revision `0014` (Head der alten Kette): Schema ist nachweislich identisch
  mit der konsolidierten Baseline (per Alembic-Check verifiziert) → einmalig `stamp` auf
  die neue Baseline, danach `upgrade head` (No-Op). Keine Schemaänderung, kein Datenrisiko.
- DB auf einer anderen Retired-Revision (`0001`–`0013`): historischer Zwischenstand, dessen
  Schema NICHT der Baseline entspricht und der ohne die gelöschte alte Kette nicht
  weitergeführt werden kann → klare Fehlermeldung statt stiller Falschmigration.
- Pre-Alembic-DB (kein `alembic_version`, aber `projects` existiert): war früher per
  Stamp auf die alte Baseline 0001 erreichbar; nach dem Squash gibt es die
  Zwischenrevisionen 0002–0014 nicht mehr, ein Stamp würde ein Alt-Schema fälschlich als
  aktuell markieren → klare Fehlermeldung (DB neu aufbauen, siehe Migrations-Policy).
- Unbekannte Revision: klare Fehlermeldung statt nackigem Fehler aus Alembic.

Kein ad-hoc `ALTER TABLE` mehr — jede künftige Schemaänderung ist eine Alembic-Revision
unter `backend/alembic/versions/`.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from .database import DATABASE_URL, engine

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_BASELINE_REVISION = "0001_consolidated"

# Revisionen der alten, squashten Kette, die auf der Baseline aufbauen.
# '0014' (alter Head) ist schema-identisch mit der Baseline → sicher zu stempeln.
_RETIRED_HEAD_REVISIONS = {"0014"}
# Alle anderen alten Revisionen sind historische Zwischenstände, deren Schema NICHT der
# Baseline entspricht — ein Stamp würde die DB fälschlich als „up to date" markieren.
_RETIRED_OLD_REVISIONS = {f"{i:04d}" for i in range(1, 14)}


class MigrationStateError(RuntimeError):
    """DB-Zustand, der nicht automatisch auf die aktuelle Baseline bringbar ist."""


def _alembic_config() -> Config:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg


def _current_revisions() -> list[str]:
    """Aktuell eingetragene Revision(en) aus der alembic_version-Tabelle."""
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    return [row[0] for row in rows]


def _script_revision_ids(cfg: Config) -> set[str]:
    """Alle Revisionen, die in der aktuellen Migrationskette existieren (inkl. Baseline)."""
    return {rev.revision for rev in ScriptDirectory.from_config(cfg).walk_revisions()}


def run_migrations() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    cfg = _alembic_config()
    script_ids = _script_revision_ids(cfg)

    if "alembic_version" not in table_names:
        if "projects" in table_names:
            raise MigrationStateError(
                "Pre-Alembic-Datenbank erkannt (alembic_version fehlt, Tabellen existieren). "
                "Nach dem Squash der Migrationshistorie (0001_consolidated, siehe CONCEPT.md "
                "Abschnitt 12.1) gibt es keinen automatischen Pfad mehr von diesem Alt-Schema "
                "zum aktuellen Stand. DB neu aufbauen (Datei löschen bzw. Postgres-DB neu "
                "anlegen, Alembic baut das Schema beim naechsten Start frisch auf) oder "
                "den Pre-Squash-Commit auschecken und die alte Kette dort einmalig durchlaufen."
            )
        # Frische DB → Baseline inkl. Seeds real ausführen.
        command.upgrade(cfg, "head")
        return

    revisions = _current_revisions()
    if len(revisions) != 1:
        raise MigrationStateError(
            "alembic_version enthält mehr als eine Revision; ein sauberer Stand hat genau "
            f"einen Eintrag. Gefunden: {revisions}. Zustand manuell prüfen."
        )
    current = revisions[0]

    if current in script_ids:
        # Normalfall: bekannte Revision der aktuellen Kette → auf Head bringen.
        command.upgrade(cfg, "head")
        return

    if current in _RETIRED_HEAD_REVISIONS:
        logger.warning(
            "DB steht auf der retired Revision %s (alter Migrations-Head). Schema ist "
            "identisch mit der konsolidierten Baseline %s → stample und upgrade.",
            current,
            _BASELINE_REVISION,
        )
        # purge=True: die Alt-Revision ist im Script-Ordner nicht mehr auflösbar, ein
        # normales Stamp würde beim Auflösen des Ist-Stands scheitern. purge entfernt die
        # alte Version-Zeile direkt und setzt dann die Ziel-Baseline.
        command.stamp(cfg, _BASELINE_REVISION, purge=True)
        command.upgrade(cfg, "head")
        return

    if current in _RETIRED_OLD_REVISIONS:
        raise MigrationStateError(
            f"DB steht auf retired Zwischenstand {current} (Zwischenstand der alten "
            "Migrationskette 0001-0014). Deren Schema entspricht NICHT der konsolidierten "
            "Baseline und der Blick zurück ist entfernt. DB neu aufbauen oder gezielt "
            "nur den schema-identischen Alt-Stand '0014' als Vorstufe nutzen."
        )

    raise MigrationStateError(
        f"DB kennt die unbekannte Alembic-Revision '{current}' — kein Upgrade-Pfad "
        "bekannt. Liegt ein Fremd-Schema vor? DB-Zustand prüfen (siehe CONCEPT.md "
        "Abschnitt 12.1 Migrations-Policy) oder DB neu aufbauen."
    )