import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import ActivityFeed from "./ActivityFeed";
import AttachmentList from "../../../components/AttachmentList";
import BlockerList from "./BlockerList";
import DecisionList from "./DecisionList";
import NotesSection from "../../../components/NotesSection";
import TaskList from "./TaskList";
import TagChip from "../../../components/TagChip";
import usePeopleMap from "../../../hooks/usePeopleMap";
import { PLAN_PHASE_STATUS_LABELS, type EntityType, type PlanPhaseDetail } from "../../../types";

// Phase 26.10: PlanPhase Workspace (P7) - rechtsseitiger Drawer mit zwei Sub-Tabs.
// Übersicht = read-only Phasendetails + Rohmetriken (keine Ampel, BD-1: Ist-Stunden immer
// None). Kommunikation = phasenbezogener Activity Feed + Notizen/Aufgaben/Entscheidungen/
// Blocker, alle mit plan_phase_id verknüpft (P3-Endpoints, backend/app/routers/planning.py
// + communication.py).
const PHASE_ACTIVITY_TYPES: EntityType[] = ["comment", "decision", "task", "blocker"];

function fmtNum(v: number | null | undefined, suffix = ""): string {
  return v == null ? "\u2014" : `${v}${suffix}`;
}

function fmtDate(iso: string | null): string {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export default function PlanPhaseWorkspace({
  planPhaseId,
  projectId,
  onClose,
  onChanged,
}: {
  planPhaseId: number | null;
  projectId: number;
  onClose: () => void;
  onChanged?: () => void;
}) {
  const [detail, setDetail] = useState<PlanPhaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"uebersicht" | "kommunikation">("uebersicht");
  const people = usePeopleMap();

  const load = () => {
    if (planPhaseId == null) return;
    setError(null);
    api.getPlanPhaseDetail(planPhaseId).then(setDetail).catch((e) => setError(String(e)));
  };

  // Beim Phasenwechsel: Detail zurücksetzen (vermeidet Stale-Data-Flash) und neu laden.
  // Nach Mutationen (reload) wird load() direkt ohne Zurücksetzen aufgerufen.
  useEffect(() => {
    setDetail(null);
    load();
  }, [planPhaseId]);

  const reload = () => {
    load();
    onChanged?.();
  };

  if (planPhaseId == null) return null;

  const handleAddNote = async (input: { text: string; tags: string[]; files: File[] }) => {
    const comment = await api.createComment(projectId, {
      text: input.text,
      tags: input.tags,
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
        <button type="button" className="btn secondary" onClick={onClose}>
          Schließen
        </button>
      </div>

      <div style={{ display: "flex", gap: "0.35rem", marginBottom: "0.75rem" }}>
        <button
          type="button"
          className={tab === "uebersicht" ? "btn" : "btn secondary"}
          onClick={() => setTab("uebersicht")}
        >
          Übersicht
        </button>
        <button
          type="button"
          className={tab === "kommunikation" ? "btn" : "btn secondary"}
          onClick={() => setTab("kommunikation")}
        >
          Kommunikation
        </button>
      </div>

      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {!detail ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Lade Phase …</p>
      ) : tab === "uebersicht" ? (
        <>
          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Phasendetails</h4>
            <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem" }}>
              <div>
                <strong>Phastyp:</strong> {detail.phase_type}
              </div>
              <div>
                <strong>Status:</strong> {PLAN_PHASE_STATUS_LABELS[detail.status]}
              </div>
              <div>
                <strong>Teilprojekt:</strong>{" "}
                {detail.subproject_id == null ? "Projektweit" : `Teilprojekt #${detail.subproject_id}`}
              </div>
              <div>
                <strong>Plan-Start:</strong> {fmtDate(detail.baseline_start)}
              </div>
              <div>
                <strong>Plan-Ende:</strong> {fmtDate(detail.baseline_end)}
              </div>
              <div>
                <strong>Forecast-Start:</strong> {fmtDate(detail.forecast_start)}
              </div>
              <div>
                <strong>Forecast-Ende:</strong> {fmtDate(detail.forecast_end)}
              </div>
              <div>
                <strong>Ist-Start:</strong> {fmtDate(detail.actual_start)}
              </div>
              <div>
                <strong>Ist-Ende:</strong> {fmtDate(detail.actual_end)}
              </div>
              <div>
                <strong>Owner:</strong>{" "}
                {detail.owner_person_id != null ? (people.get(detail.owner_person_id) ?? "\u2026") : "\u2014"}
              </div>
              <div>
                <strong>Plan-FTE:</strong> {fmtNum(detail.plan_fte, " FTE")}
              </div>
            </div>
            {detail.tags.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.5rem 0" }}>
                {detail.tags.map((t) => (
                  <TagChip key={t} name={t} />
                ))}
              </div>
            )}
            <AttachmentList documents={detail.documents} />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Metriken</h4>
            <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem" }}>
              <div>
                <strong>Zeitfortschritt:</strong> {fmtNum(detail.metrics.time_progress_pct, "%")}
              </div>
              <div>
                <strong>Planstunden:</strong> {fmtNum(detail.metrics.plan_hours, " h")}
              </div>
              <div>
                <strong>Aufwandsverbrauch:</strong> {"\u2014"}
              </div>
              <div>
                <strong>Ist-Stunden:</strong> {"\u2014"}
              </div>
              <div>
                <strong>Reconciliation Headline:</strong>{" "}
                {fmtNum(detail.metrics.reconciliation.headline_fte, " FTE")}
              </div>
              <div>
                <strong>Reconciliation Aufschlüsselung:</strong>{" "}
                {fmtNum(detail.metrics.reconciliation.breakdown_fte, " FTE")}
              </div>
              <div>
                <strong>Reconciliation offen:</strong>{" "}
                {fmtNum(detail.metrics.reconciliation.open_fte, " FTE")}
              </div>
            </div>
          </div>

          <div className="card">
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Ressourcenbedarfe</h4>
            {detail.resource_demands.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: 0 }}>Keine Bedarfe.</p>
            ) : (
              <table style={{ width: "100%", fontSize: "0.82rem", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ textAlign: "left", color: "var(--text-muted)" }}>
                    <th style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>Rolle</th>
                    <th style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>Periode</th>
                    <th style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>FTE</th>
                    <th style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>Zugewiesen</th>
                    <th style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>Lücke</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.resource_demands.map((d) => (
                    <tr key={d.id}>
                      <td style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>
                        {d.resource_role_name}
                      </td>
                      <td style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>{d.period}</td>
                      <td style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>{d.fte}</td>
                      <td style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>
                        {d.assigned_fte}
                      </td>
                      <td style={{ padding: "0.2rem 0.3rem", borderBottom: "1px solid var(--border)" }}>
                        {d.allocation_gap}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      ) : (
        <>
          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Aktivität</h4>
            <ActivityFeed
              projectId={projectId}
              planPhaseId={planPhaseId}
              filterTypes={PHASE_ACTIVITY_TYPES}
              onOpenSection={() => setTab("kommunikation")}
              onChanged={reload}
            />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Notizen</h4>
            <NotesSection notes={detail.comments} onAdd={handleAddNote} onDelete={handleDeleteNote} />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Aufgaben</h4>
            <TaskList
              projectId={projectId}
              tasks={detail.tasks}
              onChanged={reload}
              planPhaseId={planPhaseId}
            />
          </div>

          <div className="card" style={{ marginBottom: "0.75rem" }}>
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Entscheidungen</h4>
            <DecisionList
              projectId={projectId}
              decisions={detail.decisions}
              onChanged={reload}
              planPhaseId={planPhaseId}
            />
          </div>

          <div className="card">
            <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Blocker</h4>
            <BlockerList
              projectId={projectId}
              blockers={detail.blockers}
              onChanged={reload}
              planPhaseId={planPhaseId}
            />
          </div>
        </>
      )}
    </div>
  );
}
