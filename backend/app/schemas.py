from typing import Literal

from pydantic import BaseModel, ConfigDict

JiraProjectStatus = Literal["aktiv", "on_hold", "beendet"]


class ProjectCreate(BaseModel):
    name: str
    kunde: str | None = None
    start_monat: str  # "MM.YYYY"
    anzahl_monate: int = 14
    jira_component: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    kunde: str | None = None
    start_monat: str | None = None
    anzahl_monate: int | None = None
    jira_component: str | None = None


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kunde: str | None
    start_monat: str
    anzahl_monate: int
    reihenfolge: int
    monate: list[str]


class ProjectReorder(BaseModel):
    project_ids: list[int]


class SubprojectCreate(BaseModel):
    name: str
    reihenfolge: int = 0


class SubprojectUpdate(BaseModel):
    name: str | None = None
    reihenfolge: int | None = None


class SubprojectDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    reihenfolge: int
    phasen: dict[str, list[str]]  # monat -> Phasencodes
    fte: dict[str, float]  # monat -> Soll-FTE


class SubprojectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_id: int
    project_name: str


class ProjectAssignmentOut(BaseModel):
    """Team-Zuordnung aus Sicht des Projekts (Gegenstück zu AssignmentOut aus MA-Sicht)."""

    id: int
    team_member_id: int
    member_name: str
    fte: float


class ProjectDetail(ProjectSummary):
    jira_component: str | None
    jira_project_key: str | None  # gesetzt, wenn aus dem Jira-Projekt-Katalog automatisch angelegt
    phasen: dict[str, list[str]]  # monat -> Phasencodes (Grundplanung direkt am Projekt)
    fte: dict[str, float]  # monat -> Soll-FTE (Summe aus Teilprojekten, falls vorhanden)
    aus_teilprojekten: bool  # true = phasen/fte sind aus Teilprojekten zusammengefasst (read-only)
    ist: dict[str, float]  # monat -> Ist-FTE aus Jira-Worklogs (siehe CONCEPT.md Abschnitt 4)
    team_assignments: list[ProjectAssignmentOut]
    subprojects: list[SubprojectDetail]


class PhasenUpdate(BaseModel):
    monat: str
    codes: list[str]  # z.B. ["p"] oder ["k", "t"]; leer = Zelle löschen


class FteUpdate(BaseModel):
    monat: str
    wert_soll: float


# ---------------------------------------------------------------------------
# Team-Kapazität (siehe CONCEPT.md Abschnitt 6/9, Phase 4)
# ---------------------------------------------------------------------------


class TeamCreate(BaseModel):
    name: str


class TeamUpdate(BaseModel):
    name: str | None = None


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TeamMemberCreate(BaseModel):
    name: str
    jira_account_id: str | None = None
    wochenstunden: float = 40
    team_id: int | None = None


class TeamMemberUpdate(BaseModel):
    name: str | None = None
    jira_account_id: str | None = None
    wochenstunden: float | None = None
    team_id: int | None = None


class AssignmentCreate(BaseModel):
    project_id: int
    fte: float = 0


class AssignmentOut(BaseModel):
    id: int
    project_id: int
    project_name: str
    fte: float


class TeamMemberOut(BaseModel):
    id: int
    name: str
    jira_account_id: str | None
    wochenstunden: float
    team_id: int | None
    team_name: str | None
    assignments: list[AssignmentOut]


class UnassignedAuthorOut(BaseModel):
    account_id: str
    display_name: str


class TeamWithMembers(TeamOut):
    members: list[TeamMemberOut]


# ---------------------------------------------------------------------------
# Jira-Ist-Integration (siehe CONCEPT.md Abschnitt 4, Phase 2)
# ---------------------------------------------------------------------------


class JiraStatus(BaseModel):
    configured: bool
    base_url: str | None
    tempo_configured: bool  # true = Worklogs kommen über die Tempo-API statt nativem Jira-Worklog
    hinweis: str


class JiraAccountMatch(BaseModel):
    account_id: str
    display_name: str
    email: str | None = None


class JiraUnknownAuthor(BaseModel):
    account_id: str
    display_name: str


class JiraSyncResultItem(BaseModel):
    project_id: int
    project_name: str
    jira_component: str
    worklogs_synced: int
    unzugeordnete_buchungen: int
    # Beispiele (max. jira_sync.MAX_UNBEKANNTE_BEISPIELE) unbekannter Autoren, zum Abgleich mit
    # den in den Team-Stammdaten hinterlegten Jira-Account-IDs.
    unbekannte_beispiele: list[JiraUnknownAuthor] = []
    error: str | None = None


class JiraSyncResult(BaseModel):
    status: str
    ergebnisse: list[JiraSyncResultItem]


class JiraProjectOut(BaseModel):
    key: str
    name: str
    relevant: bool
    status: JiraProjectStatus


class JiraProjectUpdate(BaseModel):
    relevant: bool
    status: JiraProjectStatus = "aktiv"


class JiraComponentOut(BaseModel):
    id: str
    name: str


# ---------------------------------------------------------------------------
# Gap-Analyse mit Hochrechnung (siehe CONCEPT.md Abschnitt 5, Phase 3)
# ---------------------------------------------------------------------------


class GapAnalysis(BaseModel):
    project_id: int
    project_name: str
    monate: list[str]
    soll: dict[str, float]  # monat -> geplanter FTE-Wert (Projekt- oder Teilprojekt-Summe)
    ist: dict[str, float]  # monat -> Ist-FTE aus Jira-Worklogs
    gap: dict[str, float]  # monat -> ist - soll, nur für Monate mit Ist-Daten
    hochrechnung: dict[str, float]  # monat -> projizierter FTE-Wert (Trendfortschreibung)
    soll_gesamt: float
    projiziert_gesamt: float  # Summe aus Ist (vergangen/laufend) + Hochrechnung (Rest)
    gap_gesamt: float  # projiziert_gesamt - soll_gesamt
    gap_pct: float | None  # gap_gesamt relativ zu soll_gesamt; None ohne belastbare Basis
    status: str  # "gruen" | "gelb" | "rot" | "grau" (kein Plan/keine Ist-Daten)


class ForecastSummary(BaseModel):
    """Eine Zeile "Hochrechnung Jahresende/Projektende" je Projekt (CONCEPT.md Abschnitt 5)."""

    project_id: int
    project_name: str
    soll_gesamt: float
    projiziert_gesamt: float
    gap_gesamt: float
    gap_pct: float | None
    status: str
