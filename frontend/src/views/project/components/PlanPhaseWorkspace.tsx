import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import ActivityFeed from "./ActivityFeed";
import BlockerList from "./BlockerList";
import DecisionList from "./DecisionList";
import DocumentListPanel from "./DocumentListPanel";
import MilestoneList from "./MilestoneList";
import NotesSection from "../../../components/NotesSection";
import PersonPicker from "../../../components/PersonPicker";
import PlanPhaseCapacityTab from "./PlanPhaseCapacityTab";
import PlanPhaseCreateModal from "./PlanPhaseCreateModal";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import TaskList from "./TaskList";
import usePeopleMap from "../../../hooks/usePeopleMap";
import { useProjectWorkspace } from "../ProjectWorkspaceContext";
import {
  MAX_PLAN_PHASE_DEPTH,
  PLAN_PHASE_STATUS_LABELS,
  PLAN_PHASE_STATUS_OPTIONS,
  PLAN_PHASE_TYPE_SUGGESTIONS,
  planPhaseDepth,
  type EntityType,
  type JiraMatchPreview,
  type PlanPhase,
  type PlanPhaseDetail,
  type PlanPhaseStatus,
} from "../../../types";

// P11 (Planungs-/Kapazitätskonsolidierung): PlanPhase Workspace - rechtsseitiger Drawer, die
// primäre Bearbeitungsoberfläche einer Phase. Vier Tabs: Übersicht (editierbar,
// Sofort-Speichern), Kapazität (Direct Assignment - siehe PlanPhaseCapacityTab), Aktivität
// (bestehende generische Kommentar-/Task-/Blocker-/Decision-/ActivityFeed-Infrastruktur +
// kompakte Meilensteine-Karte), Dateien (Document/DocumentLink-System). forecast_start/
// forecast_end erscheinen hier nur als "Start"/"Ende" (= "aktueller Plan") - baseline_*/
// progress erscheinen im Normalflow gar nicht mehr (Progress deprecatet seit P6).
//
// P20.1 (Auftrag Abschnitt 17-20): bewusst NICHT mehr Bestandteil des normalen Workspace -
// der permanente "Seit Planstand VX"-Kurzvergleich (gehört auf Projektebene, siehe
// BaselineList/ProjectHistoryTab: Projekt → Planstände → Vergleich), die "Tatsächlicher
// Verlauf"-Karte (actual_start/actual_end bleiben in DB/API aus Compat-Gründen bestehen, aber
// P20 liefert mit Tempo/Jira-Ist-Aufwand einen wesentlich relevanteren Ist-Begriff - ein
// Projektleiter soll sie nicht zusätzlich manuell pflegen müssen) und der "Planstand"-Eintrag
// im phasenscoped Activity-Filter (BaselineSnapshot ist ein projektweiter Snapshot ohne
// plan_phase_id-Spalte, gehört in Projekt-Historie/Planstände, nicht in den Phasenfilter).
const PHASE_ACTIVITY_TYPES: EntityType[] = ["comment", "decision", "task", "blocker", "milestone"];

type Tab = "uebersicht" | "kapazitaet" | "aktivitaet" | "dateien";

function fmtNum(v: number | null | undefined, suffix = ""): string {
  return v == null ? "—" : `${v}${suffix}`;
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso + "T00:00:00");
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

// P19.1 (Workspace Information Architecture, Abschnitt 6): volle Ahnenkette von der Wurzel bis
// zur aktuellen Phase, rein clientseitig aus der bereits vorhandenen allPhases-Liste abgeleitet
// (kein neuer Backend-Call) - z.B. "Wareneingang › Schnittstellen › WE-Anmeldung". Bricht bei
// einem Zyklus defensiv ab (sollte durch das Backend nie erreichbar sein, siehe planPhaseDepth).
function ancestorChain(phases: PlanPhase[], phaseId: number): PlanPhase[] {
  const byId = new Map(phases.map((p) => [p.id, p]));
  const chain: PlanPhase[] = [];
  let current = byId.get(phaseId);
  const seen = new Set<number>();
  while (current && !seen.has(current.id)) {
    seen.add(current.id);
    chain.unshift(current);
    current = current.parent_phase_id != null ? byId.get(current.parent_phase_id) : undefined;
  }
  return chain;
}

export default function PlanPhaseWorkspace({
  planPhaseId,
  projectId,
  allPhases,
  onClose,
  onChanged,
  onNavigate,
}: {
  planPhaseId: number | null;
  projectId: number;
  allPhases: PlanPhase[];
  onClose: () => void;
  onChanged?: () => void;
  // P19.1: wechselt die im Drawer offene Phase (z.B. per Klick auf eine Ahnenphase im
  // Breadcrumb), ohne den Drawer zu schließen. Optional, damit bestehende Einbindungen ohne
  // Anpassung weiterlaufen - ohne diese Prop ist der Breadcrumb nicht klickbar.
  onNavigate?: (planPhaseId: number) => void;
}) {
  const [detail, setDetail] = useState<PlanPhaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("uebersicht");
  const [showCreateChild, setShowCreateChild] = useState(false);
  // ActivityFeed lädt selbst nach, bekommt Mutationen von NotesSection/TaskList/DecisionList/
  // BlockerList (Geschwisterkomponenten im selben Tab) aber nicht automatisch mit - dieser
  // Zähler wird bei jedem reload() hochgezählt und an ActivityFeed durchgereicht (P16.1).
  const [activityVersion, setActivityVersion] = useState(0);
  const people = usePeopleMap();
  const { project } = useProjectWorkspace();
  // P20.5 (Übersicht-Tab, Ist-Daten-Zeile, siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md
  // Abschnitt 9): Labels, die im verknüpften Jira-Projekt tatsächlich vorkommen, als
  // Datalist-Vorschläge (Dropdown-artig, aber weiterhin Freitext möglich - kein neuer
  // Jira-API-Endpoint, list_labels() existiert bereits für den Component-Picker). Ohne
  // verknüpftes Jira-Projekt bleibt die Liste leer, das Feld bleibt reiner Freitext.
  const [jiraLabelSuggestions, setJiraLabelSuggestions] = useState<string[]>([]);
  useEffect(() => {
    if (!project.jira_project_key) {
      setJiraLabelSuggestions([]);
      return;
    }
    api
      .jiraListLabels(project.jira_project_key)
      .then(setJiraLabelSuggestions)
      .catch(() => setJiraLabelSuggestions([]));
  }, [project.jira_project_key]);
  // P20.5 (Mapping-Preview, Abschnitt 10): zeigt, was das aktuell GESPEICHERTE jira_label
  // treffen würde - rein lesend gegen den Sync-Cache, aktualisiert sich automatisch nach
  // jedem Speichern (detail.jira_label ändert sich dann), keine Live-Jira-Abfrage.
  const [jiraMatchPreview, setJiraMatchPreview] = useState<JiraMatchPreview | null>(null);

  const load = () => {
    if (planPhaseId == null) return;
    setError(null);
    api.getPlanPhaseDetail(planPhaseId).then(setDetail).catch((e) => setError(String(e)));
  };

  // Beim Phasenwechsel: Detail zurücksetzen (vermeidet Stale-Data-Flash), Tab/Korrektur-Modus
  // zurücksetzen und neu laden. Nach Mutationen (reload) wird load() direkt aufgerufen.
  useEffect(() => {
    setDetail(null);
    setTab("uebersicht");
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planPhaseId]);

  const reload = () => {
    load();
    setActivityVersion((v) => v + 1);
    onChanged?.();
  };

  // P20.5: Mapping-Preview für das aktuell gespeicherte jira_label - muss vor dem frühen
  // `return null` unten stehen (Rules of Hooks), daher hier statt weiter unten im JSX-Zweig.
  useEffect(() => {
    if (!detail || !detail.jira_label) {
      setJiraMatchPreview(null);
      return;
    }
    api
      .getPlanPhaseJiraMatches(detail.id, detail.jira_label)
      .then(setJiraMatchPreview)
      .catch(() => setJiraMatchPreview(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail?.id, detail?.jira_label]);

  if (planPhaseId == null) return null;

  const update = async (changes: Record<string, unknown>) => {
    try {
      await api.updatePlanPhase(planPhaseId, changes);
      reload();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleAddNote = async (input: { text: string; tags: string[]; files: File[]; parentId?: number | null }) => {
    const comment = await api.createComment(projectId, {
      text: input.text,
      tags: input.tags,
      parent_id: input.parentId ?? null,
      plan_phase_id: planPhaseId,
    });
    for (const file of input.files) {
      await api.uploadDocument(projectId, file, { entityType: "comment", entityId: comment.id });
    }
    reload();
  };

  const handleDeleteNote = async (commentId: number) => {
    await api.deleteComment(commentId);
    reload();
  };

  // Statuswert der aktuellen Phase in den Options-Dropdown mit aufnehmen, falls es sich um
  // einen historischen Wert handelt (z.B. "verzoegert") - Daten bleiben sichtbar/wählbar
  // erhalten, ohne dass er als neuer Zielwert beworben wird (siehe types.ts).
  const statusOptions = detail && !PLAN_PHASE_STATUS_OPTIONS.includes(detail.status)
    ? [detail.status, ...PLAN_PHASE_STATUS_OPTIONS]
    : PLAN_PHASE_STATUS_OPTIONS;

  // P19.1: volle Ahnenkette INKLUSIVE der aktuellen Phase (letztes Segment, nicht klickbar -
  // entspricht dem Beispiel "Wareneingang › Schnittstellen › WE-Anmeldung" aus dem Auftrag).
  // Nur gerendert, wenn tatsächlich mindestens ein Vorfahre existiert (sonst wäre der
  // Breadcrumb identisch mit der bereits sichtbaren Überschrift).
  const breadcrumbChain = detail ? ancestorChain(allPhases, detail.id) : [];

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: "min(34rem, 100vw)",
        background: "#fff",
        borderLeft: "1px solid var(--border)",
        boxShadow: "-4px 0 16px rgba(0,0,0,0.12)",
        zIndex: 900,
        overflowY: "auto",
        padding: "1rem",
      }}
    >
      <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
        <h3 style={{ color: "var(--navy)", margin: 0 }}>{detail?.phase_type ?? "Phase"}</h3>
        <div style={{ display: "flex", gap: "0.4rem" }}>
          {detail && planPhaseDepth(allPhases, detail.id) < MAX_PLAN_PHASE_DEPTH && (
            <button type="button" className="btn secondary" onClick={() => setShowCreateChild(true)}>
              + Unterphase
            </button>
          )}
          <button type="button" className="btn secondary" onClick={onClose}>
            Schließen
          </button>
        </div>
      </div>
      {breadcrumbChain.length > 1 && (
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "-0.3rem 0 0.6rem", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.25rem" }}>
          {breadcrumbChain.map((phase, i) => {
            const isCurrent = i === breadcrumbChain.length - 1;
            return (
              <span key={phase.id} style={{ display: "inline-flex", alignItems: "center", gap: "0.25rem" }}>
                {!isCurrent && onNavigate ? (
                  <button
                    type="button"
                    onClick={() => onNavigate(phase.id)}
                    style={{ border: "none", background: "none", padding: 0, font: "inherit", color: "var(--blau)", cursor: "pointer", textDecoration: "underline" }}
                  >
                    {phase.phase_type}
                  </button>
                ) : (
                  <span style={isCurrent ? { fontWeight: 600, color: "var(--navy)" } : undefined}>{phase.phase_type}</span>
                )}
                {!isCurrent && <span aria-hidden="true">›</span>}
              </span>
            );
          })}
        </p>
      )}

      <div style={{ display: "flex", gap: "0.35rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
        {([
          ["uebersicht", "Übersicht"],
          ["kapazitaet", "Kapazität"],
          ["aktivitaet", "Aktivität"],
          ["dateien", "Dateien"],
        ] as [Tab, string][]).map(([key, label]) => (
          <button key={key} type="button" className={tab === key ? "btn" : "btn secondary"} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {!detail ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Lade Phase …</p>
      ) : tab === "uebersicht" ? (
        <>
          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <div className="field-row" style={{ marginTop: 0, flexDirection: "column", alignItems: "stretch" }}>
              <label>
                Name
                <input
                  key={`${detail.id}-name-${detail.phase_type}`}
                  defaultValue={detail.phase_type}
                  list="plan-phase-type-suggestions"
                  onBlur={(e) => {
                    const value = e.target.value.trim();
                    if (value && value !== detail.phase_type) update({ phase_type: value });
                  }}
                />
              </label>
              <datalist id="plan-phase-type-suggestions">
                {PLAN_PHASE_TYPE_SUGGESTIONS.map((s) => (
                  <option key={s} value={s} />
                ))}
              </datalist>

              {detail.has_children ? (
                <div style={{ fontSize: "0.85rem", background: "#f7f9fc", borderRadius: "0.4rem", padding: "0.5rem 0.6rem" }}>
                  <div>
                    <strong>Zeitraum:</strong>{" "}
                    {detail.derived_forecast_start && detail.derived_forecast_end
                      ? `${fmtDate(detail.derived_forecast_start)} – ${fmtDate(detail.derived_forecast_end)}`
                      : "—"}{" "}
                    <span style={{ color: "var(--text-muted)" }}>(abgeleitet aus {detail.children.length} Unterphase(n))</span>
                  </div>
                  <div style={{ marginTop: "0.2rem" }}>
                    <strong>Geplanter Ressourcenbedarf:</strong>{" "}
                    {detail.derived_capacity != null ? `${detail.derived_capacity.toFixed(2)} FTE` : "—"}{" "}
                    <span style={{ color: "var(--text-muted)" }}>(aggregiert, nicht direkt editierbar)</span>
                  </div>
                </div>
              ) : (
                <label>
                  Zeitraum (Start – Ende)
                  <div style={{ display: "flex", gap: "0.4rem" }}>
                    <input
                      key={`${detail.id}-fs-${detail.forecast_start}`}
                      type="date"
                      defaultValue={detail.forecast_start ?? ""}
                      onBlur={(e) => update({ forecast_start: e.target.value || null })}
                    />
                    <input
                      key={`${detail.id}-fe-${detail.forecast_end}`}
                      type="date"
                      defaultValue={detail.forecast_end ?? ""}
                      onBlur={(e) => update({ forecast_end: e.target.value || null })}
                    />
                  </div>
                </label>
              )}

              <div className="field-row" style={{ marginTop: 0 }}>
                <label>
                  Status
                  <select value={detail.status} onChange={(e) => update({ status: e.target.value as PlanPhaseStatus })}>
                    {statusOptions.map((value) => (
                      <option key={value} value={value}>
                        {PLAN_PHASE_STATUS_LABELS[value]}
                      </option>
                    ))}
                  </select>
                </label>
                {/* P20.1 (Auftrag Abschnitt 20): plan_fte hat seine EINDEUTIGE primäre
                    Bearbeitungsstelle im Kapazität-Tab - hier nur noch read-only Referenz,
                    keine doppelte Editierstelle. */}
                {!detail.has_children && (
                  <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", alignSelf: "flex-end" }}>
                    Geplanter Ressourcenbedarf: {detail.plan_fte != null ? `${detail.plan_fte.toFixed(2)} FTE` : "—"}{" "}
                    <span style={{ fontSize: "0.78rem" }}>(bearbeiten im Tab "Kapazität")</span>
                  </div>
                )}
              </div>

              <div className="field-row" style={{ marginTop: 0 }}>
                <label>
                  Übergeordnete Phase
                  <select
                    value={detail.parent_phase_id ?? ""}
                    onChange={(e) => update({ parent_phase_id: e.target.value === "" ? null : Number(e.target.value) })}
                  >
                    <option value="">— Top-Level —</option>
                    {allPhases
                      .filter((p) => p.id !== detail.id && planPhaseDepth(allPhases, p.id) < MAX_PLAN_PHASE_DEPTH)
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.phase_type}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Owner
                  <PersonPicker value={detail.owner_person_id} onChange={(personId) => update({ owner_person_id: personId })} />
                </label>
              </div>
              {detail.owner_person_id != null && (
                <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "-0.2rem 0 0" }}>
                  {people.get(detail.owner_person_id) ?? "…"}
                </p>
              )}

              <label>
                Tags
                <TagInput value={detail.tags} onChange={(tags) => update({ tags })} />
              </label>
            </div>
          </div>

          {/* P19.4: "Verknüpfte Themen" - Tags der Phase + Counts, rein clientseitig aus dem
              bereits geladenen PlanPhaseDetail abgeleitet (tags/decisions/blockers/documents
              sind schon Teil des Detail-Aufrufs oben) - kein zusätzlicher Aufruf des
              projektweiten knowledge/context-Endpoints nötig, da der phasenscoped Stand hier
              bereits vollständig vorliegt. */}
          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Verknüpfte Themen</h4>
            {detail.tags.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: 0 }}>Noch keine Tags an dieser Phase.</p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginBottom: "0.5rem" }}>
                {detail.tags.map((t) => (
                  <TagChip key={t} name={t} />
                ))}
              </div>
            )}
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", fontSize: "0.82rem", color: "var(--text-muted)" }}>
              <span>{detail.decisions.length} Entscheidung{detail.decisions.length === 1 ? "" : "en"}</span>
              <span>{detail.blockers.length} Blocker</span>
              <span>{detail.documents.length} Dokument{detail.documents.length === 1 ? "" : "e"}</span>
            </div>
          </div>

          {/* P20.5 (Übersicht-Tab, Ist-Daten-Zeile, siehe
              P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 9/10): nur auf Leaf-Phasen
              sichtbar/editierbar - analog zum Geplanten Ressourcenbedarf oben (jira_label wird
              beim Parent-Übergang serverseitig auf NULL gesetzt, gleicher Lifecycle wie
              plan_fte). Freitext + Datalist statt starrem Dropdown, damit auch ohne
              verknüpftes Jira-Projekt (leere Vorschlagsliste) editierbar bleibt. */}
          {!detail.has_children && (
            <div className="card" style={{ marginBottom: "0.75rem" }}>
              <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Ist-Daten</h4>
              <label>
                Jira-Label
                <input
                  key={`${detail.id}-jira-label-${detail.jira_label}`}
                  list="plan-phase-jira-label-suggestions"
                  defaultValue={detail.jira_label ?? ""}
                  placeholder="z. B. phase:configuration"
                  onBlur={(e) => {
                    const value = e.target.value.trim();
                    if (value !== (detail.jira_label ?? "")) update({ jira_label: value === "" ? null : value });
                  }}
                />
              </label>
              <datalist id="plan-phase-jira-label-suggestions">
                {jiraLabelSuggestions.map((l) => (
                  <option key={l} value={l} />
                ))}
              </datalist>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.4rem 0 0" }}>
                Worklogs von Issues mit diesem Label zählen als Ist-Aufwand dieser Phase. Ein
                Label darf pro Projekt nur einer Leaf-Phase zugeordnet sein.
              </p>
              {detail.jira_label && (
                <p style={{ fontSize: "0.82rem", margin: "0.4rem 0 0" }}>
                  {jiraMatchPreview == null ? (
                    <span style={{ color: "var(--text-muted)" }}>Lädt Treffer …</span>
                  ) : jiraMatchPreview.matched_issues === 0 ? (
                    <span style={{ color: "var(--text-muted)" }}>
                      Aktuell keine Treffer im letzten Sync-Stand - Label prüfen oder zuerst
                      im Jira-Tab synchronisieren.
                    </span>
                  ) : (
                    <>
                      <strong>{jiraMatchPreview.matched_issues}</strong> Issue
                      {jiraMatchPreview.matched_issues === 1 ? "" : "s"} ·{" "}
                      <strong>{jiraMatchPreview.matched_worklogs}</strong> Worklog
                      {jiraMatchPreview.matched_worklogs === 1 ? "" : "s"} ·{" "}
                      <strong>{jiraMatchPreview.total_hours} h</strong>
                      {jiraMatchPreview.sample_issue_keys.length > 0 && (
                        <span style={{ color: "var(--text-muted)" }}>
                          {" "}
                          ({jiraMatchPreview.sample_issue_keys.join(", ")})
                        </span>
                      )}
                    </>
                  )}
                </p>
              )}
            </div>
          )}

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Kennzahlen</h4>
            <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem" }}>
              <div>
                <strong>Planstunden:</strong> {fmtNum(detail.metrics.plan_hours, " h")}
              </div>
              <div>
                <strong>Zeitfortschritt:</strong> {fmtNum(detail.metrics.time_progress_pct, "%")}
                <span style={{ color: "var(--text-muted)", marginLeft: "0.4rem", fontSize: "0.78rem" }}>
                  (Anteil des geplanten Zeitraums, der vergangen ist - kein Health-/Fortschrittswert)
                </span>
              </div>
              {/* P20.4 (BD-1 CLOSED): null bleibt "noch nicht zugeordnet" statt einer
                  irreführenden 0 - siehe worklog_actuals.py/phase_metrics_calc.py. */}
              <div>
                <strong>Ist-Aufwand:</strong>{" "}
                {detail.metrics.ist_hours == null
                  ? "Noch nicht eindeutig zugeordnet"
                  : `${detail.metrics.ist_hours} h`}
              </div>
              <div>
                <strong>Aufwandsverbrauch:</strong> {fmtNum(detail.metrics.effort_consumption_pct, "%")}
              </div>
              {detail.metrics.remaining_plan_hours != null && (
                <div>
                  <strong>Verbleibender Planaufwand:</strong> {detail.metrics.remaining_plan_hours} h
                </div>
              )}
              {detail.metrics.overrun_hours != null && detail.metrics.overrun_hours > 0 && (
                <div style={{ color: "var(--rot)" }}>
                  <strong>Überverbrauch:</strong> {detail.metrics.overrun_hours} h
                </div>
              )}
            </div>
          </div>

        </>
      ) : tab === "kapazitaet" ? (
        detail.has_children ? (
          <div className="card">
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Kapazität (aggregiert)</h4>
            <p style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
              Diese Phase ist eine Sammelphase - Kapazitätsplanung und Personenbesetzung finden ausschließlich in
              ihren Unterphasen statt (keine doppelte Kapazitätsplanung auf Parent- und Kindebene).
            </p>
            <div style={{ fontSize: "0.85rem", marginTop: "0.4rem" }}>
              <strong>Aggregiert aus {detail.children.length} Unterphase(n):</strong>{" "}
              {detail.derived_capacity != null ? `${detail.derived_capacity.toFixed(2)} FTE` : "Noch keine Kapazität geplant"}
            </div>
          </div>
        ) : (
          <PlanPhaseCapacityTab
            projectId={projectId}
            planPhaseId={detail.id}
            planFte={detail.plan_fte}
            forecastStart={detail.forecast_start}
            forecastEnd={detail.forecast_end}
            metrics={detail.metrics}
            assignmentSummary={detail.assignment_summary}
            onChanged={reload}
            onUpdatePlanFte={(value) => update({ plan_fte: value })}
          />
        )
      ) : tab === "aktivitaet" ? (
        <>
          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Aktivität</h4>
            <ActivityFeed
              projectId={projectId}
              planPhaseId={planPhaseId}
              filterTypes={PHASE_ACTIVITY_TYPES}
              phaseTags={detail.tags}
              onOpenSection={() => setTab("aktivitaet")}
              onChanged={reload}
              refreshToken={activityVersion}
            />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Kommentare</h4>
            <NotesSection
              notes={detail.comments}
              onAdd={handleAddNote}
              onDelete={handleDeleteNote}
              projectId={projectId}
              planPhaseId={planPhaseId}
              phaseTags={detail.tags}
              onChanged={reload}
            />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Aufgaben</h4>
            <TaskList projectId={projectId} tasks={detail.tasks} onChanged={reload} planPhaseId={planPhaseId} />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Entscheidungen</h4>
            <DecisionList projectId={projectId} decisions={detail.decisions} onChanged={reload} planPhaseId={planPhaseId} />
          </div>

          <div className="card">
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Blocker</h4>
            <BlockerList projectId={projectId} blockers={detail.blockers} onChanged={reload} planPhaseId={planPhaseId} />
          </div>

          {/* P19.5: kompakte Meilensteine-Karte, für Leaf- UND Parent-Phasen (CONCEPT.md
              Abschnitt 5.5 - Milestones können auf beide zeigen). Wiederverwendung von
              MilestoneList.tsx, gefiltert auf diese Phase; Daten kommen bereits aus
              PlanPhaseDetail.milestones (kein zusätzlicher Round-Trip), Phasenliste aus der
              schon vorhandenen `allPhases`-Prop. */}
          <div className="card" style={{ marginTop: "0.75rem" }}>
            <MilestoneList
              projectId={projectId}
              planPhaseId={detail.id}
              milestones={detail.milestones}
              allPhases={allPhases}
              onChanged={reload}
              title="Meilensteine"
              addLabel="+ Meilenstein"
              emptyText="Noch keine Meilensteine für diese Phase."
            />
          </div>
        </>
      ) : (
        <div className="card">
          <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Dateien</h4>
          <DocumentListPanel
            projectId={projectId}
            documents={detail.documents}
            onRefresh={reload}
            entityFilter={{ entityType: "plan_phase", entityId: planPhaseId }}
            emptyText="Noch keine Dateien."
          />
        </div>
      )}

      {showCreateChild && detail && (
        <PlanPhaseCreateModal
          projectId={projectId}
          allPhases={allPhases}
          defaultParentPhaseId={detail.id}
          onClose={() => setShowCreateChild(false)}
          onCreated={reload}
        />
      )}
    </div>
  );
}
