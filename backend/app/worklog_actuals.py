"""Phase-Ist-Stunden aus dem Worklog-Resolver (P20.4, siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 15/16). DB-facing Aggregationsschicht
zwischen dem reinen Resolver (`worklog_resolver.py`) und den reinen Rohmetrik-Formeln
(`phase_metrics_calc.py`) - folgt demselben Shared-Module-Muster wie `gap_calc.py`/
`capacity_calc.py` (Router und Calc-Module importieren nur von gemeinsamen Modulen, nicht
voneinander). `actuals_coverage.py` (P20.3) nutzt `hours_by_issue()` ebenfalls, statt die
Worklog-Cache-Abfrage ein zweites Mal zu duplizieren.

P20.5 (Capacity Scope, siehe P20_5_PHASE_ACTUALS_AND_TIME_CONTROL.md Abschnitt 3/4/12):
ergänzt eine zweite, enger gefasste Sicht auf dieselben MATCHED-Worklog-Zeilen -
"Capacity Actual" zählt nur Worklogs kapazitätsplanbarer lokaler Personen (Person.active +
ResourceProfile.capacity_relevant, derselbe Filter wie capacity_calc.py/routers/planning.py
list_plan_phase_assignment_candidates), im Unterschied zu den Funktionen oben, die JEDEN
MATCHED-Worklog zählen ("Project/Jira Total Actual" bzw. das bisherige, ungefilterte
Phase-Ist). Section 12 des Auftrags verlangt ausdrücklich, dass die bisherigen,
ungefilterten Funktionen (hours_by_issue/hours_by_matched_phase/leaf_ist_hours/
parent_ist_hours/person_hours_by_matched_phase/person_hours_for_phase) UNVERÄNDERT bestehen
bleiben - sie bleiben die Quelle für Projekt-/Jira-Controlling (jira_sync.berechne_ist_fte,
actuals_coverage.py). Die neuen `capacity_*`-Funktionen unten sind die Quelle für
Plan-vs-Ist einer PlanPhase (routers/planning.py._plan_phase_metrics)."""

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


def capacity_planbare_accounts(db: Session) -> dict[str, int]:
    """jira_account_id -> Person.id für kapazitätsplanbare lokale Personen (P20.5, Abschnitt
    3): Person.active UND ResourceProfile.capacity_relevant - derselbe etablierte Filter wie
    capacity_calc.compute_available_capacity/routers/planning.py.
    list_plan_phase_assignment_candidates/routers/capacity.py (bewusst wiederverwendet statt
    neu erfunden). NICHT auf Personen mit ResourceAssignment beschränkt (Abschnitt 4 - eine
    kapazitätsplanbare Person ohne Assignment zählt trotzdem, Assignment entscheidet nur
    planned/unplanned, nie ob die Stunden überhaupt zählen)."""
    rows = (
        db.query(models.Person)
        .join(models.ResourceProfile, models.ResourceProfile.person_id == models.Person.id)
        .filter(
            models.Person.active.is_(True),
            models.ResourceProfile.capacity_relevant.is_(True),
            models.Person.jira_account_id.isnot(None),
        )
        .all()
    )
    return {p.jira_account_id: p.id for p in rows}


def _matched_worklog_rows(db: Session, project_id: int) -> dict[int, list[tuple[str, str, float]]]:
    """Rohzeilen (jira_account_id, datum, stunden) je Leaf-PlanPhase für MATCHED Issues -
    gemeinsame Grundlage für Capacity-Ist, Personen-Drilldown, Zeitraum-Klassifikation und
    actual_start/last_activity_date (Abschnitt 6/7/10/17/22/39), ein einziger Cache-/
    Resolver-Durchlauf statt mehrfacher Einzelabfragen."""
    resolution = worklog_resolver.resolve_project_issues(db, project_id)
    rows = (
        db.query(
            models.JiraWorklogCache.jira_issue_key,
            models.JiraWorklogCache.jira_account_id,
            models.JiraWorklogCache.datum,
            models.JiraWorklogCache.stunden,
        )
        .filter(models.JiraWorklogCache.projekt_mapping == str(project_id))
        .all()
    )
    result: dict[int, list[tuple[str, str, float]]] = {}
    for issue_key, account_id, datum, stunden in rows:
        r = resolution.get(issue_key)
        if r is None or r.status is not ResolutionStatus.MATCHED:
            continue
        result.setdefault(r.plan_phase_id, []).append((account_id, datum, stunden))
    return result


def capacity_rows_by_matched_phase(db: Session, project_id: int) -> dict[int, list[tuple[str, str, float]]]:
    """Wie `_matched_worklog_rows()`, aber nur Zeilen kapazitätsplanbarer Personen (P20.5,
    Abschnitt 3/7) - "Capacity Actual". Rohzeilen statt Summe, damit Aufrufer sowohl die
    Gesamtsumme (capacity_hours_by_matched_phase) als auch Datumsaufschlüsselungen (before/
    within/after, first/last date) ohne weiteren DB-Zugriff daraus ableiten können."""
    scope = capacity_planbare_accounts(db)
    rows_by_phase = _matched_worklog_rows(db, project_id)
    return {
        phase_id: [(a, d, h) for a, d, h in rows if a in scope] for phase_id, rows in rows_by_phase.items()
    }


def outside_scope_rows_by_matched_phase(db: Session, project_id: int) -> dict[int, list[tuple[str, str, float]]]:
    """Gegenstück zu `capacity_rows_by_matched_phase()`: MATCHED-Worklogs von Autoren OHNE
    kapazitätsplanbare lokale Person (P20.5, Abschnitt 9 - "außerhalb Kapazitätsscope",
    Transparenz-Zahl, NICHT Bestandteil von Plan-vs-Ist)."""
    scope = capacity_planbare_accounts(db)
    rows_by_phase = _matched_worklog_rows(db, project_id)
    return {
        phase_id: [(a, d, h) for a, d, h in rows if a not in scope]
        for phase_id, rows in rows_by_phase.items()
    }


def capacity_hours_by_matched_phase(db: Session, project_id: int) -> dict[int, float]:
    """Capacity-Ist-Stunden je Leaf-PlanPhase (P20.5, Abschnitt 7) - Summe der
    `capacity_rows_by_matched_phase()`-Zeilen. Keine Zeitraum-Kappung (Abschnitt 7/34):
    Worklogs vor/nach dem Planzeitraum zählen unverändert mit."""
    rows_by_phase = capacity_rows_by_matched_phase(db, project_id)
    return {phase_id: round(sum(h for _, _, h in rows), 2) for phase_id, rows in rows_by_phase.items()}


def leaf_capacity_ist_hours(db: Session, plan_phase: models.PlanPhase) -> float | None:
    """Capacity-Ist-Stunden einer Leaf-Phase (P20.5, Abschnitt 7) - ersetzt `leaf_ist_hours()`
    als Quelle für Plan-vs-Ist (Abschnitt 12: `leaf_ist_hours()` selbst bleibt unverändert für
    Project/Jira Total Actual bestehen). Gleiche None-vs-0.0-Konvention wie `leaf_ist_hours()`."""
    if plan_phase.jira_label is None:
        return None
    matched = capacity_hours_by_matched_phase(db, plan_phase.project_id)
    return matched.get(plan_phase.id, 0.0)


def parent_capacity_ist_hours(db: Session, plan_phase_id: int) -> float | None:
    """Capacity-Ist-Stunden einer Parent-Phase = SUM(Capacity-Ist-Stunden aller Leaf-
    Nachfahren) (P20.5, Abschnitt 35), analog zu `parent_ist_hours()`."""
    leaves = planning_calc.leaf_descendants(db, plan_phase_id)
    if not leaves:
        return None
    matched = capacity_hours_by_matched_phase(db, leaves[0].project_id)
    values = [matched.get(leaf.id, 0.0) for leaf in leaves if leaf.jira_label is not None]
    return round(sum(values), 2) if values else None


def leaf_outside_scope_summary(db: Session, plan_phase: models.PlanPhase) -> dict | None:
    """Transparenz-Zahl "außerhalb Kapazitätsscope" einer Leaf-Phase (P20.5, Abschnitt 9):
    Stunden + Anzahl unterschiedlicher Autoren, deren MATCHED-Worklogs auf dieser Phase NICHT
    von einer kapazitätsplanbaren lokalen Person stammen. None ohne jira_label (analog
    `leaf_ist_hours()`); `{"hours": 0.0, "author_count": 0}` ist eine echte Messung ("alle
    MATCHED-Worklogs stammen von kapazitätsplanbaren Personen"), keine fehlende Zuordnung."""
    if plan_phase.jira_label is None:
        return None
    rows = outside_scope_rows_by_matched_phase(db, plan_phase.project_id).get(plan_phase.id, [])
    return {"hours": round(sum(h for _, _, h in rows), 2), "author_count": len({a for a, _, _ in rows})}


def parent_outside_scope_summary(db: Session, plan_phase_id: int) -> dict | None:
    """Wie `leaf_outside_scope_summary()`, aggregiert über alle Leaf-Nachfahren (P20.5,
    Abschnitt 35) - author_count zählt eindeutige Autoren über alle Leafs hinweg (kein
    Doppelzählen derselben Person in zwei Unterphasen)."""
    leaves = planning_calc.leaf_descendants(db, plan_phase_id)
    labeled = [leaf for leaf in leaves if leaf.jira_label is not None]
    if not labeled:
        return None
    by_phase = outside_scope_rows_by_matched_phase(db, labeled[0].project_id)
    all_rows = [row for leaf in labeled for row in by_phase.get(leaf.id, [])]
    return {
        "hours": round(sum(h for _, _, h in all_rows), 2),
        "author_count": len({a for a, _, _ in all_rows}),
    }


def leaf_first_capacity_worklog_date(db: Session, plan_phase: models.PlanPhase) -> str | None:
    """Frühestes Datum eines Capacity-Worklogs dieser Leaf-Phase (P20.5, Abschnitt 17) -
    Grundlage für die automatische actual_start-Ableitung (jira_sync.py). Selbstkorrigierend:
    ein späterer Sync liefert automatisch ein früheres Datum, sobald ein rückdatierter
    Worklog im Cache erscheint (Abschnitt 18) - der Aufrufer übernimmt den Wert nur, wenn er
    früher als der bisherige actual_start ist (nie später)."""
    if plan_phase.jira_label is None:
        return None
    rows = capacity_rows_by_matched_phase(db, plan_phase.project_id).get(plan_phase.id, [])
    dates = [d for _, d, _ in rows]
    return min(dates) if dates else None


def leaf_last_activity_date(db: Session, plan_phase: models.PlanPhase) -> str | None:
    """Datum des letzten Capacity-Worklogs dieser Leaf-Phase (P20.5, Abschnitt 19/22) - NICHT
    actual_end (das bleibt der fachliche Abschlusszeitpunkt, siehe models.PlanPhase-Docstring).
    Bewusst live abgeleitet statt persistiert (immer billig aus demselben Cache-Durchlauf wie
    ist_hours ableitbar, siehe Auftrag Abschnitt 42)."""
    if plan_phase.jira_label is None:
        return None
    rows = capacity_rows_by_matched_phase(db, plan_phase.project_id).get(plan_phase.id, [])
    dates = [d for _, d, _ in rows]
    return max(dates) if dates else None


def parent_last_activity_date(db: Session, plan_phase_id: int) -> str | None:
    """Letzte Aktivität einer Parent-Phase = max(last_activity_date aller Leaf-Nachfahren)
    (P20.5, Abschnitt 35)."""
    leaves = planning_calc.leaf_descendants(db, plan_phase_id)
    dates = [leaf_last_activity_date(db, leaf) for leaf in leaves]
    dates = [d for d in dates if d is not None]
    return max(dates) if dates else None


def classify_leaf_capacity_hours(
    db: Session, plan_phase: models.PlanPhase, start: str | None, end: str | None
) -> dict[str, float] | None:
    """Vor/Im/Nach-Aufschlüsselung derselben Capacity-Ist-Worklogs einer Leaf-Phase gegen
    einen Referenzzeitraum (P20.5, Abschnitt 6/8/39) - der Aufrufer übergibt bevorzugt
    commitment_start/commitment_end (Abschnitt 40: der Referenzzeitraum darf sich durch eine
    spätere Planverschiebung nicht rückwirkend verändern), ersatzweise forecast_start/
    forecast_end, solange noch kein Commitment existiert. Verändert NIEMALS die Ist-Summe
    selbst (Abschnitt 6) - reine Aufschlüsselung derselben Zeilen wie
    `capacity_hours_by_matched_phase()`. None ohne jira_label. Ohne start/end (weder
    Commitment noch aktueller Plan vorhanden) zählt alles als "within" (keine Referenz zum
    Vergleichen)."""
    if plan_phase.jira_label is None:
        return None
    rows = capacity_rows_by_matched_phase(db, plan_phase.project_id).get(plan_phase.id, [])
    before = within = after = 0.0
    for _, datum, stunden in rows:
        if start is not None and datum < start:
            before += stunden
        elif end is not None and datum > end:
            after += stunden
        else:
            within += stunden
    return {"before": round(before, 2), "within": round(within, 2), "after": round(after, 2)}


def parent_classify_capacity_hours(db: Session, plan_phase_id: int) -> dict[str, float] | None:
    """Wie `classify_leaf_capacity_hours()`, aggregiert über alle Leaf-Nachfahren (P20.5,
    Abschnitt 35) - jeder Leaf wird gegen sein EIGENES Commitment-Fenster klassifiziert (jede
    Unterphase hat ihre eigene Referenz), die drei Summen werden anschließend addiert."""
    leaves = planning_calc.leaf_descendants(db, plan_phase_id)
    labeled = [leaf for leaf in leaves if leaf.jira_label is not None]
    if not labeled:
        return None
    total = {"before": 0.0, "within": 0.0, "after": 0.0}
    for leaf in labeled:
        start = leaf.commitment_start or leaf.forecast_start
        end = leaf.commitment_end or leaf.forecast_end
        c = classify_leaf_capacity_hours(db, leaf, start, end)
        if c is not None:
            for key in total:
                total[key] += c[key]
    return {key: round(value, 2) for key, value in total.items()}


def person_capacity_hours_by_matched_phase(db: Session, project_id: int) -> dict[int, dict[str, float]]:
    """Wie `person_hours_by_matched_phase()`, aber nur kapazitätsplanbare Autoren (P20.5,
    Abschnitt 10) - Grundlage für den primären Personen-Drilldown (nicht kapazitätsplanbare
    Jira-/Tempo-Autoren stehen weiterhin über `outside_scope_rows_by_matched_phase()` zur
    Verfügung, sekundär/transparent, siehe Abschnitt 9)."""
    rows_by_phase = capacity_rows_by_matched_phase(db, project_id)
    result: dict[int, dict[str, float]] = {}
    for phase_id, rows in rows_by_phase.items():
        by_person: dict[str, float] = {}
        for account_id, _, stunden in rows:
            by_person[account_id] = by_person.get(account_id, 0.0) + stunden
        if by_person:
            result[phase_id] = {account_id: round(h, 2) for account_id, h in by_person.items()}
    return result


def person_capacity_hours_for_phase(db: Session, plan_phase: models.PlanPhase) -> dict[str, float]:
    """Wie `person_hours_for_phase()`, aber nur kapazitätsplanbare Autoren (P20.5, Abschnitt
    10) - Leaf- ODER Parent-Phase, analog zum Vorbild."""
    leaves = planning_calc.leaf_descendants(db, plan_phase.id)
    if not leaves:
        return {}
    by_phase = person_capacity_hours_by_matched_phase(db, leaves[0].project_id)
    result: dict[str, float] = {}
    for leaf in leaves:
        for account_id, hours in by_phase.get(leaf.id, {}).items():
            result[account_id] = result.get(account_id, 0.0) + hours
    return {k: round(v, 2) for k, v in result.items()}


def maybe_capture_commitment(plan_phase: models.PlanPhase, captured_at: str) -> bool:
    """P20.5 Start Commitment (Abschnitt 25/26/47/48): einmalige, immutable Planreferenz beim
    ERSTEN fachlichen Beginn-Ereignis dieser Phase - "was war geplant, als die Phase
    tatsächlich begann?". No-Op (liefert False), wenn bereits ein Commitment existiert
    (Immutable, Abschnitt 26 - spätere Planänderungen überschreiben es nie) oder (noch) kein
    aktueller Plan (forecast_start) vorliegt, aus dem eine Referenz eingefroren werden könnte
    (Referenz ohne Planzeitraum wäre bedeutungslos - der nächste Aufruf versucht es erneut).
    Zwei Aufrufstellen, "je nachdem was zuerst geschieht" (Abschnitt 48): `refresh_actual_start()`
    unten (Zweig "erster relevanter Worklog") und routers/planning.py.update_plan_phase (Zweig
    "erster Statuswechsel aus geplant in laufend/abgeschlossen")."""
    if plan_phase.commitment_start is not None or plan_phase.forecast_start is None:
        return False
    plan_phase.commitment_start = plan_phase.forecast_start
    plan_phase.commitment_end = plan_phase.forecast_end
    plan_phase.commitment_plan_fte = plan_phase.plan_fte
    plan_phase.commitment_captured_at = captured_at
    return True


def refresh_actual_start(db: Session, project_id: int, captured_at: str) -> None:
    """Zieht actual_start aller Leaf-Phasen dieses Projekts aus dem (gerade aktualisierten)
    Worklog-Cache nach (P20.5, Abschnitt 10/17/18) - ausschließlich selbstkorrigierend (der
    gespeicherte Wert wandert nur nach FRÜHER, nie nach später, falls ein rückdatierter
    Worklog nachträglich im Cache erscheint) und löst bei Bedarf `maybe_capture_commitment()`
    aus. Aufrufer: jira_sync.sync_project_and_refresh() - nach jedem (auch automatischen)
    Sync-Lauf. Erzeugt bewusst KEINEN PlanHistory-Eintrag (Abschnitt 50 - ein Sync-Lauf ist
    keine User-/Domain-Änderung); der Aufrufer committed selbst."""
    leaves = (
        db.query(models.PlanPhase)
        .filter(models.PlanPhase.project_id == project_id, models.PlanPhase.jira_label.isnot(None))
        .all()
    )
    for leaf in leaves:
        first_date = leaf_first_capacity_worklog_date(db, leaf)
        if first_date is not None and (leaf.actual_start is None or first_date < leaf.actual_start):
            leaf.actual_start = first_date
            maybe_capture_commitment(leaf, captured_at)


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
