"""Phase-Ist-Stunden aus dem Worklog-Resolver (P20.4, siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 15/16). DB-facing Aggregationsschicht
zwischen dem reinen Resolver (`worklog_resolver.py`) und den reinen Rohmetrik-Formeln
(`phase_metrics_calc.py`) - folgt demselben Shared-Module-Muster wie `gap_calc.py`/
`capacity_calc.py` (Router und Calc-Module importieren nur von gemeinsamen Modulen, nicht
voneinander). `actuals_coverage.py` (P20.3) nutzt `hours_by_issue()` ebenfalls, statt die
Worklog-Cache-Abfrage ein zweites Mal zu duplizieren."""

from sqlalchemy.orm import Session

from . import models, planning_calc, worklog_resolver
from .worklog_resolver import ResolutionStatus


def hours_by_issue(db: Session, project_id: int) -> dict[str, float]:
    """Stunden je Issue-Key aus dem unveränderten Worklog-Cache (dieselbe Quelle wie
    `jira_sync.berechne_ist_fte`) - Projekt-Ist bleibt dadurch für P20 unangetastet
    (Abschnitt 20 des P20-Dokuments)."""
    rows = (
        db.query(models.JiraWorklogCache.jira_issue_key, models.JiraWorklogCache.stunden)
        .filter(models.JiraWorklogCache.projekt_mapping == str(project_id))
        .all()
    )
    hours: dict[str, float] = {}
    for issue_key, stunden in rows:
        hours[issue_key] = hours.get(issue_key, 0.0) + stunden
    return hours


def hours_by_matched_phase(db: Session, project_id: int) -> dict[int, float]:
    """Stunden je Leaf-PlanPhase, ausschließlich für eindeutig (MATCHED) aufgelöste Issues -
    UNMAPPED/AMBIGUOUS tragen nichts bei (keine Doppelzählung, Auftrag Abschnitt 12/13)."""
    issue_hours = hours_by_issue(db, project_id)
    resolution = worklog_resolver.resolve_project_issues(db, project_id)
    result: dict[int, float] = {}
    for issue_key, hours in issue_hours.items():
        r = resolution.get(issue_key)
        if r is not None and r.status is ResolutionStatus.MATCHED:
            result[r.plan_phase_id] = result.get(r.plan_phase_id, 0.0) + hours
    return {phase_id: round(total, 2) for phase_id, total in result.items()}


def leaf_ist_hours(db: Session, plan_phase: models.PlanPhase) -> float | None:
    """Ist-Stunden einer Leaf-Phase. `None`, wenn kein `jira_label` konfiguriert ist ("Ist-
    Aufwand noch nicht zugeordnet", Auftrag Abschnitt 18) - unterscheidet sich fachlich von
    `0.0` ("Label konfiguriert, bislang aber kein Worklog getroffen", eine echte Messung).
    Ein Aufruf pro Phasen-Detailansicht ist die etablierte Nutzung (siehe
    `routers/planning.py::_plan_phase_metrics`), daher hier bewusst kein projektweiter Cache
    über mehrere Aufrufe hinweg - analog zu den übrigen Rohmetrik-Berechnungen in diesem
    Router, die ebenfalls je Request neu berechnet werden."""
    if plan_phase.jira_label is None:
        return None
    matched = hours_by_matched_phase(db, plan_phase.project_id)
    return matched.get(plan_phase.id, 0.0)


def parent_ist_hours(db: Session, plan_phase_id: int) -> float | None:
    """Ist-Stunden einer Parent-Phase = SUM(Ist-Stunden aller Leaf-Nachfahren), analog zu
    `planning_calc.derive_parent_capacity` (Abschnitt 15 des P20-Dokuments): `None`, wenn
    KEIN Leaf-Nachfahre einen Wert hat (kein Nachfahre gemappt) - nicht `0.0`, damit "keine
    Aussage möglich" von "Ist ist 0h" unterscheidbar bleibt. Keine Worklogs werden auf
    Parent und Leaf doppelt gespeichert oder gezählt - der Resolver kennt ausschließlich
    Leaf-Phasen (nur sie tragen `jira_label`), hier wird nur aggregiert."""
    leaves = planning_calc.leaf_descendants(db, plan_phase_id)
    if not leaves:
        return None
    # Alle Leaf-Nachfahren gehören zwingend zum selben Projekt wie die Parent-Phase - ein
    # einziger projektweiter Aggregationsaufruf statt N Einzelaufrufen (kein N+1).
    matched = hours_by_matched_phase(db, leaves[0].project_id)
    values = [matched.get(leaf.id, 0.0) for leaf in leaves if leaf.jira_label is not None]
    return round(sum(values), 2) if values else None


def person_hours_by_matched_phase(db: Session, project_id: int) -> dict[int, dict[str, float]]:
    """Wie `hours_by_matched_phase()`, zusätzlich nach `jira_account_id` aufgeschlüsselt
    (P20.6, siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 17/24) - Grundlage
    für den Personen-Drilldown je Phase. Nur MATCHED-Issues tragen bei, keine Ausnahme von
    der bestehenden Doppelzählungs-Regel (Abschnitt 12/13)."""
    resolution = worklog_resolver.resolve_project_issues(db, project_id)
    rows = (
        db.query(
            models.JiraWorklogCache.jira_issue_key,
            models.JiraWorklogCache.jira_account_id,
            models.JiraWorklogCache.stunden,
        )
        .filter(models.JiraWorklogCache.projekt_mapping == str(project_id))
        .all()
    )
    result: dict[int, dict[str, float]] = {}
    for issue_key, account_id, stunden in rows:
        r = resolution.get(issue_key)
        if r is None or r.status is not ResolutionStatus.MATCHED:
            continue
        by_person = result.setdefault(r.plan_phase_id, {})
        by_person[account_id] = by_person.get(account_id, 0.0) + stunden
    return {
        phase_id: {account_id: round(hours, 2) for account_id, hours in by_person.items()}
        for phase_id, by_person in result.items()
    }


def person_hours_for_phase(db: Session, plan_phase: models.PlanPhase) -> dict[str, float]:
    """Person-Ist-Stunden (account_id -> Stunden) für eine Leaf- ODER Parent-Phase (P20.6) -
    bei Parent rekursiv über alle Leaf-Nachfahren summiert. `leaf_descendants()` liefert eine
    Leaf-Phase als ihren eigenen einzigen Nachfahren (siehe planning_calc.py), daher deckt
    diese eine Funktion beide Fälle ohne gesonderte Fallunterscheidung ab - Personen-Auflösung
    (jira_account_id -> Person/UnassignedJiraAuthor) erfolgt beim Aufrufer
    (routers/planning.py), hier werden nur Rohstunden aggregiert."""
    leaves = planning_calc.leaf_descendants(db, plan_phase.id)
    if not leaves:
        return {}
    by_phase = person_hours_by_matched_phase(db, leaves[0].project_id)
    result: dict[str, float] = {}
    for leaf in leaves:
        for account_id, hours in by_phase.get(leaf.id, {}).items():
            result[account_id] = result.get(account_id, 0.0) + hours
    return {k: round(v, 2) for k, v in result.items()}
