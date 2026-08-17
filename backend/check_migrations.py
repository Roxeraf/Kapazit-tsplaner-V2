"""Migrations-Wächter: prüft Integrität und Anwendbarkeit der Alembic-Kette.

Läuft gegen eine Wegwerf-SQLite-DB (kein Zugriff auf Entwicklungs-/Produktionsdaten) und
verifiziert:

1. Exakt ein Head in der Migrationskette (kein zerrissener Revision-Graph wie der
   historische 0013-Kettenbruch, siehe CONCEPT.md Abschnitt 12.1).
2. Voller Upgrade `base → head` auf frischer DB (inkl. Seeds).
3. `alembic check` — keine Drift zwischen Migrationen und `models.py`.
4. Seed-Daten sind vorhanden (Permissions-Grundvokabular, Health-Thresholds).
5. Voller Downgrade/Upgrade-Roundtrip.

Aufruf (aus dem Repo-Root oder `backend/`):

    python backend/check_migrations.py

Beendet sich mit Exit-Code 0 bei Erfolg, sonst 1. Als Pre-Commit-Prüfung gedacht (CI kann
es später direkt übernehmen, da die DB-Verbindung isoliert ist).
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# WICHTIG: Der Connection-String muss VOR dem Import von `app.database` gesetzt sein —
# die Engine wird zum Importzeitpunkt gebunden.
_tmp = tempfile.TemporaryDirectory(prefix="kapa_migration_check_")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from app.database import engine  # noqa: E402

_BASELINE_REVISION = "0001_consolidated"


def _config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return cfg


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def main() -> None:
    cfg = _config()

    print("1/5  Prüfe: genau ein Head in der Migrations-Kette ...")
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) != 1:
        _fail("Ketten-Integrität", f"erwartet genau einen Head, gefunden: {heads}")
    print(f"      Head: {heads[0]}")
    # Von der einen Spitze abwärts muss die Kette lückenlos bei der konsolidierten
    # Baseline enden (kein zweiter Ast, keine zerrissene Kette wie der historische
    # 0013-Kettenbruch).
    rev = script.get_revision(heads[0])
    path: list[str] = []
    while rev is not None:
        path.append(rev.revision)
        rev = script.get_revision(rev.down_revision) if rev.down_revision else None
    if path[-1] != _BASELINE_REVISION:
        _fail(
            "Kopf-Integrität",
            f"Kette endet bei '{path[-1]}', erwartet wurde die konsolidierte Baseline "
            f"'{_BASELINE_REVISION}'. Neue Revisionen müssen darauf aufbauen, nicht daneben.",
        )

    print("2/5  Upgrade base -> head auf frischer Wegwerf-DB ...")
    try:
        command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001
        _fail("Upgrade", f"{exc!r}")

    print("3/5  Prüfe Drift (Migrationen vs. models.py) ...")
    try:
        command.check(cfg)
    except Exception as exc:  # noqa: BLE001
        _fail(
            "Drift",
            f"{exc!r} — Migrationen und Models stimmen nicht überein. "
            "Neue Modelländerung braucht eine neue Alembic-Revision (siehe CONCEPT.md "
            "Abschnitt 12.1, Migrations-Policy), kein ad-hoc ALTER.",
        )

    print("4/5  Prüfe Seeds ...")
    with engine.connect() as conn:
        permissions = conn.execute(text("SELECT COUNT(*) FROM permissions")).scalar_one()
        thresholds = conn.execute(text("SELECT COUNT(*) FROM health_thresholds")).scalar_one()
        if permissions != 12:
            _fail("Seeds", f"permissions hat {permissions} Zeilen, erwartet 12")
        if thresholds != 5:
            _fail("Seeds", f"health_thresholds hat {thresholds} Zeilen, erwartet 5")

    print("5/5  Downgrade/Upgrade-Roundtrip ...")
    try:
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001
        _fail("Roundtrip", f"{exc!r}")

    table_count = len(inspect(engine).get_table_names())
    print(f"OK — Kette integer, kein Drift, Seeds vollständig, Roundtrip sauber "
          f"({table_count} Tabellen nach dem Rebuild).")


if __name__ == "__main__":
    try:
        main()
    finally:
        engine.dispose()  # Windows: Datei-Handle vor Temp-Cleanup freigeben
        _tmp.cleanup()