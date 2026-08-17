from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import documents_storage, entity_links, models, schemas
from ..database import get_db

router = APIRouter(tags=["documents"])


def _get_document_or_404(db: Session, document_id: int) -> models.Document:
    doc = db.get(models.Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    return doc


@router.post("/projects/{project_id}/documents", response_model=schemas.DocumentOut, status_code=201)
def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    tags: str | None = Form(None),
    entity_type: str | None = Form(None),
    entity_id: int | None = Form(None),
    hochgeladen_von: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Einziger Upload-Pfad im gesamten Projekt (siehe CONCEPT.md Abschnitt 6a) - egal ob
    Direkt-Upload im Dokumente-Tab oder Anhang an eine Notiz/Entscheidung/Risiko/
    Meetingprotokoll (dann entity_type+entity_id gesetzt, legt atomar auch den
    DocumentLink an)."""
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    if (entity_type is None) != (entity_id is None):
        raise HTTPException(status_code=422, detail="entity_type und entity_id müssen zusammen gesetzt werden")

    speicherpfad, groesse, mimetype = documents_storage.save_upload(project_id, file)
    document = models.Document(
        project_id=project_id,
        dateiname=file.filename or "datei",
        speicherpfad=speicherpfad,
        mimetype=mimetype,
        groesse_bytes=groesse,
        hochgeladen_von=hochgeladen_von,
        hochgeladen_am=datetime.now(timezone.utc).isoformat(),
    )
    db.add(document)
    db.flush()

    if tags:
        entity_links.sync_tags(db, "document", document.id, [t.strip() for t in tags.split(",")])
    if entity_type is not None and entity_id is not None:
        entity_links.create_document_link(db, document.id, entity_type, entity_id)

    db.commit()
    db.refresh(document)
    return entity_links.document_out(db, document)


@router.get("/projects/{project_id}/documents", response_model=list[schemas.DocumentOut])
def list_documents(project_id: int, search: str | None = None, tag: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Document).filter(models.Document.project_id == project_id)
    if search:
        query = query.filter(models.Document.dateiname.ilike(f"%{search}%"))
    documents = query.order_by(models.Document.hochgeladen_am.desc()).all()

    results = [entity_links.document_out(db, d) for d in documents]
    if tag:
        results = [d for d in results if tag in d.tags]
    return results


@router.get("/documents/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db)):
    document = _get_document_or_404(db, document_id)
    path = documents_storage.resolve_path(document.speicherpfad)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Datei nicht (mehr) auf dem Server vorhanden")
    return FileResponse(path=path, filename=document.dateiname, media_type=document.mimetype or "application/octet-stream")


@router.put("/documents/{document_id}", response_model=schemas.DocumentOut)
def update_document(document_id: int, payload: schemas.DocumentUpdate, db: Session = Depends(get_db)):
    document = _get_document_or_404(db, document_id)
    if payload.dateiname is not None:
        document.dateiname = payload.dateiname
    if payload.tags is not None:
        entity_links.sync_tags(db, "document", document.id, payload.tags)
    db.commit()
    db.refresh(document)
    return entity_links.document_out(db, document)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Löscht Datei + Document-Zeile + alle zugehörigen DocumentLink/TagLink-Zeilen. Das
    Frontend zeigt vorher die "Verwendet in"-Liste im Confirm-Dialog (siehe DocumentOut.used_in)."""
    document = _get_document_or_404(db, document_id)
    db.query(models.DocumentLink).filter(models.DocumentLink.document_id == document_id).delete()
    db.query(models.TagLink).filter(models.TagLink.entity_type == "document", models.TagLink.entity_id == document_id).delete()
    documents_storage.delete_file(document.speicherpfad)
    db.delete(document)
    db.commit()


@router.post("/document-links", response_model=schemas.DocumentLinkOut, status_code=201)
def create_document_link(payload: schemas.DocumentLinkCreate, db: Session = Depends(get_db)):
    """Verknüpft ein bereits existierendes Document mit einer weiteren Entität (kein
    Re-Upload) - z.B. eine Datei aus dem Dokumente-Tab an ein zusätzliches Risiko hängen."""
    document = _get_document_or_404(db, payload.document_id)
    link = entity_links.create_document_link(db, document.id, payload.entity_type, payload.entity_id)
    db.commit()
    return schemas.DocumentLinkOut(
        id=link.id, document_id=link.document_id, entity_type=link.entity_type, entity_id=link.entity_id,
        erstellt_am=link.erstellt_am,
    )


@router.delete("/document-links/{link_id}", status_code=204)
def delete_document_link(link_id: int, db: Session = Depends(get_db)):
    """Entfernt nur die Verknüpfung - die Datei/das Document bleibt in der zentralen
    Ablage bestehen (siehe CONCEPT.md Abschnitt 6a)."""
    link = db.get(models.DocumentLink, link_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Verknüpfung nicht gefunden")
    db.delete(link)
    db.commit()


def _tag_out(t: models.Tag) -> schemas.TagOut:
    return schemas.TagOut(
        id=t.id,
        name=t.name,
        category_id=t.category_id,
        description=t.description,
        color=t.color,
        active=t.active,
        ai_relevant=t.ai_relevant,
        ai_description=t.ai_description,
        synonyms=[s.strip() for s in t.synonyms.split(",")] if t.synonyms else [],
    )


@router.get("/tags", response_model=list[schemas.TagOut])
def list_tags(search: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Tag)
    if search:
        query = query.filter(models.Tag.name.ilike(f"%{search}%"))
    tags = query.order_by(models.Tag.name).limit(50).all()
    return [_tag_out(t) for t in tags]


@router.post("/tags", response_model=schemas.TagOut, status_code=201)
def create_tag(payload: schemas.TagCreate, db: Session = Depends(get_db)):
    if db.query(models.Tag).filter(models.Tag.name == payload.name).first() is not None:
        raise HTTPException(status_code=409, detail="Tag mit diesem Namen existiert bereits")
    if payload.category_id is not None and db.get(models.TagCategory, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="Tag-Kategorie nicht gefunden")
    values = payload.model_dump(exclude={"synonyms"})
    values["synonyms"] = ", ".join(value.strip() for value in payload.synonyms if value.strip()) or None
    tag = models.Tag(**values)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _tag_out(tag)


@router.patch("/tags/{tag_id}", response_model=schemas.TagOut)
def update_tag(tag_id: int, payload: schemas.TagUpdate, db: Session = Depends(get_db)):
    tag = db.get(models.Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag nicht gefunden")
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes and changes["category_id"] is not None:
        if db.get(models.TagCategory, changes["category_id"]) is None:
            raise HTTPException(status_code=404, detail="Tag-Kategorie nicht gefunden")
    if "synonyms" in changes:
        synonyms = changes.pop("synonyms")
        tag.synonyms = ", ".join(s.strip() for s in synonyms if s.strip()) if synonyms else None
    for field, value in changes.items():
        setattr(tag, field, value)
    db.commit()
    db.refresh(tag)
    return _tag_out(tag)


@router.get("/tag-categories", response_model=list[schemas.TagCategoryOut])
def list_tag_categories(db: Session = Depends(get_db)):
    categories = db.query(models.TagCategory).order_by(models.TagCategory.name).all()
    return [
        schemas.TagCategoryOut(id=c.id, name=c.name, description=c.description) for c in categories
    ]


@router.post("/tag-categories", response_model=schemas.TagCategoryOut, status_code=201)
def create_tag_category(payload: schemas.TagCategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(models.TagCategory).filter(models.TagCategory.name == payload.name).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Tag-Kategorie mit diesem Namen existiert bereits")
    category = models.TagCategory(name=payload.name, description=payload.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return schemas.TagCategoryOut(id=category.id, name=category.name, description=category.description)
