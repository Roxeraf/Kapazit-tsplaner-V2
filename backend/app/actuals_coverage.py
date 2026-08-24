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

from . import worklog_actuals, worklog_resolver
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


def project_coverage(db: Session, project_id: int) -> ProjectCoverage:
    # P20.4 (worklog_actuals.py): dieselbe Worklog-Cache-Abfrage wird auch für die
    # Phase-Ist-Aggregation gebraucht - hier zentral gehalten, keine zweite Definition.
    issue_hours = worklog_actuals.hours_by_issue(db, project_id)
    project_ist_total = round(sum(issue_hours.values()), 2)

    resolution = worklog_resolver.resolve_project_issues(db, project_id)

    mapped_total = 0.0
    ambiguous_total = 0.0
    for issue_key, hours in issue_hours.items():
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
