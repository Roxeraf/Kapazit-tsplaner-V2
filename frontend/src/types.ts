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

export interface ProjectSummary {
  id: number;
  name: string;
  kunde: string | null;
  start_monat: string;
  anzahl_monate: number;
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
  ist: Record<string, number>;
  subprojects: SubprojectDetail[];
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
  subproject_id: number;
  subproject_name: string;
  project_name: string;
  anteil: number;
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
  hinweis: string;
}

export interface JiraSyncResultItem {
  project_id: number;
  project_name: string;
  jira_component: string;
  worklogs_synced: number;
  unzugeordnete_buchungen: number;
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
