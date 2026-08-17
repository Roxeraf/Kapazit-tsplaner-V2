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
  projektleiter: string | null;
  monate: string[];
}

export interface SubprojectDetail {
  id: number;
  name: string;
  reihenfolge: number;
  phasen: Record<string, PhaseCode[]>;
  fte: Record<string, number>;
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
  phasen: Record<string, PhaseCode[]>;
  fte: Record<string, number>;
  aus_teilprojekten: boolean;
  ist: Record<string, number>;
  subprojects: SubprojectDetail[];
  team_assignments: ProjectAssignment[];
}

export interface Team {
  id: number;
  name: string;
}

export interface TeamWithMembers extends Team {
  members: TeamMember[];
}

export interface Assignment {
  id: number;
  project_id: number;
  project_name: string;
  fte: number;
}

export interface ProjectAssignment {
  id: number;
  team_member_id: number;
  member_name: string;
  fte: number;
}

export interface TeamMember {
  id: number;
  name: string;
  jira_account_id: string | null;
  wochenstunden: number;
  team_id: number | null;
  team_name: string | null;
  assignments: Assignment[];
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
// CONCEPT.md Abschnitt 6a). "document" nur für Tags relevant.
export type EntityType = "comment" | "decision" | "risk" | "meeting_minutes" | "task" | "document" | "blocker" | "plan_phase" | "milestone";

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
  entschieden_von: string | null;
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
  owner: string | null;
  faellig_am: string | null;
  erstellt_am: string;
  aktualisiert_am: string;
  tags: string[];
  documents: Document[];
}

export interface MemberUtilization {
  member_id: number;
  member_name: string;
  team_id: number | null;
  team_name: string | null;
  kapazitaet_fte: number;
  zugeordnet_fte: number;
  auslastung_pct: number | null;
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
  zustaendig: string | null;
  faellig_am: string | null;
  erstellt_am: string;
  aktualisiert_am: string;
  tags: string[];
  documents: Document[];
}

// Fachliche Administration (Phase 25)
export interface AdminPerson { id: number; external_id: string | null; display_name: string; email: string | null; source: "LOCAL" | "ENTERPRISE_PLATFORM"; active: boolean }
export interface AdminProjectRole { id: number; name: string; description: string | null; active: boolean }
export interface AdminPermission { id: number; name: string; description: string | null }
export interface AdminAppRole { id: number; name: string; description: string | null; permissions: string[] }
export interface AdminResourceRole { id: number; name: string; description: string | null; active: boolean }
export interface AdminSkill { id: number; name: string; category: string | null; active: boolean }
export interface AdminTagCategory { id: number; name: string; description: string | null }
export interface AdminTag { id: number; name: string; category_id: number | null; description: string | null; color: string | null; active: boolean; ai_relevant: boolean; ai_description: string | null; synonyms: string[] }
export interface AdminHealthThreshold { metric: string; yellow: number; red: number }
export interface AdminCapacityCalendar { id: number; name: string; description: string | null; active: boolean }
export interface AiReadinessMetric { key: string; value: number | string | boolean; unit: string | null }
export interface AiReadinessCheck { key: string; label: string; status: "READY" | "PARTIAL" | "BLOCKED"; evidence: string; recommendation: string | null; metrics: AiReadinessMetric[] }
export interface AiReadinessReport { phase: number; overall_status: "READY" | "PARTIAL" | "BLOCKED"; generated_at: string; productive_agent_enabled: boolean; checks: AiReadinessCheck[]; blockers: string[] }
