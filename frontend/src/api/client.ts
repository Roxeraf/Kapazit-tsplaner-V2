import type {
  JiraAccountMatch,
  JiraComponent,
  JiraProject,
  JiraProjectStatus,
  JiraStatus,
  JiraSyncResult,
  ProjectDetail,
  ProjectSummary,
  SubprojectDetail,
  SubprojectListItem,
  Team,
  TeamMember,
  TeamWithMembers,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  listProjects: () => request<ProjectSummary[]>("/projects"),
  getProject: (id: number) => request<ProjectDetail>(`/projects/${id}`),
  createProject: (payload: {
    name: string;
    kunde?: string;
    start_monat: string;
    anzahl_monate: number;
  }) => request<ProjectDetail>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  updateProject: (
    projectId: number,
    payload: Partial<{
      name: string;
      kunde: string | null;
      start_monat: string;
      anzahl_monate: number;
      jira_component: string | null;
    }>,
  ) => request<ProjectDetail>(`/projects/${projectId}`, { method: "PUT", body: JSON.stringify(payload) }),
  createSubproject: (projectId: number, name: string, reihenfolge: number) =>
    request(`/projects/${projectId}/subprojects`, {
      method: "POST",
      body: JSON.stringify({ name, reihenfolge }),
    }),
  setProjectPhasen: (projectId: number, monat: string, codes: string[]) =>
    request<ProjectDetail>(`/projects/${projectId}/phasen`, {
      method: "PUT",
      body: JSON.stringify({ monat, codes }),
    }),
  setProjectFte: (projectId: number, monat: string, wert_soll: number) =>
    request<ProjectDetail>(`/projects/${projectId}/fte`, {
      method: "PUT",
      body: JSON.stringify({ monat, wert_soll }),
    }),
  setPhasen: (subprojectId: number, monat: string, codes: string[]) =>
    request(`/projects/subprojects/${subprojectId}/phasen`, {
      method: "PUT",
      body: JSON.stringify({ monat, codes }),
    }),
  setFte: (subprojectId: number, monat: string, wert_soll: number) =>
    request(`/projects/subprojects/${subprojectId}/fte`, {
      method: "PUT",
      body: JSON.stringify({ monat, wert_soll }),
    }),
  updateSubproject: (subprojectId: number, payload: { name?: string; reihenfolge?: number }) =>
    request<SubprojectDetail>(`/projects/subprojects/${subprojectId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  listAllSubprojects: () => request<SubprojectListItem[]>("/projects/subprojects/all"),
  exportPptxUrl: (projectId: number) => `${API_BASE}/projects/${projectId}/export/pptx`,
  exportPortfolioPptxUrl: () => `${API_BASE}/projects/export/pptx/portfolio`,

  // Team-Kapazität
  listTeams: () => request<TeamWithMembers[]>("/team"),
  createTeam: (name: string) =>
    request<Team>("/team/teams", { method: "POST", body: JSON.stringify({ name }) }),
  updateTeam: (teamId: number, payload: { name?: string }) =>
    request<Team>(`/team/teams/${teamId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTeam: (teamId: number) => request<void>(`/team/teams/${teamId}`, { method: "DELETE" }),
  createMember: (payload: {
    name: string;
    jira_account_id?: string | null;
    wochenstunden?: number;
    team_id?: number | null;
  }) => request<TeamMember>("/team/members", { method: "POST", body: JSON.stringify(payload) }),
  updateMember: (
    memberId: number,
    payload: Partial<{
      name: string;
      jira_account_id: string | null;
      wochenstunden: number;
      team_id: number | null;
    }>,
  ) => request<TeamMember>(`/team/members/${memberId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteMember: (memberId: number) => request<void>(`/team/members/${memberId}`, { method: "DELETE" }),
  createAssignment: (memberId: number, subprojectId: number, anteil: number) =>
    request<TeamMember>(`/team/members/${memberId}/assignments`, {
      method: "POST",
      body: JSON.stringify({ subproject_id: subprojectId, anteil }),
    }),
  deleteAssignment: (assignmentId: number) =>
    request<void>(`/team/assignments/${assignmentId}`, { method: "DELETE" }),

  // Jira-Ist-Integration
  jiraStatus: () => request<JiraStatus>("/jira/status"),
  jiraLookupAccount: (query: string) =>
    request<JiraAccountMatch[]>(`/jira/lookup-account?query=${encodeURIComponent(query)}`),
  jiraSync: (projectId?: number) =>
    request<JiraSyncResult>(`/jira/sync${projectId ? `?project_id=${projectId}` : ""}`, {
      method: "POST",
    }),
  jiraListProjects: (query?: string) =>
    request<JiraProject[]>(`/jira/projects${query ? `?query=${encodeURIComponent(query)}` : ""}`),
  jiraSetProject: (key: string, payload: { relevant: boolean; status: JiraProjectStatus }) =>
    request<JiraProject>(`/jira/projects/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  jiraListComponents: (key: string) =>
    request<JiraComponent[]>(`/jira/projects/${encodeURIComponent(key)}/components`),
  jiraListLabels: (key: string) => request<string[]>(`/jira/projects/${encodeURIComponent(key)}/labels`),
};
