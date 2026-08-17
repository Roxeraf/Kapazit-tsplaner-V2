"""Zentrale Tag-/Dokument-Verknüpfungslogik, gemeinsam genutzt von routers/documents.py und
routers/communication.py (siehe CONCEPT.md Abschnitt 6a). Ein Router importiert absichtlich
nicht vom anderen - beide importieren nur von hier."""

from datetime import datetime, timezone

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
}

# Öffentliches Vokabular für Aufrufer außerhalb dieses Moduls (z.B. routers/knowledge.py,
# routers/communication.py), ohne das interne Registry-Dict direkt zu exponieren.
ENTITY_TYPES: tuple[str, ...] = tuple(_ENTITY_REGISTRY.keys())


def model_for(entity_type: str) -> type | None:
    """Das SQLAlchemy-Modell eines entity_type, falls im Knowledge-Layer-Vokabular bekannt."""
    model, _ = _ENTITY_REGISTRY.get(entity_type, (None, None))
    return model


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
    """Einfache Volltextsuche über Titel/Text aller taggable Entitäten sowie über Tag-Namen
    (liefert dann die damit verknüpften Entitäten) - noch kein Vector-RAG, siehe Master-MD
    Abschnitt 46."""
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

    for tag in db.query(models.Tag).filter(models.Tag.name.ilike(like)).limit(10).all():
        links = db.query(models.TagLink).filter(models.TagLink.tag_id == tag.id).all()
        for link in links:
            summary = entity_summary(db, link.entity_type, link.entity_id)
            if summary is not None:
                _add(
                    link.entity_type, link.entity_id, summary["label"], summary["project_id"], f"tag:{tag.name}"
                )

    return results
