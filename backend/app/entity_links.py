"""Zentrale Tag-/Dokument-Verknüpfungslogik, gemeinsam genutzt von routers/documents.py und
routers/communication.py (siehe CONCEPT.md Abschnitt 6a). Ein Router importiert absichtlich
nicht vom anderen - beide importieren nur von hier."""

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models, schemas

# Kurzform je entity_type für die "Verwendet in"-Anzeige (siehe _resolve_entity_label).
_ENTITY_LABEL_PREFIX = {
    "comment": "Notiz",
    "decision": "Entscheidung",
    "risk": "Risiko",
    "meeting_minutes": "Meeting",
    "task": "Aufgabe",
    "blocker": "Blocker",
    "plan_phase": "Planphase",
    "milestone": "Milestone",
}

# Registry für den Knowledge Query Layer (Phase 15, siehe CONCEPT.md Abschnitt 12/46):
# entity_type -> (Modell, Feld mit dem anzeigbaren Titel/Text). Deckt dasselbe Vokabular wie
# TagLink/DocumentLink/EntityRelation ab (schemas.EntityType).
_ENTITY_REGISTRY: dict[str, tuple[type, str]] = {
    "comment": (models.Comment, "text"),
    "decision": (models.Decision, "titel"),
    "risk": (models.Risk, "titel"),
    "meeting_minutes": (models.MeetingMinutes, "titel"),
    "task": (models.Task, "titel"),
    "document": (models.Document, "dateiname"),
    "blocker": (models.Blocker, "title"),
    "plan_phase": (models.PlanPhase, "phase_type"),
    "milestone": (models.Milestone, "name"),
}

# Öffentliches Vokabular für Aufrufer außerhalb dieses Moduls (z.B. routers/knowledge.py,
# routers/communication.py), ohne das interne Registry-Dict direkt zu exponieren.
ENTITY_TYPES: tuple[str, ...] = tuple(_ENTITY_REGISTRY.keys())

# Zeitstempelfeld je entity_type für den Activity Feed (Phase 16) und Tag-Dossiers
# (Phase 24, Master-MD Abschnitt 44 "Activity Integration"). Ursprünglich lokal in
# routers/communication.py, hierher verschoben, damit routers/knowledge.py dieselbe
# Zeitbasis nutzen kann statt eine zweite Registry zu pflegen. "document" fehlt bewusst
# (Dateien sind keine Aktivität) - "plan_phase"/"milestone" ergänzt (Phase 17 lieferte die
# Modelle, war hier aber noch nicht nachgezogen worden).
_ACTIVITY_TIMESTAMP_FIELD: dict[str, str] = {
    "comment": "erstellt_am",
    "decision": "erstellt_am",
    "risk": "erstellt_am",
    "meeting_minutes": "erstellt_am",
    "task": "erstellt_am",
    "blocker": "erstellt_am",
    "plan_phase": "erstellt_am",
    "milestone": "erstellt_am",
}

ACTIVITY_ENTITY_TYPES: tuple[str, ...] = tuple(_ACTIVITY_TIMESTAMP_FIELD.keys())


def model_for(entity_type: str) -> type | None:
    """Das SQLAlchemy-Modell eines entity_type, falls im Knowledge-Layer-Vokabular bekannt."""
    model, _ = _ENTITY_REGISTRY.get(entity_type, (None, None))
    return model


def timestamp_for(db: Session, entity_type: str, entity_id: int) -> str | None:
    """Aktivitäts-Zeitstempel einer Entität, falls entity_type im Activity-Vokabular bekannt
    ist und die Zeile noch existiert."""
    field = _ACTIVITY_TIMESTAMP_FIELD.get(entity_type)
    if field is None:
        return None
    model = model_for(entity_type)
    if model is None:
        return None
    row = db.get(model, entity_id)
    return getattr(row, field, None) if row is not None else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sync_tags(db: Session, entity_type: str, entity_id: int, tag_names: list[str]) -> None:
    """Ersetzt die Tag-Zuordnung einer Entität durch tag_names (Upsert der Tag-Zeilen,
    Replace der TagLink-Zeilen)."""
    db.query(models.TagLink).filter(
        models.TagLink.entity_type == entity_type, models.TagLink.entity_id == entity_id
    ).delete()

    seen: set[str] = set()
    for raw in tag_names:
        name = raw.strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        tag = db.query(models.Tag).filter(models.Tag.name == name).first()
        if tag is None:
            tag = models.Tag(name=name)
            db.add(tag)
            db.flush()
        db.add(models.TagLink(tag_id=tag.id, entity_type=entity_type, entity_id=entity_id))


def tags_for(db: Session, entity_type: str, entity_id: int) -> list[str]:
    rows = (
        db.query(models.Tag.name)
        .join(models.TagLink, models.TagLink.tag_id == models.Tag.id)
        .filter(models.TagLink.entity_type == entity_type, models.TagLink.entity_id == entity_id)
        .order_by(models.Tag.name)
        .all()
    )
    return [r[0] for r in rows]


def _resolve_entity_label(db: Session, entity_type: str, entity_id: int) -> str:
    prefix = _ENTITY_LABEL_PREFIX.get(entity_type, entity_type)
    text: str | None = None
    if entity_type == "comment":
        row = db.get(models.Comment, entity_id)
        text = row.text[:60] if row else None
    elif entity_type == "decision":
        row = db.get(models.Decision, entity_id)
        text = row.titel if row else None
    elif entity_type == "risk":
        row = db.get(models.Risk, entity_id)
        text = row.titel if row else None
    elif entity_type == "meeting_minutes":
        row = db.get(models.MeetingMinutes, entity_id)
        text = row.titel if row else None
    elif entity_type == "task":
        row = db.get(models.Task, entity_id)
        text = row.titel if row else None
    elif entity_type == "blocker":
        row = db.get(models.Blocker, entity_id)
        text = row.title if row else None
    elif entity_type == "plan_phase":
        row = db.get(models.PlanPhase, entity_id)
        text = row.phase_type if row else None
    elif entity_type == "milestone":
        row = db.get(models.Milestone, entity_id)
        text = row.name if row else None
    if text is None:
        return f"{prefix} #{entity_id} (gelöscht)"
    return f"{prefix} „{text}“"


def documents_for(db: Session, entity_type: str, entity_id: int) -> list[schemas.DocumentOut]:
    doc_ids = (
        db.query(models.DocumentLink.document_id)
        .filter(models.DocumentLink.entity_type == entity_type, models.DocumentLink.entity_id == entity_id)
        .all()
    )
    documents = db.query(models.Document).filter(models.Document.id.in_([d[0] for d in doc_ids])).all()
    return [document_out(db, d) for d in documents]


def document_out(db: Session, document: models.Document) -> schemas.DocumentOut:
    links = db.query(models.DocumentLink).filter(models.DocumentLink.document_id == document.id).all()
    used_in = [
        schemas.DocumentUsageOut(
            entity_type=link.entity_type,
            entity_id=link.entity_id,
            label=_resolve_entity_label(db, link.entity_type, link.entity_id),
        )
        for link in links
    ]
    return schemas.DocumentOut(
        id=document.id,
        project_id=document.project_id,
        dateiname=document.dateiname,
        mimetype=document.mimetype,
        groesse_bytes=document.groesse_bytes,
        hochgeladen_von=document.hochgeladen_von,
        hochgeladen_am=document.hochgeladen_am,
        tags=tags_for(db, "document", document.id),
        used_in=used_in,
    )


def create_document_link(db: Session, document_id: int, entity_type: str, entity_id: int) -> models.DocumentLink:
    existing = (
        db.query(models.DocumentLink)
        .filter(
            models.DocumentLink.document_id == document_id,
            models.DocumentLink.entity_type == entity_type,
            models.DocumentLink.entity_id == entity_id,
        )
        .first()
    )
    if existing is not None:
        return existing
    link = models.DocumentLink(
        document_id=document_id, entity_type=entity_type, entity_id=entity_id, erstellt_am=_now()
    )
    db.add(link)
    db.flush()
    return link


def delete_links_for_entity(db: Session, entity_type: str, entity_id: int) -> None:
    """Löscht TagLink/DocumentLink-Zeilen einer gelöschten Entität - lässt die verlinkten
    Document-Zeilen selbst unangetastet (zentrale Ablage bleibt bestehen, siehe
    CONCEPT.md Abschnitt 6a)."""
    db.query(models.TagLink).filter(
        models.TagLink.entity_type == entity_type, models.TagLink.entity_id == entity_id
    ).delete()
    db.query(models.DocumentLink).filter(
        models.DocumentLink.entity_type == entity_type, models.DocumentLink.entity_id == entity_id
    ).delete()


def create_relation(
    db: Session,
    source_entity_type: str,
    source_entity_id: int,
    target_entity_type: str,
    target_entity_id: int,
    relation_type: str,
    created_by_person_id: int | None = None,
) -> models.EntityRelation:
    """Legt eine gerichtete, typisierte Beziehung zwischen zwei Entitäten an (z.B. Decision
    `resulted_in` Task), siehe CONCEPT.md Abschnitt 12 (Knowledge Layer)."""
    existing = (
        db.query(models.EntityRelation)
        .filter(
            models.EntityRelation.source_entity_type == source_entity_type,
            models.EntityRelation.source_entity_id == source_entity_id,
            models.EntityRelation.target_entity_type == target_entity_type,
            models.EntityRelation.target_entity_id == target_entity_id,
            models.EntityRelation.relation_type == relation_type,
        )
        .first()
    )
    if existing is not None:
        return existing
    relation = models.EntityRelation(
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        relation_type=relation_type,
        created_at=_now(),
        created_by_person_id=created_by_person_id,
    )
    db.add(relation)
    db.flush()
    return relation


def relations_for(db: Session, entity_type: str, entity_id: int) -> list[models.EntityRelation]:
    """Alle Relationen, in denen die Entität als Quelle oder Ziel auftritt."""
    return (
        db.query(models.EntityRelation)
        .filter(
            (
                (models.EntityRelation.source_entity_type == entity_type)
                & (models.EntityRelation.source_entity_id == entity_id)
            )
            | (
                (models.EntityRelation.target_entity_type == entity_type)
                & (models.EntityRelation.target_entity_id == entity_id)
            )
        )
        .order_by(models.EntityRelation.created_at)
        .all()
    )


def delete_relations_for_entity(db: Session, entity_type: str, entity_id: int) -> None:
    """Löscht EntityRelation-Zeilen einer gelöschten Entität (als Quelle oder Ziel)."""
    db.query(models.EntityRelation).filter(
        (
            (models.EntityRelation.source_entity_type == entity_type)
            & (models.EntityRelation.source_entity_id == entity_id)
        )
        | (
            (models.EntityRelation.target_entity_type == entity_type)
            & (models.EntityRelation.target_entity_id == entity_id)
        )
    ).delete(synchronize_session=False)


# ---------------------------------------------------------------------------
# Knowledge Query Layer (Phase 15, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 46).
# Zentrale strukturierte Zugriffsschicht über alle taggable Entitäten - noch kein
# Vector-RAG/KI-Agent, soll später sowohl UI-Funktionen als auch einen KI-Agenten versorgen.
# ---------------------------------------------------------------------------


def entity_summary(db: Session, entity_type: str, entity_id: int) -> dict | None:
    """Generische Kurzdarstellung einer Entität (entity_type/entity_id/project_id/label)."""
    model, text_field = _ENTITY_REGISTRY.get(entity_type, (None, None))
    if model is None:
        return None
    row = db.get(model, entity_id)
    if row is None:
        return None
    text = getattr(row, text_field)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "project_id": getattr(row, "project_id", None),
        "label": text[:200] if text else None,
    }


def list_entity_summaries(db: Session, entity_type: str, project_id: int | None = None) -> list[dict]:
    """Alle Entitäten eines Typs (optional auf ein Projekt eingeschränkt), inkl. Tags."""
    model, text_field = _ENTITY_REGISTRY.get(entity_type, (None, None))
    if model is None:
        return []
    query = db.query(model)
    if project_id is not None and hasattr(model, "project_id"):
        query = query.filter(model.project_id == project_id)
    rows = query.order_by(model.id).all()
    return [
        {
            "entity_type": entity_type,
            "entity_id": row.id,
            "project_id": getattr(row, "project_id", None),
            "label": ((getattr(row, text_field) or "")[:200]) or None,
            "tags": tags_for(db, entity_type, row.id),
        }
        for row in rows
    ]


def search_entities(db: Session, query_text: str, project_id: int | None = None) -> list[dict]:
    """Volltextsuche über Titel/Text aller taggable Entitäten sowie über Tags - liefert dann
    die damit verknüpften Entitäten. Noch kein Vector-RAG (Master-MD Abschnitt 46), aber seit
    Phase 24 "semantisch" im Sinne von Abschnitt 43 erweitert: ein Treffer in `ai_description`
    oder `synonyms` eines Tags zählt ebenfalls als Treffer (z.B. Suche nach "Produktivstart"
    findet darüber den Tag "GoLive" und dessen Entitäten), erklärbar über den `match`-Grund."""
    like = f"%{query_text}%"
    results: list[dict] = []
    seen: set[tuple[str, int]] = set()

    def _add(entity_type: str, entity_id: int, label: str | None, entity_project_id: int | None, match: str) -> None:
        key = (entity_type, entity_id)
        if key in seen:
            return
        if project_id is not None and entity_project_id is not None and entity_project_id != project_id:
            return
        seen.add(key)
        results.append(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "project_id": entity_project_id,
                "label": label,
                "match": match,
            }
        )

    for entity_type, (model, text_field) in _ENTITY_REGISTRY.items():
        q = db.query(model).filter(getattr(model, text_field).ilike(like))
        if project_id is not None and hasattr(model, "project_id"):
            q = q.filter(model.project_id == project_id)
        for row in q.limit(20).all():
            text = getattr(row, text_field)
            _add(entity_type, row.id, (text or "")[:200] or None, getattr(row, "project_id", None), "text")

    tag_query = db.query(models.Tag).filter(
        or_(
            models.Tag.name.ilike(like),
            models.Tag.synonyms.ilike(like),
            models.Tag.ai_description.ilike(like),
        )
    )
    for tag in tag_query.limit(10).all():
        # Direkter Namenstreffer wird von semantischen Treffern (nur Synonym/AI-Beschreibung)
        # unterschieden, damit der Aufrufer nachvollziehen kann, warum etwas gefunden wurde.
        direct_hit = query_text.lower() in (tag.name or "").lower()
        match_label = f"tag:{tag.name}" if direct_hit else f"tag_semantisch:{tag.name}"
        links = db.query(models.TagLink).filter(models.TagLink.tag_id == tag.id).all()
        for link in links:
            summary = entity_summary(db, link.entity_type, link.entity_id)
            if summary is not None:
                _add(link.entity_type, link.entity_id, summary["label"], summary["project_id"], match_label)

    return results


# ---------------------------------------------------------------------------
# Tag-Dossiers & Related Entities (Phase 24, siehe CONCEPT.md Abschnitt 12.4 / Master-MD
# Abschnitt 44 "dynamische Tag-Sichten" und Abschnitt 40 "Knowledge Layer").
# ---------------------------------------------------------------------------


def resolve_tag(db: Session, name: str) -> models.Tag | None:
    """Löst einen angeforderten Tag-Namen auf einen Tag auf. Exakter Name (case-insensitiv)
    hat Vorrang, sonst Fallback auf einen Synonym-Treffer (Master-MD Abschnitt 43: Tag
    "GoLive" mit Synonymen "Produktivstart"/"Livegang"/"Rollout") - damit findet ein
    Tag-Dossier für "Livegang" denselben Tag wie "GoLive"."""
    name = name.strip()
    if not name:
        return None
    tag = db.query(models.Tag).filter(models.Tag.name.ilike(name)).first()
    if tag is not None:
        return tag
    return db.query(models.Tag).filter(models.Tag.synonyms.ilike(f"%{name}%")).first()


def entities_by_tags(
    db: Session, tag_names: list[str], mode: str = "and", project_id: int | None = None
) -> list[dict]:
    """Entitäten, die ALLE (`mode="and"`) bzw. IRGENDEINE (`mode="or"`) der angegebenen Tags
    tragen - Grundlage für Tag-Dossiers und kombinierte Tag-Sichten wie "#Kunde + #GoLive"
    (Master-MD Abschnitt 44). Ein einzelner Tag-Name ergibt das einfache Tag-Dossier aus dem
    Beispiel in Abschnitt 44 ("#Schnittstelle -> 4 Diskussionen, 3 Entscheidungen, ...")."""
    resolved_ids: list[int] = []
    for raw_name in tag_names:
        tag = resolve_tag(db, raw_name)
        if tag is not None:
            resolved_ids.append(tag.id)
    if not resolved_ids:
        return []

    distinct_ids = set(resolved_ids)
    if mode == "and" and len(distinct_ids) < len(tag_names):
        # Mindestens einer der angeforderten Tags existiert nicht -> AND kann nie erfüllt sein.
        return []

    rows = (
        db.query(
            models.TagLink.entity_type,
            models.TagLink.entity_id,
            models.TagLink.tag_id,
        )
        .filter(models.TagLink.tag_id.in_(distinct_ids))
        .all()
    )
    matched_ids: dict[tuple[str, int], set[int]] = {}
    for entity_type, entity_id, tag_id in rows:
        matched_ids.setdefault((entity_type, entity_id), set()).add(tag_id)

    required = len(distinct_ids) if mode == "and" else 1
    results: list[dict] = []
    for (entity_type, entity_id), ids in matched_ids.items():
        if len(ids) < required:
            continue
        summary = entity_summary(db, entity_type, entity_id)
        if summary is None:
            continue
        if project_id is not None and summary["project_id"] is not None and summary["project_id"] != project_id:
            continue
        summary["tags"] = tags_for(db, entity_type, entity_id)
        results.append(summary)

    results.sort(key=lambda s: (s["entity_type"], s["entity_id"]))
    return results


def related_entities(db: Session, entity_type: str, entity_id: int, limit: int = 10) -> list[dict]:
    """Andere Entitäten mit den meisten gemeinsamen Tags - einfachste erklärbare Ähnlichkeit
    ohne Vector-/Embedding-Schicht (Master-MD Abschnitt 46: "noch kein Vector-RAG"), gedacht
    als "Related Entities" auf der Wissenskarte einer Entität (Abschnitt 40)."""
    own_tag_ids = [
        row[0]
        for row in db.query(models.TagLink.tag_id)
        .filter(models.TagLink.entity_type == entity_type, models.TagLink.entity_id == entity_id)
        .all()
    ]
    if not own_tag_ids:
        return []

    rows = (
        db.query(models.TagLink.entity_type, models.TagLink.entity_id, models.Tag.name)
        .join(models.Tag, models.Tag.id == models.TagLink.tag_id)
        .filter(models.TagLink.tag_id.in_(own_tag_ids))
        .all()
    )
    shared: dict[tuple[str, int], set[str]] = {}
    for other_type, other_id, tag_name in rows:
        if other_type == entity_type and other_id == entity_id:
            continue
        shared.setdefault((other_type, other_id), set()).add(tag_name)

    scored: list[tuple[int, dict, list[str]]] = []
    for (other_type, other_id), tag_names_set in shared.items():
        summary = entity_summary(db, other_type, other_id)
        if summary is None:
            continue
        scored.append((len(tag_names_set), summary, sorted(tag_names_set)))
    scored.sort(key=lambda item: item[0], reverse=True)

    return [{**summary, "shared_tags": tag_names_out} for _, summary, tag_names_out in scored[:limit]]
