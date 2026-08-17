"""Sync- und Umrechnungslogik für die Jira-Ist-Integration (CONCEPT.md Abschnitt 4)."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from . import jira_client, models, tempo_client
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

    Alle Buchungen werden übernommen. Für noch nicht zugeordnete Accounts verwendet die
    Ist-FTE-Berechnung 40 Wochenstunden als transparenten Standardwert. Damit verschwinden
    Tempo-/Jira-Daten nicht nur deshalb, weil die Personenpflege noch nicht abgeschlossen ist.
    Nur Buchungen von Personen mit bekanntem `jira_account_id` (siehe models.Person) werden
    als zugeordnet gezählt, da sonst keine Wochenstunden für die FTE-Umrechnung bekannt sind.

    Rückgabe: (Anzahl gecachter Worklogs, Anzahl unzugeordneter Buchungen, Beispiele
    unbekannter Autoren als {"account_id", "display_name"} — zum Abgleich mit den in den
    Personen-Stammdaten hinterlegten Jira-Account-IDs, falls eine Zuordnung fehlschlägt).
    """
    since = (date.today() - timedelta(days=SYNC_LOOKBACK_DAYS)).isoformat()
    if tempo_client.is_configured():
        issues = jira_client.search_issues_for_component(project.jira_component, since)
        raw_worklogs = tempo_client.fetch_worklogs_for_issues(issues, since)
    else:
        raw_worklogs = jira_client.fetch_worklogs_for_component(project.jira_component, since)

    # Der Cache kennt nur eine Zeile je (Person, Ticket, Tag) — Tempo erlaubt aber mehrere
    # Buchungen am selben Tag/Ticket (z.B. vormittags/nachmittags getrennt). Vor dem Speichern
    # zusammenrechnen, statt mit doppeltem Schlüssel gegen den Unique-Constraint zu laufen.
    aggregiert: dict[tuple[str, str, str], dict] = {}
    for wl in raw_worklogs:
        key = (wl["issue_key"], wl["author_account_id"], wl["started"])
        if key in aggregiert:
            aggregiert[key]["stunden"] += wl["stunden"]
        else:
            aggregiert[key] = dict(wl)
    raw_worklogs = list(aggregiert.values())

    known_account_ids = {
        p.jira_account_id
        for p in db.query(models.Person).filter(models.Person.jira_account_id.isnot(None))
    }

    gespeichert = 0
    unzugeordnet = 0
    unzugeordnete_accounts: dict[str, str] = {}
    unbekannte_beispiele: dict[str, str] = {}
    for wl in raw_worklogs:
        if wl["author_account_id"] not in known_account_ids:
            unzugeordnet += 1
            unzugeordnete_accounts.setdefault(wl["author_account_id"], wl["author_display_name"])
            if len(unbekannte_beispiele) < MAX_UNBEKANNTE_BEISPIELE:
                unbekannte_beispiele.setdefault(wl["author_account_id"], wl["author_display_name"])

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

    # Neue unbekannte Autoren mit aufgelöstem Klarnamen persistieren, für die Übersicht
    # "Personen aus Buchungen ohne Teammitglied" in der Team-Kapazität-Ansicht. Tempo liefert
    # selbst keinen Namen (siehe tempo_client.py), deshalb hier per Jira auflösen — aber nur für
    # Accounts, die wir noch nicht kennen, damit nicht bei jedem Sync erneut aufgelöst wird.
    bereits_erfasst = {row[0] for row in db.query(models.UnassignedJiraAuthor.jira_account_id).all()}
    for account_id in unzugeordnete_accounts.keys() - bereits_erfasst:
        try:
            display_name = jira_client.get_user(account_id).get("displayName", unzugeordnete_accounts[account_id])
        except Exception:  # noqa: BLE001 – Name ist nur Anzeigesache, Sync darf trotzdem gelingen
            display_name = unzugeordnete_accounts[account_id]
        db.add(models.UnassignedJiraAuthor(jira_account_id=account_id, display_name=display_name))

    db.commit()
    return (
        gespeichert,
        unzugeordnet,
        [{"account_id": aid, "display_name": name} for aid, name in unbekannte_beispiele.items()],
    )


def berechne_ist_fte(db: Session, project: models.Project) -> dict[str, float]:
    """Ist-FTE je Monat aus dem Worklog-Cache.

    Formel (CONCEPT.md Abschnitt 4, Punkt 4):
    Ist_FTE(Monat) = Summe_Stunden / (Wochenstunden_Person × Arbeitswochen_Monat), je Person
    berechnet und je Projekt/Monat aufsummiert.
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

    # Alleinige Quelle für Wochenstunden ist seit dem Legacy Cutover (Phase 26.9)
    # Person.jira_account_id + ResourceProfile.weekly_hours. Unbekannte Autoren werden unten
    # mit dem 40h-Standardwert berechnet (siehe Kommentar dort).
    wochenstunden_by_account = {
        person.jira_account_id: profile.weekly_hours
        for person, profile in (
            db.query(models.Person, models.ResourceProfile)
            .join(models.ResourceProfile, models.ResourceProfile.person_id == models.Person.id)
            .filter(models.Person.jira_account_id.isnot(None))
        )
    }

    stunden_je_ma_monat: dict[tuple[str, str], float] = {}
    for row in rows:
        key = (row.jira_account_id, _monat_label(row.datum))
        stunden_je_ma_monat[key] = stunden_je_ma_monat.get(key, 0) + row.stunden

    ist: dict[str, float] = {}
    for (account_id, monat), stunden in stunden_je_ma_monat.items():
        # Unbekannte Jira-/Tempo-Autoren dürfen die Ist-Daten nicht vollständig ausblenden.
        # Sobald der Account einer Person zugeordnet wird, gilt automatisch deren echtes Profil.
        wochenstunden = wochenstunden_by_account.get(account_id, 40)
        fte_anteil = stunden / (wochenstunden * ARBEITSWOCHEN_PRO_MONAT)
        ist[monat] = ist.get(monat, 0) + fte_anteil

    return {monat: round(wert, 2) for monat, wert in ist.items()}
