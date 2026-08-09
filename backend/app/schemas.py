from typing import Literal

from pydantic import BaseModel, ConfigDict

JiraProjectStatus = Literal["aktiv", "on_hold", "beendet"]

# Lifecycle-Status eines Kapa-Projekts (unabhängig von JiraProjectStatus, das nur den
# Jira-Katalog-Eintrag betrifft, siehe models.JiraProjectCatalog).
ProjectStatus = Literal["aktiv", "on_hold", "abgeschlossen", "archiviert"]


class ProjectCreate(BaseModel):
    name: str
    kunde: str | None = None
    start_monat: str  # "MM.YYYY"
    anzahl_monate: int = 14
    jira_component: str | None = None
    projektleiter: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    kunde: str | None = None
    start_monat: str | None = None
    anzahl_monate: int | None = None
    jira_component: str | None = None
    status: ProjectStatus | None = None
    projektleiter: str | None = None
    # Nur für die Änderungshistorie (siehe PlanHistory) - wird nicht am Projekt persistiert.
    kommentar_id: int | None = None
    batch_id: str | None = None


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kunde: str | None
    start_monat: str
    anzahl_monate: int
    reihenfolge: int
    status: ProjectStatus
    projektleiter: str | None
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
    # Nur für die Änderungshistorie (siehe PlanHistory) - wird nicht persistiert.
    kommentar_id: int | None = None
    batch_id: str | None = None


class FteUpdate(BaseModel):
    monat: str
    wert_soll: float
    # Nur für die Änderungshistorie (siehe PlanHistory) - wird nicht persistiert.
    kommentar_id: int | None = None
    batch_id: str | None = None


# ---------------------------------------------------------------------------
# Zentrale Dokumentenablage, Tags & Kommunikation (siehe CONCEPT.md Abschnitt 6a)
# ---------------------------------------------------------------------------

# entity_type-Vokabular, geteilt zwischen TagLink und DocumentLink. "document" nur für
# TagLink relevant (Dokumente sind selbst taggbar, aber nie Ziel eines DocumentLink).
EntityType = Literal["comment", "decision", "risk", "meeting_minutes", "document"]


class DocumentUsageOut(BaseModel):
    entity_type: str
    entity_id: int
    label: str


class DocumentOut(BaseModel):
    id: int
    project_id: int
    dateiname: str
    mimetype: str | None
    groesse_bytes: int
    hochgeladen_von: str | None
    hochgeladen_am: str
    tags: list[str] = []
    used_in: list[DocumentUsageOut] = []


class DocumentUpdate(BaseModel):
    dateiname: str | None = None
    tags: list[str] | None = None


class DocumentLinkCreate(BaseModel):
    document_id: int
    entity_type: EntityType
    entity_id: int


class DocumentLinkOut(BaseModel):
    id: int
    document_id: int
    entity_type: str
    entity_id: int
    erstellt_am: str


class TagOut(BaseModel):
    id: int
    name: str


class DecisionCreate(BaseModel):
    titel: str
    beschreibung: str | None = None
    status: str = "offen"
    entschieden_von: str | None = None
    entschieden_am: str | None = None
    tags: list[str] = []


class DecisionUpdate(BaseModel):
    titel: str | None = None
    beschreibung: str | None = None
    status: str | None = None
    entschieden_von: str | None = None
    entschieden_am: str | None = None
    tags: list[str] | None = None


class DecisionOut(BaseModel):
    id: int
    project_id: int
    titel: str
    beschreibung: str | None
    status: str
    entschieden_von: str | None
    entschieden_am: str | None
    erstellt_am: str
    tags: list[str] = []
    documents: list[DocumentOut] = []


class RiskCreate(BaseModel):
    titel: str
    beschreibung: str | None = None
    wahrscheinlichkeit: str = "mittel"
    auswirkung: str = "mittel"
    status: str = "offen"
    owner: str | None = None
    faellig_am: str | None = None
    tags: list[str] = []


class RiskUpdate(BaseModel):
    titel: str | None = None
    beschreibung: str | None = None
    wahrscheinlichkeit: str | None = None
    auswirkung: str | None = None
    status: str | None = None
    owner: str | None = None
    faellig_am: str | None = None
    tags: list[str] | None = None


class RiskOut(BaseModel):
    id: int
    project_id: int
    titel: str
    beschreibung: str | None
    wahrscheinlichkeit: str
    auswirkung: str
    status: str
    owner: str | None
    faellig_am: str | None
    erstellt_am: str
    aktualisiert_am: str
    tags: list[str] = []
    documents: list[DocumentOut] = []


class MeetingMinutesCreate(BaseModel):
    titel: str
    datum: str
    teilnehmer: str | None = None
    text: str
    tags: list[str] = []


class MeetingMinutesUpdate(BaseModel):
    titel: str | None = None
    datum: str | None = None
    teilnehmer: str | None = None
    text: str | None = None
    tags: list[str] | None = None


class MeetingMinutesOut(BaseModel):
    id: int
    project_id: int
    titel: str
    datum: str
    teilnehmer: str | None
    text: str
    erstellt_am: str
    tags: list[str] = []
    documents: list[DocumentOut] = []


# ---------------------------------------------------------------------------
# Kommentare & Änderungshistorie (Speichern-Button/Entwurfsmodus)
# ---------------------------------------------------------------------------


class CommentCreate(BaseModel):
    subproject_id: int | None = None
    monat: str | None = None
    phase_code: str | None = None
    text: str
    # Nur für allgemeine Notizen relevant (monat/phase_code=None) - Zell-Kommentare bleiben
    # reiner Text, siehe CONCEPT.md Abschnitt 6a.
    tags: list[str] = []


class CommentUpdate(BaseModel):
    text: str | None = None
    tags: list[str] | None = None


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    subproject_id: int | None
    monat: str | None
    phase_code: str | None
    text: str
    erstellt_am: str
    tags: list[str] = []
    documents: list[DocumentOut] = []


class PlanHistoryOut(BaseModel):
    id: int
    subproject_id: int | None
    bereich: str
    monat: str | None
    feld: str
    alter_wert: str | None
    neuer_wert: str | None
    geaendert_am: str
    batch_id: str | None = None
    kommentar: CommentOut | None = None


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
# Controlling-Erweiterung: Auslastung & KPIs (siehe CONCEPT.md Abschnitt 6/9, Schritt 9).
# Reine Aggregation aus TeamMember/Assignment bzw. Gap-Analyse/Risk/Decision - keine
# neuen Tabellen.
# ---------------------------------------------------------------------------


class MemberUtilizationOut(BaseModel):
    member_id: int
    member_name: str
    team_id: int | None
    team_name: str | None
    kapazitaet_fte: float
    zugeordnet_fte: float
    auslastung_pct: float | None  # None = keine Kapazität hinterlegt (wochenstunden = 0)


class KpiSummary(BaseModel):
    anzahl_projekte_aktiv: int
    anzahl_projekte_gruen: int
    anzahl_projekte_gelb: int
    anzahl_projekte_rot: int
    anzahl_projekte_grau: int
    durchschnittliche_auslastung_pct: float | None
    offene_risiken_gesamt: int
    offene_entscheidungen_gesamt: int


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
