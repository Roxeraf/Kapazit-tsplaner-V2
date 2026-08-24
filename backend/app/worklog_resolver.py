"""Worklog->PlanPhase Resolver (P20.2, BD-1A/B/C CLOSED, siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 8). Reine, deterministische Zuordnung
eines Jira-Issues zu einer Leaf-PlanPhase - issue-scoped, nicht worklog-zeilen-scoped: ein
Ticket gehört im Regelfall über seine gesamte Laufzeit zu genau einer Phase (siehe
WorklogPhaseOverride-Docstring), deshalb wird hier je Issue einmal aufgelöst statt je
JiraWorklogCache-Zeile - alle Worklogs desselben Issues erhalten damit automatisch dieselbe
Zuordnung, ohne N+1 über Worklog-Zeilen.

Prioritätskette (Abschnitt 8, keine Ausnahmen):
1. Manual Override (WorklogPhaseOverride) - höchste Priorität, unabhängig von Labels.
2. Label-Match (Issue-Labels ∩ PlanPhase.jira_label, nur innerhalb desselben Projekts).
3. kein Treffer -> UNMAPPED, mehr als ein Treffer -> AMBIGUOUS.

Kein Datum an keiner Stelle (BD-1, Auftrag Abschnitt 7). Ein Issue wird nie mehr als einer
Phase operativ zugerechnet (keine Doppelzählung, Abschnitt 12/13).
"""

from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session

from . import models


class ResolutionStatus(str, Enum):
    MATCHED = "matched"
    UNMAPPED = "unmapped"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class IssueResolution:
    status: ResolutionStatus
    plan_phase_id: int | None
    # Für die Erklärbarkeit (Auftrag Abschnitt 35): "manual_override" | "jira_label" | None.
    mapping_source: str | None
    # Issue-Key (Override) bzw. das treffende Label (Match) - None bei UNMAPPED/AMBIGUOUS.
    mapping_value: str | None
    # Nur bei AMBIGUOUS befüllt: alle Phasen, die das Issue laut Label-Matchträfe (für UI/
    # Erklärung, welche Phasen konkret kollidieren).
    candidate_phase_ids: tuple[int, ...] = field(default_factory=tuple)


def _override_resolution(issue_key: str, plan_phase_id: int) -> IssueResolution:
    return IssueResolution(
        status=ResolutionStatus.MATCHED,
        plan_phase_id=plan_phase_id,
        mapping_source="manual_override",
        mapping_value=issue_key,
    )


def resolve_issue(
    issue_key: str,
    issue_labels: list[str],
    override_phase_id: int | None,
    phases_by_label: dict[str, list[int]],
) -> IssueResolution:
    """Reine Funktion, keine Seiteneffekte, kein DB-Zugriff - isoliert testbar (Abschnitt 8).

    `phases_by_label` bildet bereits nur auf Leaf-Phasen desselben Projekts ab (der Aufrufer
    - resolve_project_issues() - baut diese Map projekt-gescoped auf); diese Funktion selbst
    kennt kein Projekt und keine Hierarchie, sie operiert rein auf den übergebenen Mengen.
    """
    if override_phase_id is not None:
        return _override_resolution(issue_key, override_phase_id)

    matched_phase_ids: dict[int, str] = {}
    for label in issue_labels:
        for phase_id in phases_by_label.get(label, []):
            matched_phase_ids.setdefault(phase_id, label)

    if not matched_phase_ids:
        return IssueResolution(
            status=ResolutionStatus.UNMAPPED, plan_phase_id=None, mapping_source=None, mapping_value=None
        )
    if len(matched_phase_ids) == 1:
        (phase_id, label) = next(iter(matched_phase_ids.items()))
        return IssueResolution(
            status=ResolutionStatus.MATCHED, plan_phase_id=phase_id, mapping_source="jira_label", mapping_value=label
        )
    return IssueResolution(
        status=ResolutionStatus.AMBIGUOUS,
        plan_phase_id=None,
        mapping_source="jira_label",
        mapping_value=None,
        candidate_phase_ids=tuple(sorted(matched_phase_ids)),
    )


def resolve_project_issues(db: Session, project_id: int) -> dict[str, IssueResolution]:
    """Orchestriert resolve_issue() für alle beim letzten Sync gecachten Issues eines
    Projekts (JiraIssueCache) gegen die aktuell konfigurierten Leaf-Phase-Labels und
    Overrides desselben Projekts. Drei DB-Queries, danach reine In-Memory-Berechnung - kein
    N+1 über Worklog-Zeilen oder Issues."""
    issues = db.query(models.JiraIssueCache).filter(models.JiraIssueCache.project_id == project_id).all()
    overrides = {
        o.jira_issue_key: o.plan_phase_id
        for o in db.query(models.WorklogPhaseOverride).filter(models.WorklogPhaseOverride.project_id == project_id)
    }
    phases_by_label: dict[str, list[int]] = {}
    for phase_id, jira_label in (
        db.query(models.PlanPhase.id, models.PlanPhase.jira_label)
        .filter(models.PlanPhase.project_id == project_id, models.PlanPhase.jira_label.isnot(None))
        .all()
    ):
        phases_by_label.setdefault(jira_label, []).append(phase_id)

    result: dict[str, IssueResolution] = {}
    for issue in issues:
        labels = issue.labels.split(",") if issue.labels else []
        result[issue.jira_issue_key] = resolve_issue(
            issue.jira_issue_key, labels, overrides.get(issue.jira_issue_key), phases_by_label
        )

    # Ein Override hat höchste Priorität, auch für ein Issue, das (noch) nicht im
    # JiraIssueCache steht (z.B. Override vor dem nächsten Sync angelegt) - so verschwindet
    # ein bereits getroffener Override nie nur, weil der Cache noch nicht nachgezogen ist.
    for issue_key, plan_phase_id in overrides.items():
        if issue_key not in result:
            result[issue_key] = _override_resolution(issue_key, plan_phase_id)

    return result
