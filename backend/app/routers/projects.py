from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import documents_storage, entity_links, jira_sync, models, schemas
from ..constants import PHASE_CODES, berechne_monate
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


def _log_change(
    db: Session,
    *,
    project_id: int,
    subproject_id: int | None,
    bereich: str,
    monat: str | None,
    feld: str,
    alt: str | None,
    neu: str | None,
    kommentar_id: int | None,
    batch_id: str | None = None,
) -> None:
    """Schreibt einen PlanHistory-Eintrag, wenn sich ein Wert tatsächlich geändert hat.

    batch_id gruppiert alle Einträge eines Speichern-Klicks zu einer "Revision" für die
    Historie-Ansicht (siehe HistoryTimeline.tsx) - unabhängig von kommentar_id, das die
    fachliche Begründung ist (optional).
    """
    if alt == neu:
        return
    db.add(
        models.PlanHistory(
            project_id=project_id,
            subproject_id=subproject_id,
            bereich=bereich,
            monat=monat,
            feld=feld,
            alter_wert=alt,
            neuer_wert=neu,
            geaendert_am=datetime.now(timezone.utc).isoformat(),
            kommentar_id=kommentar_id,
            batch_id=batch_id,
        )
    )


def _phasen_dict(gantt_phases) -> dict[str, list[str]]:
    phasen: dict[str, list[str]] = {}
    for gp in gantt_phases:
        phasen.setdefault(gp.monat, []).append(gp.phase_code)
    return phasen


def _subproject_detail(sp: models.Subproject) -> schemas.SubprojectDetail:
    fte = {f.monat: f.wert_soll for f in sp.fte_plan}
    return schemas.SubprojectDetail(
        id=sp.id,
        name=sp.name,
        reihenfolge=sp.reihenfolge,
        phasen=_phasen_dict(sp.gantt_phases),
        fte=fte,
    )


def _project_phasen(p: models.Project) -> dict[str, list[str]]:
    """Gantt-Phasen auf Projekt-Ebene.

    Hat das Projekt Teilprojekte, ist die Projekt-Zeile die Zusammenfassung daraus (ein Monat
    zeigt Phase X, wenn mindestens ein Teilprojekt sie hat) statt einer eigenen, unabhängigen
    Eintragung — konsistent zur FTE-Summe in _project_fte(). Ohne Teilprojekte bleibt die direkt
    am Projekt gepflegte Phasenliste (project_gantt_phases) maßgeblich.
    """
    if p.subprojects:
        union: dict[str, set[str]] = {}
        for sp in p.subprojects:
            for gp in sp.gantt_phases:
                union.setdefault(gp.monat, set()).add(gp.phase_code)
        return {monat: sorted(codes) for monat, codes in union.items()}
    return _phasen_dict(p.gantt_phases)


def _project_fte(p: models.Project) -> dict[str, float]:
    """FTE-Soll auf Projekt-Ebene.

    Hat das Projekt Teilprojekte (Feinplanung), ist die Projekt-Zeile die Summe daraus statt
    eines eigenen manuellen Werts — sonst könnten Projekt- und Teilprojekt-Ebene auseinanderlaufen.
    Ohne Teilprojekte bleibt der manuell auf Projekt-Ebene eingetragene Wert (project_fte_plan)
    maßgeblich (siehe PUT /projects/{id}/fte).
    """
    if p.subprojects:
        summe: dict[str, float] = {}
        for sp in p.subprojects:
            for f in sp.fte_plan:
                summe[f.monat] = summe.get(f.monat, 0) + f.wert_soll
        return {monat: round(wert, 2) for monat, wert in summe.items()}
    return {f.monat: f.wert_soll for f in p.fte_plan}


def _project_detail(db: Session, p: models.Project) -> schemas.ProjectDetail:
    return schemas.ProjectDetail(
        id=p.id,
        name=p.name,
        kunde=p.kunde,
        start_monat=p.start_monat,
        anzahl_monate=p.anzahl_monate,
        reihenfolge=p.reihenfolge,
        status=p.status,
        projektleiter=p.projektleiter,
        monate=berechne_monate(p.start_monat, p.anzahl_monate),
        jira_component=p.jira_component,
        jira_project_key=p.jira_project_key,
        phasen=_project_phasen(p),
        fte=_project_fte(p),
        aus_teilprojekten=bool(p.subprojects),
        ist=jira_sync.berechne_ist_fte(db, p),
        subprojects=[_subproject_detail(sp) for sp in p.subprojects],
        team_assignments=[
            schemas.ProjectAssignmentOut(
                id=a.id, team_member_id=a.team_member_id, member_name=a.team_member.name, fte=a.fte
            )
            for a in p.assignments
        ],
    )


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


def _get_subproject_or_404(db: Session, subproject_id: int) -> models.Subproject:
    sp = db.get(models.Subproject, subproject_id)
    if sp is None:
        raise HTTPException(status_code=404, detail="Teilprojekt nicht gefunden")
    return sp


def _get_comment_or_404(db: Session, comment_id: int) -> models.Comment:
    comment = db.get(models.Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Kommentar nicht gefunden")
    return comment


@router.get("", response_model=list[schemas.ProjectSummary])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.reihenfolge, models.Project.id).all()
    return [
        schemas.ProjectSummary(
            id=p.id,
            name=p.name,
            kunde=p.kunde,
            start_monat=p.start_monat,
            anzahl_monate=p.anzahl_monate,
            reihenfolge=p.reihenfolge,
            status=p.status,
            projektleiter=p.projektleiter,
            monate=berechne_monate(p.start_monat, p.anzahl_monate),
        )
        for p in projects
    ]


@router.post("", response_model=schemas.ProjectDetail, status_code=201)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    max_reihenfolge = db.query(func.max(models.Project.reihenfolge)).scalar()
    project = models.Project(**payload.model_dump(), reihenfolge=(max_reihenfolge or 0) + 1)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_detail(db, project)


@router.put("/reorder", status_code=204)
def reorder_projects(payload: schemas.ProjectReorder, db: Session = Depends(get_db)):
    """Setzt die Sortierposition der Portfolio-Kacheln anhand der übergebenen Reihenfolge der IDs.

    Muss vor der Route /{project_id} stehen, da beide Pfade denselben Segmentaufbau haben und
    Starlette sonst "reorder" als project_id-Pfadparameter fehlinterpretieren würde.
    """
    for index, project_id in enumerate(payload.project_ids):
        db.query(models.Project).filter(models.Project.id == project_id).update({"reihenfolge": index})
    db.commit()


@router.get("/{project_id}", response_model=schemas.ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    return _project_detail(db, project)


@router.put("/{project_id}", response_model=schemas.ProjectDetail)
def update_project(project_id: int, payload: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)
    changes = payload.model_dump(exclude_unset=True)
    kommentar_id = changes.pop("kommentar_id", None)
    batch_id = changes.pop("batch_id", None)
    for field, value in changes.items():
        alt = getattr(project, field)
        if alt != value:
            _log_change(
                db,
                project_id=project_id,
                subproject_id=None,
                bereich="stammdaten",
                monat=None,
                feld=field,
                alt=str(alt) if alt is not None else None,
                neu=str(value) if value is not None else None,
                kommentar_id=kommentar_id,
                batch_id=batch_id,
            )
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return _project_detail(db, project)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)

    # Beim Löschen den Jira-Katalog-Eintrag zurücksetzen, sonst zeigt die Jira-Projektliste das
    # Projekt fälschlich weiter als "wird geplant"/aktiv an, obwohl das Kapa-Projekt weg ist.
    if project.jira_project_key:
        catalog_entry = db.get(models.JiraProjectCatalog, project.jira_project_key)
        if catalog_entry is not None:
            catalog_entry.relevant = False

    # Kommentare/Entscheidungen/Risiken/Meetingprotokolle können eigene Tag-/Dokument-
    # Verknüpfungen haben (siehe entity_links.py) - deren TagLink/DocumentLink-Zeilen zuerst
    # entfernen, sonst blieben Waisen-Zeilen zurück (die verlinkten Document-Zeilen selbst
    # werden unten separat behandelt, nicht hier - zentrale Ablage, siehe CONCEPT.md 6a).
    comment_ids = [c[0] for c in db.query(models.Comment.id).filter(models.Comment.project_id == project_id).all()]
    decision_ids = [d[0] for d in db.query(models.Decision.id).filter(models.Decision.project_id == project_id).all()]
    risk_ids = [r[0] for r in db.query(models.Risk.id).filter(models.Risk.project_id == project_id).all()]
    meeting_ids = [
        m[0] for m in db.query(models.MeetingMinutes.id).filter(models.MeetingMinutes.project_id == project_id).all()
    ]
    for entity_type, ids in (
        ("comment", comment_ids),
        ("decision", decision_ids),
        ("risk", risk_ids),
        ("meeting_minutes", meeting_ids),
    ):
        if not ids:
            continue
        db.query(models.TagLink).filter(
            models.TagLink.entity_type == entity_type, models.TagLink.entity_id.in_(ids)
        ).delete(synchronize_session=False)
        db.query(models.DocumentLink).filter(
            models.DocumentLink.entity_type == entity_type, models.DocumentLink.entity_id.in_(ids)
        ).delete(synchronize_session=False)

    # GapSnapshot, PlanHistory, Comment, Decision, Risk, MeetingMinutes haben eine FK auf
    # project_id, aber keine Cascade-Relationship am Project-Modell (siehe models.py).
    db.query(models.GapSnapshot).filter(models.GapSnapshot.project_id == project_id).delete()
    db.query(models.PlanHistory).filter(models.PlanHistory.project_id == project_id).delete()
    db.query(models.Comment).filter(models.Comment.project_id == project_id).delete()
    db.query(models.Decision).filter(models.Decision.project_id == project_id).delete()
    db.query(models.Risk).filter(models.Risk.project_id == project_id).delete()
    db.query(models.MeetingMinutes).filter(models.MeetingMinutes.project_id == project_id).delete()

    # Dokumente: Datei + Document-Zeile + eigene TagLink-Zeilen (als "document" getaggt) +
    # DocumentLink-Zeilen, bei denen dieses Dokument die verlinkte Datei ist.
    documents = db.query(models.Document).filter(models.Document.project_id == project_id).all()
    document_ids = [d.id for d in documents]
    if document_ids:
        db.query(models.TagLink).filter(
            models.TagLink.entity_type == "document", models.TagLink.entity_id.in_(document_ids)
        ).delete(synchronize_session=False)
        db.query(models.DocumentLink).filter(models.DocumentLink.document_id.in_(document_ids)).delete(
            synchronize_session=False
        )
    for document in documents:
        documents_storage.delete_file(document.speicherpfad)
    db.query(models.Document).filter(models.Document.project_id == project_id).delete()

    db.delete(project)
    db.commit()


@router.put("/{project_id}/phasen", response_model=schemas.ProjectDetail)
def set_project_phasen(project_id: int, payload: schemas.PhasenUpdate, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)

    invalid = [c for c in payload.codes if c not in PHASE_CODES]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Ungültige Phasencodes: {invalid}")

    bisherige_codes = {
        gp.phase_code
        for gp in db.query(models.ProjectGanttPhase).filter(
            models.ProjectGanttPhase.project_id == project_id,
            models.ProjectGanttPhase.monat == payload.monat,
        )
    }
    neue_codes = set(dict.fromkeys(payload.codes))
    for code in neue_codes - bisherige_codes:
        _log_change(
            db,
            project_id=project_id,
            subproject_id=None,
            bereich="phase",
            monat=payload.monat,
            feld=code,
            alt="inaktiv",
            neu="aktiv",
            kommentar_id=payload.kommentar_id,
            batch_id=payload.batch_id,
        )
    for code in bisherige_codes - neue_codes:
        _log_change(
            db,
            project_id=project_id,
            subproject_id=None,
            bereich="phase",
            monat=payload.monat,
            feld=code,
            alt="aktiv",
            neu="inaktiv",
            kommentar_id=payload.kommentar_id,
            batch_id=payload.batch_id,
        )

    db.query(models.ProjectGanttPhase).filter(
        models.ProjectGanttPhase.project_id == project_id,
        models.ProjectGanttPhase.monat == payload.monat,
    ).delete()
    for code in neue_codes:  # dedupe, siehe oben
        db.add(models.ProjectGanttPhase(project_id=project_id, monat=payload.monat, phase_code=code))
    db.commit()
    db.refresh(project)
    return _project_detail(db, project)


@router.put("/{project_id}/fte", response_model=schemas.ProjectDetail)
def set_project_fte(project_id: int, payload: schemas.FteUpdate, db: Session = Depends(get_db)):
    project = _get_project_or_404(db, project_id)

    entry = (
        db.query(models.ProjectFtePlan)
        .filter(models.ProjectFtePlan.project_id == project_id, models.ProjectFtePlan.monat == payload.monat)
        .first()
    )
    alter_wert = entry.wert_soll if entry is not None else None
    _log_change(
        db,
        project_id=project_id,
        subproject_id=None,
        bereich="fte",
        monat=payload.monat,
        feld="fte_soll",
        alt=str(alter_wert) if alter_wert is not None else None,
        neu=str(payload.wert_soll),
        kommentar_id=payload.kommentar_id,
        batch_id=payload.batch_id,
    )
    if entry is None:
        entry = models.ProjectFtePlan(project_id=project_id, monat=payload.monat, wert_soll=payload.wert_soll)
        db.add(entry)
    else:
        entry.wert_soll = payload.wert_soll
    db.commit()
    db.refresh(project)
    return _project_detail(db, project)


@router.get("/subprojects/all", response_model=list[schemas.SubprojectListItem])
def list_all_subprojects(db: Session = Depends(get_db)):
    """Flache Liste aller Teilprojekte (für die Zuordnung MA <-> Teilprojekt, siehe /team)."""
    rows = (
        db.query(models.Subproject)
        .join(models.Project)
        .order_by(models.Project.name, models.Subproject.reihenfolge)
        .all()
    )
    return [
        schemas.SubprojectListItem(
            id=sp.id, name=sp.name, project_id=sp.project_id, project_name=sp.project.name
        )
        for sp in rows
    ]


@router.post("/{project_id}/subprojects", response_model=schemas.SubprojectDetail, status_code=201)
def create_subproject(project_id: int, payload: schemas.SubprojectCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    sp = models.Subproject(project_id=project_id, **payload.model_dump())
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return _subproject_detail(sp)


@router.put("/subprojects/{subproject_id}", response_model=schemas.SubprojectDetail)
def update_subproject(subproject_id: int, payload: schemas.SubprojectUpdate, db: Session = Depends(get_db)):
    sp = _get_subproject_or_404(db, subproject_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sp, field, value)
    db.commit()
    db.refresh(sp)
    return _subproject_detail(sp)


@router.delete("/subprojects/{subproject_id}", status_code=204)
def delete_subproject(subproject_id: int, db: Session = Depends(get_db)):
    sp = _get_subproject_or_404(db, subproject_id)

    # PlanHistory/Comment haben keine Cascade-Relationship am Subproject-Modell - sonst
    # blieben Waisen-Zeilen in der DB zurück (analog zu delete_project). Comments können
    # eigene Tag-/DocumentLink-Zeilen haben (siehe entity_links.py) - vor dem Löschen der
    # Comment-Zeilen selbst entfernen, die verlinkten Document-Zeilen bleiben bestehen.
    comment_ids = [
        c[0] for c in db.query(models.Comment.id).filter(models.Comment.subproject_id == subproject_id).all()
    ]
    if comment_ids:
        db.query(models.TagLink).filter(
            models.TagLink.entity_type == "comment", models.TagLink.entity_id.in_(comment_ids)
        ).delete(synchronize_session=False)
        db.query(models.DocumentLink).filter(
            models.DocumentLink.entity_type == "comment", models.DocumentLink.entity_id.in_(comment_ids)
        ).delete(synchronize_session=False)
    db.query(models.PlanHistory).filter(models.PlanHistory.subproject_id == subproject_id).delete()
    db.query(models.Comment).filter(models.Comment.subproject_id == subproject_id).delete()

    db.delete(sp)
    db.commit()


@router.put("/subprojects/{subproject_id}/phasen", response_model=schemas.SubprojectDetail)
def set_phasen(subproject_id: int, payload: schemas.PhasenUpdate, db: Session = Depends(get_db)):
    sp = _get_subproject_or_404(db, subproject_id)

    invalid = [c for c in payload.codes if c not in PHASE_CODES]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Ungültige Phasencodes: {invalid}")

    bisherige_codes = {
        gp.phase_code
        for gp in db.query(models.GanttPhase).filter(
            models.GanttPhase.subproject_id == subproject_id,
            models.GanttPhase.monat == payload.monat,
        )
    }
    neue_codes = set(dict.fromkeys(payload.codes))
    for code in neue_codes - bisherige_codes:
        _log_change(
            db,
            project_id=sp.project_id,
            subproject_id=subproject_id,
            bereich="phase",
            monat=payload.monat,
            feld=code,
            alt="inaktiv",
            neu="aktiv",
            kommentar_id=payload.kommentar_id,
            batch_id=payload.batch_id,
        )
    for code in bisherige_codes - neue_codes:
        _log_change(
            db,
            project_id=sp.project_id,
            subproject_id=subproject_id,
            bereich="phase",
            monat=payload.monat,
            feld=code,
            alt="aktiv",
            neu="inaktiv",
            kommentar_id=payload.kommentar_id,
            batch_id=payload.batch_id,
        )

    db.query(models.GanttPhase).filter(
        models.GanttPhase.subproject_id == subproject_id,
        models.GanttPhase.monat == payload.monat,
    ).delete()
    for code in neue_codes:  # dedupe, siehe oben
        db.add(models.GanttPhase(subproject_id=subproject_id, monat=payload.monat, phase_code=code))
    db.commit()
    db.refresh(sp)
    return _subproject_detail(sp)


@router.put("/subprojects/{subproject_id}/fte", response_model=schemas.SubprojectDetail)
def set_fte(subproject_id: int, payload: schemas.FteUpdate, db: Session = Depends(get_db)):
    sp = _get_subproject_or_404(db, subproject_id)

    entry = (
        db.query(models.FtePlan)
        .filter(models.FtePlan.subproject_id == subproject_id, models.FtePlan.monat == payload.monat)
        .first()
    )
    alter_wert = entry.wert_soll if entry is not None else None
    _log_change(
        db,
        project_id=sp.project_id,
        subproject_id=subproject_id,
        bereich="fte",
        monat=payload.monat,
        feld="fte_soll",
        alt=str(alter_wert) if alter_wert is not None else None,
        neu=str(payload.wert_soll),
        kommentar_id=payload.kommentar_id,
        batch_id=payload.batch_id,
    )
    if entry is None:
        entry = models.FtePlan(subproject_id=subproject_id, monat=payload.monat, wert_soll=payload.wert_soll)
        db.add(entry)
    else:
        entry.wert_soll = payload.wert_soll
    db.commit()
    db.refresh(sp)
    return _subproject_detail(sp)


# ---------------------------------------------------------------------------
# Kommentare & Änderungshistorie (Speichern-Button/Entwurfsmodus)
# ---------------------------------------------------------------------------


def _comment_out(db: Session, comment: models.Comment) -> schemas.CommentOut:
    return schemas.CommentOut(
        id=comment.id,
        project_id=comment.project_id,
        subproject_id=comment.subproject_id,
        monat=comment.monat,
        phase_code=comment.phase_code,
        text=comment.text,
        erstellt_am=comment.erstellt_am,
        tags=entity_links.tags_for(db, "comment", comment.id),
        documents=entity_links.documents_for(db, "comment", comment.id),
    )


@router.post("/{project_id}/comments", response_model=schemas.CommentOut, status_code=201)
def create_comment(project_id: int, payload: schemas.CommentCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    if payload.subproject_id is not None:
        _get_subproject_or_404(db, payload.subproject_id)
    comment = models.Comment(
        project_id=project_id,
        subproject_id=payload.subproject_id,
        monat=payload.monat,
        phase_code=payload.phase_code,
        text=payload.text,
        erstellt_am=datetime.now(timezone.utc).isoformat(),
    )
    db.add(comment)
    db.flush()
    if payload.tags:
        entity_links.sync_tags(db, "comment", comment.id, payload.tags)
    db.commit()
    db.refresh(comment)
    return _comment_out(db, comment)


@router.get("/{project_id}/comments", response_model=list[schemas.CommentOut])
def list_comments(project_id: int, db: Session = Depends(get_db)):
    """Alle Kommentare zum Projekt inkl. seiner Teilprojekte - das Frontend filtert nach
    subproject_id/monat/phase_code, um jeden Kommentar an der richtigen Stelle anzuzeigen."""
    _get_project_or_404(db, project_id)
    comments = (
        db.query(models.Comment)
        .filter(models.Comment.project_id == project_id)
        .order_by(models.Comment.erstellt_am.desc())
        .all()
    )
    return [_comment_out(db, c) for c in comments]


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = _get_comment_or_404(db, comment_id)

    # PlanHistory verweist optional auf einen Kommentar als Begründung - beim Löschen nur die
    # Verknüpfung entfernen, die Historie selbst bleibt erhalten (kein Cascade-Delete).
    db.query(models.PlanHistory).filter(models.PlanHistory.kommentar_id == comment_id).update(
        {"kommentar_id": None}
    )
    # Tags/Anhänge der Notiz entfernen - die verlinkten Document-Zeilen bleiben in der
    # zentralen Ablage bestehen (siehe CONCEPT.md Abschnitt 6a).
    entity_links.delete_links_for_entity(db, "comment", comment_id)
    db.delete(comment)
    db.commit()


def _history_out(db: Session, entry: models.PlanHistory) -> schemas.PlanHistoryOut:
    kommentar = db.get(models.Comment, entry.kommentar_id) if entry.kommentar_id is not None else None
    return schemas.PlanHistoryOut(
        id=entry.id,
        subproject_id=entry.subproject_id,
        bereich=entry.bereich,
        monat=entry.monat,
        feld=entry.feld,
        alter_wert=entry.alter_wert,
        neuer_wert=entry.neuer_wert,
        geaendert_am=entry.geaendert_am,
        batch_id=entry.batch_id,
        kommentar=_comment_out(db, kommentar) if kommentar is not None else None,
    )


@router.get("/{project_id}/history", response_model=list[schemas.PlanHistoryOut])
def get_project_history(project_id: int, db: Session = Depends(get_db)):
    """Änderungshistorie auf Projekt-Ebene (subproject_id IS NULL) - Teilprojekte haben eine
    eigene, getrennte Historie über GET /projects/subprojects/{subproject_id}/history."""
    _get_project_or_404(db, project_id)
    entries = (
        db.query(models.PlanHistory)
        .filter(models.PlanHistory.project_id == project_id, models.PlanHistory.subproject_id.is_(None))
        .order_by(models.PlanHistory.geaendert_am.desc())
        .all()
    )
    return [_history_out(db, e) for e in entries]


@router.get("/subprojects/{subproject_id}/history", response_model=list[schemas.PlanHistoryOut])
def get_subproject_history(subproject_id: int, db: Session = Depends(get_db)):
    _get_subproject_or_404(db, subproject_id)
    entries = (
        db.query(models.PlanHistory)
        .filter(models.PlanHistory.subproject_id == subproject_id)
        .order_by(models.PlanHistory.geaendert_am.desc())
        .all()
    )
    return [_history_out(db, e) for e in entries]
