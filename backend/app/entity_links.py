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
}


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
