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


@router.get("/tags", response_model=list[schemas.TagOut])
def list_tags(search: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Tag)
    if search:
        query = query.filter(models.Tag.name.ilike(f"%{search}%"))
    tags = query.order_by(models.Tag.name).limit(50).all()
    return [schemas.TagOut(id=t.id, name=t.name) for t in tags]
