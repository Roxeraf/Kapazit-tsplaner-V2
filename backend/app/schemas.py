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
    # Projektleitung seit Phase 26.1/26.9 ausschließlich über die Personen-Bridge - das
    # ehemalige Freitextfeld projektleiter ist entfernt (Legacy Cutover).
    projektleiter_person_id: int | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    kunde: str | None = None
    start_monat: str | None = None
    anzahl_monate: int | None = None
    jira_component: str | None = None
    status: ProjectStatus | None = None
    projektleiter_person_id: int | None = None
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
    projektleiter_person_id: int | None = None
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


class SubprojectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_id: int
    project_name: str


class ProjectDetail(ProjectSummary):
    jira_component: str | None
    jira_project_key: str | None  # gesetzt, wenn aus dem Jira-Projekt-Katalog automatisch angelegt
    ist: dict[str, float]  # monat -> Ist-FTE aus Jira-Worklogs (siehe CONCEPT.md Abschnitt 4)
    subprojects: list[SubprojectDetail]


class ProjectActualsCoverageOut(BaseModel):
    """P20.3 (BD-1C/D CLOSED, siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 19)
    - Vertrauenskennzahl, keine Health-Ampel. project_ist_total = mapped_total +
    ambiguous_total + unmapped_total (immer, per Konstruktion) - Projekt-Ist bleibt führend,
    wird nie aus den Phasen zurückgerechnet."""

    project_id: int
    project_ist_total: float
    mapped_total: float
    ambiguous_total: float
    unmapped_total: float
    coverage_pct: float | None  # None bei project_ist_total == 0


# ---------------------------------------------------------------------------
# Zentrale Dokumentenablage, Tags & Kommunikation (siehe CONCEPT.md Abschnitt 6a)
# ---------------------------------------------------------------------------

# entity_type-Vokabular, geteilt zwischen TagLink, DocumentLink und EntityRelation.
# "document" nur für TagLink relevant (Dokumente sind selbst taggbar, aber nie Ziel eines
# DocumentLink). Siehe Kapazitätsplaner-v2-Zielarchitektur, CONCEPT.md Abschnitt 12.
EntityType = Literal[
    "comment", "decision", "risk", "meeting_minutes", "task", "document", "blocker",
    "plan_phase", "milestone", "baseline_snapshot",
]

# relation_type-Vokabular für EntityRelation (Master-MD Abschnitt 45, "Knowledge Layer").
RelationType = Literal[
    "related_to",
    "resulted_in",
    "based_on",
    "follow_up",
    "blocks",
    "resolves",
    "depends_on",
    "supports",
    "caused_by",
]


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


class TagCategoryCreate(BaseModel):
    name: str
    description: str | None = None


class TagCreate(BaseModel):
    name: str
    category_id: int | None = None
    description: str | None = None
    color: str | None = None
    active: bool = True
    ai_relevant: bool = False
    ai_description: str | None = None
    synonyms: list[str] = []


class TagCategoryOut(BaseModel):
    id: int
    name: str
    description: str | None


class TagOut(BaseModel):
    id: int
    name: str
    category_id: int | None = None
    description: str | None = None
    color: str | None = None
    active: bool = True
    ai_relevant: bool = False
    ai_description: str | None = None
    synonyms: list[str] = []


class TagUpdate(BaseModel):
    category_id: int | None = None
    description: str | None = None
    color: str | None = None
    active: bool | None = None
    ai_relevant: bool | None = None
    ai_description: str | None = None
    synonyms: list[str] | None = None


class EntityRelationCreate(BaseModel):
    source_entity_type: EntityType
    source_entity_id: int
    target_entity_type: EntityType
    target_entity_id: int
    relation_type: RelationType
    created_by_person_id: int | None = None


class EntityRelationOut(BaseModel):
    id: int
    source_entity_type: str
    source_entity_id: int
    target_entity_type: str
    target_entity_id: int
    relation_type: str
    created_at: str
    created_by_person_id: int | None


# ---------------------------------------------------------------------------
# Knowledge Query Layer (Phase 15, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 46) -
# strukturierte Zugriffsschicht über alle taggable Entitäten, noch kein Vector-RAG/KI-Agent.
# ---------------------------------------------------------------------------


class KnowledgeEntityOut(BaseModel):
    entity_type: str
    entity_id: int
    project_id: int | None
    label: str | None
    tags: list[str] = []


class KnowledgeSearchResult(BaseModel):
    entity_type: str
    entity_id: int
    project_id: int | None
    label: str | None
    # "text" | "tag:<Tag-Name>" | "tag_semantisch:<Tag-Name>" (Phase 24: Treffer nur über
    # Synonym oder AI-Beschreibung des Tags, nicht über den Tag-Namen selbst).
    match: str


class RelatedEntityOut(BaseModel):
    """Andere Entität mit gemeinsamen Tags (Phase 24, "Related Entities" - Master-MD
    Abschnitt 40/46). Einfachste erklärbare Ähnlichkeit ohne Vector-/Embedding-Schicht."""

    entity_type: str
    entity_id: int
    project_id: int | None
    label: str | None
    shared_tags: list[str] = []


class KnowledgeContextOut(BaseModel):
    """"Wissenskarte" einer einzelnen Entität - Tags, Dokumente, Relationen (Quelle wie
    Ziel) und seit Phase 24 zusätzlich tag-basierte Related Entities an einem Ort, gedacht
    als Grundlage für spätere KI-Kontextassemblierung."""

    entity_type: str
    entity_id: int
    project_id: int | None
    label: str | None
    tags: list[str] = []
    documents: list[DocumentOut] = []
    relations: list[EntityRelationOut] = []
    related: list[RelatedEntityOut] = []


class KnowledgeProjectContextOut(BaseModel):
    project_id: int
    counts: dict[str, int]
    tags: list[str] = []
    relations: list[EntityRelationOut] = []


class DecisionCreate(BaseModel):
    titel: str
    beschreibung: str | None = None
    # Trennt WAS entschieden wurde (beschreibung) von WARUM (Decision Context, Phase 16,
    # siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 35: decision_text vs. reason).
    begruendung: str | None = None
    status: str = "offen"
    entschieden_von_person_id: int | None = None
    entschieden_am: str | None = None
    tags: list[str] = []
    plan_phase_id: int | None = None


class DecisionUpdate(BaseModel):
    titel: str | None = None
    beschreibung: str | None = None
    begruendung: str | None = None
    status: str | None = None
    entschieden_von_person_id: int | None = None
    entschieden_am: str | None = None
    tags: list[str] | None = None
    plan_phase_id: int | None = None


class DecisionOut(BaseModel):
    id: int
    project_id: int
    titel: str
    beschreibung: str | None
    begruendung: str | None = None
    status: str
    entschieden_von_person_id: int | None
    entschieden_am: str | None
    erstellt_am: str
    plan_phase_id: int | None = None
    tags: list[str] = []
    documents: list[DocumentOut] = []


class RiskCreate(BaseModel):
    titel: str
    beschreibung: str | None = None
    wahrscheinlichkeit: str = "mittel"
    auswirkung: str = "mittel"
    status: str = "offen"
    owner_person_id: int | None = None
    faellig_am: str | None = None
    tags: list[str] = []


class RiskUpdate(BaseModel):
    titel: str | None = None
    beschreibung: str | None = None
    wahrscheinlichkeit: str | None = None
    auswirkung: str | None = None
    status: str | None = None
    owner_person_id: int | None = None
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
    owner_person_id: int | None
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


class TaskCreate(BaseModel):
    titel: str
    beschreibung: str | None = None
    status: str = "offen"
    zustaendig_person_id: int | None = None
    faellig_am: str | None = None
    tags: list[str] = []
    plan_phase_id: int | None = None


class TaskUpdate(BaseModel):
    titel: str | None = None
    beschreibung: str | None = None
    status: str | None = None
    zustaendig_person_id: int | None = None
    faellig_am: str | None = None
    tags: list[str] | None = None
    plan_phase_id: int | None = None


class TaskOut(BaseModel):
    id: int
    project_id: int
    titel: str
    beschreibung: str | None
    status: str
    zustaendig_person_id: int | None
    faellig_am: str | None
    erstellt_am: str
    aktualisiert_am: str
    plan_phase_id: int | None = None
    tags: list[str] = []
    documents: list[DocumentOut] = []


# ---------------------------------------------------------------------------
# Blocker (Phase 16, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 37/38). Englische
# Feldnamen wie Person/ResourceProfile (Zielarchitektur-native Entität), im Unterschied zu
# den aus dem Excel-Tool abgeleiteten Kommunikation-Tab-Modellen oberhalb.
# ---------------------------------------------------------------------------

BlockerParty = Literal["INTERNAL", "CUSTOMER", "THIRD_PARTY", "UNKNOWN"]


class BlockerCreate(BaseModel):
    title: str
    description: str | None = None
    status: str = "offen"  # offen/in_bearbeitung/geloest
    severity: str = "mittel"  # niedrig/mittel/hoch/kritisch
    active_since: str | None = None
    caused_by_party: BlockerParty = "UNKNOWN"
    waiting_for_party: BlockerParty = "UNKNOWN"
    owner_person_id: int | None = None
    owner_team_id: int | None = None
    next_action: str | None = None
    impact: str | None = None
    tags: list[str] = []
    plan_phase_id: int | None = None


class BlockerUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    severity: str | None = None
    active_since: str | None = None
    caused_by_party: BlockerParty | None = None
    waiting_for_party: BlockerParty | None = None
    owner_person_id: int | None = None
    owner_team_id: int | None = None
    next_action: str | None = None
    impact: str | None = None
    tags: list[str] | None = None
    plan_phase_id: int | None = None


class BlockerOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None
    status: str
    severity: str
    active_since: str | None
    caused_by_party: str
    waiting_for_party: str
    owner_person_id: int | None
    owner_team_id: int | None
    next_action: str | None
    impact: str | None
    erstellt_am: str
    aktualisiert_am: str
    plan_phase_id: int | None = None
    tags: list[str] = []
    documents: list[DocumentOut] = []


# ---------------------------------------------------------------------------
# PlanPhase & Milestone (Phase 17, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 8/9/10).
# Zielarchitektur-native Entitäten, englische Feldnamen. Additiv - kein Sync mit dem
# bestehenden Gantt-Grid (GanttPhase/ProjectGanttPhase bleiben unverändert die Bedienoberfläche).
# ---------------------------------------------------------------------------


class PlanPhaseCreate(BaseModel):
    subproject_id: int | None = None
    # Self-referencing FK (P18/B-1/B-3, CONCEPT.md Abschnitt 6b.1) - None = Top-Level-Phase.
    parent_phase_id: int | None = None
    reihenfolge: int = 0
    phase_type: str
    baseline_start: str | None = None
    baseline_end: str | None = None
    forecast_start: str | None = None
    forecast_end: str | None = None
    actual_start: str | None = None
    actual_end: str | None = None
    status: str = "geplant"  # Zielvokabular: geplant/laufend/abgeschlossen/entfaellt (siehe models.PlanPhase.status)
    progress: float | None = None
    plan_fte: float | None = None
    # P20.1 (BD-1A CLOSED): Jira-Label fuer den automatischen Worklog-Resolver, nur auf
    # Leaf-Phasen sinnvoll - gleicher Lifecycle wie plan_fte (siehe models.PlanPhase.jira_label).
    jira_label: str | None = None
    owner_person_id: int | None = None
    owner_team_id: int | None = None
    tags: list[str] = []


class PlanPhaseUpdate(BaseModel):
    subproject_id: int | None = None
    # Unset (None-Default, exclude_unset) = unverändert; explizit auf null gesetzt = Phase
    # wird Top-Level (P18/B-3, CONCEPT.md Abschnitt 6b.1).
    parent_phase_id: int | None = None
    reihenfolge: int | None = None
    phase_type: str | None = None
    baseline_start: str | None = None
    baseline_end: str | None = None
    forecast_start: str | None = None
    forecast_end: str | None = None
    actual_start: str | None = None
    actual_end: str | None = None
    status: str | None = None
    # Deprecated (P6/P11): bleibt im Schema aus Rückwärtskompatibilität, wird von
    # update_plan_phase() aber ignoriert (siehe routers/planning.py) - kein Update-Pfad soll
    # progress mehr schreiben können, nicht nur create_plan_phase().
    progress: float | None = None
    plan_fte: float | None = None
    jira_label: str | None = None
    owner_person_id: int | None = None
    owner_team_id: int | None = None
    tags: list[str] | None = None


class PlanPhaseOut(BaseModel):
    id: int
    project_id: int
    subproject_id: int | None
    parent_phase_id: int | None
    reihenfolge: int
    phase_type: str
    baseline_start: str | None
    baseline_end: str | None
    forecast_start: str | None
    forecast_end: str | None
    actual_start: str | None
    actual_end: str | None
    status: str
    progress: float | None
    plan_fte: float | None
    # P20.1 (BD-1A CLOSED): siehe models.PlanPhase.jira_label / PlanPhaseCreate.jira_label.
    jira_label: str | None = None
    owner_person_id: int | None
    owner_team_id: int | None
    erstellt_am: str
    aktualisiert_am: str
    tags: list[str] = []
    documents: list[DocumentOut] = []
    # P18/B-3 (CONCEPT.md Abschnitt 6b.3): query-seitig berechnet, kein gespeichertes Feld.
    has_children: bool = False
    # Nur für Parent-Phasen (has_children=True) befüllt - abgeleitet aus den Leaf-Nachfahren
    # (Abschnitt 6b.3/6b.6), NIE aus einem eigenen Feld der Parent-Phase selbst.
    # forecast_start/forecast_end/plan_fte bleiben für Parent-Phasen None (Abschnitt 6b.1a).
    derived_forecast_start: str | None = None
    derived_forecast_end: str | None = None
    derived_capacity: float | None = None


class WorklogPhaseOverrideCreate(BaseModel):
    """P20.1 (BD-1B CLOSED): manuelle Worklog->PlanPhase-Zuordnung auf Issue-Key-Ebene, siehe
    models.WorklogPhaseOverride. previous_status wird optional mitgegeben, da der Resolver
    (P20.2), der ihn eigentlich berechnet, in diesem Paket noch nicht existiert."""

    jira_issue_key: str
    previous_status: str | None = None
    note: str | None = None
    created_by_person_id: int | None = None


class WorklogPhaseOverrideOut(BaseModel):
    id: int
    project_id: int
    jira_issue_key: str
    plan_phase_id: int
    previous_status: str | None
    note: str | None
    created_by_person_id: int | None
    created_at: str


class MilestoneCreate(BaseModel):
    subproject_id: int | None = None
    # P18/B-1/B-7 (CONCEPT.md Abschnitt 6b.8): ersetzt subproject_id fachlich - NULL bleibt
    # "projektweiter Meilenstein", gesetzt kann auf eine Leaf- ODER Parent-Phase zeigen (ein
    # Meilenstein schließt oft eine Sammelphase ab).
    plan_phase_id: int | None = None
    name: str
    baseline_date: str | None = None
    forecast_date: str | None = None
    actual_date: str | None = None
    status: str = "geplant"  # geplant/gefaehrdet/erreicht/verpasst
    owner_person_id: int | None = None
    owner_team_id: int | None = None
    tags: list[str] = []


class MilestoneUpdate(BaseModel):
    subproject_id: int | None = None
    plan_phase_id: int | None = None
    name: str | None = None
    baseline_date: str | None = None
    forecast_date: str | None = None
    actual_date: str | None = None
    status: str | None = None
    owner_person_id: int | None = None
    owner_team_id: int | None = None
    tags: list[str] | None = None


class MilestoneOut(BaseModel):
    id: int
    project_id: int
    subproject_id: int | None
    plan_phase_id: int | None
    name: str
    baseline_date: str | None
    forecast_date: str | None
    actual_date: str | None
    status: str
    owner_person_id: int | None
    owner_team_id: int | None
    erstellt_am: str
    aktualisiert_am: str
    tags: list[str] = []
    documents: list[DocumentOut] = []


# ---------------------------------------------------------------------------
# Baseline Management (Phase 18, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 12) -
# eingefrorener, benannter Planstand (PlanPhase/Milestone-Felder) zu einem Zeitpunkt.
# ---------------------------------------------------------------------------


class BaselineSnapshotCreate(BaseModel):
    name: str
    reason: str | None = None
    created_by_person_id: int | None = None
    tags: list[str] = []


class BaselineEntryOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    field: str
    value: str | None


class BaselineSnapshotOut(BaseModel):
    id: int
    project_id: int
    name: str
    reason: str | None = None
    created_at: str
    created_by_person_id: int | None
    tags: list[str] = []
    entries: list[BaselineEntryOut] = []


class BaselineSnapshotSummary(BaseModel):
    id: int
    project_id: int
    name: str
    reason: str | None = None
    created_at: str
    created_by_person_id: int | None
    entry_count: int
    tags: list[str] = []


class BaselineDeviationOut(BaseModel):
    entity_type: str
    entity_id: int
    label: str | None
    field: str
    baseline_value: str | None
    current_value: str | None
    delta_days: int | None  # None, wenn baseline_value/current_value kein gültiges Datum ist
    # P18.1 Stabilization (CONCEPT.md Abschnitt 16.16): "changed" (Default, bestehendes
    # Feld-Delta-Verhalten) vs. "added"/"removed" für strukturelle Baum-Änderungen (eine nach
    # dem Snapshot neu angelegte bzw. seither gelöschte PlanPhase). field/baseline_value/
    # current_value bleiben bei "added"/"removed" auf den rekonstruierbaren Phasennamen
    # bezogen (siehe baseline_calc.py), nicht auf ein echtes vergleichbares Feld.
    type: Literal["changed", "added", "removed"] = "changed"


# ---------------------------------------------------------------------------
# Capacity Planning Core (Phase 19, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt
# 14-19). Grundsatz "Demand ≠ Assignment" - komplett unabhängig vom bestehenden
# Assignment-Modell (TeamMember<->Project, siehe TeamMemberOut/AssignmentOut oben).
# ---------------------------------------------------------------------------

CommitmentLevel = Literal["FIX", "TENTATIVE", "SCENARIO"]


class ResourceRoleCreate(BaseModel):
    name: str
    description: str | None = None


class ResourceRoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None


class ResourceRoleOut(BaseModel):
    id: int
    name: str
    description: str | None
    active: bool


class SkillCreate(BaseModel):
    name: str
    category: str | None = None


class SkillUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    active: bool | None = None


class SkillOut(BaseModel):
    id: int
    name: str
    category: str | None
    active: bool


class PersonSkillCreate(BaseModel):
    skill_id: int
    level: str | None = None


class PersonSkillOut(BaseModel):
    id: int
    person_id: int
    skill_id: int
    skill_name: str
    level: str | None


class ResourceDemandCreate(BaseModel):
    plan_phase_id: int | None = None
    resource_role_id: int
    period: str
    fte: float = 0
    commitment_level: CommitmentLevel = "TENTATIVE"


class ResourceDemandUpdate(BaseModel):
    plan_phase_id: int | None = None
    resource_role_id: int | None = None
    period: str | None = None
    fte: float | None = None
    commitment_level: CommitmentLevel | None = None


class ResourceAssignmentCreate(BaseModel):
    person_id: int
    fte: float = 0


class ResourceAssignmentOut(BaseModel):
    id: int
    resource_demand_id: int
    person_id: int
    person_name: str
    fte: float
    erstellt_am: str
    aktualisiert_am: str


class ResourceDemandOut(BaseModel):
    id: int
    project_id: int
    plan_phase_id: int | None
    resource_role_id: int
    resource_role_name: str
    period: str
    fte: float
    commitment_level: str
    erstellt_am: str
    aktualisiert_am: str
    assigned_fte: float  # Summe der ResourceAssignment.fte
    # Allocation Gap (Phase 21, Master-MD Abschnitt 22): fte - assigned_fte. Negativ =
    # Unterdeckung (weniger zugeordnet als bedarf), positiv = Überdeckung.
    allocation_gap: float
    # P19.2 (Kapazität-Tab N+1-Fix): die einzelnen ResourceAssignments dieses Demands additiv
    # mitgeliefert - löst das N+1-Muster auf (vorher: pro aufgeklapptem Demand ein eigener
    # GET .../assignments-Call). Der eigenständige Endpoint (GET .../assignments) bleibt
    # bestehen (z.B. für Nach-Mutation-Refresh ohne vollen Detail-Reload).
    assignments: list[ResourceAssignmentOut] = []


class CandidatePersonOut(BaseModel):
    """Phase 26.3: Person mit freier Kapazität für einen ResourceDemand. Es gibt keine
    Person<->ResourceRole-Zuordnung im Datenmodell (siehe capacity_calc.compute_capacity_gap-
    Docstring) - Filterung ausschließlich nach verfügbarer Kapazität, Skills sind rein
    informativ mitgeliefert, kein Filterkriterium."""

    person_id: int
    display_name: str
    available_fte: float
    skills: list[str] = []


# ---------------------------------------------------------------------------
# Real Capacity (Phase 20, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 20).
# Grundformel: Nominal Capacity - Holiday - Absence - Internal Allocation = Available Capacity.
# ---------------------------------------------------------------------------


class CapacityCalendarCreate(BaseModel):
    name: str
    description: str | None = None


class CapacityCalendarUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None


class CapacityCalendarOut(BaseModel):
    id: int
    name: str
    description: str | None
    active: bool


class HolidayCreate(BaseModel):
    date: str
    name: str


class HolidayOut(BaseModel):
    id: int
    capacity_calendar_id: int
    date: str
    name: str


class WorkingTimeCreate(BaseModel):
    capacity_calendar_id: int | None = None
    valid_from: str
    valid_to: str | None = None
    weekly_hours: float = 40


class WorkingTimeUpdate(BaseModel):
    capacity_calendar_id: int | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    weekly_hours: float | None = None


class WorkingTimeOut(BaseModel):
    id: int
    person_id: int
    capacity_calendar_id: int | None
    valid_from: str
    valid_to: str | None
    weekly_hours: float


class AbsenceCreate(BaseModel):
    absence_type: str = "urlaub"
    start_date: str
    end_date: str


class AbsenceUpdate(BaseModel):
    absence_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class AbsenceOut(BaseModel):
    id: int
    person_id: int
    absence_type: str
    start_date: str
    end_date: str


class InternalAllocationCreate(BaseModel):
    period: str
    fte: float = 0
    description: str | None = None


class InternalAllocationUpdate(BaseModel):
    period: str | None = None
    fte: float | None = None
    description: str | None = None


class InternalAllocationOut(BaseModel):
    id: int
    person_id: int
    period: str
    fte: float
    description: str | None


class PersonCapacityOut(BaseModel):
    """Verfügbare Kapazität einer Person in einer Periode (Master-MD Abschnitt 20
    Grundformel). Holiday/Absence werden über den Werktage-Anteil der Periode proportional
    in FTE umgerechnet, InternalAllocation wird direkt in FTE abgezogen (bereits so
    gepflegt)."""

    person_id: int
    period: str
    nominal_fte: float
    holiday_fte: float
    absence_fte: float
    internal_fte: float
    available_fte: float
    working_days: int
    holiday_days: int
    absence_days: int


class ProjectMonthlyCapacityPhaseContribution(BaseModel):
    """Ein Beitrag einer einzelnen Leaf-PlanPhase zu Projektkapazität(Monat) (P19.7,
    CONCEPT.md Abschnitt 6b.6/Auftrag Abschnitt 20) - für die Monats-Drilldown-Darstellung
    im Planning-Tab. Reine Aufschlüsselung derselben Summe aus ProjectMonthlyCapacityEntry.hours,
    kein zusätzlicher Berechnungsweg."""

    plan_phase_id: int
    phase_type: str
    hours: float


class ProjectMonthlyCapacityEntry(BaseModel):
    """Ein Monat der abgeleiteten Projektkapazität (P18/B-5, CONCEPT.md Abschnitt 6b.6) -
    reine AUSWERTUNG, kein Eingabefeld: SUM(monthly_distribution(leaf.plan_fte, ...)) über
    alle Leaf-PlanPhases des Projekts. Read-only, UI-Label "Projektkapazität" (nicht
    "ResourceDemand"). by_phase (P19.7) schlüsselt dieselbe Summe additiv nach beitragender
    Phase auf - rein darstellend, keine Bewertung/Ampel (das ist explizit nicht Teil dieser
    Auswertung)."""

    period: str
    hours: float
    fte_equivalent: float
    by_phase: list[ProjectMonthlyCapacityPhaseContribution] = []


class PersonCapacityRangeOut(BaseModel):
    """Bereichsbasierte Variante von PersonCapacityOut (P18/B-4, CONCEPT.md Abschnitt
    6b.5/6b.11) - für die Available-Capacity-Prüfung über einen ganzen PlanPhase-Zeitraum
    statt nur einen einzelnen Monats-Bucket. Keine holiday_days/absence_days (Tageszahlen
    wären über mehrere Monate hinweg nicht mehr eindeutig interpretierbar - die zugrunde
    liegenden Werte fließen bereits werktage-gewichtet in die FTE-Felder ein)."""

    person_id: int
    range_start: str
    range_end: str
    nominal_fte: float
    holiday_fte: float
    absence_fte: float
    internal_fte: float
    available_fte: float
    working_days: int


# ---------------------------------------------------------------------------
# Activity Feed (Phase 16, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 32) - reine
# chronologische Aggregation bestehender Endpunkte, keine neue Tabelle.
# ---------------------------------------------------------------------------


class ActivityItemOut(BaseModel):
    entity_type: str
    entity_id: int
    label: str | None
    timestamp: str
    tags: list[str] = []


# ---------------------------------------------------------------------------
# Tag-Dossiers (Phase 24, siehe CONCEPT.md Abschnitt 12.4 / Master-MD Abschnitt 44
# "dynamische Tag-Sichten") - ein Tag (oder eine Kombination wie "#Kunde + #GoLive") wird
# zu einem dynamischen Projektdossier: Anzahl je Entitätstyp, die Entitäten selbst und die
# jüngste Aktivität dazu.
# ---------------------------------------------------------------------------


class TagDossierOut(BaseModel):
    tags: list[str]
    mode: Literal["and", "or"]
    project_id: int | None
    counts: dict[str, int] = {}
    entities: list[KnowledgeEntityOut] = []
    activity: list[ActivityItemOut] = []


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
    # Gesetzt = Antwort auf einen anderen Kommentar (Discussion Threading, Phase 16, siehe
    # CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 34).
    parent_id: int | None = None
    plan_phase_id: int | None = None


class CommentUpdate(BaseModel):
    text: str | None = None
    tags: list[str] | None = None
    plan_phase_id: int | None = None


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    subproject_id: int | None
    monat: str | None
    phase_code: str | None
    text: str
    erstellt_am: str
    parent_id: int | None = None
    plan_phase_id: int | None = None
    tags: list[str] = []
    documents: list[DocumentOut] = []


class PlanHistoryOut(BaseModel):
    id: int
    subproject_id: int | None
    # P18/B-1/B-3 (CONCEPT.md Abschnitt 6b.1a) - gesetzt u.a. beim Leaf->Parent-Übergang
    # (bereich="phase_struktur", historisiert den zuvor operativen plan_fte-Wert).
    plan_phase_id: int | None = None
    bereich: str
    monat: str | None
    feld: str
    alter_wert: str | None
    neuer_wert: str | None
    geaendert_am: str
    batch_id: str | None = None
    kommentar: CommentOut | None = None


# ---------------------------------------------------------------------------
# Team-Kapazität (siehe CONCEPT.md Abschnitt 6/9, Phase 4). Mitgliederverwaltung läuft seit
# dem Legacy Cutover (Phase 26.9) über Person/ResourceProfile (routers/people.py),
# TeamMember/Assignment sind entfallen - "Mitglied eines Teams" = ResourceProfile.team_id.
# ---------------------------------------------------------------------------


class TeamCreate(BaseModel):
    name: str


class TeamUpdate(BaseModel):
    name: str | None = None


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UnassignedAuthorOut(BaseModel):
    account_id: str
    display_name: str


# ---------------------------------------------------------------------------
# Personen, Organisation & Permissions (Phase 14, siehe CONCEPT.md Abschnitt 12). Person ist
# bewusst schlank (kein Auth/Login) - seit Phase 26.9 die alleinige Kapazitätsressource
# (ResourceProfile macht sie kapazitätsplanbar/teamzugehörig).
# ---------------------------------------------------------------------------

PersonSource = Literal["LOCAL", "ENTERPRISE_PLATFORM"]


class PersonCreate(BaseModel):
    display_name: str
    email: str | None = None
    external_id: str | None = None
    source: PersonSource = "LOCAL"
    active: bool = True
    # Seit dem Legacy Cutover (Phase 26.9) die alleinige Jira-Worklog-Zuordnungsebene -
    # TeamMember.jira_account_id ist entfallen (siehe jira_sync.py).
    jira_account_id: str | None = None


class PersonUpdate(BaseModel):
    display_name: str | None = None
    email: str | None = None
    active: bool | None = None
    jira_account_id: str | None = None


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str | None
    display_name: str
    email: str | None
    source: PersonSource
    active: bool
    jira_account_id: str | None = None


class ResourceProfileCreate(BaseModel):
    team_id: int | None = None
    weekly_hours: float = 40
    capacity_relevant: bool = True
    active: bool = True


class ResourceProfileUpdate(BaseModel):
    team_id: int | None = None
    weekly_hours: float | None = None
    capacity_relevant: bool | None = None
    active: bool | None = None


class ResourceProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int
    team_id: int | None
    weekly_hours: float
    capacity_relevant: bool
    active: bool


class ProjectRoleCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectRoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    active: bool | None = None


class ProjectRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    active: bool


class ProjectMembershipCreate(BaseModel):
    person_id: int
    project_role_id: int


class ProjectMembershipOut(BaseModel):
    id: int
    project_id: int
    person_id: int
    person_name: str
    project_role_id: int
    project_role_name: str


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None


class AppRoleCreate(BaseModel):
    name: str
    description: str | None = None


class AppRoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class AppRoleOut(BaseModel):
    id: int
    name: str
    description: str | None
    permissions: list[str] = []


# ---------------------------------------------------------------------------
# Controlling-Erweiterung: Auslastung & KPIs (siehe CONCEPT.md Abschnitt 6/9, Schritt 9).
# Reine Aggregation aus Person/ResourceAssignment bzw. Gap-Analyse/Risk/Decision - keine
# neuen Tabellen. MemberUtilizationOut ist mit dem Legacy Cutover (Phase 26.9) durch
# PortfolioUtilizationEntry ersetzt (periodenscharf, Personen-basiert).
# ---------------------------------------------------------------------------


class PortfolioUtilizationEntry(BaseModel):
    person_id: int
    person_name: str
    team_id: int | None
    team_name: str | None
    jira_account_id: str | None
    weekly_hours: float
    kapazitaet_fte: float
    zugeordnet_fte: float
    auslastung_pct: float | None  # None = keine Kapazität hinterlegt (weekly_hours = 0)


class KpiSummary(BaseModel):
    anzahl_projekte_aktiv: int
    anzahl_projekte_gruen: int
    anzahl_projekte_gelb: int
    anzahl_projekte_rot: int
    anzahl_projekte_grau: int
    durchschnittliche_auslastung_pct: float | None
    offene_risiken_gesamt: int
    offene_entscheidungen_gesamt: int
    offene_aufgaben_gesamt: int


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


# ---------------------------------------------------------------------------
# GAP Engine (Phase 21, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt 21/22). Verbindet
# Projektplanung (PlanPhase/Milestone, Phase 17) + Kapazitätsplanung (ResourceDemand, Phase
# 19; Available Capacity, Phase 20) + Ist-Daten (Jira, bestehend) + Forecast zu den in der
# Master-MD Abschnitt 22 definierten GAP-Arten. Rein berechnete Endpunkte, keine neuen
# Tabellen - die bestehende Soll-/Ist-Logik oben (GapAnalysis) wird wiederverwendet, nicht
# ersetzt (Effort Gap).
# ---------------------------------------------------------------------------


class CapacityGapOut(BaseModel):
    """Demand/Capacity Gap = Available Capacity - Resource Demand (Master-MD Abschnitt 22).
    Portfolioweit über alle kapazitätsrelevanten Personen, da es keine Person<->ResourceRole-
    Zuordnung im Datenmodell gibt (siehe CONCEPT.md Abschnitt 12.3) - resource_role_id
    filtert nur die Bedarfsseite, nicht die Kapazitätsseite."""

    period: str
    resource_role_id: int | None
    demand_fte: float
    available_fte: float
    capacity_gap_fte: float
    persons_considered: int


class ScheduleGapEntry(BaseModel):
    """Schedule Gap (live, nicht auf einen BaselineSnapshot angewiesen - siehe Phase 18 für
    die Snapshot-basierte Variante). Deckt sowohl 'Baseline vs Forecast' als auch 'Forecast
    vs Actual' ab (Master-MD Abschnitt 21)."""

    entity_type: str  # "plan_phase" | "milestone"
    entity_id: int
    label: str | None
    baseline_date: str | None
    forecast_date: str | None
    actual_date: str | None
    baseline_vs_forecast_days: int | None
    forecast_vs_actual_days: int | None


class ProgressGapEntry(BaseModel):
    """Progress Gap = Expected Progress - Actual Progress, in Prozentpunkten (Master-MD
    Abschnitt 22). Expected Progress wird aus dem zeitlichen Anteil zwischen Start und Ende
    (Forecast, ersatzweise Baseline) bis heute berechnet."""

    plan_phase_id: int
    label: str
    expected_progress_pct: float | None
    actual_progress_pct: float | None
    progress_gap_pp: float | None


class UtilizationGapOut(BaseModel):
    """Utilization Gap = tatsächliche/erwartete Auslastung ggü. Ziel-Auslastung (Master-MD
    Abschnitt 22). target_pct ist fix 100% (volle Auslastung der verfügbaren Kapazität) -
    keine konfigurierbare Ziel-Auslastung in diesem Durchgang."""

    person_id: int
    period: str
    assigned_fte: float
    available_fte: float
    utilization_pct: float | None
    target_pct: float
    utilization_gap_pp: float | None


class ProjectGapsOut(BaseModel):
    """Bündelt Effort-/Schedule-/Progress-Gap eines Projekts an einer Stelle - einfache Form
    des in Master-MD Abschnitt 21/25 geforderten Drill-downs. Der volle hierarchische
    Portfolio-Drill-down (Abschnitt 52) bleibt Controlling (Phase 22/23)."""

    project_id: int
    effort: GapAnalysis
    schedule: list[ScheduleGapEntry]
    progress: list[ProgressGapEntry]


# ---------------------------------------------------------------------------
# Project Control & Health (Phase 22, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt
# 6/49/50). Mehrdimensionales Project Health auf Basis der GAP-Engine (Phase 21) und
# bestehender Daten (Blocker/Risk/Milestone), mit konfigurierbaren Schwellwerten
# (HealthThreshold). Rein berechnete Endpunkte bis auf die Schwellwert-Konfiguration selbst.
# ---------------------------------------------------------------------------


class HealthThresholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric: str
    yellow: float
    red: float


class HealthThresholdUpdate(BaseModel):
    yellow: float
    red: float


class HealthDimension(BaseModel):
    """Eine Project-Health-Dimension. value ist der zugrunde liegende 'badness'-Wert (nicht-
    negativ, je größer desto schlechter - z.B. Verzugstage, fehlende FTE, Risiko-Score),
    None wenn keine belastbare Datenbasis vorliegt (status dann 'grau')."""

    status: str  # "gruen" | "gelb" | "rot" | "grau"
    value: float | None
    explanation: str


class ProjectHealthOut(BaseModel):
    project_id: int
    project_name: str
    overall: HealthDimension
    schedule: HealthDimension
    capacity: HealthDimension
    effort: HealthDimension
    progress: HealthDimension
    risks: HealthDimension
    blockers: HealthDimension
    milestones: HealthDimension
    customer: HealthDimension


class CockpitMilestoneEntry(BaseModel):
    id: int
    name: str
    baseline_date: str | None
    forecast_date: str | None
    actual_date: str | None
    status: str


class CockpitCapacity(BaseModel):
    period: str
    demand_fte: float
    assigned_fte: float
    allocation_gap_fte: float


class CockpitBlockers(BaseModel):
    open_total: int
    customer: int
    internal: int
    third_party: int
    unknown: int


class CockpitTasks(BaseModel):
    open_total: int
    overdue: int


class ProjectControlCockpitOut(BaseModel):
    """Project Control Cockpit (Master-MD Abschnitt 6) - bündelt Health, aktuelle Phase,
    Forecast-Ende, Milestones, Kapazität, Blocker- und Aufgaben-Zusammenfassung sowie
    projektbezogene Tags ('Aktuelle Themen') an einer Stelle."""

    project_id: int
    project_name: str
    kunde: str | None
    projektleiter: str | None
    health: ProjectHealthOut
    current_phase: str | None
    forecast_end: str | None
    milestones: list[CockpitMilestoneEntry]
    capacity: CockpitCapacity
    blockers: CockpitBlockers
    tasks: CockpitTasks
    tags: list[str]


# ---------------------------------------------------------------------------
# Controlling & Capacity Intelligence (Phase 23, siehe CONCEPT.md Abschnitt 12 / Master-MD
# Abschnitt 23). Portfolioweite Aggregation der bereits bestehenden GAP-/Health-/Capacity-
# Berechnungen (Phase 19-22) über alle Projekte hinweg - Komposition statt Duplikation:
# bestehende Item-Schemas werden um project_id/project_name ergänzt, nicht neu gebaut.
# ---------------------------------------------------------------------------


class PortfolioAllocationGapEntry(BaseModel):
    project_id: int
    project_name: str
    resource_demand_id: int
    resource_role_id: int
    resource_role_name: str
    period: str
    fte: float
    assigned_fte: float
    allocation_gap: float


class PortfolioScheduleGapEntry(BaseModel):
    project_id: int
    project_name: str
    entry: ScheduleGapEntry


class PortfolioProgressGapEntry(BaseModel):
    project_id: int
    project_name: str
    entry: ProgressGapEntry


class PortfolioBaselineDeviationEntry(BaseModel):
    project_id: int
    project_name: str
    baseline_id: int
    baseline_name: str
    deviation: BaselineDeviationOut


class BlockerPortfolioEntry(BaseModel):
    """Bewusst schlank (kein tags/documents wie BlockerOut) - vermeidet N+1-Abfragen bei
    einer projektübergreifenden Liste, analog zu CockpitMilestoneEntry (Phase 22)."""

    project_id: int
    project_name: str
    id: int
    title: str
    status: str
    severity: str
    caused_by_party: str
    waiting_for_party: str
    active_since: str | None


class MilestonePortfolioEntry(BaseModel):
    project_id: int
    project_name: str
    id: int
    name: str
    baseline_date: str | None
    forecast_date: str | None
    actual_date: str | None
    status: str


class RoleAnalysisEntry(BaseModel):
    resource_role_id: int
    resource_role_name: str
    period: str
    demand_fte: float
    assigned_fte: float
    gap_fte: float


# ---------------------------------------------------------------------------
# PlanPhase Detail & Metriken (P3, siehe CONCEPT.md Abschnitt 12 / Master-MD Abschnitt
# 8/9/17). Aggregierte Detailansicht einer PlanPhase mit eingebetteten phasenbezogenen
# Entitäten (Comment/Task/Blocker/Decision/ResourceDemand) und Rohmetriken. Bewusst am Ende
# der Schemas-Datei platziert, da PlanPhaseDetail auf Out-Schemas verweist, die erst später
# im Modul definiert sind (CommentOut/ResourceDemandOut) - so bleiben die Forward-Refs zur
# Laufzeit auflösbar, ohne from __future__ import annotations zu benötigen.
# ---------------------------------------------------------------------------


class ReconciliationOut(BaseModel):
    headline_fte: float | None
    breakdown_fte: float | None
    open_fte: float | None


class PhaseMetricsOut(BaseModel):
    # Rohmetriken nur - keine control_status/Ampel-Logik (folgt erst nach BD-3).
    time_progress_pct: float | None
    plan_hours: float | None
    effort_consumption_pct: float | None  # BD-1: aktuell immer None (keine Ist-Stunden-Quelle)
    ist_hours: float | None  # BD-1: aktuell immer None
    reconciliation: ReconciliationOut


class PlanPhaseAssignedPersonOut(BaseModel):
    # Eine Zeile je Person (über alle ResourceDemands dieser Phase aggregiert - Abschnitt
    # 6b.10), nicht je ResourceAssignment-Datensatz.
    person_id: int
    person_name: str
    fte: float


class PlanPhaseAssignmentSummaryOut(BaseModel):
    """Bedarf/Besetzt/Offen einer Leaf-PlanPhase (P18/B-4, CONCEPT.md Abschnitt 6b.10) - UI-
    Vokabular: "Geplanter Ressourcenbedarf"/"Besetzung"/"Offen", NICHT "ResourceDemand". Vor
    P19.2 nur über einen eigenen Endpoint (GET .../assignment-summary) erreichbar - ab P19.2
    zusätzlich additiv in PlanPhaseDetail eingebettet (siehe dort), der eigenständige Endpoint
    bleibt unverändert bestehen (andere Aufrufer)."""

    plan_phase_id: int
    plan_fte: float | None
    assigned_fte: float
    open_fte: float | None
    assignments: list[PlanPhaseAssignedPersonOut]


class PlanPhaseDetail(PlanPhaseOut):
    # Aggregierte Detailansicht einer PlanPhase. Eingebettet werden Entitäten mit
    # plan_phase_id-FK (Comment/Task/Blocker/Decision/ResourceDemand/Milestone).
    # BaselineSnapshot wird weiterhin bewusst NICHT eingebettet (kein Snapshot-vs-Snapshot-
    # Vergleich hier, siehe P19.6 - der Planstand-Vergleich läuft client-seitig gegen den
    # bestehenden /baselines/{id}/deviations-Endpoint).
    comments: list[CommentOut] = []
    tasks: list[TaskOut] = []
    blockers: list[BlockerOut] = []
    decisions: list[DecisionOut] = []
    resource_demands: list[ResourceDemandOut] = []
    # P19.5 (additiv): Milestones dieser Phase (plan_phase_id-FK, seit P18/B-7), damit der
    # PlanPhase-Workspace sie ohne einen zusätzlichen Round-Trip anzeigen kann (Gap 2 aus
    # P19_PLANPHASE_WORKSPACE_UX_AUDIT.md). Bewusst nicht rekursiv (nur diese Phase selbst,
    # keine Nachfahren-Milestones).
    milestones: list[MilestoneOut] = []
    metrics: PhaseMetricsOut
    # P18/B-3: direkte Kinder (nicht rekursiv) - für die Baum-UI (B-6). Leer bei einer Leaf.
    children: list[PlanPhaseOut] = []
    # P19.2 (Kapazität-Tab Round-Trip-Reduktion): dieselbe Bedarf/Besetzt/Offen-Auswertung wie
    # GET .../assignment-summary, additiv mitgeliefert, damit der Kapazität-Tab sie nicht mehr
    # separat nachladen muss. Der eigenständige Endpoint bleibt bestehen (andere Aufrufer).
    assignment_summary: PlanPhaseAssignmentSummaryOut


class PlanPhaseReparentChildrenRequest(BaseModel):
    # None = Kinder werden auf Top-Level verschoben (Abschnitt 6b.9).
    new_parent_phase_id: int | None = None


class PlanPhaseReparentChildrenResult(BaseModel):
    moved_count: int
    children: list[PlanPhaseOut]


class PlanPhaseSubtreeImpactOut(BaseModel):
    plan_phase_id: int
    phase_type: str
    descendant_phase_count: int
    comments_affected: int
    tasks_affected: int
    blockers_affected: int
    decisions_affected: int
    milestones_affected: int
    documents_affected: int
    resource_demands_affected: int
    resource_assignments_affected: int


class PlanPhaseDeleteSubtreeRequest(BaseModel):
    # Starke Bestätigung (BD-11, CLOSED): beide Werte müssen mit der tatsächlichen Phase/
    # Nachfahrenzahl aus GET .../subtree-impact übereinstimmen, sonst 422 (Abschnitt 6b.9).
    confirm_phase_type: str
    confirm_descendant_count: int


class PlanPhaseAssignPersonRequest(BaseModel):
    person_id: int
    fte: float
