"""PlanPhase & Milestone (Project Planning Core, Phase 17, siehe CONCEPT.md Abschnitt 12 /
Master-MD Abschnitt 8/9/10). Seit dem Legacy Cutover (Phase 26.9) die alleinige
Planungswahrheit - das ehemals parallele Gantt-Grid (GanttPhase/ProjectGanttPhase) ist
entfallen. Folgt demselben CRUD-Muster wie routers/communication.py."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import (
    capacity_calc,
    entity_links,
    history,
    models,
    phase_metrics_calc,
    planning_calc,
    schemas,
    worklog_actuals,
)
from ..database import get_db

router = APIRouter(prefix="/projects", tags=["planning"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_project_or_404(db: Session, project_id: int) -> models.Project:
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project


def _check_subproject(db: Session, project_id: int, subproject_id: int | None) -> None:
    if subproject_id is None:
        return
    sp = db.get(models.Subproject, subproject_id)
    if sp is None:
        raise HTTPException(status_code=404, detail="Teilprojekt nicht gefunden")
    if sp.project_id != project_id:
        raise HTTPException(status_code=422, detail="subproject_id muss zum selben Projekt gehören")


def _check_milestone_plan_phase(db: Session, project_id: int, plan_phase_id: int | None) -> None:
    """P18/B-7 (CONCEPT.md Abschnitt 6b.8): ein Milestone kann sowohl auf eine Leaf- als auch
    auf eine Parent-Phase zeigen (im Unterschied zur Kapazitätsplanung, die Leaf-only ist) -
    hier genügt Existenz + Projekt-Grenze, keine Hierarchie-Validierung nötig."""
    if plan_phase_id is None:
        return
    plan_phase = db.get(models.PlanPhase, plan_phase_id)
    if plan_phase is None:
        raise HTTPException(status_code=404, detail="Planphase nicht gefunden")
    if plan_phase.project_id != project_id:
        raise HTTPException(status_code=422, detail="plan_phase_id muss zum selben Projekt gehören")


def _check_owner(db: Session, owner_person_id: int | None, owner_team_id: int | None) -> None:
    if owner_person_id is not None and db.get(models.Person, owner_person_id) is None:
        raise HTTPException(status_code=404, detail="Person (owner_person_id) nicht gefunden")
    if owner_team_id is not None and db.get(models.Team, owner_team_id) is None:
        raise HTTPException(status_code=404, detail="Team (owner_team_id) nicht gefunden")


def _check_parent_phase(
    db: Session, project_id: int, plan_phase_id: int | None, parent_phase_id: int | None
) -> None:
    """Validiert parent_phase_id beim Anlegen/Verschieben einer PlanPhase (P18/B-3, BD-10,
    CLOSED): Projekt-Grenze, kein Selbst-Parent, kein Zyklus, maximale Hierarchietiefe 3
    Ebenen. plan_phase_id ist None beim Anlegen (die Phase existiert noch nicht, ein Zyklus
    ist dann unmöglich)."""
    if parent_phase_id is None:
        return
    parent = db.get(models.PlanPhase, parent_phase_id)
    if parent is None:
        raise HTTPException(status_code=404, detail="Übergeordnete Phase nicht gefunden")
    if parent.project_id != project_id:
        raise HTTPException(status_code=422, detail="parent_phase_id muss zum selben Projekt gehören")
    if plan_phase_id is not None:
        if parent_phase_id == plan_phase_id:
            raise HTTPException(
                status_code=422, detail="Eine Phase kann nicht ihre eigene übergeordnete Phase sein"
            )
        descendant_ids = {d.id for d in planning_calc.all_descendants(db, plan_phase_id)}
        if parent_phase_id in descendant_ids:
            raise HTTPException(
                status_code=422,
                detail="Zyklus: die gewählte übergeordnete Phase ist eine Unterphase dieser Phase",
            )
    # Tiefen-Check berücksichtigt bewusst nicht nur die neue Tiefe von plan_phase_id selbst,
    # sondern auch die Höhe ihres eigenen Teilbaums (falls sie bereits Kinder hat, z.B. beim
    # Reparenting einer ganzen Parent-Phase mitsamt Enkeln) - sonst könnten Nachfahren
    # unbemerkt über die maximale Hierarchietiefe hinausrutschen.
    new_own_depth = planning_calc.depth_of(db, parent_phase_id) + 1
    subtree_extra_levels = 0
    if plan_phase_id is not None:
        subtree_extra_levels = planning_calc.subtree_max_depth(db, plan_phase_id) - planning_calc.depth_of(
            db, plan_phase_id
        )
    if new_own_depth + subtree_extra_levels > planning_calc.MAX_HIERARCHY_DEPTH:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Maximale Hierarchietiefe ({planning_calc.MAX_HIERARCHY_DEPTH} Ebenen) erreicht - "
                "diese Phase (bzw. ihre Unterphasen) kann/können hier nicht eingehängt werden"
            ),
        )


def _maybe_historize_parent_fte(db: Session, parent: models.PlanPhase) -> None:
    """P18/B-3 (CONCEPT.md Abschnitt 6b.1a): sobald eine Phase ihr erstes Kind erhält, wird
    ihr plan_fte serverseitig auf NULL gesetzt und der alte Wert in PlanHistory historisiert -
    keine automatische Reaktivierung, falls sie später wieder zum Leaf wird (letztes Kind
    entfernt/reparented: keine Sonderbehandlung, plan_fte bleibt NULL, Korrektur 35.1). Ein
    bereits kinderloser Aufruf mit plan_fte=None ist ein No-Op (idempotent bei weiteren
    Kindern derselben Phase).

    P20.1 (BD-1E CLOSED, siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 15):
    jira_label folgt demselben Lifecycle wie plan_fte - wird hier mit historisiert/zurückgesetzt,
    kein zweiter Code-Pfad an den drei Aufrufstellen (create_plan_phase, update_plan_phase,
    reparent_children)."""
    batch_id = history.new_batch_id()
    if parent.plan_fte is not None:
        history.record_rows(
            db,
            project_id=parent.project_id,
            entity_type="plan_phase",
            action=history.ACTION_UPDATED,
            changes=[("plan_fte", parent.plan_fte, None)],
            entity_id=parent.id,
            entity_label=parent.phase_type,
            plan_phase_id=parent.id,
            batch_id=batch_id,
            bereich="phase_struktur",
        )
        parent.plan_fte = None
    if parent.jira_label is not None:
        history.record_rows(
            db,
            project_id=parent.project_id,
            entity_type="plan_phase",
            action=history.ACTION_UPDATED,
            changes=[("jira_label", parent.jira_label, None)],
            entity_id=parent.id,
            entity_label=parent.phase_type,
            plan_phase_id=parent.id,
            batch_id=batch_id,
            bereich="phase_struktur",
        )
        parent.jira_label = None


def _check_jira_label_conflict(
    db: Session, project_id: int, plan_phase_id: int | None, jira_label: str | None
) -> None:
    """P20.1 (BD-1G CLOSED, siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 11):
    zwei Leaf-Phasen desselben Projekts dürfen nie denselben jira_label-Wert tragen - jedes
    matchende Issue würde sonst laut Resolver (P20.2) strukturell für beide Phasen zutreffen
    und wäre damit immer AMBIGUOUS. Harter Block (409) statt Warnung, da es dafür keinen
    legitimen Anwendungsfall gibt (anders als bei einem Issue mit mehreren unterschiedlichen
    Phase-Labels, das ein gültiger Ambiguous-Grenzfall bleibt). plan_phase_id ist None beim
    Anlegen (die Phase existiert noch nicht, schließt sich also nie selbst aus)."""
    if jira_label is None:
        return
    query = db.query(models.PlanPhase).filter(
        models.PlanPhase.project_id == project_id,
        models.PlanPhase.jira_label == jira_label,
    )
    if plan_phase_id is not None:
        query = query.filter(models.PlanPhase.id != plan_phase_id)
    conflict = query.first()
    if conflict is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f'Das Label "{jira_label}" ist bereits Phase "{conflict.phase_type}" '
                f"(#{conflict.id}) zugeordnet. Ein Label darf pro Projekt nur einer "
                "Leaf-Phase zugeordnet sein."
            ),
        )


# ---------------------------------------------------------------------------
# PlanPhase
# ---------------------------------------------------------------------------


def _plan_phase_out(db: Session, p: models.PlanPhase) -> schemas.PlanPhaseOut:
    has_children = planning_calc.has_children(db, p.id)
    derived_start, derived_end = (
        planning_calc.derive_parent_bounds(db, p.id) if has_children else (None, None)
    )
    return schemas.PlanPhaseOut(
        id=p.id,
        project_id=p.project_id,
        subproject_id=p.subproject_id,
        parent_phase_id=p.parent_phase_id,
        reihenfolge=p.reihenfolge,
        phase_type=p.phase_type,
        baseline_start=p.baseline_start,
        baseline_end=p.baseline_end,
        forecast_start=p.forecast_start,
        forecast_end=p.forecast_end,
        actual_start=p.actual_start,
        actual_end=p.actual_end,
        status=p.status,
        progress=p.progress,
        plan_fte=p.plan_fte,
        jira_label=p.jira_label,
        owner_person_id=p.owner_person_id,
        owner_team_id=p.owner_team_id,
        erstellt_am=p.erstellt_am,
        aktualisiert_am=p.aktualisiert_am,
        tags=entity_links.tags_for(db, "plan_phase", p.id),
        documents=entity_links.documents_for(db, "plan_phase", p.id),
        has_children=has_children,
        derived_forecast_start=derived_start,
        derived_forecast_end=derived_end,
        derived_capacity=planning_calc.derive_parent_capacity(db, p.id) if has_children else None,
    )


def _get_plan_phase_or_404(db: Session, plan_phase_id: int) -> models.PlanPhase:
    p = db.get(models.PlanPhase, plan_phase_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Planphase nicht gefunden")
    return p


def _comment_out(db: Session, c: models.Comment) -> schemas.CommentOut:
    return schemas.CommentOut(
        id=c.id,
        project_id=c.project_id,
        subproject_id=c.subproject_id,
        monat=c.monat,
        phase_code=c.phase_code,
        text=c.text,
        erstellt_am=c.erstellt_am,
        parent_id=c.parent_id,
        plan_phase_id=c.plan_phase_id,
        tags=entity_links.tags_for(db, "comment", c.id),
        documents=entity_links.documents_for(db, "comment", c.id),
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


def _resource_demand_out(db: Session, demand: models.ResourceDemand) -> schemas.ResourceDemandOut:
    role = db.get(models.ResourceRole, demand.resource_role_id)
    # P19.2 (Kapazität-Tab N+1-Fix): Assignments inkl. Personenname in einem Zug mit abholen und
    # additiv in ResourceDemandOut.assignments einbetten (statt sie erst beim Aufklappen der
    # Rollenaufschlüsselung über einen eigenen Call pro Demand nachzuladen).
    rows = (
        db.query(models.ResourceAssignment, models.Person.display_name)
        .join(models.Person, models.Person.id == models.ResourceAssignment.person_id)
        .filter(models.ResourceAssignment.resource_demand_id == demand.id)
        .all()
    )
    assigned_fte = round(sum(a.fte for a, _ in rows), 2)
    return schemas.ResourceDemandOut(
        id=demand.id,
        project_id=demand.project_id,
        plan_phase_id=demand.plan_phase_id,
        resource_role_id=demand.resource_role_id,
        resource_role_name=role.name if role else "",
        period=demand.period,
        fte=demand.fte,
        commitment_level=demand.commitment_level,
        erstellt_am=demand.erstellt_am,
        aktualisiert_am=demand.aktualisiert_am,
        assigned_fte=assigned_fte,
        allocation_gap=round(demand.fte - assigned_fte, 2),
        assignments=[
            schemas.ResourceAssignmentOut(
                id=a.id,
                resource_demand_id=a.resource_demand_id,
                person_id=a.person_id,
                person_name=name,
                fte=a.fte,
                erstellt_am=a.erstellt_am,
                aktualisiert_am=a.aktualisiert_am,
            )
            for a, name in rows
        ],
    )


def _plan_phase_metrics(db: Session, p: models.PlanPhase) -> schemas.PhaseMetricsOut:
    # breakdown_sum = Summe ResourceDemand.fte dieser Phase (0.0, wenn keine Demands).
    breakdown_sum = (
        db.query(func.sum(models.ResourceDemand.fte))
        .filter(models.ResourceDemand.plan_phase_id == p.id)
        .scalar()
    ) or 0.0
    has_kids = planning_calc.has_children(db, p.id)
    if has_kids:
        # P20.4 (Parent-Übersicht, siehe P20_4_PLANPHASE_WORKSPACE_UX_REDIRECT.md Abschnitt 9):
        # eine Parent-Phase trägt selbst nie forecast_start/forecast_end/plan_fte (immer None,
        # Abschnitt 6b.1a) - Zeit verstrichen und Planstunden müssen deshalb wie
        # derive_parent_capacity/parent_ist_hours aus den Leaf-Nachfahren abgeleitet werden,
        # sonst wären beide Werte für jede Parent-Phase fälschlich None.
        derived_start, derived_end = planning_calc.derive_parent_bounds(db, p.id)
        time_progress_pct = phase_metrics_calc.time_progress(derived_start, derived_end)
        leaf_hours = [
            phase_metrics_calc.plan_hours(leaf.plan_fte, leaf.forecast_start, leaf.forecast_end)
            for leaf in planning_calc.leaf_descendants(db, p.id)
        ]
        leaf_hours = [h for h in leaf_hours if h is not None]
        ph = round(sum(leaf_hours), 2) if leaf_hours else None
    else:
        time_progress_pct = phase_metrics_calc.time_progress(p.forecast_start, p.forecast_end)
        ph = phase_metrics_calc.plan_hours(p.plan_fte, p.forecast_start, p.forecast_end)
    recon = phase_metrics_calc.reconcile(p.plan_fte, breakdown_sum)
    # P20.4 (BD-1 CLOSED, siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 15/16):
    # Parent-Ist ist IMMER die rekursive Summe ihrer Leaf-Nachfahren, nie eine eigene Quelle
    # (analog planning_calc.derive_parent_capacity für plan_fte).
    ist = (
        worklog_actuals.parent_ist_hours(db, p.id)
        if has_kids
        else worklog_actuals.leaf_ist_hours(db, p)
    )
    return schemas.PhaseMetricsOut(
        time_progress_pct=time_progress_pct,
        plan_hours=ph,
        effort_consumption_pct=phase_metrics_calc.effort_consumption(ist, ph),
        ist_hours=ist,
        remaining_plan_hours=phase_metrics_calc.remaining_plan_hours(ist, ph),
        overrun_hours=phase_metrics_calc.overrun_hours(ist, ph),
        reconciliation=schemas.ReconciliationOut(
            headline_fte=recon["headline_fte"],
            breakdown_fte=recon["breakdown_fte"],
            open_fte=recon["open_fte"],
        ),
    )


def _plan_phase_detail(db: Session, p: models.PlanPhase) -> schemas.PlanPhaseDetail:
    has_children = planning_calc.has_children(db, p.id)
    derived_start, derived_end = (
        planning_calc.derive_parent_bounds(db, p.id) if has_children else (None, None)
    )
    return schemas.PlanPhaseDetail(
        id=p.id,
        project_id=p.project_id,
        subproject_id=p.subproject_id,
        parent_phase_id=p.parent_phase_id,
        reihenfolge=p.reihenfolge,
        phase_type=p.phase_type,
        baseline_start=p.baseline_start,
        baseline_end=p.baseline_end,
        forecast_start=p.forecast_start,
        forecast_end=p.forecast_end,
        actual_start=p.actual_start,
        actual_end=p.actual_end,
        status=p.status,
        progress=p.progress,
        plan_fte=p.plan_fte,
        jira_label=p.jira_label,
        owner_person_id=p.owner_person_id,
        owner_team_id=p.owner_team_id,
        erstellt_am=p.erstellt_am,
        aktualisiert_am=p.aktualisiert_am,
        tags=entity_links.tags_for(db, "plan_phase", p.id),
        documents=entity_links.documents_for(db, "plan_phase", p.id),
        has_children=has_children,
        derived_forecast_start=derived_start,
        derived_forecast_end=derived_end,
        derived_capacity=planning_calc.derive_parent_capacity(db, p.id) if has_children else None,
        children=[_plan_phase_out(db, child) for child in planning_calc.direct_children(db, p.id)],
        comments=[
            _comment_out(db, c)
            for c in (
                db.query(models.Comment)
                .filter(models.Comment.plan_phase_id == p.id)
                .order_by(models.Comment.erstellt_am.desc())
                .all()
            )
        ],
        tasks=[
            _task_out(db, t)
            for t in (
                db.query(models.Task)
                .filter(models.Task.plan_phase_id == p.id)
                .order_by(models.Task.erstellt_am.desc())
                .all()
            )
        ],
        blockers=[
            _blocker_out(db, b)
            for b in (
                db.query(models.Blocker)
                .filter(models.Blocker.plan_phase_id == p.id)
                .order_by(models.Blocker.erstellt_am.desc())
                .all()
            )
        ],
        decisions=[
            _decision_out(db, d)
            for d in (
                db.query(models.Decision)
                .filter(models.Decision.plan_phase_id == p.id)
                .order_by(models.Decision.erstellt_am.desc())
                .all()
            )
        ],
        resource_demands=[
            _resource_demand_out(db, demand)
            for demand in (
                db.query(models.ResourceDemand)
                .filter(models.ResourceDemand.plan_phase_id == p.id)
                .order_by(models.ResourceDemand.id)
                .all()
            )
        ],
        # P19.5 (additiv, siehe schemas.PlanPhaseDetail.milestones): gleiche Sortierung wie
        # list_milestones (Datum, dann id) - kein neuer Endpoint nötig, _milestone_out ist
        # bereits weiter unten in dieser Datei definiert.
        milestones=[
            _milestone_out(db, m)
            for m in (
                db.query(models.Milestone)
                .filter(models.Milestone.plan_phase_id == p.id)
                .order_by(models.Milestone.baseline_date, models.Milestone.id)
                .all()
            )
        ],
        metrics=_plan_phase_metrics(db, p),
        # P19.2 (Kapazität-Tab Round-Trip-Reduktion, Gap 3): dieselbe Bedarf/Besetzt/Offen-
        # Auswertung wie GET .../assignment-summary additiv mitliefern, damit der Kapazität-Tab
        # sie beim Öffnen nicht mehr separat nachladen muss. Der eigenständige Endpoint bleibt
        # unverändert bestehen (andere Aufrufer könnten ihn weiterhin direkt nutzen).
        assignment_summary=_plan_phase_assignment_summary(db, p),
    )


@router.get("/{project_id}/plan-phases", response_model=list[schemas.PlanPhaseOut])
def list_plan_phases(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.PlanPhase)
        .filter(models.PlanPhase.project_id == project_id)
        .order_by(models.PlanPhase.baseline_start, models.PlanPhase.id)
        .all()
    )
    return [_plan_phase_out(db, p) for p in rows]


@router.post("/{project_id}/plan-phases", response_model=schemas.PlanPhaseOut, status_code=201)
def create_plan_phase(project_id: int, payload: schemas.PlanPhaseCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    _check_subproject(db, project_id, payload.subproject_id)
    _check_owner(db, payload.owner_person_id, payload.owner_team_id)
    _check_parent_phase(db, project_id, plan_phase_id=None, parent_phase_id=payload.parent_phase_id)
    _check_jira_label_conflict(db, project_id, plan_phase_id=None, jira_label=payload.jira_label)
    now = _now()
    plan_phase = models.PlanPhase(
        project_id=project_id,
        subproject_id=payload.subproject_id,
        parent_phase_id=payload.parent_phase_id,
        reihenfolge=payload.reihenfolge,
        phase_type=payload.phase_type,
        baseline_start=payload.baseline_start,
        baseline_end=payload.baseline_end,
        forecast_start=payload.forecast_start,
        forecast_end=payload.forecast_end,
        actual_start=payload.actual_start,
        actual_end=payload.actual_end,
        status=payload.status,
        progress=None,  # P6: Fortschritts-Dimension deprecatet - wird beim Anlegen ignoriert
        plan_fte=payload.plan_fte,
        jira_label=payload.jira_label,
        owner_person_id=payload.owner_person_id,
        owner_team_id=payload.owner_team_id,
        erstellt_am=now,
        aktualisiert_am=now,
    )
    db.add(plan_phase)
    db.flush()
    created_batch = history.record_created(
        db,
        project_id=project_id,
        entity_type="plan_phase",
        entity_id=plan_phase.id,
        entity_label=plan_phase.phase_type,
        fields=history.snapshot(plan_phase, "plan_phase"),
        plan_phase_id=plan_phase.id,
    )
    if payload.parent_phase_id is not None:
        # P18/B-3 (Abschnitt 6b.1a): das ist das erste Kind der übergeordneten Phase (oder
        # eines von mehreren) - _maybe_historize_parent_fte ist idempotent (No-Op, sobald
        # plan_fte bereits None ist), daher unabhängig von "erstes Kind ja/nein" sicher.
        parent = db.get(models.PlanPhase, payload.parent_phase_id)
        _maybe_historize_parent_fte(db, parent)
    if payload.tags:
        entity_links.sync_tags(db, "plan_phase", plan_phase.id, payload.tags)
        history.record_tag_diff(
            db,
            project_id=project_id,
            entity_type="plan_phase",
            entity_id=plan_phase.id,
            entity_label=plan_phase.phase_type,
            old_tags=[],
            new_tags=payload.tags,
            plan_phase_id=plan_phase.id,
            batch_id=created_batch,
        )
    db.commit()
    db.refresh(plan_phase)
    return _plan_phase_out(db, plan_phase)


@router.put("/plan-phases/{plan_phase_id}", response_model=schemas.PlanPhaseOut)
def update_plan_phase(plan_phase_id: int, payload: schemas.PlanPhaseUpdate, db: Session = Depends(get_db)):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"tags"})
    # P11: progress ist deprecatet (P6) - kein Update-Pfad soll ihn mehr schreiben können,
    # analog zu create_plan_phase() oben. Feld bleibt im Schema für Rückwärtskompatibilität.
    changes.pop("progress", None)
    if "subproject_id" in changes:
        _check_subproject(db, plan_phase.project_id, changes["subproject_id"])
    _check_owner(db, changes.get("owner_person_id"), changes.get("owner_team_id"))
    new_parent_id = changes.get("parent_phase_id")
    if "parent_phase_id" in changes and new_parent_id != plan_phase.parent_phase_id:
        _check_parent_phase(db, plan_phase.project_id, plan_phase_id=plan_phase.id, parent_phase_id=new_parent_id)
    if "jira_label" in changes and changes["jira_label"] != plan_phase.jira_label:
        _check_jira_label_conflict(
            db, plan_phase.project_id, plan_phase_id=plan_phase.id, jira_label=changes["jira_label"]
        )
    old = history.snapshot(plan_phase, "plan_phase")
    old_tags = entity_links.tags_for(db, "plan_phase", plan_phase.id)
    batch_id = history.new_batch_id()
    if changes:
        for field, value in changes.items():
            setattr(plan_phase, field, value)
        plan_phase.aktualisiert_am = _now()
    history.record_updated(
        db,
        project_id=plan_phase.project_id,
        entity_type="plan_phase",
        entity_id=plan_phase.id,
        entity_label=plan_phase.phase_type,
        old=old,
        new=history.snapshot(plan_phase, "plan_phase"),
        plan_phase_id=plan_phase.id,
        batch_id=batch_id,
    )
    if "parent_phase_id" in changes and new_parent_id is not None:
        parent = db.get(models.PlanPhase, new_parent_id)
        _maybe_historize_parent_fte(db, parent)
    if payload.tags is not None:
        entity_links.sync_tags(db, "plan_phase", plan_phase.id, payload.tags)
        history.record_tag_diff(
            db,
            project_id=plan_phase.project_id,
            entity_type="plan_phase",
            entity_id=plan_phase.id,
            entity_label=plan_phase.phase_type,
            old_tags=old_tags,
            new_tags=payload.tags,
            plan_phase_id=plan_phase.id,
            batch_id=batch_id,
        )
    db.commit()
    db.refresh(plan_phase)
    return _plan_phase_out(db, plan_phase)


@router.delete("/plan-phases/{plan_phase_id}", status_code=204)
def delete_plan_phase(plan_phase_id: int, db: Session = Depends(get_db)):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    child_count = len(planning_calc.direct_children(db, plan_phase_id))
    if child_count > 0:
        # BD-11, CLOSED (Abschnitt 6b.9): Standard-DELETE einer Parent-Phase mit Kindern wird
        # blockiert, NICHT kaskadiert. Angebotene Wege: reparent-children (danach ist die
        # Phase leaf und normal löschbar) oder die separate, stark bestätigte
        # delete-subtree-Aktion.
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    f"Diese Phase enthält {child_count} Unterphase(n) und kann nicht direkt "
                    "gelöscht werden. Unterphasen verschieben oder den gesamten Zweig löschen."
                ),
                "child_count": child_count,
            },
        )
    # P20.1G (Delete Stabilization): Root-Cause-Fix - VOR dem eigentlichen db.delete() alle
    # ResourceAssignment/ResourceDemand/WorklogPhaseOverride-Zeilen dieser Phase aufräumen
    # (siehe capacity_calc.cleanup_phase_resource_dependencies-Docstring).
    history.record_deleted(
        db,
        project_id=plan_phase.project_id,
        entity_type="plan_phase",
        entity_id=plan_phase.id,
        entity_label=plan_phase.phase_type,
        fields=history.snapshot(plan_phase, "plan_phase"),
        plan_phase_id=None,
    )
    capacity_calc.cleanup_phase_resource_dependencies(db, [plan_phase_id])
    entity_links.delete_links_for_entity(db, "plan_phase", plan_phase_id)
    entity_links.delete_relations_for_entity(db, "plan_phase", plan_phase_id)
    try:
        db.delete(plan_phase)
        db.commit()
    except IntegrityError:
        # Letzte Sicherheitsnetz-Ebene (Auftrag Abschnitt 26): sollte durch die Aufräumung
        # oben nicht mehr erreichbar sein - falls doch (z.B. eine künftige, hier noch nicht
        # bekannte FK-Beziehung), NIEMALS eine rohe 500-Exception ohne CORS-Header
        # durchschlagen lassen, sondern einen strukturierten, fachlichen 409 liefern.
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Diese Phase kann aufgrund bestehender Verknüpfungen nicht gelöscht werden.",
                "child_count": 0,
            },
        ) from None


@router.post(
    "/plan-phases/{plan_phase_id}/reparent-children",
    response_model=schemas.PlanPhaseReparentChildrenResult,
)
def reparent_children(
    plan_phase_id: int, payload: schemas.PlanPhaseReparentChildrenRequest, db: Session = Depends(get_db)
):
    """P18/B-3 (CONCEPT.md Abschnitt 6b.9): verschiebt alle direkten Kinder dieser Phase auf
    eine andere übergeordnete Phase (oder auf Top-Level, new_parent_phase_id=None). Danach ist
    diese Phase leaf und normal per DELETE löschbar - plan_fte bleibt dabei unverändert NULL
    (keine automatische Reaktivierung, Abschnitt 6b.1a)."""
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    children = planning_calc.direct_children(db, plan_phase_id)
    for child in children:
        _check_parent_phase(
            db, plan_phase.project_id, plan_phase_id=child.id, parent_phase_id=payload.new_parent_phase_id
        )
    now = _now()
    batch_id = history.new_batch_id()
    for child in children:
        old_parent = child.parent_phase_id
        child.parent_phase_id = payload.new_parent_phase_id
        child.aktualisiert_am = now
        history.record_updated(
            db,
            project_id=plan_phase.project_id,
            entity_type="plan_phase",
            entity_id=child.id,
            entity_label=child.phase_type,
            old={"parent_phase_id": old_parent},
            new={"parent_phase_id": payload.new_parent_phase_id},
            plan_phase_id=child.id,
            batch_id=batch_id,
        )
    if payload.new_parent_phase_id is not None:
        new_parent = db.get(models.PlanPhase, payload.new_parent_phase_id)
        _maybe_historize_parent_fte(db, new_parent)
    db.commit()
    return schemas.PlanPhaseReparentChildrenResult(
        moved_count=len(children),
        children=[_plan_phase_out(db, child) for child in children],
    )


def _collect_subtree_impact(db: Session, plan_phase: models.PlanPhase) -> dict:
    descendants = planning_calc.all_descendants(db, plan_phase.id)
    all_ids = [plan_phase.id] + [d.id for d in descendants]

    def _count(model, column) -> int:
        return db.query(model).filter(column.in_(all_ids)).count()

    demand_ids = [
        row[0]
        for row in db.query(models.ResourceDemand.id)
        .filter(models.ResourceDemand.plan_phase_id.in_(all_ids))
        .all()
    ]
    assignments = (
        db.query(models.ResourceAssignment)
        .filter(models.ResourceAssignment.resource_demand_id.in_(demand_ids))
        .count()
        if demand_ids
        else 0
    )
    # P20.1G: direkte Zuordnungen (plan_phase_id gesetzt) zählen zusätzlich zu den
    # Legacy-Assignments über eine ResourceDemand dieser Phasen (assignments oben).
    direct_assignments = (
        db.query(models.ResourceAssignment).filter(models.ResourceAssignment.plan_phase_id.in_(all_ids)).count()
    )
    worklog_overrides_affected = (
        db.query(models.WorklogPhaseOverride)
        .filter(models.WorklogPhaseOverride.plan_phase_id.in_(all_ids))
        .count()
    )
    documents_affected = (
        db.query(models.DocumentLink)
        .filter(models.DocumentLink.entity_type == "plan_phase", models.DocumentLink.entity_id.in_(all_ids))
        .count()
    )
    return {
        "descendants": descendants,
        "all_ids": all_ids,
        "comments_affected": _count(models.Comment, models.Comment.plan_phase_id),
        "tasks_affected": _count(models.Task, models.Task.plan_phase_id),
        "blockers_affected": _count(models.Blocker, models.Blocker.plan_phase_id),
        "decisions_affected": _count(models.Decision, models.Decision.plan_phase_id),
        "milestones_affected": _count(models.Milestone, models.Milestone.plan_phase_id),
        "documents_affected": documents_affected,
        "resource_demands_affected": len(demand_ids),
        "resource_assignments_affected": assignments + direct_assignments,
        "worklog_overrides_affected": worklog_overrides_affected,
        "demand_ids": demand_ids,
    }


@router.get("/plan-phases/{plan_phase_id}/subtree-impact", response_model=schemas.PlanPhaseSubtreeImpactOut)
def get_subtree_impact(plan_phase_id: int, db: Session = Depends(get_db)):
    """P18/B-3 (Abschnitt 6b.9): zeigt die Auswirkungen einer "Gesamten Zweig löschen"-Aktion
    an, BEVOR sie ausgeführt wird - Anzahl betroffener Nachfahren-Phasen sowie Assignments/
    Collaboration (Comments/Tasks/Blocker/Decisions)/Milestones/Documents."""
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    impact = _collect_subtree_impact(db, plan_phase)
    return schemas.PlanPhaseSubtreeImpactOut(
        plan_phase_id=plan_phase.id,
        phase_type=plan_phase.phase_type,
        descendant_phase_count=len(impact["descendants"]),
        comments_affected=impact["comments_affected"],
        tasks_affected=impact["tasks_affected"],
        blockers_affected=impact["blockers_affected"],
        decisions_affected=impact["decisions_affected"],
        milestones_affected=impact["milestones_affected"],
        documents_affected=impact["documents_affected"],
        resource_demands_affected=impact["resource_demands_affected"],
        resource_assignments_affected=impact["resource_assignments_affected"],
        worklog_overrides_affected=impact["worklog_overrides_affected"],
    )


@router.post("/plan-phases/{plan_phase_id}/delete-subtree", status_code=204)
def delete_subtree(
    plan_phase_id: int, payload: schemas.PlanPhaseDeleteSubtreeRequest, db: Session = Depends(get_db)
):
    """P18/B-3 (BD-11, CLOSED, Abschnitt 6b.9): separate, stark bestätigte, auditierbare
    Aktion - NIE die Standardaktion (das ist der blockierende Standard-DELETE oben). Löscht
    diese Phase und alle Nachfahren-Phasen inkl. ihrer ResourceDemand/ResourceAssignment-
    Zeilen. Collaboration-Inhalte (Comments/Tasks/Blocker/Decisions/Milestones) werden NICHT
    gelöscht, nur entkoppelt (plan_phase_id -> NULL, analog zum bestehenden ON DELETE SET
    NULL-Verhalten eines einzelnen Phasen-Deletes) - ihre Historie bleibt erhalten."""
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    impact = _collect_subtree_impact(db, plan_phase)
    descendant_count = len(impact["descendants"])
    if (
        payload.confirm_phase_type != plan_phase.phase_type
        or payload.confirm_descendant_count != descendant_count
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Bestätigung stimmt nicht überein - erwartet phase_type="
                f"'{plan_phase.phase_type}' und descendant_count={descendant_count}"
            ),
        )

    all_ids = impact["all_ids"]
    now = _now()

    # P20.1G (Delete Stabilization): dieselbe dialektunabhängige Aufräumung wie beim
    # Standard-DELETE einer einzelnen Phase (siehe capacity_calc.cleanup_phase_resource_dependencies-
    # Docstring) - deckt jetzt zusätzlich WorklogPhaseOverride und direkte
    # ResourceAssignment.plan_phase_id-Zeilen ab (vorher hier fehlend, derselbe Root-Cause-Bug
    # wie beim Einzel-Delete).
    capacity_calc.cleanup_phase_resource_dependencies(db, all_ids)

    # Collaboration-Inhalte bleiben erhalten, nur die Verknüpfung entfällt (wie beim
    # bestehenden ON DELETE SET NULL-Verhalten eines einzelnen Phasen-Deletes).
    for model in (models.Comment, models.Task, models.Blocker, models.Decision, models.Milestone):
        db.query(model).filter(model.plan_phase_id.in_(all_ids)).update(
            {"plan_phase_id": None}, synchronize_session=False
        )
    db.query(models.PlanHistory).filter(models.PlanHistory.plan_phase_id.in_(all_ids)).update(
        {"plan_phase_id": None}, synchronize_session=False
    )
    db.query(models.DocumentLink).filter(
        models.DocumentLink.entity_type == "plan_phase", models.DocumentLink.entity_id.in_(all_ids)
    ).delete(synchronize_session=False)
    db.query(models.TagLink).filter(
        models.TagLink.entity_type == "plan_phase", models.TagLink.entity_id.in_(all_ids)
    ).delete(synchronize_session=False)
    db.query(models.EntityRelation).filter(
        (
            (models.EntityRelation.source_entity_type == "plan_phase")
            & (models.EntityRelation.source_entity_id.in_(all_ids))
        )
        | (
            (models.EntityRelation.target_entity_type == "plan_phase")
            & (models.EntityRelation.target_entity_id.in_(all_ids))
        )
    ).delete(synchronize_session=False)

    # Audit-Eintrag (Abschnitt 6b.9: auditierbar, wer wann welchen Zweig gelöscht hat).
    # plan_phase_id bleibt bewusst None - die referenzierten Phasen existieren gleich nicht
    # mehr, der Alt-Wert hält die Information stattdessen im Klartext fest.
    history.record_deleted(
        db,
        project_id=plan_phase.project_id,
        entity_type="plan_phase",
        entity_id=plan_phase.id,
        entity_label=f"{plan_phase.phase_type} (+{descendant_count} Unterphasen)",
        fields=history.snapshot(plan_phase, "plan_phase"),
        plan_phase_id=None,
        timestamp=now,
        bereich="phase_subtree_delete",
    )

    # Nachfahren-Phasen tiefste Ebene zuerst löschen (parent_phase_id-FK hat kein
    # ON DELETE CASCADE - ein Kind muss vor seinem Elternteil gelöscht werden). P20.2
    # (Regression Recovery): NICHT über ORM-Objekt-`db.delete(phase)` + einem gemeinsamen
    # `db.commit()` am Ende - PlanPhase.parent_phase_id ist eine reine FK-Spalte OHNE
    # gemapptes `relationship()` (siehe models.py), SQLAlchemys Unit-of-Work hat für
    # Self-FKs ohne Relationship-Metadaten keine Dependency-Info und kann die noetige
    # Reihenfolge nicht herleiten - der finale DELETE-Batch wird dann NICHT zwingend in der
    # hier berechneten tiefste-zuerst-Reihenfolge ausgefuehrt (beobachtet: Primary-Key-
    # aufsteigend statt tiefe-absteigend). Bei einer 3-Ebenen-Hierarchie (Parent/Child/
    # Grandchild, BD-10) fuehrte das auf echtem PostgreSQL zu `ForeignKeyViolation:
    # ... still referenced from table "plan_phases"`, weil der Parent vor seinem Kind
    # geloescht wurde - auf SQLite (FK-Pragma standardmaessig aus, siehe capacity_calc.
    # cleanup_phase_resource_dependencies-Docstring) blieb das unbemerkt, weshalb keiner
    # der 16 SQLite-Regressionsskripte dies auffing. Bulk-`Query.delete()` je Phase (statt
    # ORM-Objekt-Delete) fuehrt das DELETE SOFORT beim Aufruf aus, nicht erst gebuendelt bei
    # einem spaeteren Flush - garantiert dieselbe, hier explizit berechnete Reihenfolge
    # dialektunabhaengig auf SQLite und PostgreSQL.
    descendants_by_depth = sorted(
        impact["descendants"], key=lambda phase: planning_calc.depth_of(db, phase.id), reverse=True
    )
    for phase in descendants_by_depth:
        db.query(models.PlanPhase).filter(models.PlanPhase.id == phase.id).delete(synchronize_session=False)
    db.query(models.PlanPhase).filter(models.PlanPhase.id == plan_phase.id).delete(synchronize_session=False)
    try:
        db.commit()
    except IntegrityError:
        # Letztes Sicherheitsnetz (Auftrag Abschnitt 26), siehe delete_plan_phase oben.
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"message": "Dieser Zweig kann aufgrund bestehender Verknüpfungen nicht gelöscht werden.", "child_count": descendant_count},
        ) from None


@router.get("/plan-phases/{plan_phase_id}", response_model=schemas.PlanPhaseDetail)
def get_plan_phase_detail(plan_phase_id: int, db: Session = Depends(get_db)):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    return _plan_phase_detail(db, plan_phase)


@router.get("/plan-phases/{plan_phase_id}/metrics", response_model=schemas.PhaseMetricsOut)
def get_plan_phase_metrics(plan_phase_id: int, db: Session = Depends(get_db)):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    return _plan_phase_metrics(db, plan_phase)


@router.get("/plan-phases/{plan_phase_id}/jira-matches", response_model=schemas.JiraMatchPreviewOut)
def get_plan_phase_jira_matches(plan_phase_id: int, label: str, db: Session = Depends(get_db)):
    """P20.5 (Mapping-Preview, siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt
    10): zeigt vor dem Speichern eines jira_label, was er aktuell treffen würde - rein
    lesend gegen den bereits vorhandenen Sync-Cache, keine Live-Jira-Abfrage, kein
    zusätzlicher API-Call. `label` wird gegen `JiraIssueCache.labels` (kommagetrennt)
    dieses Projekts geprüft, unabhängig davon, ob die Phase das Label bereits gespeichert
    hat (Preview VOR dem Speichern)."""
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    issues = (
        db.query(models.JiraIssueCache)
        .filter(models.JiraIssueCache.project_id == plan_phase.project_id)
        .all()
    )
    matched = [i for i in issues if label in (i.labels.split(",") if i.labels else [])]
    matched_keys = [i.jira_issue_key for i in matched]

    matched_worklogs = 0
    total_hours = 0.0
    if matched_keys:
        rows = (
            db.query(models.JiraWorklogCache)
            .filter(
                models.JiraWorklogCache.projekt_mapping == str(plan_phase.project_id),
                models.JiraWorklogCache.jira_issue_key.in_(matched_keys),
            )
            .all()
        )
        matched_worklogs = len(rows)
        total_hours = round(sum(r.stunden for r in rows), 2)

    return schemas.JiraMatchPreviewOut(
        matched_issues=len(matched),
        matched_worklogs=matched_worklogs,
        total_hours=total_hours,
        sample_issue_keys=matched_keys[:5],
        as_of=max((i.last_synced_at for i in matched), default=None),
    )


@router.get("/plan-phases/{plan_phase_id}/person-actuals", response_model=schemas.PlanPhasePersonActualsOut)
def get_plan_phase_person_actuals(plan_phase_id: int, db: Session = Depends(get_db)):
    """P20.6 (Personen-Drilldown + Planned-vs-Actual, siehe
    P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 17/18/24/25): gruppiert dieselben
    Resolver-zugeordneten Worklog-Zeilen wie die Phase-Ist-Metriken (P20.4) zusätzlich nach
    Person, und vergleicht sie mit den geplanten `ResourceAssignment`s dieser Phase (bzw.
    ihrer Leaf-Nachfahren, falls Parent) - keine neue Personendatenquelle, keine
    automatische Änderung der Ressourcenplanung."""
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)

    ist_hours = (
        worklog_actuals.parent_ist_hours(db, plan_phase.id)
        if planning_calc.has_children(db, plan_phase.id)
        else worklog_actuals.leaf_ist_hours(db, plan_phase)
    )
    person_hours = worklog_actuals.person_hours_for_phase(db, plan_phase)

    accounts = list(person_hours.keys())
    persons_by_account = (
        {p.jira_account_id: p for p in db.query(models.Person).filter(models.Person.jira_account_id.in_(accounts))}
        if accounts
        else {}
    )
    unassigned_by_account = (
        {
            u.jira_account_id: u
            for u in db.query(models.UnassignedJiraAuthor).filter(
                models.UnassignedJiraAuthor.jira_account_id.in_(accounts)
            )
        }
        if accounts
        else {}
    )

    # Geplante Personen: ResourceAssignment über alle Leaf-Nachfahren dieser Phase (bzw. sie
    # selbst, falls bereits Leaf - leaf_descendants liefert eine Leaf-Phase als ihren eigenen
    # einzigen Nachfahren, daher ohne Fallunterscheidung). P20.1: über BEIDE Ressourcenwege
    # gemerged (direkte plan_phase_id-Zuordnung + Legacy über eine ResourceDemand) - eine
    # migrierte Zeile (beide FKs gesetzt) zählt nur einmal über den direkten Zweig.
    leaf_ids = [leaf.id for leaf in planning_calc.leaf_descendants(db, plan_phase.id)]
    if leaf_ids:
        direct_assignment_rows = (
            db.query(models.ResourceAssignment, models.Person)
            .join(models.Person, models.Person.id == models.ResourceAssignment.person_id)
            .filter(models.ResourceAssignment.plan_phase_id.in_(leaf_ids))
            .all()
        )
        legacy_assignment_rows = (
            db.query(models.ResourceAssignment, models.Person)
            .join(models.ResourceDemand, models.ResourceDemand.id == models.ResourceAssignment.resource_demand_id)
            .join(models.Person, models.Person.id == models.ResourceAssignment.person_id)
            .filter(
                models.ResourceDemand.plan_phase_id.in_(leaf_ids),
                models.ResourceAssignment.plan_phase_id.is_(None),
            )
            .all()
        )
        assignment_rows = direct_assignment_rows + legacy_assignment_rows
    else:
        assignment_rows = []
    planned_by_person_id: dict[int, dict] = {}
    for assignment, person in assignment_rows:
        entry = planned_by_person_id.setdefault(
            person.id, {"person_id": person.id, "person_name": person.display_name, "fte": 0.0}
        )
        entry["fte"] += assignment.fte
    planned_person_ids = set(planned_by_person_id.keys())

    persons_out = []
    for account_id, hours in person_hours.items():
        person = persons_by_account.get(account_id)
        if person is not None:
            display_name = person.display_name
        elif account_id in unassigned_by_account:
            display_name = unassigned_by_account[account_id].display_name
        else:
            display_name = account_id
        persons_out.append(
            schemas.PersonActualOut(
                jira_account_id=account_id,
                person_id=person.id if person is not None else None,
                display_name=display_name,
                hours=hours,
                planned=person is not None and person.id in planned_person_ids,
            )
        )
    persons_out.sort(key=lambda p: -p.hours)

    actual_person_ids = {p.id for p in persons_by_account.values()}
    planned_without_actual = [
        schemas.PlanPhaseAssignedPersonOut(person_id=e["person_id"], person_name=e["person_name"], fte=round(e["fte"], 4))
        for e in sorted(planned_by_person_id.values(), key=lambda e: e["person_name"])
        if e["person_id"] not in actual_person_ids
    ]

    unplanned_actual_hours = (
        None if ist_hours is None else round(sum(p.hours for p in persons_out if not p.planned), 2)
    )

    return schemas.PlanPhasePersonActualsOut(
        plan_phase_id=plan_phase.id,
        ist_hours=ist_hours,
        persons=persons_out,
        unplanned_actual_hours=unplanned_actual_hours,
        planned_without_actual=planned_without_actual,
    )


# ---------------------------------------------------------------------------
# Worklog Phase Overrides (P20.1, BD-1B CLOSED, siehe
# P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 14/25) - manuelle
# Worklog->PlanPhase-Zuordnung auf Issue-Key-Ebene. Ändert niemals Jira/Tempo-Originaldaten.
# Der Resolver, der diese Overrides tatsächlich auswertet, folgt erst in P20.2 - dieses Paket
# liefert nur die Datenhaltung + CRUD.
# ---------------------------------------------------------------------------


def _worklog_phase_override_out(o: models.WorklogPhaseOverride) -> schemas.WorklogPhaseOverrideOut:
    return schemas.WorklogPhaseOverrideOut(
        id=o.id,
        project_id=o.project_id,
        jira_issue_key=o.jira_issue_key,
        plan_phase_id=o.plan_phase_id,
        previous_status=o.previous_status,
        note=o.note,
        created_by_person_id=o.created_by_person_id,
        created_at=o.created_at,
    )


@router.get(
    "/plan-phases/{plan_phase_id}/worklog-overrides",
    response_model=list[schemas.WorklogPhaseOverrideOut],
)
def list_worklog_overrides(plan_phase_id: int, db: Session = Depends(get_db)):
    _get_plan_phase_or_404(db, plan_phase_id)
    rows = (
        db.query(models.WorklogPhaseOverride)
        .filter(models.WorklogPhaseOverride.plan_phase_id == plan_phase_id)
        .order_by(models.WorklogPhaseOverride.created_at.desc())
        .all()
    )
    return [_worklog_phase_override_out(o) for o in rows]


@router.post(
    "/plan-phases/{plan_phase_id}/worklog-overrides",
    response_model=schemas.WorklogPhaseOverrideOut,
    status_code=201,
)
def create_worklog_override(
    plan_phase_id: int, payload: schemas.WorklogPhaseOverrideCreate, db: Session = Depends(get_db)
):
    """Legt einen Override an oder verschiebt einen bestehenden auf diese Phase (Upsert per
    jira_issue_key, das über die gesamte Tabelle UNIQUE ist - Abschnitt 14: "Bearbeiten" eines
    Overrides ist fachlich dasselbe wie ihn erneut mit neuer Ziel-Phase anzulegen)."""
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    if payload.created_by_person_id is not None and db.get(models.Person, payload.created_by_person_id) is None:
        raise HTTPException(status_code=404, detail="Person (created_by_person_id) nicht gefunden")
    override = (
        db.query(models.WorklogPhaseOverride)
        .filter(models.WorklogPhaseOverride.jira_issue_key == payload.jira_issue_key)
        .first()
    )
    now = _now()
    if override is None:
        override = models.WorklogPhaseOverride(jira_issue_key=payload.jira_issue_key)
        db.add(override)
        is_create = True
        old = None
    else:
        is_create = False
        old = history.snapshot(override, "worklog_override")
    override.project_id = plan_phase.project_id
    override.plan_phase_id = plan_phase_id
    override.previous_status = payload.previous_status
    override.note = payload.note
    override.created_by_person_id = payload.created_by_person_id
    override.created_at = now
    db.flush()
    label = payload.jira_issue_key
    if is_create:
        history.record_created(
            db,
            project_id=plan_phase.project_id,
            entity_type="worklog_override",
            entity_id=override.id,
            entity_label=label,
            fields=history.snapshot(override, "worklog_override"),
            plan_phase_id=plan_phase_id,
        )
    else:
        history.record_updated(
            db,
            project_id=plan_phase.project_id,
            entity_type="worklog_override",
            entity_id=override.id,
            entity_label=label,
            old=old or {},
            new=history.snapshot(override, "worklog_override"),
            plan_phase_id=plan_phase_id,
        )
    db.commit()
    db.refresh(override)
    return _worklog_phase_override_out(override)


@router.delete("/plan-phases/{plan_phase_id}/worklog-overrides/{jira_issue_key}", status_code=204)
def delete_worklog_override(plan_phase_id: int, jira_issue_key: str, db: Session = Depends(get_db)):
    _get_plan_phase_or_404(db, plan_phase_id)
    override = (
        db.query(models.WorklogPhaseOverride)
        .filter(
            models.WorklogPhaseOverride.plan_phase_id == plan_phase_id,
            models.WorklogPhaseOverride.jira_issue_key == jira_issue_key,
        )
        .first()
    )
    if override is None:
        raise HTTPException(status_code=404, detail="Override nicht gefunden")
    history.record_deleted(
        db,
        project_id=override.project_id,
        entity_type="worklog_override",
        entity_id=override.id,
        entity_label=override.jira_issue_key,
        fields=history.snapshot(override, "worklog_override"),
        plan_phase_id=plan_phase_id,
    )
    db.delete(override)
    db.commit()


# ---------------------------------------------------------------------------
# Direct Assignment ohne Rollen-Zwang (P18/B-4, P20.1: jetzt ohne ResourceDemand als
# technischen Adapter - siehe CONCEPT.md Abschnitt 6b.4/6b.10/6b.11 sowie Abschnitt 12/6c)
# ---------------------------------------------------------------------------


def _find_system_role(db: Session) -> models.ResourceRole | None:
    """Interne Systemrolle "Ohne Rolle", per B-1-Migration geseedet (Abschnitt 6b.4) - reine
    Lookup-Funktion (KEIN auto-create mehr, P20.1): der neue Direct-Assignment-Flow braucht
    sie nicht mehr als Trägerschicht, sie wird hier nur noch gesucht, um bestehende
    Alt-Zuordnungen (vor P20.1 über diese Systemrolle angelegt) beim Upsert/Unassign
    wiederzufinden und zu aktualisieren statt eine doppelte, zweite Zeile für dieselbe Person
    anzulegen. None, falls die Migration (noch) nicht gelaufen ist oder keine Alt-Zuordnungen
    existieren - dann gibt es schlicht nichts zu migrieren/finden."""
    return db.query(models.ResourceRole).filter(models.ResourceRole.is_system_role.is_(True)).first()


def _plan_phase_assignment_rows(
    db: Session, plan_phase_id: int
) -> list[tuple[models.ResourceAssignment, str]]:
    """P20.1 (Capacity Consumer Rewiring, CONCEPT.md Abschnitt 12/6c): alle Personenzuordnungen
    einer Leaf-PlanPhase, über BEIDE Ressourcenwege gemerged - der neue direkte Standardpfad
    (ResourceAssignment.plan_phase_id gesetzt) UND der Legacy-Pfad über eine ResourceDemand
    dieser Phase (Rollen-Aufschlüsselung oder die frühere "Ohne Rolle"-Carrier-Demand). Eine
    bereits migrierte Zeile (beide FKs gesetzt, siehe
    scripts/migrate_resource_assignments_to_plan_phase.py) zählt nur einmal - sie wird über
    plan_phase_id gefunden, die Legacy-Query schließt `plan_phase_id IS NOT NULL` explizit aus."""
    direct_rows = (
        db.query(models.ResourceAssignment, models.Person.display_name)
        .join(models.Person, models.Person.id == models.ResourceAssignment.person_id)
        .filter(models.ResourceAssignment.plan_phase_id == plan_phase_id)
        .all()
    )
    legacy_rows = (
        db.query(models.ResourceAssignment, models.Person.display_name)
        .join(models.ResourceDemand, models.ResourceDemand.id == models.ResourceAssignment.resource_demand_id)
        .join(models.Person, models.Person.id == models.ResourceAssignment.person_id)
        .filter(
            models.ResourceDemand.plan_phase_id == plan_phase_id,
            models.ResourceAssignment.plan_phase_id.is_(None),
        )
        .all()
    )
    return direct_rows + legacy_rows


def _plan_phase_assignment_summary(
    db: Session, plan_phase: models.PlanPhase
) -> schemas.PlanPhaseAssignmentSummaryOut:
    rows = _plan_phase_assignment_rows(db, plan_phase.id)
    by_person: dict[int, dict] = {}
    for assignment, person_name in rows:
        entry = by_person.setdefault(
            assignment.person_id, {"person_id": assignment.person_id, "person_name": person_name, "fte": 0.0}
        )
        entry["fte"] += assignment.fte
    assigned_fte = sum(entry["fte"] for entry in by_person.values())
    summary = phase_metrics_calc.assignment_summary(plan_phase.plan_fte, assigned_fte)
    return schemas.PlanPhaseAssignmentSummaryOut(
        plan_phase_id=plan_phase.id,
        plan_fte=summary["plan_fte"],
        assigned_fte=summary["assigned_fte"],
        open_fte=summary["open_fte"],
        assignments=[
            schemas.PlanPhaseAssignedPersonOut(
                person_id=e["person_id"], person_name=e["person_name"], fte=round(e["fte"], 4)
            )
            for e in sorted(by_person.values(), key=lambda e: e["person_name"])
        ],
    )


@router.get(
    "/plan-phases/{plan_phase_id}/assignment-summary", response_model=schemas.PlanPhaseAssignmentSummaryOut
)
def get_plan_phase_assignment_summary(plan_phase_id: int, db: Session = Depends(get_db)):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    return _plan_phase_assignment_summary(db, plan_phase)


def _require_leaf_for_assignment(db: Session, plan_phase: models.PlanPhase) -> None:
    if planning_calc.has_children(db, plan_phase.id):
        raise HTTPException(
            status_code=422,
            detail="Direkte Personenzuordnung ist nur auf einer Leaf-Phase möglich (diese Phase ist eine Sammelphase)",
        )


def _upsert_direct_assignment(
    db: Session, plan_phase: models.PlanPhase, person_id: int, fte: float
) -> models.ResourceAssignment:
    """P20.1 (Abschnitt 3/9/27): erzeugt/aktualisiert eine Personenzuordnung DIREKT an der
    Leaf-PlanPhase - KEIN ResourceDemand mehr als technischer Adapter (löst die frühere
    "Ohne Rolle"-Systemrolle als Trägerschicht ab, Abschnitt 41 "kein Scope Creep":
    ResourceRole/ResourceDemand bleiben als Tabellen/Legacy-Pfad unverändert bestehen, nur der
    NEUE Assignment-Flow braucht sie nicht mehr). Upsert-Semantik: existiert bereits eine
    direkte Zuordnung dieser Person auf dieser Phase, wird nur ihre FTE aktualisiert; existiert
    stattdessen noch eine Legacy-Zuordnung derselben Person über die frühere Carrier-Demand
    ("Ohne Rolle"), wird DIESE aktualisiert statt eine zweite (doppelt zählende) Zeile
    anzulegen - eine echte Rollen-Aufschlüsselung über eine ANDERE (nicht-System-)Rolle bleibt
    davon unberührt. Ändert plan_fte NIE (Kernprinzip, Abschnitt 3/6b.10) - auch bei
    Überbesetzung nicht."""
    now = _now()
    direct = (
        db.query(models.ResourceAssignment)
        .filter(
            models.ResourceAssignment.plan_phase_id == plan_phase.id,
            models.ResourceAssignment.person_id == person_id,
        )
        .first()
    )
    if direct is not None:
        direct.fte = fte
        direct.aktualisiert_am = now
        return direct

    system_role = _find_system_role(db)
    legacy_carrier = None
    if system_role is not None:
        carrier_demand = (
            db.query(models.ResourceDemand)
            .filter(
                models.ResourceDemand.plan_phase_id == plan_phase.id,
                models.ResourceDemand.resource_role_id == system_role.id,
            )
            .first()
        )
        if carrier_demand is not None:
            legacy_carrier = (
                db.query(models.ResourceAssignment)
                .filter(
                    models.ResourceAssignment.resource_demand_id == carrier_demand.id,
                    models.ResourceAssignment.person_id == person_id,
                    models.ResourceAssignment.plan_phase_id.is_(None),
                )
                .first()
            )
    if legacy_carrier is not None:
        legacy_carrier.fte = fte
        legacy_carrier.aktualisiert_am = now
        return legacy_carrier

    assignment = models.ResourceAssignment(
        plan_phase_id=plan_phase.id, person_id=person_id, fte=fte, erstellt_am=now, aktualisiert_am=now
    )
    db.add(assignment)
    return assignment


def _delete_person_assignment(db: Session, plan_phase_id: int, person_id: int) -> bool:
    """P20.1: entfernt die primäre Zuordnung (direkt ODER die frühere "Ohne Rolle"-Carrier-
    Zuordnung) dieser Person von dieser Phase - identisches Verhalten wie vorher, jetzt über
    beide Speicherwege. Rührt eine etwaige ZUSÄTZLICHE Zuordnung über eine echte
    Rollen-Aufschlüsselung (andere, nicht-System-Rolle) NICHT an - die bleibt Legacy über die
    bestehenden /resource-demands/{id}/assignments-Endpunkte verwaltet. True, wenn etwas
    gelöscht wurde."""
    direct = (
        db.query(models.ResourceAssignment)
        .filter(
            models.ResourceAssignment.plan_phase_id == plan_phase_id,
            models.ResourceAssignment.person_id == person_id,
        )
        .first()
    )
    if direct is not None:
        db.delete(direct)
        return True

    system_role = _find_system_role(db)
    if system_role is None:
        return False
    demand = (
        db.query(models.ResourceDemand)
        .filter(
            models.ResourceDemand.plan_phase_id == plan_phase_id,
            models.ResourceDemand.resource_role_id == system_role.id,
        )
        .first()
    )
    if demand is None:
        return False
    deleted = (
        db.query(models.ResourceAssignment)
        .filter(
            models.ResourceAssignment.resource_demand_id == demand.id,
            models.ResourceAssignment.person_id == person_id,
        )
        .delete(synchronize_session=False)
    )
    return deleted > 0


@router.post(
    "/plan-phases/{plan_phase_id}/assign-person", response_model=schemas.PlanPhaseAssignmentSummaryOut
)
def assign_person_to_plan_phase(
    plan_phase_id: int, payload: schemas.PlanPhaseAssignPersonRequest, db: Session = Depends(get_db)
):
    """P18/B-4, P20.1 (Abschnitt 3/6b.4/6b.10/9): direkte Personenzuordnung OHNE erzwungene
    Rollenauswahl UND ohne ResourceDemand als technischen Adapter (P20.1 - vorher: interne
    Systemrolle "Ohne Rolle"). Ändert plan_fte NIE, auch bei Überbesetzung nicht. Upsert:
    erneutes Zuweisen derselben Person aktualisiert nur die FTE."""
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    _require_leaf_for_assignment(db, plan_phase)
    person = db.get(models.Person, payload.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person nicht gefunden")

    previous = (
        db.query(models.ResourceAssignment)
        .filter(
            models.ResourceAssignment.plan_phase_id == plan_phase.id,
            models.ResourceAssignment.person_id == payload.person_id,
        )
        .first()
    )
    old_fte = previous.fte if previous is not None else None
    assignment = _upsert_direct_assignment(db, plan_phase, payload.person_id, payload.fte)
    db.flush()
    if previous is None:
        history.record_created(
            db,
            project_id=plan_phase.project_id,
            entity_type="resource_assignment",
            entity_id=assignment.id,
            entity_label=person.display_name,
            fields={"fte": assignment.fte, "person_id": person.id},
            plan_phase_id=plan_phase.id,
        )
    else:
        history.record_updated(
            db,
            project_id=plan_phase.project_id,
            entity_type="resource_assignment",
            entity_id=assignment.id,
            entity_label=person.display_name,
            old={"fte": old_fte, "person_id": person.id},
            new={"fte": assignment.fte, "person_id": person.id},
            plan_phase_id=plan_phase.id,
        )
    db.commit()
    db.refresh(plan_phase)
    return _plan_phase_assignment_summary(db, plan_phase)


@router.delete(
    "/plan-phases/{plan_phase_id}/assign-person/{person_id}",
    response_model=schemas.PlanPhaseAssignmentSummaryOut,
)
def unassign_person_from_plan_phase(plan_phase_id: int, person_id: int, db: Session = Depends(get_db)):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    existing = (
        db.query(models.ResourceAssignment)
        .filter(
            models.ResourceAssignment.plan_phase_id == plan_phase_id,
            models.ResourceAssignment.person_id == person_id,
        )
        .first()
    )
    person = db.get(models.Person, person_id)
    if existing is not None:
        history.record_deleted(
            db,
            project_id=plan_phase.project_id,
            entity_type="resource_assignment",
            entity_id=existing.id,
            entity_label=person.display_name if person else f"Person #{person_id}",
            fields=history.snapshot(existing, "resource_assignment"),
            plan_phase_id=plan_phase.id,
        )
    if _delete_person_assignment(db, plan_phase_id, person_id):
        if existing is None:
            history.record_deleted(
                db,
                project_id=plan_phase.project_id,
                entity_type="resource_assignment",
                entity_id=person_id,
                entity_label=person.display_name if person else f"Person #{person_id}",
                fields={"fte": None, "person_id": person_id},
                plan_phase_id=plan_phase.id,
            )
        db.commit()
    return _plan_phase_assignment_summary(db, plan_phase)


# ---------------------------------------------------------------------------
# Phasenscoped Assignment-API (Auftrag Abschnitt 27, API-Zielbild) - CRUD ausschließlich für
# den neuen direkten Pfad (ResourceAssignment.plan_phase_id). Legacy-Zuordnungen über eine
# ResourceDemand bleiben über die bestehenden /resource-demands/{id}/assignments-Endpunkte
# erreichbar (nicht Teil dieser neuen, absichtlich schlanken Ressource) - für die
# Bedarf/Besetzt/Offen-Gesamtsicht bleibt assignment-summary/PlanPhaseDetail die
# Zusammenführung beider Wege (_plan_phase_assignment_rows).
# ---------------------------------------------------------------------------


@router.get(
    "/{project_id}/plan-phases/{plan_phase_id}/assignments", response_model=list[schemas.ResourceAssignmentOut]
)
def list_plan_phase_direct_assignments(project_id: int, plan_phase_id: int, db: Session = Depends(get_db)):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    if plan_phase.project_id != project_id:
        raise HTTPException(status_code=404, detail="Planphase gehört nicht zu diesem Projekt")
    rows = (
        db.query(models.ResourceAssignment, models.Person.display_name)
        .join(models.Person, models.Person.id == models.ResourceAssignment.person_id)
        .filter(models.ResourceAssignment.plan_phase_id == plan_phase_id)
        .order_by(models.Person.display_name)
        .all()
    )
    return [
        schemas.ResourceAssignmentOut(
            id=a.id,
            resource_demand_id=a.resource_demand_id,
            plan_phase_id=a.plan_phase_id,
            person_id=a.person_id,
            person_name=name,
            fte=a.fte,
            erstellt_am=a.erstellt_am,
            aktualisiert_am=a.aktualisiert_am,
        )
        for a, name in rows
    ]


@router.post(
    "/{project_id}/plan-phases/{plan_phase_id}/assignments",
    response_model=schemas.ResourceAssignmentOut,
    status_code=201,
)
def create_plan_phase_direct_assignment(
    project_id: int,
    plan_phase_id: int,
    payload: schemas.PlanPhaseResourceAssignmentCreate,
    db: Session = Depends(get_db),
):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    if plan_phase.project_id != project_id:
        raise HTTPException(status_code=404, detail="Planphase gehört nicht zu diesem Projekt")
    _require_leaf_for_assignment(db, plan_phase)
    person = db.get(models.Person, payload.person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person nicht gefunden")

    previous = (
        db.query(models.ResourceAssignment)
        .filter(
            models.ResourceAssignment.plan_phase_id == plan_phase.id,
            models.ResourceAssignment.person_id == payload.person_id,
        )
        .first()
    )
    old_fte = previous.fte if previous is not None else None
    assignment = _upsert_direct_assignment(db, plan_phase, payload.person_id, payload.fte)
    db.flush()
    if previous is None:
        history.record_created(
            db,
            project_id=plan_phase.project_id,
            entity_type="resource_assignment",
            entity_id=assignment.id,
            entity_label=person.display_name,
            fields={"fte": assignment.fte, "person_id": person.id},
            plan_phase_id=plan_phase.id,
        )
    else:
        history.record_updated(
            db,
            project_id=plan_phase.project_id,
            entity_type="resource_assignment",
            entity_id=assignment.id,
            entity_label=person.display_name,
            old={"fte": old_fte, "person_id": person.id},
            new={"fte": assignment.fte, "person_id": person.id},
            plan_phase_id=plan_phase.id,
        )
    db.commit()
    db.refresh(assignment)
    return schemas.ResourceAssignmentOut(
        id=assignment.id,
        resource_demand_id=assignment.resource_demand_id,
        plan_phase_id=assignment.plan_phase_id,
        person_id=assignment.person_id,
        person_name=person.display_name,
        fte=assignment.fte,
        erstellt_am=assignment.erstellt_am,
        aktualisiert_am=assignment.aktualisiert_am,
    )


def _get_direct_assignment_or_404(db: Session, plan_phase_id: int, assignment_id: int) -> models.ResourceAssignment:
    assignment = (
        db.query(models.ResourceAssignment)
        .filter(models.ResourceAssignment.id == assignment_id, models.ResourceAssignment.plan_phase_id == plan_phase_id)
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Ressourcenzuordnung nicht gefunden")
    return assignment


@router.patch(
    "/{project_id}/plan-phases/{plan_phase_id}/assignments/{assignment_id}",
    response_model=schemas.ResourceAssignmentOut,
)
def update_plan_phase_direct_assignment(
    project_id: int,
    plan_phase_id: int,
    assignment_id: int,
    payload: schemas.PlanPhaseResourceAssignmentUpdate,
    db: Session = Depends(get_db),
):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    if plan_phase.project_id != project_id:
        raise HTTPException(status_code=404, detail="Planphase gehört nicht zu diesem Projekt")
    assignment = _get_direct_assignment_or_404(db, plan_phase_id, assignment_id)
    old = history.snapshot(assignment, "resource_assignment")
    assignment.fte = payload.fte
    assignment.aktualisiert_am = _now()
    person = db.get(models.Person, assignment.person_id)
    history.record_updated(
        db,
        project_id=plan_phase.project_id,
        entity_type="resource_assignment",
        entity_id=assignment.id,
        entity_label=person.display_name if person else f"Person #{assignment.person_id}",
        old=old,
        new=history.snapshot(assignment, "resource_assignment"),
        plan_phase_id=plan_phase.id,
    )
    db.commit()
    db.refresh(assignment)
    person = db.get(models.Person, assignment.person_id)
    return schemas.ResourceAssignmentOut(
        id=assignment.id,
        resource_demand_id=assignment.resource_demand_id,
        plan_phase_id=assignment.plan_phase_id,
        person_id=assignment.person_id,
        person_name=person.display_name if person else "",
        fte=assignment.fte,
        erstellt_am=assignment.erstellt_am,
        aktualisiert_am=assignment.aktualisiert_am,
    )


@router.delete("/{project_id}/plan-phases/{plan_phase_id}/assignments/{assignment_id}", status_code=204)
def delete_plan_phase_direct_assignment(
    project_id: int, plan_phase_id: int, assignment_id: int, db: Session = Depends(get_db)
):
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    if plan_phase.project_id != project_id:
        raise HTTPException(status_code=404, detail="Planphase gehört nicht zu diesem Projekt")
    assignment = _get_direct_assignment_or_404(db, plan_phase_id, assignment_id)
    person = db.get(models.Person, assignment.person_id)
    history.record_deleted(
        db,
        project_id=plan_phase.project_id,
        entity_type="resource_assignment",
        entity_id=assignment.id,
        entity_label=person.display_name if person else f"Person #{assignment.person_id}",
        fields=history.snapshot(assignment, "resource_assignment"),
        plan_phase_id=plan_phase.id,
    )
    db.delete(assignment)
    db.commit()


@router.get(
    "/plan-phases/{plan_phase_id}/assignment-candidates", response_model=list[schemas.CandidatePersonOut]
)
def list_plan_phase_assignment_candidates(plan_phase_id: int, db: Session = Depends(get_db)):
    """Wie GET /resource-demands/{id}/candidates, aber Available Capacity über den GESAMTEN
    Phasenzeitraum geprüft (compute_person_capacity_for_range, Abschnitt 6b.5/6b.11) statt
    nur einen einzelnen Monats-Bucket - für die direkte Personenzuordnung ohne Rollen-Zwang.
    Schließt Personen aus, die bereits über irgendeine ResourceDemand dieser Phase zugeordnet
    sind (Rollen-Aufschlüsselung UND direkte Zuordnung zählen gleichermaßen)."""
    plan_phase = _get_plan_phase_or_404(db, plan_phase_id)
    if not plan_phase.forecast_start or not plan_phase.forecast_end:
        raise HTTPException(
            status_code=422, detail="Phase hat noch keinen Zeitraum (forecast_start/forecast_end fehlt)"
        )
    range_start = date.fromisoformat(plan_phase.forecast_start)
    range_end = date.fromisoformat(plan_phase.forecast_end)

    # P20.1: BEIDE Ressourcenwege ausschließen (direkte plan_phase_id-Zuordnung + Legacy über
    # eine ResourceDemand dieser Phase) - Rollen-Aufschlüsselung UND direkte Zuordnung zählen
    # weiterhin gleichermaßen.
    already_assigned = {
        row[0] for row in db.query(models.ResourceAssignment.person_id).filter(
            models.ResourceAssignment.plan_phase_id == plan_phase_id
        ).all()
    } | {
        row[0]
        for row in db.query(models.ResourceAssignment.person_id)
        .join(models.ResourceDemand, models.ResourceDemand.id == models.ResourceAssignment.resource_demand_id)
        .filter(models.ResourceDemand.plan_phase_id == plan_phase_id)
        .all()
    }

    persons = (
        db.query(models.Person)
        .join(models.ResourceProfile, models.ResourceProfile.person_id == models.Person.id)
        .filter(models.Person.active.is_(True), models.ResourceProfile.capacity_relevant.is_(True))
        .all()
    )

    candidates: list[schemas.CandidatePersonOut] = []
    for person in persons:
        if person.id in already_assigned:
            continue
        capacity = capacity_calc.compute_person_capacity_for_range(db, person.id, range_start, range_end)
        if capacity is None or capacity.available_fte <= 0:
            continue
        skill_rows = (
            db.query(models.Skill.name)
            .join(models.PersonSkill, models.PersonSkill.skill_id == models.Skill.id)
            .filter(models.PersonSkill.person_id == person.id)
            .order_by(models.Skill.name)
            .all()
        )
        candidates.append(
            schemas.CandidatePersonOut(
                person_id=person.id,
                display_name=person.display_name,
                available_fte=capacity.available_fte,
                skills=[name for (name,) in skill_rows],
            )
        )

    candidates.sort(key=lambda c: c.available_fte, reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------


def _milestone_out(db: Session, m: models.Milestone) -> schemas.MilestoneOut:
    return schemas.MilestoneOut(
        id=m.id,
        project_id=m.project_id,
        subproject_id=m.subproject_id,
        plan_phase_id=m.plan_phase_id,
        name=m.name,
        baseline_date=m.baseline_date,
        forecast_date=m.forecast_date,
        actual_date=m.actual_date,
        status=m.status,
        owner_person_id=m.owner_person_id,
        owner_team_id=m.owner_team_id,
        erstellt_am=m.erstellt_am,
        aktualisiert_am=m.aktualisiert_am,
        tags=entity_links.tags_for(db, "milestone", m.id),
        documents=entity_links.documents_for(db, "milestone", m.id),
    )


def _get_milestone_or_404(db: Session, milestone_id: int) -> models.Milestone:
    m = db.get(models.Milestone, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone nicht gefunden")
    return m


@router.get("/{project_id}/milestones", response_model=list[schemas.MilestoneOut])
def list_milestones(project_id: int, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    rows = (
        db.query(models.Milestone)
        .filter(models.Milestone.project_id == project_id)
        .order_by(models.Milestone.baseline_date, models.Milestone.id)
        .all()
    )
    return [_milestone_out(db, m) for m in rows]


@router.post("/{project_id}/milestones", response_model=schemas.MilestoneOut, status_code=201)
def create_milestone(project_id: int, payload: schemas.MilestoneCreate, db: Session = Depends(get_db)):
    _get_project_or_404(db, project_id)
    _check_subproject(db, project_id, payload.subproject_id)
    _check_milestone_plan_phase(db, project_id, payload.plan_phase_id)
    _check_owner(db, payload.owner_person_id, payload.owner_team_id)
    now = _now()
    milestone = models.Milestone(
        project_id=project_id,
        subproject_id=payload.subproject_id,
        plan_phase_id=payload.plan_phase_id,
        name=payload.name,
        baseline_date=payload.baseline_date,
        forecast_date=payload.forecast_date,
        actual_date=payload.actual_date,
        status=payload.status,
        owner_person_id=payload.owner_person_id,
        owner_team_id=payload.owner_team_id,
        erstellt_am=now,
        aktualisiert_am=now,
    )
    db.add(milestone)
    db.flush()
    created_batch = history.record_created(
        db,
        project_id=project_id,
        entity_type="milestone",
        entity_id=milestone.id,
        entity_label=milestone.name,
        fields=history.snapshot(milestone, "milestone"),
        plan_phase_id=milestone.plan_phase_id,
    )
    if payload.tags:
        entity_links.sync_tags(db, "milestone", milestone.id, payload.tags)
        history.record_tag_diff(
            db,
            project_id=project_id,
            entity_type="milestone",
            entity_id=milestone.id,
            entity_label=milestone.name,
            old_tags=[],
            new_tags=payload.tags,
            plan_phase_id=milestone.plan_phase_id,
            batch_id=created_batch,
        )
    db.commit()
    db.refresh(milestone)
    return _milestone_out(db, milestone)


@router.put("/milestones/{milestone_id}", response_model=schemas.MilestoneOut)
def update_milestone(milestone_id: int, payload: schemas.MilestoneUpdate, db: Session = Depends(get_db)):
    milestone = _get_milestone_or_404(db, milestone_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"tags"})
    if "subproject_id" in changes:
        _check_subproject(db, milestone.project_id, changes["subproject_id"])
    if "plan_phase_id" in changes:
        _check_milestone_plan_phase(db, milestone.project_id, changes["plan_phase_id"])
    _check_owner(db, changes.get("owner_person_id"), changes.get("owner_team_id"))
    old = history.snapshot(milestone, "milestone")
    old_tags = entity_links.tags_for(db, "milestone", milestone.id)
    batch_id = history.new_batch_id()
    if changes:
        for field, value in changes.items():
            setattr(milestone, field, value)
        milestone.aktualisiert_am = _now()
    history.record_updated(
        db,
        project_id=milestone.project_id,
        entity_type="milestone",
        entity_id=milestone.id,
        entity_label=milestone.name,
        old=old,
        new=history.snapshot(milestone, "milestone"),
        plan_phase_id=milestone.plan_phase_id,
        batch_id=batch_id,
    )
    if payload.tags is not None:
        entity_links.sync_tags(db, "milestone", milestone.id, payload.tags)
        history.record_tag_diff(
            db,
            project_id=milestone.project_id,
            entity_type="milestone",
            entity_id=milestone.id,
            entity_label=milestone.name,
            old_tags=old_tags,
            new_tags=payload.tags,
            plan_phase_id=milestone.plan_phase_id,
            batch_id=batch_id,
        )
    db.commit()
    db.refresh(milestone)
    return _milestone_out(db, milestone)


@router.delete("/milestones/{milestone_id}", status_code=204)
def delete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    milestone = _get_milestone_or_404(db, milestone_id)
    history.record_deleted(
        db,
        project_id=milestone.project_id,
        entity_type="milestone",
        entity_id=milestone.id,
        entity_label=milestone.name,
        fields=history.snapshot(milestone, "milestone"),
        plan_phase_id=milestone.plan_phase_id,
    )
    entity_links.delete_links_for_entity(db, "milestone", milestone_id)
    entity_links.delete_relations_for_entity(db, "milestone", milestone_id)
    db.delete(milestone)
    db.commit()
