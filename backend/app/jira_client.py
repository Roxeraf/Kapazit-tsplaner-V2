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


def search_users(query: str) -> list[dict]:
    """Nutzersuche für die MA-Stammdatenpflege (Zuordnung Team-Member -> Jira-Account)."""
    with _client() as client:
        resp = client.get("/rest/api/3/user/search", params={"query": query, "maxResults": 20})
        resp.raise_for_status()
        return resp.json()


def fetch_worklogs_for_component(component: str, since: str) -> list[dict]:
    """Worklogs aller Issues mit gegebener Component/Label seit `since` (ISO-Datum "YYYY-MM-DD").

    Empfehlung aus CONCEPT.md Abschnitt 4: Mapping über Jira-Component oder -Label, da ohne
    Custom-Field-Setup nutzbar. Rückgabe je Worklog: issue_key, author_account_id, started, stunden.
    """
    jql = f'(component = "{component}" OR labels = "{component}") AND worklogDate >= "{since}"'

    with _client() as client:
        issue_keys: list[str] = []
        next_page_token: str | None = None
        while True:
            # Atlassian hat GET /rest/api/3/search Ende 2025 abgeschaltet (liefert seither
            # 410 Gone). Nachfolger ist POST /rest/api/3/search/jql mit Cursor-Pagination
            # (nextPageToken) statt startAt/total.
            body: dict = {"jql": jql, "fields": ["key"], "maxResults": 100}
            if next_page_token:
                body["nextPageToken"] = next_page_token
            resp = client.post("/rest/api/3/search/jql", json=body)
            resp.raise_for_status()
            data = resp.json()
            issues = data.get("issues", [])
            issue_keys.extend(issue["key"] for issue in issues)
            next_page_token = data.get("nextPageToken")
            if not issues or not next_page_token:
                break

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
                            "started": started,
                            "stunden": wl["timeSpentSeconds"] / 3600,
                        }
                    )
                wl_start_at += len(entries)
                if not entries or wl_start_at >= data.get("total", 0):
                    break

    return worklogs
