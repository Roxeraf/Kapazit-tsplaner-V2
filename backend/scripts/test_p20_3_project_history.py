"""P20.3 Automatic Project History: Coverage, Bundling, Noise-Prevention, Immutability.

Kein pytest (bestehendes Skript-Muster). Baut eine Wegwerf-DB, startet die echte FastAPI-App
per TestClient und prüft die tatsächlichen Endpunkte.

Wenn P20_3_POSTGRES_TEST_URL gesetzt ist (postgresql+psycopg2://...), laufen die
FK-/Delete-Prüfungen gegen echtes PostgreSQL — SQLite green reicht laut Auftrag nicht
für Migrationen/Foreign Keys/Delete-Semantik.

Aufruf: python backend/scripts/test_p20_3_project_history.py
Exit-Code 0 bei Erfolg, sonst 1.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_postgres_url = os.environ.get("P20_3_POSTGRES_TEST_URL")
_tmp = tempfile.TemporaryDirectory(prefix="kapa_p20_3_history_")
if _postgres_url:
    os.environ["DATABASE_URL"] = _postgres_url
else:
    os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "check.db").replace("\\", "/")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
from app import history, models  # noqa: E402

client = TestClient(app)


def _fail(step: str, reason: str) -> None:
    print(f"[FAIL] {step}: {reason}")
    sys.exit(1)


def _rows(project_id: int) -> list[dict]:
    resp = client.get(f"/projects/{project_id}/history")
    if resp.status_code != 200:
        _fail("GET history", f"{resp.status_code}: {resp.text}")
    return resp.json()


def _count(project_id: int) -> int:
    return len(_rows(project_id))


def _create_project(name: str) -> int:
    resp = client.post("/projects", json={"name": name, "start_monat": "10.2026", "anzahl_monate": 3, "kunde": "Acme"})
    if resp.status_code != 201:
        _fail("Projekt anlegen", f"{resp.status_code}: {resp.text}")
    return resp.json()["id"]


def _create_phase(project_id: int, **kwargs) -> dict:
    payload = {"phase_type": "Phase", "status": "geplant", **kwargs}
    resp = client.post(f"/projects/{project_id}/plan-phases", json=payload)
    if resp.status_code != 201:
        _fail("PlanPhase anlegen", f"{resp.status_code}: {resp.text}")
    return resp.json()


def _create_person(name: str) -> int:
    db = SessionLocal()
    person = models.Person(display_name=name)
    db.add(person)
    db.commit()
    person_id = person.id
    db.close()
    return person_id


def _by_field(rows: list[dict], feld: str) -> list[dict]:
    return [r for r in rows if r.get("feld") == feld]


def _actions(rows: list[dict], action: str) -> list[dict]:
    return [r for r in rows if r.get("action") == action]


def _assert_no_put_delete_history() -> None:
    routes = {getattr(r, "path", "") + " " + ",".join(sorted(getattr(r, "methods", []) or [])) for r in app.routes}
    offenders = [
        r
        for r in routes
        if "/history" in r
        and ("PUT" in r or "DELETE" in r or "PATCH" in r)
    ]
    if offenders:
        _fail("History immutable", f"schreibende History-Routen: {offenders}")


def _assert_jira_sync_is_quiet() -> None:
    jira_py = (BACKEND_DIR / "app" / "routers" / "jira.py").read_text(encoding="utf-8")
    sync_py = (BACKEND_DIR / "app" / "jira_sync.py").read_text(encoding="utf-8")
    if "from .. import history" in jira_py or "import history" in jira_py:
        _fail("Noise Prevention", "routers/jira.py importiert history — Sync würde Audit-Noise erzeugen")
    if "history.record" in sync_py or "PlanHistory" in sync_py:
        _fail("Noise Prevention", "jira_sync.py schreibt PlanHistory")


def main() -> None:
    dialect = "PostgreSQL" if _postgres_url else "SQLite"
    print(f"P20.3 Project History tests gegen {dialect}")

    _assert_no_put_delete_history()
    _assert_jira_sync_is_quiet()

    print("1/12  Projekt anlegen und Stammdaten-Update ...")
    project_id = _create_project("History-Projekt")
    created = _rows(project_id)
    if not _actions(created, "created"):
        _fail("Project create", f"kein created-Eintrag: {created}")
    before = _count(project_id)
    resp = client.put(f"/projects/{project_id}", json={"name": "History-Projekt v2", "kunde": "Neue GmbH"})
    if resp.status_code != 200:
        _fail("Project update", f"{resp.status_code}: {resp.text}")
    after = _rows(project_id)
    name_rows = [r for r in after if r["feld"] == "name" and r["action"] == "updated"]
    kunde_rows = [r for r in after if r["feld"] == "kunde" and r["action"] == "updated"]
    if not name_rows or name_rows[0]["alter_wert"] != "History-Projekt" or name_rows[0]["neuer_wert"] != "History-Projekt v2":
        _fail("Project name", f"{name_rows}")
    if not kunde_rows or kunde_rows[0]["neuer_wert"] != "Neue GmbH":
        _fail("Project kunde", f"{kunde_rows}")
    batches = {r["batch_id"] for r in after if r["action"] == "updated" and r["feld"] in ("name", "kunde")}
    if len(batches) != 1:
        _fail("Project bundle", f"Name+Kunde sollten eine batch_id teilen: {batches}")
    if any(r["entity_type"] != "project" for r in name_rows + kunde_rows):
        _fail("Project entity_type", "Stammdaten-Update ohne entity_type=project")

    print("2/12  No-Op-Update erzeugt keinen History-Noise ...")
    before = _count(project_id)
    resp = client.put(f"/projects/{project_id}", json={"name": "History-Projekt v2", "kunde": "Neue GmbH"})
    if resp.status_code != 200:
        _fail("Project no-op", f"{resp.status_code}: {resp.text}")
    if _count(project_id) != before:
        _fail("Project no-op", f"erwartete {before} Zeilen, bekommen {_count(project_id)}")

    print("3/12  PlanPhase create / rename / Zeitraum / plan_fte / Bundling / Parent / Delete ...")
    phase = _create_phase(
        project_id,
        phase_type="Konfiguration",
        forecast_start="2026-11-13",
        forecast_end="2026-11-20",
        plan_fte=0.6,
    )
    rows = _rows(project_id)
    created_phase = [
        r for r in rows if r.get("entity_type") == "plan_phase" and r.get("action") == "created" and r.get("entity_id") == phase["id"]
    ]
    if not created_phase or not any(r["feld"] == history.EVENT_FIELD for r in created_phase):
        _fail("Phase create", f"{created_phase}")
    create_batch = created_phase[0]["batch_id"]
    if any(r["batch_id"] != create_batch for r in created_phase):
        _fail("Phase create batch", "Create-Felder nicht gebündelt")

    resp = client.put(f"/projects/plan-phases/{phase['id']}", json={"phase_type": "Konfig v2"})
    if resp.status_code != 200:
        _fail("Phase rename", f"{resp.status_code}: {resp.text}")
    renamed = [r for r in _rows(project_id) if r["feld"] == "phase_type" and r["action"] == "updated"]
    if not renamed or renamed[0]["alter_wert"] != "Konfiguration" or renamed[0]["neuer_wert"] != "Konfig v2":
        _fail("Phase rename", f"{renamed}")

    before = _count(project_id)
    resp = client.put(
        f"/projects/plan-phases/{phase['id']}",
        json={"forecast_end": "2026-11-27", "plan_fte": 0.8},
    )
    if resp.status_code != 200:
        _fail("Phase multi-field", f"{resp.status_code}: {resp.text}")
    multi = [
        r
        for r in _rows(project_id)
        if r.get("action") == "updated" and r.get("entity_id") == phase["id"] and r["feld"] in ("forecast_end", "plan_fte")
    ]
    if len(multi) < 2:
        _fail("Phase multi-field", f"erwartete forecast_end + plan_fte: {multi}")
    if len({r["batch_id"] for r in multi}) != 1:
        _fail("Phase bundle", f"eine Useraktion muss eine batch_id haben: {multi}")
    end_row = next(r for r in multi if r["feld"] == "forecast_end")
    if end_row["alter_wert"] != "2026-11-20" or end_row["neuer_wert"] != "2026-11-27":
        _fail("Phase date", f"{end_row}")

    before_parent = _count(project_id)
    child = _create_phase(project_id, phase_type="Testing", parent_phase_id=phase["id"], plan_fte=0.4)
    parent_fte = [
        r
        for r in _rows(project_id)
        if r.get("plan_phase_id") == phase["id"] and r["feld"] == "plan_fte" and r["action"] == "updated"
    ]
    if not parent_fte or parent_fte[0]["neuer_wert"] is not None:
        _fail("Parent plan_fte", f"{parent_fte}")
    if _count(project_id) <= before_parent:
        _fail("Child create", "Unterphase erzeugte keine History")

    resp = client.put(f"/projects/plan-phases/{child['id']}", json={"parent_phase_id": None})
    if resp.status_code != 200:
        _fail("Parent change", f"{resp.status_code}: {resp.text}")
    parent_change = [r for r in _rows(project_id) if r["feld"] == "parent_phase_id" and r.get("entity_id") == child["id"]]
    if not parent_change:
        _fail("Parent change", "parent_phase_id nicht historisiert")

    label = child["phase_type"]
    resp = client.delete(f"/projects/plan-phases/{child['id']}")
    if resp.status_code != 204:
        _fail("Phase delete", f"{resp.status_code}: {resp.text}")
    deleted = [
        r
        for r in _rows(project_id)
        if r.get("action") == "deleted" and r.get("entity_type") == "plan_phase" and (r.get("entity_label") == label or r.get("alter_wert") == label)
    ]
    if not deleted:
        _fail("Phase delete history", f"verständlicher Delete-Eintrag fehlt: {_rows(project_id)[:8]}")

    print("4/12  ResourceAssignment create / FTE / delete ...")
    person_id = _create_person("Christian Cron")
    assign_phase = _create_phase(
        project_id,
        phase_type="Besetzung",
        forecast_start="2026-11-21",
        forecast_end="2026-11-28",
        plan_fte=0.5,
    )
    resp = client.post(
        f"/projects/{project_id}/plan-phases/{assign_phase['id']}/assignments",
        json={"person_id": person_id, "fte": 0.2},
    )
    if resp.status_code != 201:
        _fail("Assignment create", f"{resp.status_code}: {resp.text}")
    assignment = resp.json()
    created_asg = [
        r
        for r in _rows(project_id)
        if r.get("entity_type") == "resource_assignment" and r.get("action") == "created" and r.get("entity_id") == assignment["id"]
    ]
    if not created_asg:
        _fail("Assignment create history", f"{_rows(project_id)[:12]}")
    if created_asg[0]["entity_label"] != "Christian Cron":
        _fail("Assignment label", created_asg[0]["entity_label"])

    resp = client.patch(
        f"/projects/{project_id}/plan-phases/{assign_phase['id']}/assignments/{assignment['id']}",
        json={"fte": 0.4},
    )
    if resp.status_code != 200:
        _fail("Assignment FTE", f"{resp.status_code}: {resp.text}")
    fte_rows = [
        r
        for r in _rows(project_id)
        if r.get("entity_type") == "resource_assignment" and r["feld"] == "fte" and r["action"] == "updated"
    ]
    if not fte_rows or fte_rows[0]["alter_wert"] != "0.2" or fte_rows[0]["neuer_wert"] != "0.4":
        _fail("Assignment FTE history", f"{fte_rows}")

    resp = client.patch(
        f"/projects/{project_id}/plan-phases/{assign_phase['id']}/assignments/{assignment['id']}",
        json={"fte": 0.4},
    )
    if resp.status_code != 200:
        _fail("Assignment no-op", f"{resp.status_code}: {resp.text}")
    if len([r for r in _rows(project_id) if r.get("entity_type") == "resource_assignment" and r["feld"] == "fte" and r["action"] == "updated"]) != 1:
        _fail("Assignment no-op", "FTE-No-Op hat Noise erzeugt")

    resp = client.delete(
        f"/projects/{project_id}/plan-phases/{assign_phase['id']}/assignments/{assignment['id']}"
    )
    if resp.status_code != 204:
        _fail("Assignment delete", f"{resp.status_code}: {resp.text}")
    deleted_asg = [
        r
        for r in _rows(project_id)
        if r.get("entity_type") == "resource_assignment" and r.get("action") == "deleted"
    ]
    if not deleted_asg or deleted_asg[0]["entity_label"] != "Christian Cron":
        _fail("Assignment delete history", f"{deleted_asg}")

    print("5/12  Milestone create/update/delete ...")
    resp = client.post(
        f"/projects/{project_id}/milestones",
        json={"name": "Go-Live", "forecast_date": "2026-12-15", "status": "geplant"},
    )
    if resp.status_code != 201:
        _fail("Milestone create", f"{resp.status_code}: {resp.text}")
    milestone = resp.json()
    resp = client.put(f"/projects/milestones/{milestone['id']}", json={"forecast_date": "2026-12-18"})
    if resp.status_code != 200:
        _fail("Milestone update", f"{resp.status_code}: {resp.text}")
    moved = [
        r
        for r in _rows(project_id)
        if r.get("entity_type") == "milestone" and r["feld"] == "forecast_date" and r["action"] == "updated"
    ]
    if not moved or moved[0]["alter_wert"] != "2026-12-15" or moved[0]["neuer_wert"] != "2026-12-18":
        _fail("Milestone date", f"{moved}")
    resp = client.delete(f"/projects/milestones/{milestone['id']}")
    if resp.status_code != 204:
        _fail("Milestone delete", f"{resp.status_code}: {resp.text}")
    if not any(r.get("entity_type") == "milestone" and r.get("action") == "deleted" for r in _rows(project_id)):
        _fail("Milestone delete history", "Eintrag fehlt")

    print("6/12  Collaboration (Task/Blocker/Decision) ...")
    resp = client.post(f"/projects/{project_id}/tasks", json={"titel": "Kickoff vorbereiten", "status": "offen"})
    if resp.status_code != 201:
        _fail("Task create", f"{resp.status_code}: {resp.text}")
    task = resp.json()
    resp = client.put(f"/projects/tasks/{task['id']}", json={"status": "erledigt"})
    if resp.status_code != 200:
        _fail("Task complete", f"{resp.status_code}: {resp.text}")
    if not any(r.get("entity_type") == "task" and r["feld"] == "status" and r["neuer_wert"] == "erledigt" for r in _rows(project_id)):
        _fail("Task status history", "Status-Änderung fehlt")
    resp = client.delete(f"/projects/tasks/{task['id']}")
    if resp.status_code != 204:
        _fail("Task delete", f"{resp.status_code}: {resp.text}")

    resp = client.post(f"/projects/{project_id}/blockers", json={"title": "Schnittstelle fehlt", "status": "offen"})
    if resp.status_code != 201:
        _fail("Blocker create", f"{resp.status_code}: {resp.text}")
    blocker = resp.json()
    resp = client.put(f"/projects/blockers/{blocker['id']}", json={"status": "geloest"})
    if resp.status_code != 200:
        _fail("Blocker resolve", f"{resp.status_code}: {resp.text}")
    if not any(r.get("entity_type") == "blocker" and r["neuer_wert"] == "geloest" for r in _rows(project_id)):
        _fail("Blocker history", "gelöst nicht historisiert")
    resp = client.delete(f"/projects/blockers/{blocker['id']}")
    if resp.status_code != 204:
        _fail("Blocker delete", f"{resp.status_code}: {resp.text}")

    resp = client.post(f"/projects/{project_id}/decisions", json={"titel": "Go für Wave 2", "status": "offen"})
    if resp.status_code != 201:
        _fail("Decision create", f"{resp.status_code}: {resp.text}")
    decision = resp.json()
    resp = client.put(f"/projects/decisions/{decision['id']}", json={"status": "entschieden"})
    if resp.status_code != 200:
        _fail("Decision update", f"{resp.status_code}: {resp.text}")
    resp = client.delete(f"/projects/decisions/{decision['id']}")
    if resp.status_code != 204:
        _fail("Decision delete", f"{resp.status_code}: {resp.text}")
    if not any(r.get("entity_type") == "decision" and r.get("action") == "deleted" for r in _rows(project_id)):
        _fail("Decision delete history", "Eintrag fehlt")

    print("7/12  Jira-Label und Worklog-Override, kein Sync-Noise ...")
    mapped = _create_phase(project_id, phase_type="Mapped", jira_label="phase:mapped")
    resp = client.put(f"/projects/plan-phases/{mapped['id']}", json={"jira_label": "phase:mapped-v2"})
    if resp.status_code != 200:
        _fail("jira_label update", f"{resp.status_code}: {resp.text}")
    label_rows = [r for r in _rows(project_id) if r["feld"] == "jira_label" and r["action"] == "updated" and r.get("entity_id") == mapped["id"]]
    if not label_rows or label_rows[0]["alter_wert"] != "phase:mapped" or label_rows[0]["neuer_wert"] != "phase:mapped-v2":
        _fail("jira_label history", f"{label_rows}")

    before_override = _count(project_id)
    resp = client.post(
        f"/projects/plan-phases/{mapped['id']}/worklog-overrides",
        json={"jira_issue_key": "WMX-42", "note": "manuell"},
    )
    if resp.status_code != 201:
        _fail("Override create", f"{resp.status_code}: {resp.text}")
    if _count(project_id) <= before_override:
        _fail("Override create history", "kein Eintrag")
    other = _create_phase(project_id, phase_type="Andere")
    resp = client.post(
        f"/projects/plan-phases/{other['id']}/worklog-overrides",
        json={"jira_issue_key": "WMX-42", "note": "verschoben"},
    )
    if resp.status_code != 201:
        _fail("Override move", f"{resp.status_code}: {resp.text}")
    moved_ov = [
        r
        for r in _rows(project_id)
        if r.get("entity_type") == "worklog_override" and r["feld"] == "plan_phase_id" and r["action"] == "updated"
    ]
    if not moved_ov:
        _fail("Override move history", "plan_phase_id-Änderung fehlt")
    resp = client.delete(f"/projects/plan-phases/{other['id']}/worklog-overrides/WMX-42")
    if resp.status_code != 204:
        _fail("Override delete", f"{resp.status_code}: {resp.text}")
    if not any(r.get("entity_type") == "worklog_override" and r.get("action") == "deleted" for r in _rows(project_id)):
        _fail("Override delete history", "Eintrag fehlt")

    print("8/12  History ist project-scoped und chronologisch ...")
    other_id = _create_project("Anderes Projekt")
    mine = {r["id"] for r in _rows(project_id)}
    theirs = {r["id"] for r in _rows(other_id)}
    if mine & theirs:
        _fail("Project scope", f"überlappende History-IDs: {mine & theirs}")
    ordered = _rows(project_id)
    timestamps = [r["geaendert_am"] for r in ordered]
    if timestamps != sorted(timestamps, reverse=True):
        _fail("Chronologie", "GET /history ist nicht absteigend nach geaendert_am")

    print("9/12  Tags an einer Phase werden historisiert ...")
    tagged = _create_phase(project_id, phase_type="Getaggt")
    resp = client.put(f"/projects/plan-phases/{tagged['id']}", json={"tags": ["Kunde", "GoLive"]})
    if resp.status_code != 200:
        _fail("Tags", f"{resp.status_code}: {resp.text}")
    tag_rows = [r for r in _rows(project_id) if r["feld"] == "tags" and r.get("entity_id") == tagged["id"]]
    if not tag_rows or "Kunde" not in (tag_rows[0]["neuer_wert"] or ""):
        _fail("Tags history", f"{tag_rows}")

    print("10/12  Kommentare erzeugen KEINE doppelte History ...")
    before = _count(project_id)
    resp = client.post(f"/projects/{project_id}/comments", json={"text": "Nur ein Kommentar"})
    if resp.status_code not in (200, 201):
        _fail("Comment", f"{resp.status_code}: {resp.text}")
    extra = [r for r in _rows(project_id)[0 : _count(project_id) - before + 5] if r.get("entity_type") == "comment"]
    if _count(project_id) != before:
        # erlaubt: keine neuen Zeilen. Falls doch welche, dürfen sie nicht comment sein.
        if any(r.get("entity_type") == "comment" for r in _rows(project_id)):
            _fail("Comment noise", f"Kommentare dürfen nicht als History gespeichert werden: {extra}")
        if _count(project_id) != before:
            _fail("Comment noise", f"History wuchs von {before} auf {_count(project_id)}")

    print("11/12  Baseline-API bleibt (Legacy Compat), schreibt aber kein Planstand-Event ...")
    before = _count(project_id)
    resp = client.post(f"/projects/{project_id}/baselines", json={"name": "Legacy-Snapshot"})
    if resp.status_code != 201:
        _fail("Baseline compat", f"{resp.status_code}: {resp.text}")
    snapshot = resp.json()
    if any(r.get("entity_type") == "baseline_snapshot" for r in _rows(project_id)):
        _fail("Planstand event", "POST /baselines darf keine History 'Planstand erstellt' schreiben")
    if _count(project_id) != before:
        _fail("Planstand event", f"History wuchs durch Baseline-Create von {before} auf {_count(project_id)}")
    listed = client.get(f"/projects/{project_id}/baselines")
    if listed.status_code != 200 or not any(b["id"] == snapshot["id"] for b in listed.json()):
        _fail("Baseline list", "Legacy-GET muss weiter funktionieren")

    print("12/12  FK-Semantik: History überlebt Phasen-Delete; actor_person_id SET NULL ...")
    db = SessionLocal()
    try:
        if not _postgres_url:
            from sqlalchemy import event, text

            if engine.dialect.name == "sqlite":
                with engine.connect() as conn:
                    conn.execute(text("PRAGMA foreign_keys=ON"))
                    conn.commit()

        actor = models.Person(display_name="Actor")
        db.add(actor)
        db.flush()
        entry = models.PlanHistory(
            project_id=project_id,
            bereich="stammdaten",
            feld="name",
            alter_wert="a",
            neuer_wert="b",
            geaendert_am=history.now_iso(),
            entity_type="project",
            entity_id=project_id,
            entity_label="History-Projekt v2",
            action="updated",
            actor_person_id=actor.id,
        )
        db.add(entry)
        db.commit()
        entry_id = entry.id
        actor_id = actor.id
    finally:
        db.close()

    db = SessionLocal()
    try:
        db.query(models.Person).filter(models.Person.id == actor_id).delete()
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        _fail("actor FK", f"Person-Delete mit History-Actor muss SET NULL sein: {exc}")
    finally:
        db.close()

    db = SessionLocal()
    try:
        surviving = db.get(models.PlanHistory, entry_id)
        if surviving is None:
            _fail("actor FK", "History-Eintrag verschwand mit der Person")
        if surviving.actor_person_id is not None:
            _fail("actor FK", f"erwartet SET NULL, ist {surviving.actor_person_id}")
    finally:
        db.close()

    # History bleibt nach Phasen-Delete lesbar (plan_phase_id SET NULL, Label erhalten).
    survivors = [r for r in _rows(project_id) if r.get("action") == "deleted" and r.get("entity_type") == "plan_phase"]
    if not survivors:
        _fail("Delete understandability", "gelöschte Phase hinterließ keinen History-Eintrag")
    if not survivors[0].get("entity_label") and not survivors[0].get("alter_wert"):
        _fail("Delete understandability", f"Delete ohne Label: {survivors[0]}")

    print(
        f"[PASS] P20.3 Project History ({dialect}): create/update/delete/bundling/noise/immutable/"
        "project-scoped/FK"
    )


if __name__ == "__main__":
    main()
