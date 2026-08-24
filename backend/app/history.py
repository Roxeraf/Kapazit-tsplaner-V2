"""Automatische Projekthistorie (P20.3).

Gemeinsames Schreibmodul für PlanHistory. Router importieren von hier, nicht voneinander
(siehe CONCEPT.md Cross-Router-Regel). Keine zweite Audit-Engine: bestehende PlanHistory-
Tabelle wird um optionale Identifikationsspalten erweitert und an den fachlichen
Schreibpfaden aufgerufen.

Fachliches Prinzip: USER ACTION → DOMAIN CHANGE → AUTOMATIC HISTORY ENTRY.

Kein Auth-Kontext im aktuellen System (CONCEPT.md Abschnitt 8/15) — actor_person_id bleibt
deshalb nullable und wird hier nicht gesetzt. History-Einträge sind immutable: dieses Modul
bietet nur Insert/Read-Helfer, kein Update/Delete einzelner Einträge.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from . import models

# Source-of-Truth-Felder je entity_type. Alles andere (Timestamps, Caches, derived values,
# interne IDs als Selbstzweck) ist Noise und wird nicht historisiert.
TRACKED_FIELDS: dict[str, tuple[str, ...]] = {
    "project": (
        "name",
        "kunde",
        "status",
        "projektleiter_person_id",
        "start_monat",
        "anzahl_monate",
        "jira_component",
    ),
    "plan_phase": (
        "phase_type",
        "forecast_start",
        "forecast_end",
        "status",
        "plan_fte",
        "parent_phase_id",
        "owner_person_id",
        "owner_team_id",
        "reihenfolge",
        "jira_label",
    ),
    "resource_assignment": ("fte", "person_id"),
    "milestone": ("name", "forecast_date", "status", "plan_phase_id", "owner_person_id", "owner_team_id"),
    "task": ("titel", "status", "beschreibung", "zustaendig_person_id", "faellig_am", "plan_phase_id"),
    "blocker": ("title", "status", "description", "severity", "owner_person_id", "plan_phase_id"),
    "decision": ("titel", "status", "beschreibung", "begruendung", "entschieden_von_person_id", "plan_phase_id"),
    "worklog_override": ("jira_issue_key", "plan_phase_id"),
    "document_link": ("document_id", "entity_type", "entity_id"),
}

# Bereich bleibt die bestehende PlanHistory-Spalte (String(20)) — View-Filter im Frontend
# mappen diese Werte auf Planung/Kapazität/Team/Zusammenarbeit. Alte Werte
# (phase/fte/stammdaten/phase_struktur/phase_subtree_delete) bleiben gültig.
_BEREICH: dict[str, str] = {
    "project": "stammdaten",
    "plan_phase": "plan_phase",
    "resource_assignment": "assignment",
    "milestone": "milestone",
    "task": "task",
    "blocker": "blocker",
    "decision": "decision",
    "document_link": "document_link",
    "worklog_override": "jira_mapping",
    "tag_link": "tag_link",
}

# Beim Anlegen nur die Felder, die den Eintrag verständlich machen — nicht jedes
# Source-of-Truth-Feld als "null → Wert" (CONCEPT.md P20.3 Create-Semantik).
CREATE_DETAIL_FIELDS: dict[str, tuple[str, ...]] = {
    "project": ("name", "kunde", "status", "start_monat", "anzahl_monate"),
    "plan_phase": ("phase_type", "forecast_start", "forecast_end", "plan_fte"),
    "resource_assignment": ("fte",),
    "milestone": ("name", "forecast_date", "status"),
    "task": ("titel", "status"),
    "blocker": ("title", "status"),
    "decision": ("titel", "status"),
    "worklog_override": ("jira_issue_key", "plan_phase_id"),
    "document_link": ("document_id", "entity_type", "entity_id"),
}

# Marker-Feld für Create/Delete ohne Feldliste (eine verständliche Zeile statt
# "field x changed from null to value").
EVENT_FIELD = "_entity"

ACTION_CREATED = "created"
ACTION_UPDATED = "updated"
ACTION_DELETED = "deleted"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_batch_id() -> str:
    return str(uuid.uuid4())


def stringify(value: Any) -> str | None:
    """Kanonische String-Form für Alt-/Neu-Werte. None bleibt None (nicht "None")."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text if text else "0"
    if isinstance(value, (list, tuple)):
        return ", ".join(stringify(v) or "" for v in value).strip(", ") or None
    return str(value)


def values_equal(old: Any, new: Any) -> bool:
    return stringify(old) == stringify(new)


def snapshot(obj: Any, entity_type: str) -> dict[str, Any]:
    fields = TRACKED_FIELDS.get(entity_type, ())
    return {field: getattr(obj, field, None) for field in fields}


def record_rows(
    db: Session,
    *,
    project_id: int,
    entity_type: str,
    action: str,
    changes: Iterable[tuple[str, Any, Any]],
    entity_id: int | None = None,
    entity_label: str | None = None,
    plan_phase_id: int | None = None,
    subproject_id: int | None = None,
    batch_id: str | None = None,
    kommentar_id: int | None = None,
    actor_person_id: int | None = None,
    bereich: str | None = None,
    timestamp: str | None = None,
) -> str | None:
    """Schreibt PlanHistory-Zeilen für tatsächlich geänderte Felder. Gibt die verwendete
    batch_id zurück, oder None wenn nichts zu schreiben war (No-Op)."""
    rows = [(feld, alt, neu) for feld, alt, neu in changes if not values_equal(alt, neu)]
    if not rows:
        return None
    used_batch = batch_id or new_batch_id()
    used_ts = timestamp or now_iso()
    used_bereich = bereich or _BEREICH.get(entity_type, entity_type[:20])
    for feld, alt, neu in rows:
        db.add(
            models.PlanHistory(
                project_id=project_id,
                subproject_id=subproject_id,
                plan_phase_id=plan_phase_id,
                bereich=used_bereich,
                monat=None,
                feld=feld,
                alter_wert=stringify(alt),
                neuer_wert=stringify(neu),
                geaendert_am=used_ts,
                kommentar_id=kommentar_id,
                batch_id=used_batch,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_label=entity_label,
                action=action,
                actor_person_id=actor_person_id,
            )
        )
    return used_batch


def record_created(
    db: Session,
    *,
    project_id: int,
    entity_type: str,
    entity_id: int | None,
    entity_label: str,
    fields: dict[str, Any] | None = None,
    plan_phase_id: int | None = None,
    batch_id: str | None = None,
    actor_person_id: int | None = None,
    timestamp: str | None = None,
) -> str:
    """Create: eine verständliche Entitätszeile plus gesetzte Source-of-Truth-Felder
    (nicht als null→value-Diff, sondern als action=created mit nur neuem Wert)."""
    used_batch = batch_id or new_batch_id()
    tracked = CREATE_DETAIL_FIELDS.get(entity_type, TRACKED_FIELDS.get(entity_type, ()))
    initial = fields or {}
    changes: list[tuple[str, Any, Any]] = [(EVENT_FIELD, None, entity_label)]
    for feld in tracked:
        if feld not in initial:
            continue
        value = initial[feld]
        if value is None or value == "" or value == []:
            continue
        changes.append((feld, None, value))
    record_rows(
        db,
        project_id=project_id,
        entity_type=entity_type,
        action=ACTION_CREATED,
        changes=changes,
        entity_id=entity_id,
        entity_label=entity_label,
        plan_phase_id=plan_phase_id,
        batch_id=used_batch,
        actor_person_id=actor_person_id,
        timestamp=timestamp,
    )
    return used_batch


def record_updated(
    db: Session,
    *,
    project_id: int,
    entity_type: str,
    entity_id: int | None,
    entity_label: str,
    old: dict[str, Any],
    new: dict[str, Any],
    plan_phase_id: int | None = None,
    batch_id: str | None = None,
    kommentar_id: int | None = None,
    actor_person_id: int | None = None,
    timestamp: str | None = None,
    extra_changes: Iterable[tuple[str, Any, Any]] = (),
) -> str | None:
    """Update: nur tatsächlich geänderte, getrackte Felder. No-Op ohne Diff."""
    tracked = TRACKED_FIELDS.get(entity_type, ())
    keys = set(tracked) | set(old) | set(new)
    changes: list[tuple[str, Any, Any]] = []
    for feld in keys:
        if feld not in tracked:
            continue
        if feld not in new and feld not in old:
            continue
        changes.append((feld, old.get(feld), new.get(feld)))
    changes.extend(extra_changes)
    return record_rows(
        db,
        project_id=project_id,
        entity_type=entity_type,
        action=ACTION_UPDATED,
        changes=changes,
        entity_id=entity_id,
        entity_label=entity_label,
        plan_phase_id=plan_phase_id,
        batch_id=batch_id,
        kommentar_id=kommentar_id,
        actor_person_id=actor_person_id,
        timestamp=timestamp,
    )


def record_deleted(
    db: Session,
    *,
    project_id: int,
    entity_type: str,
    entity_id: int | None,
    entity_label: str,
    fields: dict[str, Any] | None = None,
    plan_phase_id: int | None = None,
    batch_id: str | None = None,
    actor_person_id: int | None = None,
    timestamp: str | None = None,
    bereich: str | None = None,
) -> str:
    """Delete: Label und relevante letzte Feldwerte sichern, bevor die Entität weg ist.
    plan_phase_id darf None sein, wenn die Phase selbst gelöscht wird (FK SET NULL)."""
    used_batch = batch_id or new_batch_id()
    tracked = TRACKED_FIELDS.get(entity_type, ())
    last = fields or {}
    changes: list[tuple[str, Any, Any]] = [(EVENT_FIELD, entity_label, None)]
    for feld in tracked:
        if feld not in last:
            continue
        value = last[feld]
        if value is None or value == "" or value == []:
            continue
        changes.append((feld, value, None))
    record_rows(
        db,
        project_id=project_id,
        entity_type=entity_type,
        action=ACTION_DELETED,
        changes=changes,
        entity_id=entity_id,
        entity_label=entity_label,
        plan_phase_id=plan_phase_id,
        batch_id=used_batch,
        actor_person_id=actor_person_id,
        timestamp=timestamp,
        bereich=bereich,
    )
    return used_batch


def record_tag_diff(
    db: Session,
    *,
    project_id: int,
    entity_type: str,
    entity_id: int,
    entity_label: str,
    old_tags: list[str],
    new_tags: list[str],
    plan_phase_id: int | None = None,
    batch_id: str | None = None,
    actor_person_id: int | None = None,
) -> str | None:
    """Tag hinzugefügt/entfernt an einer projektbezogenen Entität. Tag-Katalog-Umbenennungen
    (Admin) gehören NICHT in die Projekthistorie."""
    old_norm = sorted({t.strip() for t in old_tags if t and t.strip()})
    new_norm = sorted({t.strip() for t in new_tags if t and t.strip()})
    if old_norm == new_norm:
        return None
    return record_rows(
        db,
        project_id=project_id,
        entity_type=entity_type,
        action=ACTION_UPDATED,
        changes=[("tags", old_norm, new_norm)],
        entity_id=entity_id,
        entity_label=entity_label,
        plan_phase_id=plan_phase_id,
        batch_id=batch_id,
        actor_person_id=actor_person_id,
        bereich="tag_link",
    )
