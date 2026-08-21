export type PhaseCode = "p" | "k" | "t" | "s" | "g" | "?";

export const PHASE_LABELS: Record<PhaseCode, string> = {
  p: "Pflichtenheft",
  k: "Konfiguration",
  t: "Test",
  s: "Schulung",
  g: "GoLive",
  "?": "Meilenstein",
};

export const PHASE_COLORS: Record<PhaseCode, string> = {
  p: "#0A55B9",
  k: "#288CE1",
  t: "#C355D7",
  s: "#F2A71B",
  g: "#CD145A",
  "?": "#002F5E",
};

export type ProjectStatus = "aktiv" | "on_hold" | "abgeschlossen" | "archiviert";

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  aktiv: "Aktiv",
  on_hold: "On Hold",
  abgeschlossen: "Abgeschlossen",
  archiviert: "Archiviert",
};

export interface ProjectSummary {
  id: number;
  name: string;
  kunde: string | null;
  start_monat: string;
  anzahl_monate: number;
  reihenfolge: number;
  status: ProjectStatus;
  projektleiter_person_id: number | null;
  monate: string[];
}

export interface SubprojectDetail {
  id: number;
  name: string;
  reihenfolge: number;
}

export interface SubprojectListItem {
  id: number;
  name: string;
  project_id: number;
  project_name: string;
}

export interface ProjectDetail extends ProjectSummary {
  jira_component: string | null;
  jira_project_key: string | null;
  ist: Record<string, number>;
  subprojects: SubprojectDetail[];
}

export interface Team {
  id: number;
  name: string;
}

export interface JiraStatus {
  configured: boolean;
  base_url: string | null;
  tempo_configured: boolean;
  hinweis: string;
}

export interface JiraUnknownAuthor {
  account_id: string;
  display_name: string;
}

export interface JiraSyncResultItem {
  project_id: number;
  project_name: string;
  jira_component: string;
  worklogs_synced: number;
  unzugeordnete_buchungen: number;
  unbekannte_beispiele: JiraUnknownAuthor[];
  error: string | null;
}

export interface JiraSyncResult {
  status: string;
  ergebnisse: JiraSyncResultItem[];
}

export interface JiraAccountMatch {
  account_id: string;
  display_name: string;
  email: string | null;
}

export interface UnassignedAuthor {
  account_id: string;
  display_name: string;
}

export type JiraProjectStatus = "aktiv" | "on_hold" | "beendet";

export const JIRA_PROJECT_STATUS_LABELS: Record<JiraProjectStatus, string> = {
  aktiv: "Aktiv",
  on_hold: "On Hold",
  beendet: "Beendet",
};

export interface JiraProject {
  key: string;
  name: string;
  relevant: boolean;
  status: JiraProjectStatus;
}

export interface JiraComponent {
  id: string;
  name: string;
}

export type GapStatus = "gruen" | "gelb" | "rot" | "grau";

export interface GapAnalysis {
  project_id: number;
  project_name: string;
  monate: string[];
  soll: Record<string, number>;
  ist: Record<string, number>;
  gap: Record<string, number>;
  hochrechnung: Record<string, number>;
  soll_gesamt: number;
  projiziert_gesamt: number;
  gap_gesamt: number;
  gap_pct: number | null;
  status: GapStatus;
}

export interface ForecastSummary {
  project_id: number;
  project_name: string;
  soll_gesamt: number;
  projiziert_gesamt: number;
  gap_gesamt: number;
  gap_pct: number | null;
  status: GapStatus;
}

export interface Comment {
  id: number;
  project_id: number;
  subproject_id: number | null;
  monat: string | null;
  phase_code: PhaseCode | null;
  text: string;
  erstellt_am: string;
  tags: string[];
  documents: Document[];
}

export interface PlanHistoryEntry {
  id: number;
  subproject_id: number | null;
  bereich: "phase" | "fte" | "stammdaten";
  monat: string | null;
  feld: string;
  alter_wert: string | null;
  neuer_wert: string | null;
  geaendert_am: string;
  batch_id: string | null;
  kommentar: Comment | null;
}

// entity_type-Vokabular, geteilt zwischen Tags und Document-Verknüpfungen (siehe
// CONCEPT.md Abschnitt 6a). "document" nur für Tags relevant. "plan_phase"/"milestone" seit
// Phase 26.2 genutzt, "blocker" seit Phase 26.4 - Backend unterstützt alle drei bereits seit
// Phase 16/17 (entity_links-Registry).
export type EntityType = "comment" | "decision" | "risk" | "meeting_minutes" | "task" | "document" | "plan_phase" | "milestone" | "blocker" | "baseline_snapshot";

export interface DocumentUsage {
  entity_type: string;
  entity_id: number;
  label: string;
}

export interface Document {
  id: number;
  project_id: number;
  dateiname: string;
  mimetype: string | null;
  groesse_bytes: number;
  hochgeladen_von: string | null;
  hochgeladen_am: string;
  tags: string[];
  used_in: DocumentUsage[];
}

export interface DocumentLink {
  id: number;
  document_id: number;
  entity_type: string;
  entity_id: number;
  erstellt_am: string;
}

export interface Tag {
  id: number;
  name: string;
}

export type DecisionStatus = "offen" | "entschieden" | "verworfen";

export const DECISION_STATUS_LABELS: Record<DecisionStatus, string> = {
  offen: "Offen",
  entschieden: "Entschieden",
  verworfen: "Verworfen",
};

export interface Decision {
  id: number;
  project_id: number;
  titel: string;
  beschreibung: string | null;
  status: DecisionStatus;
  entschieden_von_person_id: number | null;
  entschieden_am: string | null;
  erstellt_am: string;
  tags: string[];
  documents: Document[];
}

export type RiskLevel = "niedrig" | "mittel" | "hoch";

export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  niedrig: "Niedrig",
  mittel: "Mittel",
  hoch: "Hoch",
};

export type RiskStatus = "offen" | "in_bearbeitung" | "geschlossen";

export const RISK_STATUS_LABELS: Record<RiskStatus, string> = {
  offen: "Offen",
  in_bearbeitung: "In Bearbeitung",
  geschlossen: "Geschlossen",
};

export interface Risk {
  id: number;
  project_id: number;
  titel: string;
  beschreibung: string | null;
  wahrscheinlichkeit: RiskLevel;
  auswirkung: RiskLevel;
  status: RiskStatus;
  owner_person_id: number | null;
  faellig_am: string | null;
  erstellt_am: string;
  aktualisiert_am: string;
  tags: string[];
  documents: Document[];
}

// Ersetzt MemberUtilization (Phase 26.9 Legacy Cutover) - Person/ResourceProfile statt
// TeamMember, periodenscharf statt statisch (siehe backend/app/capacity_calc.py).
export interface PortfolioUtilizationEntry {
  person_id: number;
  person_name: string;
  team_id: number | null;
  team_name: string | null;
  jira_account_id: string | null;
  weekly_hours: number;
  kapazitaet_fte: number;
  zugeordnet_fte: number;
  auslastung_pct: number | null;
}

export interface ResourceProfile {
  id: number;
  person_id: number;
  team_id: number | null;
  weekly_hours: number;
  capacity_relevant: boolean;
  active: boolean;
}

export interface KpiSummary {
  anzahl_projekte_aktiv: number;
  anzahl_projekte_gruen: number;
  anzahl_projekte_gelb: number;
  anzahl_projekte_rot: number;
  anzahl_projekte_grau: number;
  durchschnittliche_auslastung_pct: number | null;
  offene_risiken_gesamt: number;
  offene_entscheidungen_gesamt: number;
  offene_aufgaben_gesamt: number;
}

export interface MeetingMinutes {
  id: number;
  project_id: number;
  titel: string;
  datum: string;
  teilnehmer: string | null;
  text: string;
  erstellt_am: string;
  tags: string[];
  documents: Document[];
}

export type TaskStatus = "offen" | "in_bearbeitung" | "erledigt";

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  offen: "Offen",
  in_bearbeitung: "In Bearbeitung",
  erledigt: "Erledigt",
};

export interface Task {
  id: number;
  project_id: number;
  titel: string;
  beschreibung: string | null;
  status: TaskStatus;
  zustaendig_person_id: number | null;
  faellig_am: string | null;
  erstellt_am: string;
  aktualisiert_am: string;
  tags: string[];
  documents: Document[];
}

// Phase 26.4: Blocker (Phase 16 der Zielarchitektur, backend/app/routers/communication.py) -
// caused_by_party/waiting_for_party trennen bewusst "wer hat verursacht" von "bei wem liegt
// aktuell der Ball".
export type BlockerParty = "INTERNAL" | "CUSTOMER" | "THIRD_PARTY" | "UNKNOWN";

export const BLOCKER_PARTY_LABELS: Record<BlockerParty, string> = {
  INTERNAL: "Intern",
  CUSTOMER: "Kunde",
  THIRD_PARTY: "Drittpartei",
  UNKNOWN: "Unbekannt",
};

export type BlockerStatus = "offen" | "in_bearbeitung" | "geloest";

export const BLOCKER_STATUS_LABELS: Record<BlockerStatus, string> = {
  offen: "Offen",
  in_bearbeitung: "In Bearbeitung",
  geloest: "Gelöst",
};

export type BlockerSeverity = "niedrig" | "mittel" | "hoch" | "kritisch";

export const BLOCKER_SEVERITY_LABELS: Record<BlockerSeverity, string> = {
  niedrig: "Niedrig",
  mittel: "Mittel",
  hoch: "Hoch",
  kritisch: "Kritisch",
};

export interface Blocker {
  id: number;
  project_id: number;
  title: string;
  description: string | null;
  status: BlockerStatus;
  severity: BlockerSeverity;
  active_since: string | null;
  caused_by_party: BlockerParty;
  waiting_for_party: BlockerParty;
  owner_person_id: number | null;
  owner_team_id: number | null;
  next_action: string | null;
  impact: string | null;
  erstellt_am: string;
  aktualisiert_am: string;
  tags: string[];
  documents: Document[];
}

// Phase 26.4: Activity Feed (Phase 16, backend/app/routers/communication.py) - reine
// chronologische Aggregation, keine neue Tabelle.
export interface ActivityItem {
  entity_type: EntityType;
  entity_id: number;
  label: string | null;
  timestamp: string;
  tags: string[];
}

// relation_type-Vokabular für EntityRelation (siehe backend/app/schemas.py). "resulted_in"
// wird für alle "aus diesem Objekt erstellt"-Aktionen verwendet (Phase 26.4) - deckt sowohl
// "Diskussion resultierte in Entscheidung" als auch "Blocker resultierte in Folgeaufgabe".
export type RelationType =
  | "related_to"
  | "resulted_in"
  | "based_on"
  | "follow_up"
  | "blocks"
  | "resolves"
  | "depends_on"
  | "supports"
  | "caused_by";

export interface EntityRelation {
  id: number;
  source_entity_type: string;
  source_entity_id: number;
  target_entity_type: string;
  target_entity_id: number;
  relation_type: RelationType;
  created_at: string;
  created_by_person_id: number | null;
}

// Phase 26.6: Project Control Cockpit (Phase 22 der Zielarchitektur,
// backend/app/routers/health.py) - bündelt Health, aktuelle Phase, Forecast-Ende,
// Milestones, Kapazität, Blocker-/Aufgaben-Zusammenfassung und Tags an einer Stelle.
export type HealthStatus = "gruen" | "gelb" | "rot" | "grau";

export const HEALTH_STATUS_COLOR: Record<HealthStatus, string> = {
  gruen: "var(--gruen)",
  gelb: "var(--gelb)",
  rot: "var(--rot)",
  grau: "var(--grau)",
};

export interface HealthDimension {
  status: HealthStatus;
  value: number | null;
  explanation: string;
}

export interface ProjectHealth {
  project_id: number;
  project_name: string;
  overall: HealthDimension;
  schedule: HealthDimension;
  capacity: HealthDimension;
  effort: HealthDimension;
  progress: HealthDimension;
  risks: HealthDimension;
  blockers: HealthDimension;
  milestones: HealthDimension;
  customer: HealthDimension;
}

export const HEALTH_DIMENSION_LABELS: Record<keyof Omit<ProjectHealth, "project_id" | "project_name">, string> = {
  overall: "Gesamt",
  schedule: "Termine",
  capacity: "Kapazität",
  effort: "Aufwand",
  progress: "Fortschritt",
  risks: "Risiken",
  blockers: "Blocker",
  milestones: "Milestones",
  customer: "Kunde",
};

export interface CockpitMilestoneEntry {
  id: number;
  name: string;
  baseline_date: string | null;
  forecast_date: string | null;
  actual_date: string | null;
  status: string;
}

export interface CockpitCapacity {
  period: string;
  demand_fte: number;
  assigned_fte: number;
  allocation_gap_fte: number;
}

export interface CockpitBlockers {
  open_total: number;
  customer: number;
  internal: number;
  third_party: number;
  unknown: number;
}

export interface CockpitTasks {
  open_total: number;
  overdue: number;
}

export interface ProjectControlCockpit {
  project_id: number;
  project_name: string;
  kunde: string | null;
  projektleiter: string | null;
  health: ProjectHealth;
  current_phase: string | null;
  forecast_end: string | null;
  milestones: CockpitMilestoneEntry[];
  capacity: CockpitCapacity;
  blockers: CockpitBlockers;
  tasks: CockpitTasks;
  tags: string[];
}

// Phase 26.7: Controlling & Capacity Intelligence (Phase 23 der Zielarchitektur,
// backend/app/routers/controlling.py) - portfolioweite Aggregation der bestehenden GAP-/
// Health-Berechnungen, bisher komplett ungenutzt.
export interface PortfolioAllocationGapEntry {
  project_id: number;
  project_name: string;
  resource_demand_id: number;
  resource_role_id: number;
  resource_role_name: string;
  period: string;
  fte: number;
  assigned_fte: number;
  allocation_gap: number;
}

// Phase 26.5: Tag-Dossiers (Phase 24 der Zielarchitektur, backend/app/routers/knowledge.py) -
// ein Tag oder eine Kombination ("#Kunde + #GoLive") wird zu einem dynamischen Dossier.
export interface KnowledgeEntity {
  entity_type: EntityType;
  entity_id: number;
  project_id: number | null;
  label: string | null;
  tags: string[];
}

export interface TagDossier {
  tags: string[];
  mode: "and" | "or";
  project_id: number | null;
  counts: Record<string, number>;
  entities: KnowledgeEntity[];
  activity: ActivityItem[];
}

// Phase 26.2: PlanPhase/Milestone (Phase 17 der Zielarchitektur, backend/app/routers/planning.py)
// - Zielarchitektur-native Entitäten, ersetzen ab jetzt das alte Gantt/FTE-Raster als
// Bedienoberfläche. status ist im Backend bewusst Freitext (kein Enum) - die folgenden
// Wertelisten sind reine Frontend-Konvention, exakt aus den Code-Kommentaren in
// backend/app/models.py übernommen (PlanPhase und Milestone haben je eigene Vokabulare).
export type PlanPhaseStatus = "geplant" | "laufend" | "abgeschlossen" | "verzoegert";

export const PLAN_PHASE_STATUS_LABELS: Record<PlanPhaseStatus, string> = {
  geplant: "Geplant",
  laufend: "Laufend",
  abgeschlossen: "Abgeschlossen",
  verzoegert: "Verzögert",
};

// Vorschläge für phase_type (Freitext im Backend) - aus den bisherigen Gantt-Phasencodes
// übernommen, damit die neue Ansicht für Nutzer:innen des alten Gantt vertraut bleibt.
export const PLAN_PHASE_TYPE_SUGGESTIONS = ["Pflichtenheft", "Konfiguration", "Test", "Schulung", "GoLive"];

export interface PlanPhase {
  id: number;
  project_id: number;
  subproject_id: number | null;
  phase_type: string;
  baseline_start: string | null;
  baseline_end: string | null;
  forecast_start: string | null;
  forecast_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  status: PlanPhaseStatus;
  progress: number | null;
  owner_person_id: number | null;
  owner_team_id: number | null;
  erstellt_am: string;
  aktualisiert_am: string;
  tags: string[];
  documents: Document[];
}

export type MilestoneStatus = "geplant" | "gefaehrdet" | "erreicht" | "verpasst";

export const MILESTONE_STATUS_LABELS: Record<MilestoneStatus, string> = {
  geplant: "Geplant",
  gefaehrdet: "Gefährdet",
  erreicht: "Erreicht",
  verpasst: "Verpasst",
};

export interface Milestone {
  id: number;
  project_id: number;
  subproject_id: number | null;
  name: string;
  baseline_date: string | null;
  forecast_date: string | null;
  actual_date: string | null;
  status: MilestoneStatus;
  owner_person_id: number | null;
  owner_team_id: number | null;
  erstellt_am: string;
  aktualisiert_am: string;
  tags: string[];
  documents: Document[];
}

export interface BaselineSnapshotSummary {
  id: number;
  project_id: number;
  name: string;
  created_at: string;
  created_by_person_id: number | null;
  entry_count: number;
}

export interface BaselineEntry {
  id: number;
  entity_type: string;
  entity_id: number;
  field: string;
  value: string | null;
}

export interface BaselineSnapshot {
  id: number;
  project_id: number;
  name: string;
  created_at: string;
  created_by_person_id: number | null;
  entries: BaselineEntry[];
}

// Phase 26.3: ResourceDemand/ResourceAssignment (Phase 19 der Zielarchitektur,
// backend/app/routers/capacity.py) - "Demand ≠ Assignment": Bedarf wird zunächst
// unabhängig von Personen geplant, ResourceAssignment ordnet ihn danach zu.
export type CommitmentLevel = "FIX" | "TENTATIVE" | "SCENARIO";

export const COMMITMENT_LEVEL_LABELS: Record<CommitmentLevel, string> = {
  FIX: "Fix",
  TENTATIVE: "Vorläufig",
  SCENARIO: "Szenario",
};

export interface ResourceDemand {
  id: number;
  project_id: number;
  plan_phase_id: number | null;
  resource_role_id: number;
  resource_role_name: string;
  period: string;
  fte: number;
  commitment_level: CommitmentLevel;
  erstellt_am: string;
  aktualisiert_am: string;
  assigned_fte: number;
  allocation_gap: number;
}

export interface ResourceAssignment {
  id: number;
  resource_demand_id: number;
  person_id: number;
  person_name: string;
  fte: number;
  erstellt_am: string;
  aktualisiert_am: string;
}

// Keine Person<->ResourceRole-Verknüpfung im Datenmodell (Rolle/Skill sind getrennte
// Dimensionen) - Kandidaten werden nur nach freier Kapazität gefiltert, skills sind rein
// informativ.
export interface CandidatePerson {
  person_id: number;
  display_name: string;
  available_fte: number;
  skills: string[];
}

// Fachliche Administration (Phase 25)
export interface AdminPerson { id: number; external_id: string | null; display_name: string; email: string | null; source: "LOCAL" | "ENTERPRISE_PLATFORM"; active: boolean; jira_account_id: string | null }
// Phase 26.1: Person ist auch außerhalb der Administration die Grundlage für den
// projektweiten PersonPicker (Projektleiter/Owner-Felder/Projektteam) - gleiche Form wie
// AdminPerson, eigener Alias statt Import aus dem Administration-Kontext.
export type Person = AdminPerson;

export interface ProjectMembership {
  id: number;
  project_id: number;
  person_id: number;
  person_name: string;
  project_role_id: number;
  project_role_name: string;
}

export interface AdminProjectRole { id: number; name: string; description: string | null; active: boolean }
export interface AdminPermission { id: number; name: string; description: string | null }
export interface AdminAppRole { id: number; name: string; description: string | null; permissions: string[] }
export interface AdminResourceRole { id: number; name: string; description: string | null; active: boolean }
export interface AdminSkill { id: number; name: string; category: string | null; active: boolean }
export interface AdminTagCategory { id: number; name: string; description: string | null }
export interface AdminTag { id: number; name: string; category_id: number | null; description: string | null; color: string | null; active: boolean; ai_relevant: boolean; ai_description: string | null; synonyms: string[] }
export interface AdminHealthThreshold { metric: string; yellow: number; red: number }
export interface AdminCapacityCalendar { id: number; name: string; description: string | null; active: boolean }
