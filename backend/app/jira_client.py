"""Dünner Client für die Atlassian/Jira REST API (v3).

Konfiguration ausschließlich über Umgebungsvariablen, siehe README.md:
JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN (Basic-Auth mit API-Token, siehe
https://id.atlassian.com/manage-profile/security/api-tokens).
"""

import os

import httpx

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")


def is_configured() -> bool:
    return bool(JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN)


def _client() -> httpx.Client:
    if not is_configured():
        raise RuntimeError(
            "Jira ist nicht konfiguriert (JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN fehlen)."
        )
    return httpx.Client(
        base_url=JIRA_BASE_URL.rstrip("/"),
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Accept": "application/json"},
        timeout=30,
    )


def list_projects(query: str | None = None) -> list[dict]:
    """Jira-Projekte (Key + Name), für den Auswahlkatalog in `/jira/projects`.

    `query` filtert serverseitig auf Name/Key (Jira-Substring-Suche), damit auch bei vielen
    Projekten nicht immer alles geladen werden muss.
    """
    with _client() as client:
        projects: list[dict] = []
        start_at = 0
        while True:
            params = {"startAt": start_at, "maxResults": 50}
            if query:
                params["query"] = query
            resp = client.get("/rest/api/3/project/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            values = data.get("values", [])
            projects.extend({"key": p["key"], "name": p["name"]} for p in values)
            start_at += len(values)
            if data.get("isLast", True) or not values:
                break
    return projects


def list_components(project_key: str) -> list[dict]:
    """Components eines Jira-Projekts, für den Component-Picker je Kapa-Projekt."""
    with _client() as client:
        resp = client.get(f"/rest/api/3/project/{project_key}/components")
        resp.raise_for_status()
        return [{"id": c["id"], "name": c["name"]} for c in resp.json()]


def _search_issues(client: httpx.Client, jql: str, fields: str) -> list[dict]:
    """Paginiert über die aktuelle Jira-Such-API.

    `GET /rest/api/3/search` wurde von Atlassian abgeschaltet (410 Gone); der Nachfolger
    `/rest/api/3/search/jql` paginiert über `nextPageToken` statt `startAt`/`total`.
    """
    issues: list[dict] = []
    next_page_token: str | None = None
    while True:
        params: dict = {"jql": jql, "fields": fields, "maxResults": 100}
        if next_page_token:
            params["nextPageToken"] = next_page_token
        resp = client.get("/rest/api/3/search/jql", params=params)
        resp.raise_for_status()
        data = resp.json()
        page_issues = data.get("issues", [])
        issues.extend(page_issues)
        next_page_token = data.get("nextPageToken")
        if not next_page_token or not page_issues:
            break
    return issues


def list_labels(project_key: str) -> list[str]:
    """Labels, die tatsächlich auf Issues in diesem Jira-Projekt verwendet werden.

    Jira hat keine "Labels je Projekt"-API (Labels sind global/freitextig) — deshalb werden
    die Issues des Projekts durchsucht und die verwendeten Labels gesammelt. Ergänzung zu
    list_components(), da viele Teams statt/zusätzlich zu Components mit Labels arbeiten.
    """
    with _client() as client:
        issues = _search_issues(client, f'project = "{project_key}"', "labels")
        labels: set[str] = set()
        for issue in issues:
            labels.update(issue.get("fields", {}).get("labels") or [])
    return sorted(labels)


def search_users(query: str) -> list[dict]:
    """Nutzersuche für die MA-Stammdatenpflege (Zuordnung Team-Member -> Jira-Account)."""
    with _client() as client:
        resp = client.get("/rest/api/3/user/search", params={"query": query, "maxResults": 20})
        resp.raise_for_status()
        return resp.json()


def search_issues_for_component(component: str, since: str) -> list[dict]:
    """Issues (Key + numerische ID) mit gegebener Jira-Component oder -Label seit `since`.

    Rückgabe je Issue: `{"key": "ABC-1", "id": "10001"}`. Basis sowohl für den nativen
    Worklog-Fallback (fetch_worklogs_for_component) als auch für Tempo (tempo_client.py).
    """
    jql = f'(component = "{component}" OR labels = "{component}") AND worklogDate >= "{since}"'
    with _client() as client:
        issues = _search_issues(client, jql, "key")
    return [{"key": issue["key"], "id": issue["id"]} for issue in issues]


def fetch_worklogs_for_component(component: str, since: str) -> list[dict]:
    """Worklogs aller Issues mit gegebener Component/Label seit `since` (ISO-Datum "YYYY-MM-DD").

    Fallback über das native Jira-Worklog-Feature, wenn Tempo nicht konfiguriert ist (siehe
    tempo_client.py) — bei Tempo-Nutzung zeigt der native Worklog-Autor häufig den
    Tempo-Systemaccount statt der echten Person. Rückgabe je Worklog: issue_key,
    author_account_id, started, stunden.
    """
    issue_keys = [issue["key"] for issue in search_issues_for_component(component, since)]

    with _client() as client:
        worklogs: list[dict] = []
        for issue_key in issue_keys:
            wl_start_at = 0
            while True:
                resp = client.get(
                    f"/rest/api/3/issue/{issue_key}/worklog",
                    params={"startAt": wl_start_at, "maxResults": 100},
                )
                resp.raise_for_status()
                data = resp.json()
                entries = data.get("worklogs", [])
                for wl in entries:
                    started = wl["started"][:10]  # "YYYY-MM-DDTHH:MM:SS.SSS+ZZZZ" -> Datum
                    if started < since:
                        continue
                    worklogs.append(
                        {
                            "issue_key": issue_key,
                            "author_account_id": wl["author"]["accountId"],
                            "author_display_name": wl["author"].get("displayName", wl["author"]["accountId"]),
                            "started": started,
                            "stunden": wl["timeSpentSeconds"] / 3600,
                        }
                    )
                wl_start_at += len(entries)
                if not entries or wl_start_at >= data.get("total", 0):
                    break

    return worklogs
