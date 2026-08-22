"""Entscheidungen/Risiken/Meetingprotokolle/Blocker (Kommunikation-Tab, siehe CONCEPT.md
Abschnitt 6a/12) sowie der projektweite Activity Feed (Phase 16). GET /tags lebt in
routers/documents.py, da es eng an entity_links.py gekoppelt ist, das auch die
Dokument-Verknüpfungen verwaltet."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import entity_links, models, schemas
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["communication"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decision_out(db: Session, d: models.Decision) -> schemas.DecisionOut:
    return schemas.DecisionOut(
        id=d.id,
        project_id=d.project_id,
        titel=d.titel,
        beschreibung=d.beschreibung,
        begruendung=d.begruendung,
        status=d.status,
        entschieden_von_person_id=d.entschieden_von_person_id,
        entschieden_am=d.entschieden_am,
        erstellt_am=d.erstellt_am,
        plan_phase_id=d.plan_phase_id,
        tags=entity_links.tags_for(db, "decision", d.id),
        documents=entity_links.documents_for(db, "decision", d.id),
    )


def _risk_out(db: Session, r: models.Risk) -> schemas.RiskOut:
    return schemas.RiskOut(
        id=r.id,
        project_id=r.project_id,
        titel=r.titel,
        beschreibung=r.beschreibung,
        wahrscheinlichkeit=r.wahrscheinlichkeit,
        auswirkung=r.auswirkung,
        status=r.status,
        owner_person_id=r.owner_person_id,
        faellig_am=r.faellig_am,
        erstellt_am=r.erstellt_am,
        aktualisiert_am=r.aktualisiert_am,
        tags=entity_links.tags_for(db, "risk", r.id),
        documents=entity_links.documents_for(db, "risk", r.id),
    )


def _validate_person_id(db: Session, person_id: int | None, field: str) -> None:
    if person_id is not None and db.get(models.Person, person_id) is None:
        raise HTTPException(status_code=404, detail=f"Person ({field}) nicht gefunden")


def _meeting_out(db: Session, m: models.MeetingMinutes) -> schemas.MeetingMinutesOut:
    return schemas.MeetingMinutesOut(
        id=m.id,
        project_id=m.project_id,
        titel=m.titel,
        datum=m.datum,
        teilnehmer=m.teilnehmer,
        text=m.text,
        erstellt_am=m.erstellt_am,
        tags=entity_links.tags_for(db, "meeting_minutes", m.id),
        documents=entity_links.documents_for(db, "meeting_minutes", m.id),
    )


def _task_out(db: Session, t: models.Task) -> schemas.TaskOut:
    return schemas.TaskOut(
        id=t.id,
        project_id=t.project_id,
        titel=t.titel,
        beschreibung=t.beschreibung,
        status=t.status,
        zustaendig_person_id=t.zustaendig_person_id,
        faellig_am=t.faellig_am,
        erstellt_am=t.erstellt_am,
        aktualisiert_am=t.aktualisiert_am,
        plan_phase_id=t.plan_phase_id,
        tags=entity_links.tags_for(db, "task", t.id),
        documents=entity_links.documents_for(db, "task", t.id),
    )


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


def _get_decision_or_404(db: Session, decision_id: int) -> models.Decision:
    d = db.get(models.Decision, decision_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Entscheidung nicht gefunden")
    return d


def _get_risk_or_404(db: Session, risk_id: int) -> models.Risk:
    r = db.get(models.Risk, risk_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Risiko nicht gefunden")
    return r


def _get_meeting_or_404(db: Session, meeting_id: int) -> models.MeetingMinutes:
    m = db.get(models.MeetingMinutes, meeting_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Meetingprotokoll nicht gefunden")
    return m


def _get_task_or_404(db: Session, task_id: int) -> models.Task:
    t = db.get(models.Task, task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden")
    return t


def _blocker_out(db: Session, b: models.Blocker) -> schemas.BlockerOut:
    return schemas.BlockerOut(
        id=b.id,
        project_id=b.project_id,
        title=b.title,
        description=b.description,
        status=b.status,
        severity=b.severity,
        active_since=b.active_since,
        caused_by_party=b.caused_by_party,
        waiting_for_party=b.waiting_for_party,
        owner_person_id=b.owner_person_id,
        owner_team_id=b.owner_team_id,
        next_action=b.next_action,
        impact=b.impact,
        erstellt_am=b.erstellt_am,
        aktualisiert_am=b.aktualisiert_am,
        plan_phase_id=b.plan_phase_id,
        tags=entity_links.tags_for(db, "blocker", b.id),
        documents=entity_links.documents_for(db, "blocker", b.id),
    )


def _get_blocker_or_404(db: Session, blocker_id: int) -> models.Blocker:
    b = db.get(models.Blocker, blocker_id)
    if b is None:
        raise HTTPException(status_code=404, detail="Blocker nicht gefunden")
    return b


# ---------------------------------------------------------------------------
# Entscheidungen
# ---------------------------------------------------------------------------


@router.get("/{project_id}/decisions", response_model=list[schemas.DecisionOut])
def list_decisions(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.Decision)
        .filter(models.Decision.project_id == project_id)
        .order_by(models.Decision.erstellt_am.desc())
        .all()
    )
    return [_decision_out(db, d) for d in rows]


@router.post("/{project_id}/decisions", response_model=schemas.DecisionOut, status_code=201)
def create_decision(project_id: int, payload: schemas.DecisionCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    _validate_person_id(db, payload.entschieden_von_person_id, "entschieden_von_person_id")
    decision = models.Decision(
        project_id=project_id,
        plan_phase_id=payload.plan_phase_id,
        titel=payload.titel,
        beschreibung=payload.beschreibung,
        begruendung=payload.begruendung,
        status=payload.status,
        entschieden_von_person_id=payload.entschieden_von_person_id,
        entschieden_am=payload.entschieden_am,
        erstellt_am=_now(),
    )
    db.add(decision)
    db.flush()
    if payload.tags:
        entity_links.sync_tags(db, "decision", decision.id, payload.tags)
    db.commit()
    db.refresh(decision)
    return _decision_out(db, decision)


@router.put("/decisions/{decision_id}", response_model=schemas.DecisionOut)
def update_decision(decision_id: int, payload: schemas.DecisionUpdate, db: Session = Depends(get_db)):
    decision = _get_decision_or_404(db, decision_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"tags"})
    if "entschieden_von_person_id" in changes:
        _validate_person_id(db, changes["entschieden_von_person_id"], "entschieden_von_person_id")
    for field, value in changes.items():
        setattr(decision, field, value)
    if payload.tags is not None:
        entity_links.sync_tags(db, "decision", decision.id, payload.tags)
    db.commit()
    db.refresh(decision)
    return _decision_out(db, decision)


@router.delete("/decisions/{decision_id}", status_code=204)
def delete_decision(decision_id: int, db: Session = Depends(get_db)):
    decision = _get_decision_or_404(db, decision_id)
    entity_links.delete_links_for_entity(db, "decision", decision_id)
    entity_links.delete_relations_for_entity(db, "decision", decision_id)
    db.delete(decision)
    db.commit()


# ---------------------------------------------------------------------------
# Risiken
# ---------------------------------------------------------------------------


@router.get("/{project_id}/risks", response_model=list[schemas.RiskOut])
def list_risks(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.Risk)
        .filter(models.Risk.project_id == project_id)
        .order_by(models.Risk.erstellt_am.desc())
        .all()
    )
    return [_risk_out(db, r) for r in rows]


@router.post("/{project_id}/risks", response_model=schemas.RiskOut, status_code=201)
def create_risk(project_id: int, payload: schemas.RiskCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    _validate_person_id(db, payload.owner_person_id, "owner_person_id")
    now = _now()
    risk = models.Risk(
        project_id=project_id,
        titel=payload.titel,
        beschreibung=payload.beschreibung,
        wahrscheinlichkeit=payload.wahrscheinlichkeit,
        auswirkung=payload.auswirkung,
        status=payload.status,
        owner_person_id=payload.owner_person_id,
        faellig_am=payload.faellig_am,
        erstellt_am=now,
        aktualisiert_am=now,
    )
    db.add(risk)
    db.flush()
    if payload.tags:
        entity_links.sync_tags(db, "risk", risk.id, payload.tags)
    db.commit()
    db.refresh(risk)
    return _risk_out(db, risk)


@router.put("/risks/{risk_id}", response_model=schemas.RiskOut)
def update_risk(risk_id: int, payload: schemas.RiskUpdate, db: Session = Depends(get_db)):
    risk = _get_risk_or_404(db, risk_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"tags"})
    if "owner_person_id" in changes:
        _validate_person_id(db, changes["owner_person_id"], "owner_person_id")
    if changes:
        for field, value in changes.items():
            setattr(risk, field, value)
        risk.aktualisiert_am = _now()
    if payload.tags is not None:
        entity_links.sync_tags(db, "risk", risk.id, payload.tags)
    db.commit()
    db.refresh(risk)
    return _risk_out(db, risk)


@router.delete("/risks/{risk_id}", status_code=204)
def delete_risk(risk_id: int, db: Session = Depends(get_db)):
    risk = _get_risk_or_404(db, risk_id)
    entity_links.delete_links_for_entity(db, "risk", risk_id)
    entity_links.delete_relations_for_entity(db, "risk", risk_id)
    db.delete(risk)
    db.commit()


# ---------------------------------------------------------------------------
# Meetingprotokolle
# ---------------------------------------------------------------------------


@router.get("/{project_id}/meeting-minutes", response_model=list[schemas.MeetingMinutesOut])
def list_meeting_minutes(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.MeetingMinutes)
        .filter(models.MeetingMinutes.project_id == project_id)
        .order_by(models.MeetingMinutes.datum.desc())
        .all()
    )
    return [_meeting_out(db, m) for m in rows]


@router.post("/{project_id}/meeting-minutes", response_model=schemas.MeetingMinutesOut, status_code=201)
def create_meeting_minutes(project_id: int, payload: schemas.MeetingMinutesCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    meeting = models.MeetingMinutes(
        project_id=project_id,
        titel=payload.titel,
        datum=payload.datum,
        teilnehmer=payload.teilnehmer,
        text=payload.text,
        erstellt_am=_now(),
    )
    db.add(meeting)
    db.flush()
    if payload.tags:
        entity_links.sync_tags(db, "meeting_minutes", meeting.id, payload.tags)
    db.commit()
    db.refresh(meeting)
    return _meeting_out(db, meeting)


@router.put("/meeting-minutes/{meeting_id}", response_model=schemas.MeetingMinutesOut)
def update_meeting_minutes(meeting_id: int, payload: schemas.MeetingMinutesUpdate, db: Session = Depends(get_db)):
    meeting = _get_meeting_or_404(db, meeting_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"tags"})
    for field, value in changes.items():
        setattr(meeting, field, value)
    if payload.tags is not None:
        entity_links.sync_tags(db, "meeting_minutes", meeting.id, payload.tags)
    db.commit()
    db.refresh(meeting)
    return _meeting_out(db, meeting)


@router.delete("/meeting-minutes/{meeting_id}", status_code=204)
def delete_meeting_minutes(meeting_id: int, db: Session = Depends(get_db)):
    meeting = _get_meeting_or_404(db, meeting_id)
    entity_links.delete_links_for_entity(db, "meeting_minutes", meeting_id)
    entity_links.delete_relations_for_entity(db, "meeting_minutes", meeting_id)
    db.delete(meeting)
    db.commit()


# ---------------------------------------------------------------------------
# Aufgaben
# ---------------------------------------------------------------------------


@router.get("/{project_id}/tasks", response_model=list[schemas.TaskOut])
def list_tasks(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.Task)
        .filter(models.Task.project_id == project_id)
        .order_by(models.Task.erstellt_am.desc())
        .all()
    )
    return [_task_out(db, t) for t in rows]


@router.post("/{project_id}/tasks", response_model=schemas.TaskOut, status_code=201)
def create_task(project_id: int, payload: schemas.TaskCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    _validate_person_id(db, payload.zustaendig_person_id, "zustaendig_person_id")
    now = _now()
    task = models.Task(
        project_id=project_id,
        plan_phase_id=payload.plan_phase_id,
        titel=payload.titel,
        beschreibung=payload.beschreibung,
        status=payload.status,
        zustaendig_person_id=payload.zustaendig_person_id,
        faellig_am=payload.faellig_am,
        erstellt_am=now,
        aktualisiert_am=now,
    )
    db.add(task)
    db.flush()
    if payload.tags:
        entity_links.sync_tags(db, "task", task.id, payload.tags)
    db.commit()
    db.refresh(task)
    return _task_out(db, task)


@router.put("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, payload: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, task_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"tags"})
    if "zustaendig_person_id" in changes:
        _validate_person_id(db, changes["zustaendig_person_id"], "zustaendig_person_id")
    if changes:
        for field, value in changes.items():
            setattr(task, field, value)
        task.aktualisiert_am = _now()
    if payload.tags is not None:
        entity_links.sync_tags(db, "task", task.id, payload.tags)
    db.commit()
    db.refresh(task)
    return _task_out(db, task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = _get_task_or_404(db, task_id)
    entity_links.delete_links_for_entity(db, "task", task_id)
    entity_links.delete_relations_for_entity(db, "task", task_id)
    db.delete(task)
    db.commit()


# ---------------------------------------------------------------------------
# Blocker (Phase 16, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 37/38)
# ---------------------------------------------------------------------------


@router.get("/{project_id}/blockers", response_model=list[schemas.BlockerOut])
def list_blockers(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.Blocker)
        .filter(models.Blocker.project_id == project_id)
        .order_by(models.Blocker.erstellt_am.desc())
        .all()
    )
    return [_blocker_out(db, b) for b in rows]


@router.post("/{project_id}/blockers", response_model=schemas.BlockerOut, status_code=201)
def create_blocker(project_id: int, payload: schemas.BlockerCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    if payload.owner_person_id is not None and db.get(models.Person, payload.owner_person_id) is None:
        raise HTTPException(status_code=404, detail="Person (owner_person_id) nicht gefunden")
    if payload.owner_team_id is not None and db.get(models.Team, payload.owner_team_id) is None:
        raise HTTPException(status_code=404, detail="Team (owner_team_id) nicht gefunden")
    now = _now()
    blocker = models.Blocker(
        project_id=project_id,
        plan_phase_id=payload.plan_phase_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        severity=payload.severity,
        active_since=payload.active_since,
        caused_by_party=payload.caused_by_party,
        waiting_for_party=payload.waiting_for_party,
        owner_person_id=payload.owner_person_id,
        owner_team_id=payload.owner_team_id,
        next_action=payload.next_action,
        impact=payload.impact,
        erstellt_am=now,
        aktualisiert_am=now,
    )
    db.add(blocker)
    db.flush()
    if payload.tags:
        entity_links.sync_tags(db, "blocker", blocker.id, payload.tags)
    db.commit()
    db.refresh(blocker)
    return _blocker_out(db, blocker)


@router.put("/blockers/{blocker_id}", response_model=schemas.BlockerOut)
def update_blocker(blocker_id: int, payload: schemas.BlockerUpdate, db: Session = Depends(get_db)):
    blocker = _get_blocker_or_404(db, blocker_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"tags"})
    if "owner_person_id" in changes and changes["owner_person_id"] is not None:
        if db.get(models.Person, changes["owner_person_id"]) is None:
            raise HTTPException(status_code=404, detail="Person (owner_person_id) nicht gefunden")
    if "owner_team_id" in changes and changes["owner_team_id"] is not None:
        if db.get(models.Team, changes["owner_team_id"]) is None:
            raise HTTPException(status_code=404, detail="Team (owner_team_id) nicht gefunden")
    if changes:
        for field, value in changes.items():
            setattr(blocker, field, value)
        blocker.aktualisiert_am = _now()
    if payload.tags is not None:
        entity_links.sync_tags(db, "blocker", blocker.id, payload.tags)
    db.commit()
    db.refresh(blocker)
    return _blocker_out(db, blocker)


@router.delete("/blockers/{blocker_id}", status_code=204)
def delete_blocker(blocker_id: int, db: Session = Depends(get_db)):
    blocker = _get_blocker_or_404(db, blocker_id)
    entity_links.delete_links_for_entity(db, "blocker", blocker_id)
    entity_links.delete_relations_for_entity(db, "blocker", blocker_id)
    db.delete(blocker)
    db.commit()


# ---------------------------------------------------------------------------
# Activity Feed (Phase 16, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 32) - reine
# chronologische Aggregation, keine neue Tabelle. Nutzt dieselbe Zeitstempel-Registry wie
# die Tag-Dossiers aus Phase 24 (entity_links.ACTIVITY_ENTITY_TYPES/timestamp_for) - "document"
# fehlt bewusst (Dateien sind keine Aktivität).
# ---------------------------------------------------------------------------


@router.get("/{project_id}/activity", response_model=list[schemas.ActivityItemOut])
def get_project_activity(project_id: int, limit: int = 50, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    items: list[schemas.ActivityItemOut] = []
    for entity_type in entity_links.ACTIVITY_ENTITY_TYPES:
        for summary in entity_links.list_entity_summaries(db, entity_type, project_id):
            timestamp = entity_links.timestamp_for(db, entity_type, summary["entity_id"])
            if timestamp is None:
                continue
            items.append(
                schemas.ActivityItemOut(
                    entity_type=entity_type,
                    entity_id=summary["entity_id"],
                    label=summary["label"],
                    timestamp=timestamp,
                    tags=summary["tags"],
                )
            )
    items.sort(key=lambda item: item.timestamp, reverse=True)
    return items[:limit]


@router.get("/plan-phases/{plan_phase_id}/activity", response_model=list[schemas.ActivityItemOut])
def get_plan_phase_activity(plan_phase_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Phasenbezogener Activity Feed - wie get_project_activity, aber eingeschränkt auf
    Entitäten mit plan_phase_id == plan_phase_id. milestone hat seit P18/B-7 ebenfalls eine
    plan_phase_id-Spalte und wird hier daher korrekt mitgeliefert. Entitätstypen ohne
    plan_phase_id-Spalte (plan_phase/risk/meeting_minutes/baseline_snapshot - Planstände sind
    projektweit, nicht phasenscoped, siehe P19.6) liefern hier nichts (siehe
    list_entity_summaries)."""
    plan_phase = db.get(models.PlanPhase, plan_phase_id)
    if plan_phase is None:
        raise HTTPException(status_code=404, detail="Planphase nicht gefunden")
    items: list[schemas.ActivityItemOut] = []
    for entity_type in entity_links.ACTIVITY_ENTITY_TYPES:
        for summary in entity_links.list_entity_summaries(db, entity_type, plan_phase_id=plan_phase_id):
            timestamp = entity_links.timestamp_for(db, entity_type, summary["entity_id"])
            if timestamp is None:
                continue
            items.append(
                schemas.ActivityItemOut(
                    entity_type=entity_type,
                    entity_id=summary["entity_id"],
                    label=summary["label"],
                    timestamp=timestamp,
                    tags=summary["tags"],
                )
            )
    items.sort(key=lambda item: item.timestamp, reverse=True)
    return items[:limit]
