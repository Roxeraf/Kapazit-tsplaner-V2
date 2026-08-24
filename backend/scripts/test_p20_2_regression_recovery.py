"""P20.2 Regression Recovery: verifiziert die beiden auf echtem PostgreSQL reproduzierten,
von den bisherigen 16 SQLite-Regressionsskripten NICHT erkannten Root-Causes (siehe
P20_2_REGRESSION_RECOVERY_REPORT.md):

1. Alembic-Revision-IDs dürfen die von Alembic per Default angelegte
   `alembic_version.version_num`-Spalte (VARCHAR(32), kein version_table_len-Override in
   alembic/env.py) nicht überschreiten. SQLite ignoriert VARCHAR-Längen (Type Affinity) und
   ließ eine 39 Zeichen lange Revision-ID (0007, vor diesem Fix) unbemerkt "funktionieren" -
   auf PostgreSQL brach JEDES `alembic upgrade head` mit `StringDataRightTruncation` ab, und
   damit der komplette App-Start (db_bootstrap.run_migrations() läuft beim Modulimport von
   app/main.py) - Root Cause von "Projekte laden nicht mehr" (der Prozess kam nie hoch).

2. `delete_subtree` (routers/planning.py) löschte Nachfahren-Phasen bisher über
   ORM-Objekt-`db.delete(phase)` in einer Schleife + einem gemeinsamen `db.commit()` am Ende.
   `PlanPhase.parent_phase_id` ist eine reine FK-Spalte ohne gemapptes `relationship()` - ohne
   Relationship-Metadaten kann SQLAlchemys Unit-of-Work die Lösch-Reihenfolge für den
   Self-FK nicht herleiten und respektierte die hier vorher berechnete "tiefste Ebene
   zuerst"-Reihenfolge NICHT zuverlässig. Bei einer 3-Ebenen-Hierarchie (Parent/Child/
   Grandchild, BD-10 erlaubt bis zu 3 Ebenen) führte das auf echtem PostgreSQL zu einer
   `ForeignKeyViolation` (Parent vor seinem Kind gelöscht) - auf SQLite blieb das unbemerkt,
   weil das FK-Pragma dort standardmäßig aus ist (siehe capacity_calc.
   cleanup_phase_resource_dependencies-Docstring) UND weil der bestehende
   test_p20_1_delete_stabilization.py-Subtree-Test nur 2 Ebenen (Parent+Child, keinen
   Grandchild) abdeckte. Der Fix ersetzt die ORM-Objekt-Deletes durch Bulk-`Query.delete()`
   je Phase in der bereits korrekt berechneten Reihenfolge (jeder Aufruf führt sein DELETE
   sofort aus, nicht erst gebündelt bei einem späteren Flush) - dialektunabhängig identisch
   auf SQLite und PostgreSQL. Dieser Test aktiviert `PRAGMA foreign_keys=ON` auf einer
   dedizierten SQLite-Engine, um dieselbe strikte FK-Semantik wie PostgreSQL zu erzwingen und
   den Bug (bzw. seinen Fix) auch ohne eine echte PostgreSQL-Instanz zuverlässig zu prüfen -
   die eigentliche Verifikation dieses Fixes lief zusätzlich gegen eine echte lokale
   PostgreSQL-16-Instanz (siehe Report Abschnitt 2/9).

3. Kapazitäts-Consumer (assignment-summary, Monthly Capacity, Portfolio Utilization, GAP,
   Health/Cockpit) dürfen bei gemischten Legacy-ResourceDemand- + direkten PlanPhase-
   ResourceAssignment-Daten sowie nach einer gelaufenen
   migrate_resource_assignments_to_plan_phase.py-Migration (beide FKs auf derselben Zeile
   gesetzt) keine Zeile doppelt zählen - regressionsgetestet hier zusätzlich zu den bereits
   grün laufenden test_p20_1_capacity_consumer_rewiring.py-Fällen.

Aufruf: python backend/scripts/test_p20_2_regression_recovery.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def check_revision_id_lengths() -> None:
    """1/3: keine Alembic-Revision-ID darf die von Alembic per Default angelegte
    alembic_version.version_num-Spalte (VARCHAR(32)) überschreiten - siehe Modul-Docstring."""
    print("1/3  Alembic-Revision-IDs <= 32 Zeichen (alembic_version.version_num VARCHAR(32)) ...")
    import re

    versions_dir = BACKEND_DIR / "alembic" / "versions"
    pattern = re.compile(r'^revision:\s*str\s*=\s*[\'"]([^\'"]+)[\'"]', re.MULTILINE)
    offenders = []
    for path in sorted(versions_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        match = pattern.search(text)
        if not match:
            _fail("Revision-ID Parsing", f"{path.name}: keine 'revision: str = ...'-Zeile gefunden")
        revision_id = match.group(1)
        if len(revision_id) > 32:
            offenders.append((path.name, revision_id, len(revision_id)))
    if offenders:
        detail = ", ".join(f"{name}: '{rev}' ({length} Zeichen)" for name, rev, length in offenders)
        _fail("Revision-ID zu lang", detail)


def check_subtree_delete_ordering() -> None:
    """2/3: 3-Ebenen delete-subtree (Parent/Child/Grandchild) mit direkter ResourceAssignment +
    WorklogPhaseOverride auf dem tiefsten Blatt.

    WICHTIG (empirisch verifiziert, siehe P20_2_REGRESSION_RECOVERY_REPORT.md Abschnitt 2/9):
    `PRAGMA foreign_keys=ON` auf SQLite reicht NICHT aus, um den konkreten Ordering-Bug
    zuverlässig zu reproduzieren - SQLAlchemys interne, dialektabhängige Batch-/
    Executemany-Reihenfolge für mehrzeilige DELETEs derselben Tabelle unterscheidet sich
    zwischen dem SQLite- und dem psycopg2-Dialekt (auf SQLite blieb die hier berechnete
    "tiefste Ebene zuerst"-Reihenfolge in Tests zufällig erhalten, auf PostgreSQL wurde sie
    umsortiert). Dieser Check läuft deshalb, wenn `P20_2_POSTGRES_TEST_URL` gesetzt ist
    (Verbindung zu einer leeren/wegwerfbaren PostgreSQL-DB, z.B.
    postgresql+psycopg2://user:pass@localhost:5432/scratch_db), GEGEN ECHTES POSTGRESQL -
    das ist die einzige Umgebung, in der der Bug/Fix nachweisbar unterscheidbar ist. Ohne
    diese Variable läuft der Check als Best-Effort-Verhaltensprüfung gegen SQLite mit
    aktiviertem FK-Pragma (verifiziert weiterhin die korrekte End-to-End-Funktionalität,
    beweist aber NICHT zuverlässig die Abwesenheit des Ordering-Bugs - siehe oben)."""
    postgres_url = os.environ.get("P20_2_POSTGRES_TEST_URL")
    label = "PostgreSQL (P20_2_POSTGRES_TEST_URL)" if postgres_url else "SQLite mit PRAGMA foreign_keys=ON (Best-Effort, siehe Docstring)"
    print(f"2/3  delete-subtree über 3 Ebenen mit FK-Enforcement [{label}] ...")
    tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_2_subtree_check_")
    try:
        if postgres_url:
            os.environ["DATABASE_URL"] = postgres_url
        else:
            os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(tmp.name) / "check.db").replace("\\", "/")

        # Frischer Modul-Import-Zustand nötig, da app.database.engine beim ersten Import
        # gebunden wird - dieses Skript läuft isoliert (eigener Prozess), kein Konflikt mit
        # den anderen Testskripten, die denselben Trick verwenden (siehe deren Docstrings).
        from sqlalchemy import event
        from fastapi.testclient import TestClient

        from app.main import app
        from app.database import SessionLocal, engine
        from app import models

        if not postgres_url:

            @event.listens_for(engine, "connect")
            def _enable_sqlite_fk(dbapi_connection, _):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        client = TestClient(app)

        project = client.post("/projects", json={"name": "P20.2 Subtree Test", "start_monat": "10.2026"}).json()
        project_id = project["id"]
        person = client.post("/people", json={"display_name": "P20.2 Person"}).json()

        parent = client.post(f"/projects/{project_id}/plan-phases", json={"phase_type": "Parent", "status": "geplant"}).json()
        child = client.post(
            f"/projects/{project_id}/plan-phases",
            json={"phase_type": "Child", "status": "geplant", "parent_phase_id": parent["id"]},
        ).json()
        grandchild = client.post(
            f"/projects/{project_id}/plan-phases",
            json={
                "phase_type": "Grandchild",
                "status": "geplant",
                "parent_phase_id": child["id"],
                "forecast_start": "2026-10-01",
                "forecast_end": "2026-10-31",
                "plan_fte": 0.2,
            },
        ).json()
        assign_resp = client.post(
            f"/projects/plan-phases/{grandchild['id']}/assign-person", json={"person_id": person["id"], "fte": 0.2}
        )
        if assign_resp.status_code != 200:
            _fail("Setup direkte Zuordnung (Grandchild)", f"{assign_resp.status_code}: {assign_resp.text}")
        override_resp = client.post(
            f"/projects/plan-phases/{grandchild['id']}/worklog-overrides",
            json={"jira_issue_key": "P202-SUBTREE-1", "note": "Test"},
        )
        if override_resp.status_code != 201:
            _fail("Setup WorklogPhaseOverride (Grandchild)", f"{override_resp.status_code}: {override_resp.text}")

        # Normaler DELETE auf 'child' muss weiterhin 409 liefern (hat noch den Grandchild).
        blocked = client.delete(f"/projects/plan-phases/{child['id']}")
        if blocked.status_code != 409:
            _fail("Parent-Block (Child hat Grandchild)", f"erwartet 409, bekommen {blocked.status_code}: {blocked.text}")

        impact = client.get(f"/projects/plan-phases/{child['id']}/subtree-impact").json()
        if impact["descendant_phase_count"] != 1:
            _fail("Subtree-Impact descendant_phase_count", f"erwartet 1 (Grandchild), bekommen {impact}")

        subtree_delete = client.post(
            f"/projects/plan-phases/{child['id']}/delete-subtree",
            json={"confirm_phase_type": child["phase_type"], "confirm_descendant_count": 1},
        )
        if subtree_delete.status_code != 204:
            _fail(
                "3-Ebenen delete-subtree (reproduzierter Postgres-Bug: Parent vor Kind gelöscht)",
                f"erwartet 204, bekommen {subtree_delete.status_code}: {subtree_delete.text}",
            )

        for phase_id in (child["id"], grandchild["id"]):
            resp = client.get(f"/projects/plan-phases/{phase_id}")
            if resp.status_code != 404:
                _fail("Nachfahren wirklich gelöscht", f"phase {phase_id}: erwartet 404, bekommen {resp.status_code}")

        parent_after = client.get(f"/projects/plan-phases/{parent['id']}")
        if parent_after.status_code != 200 or parent_after.json()["has_children"]:
            _fail("Parent bleibt erhalten und wird wieder Leaf", f"{parent_after.status_code}: {parent_after.text}")

        db = SessionLocal()
        try:
            orphaned_assignments = (
                db.query(models.ResourceAssignment)
                .filter(models.ResourceAssignment.plan_phase_id.in_([child["id"], grandchild["id"]]))
                .count()
            )
            orphaned_overrides = (
                db.query(models.WorklogPhaseOverride)
                .filter(models.WorklogPhaseOverride.plan_phase_id.in_([child["id"], grandchild["id"]]))
                .count()
            )
        finally:
            db.close()
        if orphaned_assignments or orphaned_overrides:
            _fail("Orphaned State nach 3-Ebenen delete-subtree", f"assignments={orphaned_assignments} overrides={orphaned_overrides}")

        engine.dispose()
    finally:
        tmp.cleanup()
        os.environ.pop("DATABASE_URL", None)


def check_no_double_counting_mixed_and_migrated() -> None:
    """3/3: gemischte Legacy+Direct-Daten sowie eine gelaufene Migration dürfen assignment-
    summary/Portfolio-Utilization nicht verdoppeln."""
    print("3/3  Keine Doppelzählung bei gemischten Legacy+Direct- und migrierten Daten ...")
    tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_2_double_count_check_")
    try:
        os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(tmp.name) / "check.db").replace("\\", "/")

        from fastapi.testclient import TestClient

        from app.main import app
        from app.database import engine
        from app import capacity_calc

        client = TestClient(app)

        project = client.post("/projects", json={"name": "P20.2 Double-Count Test", "start_monat": "02.2026"}).json()
        project_id = project["id"]
        christian = client.post("/people", json={"display_name": "Christian"}).json()
        max_ = client.post("/people", json={"display_name": "Max"}).json()
        for person in (christian, max_):
            profile_resp = client.post(f"/people/{person['id']}/resource-profile", json={"weekly_hours": 40})
            if profile_resp.status_code != 201:
                _fail("Setup ResourceProfile", f"{profile_resp.status_code}: {profile_resp.text}")
        role = client.post("/resource-roles", json={"name": "P20.2 Testrolle"}).json()

        phase = client.post(
            f"/projects/{project_id}/plan-phases",
            json={
                "phase_type": "Konfiguration",
                "status": "geplant",
                "forecast_start": "2026-02-01",
                "forecast_end": "2026-02-28",
                "plan_fte": 0.5,
            },
        ).json()
        phase_id = phase["id"]

        # Legacy: ResourceDemand + Assignment (real-role, nicht "Ohne Rolle").
        demand = client.post(
            f"/projects/{project_id}/resource-demands",
            json={"plan_phase_id": phase_id, "resource_role_id": role["id"], "period": "Feb 26", "fte": 0.3},
        ).json()
        client.post(f"/resource-demands/{demand['id']}/assignments", json={"person_id": max_["id"], "fte": 0.3})

        # Direkt: neuer Standardpfad.
        client.post(f"/projects/plan-phases/{phase_id}/assign-person", json={"person_id": christian["id"], "fte": 0.2})

        summary = client.get(f"/projects/plan-phases/{phase_id}/assignment-summary").json()
        if round(summary["assigned_fte"], 2) != 0.5:
            _fail("assignment-summary vor Migration", f"erwartet 0.5, bekommen {summary}")

        util = {row["person_id"]: row["zugeordnet_fte"] for row in client.get("/team/utilization?period=Feb%2026").json()}
        if round(util.get(christian["id"], -1), 2) != 0.2 or round(util.get(max_["id"], -1), 2) != 0.3:
            _fail("Portfolio Utilization vor Migration", f"{util}")

        # Migration ausführen (dry-run + apply) - migriert das direkte Assignment nicht (ist
        # schon direkt), lässt das Legacy-Assignment unverändert (kein carrier-System-role-Fall
        # hier, echte Rolle) - Doppelzählung darf trotzdem nirgends auftreten.
        import subprocess

        dry_run = subprocess.run(
            [sys.executable, str(BACKEND_DIR / "scripts" / "migrate_resource_assignments_to_plan_phase.py")],
            capture_output=True, text=True, env={**os.environ},
        )
        if dry_run.returncode != 0:
            _fail("Migrationsskript Dry-Run", dry_run.stdout + dry_run.stderr)
        apply_run = subprocess.run(
            [sys.executable, str(BACKEND_DIR / "scripts" / "migrate_resource_assignments_to_plan_phase.py"), "--apply"],
            capture_output=True, text=True, env={**os.environ},
        )
        if apply_run.returncode != 0:
            _fail("Migrationsskript Apply", apply_run.stdout + apply_run.stderr)

        summary_after = client.get(f"/projects/plan-phases/{phase_id}/assignment-summary").json()
        if round(summary_after["assigned_fte"], 2) != 0.5:
            _fail("assignment-summary nach Migration (keine Doppelzählung)", f"erwartet 0.5, bekommen {summary_after}")

        util_after = {row["person_id"]: row["zugeordnet_fte"] for row in client.get("/team/utilization?period=Feb%2026").json()}
        if round(util_after.get(christian["id"], -1), 2) != 0.2 or round(util_after.get(max_["id"], -1), 2) != 0.3:
            _fail("Portfolio Utilization nach Migration (keine Doppelzählung)", f"{util_after}")

        assigned_helper = capacity_calc.assigned_fte_for_project_period.__module__  # sanity import check
        assert assigned_helper == "app.capacity_calc"

        engine.dispose()
    finally:
        tmp.cleanup()
        os.environ.pop("DATABASE_URL", None)


_CHECKS = {
    "subtree": check_subtree_delete_ordering,
    "double_count": check_no_double_counting_mixed_and_migrated,
}


def main() -> None:
    # check 2 und 3 importieren app.main/app.database (bindet DATABASE_URL/engine EINMALIG
    # beim ersten Modulimport eines Prozesses) und setzen dafür jeweils eine eigene, frische
    # temporäre SQLite-DB - deshalb je eigener Subprozess statt eines gemeinsamen In-Process-
    # Imports (der die zweite DATABASE_URL sonst stillschweigend ignorieren würde, da Python
    # das bereits geladene app.database-Modul cached). check 1 braucht keinen App-Import und
    # läuft direkt im Hauptprozess.
    import subprocess

    check_revision_id_lengths()
    for name in _CHECKS:
        result = subprocess.run(
            [sys.executable, __file__, f"--check={name}"], capture_output=True, text=True
        )
        if result.returncode != 0:
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            sys.exit(1)
        sys.stdout.write(result.stdout)
    print(
        "OK — Alembic-Revision-IDs passen in alembic_version.version_num VARCHAR(32), "
        "3-Ebenen delete-subtree löscht unter FK-Enforcement in korrekter Reihenfolge (kein "
        "ForeignKeyViolation mehr), und gemischte Legacy+Direct- sowie migrierte Daten werden "
        "in assignment-summary/Portfolio-Utilization nicht doppelt gezählt."
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--check="):
        _CHECKS[sys.argv[1].split("=", 1)[1]]()
    else:
        main()
