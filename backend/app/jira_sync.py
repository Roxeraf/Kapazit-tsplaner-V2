"""Sync- und Umrechnungslogik für die Jira-Ist-Integration (CONCEPT.md Abschnitt 4)."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from . import jira_client, models
from .constants import ARBEITSWOCHEN_PRO_MONAT, MONAT_NAMEN

# Rückblickzeitraum für den Sync: reicht für die üblichen Projektlaufzeiten (siehe anzahl_monate).
SYNC_LOOKBACK_DAYS = 400


def _monat_label(iso_datum: str) -> str:
    """"YYYY-MM-DD" -> Monatslabel im Format von berechne_monate(), z.B. "Apr 26"."""
    jahr, monat, _ = iso_datum.split("-")
    return f"{MONAT_NAMEN[int(monat) - 1]} {int(jahr) % 100:02d}"


MAX_UNBEKANNTE_BEISPIELE = 5


def sync_project(db: Session, project: models.Project) -> tuple[int, int, list[dict]]:
    """Holt Worklogs aus Jira für die Component/Label des Projekts und cached sie.

    Nur Buchungen von MA mit bekanntem `jira_account_id` (siehe team_members) werden
    übernommen, da sonst keine Wochenstunden für die FTE-Umrechnung bekannt sind.

    Rückgabe: (Anzahl gecachter Worklogs, Anzahl unzugeordneter Buchungen, Beispiele
    unbekannter Autoren als {"account_id", "display_name"} — zum Abgleich mit den in den
    Team-Stammdaten hinterlegten Jira-Account-IDs, falls eine Zuordnung fehlschlägt).
    """
    since = (date.today() - timedelta(days=SYNC_LOOKBACK_DAYS)).isoformat()
    raw_worklogs = jira_client.fetch_worklogs_for_component(project.jira_component, since)

    known_account_ids = {
        m.jira_account_id
        for m in db.query(models.TeamMember).filter(models.TeamMember.jira_account_id.isnot(None))
    }

    gespeichert = 0
    unzugeordnet = 0
    unbekannte_beispiele: dict[str, str] = {}
    for wl in raw_worklogs:
        if wl["author_account_id"] not in known_account_ids:
            unzugeordnet += 1
            if len(unbekannte_beispiele) < MAX_UNBEKANNTE_BEISPIELE:
                unbekannte_beispiele.setdefault(wl["author_account_id"], wl["author_display_name"])
            continue

        entry = (
            db.query(models.JiraWorklogCache)
            .filter(
                models.JiraWorklogCache.jira_account_id == wl["author_account_id"],
                models.JiraWorklogCache.jira_issue_key == wl["issue_key"],
                models.JiraWorklogCache.datum == wl["started"],
            )
            .first()
        )
        if entry is None:
            entry = models.JiraWorklogCache(
                jira_account_id=wl["author_account_id"],
                jira_issue_key=wl["issue_key"],
                datum=wl["started"],
            )
            db.add(entry)
        entry.stunden = wl["stunden"]
        entry.projekt_mapping = str(project.id)
        gespeichert += 1

    db.commit()
    return (
        gespeichert,
        unzugeordnet,
        [{"account_id": aid, "display_name": name} for aid, name in unbekannte_beispiele.items()],
    )


def berechne_ist_fte(db: Session, project: models.Project) -> dict[str, float]:
    """Ist-FTE je Monat aus dem Worklog-Cache.

    Formel (CONCEPT.md Abschnitt 4, Punkt 4):
    Ist_FTE(Monat) = Summe_Stunden / (Wochenstunden_MA × Arbeitswochen_Monat), je MA berechnet
    und je Projekt/Monat aufsummiert.
    """
    if project.jira_component is None:
        return {}

    rows = (
        db.query(models.JiraWorklogCache)
        .filter(models.JiraWorklogCache.projekt_mapping == str(project.id))
        .all()
    )
    if not rows:
        return {}

    wochenstunden_by_account = {
        m.jira_account_id: m.wochenstunden
        for m in db.query(models.TeamMember).filter(models.TeamMember.jira_account_id.isnot(None))
    }

    stunden_je_ma_monat: dict[tuple[str, str], float] = {}
    for row in rows:
        if row.jira_account_id not in wochenstunden_by_account:
            continue  # MA nicht (mehr) in den Stammdaten -> keine Wochenstunden bekannt
        key = (row.jira_account_id, _monat_label(row.datum))
        stunden_je_ma_monat[key] = stunden_je_ma_monat.get(key, 0) + row.stunden

    ist: dict[str, float] = {}
    for (account_id, monat), stunden in stunden_je_ma_monat.items():
        fte_anteil = stunden / (wochenstunden_by_account[account_id] * ARBEITSWOCHEN_PRO_MONAT)
        ist[monat] = ist.get(monat, 0) + fte_anteil

    return {monat: round(wert, 2) for monat, wert in ist.items()}
