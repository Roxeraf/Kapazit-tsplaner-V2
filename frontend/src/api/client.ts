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
  PortfolioUtilizationEntry,
  ResourceProfile,
  ActivityItem,
  BaselineDeviation,
  BaselineSnapshot,
  BaselineSnapshotSummary,
  KnowledgeProjectContext,
  Blocker,
  BlockerParty,
  BlockerStatus,
  BlockerSeverity,
  CandidatePerson,
  CommitmentLevel,
  EntityRelation,
  Milestone,
  MilestoneStatus,
  PersonCapacityRange,
  PlanHistoryEntry,
  PlanPhase,
  PlanPhaseAssignmentSummary,
  PlanPhaseDetail,
  PlanPhaseStatus,
  PlanPhaseSubtreeImpact,
  PhaseMetricsOut,
  ProjectDetail,
  ProjectMembership,
  ProjectMonthlyCapacityEntry,
  ProjectStatus,
  ProjectSummary,
  PortfolioAllocationGapEntry,
  ProjectControlCockpit,
  ProjectHealth,
  RelationType,
  ResourceAssignment,
  ResourceDemand,
  TagDossier,
  Risk,
  RiskLevel,
  RiskStatus,
  SubprojectDetail,
  SubprojectListItem,
  Tag,
  Task,
  TaskStatus,
  Team,
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
      projektleiter_person_id: number | null;
      kommentar_id: number | null;
      batch_id: string | null;
    }>,
  ) => request<ProjectDetail>(`/projects/${projectId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProject: (projectId: number) => request<void>(`/projects/${projectId}`, { method: "DELETE" }),
  reorderProjects: (projectIds: number[]) =>
    request<void>("/projects/reorder", { method: "PUT", body: JSON.stringify({ project_ids: projectIds }) }),
  /** @deprecated P18/B-7/B-8 (CONCEPT.md Abschnitt 6b.7): Subproject wird fachlich durch eine
   * Parent-PlanPhase ersetzt (CONCEPT.md Abschnitt 6b.7/19 der Aufgabenstellung: "keine neue
   * Subproject-UX"). Bleibt compat-only bestehen, bis eine ausgeführte B-2-Migration
   * bestehende Subprojects auf Parent-PlanPhases überführt hat (B-8, noch nicht erfolgt) -
   * danach ist dieser Pfad vollständig obsolet. Keine neuen Aufrufstellen anlegen. */
  createSubproject: (projectId: number, name: string, reihenfolge: number) =>
    request(`/projects/${projectId}/subprojects`, {
      method: "POST",
      body: JSON.stringify({ name, reihenfolge }),
    }),
  /** @deprecated siehe createSubproject. */
  deleteSubproject: (subprojectId: number) =>
    request<void>(`/projects/subprojects/${subprojectId}`, { method: "DELETE" }),
  /** @deprecated siehe createSubproject. */
  updateSubproject: (subprojectId: number, payload: { name?: string; reihenfolge?: number }) =>
    request<SubprojectDetail>(`/projects/subprojects/${subprojectId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  /** @deprecated siehe createSubproject. */
  listAllSubprojects: () => request<SubprojectListItem[]>("/projects/subprojects/all"),

  // Planung (Phase 26.2): PlanPhase/Milestone/Baseline ersetzen ab jetzt Gantt/FTE als
  // Bedienoberfläche (backend/app/routers/planning.py, routers/baselines.py)
  listPlanPhases: (projectId: number) => request<PlanPhase[]>(`/projects/${projectId}/plan-phases`),
  createPlanPhase: (
    projectId: number,
    payload: {
      subproject_id?: number | null;
      parent_phase_id?: number | null;
      reihenfolge?: number;
      phase_type: string;
      baseline_start?: string | null;
      baseline_end?: string | null;
      forecast_start?: string | null;
      forecast_end?: string | null;
      actual_start?: string | null;
      actual_end?: string | null;
      status?: PlanPhaseStatus;
      progress?: number | null;
      plan_fte?: number | null;
      owner_person_id?: number | null;
      owner_team_id?: number | null;
      tags?: string[];
    },
  ) => request<PlanPhase>(`/projects/${projectId}/plan-phases`, { method: "POST", body: JSON.stringify(payload) }),
  updatePlanPhase: (
    planPhaseId: number,
    payload: Partial<{
      subproject_id: number | null;
      parent_phase_id: number | null;
      reihenfolge: number;
      phase_type: string;
      baseline_start: string | null;
      baseline_end: string | null;
      forecast_start: string | null;
      forecast_end: string | null;
      actual_start: string | null;
      actual_end: string | null;
      status: PlanPhaseStatus;
      progress: number | null;
      plan_fte: number | null;
      owner_person_id: number | null;
      owner_team_id: number | null;
      tags: string[];
    }>,
  ) => request<PlanPhase>(`/projects/plan-phases/${planPhaseId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deletePlanPhase: (planPhaseId: number) => request<void>(`/projects/plan-phases/${planPhaseId}`, { method: "DELETE" }),
  // P18/B-3 (CONCEPT.md Abschnitt 6b.9, BD-11): Standard-DELETE liefert 409 mit
  // {child_count, message} statt zu kaskadieren, sobald die Phase Kinder hat. Eigener
  // Rückgabetyp statt Exception, damit der Aufrufer den Blockier-Dialog (Unterphasen
  // verschieben/Gesamten Zweig löschen/Abbrechen) sauber anzeigen kann, ohne Fehlertext zu
  // parsen - der generische request()-Wrapper wirft sonst nur eine Error mit Rohtext.
  tryDeletePlanPhase: async (
    planPhaseId: number,
  ): Promise<{ blocked: false } | { blocked: true; childCount: number; message: string }> => {
    const res = await fetch(`${API_BASE}/projects/plan-phases/${planPhaseId}`, { method: "DELETE" });
    if (res.status === 204) return { blocked: false };
    if (res.status === 409) {
      const body = await res.json();
      return { blocked: true, childCount: body.detail.child_count, message: body.detail.message };
    }
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  },
  getPlanPhaseDetail: (planPhaseId: number) =>
    request<PlanPhaseDetail>(`/projects/plan-phases/${planPhaseId}`),
  getPlanPhaseMetrics: (planPhaseId: number) =>
    request<PhaseMetricsOut>(`/projects/plan-phases/${planPhaseId}/metrics`),
  getPlanPhaseActivity: (planPhaseId: number, limit?: number) =>
    request<ActivityItem[]>(
      `/projects/plan-phases/${planPhaseId}/activity${limit ? `?limit=${limit}` : ""}`,
    ),

  // P18/B-3 (CONCEPT.md Abschnitt 6b.9): Reparenting/Subtree-Delete, jeweils separat vom
  // normalen CRUD, da Subtree-Delete eine bewusst destruktive, stark bestätigte Aktion ist.
  reparentPlanPhaseChildren: (planPhaseId: number, newParentPhaseId: number | null) =>
    request<{ moved_count: number; children: PlanPhase[] }>(
      `/projects/plan-phases/${planPhaseId}/reparent-children`,
      { method: "POST", body: JSON.stringify({ new_parent_phase_id: newParentPhaseId }) },
    ),
  getPlanPhaseSubtreeImpact: (planPhaseId: number) =>
    request<PlanPhaseSubtreeImpact>(`/projects/plan-phases/${planPhaseId}/subtree-impact`),
  deletePlanPhaseSubtree: (planPhaseId: number, payload: { confirm_phase_type: string; confirm_descendant_count: number }) =>
    request<void>(`/projects/plan-phases/${planPhaseId}/delete-subtree`, { method: "POST", body: JSON.stringify(payload) }),

  // P18/B-4 (CONCEPT.md Abschnitt 6b.4/6b.10/6b.11): Direct Assignment ohne Rollen-Zwang.
  getPlanPhaseAssignmentSummary: (planPhaseId: number) =>
    request<PlanPhaseAssignmentSummary>(`/projects/plan-phases/${planPhaseId}/assignment-summary`),
  assignPersonToPlanPhase: (planPhaseId: number, payload: { person_id: number; fte: number }) =>
    request<PlanPhaseAssignmentSummary>(`/projects/plan-phases/${planPhaseId}/assign-person`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  unassignPersonFromPlanPhase: (planPhaseId: number, personId: number) =>
    request<PlanPhaseAssignmentSummary>(`/projects/plan-phases/${planPhaseId}/assign-person/${personId}`, {
      method: "DELETE",
    }),
  getPlanPhaseAssignmentCandidates: (planPhaseId: number) =>
    request<CandidatePerson[]>(`/projects/plan-phases/${planPhaseId}/assignment-candidates`),
  getPersonCapacityRange: (personId: number, start: string, end: string) =>
    request<PersonCapacityRange>(`/people/${personId}/capacity-range?start=${start}&end=${end}`),

  // P18/B-5 (CONCEPT.md Abschnitt 6b.6): read-only Auswertung, kein Eingabefeld.
  getProjectMonthlyCapacity: (projectId: number, periods?: string[]) =>
    request<ProjectMonthlyCapacityEntry[]>(
      `/projects/${projectId}/capacity/monthly${
        periods && periods.length > 0 ? `?${periods.map((p) => `periods=${encodeURIComponent(p)}`).join("&")}` : ""
      }`,
    ),

  listMilestones: (projectId: number) => request<Milestone[]>(`/projects/${projectId}/milestones`),
  createMilestone: (
    projectId: number,
    payload: {
      subproject_id?: number | null;
      plan_phase_id?: number | null;
      name: string;
      baseline_date?: string | null;
      forecast_date?: string | null;
      actual_date?: string | null;
      status?: MilestoneStatus;
      owner_person_id?: number | null;
      owner_team_id?: number | null;
      tags?: string[];
    },
  ) => request<Milestone>(`/projects/${projectId}/milestones`, { method: "POST", body: JSON.stringify(payload) }),
  updateMilestone: (
    milestoneId: number,
    payload: Partial<{
      subproject_id: number | null;
      plan_phase_id: number | null;
      name: string;
      baseline_date: string | null;
      forecast_date: string | null;
      actual_date: string | null;
      status: MilestoneStatus;
      owner_person_id: number | null;
      owner_team_id: number | null;
      tags: string[];
    }>,
  ) => request<Milestone>(`/projects/milestones/${milestoneId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteMilestone: (milestoneId: number) => request<void>(`/projects/milestones/${milestoneId}`, { method: "DELETE" }),

  listBaselines: (projectId: number) => request<BaselineSnapshotSummary[]>(`/projects/${projectId}/baselines`),
  createBaseline: (
    projectId: number,
    payload: { name: string; reason?: string | null; created_by_person_id?: number | null; tags?: string[] },
  ) => request<BaselineSnapshot>(`/projects/${projectId}/baselines`, { method: "POST", body: JSON.stringify(payload) }),
  deleteBaseline: (baselineId: number) => request<void>(`/projects/baselines/${baselineId}`, { method: "DELETE" }),
  getBaselineDeviations: (baselineId: number) =>
    request<BaselineDeviation[]>(`/projects/baselines/${baselineId}/deviations`),

  // Kapazität (Phase 26.3): ResourceDemand/ResourceAssignment ersetzen ab jetzt das alte
  // FTE-Raster (backend/app/routers/capacity.py)
  listResourceDemands: (projectId: number) => request<ResourceDemand[]>(`/projects/${projectId}/resource-demands`),
  createResourceDemand: (
    projectId: number,
    payload: { plan_phase_id?: number | null; resource_role_id: number; period: string; fte?: number; commitment_level?: CommitmentLevel },
  ) => request<ResourceDemand>(`/projects/${projectId}/resource-demands`, { method: "POST", body: JSON.stringify(payload) }),
  updateResourceDemand: (
    demandId: number,
    payload: Partial<{ plan_phase_id: number | null; resource_role_id: number; period: string; fte: number; commitment_level: CommitmentLevel }>,
  ) => request<ResourceDemand>(`/projects/resource-demands/${demandId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteResourceDemand: (demandId: number) => request<void>(`/projects/resource-demands/${demandId}`, { method: "DELETE" }),

  listResourceAssignments: (demandId: number) => request<ResourceAssignment[]>(`/resource-demands/${demandId}/assignments`),
  createResourceAssignment: (demandId: number, payload: { person_id: number; fte?: number }) =>
    request<ResourceAssignment>(`/resource-demands/${demandId}/assignments`, { method: "POST", body: JSON.stringify(payload) }),
  deleteResourceAssignment: (assignmentId: number) => request<void>(`/resource-assignments/${assignmentId}`, { method: "DELETE" }),
  getResourceDemandCandidates: (demandId: number) => request<CandidatePerson[]>(`/resource-demands/${demandId}/candidates`),

  // Blocker (Phase 26.4, backend/app/routers/communication.py)
  listBlockers: (projectId: number) => request<Blocker[]>(`/projects/${projectId}/blockers`),
  createBlocker: (
    projectId: number,
    payload: {
      title: string;
      description?: string | null;
      status?: BlockerStatus;
      severity?: BlockerSeverity;
      active_since?: string | null;
      caused_by_party?: BlockerParty;
      waiting_for_party?: BlockerParty;
      owner_person_id?: number | null;
      owner_team_id?: number | null;
      next_action?: string | null;
      impact?: string | null;
      tags?: string[];
      plan_phase_id?: number | null;
    },
  ) => request<Blocker>(`/projects/${projectId}/blockers`, { method: "POST", body: JSON.stringify(payload) }),
  updateBlocker: (
    blockerId: number,
    payload: Partial<{
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
      tags: string[];
    }>,
  ) => request<Blocker>(`/projects/blockers/${blockerId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteBlocker: (blockerId: number) => request<void>(`/projects/blockers/${blockerId}`, { method: "DELETE" }),

  // Activity Feed + EntityRelation (Phase 26.4, backend/app/routers/communication.py,knowledge.py)
  getActivity: (projectId: number, limit?: number) =>
    request<ActivityItem[]>(`/projects/${projectId}/activity${limit ? `?limit=${limit}` : ""}`),
  createEntityRelation: (payload: {
    source_entity_type: EntityType;
    source_entity_id: number;
    target_entity_type: EntityType;
    target_entity_id: number;
    relation_type: RelationType;
  }) => request<EntityRelation>("/entity-relations", { method: "POST", body: JSON.stringify(payload) }),

  // Project Control Cockpit (Phase 26.6, backend/app/routers/health.py)
  getCockpit: (projectId: number) => request<ProjectControlCockpit>(`/projects/${projectId}/cockpit`),

  // Controlling & Capacity Intelligence (Phase 26.7, backend/app/routers/controlling.py)
  getPortfolioHealth: () => request<ProjectHealth[]>("/controlling/portfolio-health"),
  getAllocationGaps: (period: string) =>
    request<PortfolioAllocationGapEntry[]>(`/controlling/allocation-gaps?period=${encodeURIComponent(period)}`),

  // Tag-Dossiers (Phase 26.5, backend/app/routers/knowledge.py)
  getTagDossier: (tags: string[], mode: "and" | "or" = "and", projectId?: number) => {
    const query = new URLSearchParams({ tags: tags.join(","), mode });
    if (projectId !== undefined) query.set("project_id", String(projectId));
    return request<TagDossier>(`/knowledge/tags/dossier?${query.toString()}`);
  },
  getProjectKnowledgeContext: (projectId: number) =>
    request<KnowledgeProjectContext>(`/knowledge/project/${projectId}`),

  exportPptxUrl: (projectId: number) => `${API_BASE}/projects/${projectId}/export/pptx`,
  exportPortfolioPptxUrl: () => `${API_BASE}/projects/export/pptx/portfolio`,

  // Team-Kapazität (Phase 26.9: Mitgliederverwaltung läuft über Person/ResourceProfile,
  // siehe listPeople/createPerson/updatePerson/getResourceProfile weiter unten)
  listTeams: () => request<Team[]>("/team"),
  listUnassignedAuthors: () => request<UnassignedAuthor[]>("/team/unassigned-authors"),
  createTeam: (name: string) =>
    request<Team>("/team/teams", { method: "POST", body: JSON.stringify({ name }) }),
  updateTeam: (teamId: number, payload: { name?: string }) =>
    request<Team>(`/team/teams/${teamId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTeam: (teamId: number) => request<void>(`/team/teams/${teamId}`, { method: "DELETE" }),

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
      // Threading (siehe CONCEPT.md Abschnitt 8) - gesetzt = Antwort auf einen anderen
      // Kommentar desselben Projekts.
      parent_id?: number | null;
      plan_phase_id?: number | null;
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
      entschieden_von_person_id?: number | null;
      entschieden_am?: string | null;
      tags?: string[];
      plan_phase_id?: number | null;
    },
  ) => request<Decision>(`/projects/${projectId}/decisions`, { method: "POST", body: JSON.stringify(payload) }),
  updateDecision: (
    decisionId: number,
    payload: Partial<{
      titel: string;
      beschreibung: string | null;
      status: DecisionStatus;
      entschieden_von_person_id: number | null;
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
      owner_person_id?: number | null;
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
      owner_person_id: number | null;
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
      zustaendig_person_id?: number | null;
      faellig_am?: string | null;
      tags?: string[];
      plan_phase_id?: number | null;
    },
  ) => request<Task>(`/projects/${projectId}/tasks`, { method: "POST", body: JSON.stringify(payload) }),
  updateTask: (
    taskId: number,
    payload: Partial<{
      titel: string;
      beschreibung: string | null;
      status: TaskStatus;
      zustaendig_person_id: number | null;
      faellig_am: string | null;
      tags: string[];
    }>,
  ) => request<Task>(`/projects/tasks/${taskId}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTask: (taskId: number) => request<void>(`/projects/tasks/${taskId}`, { method: "DELETE" }),

  // Controlling-Erweiterung: Auslastung & KPIs (siehe CONCEPT.md Abschnitt 6/9, Schritt 9)
  getUtilization: (period?: string) =>
    request<PortfolioUtilizationEntry[]>(`/team/utilization${period ? `?period=${encodeURIComponent(period)}` : ""}`),
  getKpis: () => request<KpiSummary>("/kpis"),

  // Fachliche Administration (Phase 25) + projektweiter PersonPicker (Phase 26.1)
  listPeople: (search?: string) =>
    request<AdminPerson[]>(`/people${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createPerson: (payload: { display_name: string; email?: string | null; jira_account_id?: string | null }) =>
    request<AdminPerson>("/people", { method: "POST", body: JSON.stringify(payload) }),
  updatePerson: (
    id: number,
    payload: Partial<Pick<AdminPerson, "display_name" | "email" | "active" | "jira_account_id">>,
  ) => request<AdminPerson>(`/people/${id}`, { method: "PUT", body: JSON.stringify(payload) }),

  // ResourceProfile (Phase 14/26.9) - macht eine Person kapazitätsplanbar/teamzugehörig.
  getResourceProfile: (personId: number) =>
    request<ResourceProfile | null>(`/people/${personId}/resource-profile`),
  createResourceProfile: (
    personId: number,
    payload: { team_id?: number | null; weekly_hours?: number; capacity_relevant?: boolean; active?: boolean },
  ) =>
    request<ResourceProfile>(`/people/${personId}/resource-profile`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateResourceProfile: (
    personId: number,
    payload: Partial<{ team_id: number | null; weekly_hours: number; capacity_relevant: boolean; active: boolean }>,
  ) =>
    request<ResourceProfile>(`/people/${personId}/resource-profile`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  // Projektteam (Phase 14, ab Phase 26.1 im Frontend genutzt)
  listProjectMemberships: (projectId: number) =>
    request<ProjectMembership[]>(`/projects/${projectId}/memberships`),
  createProjectMembership: (projectId: number, personId: number, projectRoleId: number) =>
    request<ProjectMembership>(`/projects/${projectId}/memberships`, {
      method: "POST",
      body: JSON.stringify({ person_id: personId, project_role_id: projectRoleId }),
    }),
  deleteProjectMembership: (membershipId: number) =>
    request<void>(`/project-memberships/${membershipId}`, { method: "DELETE" }),

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
};
