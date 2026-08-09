import type {
  Comment,
  Document,
  DocumentLink,
  EntityType,
  ForecastSummary,
  GapAnalysis,
  JiraAccountMatch,
  JiraComponent,
  JiraProject,
  JiraProjectStatus,
  JiraStatus,
  JiraSyncResult,
  PlanHistoryEntry,
  ProjectDetail,
  ProjectStatus,
  ProjectSummary,
  SubprojectDetail,
  SubprojectListItem,
  Tag,
  Team,
  TeamMember,
  TeamWithMembers,
  UnassignedAuthor,
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

// Für multipart/form-data-Uploads: der generische request() setzt immer
// Content-Type: application/json, das würde den vom Browser gesetzten
// "multipart/form-data; boundary=..."-Header überschreiben.
async function requestForm<T>(path: string, formData: FormData, method = "POST"): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method, body: formData });
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
      status: ProjectStatus;
      projektleiter: string | null;
      kommentar_id: number | null;
      batch_id: string | null;
    }>,
  ) => request<ProjectDetail>(`/projects/${projectId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProject: (projectId: number) => request<void>(`/projects/${projectId}`, { method: "DELETE" }),
  reorderProjects: (projectIds: number[]) =>
    request<void>("/projects/reorder", { method: "PUT", body: JSON.stringify({ project_ids: projectIds }) }),
  createSubproject: (projectId: number, name: string, reihenfolge: number) =>
    request(`/projects/${projectId}/subprojects`, {
      method: "POST",
      body: JSON.stringify({ name, reihenfolge }),
    }),
  deleteSubproject: (subprojectId: number) =>
    request<void>(`/projects/subprojects/${subprojectId}`, { method: "DELETE" }),
  setProjectPhasen: (
    projectId: number,
    monat: string,
    codes: string[],
    kommentar_id?: number | null,
    batch_id?: string | null,
  ) =>
    request<ProjectDetail>(`/projects/${projectId}/phasen`, {
      method: "PUT",
      body: JSON.stringify({ monat, codes, kommentar_id, batch_id }),
    }),
  setProjectFte: (
    projectId: number,
    monat: string,
    wert_soll: number,
    kommentar_id?: number | null,
    batch_id?: string | null,
  ) =>
    request<ProjectDetail>(`/projects/${projectId}/fte`, {
      method: "PUT",
      body: JSON.stringify({ monat, wert_soll, kommentar_id, batch_id }),
    }),
  setPhasen: (
    subprojectId: number,
    monat: string,
    codes: string[],
    kommentar_id?: number | null,
    batch_id?: string | null,
  ) =>
    request(`/projects/subprojects/${subprojectId}/phasen`, {
      method: "PUT",
      body: JSON.stringify({ monat, codes, kommentar_id, batch_id }),
    }),
  setFte: (
    subprojectId: number,
    monat: string,
    wert_soll: number,
    kommentar_id?: number | null,
    batch_id?: string | null,
  ) =>
    request(`/projects/subprojects/${subprojectId}/fte`, {
      method: "PUT",
      body: JSON.stringify({ monat, wert_soll, kommentar_id, batch_id }),
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
  listMembers: () => request<TeamMember[]>("/team/members"),
  listUnassignedAuthors: () => request<UnassignedAuthor[]>("/team/unassigned-authors"),
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
  createAssignment: (memberId: number, projectId: number, fte: number) =>
    request<TeamMember>(`/team/members/${memberId}/assignments`, {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, fte }),
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

  // Gap-Analyse
  getGap: (teamId?: number) =>
    request<GapAnalysis[]>(`/gap${teamId ? `?team_id=${teamId}` : ""}`),
  getForecast: (teamId?: number) =>
    request<ForecastSummary[]>(`/forecast${teamId ? `?team_id=${teamId}` : ""}`),

  // Kommentare & Änderungshistorie
  createComment: (
    projectId: number,
    payload: {
      subproject_id?: number | null;
      monat?: string | null;
      phase_code?: string | null;
      text: string;
      tags?: string[];
    },
  ) => request<Comment>(`/projects/${projectId}/comments`, { method: "POST", body: JSON.stringify(payload) }),
  listComments: (projectId: number) => request<Comment[]>(`/projects/${projectId}/comments`),
  deleteComment: (commentId: number) => request<void>(`/projects/comments/${commentId}`, { method: "DELETE" }),
  getProjectHistory: (projectId: number) => request<PlanHistoryEntry[]>(`/projects/${projectId}/history`),
  getSubprojectHistory: (subprojectId: number) =>
    request<PlanHistoryEntry[]>(`/projects/subprojects/${subprojectId}/history`),

  // Zentrale Dokumentenablage & Tags (siehe CONCEPT.md Abschnitt 6a)
  uploadDocument: (
    projectId: number,
    file: File,
    options?: { entityType?: EntityType; entityId?: number; tags?: string[]; hochgeladenVon?: string },
  ) => {
    const form = new FormData();
    form.append("file", file);
    if (options?.tags && options.tags.length > 0) form.append("tags", options.tags.join(","));
    if (options?.entityType) form.append("entity_type", options.entityType);
    if (options?.entityId !== undefined) form.append("entity_id", String(options.entityId));
    if (options?.hochgeladenVon) form.append("hochgeladen_von", options.hochgeladenVon);
    return requestForm<Document>(`/projects/${projectId}/documents`, form);
  },
  listDocuments: (projectId: number, params?: { search?: string; tag?: string }) => {
    const query = new URLSearchParams();
    if (params?.search) query.set("search", params.search);
    if (params?.tag) query.set("tag", params.tag);
    const qs = query.toString();
    return request<Document[]>(`/projects/${projectId}/documents${qs ? `?${qs}` : ""}`);
  },
  downloadDocumentUrl: (documentId: number) => `${API_BASE}/documents/${documentId}/download`,
  updateDocument: (documentId: number, payload: { dateiname?: string; tags?: string[] }) =>
    request<Document>(`/documents/${documentId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteDocument: (documentId: number) => request<void>(`/documents/${documentId}`, { method: "DELETE" }),
  linkDocument: (documentId: number, entityType: EntityType, entityId: number) =>
    request<DocumentLink>("/document-links", {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, entity_type: entityType, entity_id: entityId }),
    }),
  unlinkDocument: (linkId: number) => request<void>(`/document-links/${linkId}`, { method: "DELETE" }),
  listTags: (search?: string) => request<Tag[]>(`/tags${search ? `?search=${encodeURIComponent(search)}` : ""}`),
};
