import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../../../api/client";
import TagChip from "../../../components/TagChip";
import usePeopleMap from "../../../hooks/usePeopleMap";
import { MAX_PLAN_PHASE_DEPTH, PLAN_PHASE_STATUS_LABELS, type PlanPhase } from "../../../types";
import PlanPhaseCreateModal from "./PlanPhaseCreateModal";
import PlanPhaseDeleteDialog from "./PlanPhaseDeleteDialog";
import PlanPhaseGantt from "./PlanPhaseGantt";
import PlanPhaseWorkspace from "./PlanPhaseWorkspace";

// P18/B-6 (CONCEPT.md Abschnitt 6b): Baum-UI statt Teilprojekt-Gruppierung - Phasen werden
// rekursiv nach parent_phase_id gruppiert (max. 3 Ebenen, BD-10), nicht mehr nach
// subproject_id (compat-only, keine neue Subproject-UX). Eine Parent-Phase (has_children)
// zeigt ihre abgeleiteten Werte (derived_forecast_start/end/capacity) statt editierbarer
// eigener Felder - Kapazitätsplanung bleibt ausschließlich im Leaf Workspace (Abschnitt 6b.3).
function fmtRange(start: string | null, end: string | null): string {
  const fmt = (iso: string) => {
    const d = new Date(iso + "T00:00:00");
    return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
  };
  if (start && end) return `${fmt(start)} – ${fmt(end)}`;
  if (start) return `ab ${fmt(start)}`;
  if (end) return `bis ${fmt(end)}`;
  return "Kein Termin";
}

export default function PlanPhaseList({ projectId }: { projectId: number }) {
  const [phases, setPhases] = useState<PlanPhase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<PlanPhase | null>(null);
  const [openPhaseId, setOpenPhaseId] = useState<number | null>(null);
  const [view, setView] = useState<"list" | "gantt">("list");
  const [showCreate, setShowCreate] = useState(false);
  const [createParentId, setCreateParentId] = useState<number | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<number>>(new Set());
  const people = usePeopleMap();
  // P19.4 (Tag-Dossier-Drilldown): erlaubt externe Navigation direkt in den Workspace einer
  // Phase (z.B. "?openPhase=<id>" von TagDossierPanel.tsx aus) - der Query-Param wird nach dem
  // Öffnen entfernt, damit ein erneuter Besuch der Planung ohne Query-Param nicht wieder
  // automatisch denselben Drawer öffnet.
  const [searchParams, setSearchParams] = useSearchParams();

  const refresh = () => {
    api.listPlanPhases(projectId).then(setPhases).catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId]);

  useEffect(() => {
    const raw = searchParams.get("openPhase");
    if (!raw) return;
    const id = Number(raw);
    if (Number.isFinite(id)) setOpenPhaseId(id);
    const params = new URLSearchParams(searchParams);
    params.delete("openPhase");
    setSearchParams(params, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleDeleted = () => {
    setToDelete(null);
    refresh();
  };

  const toggleGroup = (id: number) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const childrenOf = new Map<number | null, PlanPhase[]>();
  for (const phase of phases) {
    const list = childrenOf.get(phase.parent_phase_id) ?? [];
    list.push(phase);
    childrenOf.set(phase.parent_phase_id, list);
  }
  for (const list of childrenOf.values()) list.sort((a, b) => a.reihenfolge - b.reihenfolge || a.id - b.id);
  const topLevel = childrenOf.get(null) ?? [];

  const openCreateModal = (parentId: number | null) => {
    setCreateParentId(parentId);
    setShowCreate(true);
  };

  const renderPhase = (phase: PlanPhase, depth: number) => {
    const children = childrenOf.get(phase.id) ?? [];
    const collapsed = collapsedGroups.has(phase.id);
    const canHaveChildren = depth < MAX_PLAN_PHASE_DEPTH;
    return (
      <div key={phase.id} style={{ marginLeft: depth > 0 ? "1.4rem" : 0, marginBottom: "0.5rem" }}>
        <div
          className="card"
          style={{ padding: "0.6rem 0.85rem", fontSize: "0.88rem", cursor: "pointer" }}
          onClick={() => setOpenPhaseId(phase.id)}
        >
          <div className="toolbar">
            <span style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              {phase.has_children && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleGroup(phase.id);
                  }}
                  style={{ border: "none", background: "none", cursor: "pointer", padding: 0, color: "var(--text-muted)" }}
                >
                  {collapsed ? "▸" : "▾"}
                </button>
              )}
              <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>{phase.phase_type}</span>
              {phase.has_children && (
                <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                  (Sammelphase, {children.length} Unterphase{children.length === 1 ? "" : "n"})
                </span>
              )}
            </span>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span className="legend-chip" style={{ background: "#eef3fa", padding: "0.1rem 0.55rem", borderRadius: "999px", fontSize: "0.78rem" }}>
                {PLAN_PHASE_STATUS_LABELS[phase.status]}
              </span>
              {canHaveChildren && (
                <button
                  type="button"
                  className="btn secondary"
                  style={{ fontSize: "0.72rem", padding: "0.05rem 0.4rem" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    openCreateModal(phase.id);
                  }}
                >
                  + Unterphase
                </button>
              )}
              <button
                type="button"
                className="btn secondary"
                style={{ fontSize: "0.72rem", padding: "0.05rem 0.4rem" }}
                onClick={(e) => {
                  e.stopPropagation();
                  setOpenPhaseId(phase.id);
                }}
              >
                Öffnen →
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setToDelete(phase);
                }}
                style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
              >
                ×
              </button>
            </div>
          </div>
          <div style={{ display: "flex", gap: "0.9rem", flexWrap: "wrap", color: "var(--text-muted)", fontSize: "0.82rem", marginTop: "0.2rem" }}>
            <span>
              {phase.has_children
                ? `${fmtRange(phase.derived_forecast_start, phase.derived_forecast_end)} (abgeleitet)`
                : fmtRange(phase.forecast_start, phase.forecast_end)}
            </span>
            {phase.has_children
              ? phase.derived_capacity != null && <span>{phase.derived_capacity.toFixed(2)} FTE (aggregiert)</span>
              : phase.plan_fte != null && <span>{phase.plan_fte.toFixed(2)} FTE</span>}
            {phase.owner_person_id != null && <span>{people.get(phase.owner_person_id) ?? "…"}</span>}
          </div>
          {phase.tags.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginTop: "0.35rem" }}>
              {phase.tags.map((t) => (
                <TagChip key={t} name={t} />
              ))}
            </div>
          )}
        </div>
        {!collapsed && children.map((child) => renderPhase(child, depth + 1))}
      </div>
    );
  };

  return (
    <div>
      <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
        <h3 style={{ color: "var(--navy)", margin: 0 }}>Phasen</h3>
        <div style={{ display: "flex", gap: "0.4rem" }}>
          <button
            type="button"
            className="btn secondary"
            style={view === "list" ? { background: "var(--blau)", color: "#fff", borderColor: "var(--blau)" } : undefined}
            onClick={() => setView("list")}
          >
            Listenansicht
          </button>
          <button
            type="button"
            className="btn secondary"
            style={view === "gantt" ? { background: "var(--blau)", color: "#fff", borderColor: "var(--blau)" } : undefined}
            onClick={() => setView("gantt")}
          >
            Gantt-Ansicht
          </button>
          <button type="button" className="btn" onClick={() => openCreateModal(null)}>
            + Phase hinzufügen
          </button>
        </div>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {view === "list" &&
        (topLevel.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Phasen geplant.</p>
        ) : (
          topLevel.map((phase) => renderPhase(phase, 0))
        ))}

      {view === "gantt" && <PlanPhaseGantt phases={phases} onOpen={setOpenPhaseId} />}

      {showCreate && (
        <PlanPhaseCreateModal
          projectId={projectId}
          allPhases={phases}
          defaultParentPhaseId={createParentId}
          onClose={() => setShowCreate(false)}
          onCreated={refresh}
        />
      )}

      <PlanPhaseDeleteDialog phase={toDelete} onClose={() => setToDelete(null)} onDeleted={handleDeleted} />

      <PlanPhaseWorkspace
        planPhaseId={openPhaseId}
        projectId={projectId}
        allPhases={phases}
        onClose={() => setOpenPhaseId(null)}
        onChanged={refresh}
        onNavigate={setOpenPhaseId}
      />
    </div>
  );
}
