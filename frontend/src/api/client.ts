import type {
  AdminAppRole,
  AdminCapacityCalendar,
  AdminHealthThreshold,
  AdminPermission,
  AdminPerson,
  AdminProjectRole,
  AdminResourceRole,
  AdminSkill,
  AdminTag,
  AdminTagCategory,
  AiReadinessReport,
  Comment,
  Decision,
  DecisionStatus,
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
  KpiSummary,
  MeetingMinutes,
  MemberUtilization,
  PlanHistoryEntry,
  ProjectDetail,
  ProjectStatus,
  ProjectSummary,
  Risk,
  RiskLevel,
  RiskStatus,
  SubprojectDetail,
  SubprojectListItem,
  Tag,
  Task,
  TaskStatus,
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
  getProjectGap: (projectId: number) => request<GapAnalysis>(`/gap/${projectId}`),
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

  // Kommunikation: Entscheidungen/Risiken/Meetingprotokolle (siehe CONCEPT.md Abschnitt 6a)
  listDecisions: (projectId: number) => request<Decision[]>(`/projects/${projectId}/decisions`),
  createDecision: (
    projectId: number,
    payload: {
      titel: string;
      beschreibung?: string | null;
      status?: DecisionStatus;
      entschieden_von?: string | null;
      entschieden_am?: string | null;
      tags?: string[];
    },
  ) => request<Decision>(`/projects/${projectId}/decisions`, { method: "POST", body: JSON.stringify(payload) }),
  updateDecision: (
    decisionId: number,
    payload: Partial<{
      titel: string;
      beschreibung: string | null;
      status: DecisionStatus;
      entschieden_von: string | null;
      entschieden_am: string | null;
      tags: string[];
    }>,
  ) => request<Decision>(`/projects/decisions/${decisionId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteDecision: (decisionId: number) => request<void>(`/projects/decisions/${decisionId}`, { method: "DELETE" }),

  listRisks: (projectId: number) => request<Risk[]>(`/projects/${projectId}/risks`),
  createRisk: (
    projectId: number,
    payload: {
      titel: string;
      beschreibung?: string | null;
      wahrscheinlichkeit?: RiskLevel;
      auswirkung?: RiskLevel;
      status?: RiskStatus;
      owner?: string | null;
      faellig_am?: string | null;
      tags?: string[];
    },
  ) => request<Risk>(`/projects/${projectId}/risks`, { method: "POST", body: JSON.stringify(payload) }),
  updateRisk: (
    riskId: number,
    payload: Partial<{
      titel: string;
      beschreibung: string | null;
      wahrscheinlichkeit: RiskLevel;
      auswirkung: RiskLevel;
      status: RiskStatus;
      owner: string | null;
      faellig_am: string | null;
      tags: string[];
    }>,
  ) => request<Risk>(`/projects/risks/${riskId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteRisk: (riskId: number) => request<void>(`/projects/risks/${riskId}`, { method: "DELETE" }),

  listMeetingMinutes: (projectId: number) => request<MeetingMinutes[]>(`/projects/${projectId}/meeting-minutes`),
  createMeetingMinutes: (
    projectId: number,
    payload: { titel: string; datum: string; teilnehmer?: string | null; text: string; tags?: string[] },
  ) =>
    request<MeetingMinutes>(`/projects/${projectId}/meeting-minutes`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateMeetingMinutes: (
    meetingId: number,
    payload: Partial<{ titel: string; datum: string; teilnehmer: string | null; text: string; tags: string[] }>,
  ) =>
    request<MeetingMinutes>(`/projects/meeting-minutes/${meetingId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteMeetingMinutes: (meetingId: number) =>
    request<void>(`/projects/meeting-minutes/${meetingId}`, { method: "DELETE" }),

  listTasks: (projectId: number) => request<Task[]>(`/projects/${projectId}/tasks`),
  createTask: (
    projectId: number,
    payload: {
      titel: string;
      beschreibung?: string | null;
      status?: TaskStatus;
      zustaendig?: string | null;
      faellig_am?: string | null;
      tags?: string[];
    },
  ) => request<Task>(`/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(payload) }),
  updateTask: (
    taskId: number,
    payload: Partial<{
      titel: string;
      beschreibung: string | null;
      status: TaskStatus;
      zustaendig: string | null;
      faellig_am: string | null;
      tags: string[];
    }>,
  ) => request<Task>(`/projects/tasks/${taskId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTask: (taskId: number) => request<void>(`/projects/tasks/${taskId}`, { method: "DELETE" }),

  // Controlling-Erweiterung: Auslastung & KPIs (siehe CONCEPT.md Abschnitt 6/9, Schritt 9)
  getUtilization: () => request<MemberUtilization[]>("/team/utilization"),
  getKpis: () => request<KpiSummary>("/kpis"),

  // Fachliche Administration (Phase 25)
  listPeople: () => request<AdminPerson[]>("/people"),
  createPerson: (payload: { display_name: string; email?: string | null }) =>
    request<AdminPerson>("/people", { method: "POST", body: JSON.stringify(payload) }),
  updatePerson: (id: number, payload: Partial<Pick<AdminPerson, "display_name" | "email" | "active">>) =>
    request<AdminPerson>(`/people/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  listProjectRoles: () => request<AdminProjectRole[]>("/project-roles"),
  createProjectRole: (payload: { name: string; description?: string }) => request<AdminProjectRole>("/project-roles", { method: "POST", body: JSON.stringify(payload) }),
  updateProjectRole: (id: number, payload: Partial<Omit<AdminProjectRole, "id">>) => request<AdminProjectRole>(`/project-roles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  listPermissions: () => request<AdminPermission[]>("/permissions"),
  listAppRoles: () => request<AdminAppRole[]>("/app-roles"),
  createAppRole: (payload: { name: string; description?: string }) => request<AdminAppRole>("/app-roles", { method: "POST", body: JSON.stringify(payload) }),
  updateAppRole: (id: number, payload: { name?: string; description?: string }) => request<AdminAppRole>(`/app-roles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  setRolePermission: (roleId: number, permissionId: number, enabled: boolean) => request<AdminAppRole>(`/app-roles/${roleId}/permissions/${permissionId}`, { method: enabled ? "POST" : "DELETE" }),
  listResourceRoles: () => request<AdminResourceRole[]>("/resource-roles"),
  createResourceRole: (payload: { name: string; description?: string }) => request<AdminResourceRole>("/resource-roles", { method: "POST", body: JSON.stringify(payload) }),
  updateResourceRole: (id: number, payload: Partial<Omit<AdminResourceRole, "id">>) => request<AdminResourceRole>(`/resource-roles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  listSkills: () => request<AdminSkill[]>("/skills"),
  createSkill: (payload: { name: string; category?: string }) => request<AdminSkill>("/skills", { method: "POST", body: JSON.stringify(payload) }),
  updateSkill: (id: number, payload: Partial<Omit<AdminSkill, "id">>) => request<AdminSkill>(`/skills/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  listAdminTags: () => request<AdminTag[]>("/tags"),
  createAdminTag: (payload: { name: string; category_id?: number | null }) => request<AdminTag>("/tags", { method: "POST", body: JSON.stringify(payload) }),
  updateAdminTag: (id: number, payload: Partial<Omit<AdminTag, "id" | "name">>) => request<AdminTag>(`/tags/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  listTagCategories: () => request<AdminTagCategory[]>("/tag-categories"),
  createTagCategory: (payload: { name: string; description?: string }) => request<AdminTagCategory>("/tag-categories", { method: "POST", body: JSON.stringify(payload) }),
  listHealthThresholds: () => request<AdminHealthThreshold[]>("/health-thresholds"),
  updateHealthThreshold: (metric: string, payload: { yellow: number; red: number }) => request<AdminHealthThreshold>(`/health-thresholds/${metric}`, { method: "PUT", body: JSON.stringify(payload) }),
  listCapacityCalendars: () => request<AdminCapacityCalendar[]>("/capacity-calendars"),
  createCapacityCalendar: (payload: { name: string; description?: string }) => request<AdminCapacityCalendar>("/capacity-calendars", { method: "POST", body: JSON.stringify(payload) }),
  updateCapacityCalendar: (id: number, payload: Partial<Omit<AdminCapacityCalendar, "id">>) => request<AdminCapacityCalendar>(`/capacity-calendars/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  jiraAdminStatus: () => request<{ configured: boolean; tempo_configured?: boolean }>("/jira/status"),
  getAiReadiness: () => request<AiReadinessReport>("/knowledge/readiness"),
};
