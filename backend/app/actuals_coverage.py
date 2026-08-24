"""Mapping Coverage (P20.3, BD-1C/D CLOSED, siehe
P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 12/13/19). Aggregiert den
Worklog-Resolver (P20.2, `worklog_resolver.py`) über ein ganzes Projekt zu der zentralen
Vertrauens-Kennzahl: wie viele der tatsächlich gebuchten Projekt-Ist-Stunden sind eindeutig
einer Leaf-PlanPhase zugeordnet.

Projekt-Ist bleibt dabei IMMER die führende Summe direkt aus `jira_worklogs_cache`
(Abschnitt 20/28 des Auftrags) - Coverage wird nie umgekehrt aus den Phasen zurückgerechnet,
damit bei unvollständigem Mapping keine Stunden verschwinden:

    project_ist_total = mapped_total + ambiguous_total + unmapped_total   (immer, per Konstruktion)

Kein Datum an keiner Stelle. Keine Doppelzählung: ein Issue trägt seine Stunden in genau
einen der drei Töpfe ein (Auftrag Abschnitt 12/13/14).
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from . import models, worklog_resolver
from .worklog_resolver import ResolutionStatus


@dataclass(frozen=True)
class ProjectCoverage:
    project_ist_total: float
    mapped_total: float
    ambiguous_total: float
    unmapped_total: float
    # None bei project_ist_total == 0 - "keine Aussage möglich" statt irreführender 0%/100%
    # (Auftrag Abschnitt 19).
    coverage_pct: float | None


def _hours_by_issue(db: Session, project_id: int) -> dict[str, float]:
    """Stunden je Issue-Key aus dem bestehenden, unveränderten Worklog-Cache (Abschnitt 20:
    Projekt-Ist bleibt exakt diese Summe, niemals nur die gemappten Stunden)."""
    rows = (
        db.query(models.JiraWorklogCache.jira_issue_key, models.JiraWorklogCache.stunden)
        .filter(models.JiraWorklogCache.projekt_mapping == str(project_id))
        .all()
    )
    hours: dict[str, float] = {}
    for issue_key, stunden in rows:
        hours[issue_key] = hours.get(issue_key, 0.0) + stunden
    return hours


def project_coverage(db: Session, project_id: int) -> ProjectCoverage:
    hours_by_issue = _hours_by_issue(db, project_id)
    project_ist_total = round(sum(hours_by_issue.values()), 2)

    resolution = worklog_resolver.resolve_project_issues(db, project_id)

    mapped_total = 0.0
    ambiguous_total = 0.0
    for issue_key, hours in hours_by_issue.items():
        # Kein Resolver-Ergebnis (Issue noch nicht im jira_issue_cache, z.B. weil es beim
        # letzten Sync nicht mehr traf) oder explizit UNMAPPED -> zählt in keinem der beiden
        # Töpfe, landet unten automatisch im Unmapped-Rest (Stunden verschwinden nie).
        r = resolution.get(issue_key)
        if r is None or r.status is ResolutionStatus.UNMAPPED:
            continue
        if r.status is ResolutionStatus.AMBIGUOUS:
            ambiguous_total += hours
        elif r.status is ResolutionStatus.MATCHED:
            mapped_total += hours

    mapped_total = round(mapped_total, 2)
    ambiguous_total = round(ambiguous_total, 2)
    unmapped_total = round(project_ist_total - mapped_total - ambiguous_total, 2)
    coverage_pct = round(mapped_total / project_ist_total * 100, 2) if project_ist_total else None

    return ProjectCoverage(
        project_ist_total=project_ist_total,
        mapped_total=mapped_total,
        ambiguous_total=ambiguous_total,
        unmapped_total=unmapped_total,
        coverage_pct=coverage_pct,
    )
