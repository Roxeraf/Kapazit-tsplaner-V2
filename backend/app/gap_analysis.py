"""Soll-Ist-Gap-Analyse mit Hochrechnung (CONCEPT.md Abschnitt 5, Phasenplan-Schritt 3)."""

from sqlalchemy.orm import Session

from . import jira_sync, models
from .constants import berechne_monate

# Trendfortschreibung (Variante 1, CONCEPT.md Abschnitt 5): Durchschnitt der Ist-Werte
# der letzten TREND_MONATE Monate mit Buchungen wird auf die Restmonate projiziert.
TREND_MONATE = 3

# Schwellen für den Portfolio-Mini-Indikator (CONCEPT.md Abschnitt 6): Abweichung der
# projizierten Gesamtleistung vom Gesamt-Soll, in Prozent.
GAP_SCHWELLE_GELB = 0.10
GAP_SCHWELLE_ROT = 0.25


def _soll_je_monat(db: Session, project: models.Project, monate: list[str]) -> dict[str, float]:
    """Soll-FTE je Monat aus ResourceDemand (Phase 26.9 Legacy Cutover - ersetzt die
    Summe aus dem alten FtePlan/ProjectFtePlan-Grid). ResourceDemand ist bereits
    projektweit ohne Teilprojekt-Unterscheidung modelliert (siehe models.ResourceDemand)."""
    soll = dict.fromkeys(monate, 0.0)
    demands = db.query(models.ResourceDemand).filter(models.ResourceDemand.project_id == project.id).all()
    for demand in demands:
        if demand.period in soll:
            soll[demand.period] += demand.fte
    return {m: round(w, 2) for m, w in soll.items()}


def _hochrechnung(monate: list[str], ist: dict[str, float]) -> dict[str, float]:
    """Trendfortschreibung: Durchschnitt der letzten TREND_MONATE Ist-Monate auf die
    Restmonate (Monate ohne eigene Ist-Buchungen) projiziert."""
    ist_monate = [m for m in monate if m in ist]
    if not ist_monate:
        return {}
    letzte = ist_monate[-TREND_MONATE:]
    trend = sum(ist[m] for m in letzte) / len(letzte)
    return {m: round(trend, 2) for m in monate if m not in ist}


def gap_status(gap_pct: float | None) -> str:
    if gap_pct is None:
        return "grau"
    if abs(gap_pct) <= GAP_SCHWELLE_GELB:
        return "gruen"
    if abs(gap_pct) <= GAP_SCHWELLE_ROT:
        return "gelb"
    return "rot"


def project_gap(db: Session, project: models.Project) -> dict:
    """Soll/Ist/Gap je Monat sowie Hochrechnung Projekt-/Jahresende für ein Projekt."""
    monate = berechne_monate(project.start_monat, project.anzahl_monate)
    soll = _soll_je_monat(db, project, monate)
    ist = jira_sync.berechne_ist_fte(db, project)
    gap = {m: round(ist[m] - soll.get(m, 0.0), 2) for m in ist}
    hochrechnung = _hochrechnung(monate, ist)

    soll_gesamt = round(sum(soll.values()), 2)
    projiziert_gesamt = round(sum(ist.get(m, hochrechnung.get(m, 0.0)) for m in monate), 2)
    gap_gesamt = round(projiziert_gesamt - soll_gesamt, 2)

    if soll_gesamt == 0 or not ist:
        # Kein Plan oder noch keine Ist-Buchungen -> keine belastbare Aussage möglich.
        gap_pct = None
    else:
        gap_pct = round(gap_gesamt / soll_gesamt, 4)

    return {
        "project_id": project.id,
        "project_name": project.name,
        "monate": monate,
        "soll": soll,
        "ist": ist,
        "gap": gap,
        "hochrechnung": hochrechnung,
        "soll_gesamt": soll_gesamt,
        "projiziert_gesamt": projiziert_gesamt,
        "gap_gesamt": gap_gesamt,
        "gap_pct": gap_pct,
        "status": gap_status(gap_pct),
    }


def projekte_fuer_team(db: Session, team_id: int | None) -> list[models.Project]:
    """Projekte, optional gefiltert auf solche mit mind. einer ResourceAssignment einer
    Person aus dem Team (Phase 26.9 Legacy Cutover - ersetzt den alten Assignment/TeamMember-
    Join; Teamzugehörigkeit einer Person kommt seitdem aus ResourceProfile.team_id).

    on_hold/archivierte Projekte sind aus der aktiven Kapazitätsplanung ausgeblendet.
    Abgeschlossene Projekte bleiben sichtbar (Tracking-Anforderung).
    """
    query = (
        db.query(models.Project)
        .filter(models.Project.status.notin_(["on_hold", "archiviert"]))
        .order_by(models.Project.id)
    )
    if team_id is not None:
        query = (
            query.join(models.ResourceDemand, models.ResourceDemand.project_id == models.Project.id)
            .join(
                models.ResourceAssignment,
                models.ResourceAssignment.resource_demand_id == models.ResourceDemand.id,
            )
            .join(models.ResourceProfile, models.ResourceProfile.person_id == models.ResourceAssignment.person_id)
            .filter(models.ResourceProfile.team_id == team_id)
            .distinct()
        )
    return query.all()
