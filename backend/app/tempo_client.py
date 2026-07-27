"""Client für die Tempo-Cloud-API (Zeiterfassung), getrennt von der nativen Jira-API.

Wird verwendet, wenn TEMPO_API_TOKEN gesetzt ist. Grund: Wird in Jira mit dem Tempo-
Timesheets-Plugin gebucht, zeigt der native Jira-Worklog-Autor häufig den
Tempo-Systemaccount ("Timesheets by Tempo - Jira Time Tracking") statt der echten Person —
die tatsächliche Zuordnung kennt nur Tempo selbst. Deshalb hier direkter Zugriff auf Tempo,
als Ersatz für jira_client.fetch_worklogs_for_component().

Konfiguration: TEMPO_API_TOKEN (Bearer-Token, erzeugt in Jira unter
Tempo -> Einstellungen -> API Integration; siehe README.md). Andere Basis-URL/Auth als
JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN, daher ein eigenständiger Client statt Erweiterung
von jira_client.py.
"""

import os
from datetime import date

import httpx

TEMPO_API_TOKEN = os.environ.get("TEMPO_API_TOKEN")
TEMPO_BASE_URL = "https://api.tempo.io/4"

# Anzahl Issue-IDs pro Tempo-Anfrage, damit die Query-String-Länge nicht ausufert.
ISSUE_BATCH_SIZE = 50


def is_configured() -> bool:
    return bool(TEMPO_API_TOKEN)


def _client() -> httpx.Client:
    if not is_configured():
        raise RuntimeError("Tempo ist nicht konfiguriert (TEMPO_API_TOKEN fehlt).")
    return httpx.Client(
        base_url=TEMPO_BASE_URL,
        headers={"Authorization": f"Bearer {TEMPO_API_TOKEN}", "Accept": "application/json"},
        timeout=30,
    )


def _paginated_get(client: httpx.Client, path: str, params: dict) -> list[dict]:
    """Tempo paginiert über `metadata.next` (volle URL zur nächsten Seite, falls vorhanden)."""
    results: list[dict] = []
    url = path
    next_params: dict | None = params
    while True:
        resp = client.get(url, params=next_params)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise httpx.HTTPStatusError(f"{exc}\nAntwort: {resp.text}", request=exc.request, response=exc.response) from exc
        data = resp.json()
        results.extend(data.get("results", []))
        next_url = data.get("metadata", {}).get("next")
        if not next_url:
            break
        url = next_url
        next_params = None  # in der next-URL bereits enthalten
    return results


def fetch_worklogs_for_issues(issues: list[dict], since: str) -> list[dict]:
    """Tempo-Worklogs für die gegebenen Issues (`[{"key": ..., "id": ...}, ...]`) seit `since`.

    Rückgabe im selben Format wie jira_client.fetch_worklogs_for_component(), damit
    jira_sync.sync_project() beide Quellen gleich weiterverarbeiten kann. Da Tempo keine
    Anzeigenamen im Worklog mitliefert, ist author_display_name hier zunächst die Account-ID.
    """
    if not issues:
        return []
    id_to_key = {str(issue["id"]): issue["key"] for issue in issues}
    issue_ids = list(id_to_key.keys())
    today = date.today().isoformat()

    with _client() as client:
        raw: list[dict] = []
        for start in range(0, len(issue_ids), ISSUE_BATCH_SIZE):
            batch = issue_ids[start : start + ISSUE_BATCH_SIZE]
            raw.extend(
                _paginated_get(client, "/worklogs", {"issueId": batch, "from": since, "to": today, "limit": 1000})
            )

    worklogs: list[dict] = []
    for wl in raw:
        started = wl["startDate"]
        if started < since:
            continue
        issue_id = str(wl["issue"]["id"])
        worklogs.append(
            {
                "issue_key": id_to_key.get(issue_id, issue_id),
                "author_account_id": wl["author"]["accountId"],
                "author_display_name": wl["author"]["accountId"],
                "started": started,
                "stunden": wl["timeSpentSeconds"] / 3600,
            }
        )
    return worklogs
