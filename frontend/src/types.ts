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
  // Gesetzt = Antwort auf einen anderen Kommentar (Discussion Threading, siehe CONCEPT.md
  // Abschnitt 8). Backend erlaubt beliebige Tiefe, die UI begrenzt die Darstellung auf eine
  // Verschachtelungsebene (siehe NotesSection.tsx).
  parent_id: number | null;
  plan_phase_id: number | null;
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
  plan_phase_id: number | null;
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
  plan_phase_id: number | null;
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
  plan_phase_id: number | null;
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

// P16.5 (Aktuelle Themen): welche Tags im Projekt tatsächlich verwendet werden -
// backend/app/routers/knowledge.py get_project_knowledge_context.
export interface KnowledgeProjectContext {
  project_id: number;
  counts: Record<string, number>;
  tags: string[];
  relations: EntityRelation[];
}

// Phase 26.2/P11: PlanPhase/Milestone (Phase 17 der Zielarchitektur, backend/app/routers/planning.py)
// - Zielarchitektur-native Entitäten, ersetzen ab jetzt das alte Gantt/FTE-Raster als
// Bedienoberfläche. status ist im Backend bewusst Freitext (kein Enum) - die folgenden
// Wertelisten sind reine Frontend-Konvention. Zielvokabular (P11, Planungs-/Kapazitäts-
// konsolidierung): Geplant/In Arbeit/Abgeschlossen/Entfällt. "verzoegert" bleibt als
// historischer Wert lesbar (Altdaten vor der Konsolidierung) - er wird NICHT automatisch zu
// "entfaellt" migriert (fachlich falsch, siehe CONCEPT.md) und ist in
// PLAN_PHASE_STATUS_OPTIONS bewusst nicht enthalten: Verzögerung ist künftig eine berechnete
// Steuerungsinformation (Schedule Gap), kein manuell wählbarer Status mehr.
export type PlanPhaseStatus = "geplant" | "laufend" | "abgeschlossen" | "entfaellt" | "verzoegert";

export const PLAN_PHASE_STATUS_LABELS: Record<PlanPhaseStatus, string> = {
  geplant: "Geplant",
  laufend: "In Arbeit",
  abgeschlossen: "Abgeschlossen",
  entfaellt: "Entfällt",
  verzoegert: "Verzögert (historisch)",
};

// Für Create-/Edit-Dropdowns: nur das aktuelle Zielvokabular, "verzoegert" absichtlich
// ausgeschlossen (siehe Kommentar oben). Bestehende Phasen mit status="verzoegert" behalten
// ihren Wert und ihr Label, bis sie manuell auf einen der vier Zielwerte umgestellt werden.
export const PLAN_PHASE_STATUS_OPTIONS: PlanPhaseStatus[] = ["geplant", "laufend", "abgeschlossen", "entfaellt"];

// Vorschläge für phase_type (Freitext im Backend) - aus den bisherigen Gantt-Phasencodes
// übernommen, damit die neue Ansicht für Nutzer:innen des alten Gantt vertraut bleibt.
export const PLAN_PHASE_TYPE_SUGGESTIONS = ["Pflichtenheft", "Konfiguration", "Test", "Schulung", "GoLive"];

// P18/B-1/B-3 (BD-10, CLOSED): maximale Hierarchietiefe 3 Ebenen, backend-validiert. Frontend
// nutzt denselben Wert nur zur Vorfilterung (z.B. "Übergeordnete Phase"-Picker,
// "+ Unterphase hinzufügen"-Sichtbarkeit) - keine zweite Quelle der Wahrheit, das Backend
// validiert unabhängig davon verbindlich.
export const MAX_PLAN_PHASE_DEPTH = 3;

// 1 = Top-Level, 2 = Kind einer Top-Level-Phase, 3 = Enkelkind. Bricht bei einem Zyklus
// defensiv ab (sollte durch das Backend nie erreichbar sein).
export function planPhaseDepth(phases: PlanPhase[], phaseId: number): number {
  const byId = new Map(phases.map((p) => [p.id, p]));
  let depth = 1;
  let current = byId.get(phaseId);
  const seen = new Set<number>([phaseId]);
  while (current?.parent_phase_id != null) {
    if (seen.has(current.parent_phase_id)) break;
    seen.add(current.parent_phase_id);
    current = byId.get(current.parent_phase_id);
    depth += 1;
  }
  return depth;
}

// P19.6 (Planstand-UX): alle Nachfahren-IDs einer Phase (rekursiv über parent_phase_id) - für
// den phasenscoped Planstand-Vergleich bei Parent-Phasen (Deviations der ganzen Unterphasen-
// Gruppe zählen als "seit Planstand geändert" für die Parent-Phase). Enthält NICHT die Phase
// selbst. Bricht bei einem Zyklus defensiv ab (sollte durch das Backend nie erreichbar sein).
export function planPhaseDescendantIds(phases: PlanPhase[], phaseId: number): Set<number> {
  const childrenByParent = new Map<number, PlanPhase[]>();
  for (const p of phases) {
    if (p.parent_phase_id == null) continue;
    const list = childrenByParent.get(p.parent_phase_id) ?? [];
    list.push(p);
    childrenByParent.set(p.parent_phase_id, list);
  }
  const result = new Set<number>();
  const stack = [phaseId];
  while (stack.length > 0) {
    const current = stack.pop()!;
    for (const child of childrenByParent.get(current) ?? []) {
      if (result.has(child.id)) continue;
      result.add(child.id);
      stack.push(child.id);
    }
  }
  return result;
}

export interface PlanPhase {
  id: number;
  project_id: number;
  subproject_id: number | null;
  // P18/B-1/B-3: Self-referencing Hierarchie (CONCEPT.md Abschnitt 6b.1). null = Top-Level.
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
  // P20.1 (BD-1A CLOSED): Jira-Label dieser Leaf-Phase für den Worklog-Resolver, nur auf
  // Leaf-Phasen gepflegt (gleicher Lifecycle wie plan_fte).
  jira_label: string | null;
  owner_person_id: number | null;
  owner_team_id: number | null;
  erstellt_am: string;
  aktualisiert_am: string;
  tags: string[];
  documents: Document[];
  // P18/B-3: query-seitig berechnet, kein gespeichertes Feld (CONCEPT.md Abschnitt 6b.3).
  has_children: boolean;
  // Nur bei has_children=true befüllt - aus den Leaf-Nachfahren abgeleitet, NIE aus einem
  // eigenen Feld der Parent-Phase (forecast_start/forecast_end/plan_fte bleiben dann null).
  derived_forecast_start: string | null;
  derived_forecast_end: string | null;
  derived_capacity: number | null;
}

// Phase 26.10: PlanPhase Workspace (P3-Endpoints, backend/app/routers/planning.py +
// communication.py). Reconciliation vergleicht Headline-FTE (PlanPhase.plan_fte) mit der
// Aufschlüsselungs-Summe (Summe ResourceDemand.fte dieser Phase). BD-1: effort_consumption_pct
// und ist_hours sind aktuell immer None (keine Ist-Stunden-Quelle) - Rohmetriken ohne Ampel.
export interface ReconciliationOut {
  headline_fte: number | null;
  breakdown_fte: number | null;
  open_fte: number | null;
}

export interface PhaseMetricsOut {
  time_progress_pct: number | null;
  plan_hours: number | null;
  // P20.4 (BD-1 CLOSED): null bleibt "noch nicht zugeordnet" (kein jira_label bzw. kein
  // gemappter Leaf-Nachfahre) - niemals eine irreführende 0.
  effort_consumption_pct: number | null;
  ist_hours: number | null;
  remaining_plan_hours: number | null;
  overrun_hours: number | null;
  reconciliation: ReconciliationOut;
}

// P20.5 (siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 10) - Mapping-Preview
// vor dem Speichern eines jira_label, rein lesend gegen den Sync-Cache.
export interface JiraMatchPreview {
  matched_issues: number;
  matched_worklogs: number;
  total_hours: number;
  sample_issue_keys: string[];
  as_of: string | null;
}

// P20.3 (siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 19) - reine Vertrauens-/
// Vollständigkeitskennzahl, keine Health-Ampel. project_ist_total = mapped_total +
// ambiguous_total + unmapped_total (immer, per Konstruktion).
export interface ProjectActualsCoverage {
  project_id: number;
  project_ist_total: number;
  mapped_total: number;
  ambiguous_total: number;
  unmapped_total: number;
  coverage_pct: number | null;
}

// P20.6 (siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 17/18/24/25) -
// Personen-Drilldown + Planned-vs-Actual-Vergleich einer Phase.
export interface PersonActual {
  jira_account_id: string;
  person_id: number | null;
  display_name: string;
  hours: number;
  planned: boolean;
}

export interface PlanPhasePersonActuals {
  plan_phase_id: number;
  ist_hours: number | null;
  persons: PersonActual[];
  unplanned_actual_hours: number | null;
  planned_without_actual: PlanPhaseAssignedPerson[];
}

export interface PlanPhaseDetail extends PlanPhase {
  comments: Comment[];
  tasks: Task[];
  blockers: Blocker[];
  decisions: Decision[];
  resource_demands: ResourceDemand[];
  // P19.5 (additiv): Milestones dieser Phase (plan_phase_id-FK), damit der PlanPhase-Workspace
  // sie ohne zusätzlichen Round-Trip anzeigen kann. Nicht rekursiv (nur diese Phase selbst).
  milestones: Milestone[];
  metrics: PhaseMetricsOut;
  // P18/B-3: direkte Kinder (nicht rekursiv) - für die Baum-UI.
  children: PlanPhase[];
  // P19.2 (Kapazität-Tab Round-Trip-Reduktion): dieselbe Bedarf/Besetzt/Offen-Auswertung wie
  // GET .../assignment-summary, additiv eingebettet - der eigenständige Endpoint bleibt
  // bestehen. Frontend bevorzugt diesen eingebetteten Wert, wenn vorhanden.
  assignment_summary: PlanPhaseAssignmentSummary;
}

// P18/B-4 (CONCEPT.md Abschnitt 6b.10): Bedarf/Besetzt/Offen einer Leaf-PlanPhase - UI-
// Vokabular "Geplanter Ressourcenbedarf"/"Besetzung"/"Offen", NICHT "ResourceDemand".
export interface PlanPhaseAssignedPerson {
  person_id: number;
  person_name: string;
  fte: number;
}

export interface PlanPhaseAssignmentSummary {
  plan_phase_id: number;
  plan_fte: number | null;
  assigned_fte: number;
  open_fte: number | null;
  assignments: PlanPhaseAssignedPerson[];
}

// P18/B-3 (CONCEPT.md Abschnitt 6b.9): Vorschau vor "Gesamten Zweig löschen".
export interface PlanPhaseSubtreeImpact {
  plan_phase_id: number;
  phase_type: string;
  descendant_phase_count: number;
  comments_affected: number;
  tasks_affected: number;
  blockers_affected: number;
  decisions_affected: number;
  milestones_affected: number;
  documents_affected: number;
  resource_demands_affected: number;
  resource_assignments_affected: number;
}

// P19.7: Beitrag einer einzelnen Leaf-PlanPhase zu Projektkapazität(Monat) - für die
// Monats-Drilldown-Darstellung ("Oktober: Pflichtenheft 48h, Konfiguration 67h, Gesamt 115h").
export interface ProjectMonthlyCapacityPhaseContribution {
  plan_phase_id: number;
  phase_type: string;
  hours: number;
}

// P18/B-5 (CONCEPT.md Abschnitt 6b.6): read-only Auswertung, kein Eingabefeld.
export interface ProjectMonthlyCapacityEntry {
  period: string;
  hours: number;
  fte_equivalent: number;
  by_phase: ProjectMonthlyCapacityPhaseContribution[];
}

// P18/B-4 (CONCEPT.md Abschnitt 6b.5/6b.11): Available Capacity über einen Datumsbereich statt
// nur einen Monats-Bucket.
export interface PersonCapacityRange {
  person_id: number;
  range_start: string;
  range_end: string;
  nominal_fte: number;
  holiday_fte: number;
  absence_fte: number;
  internal_fte: number;
  available_fte: number;
  working_days: number;
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
  // P18/B-1/B-7 (CONCEPT.md Abschnitt 6b.8): ersetzt subproject_id fachlich. null = projekt-
  // weiter Meilenstein; gesetzt kann auf eine Leaf- oder Parent-Phase zeigen.
  plan_phase_id: number | null;
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
  reason: string | null;
  created_at: string;
  created_by_person_id: number | null;
  entry_count: number;
  tags: string[];
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
  reason: string | null;
  created_at: string;
  created_by_person_id: number | null;
  tags: string[];
  entries: BaselineEntry[];
}

// Planstand-Vergleich (backend/app/baseline_calc.py compute_deviations, Abschnitt 5.3/13.4
// CONCEPT.md): rohe Feld-Deltas, das Frontend formatiert sie in Fachsprache
// (siehe planstandFieldLabels.ts), keine Rohfeldnamen im UI.
export interface BaselineDeviation {
  entity_type: EntityType;
  entity_id: number;
  label: string | null;
  field: string;
  baseline_value: string | null;
  current_value: string | null;
  delta_days: number | null;
  // P18.1 Stabilization: "changed" (Default) vs. "added"/"removed" für strukturelle
  // PlanPhase-Baum-Änderungen seit dem Planstand (siehe backend/app/baseline_calc.py).
  type: "changed" | "added" | "removed";
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
  // P19.2 (Kapazität-Tab N+1-Fix): die ResourceAssignments dieses Demands additiv eingebettet -
  // löst das N+1-Muster auf (vorher: pro aufgeklapptem Demand ein eigener listResourceAssignments-
  // Call). Der eigenständige Endpoint bleibt bestehen (z.B. für gezielten Refresh nach Mutation).
  assignments: ResourceAssignment[];
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
