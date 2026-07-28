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
  kommentar: Comment | null;
}
