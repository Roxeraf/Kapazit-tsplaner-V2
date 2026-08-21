import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import ConfirmDialog from "../../../components/ConfirmDialog";
import TagChip from "../../../components/TagChip";
import usePeopleMap from "../../../hooks/usePeopleMap";
import { PLAN_PHASE_STATUS_LABELS, type PlanPhase, type SubprojectDetail } from "../../../types";
import PlanPhaseCreateModal from "./PlanPhaseCreateModal";
import PlanPhaseGantt from "./PlanPhaseGantt";
import PlanPhaseWorkspace from "./PlanPhaseWorkspace";

// P11 (Planungs-/Kapazitätskonsolidierung): Liste ist ab jetzt eine kompakte Übersicht
// (scannable Karten: Name, Zeitraum, Status, Plan-FTE, Owner, Tags, "Öffnen"). Bearbeitung
// findet ausschließlich im PlanPhaseWorkspace-Drawer statt - der bisherige, parallel zum
// Drawer bestehende Voll-Inline-Editor (sechs Datumsfelder + PersonPicker + TagInput direkt in
// jeder Karte) ist entfernt. Das war das konkrete UX-Debt-Symptom aus dem Screenshot: der
// Drawer war nur zusätzlich eingebaut worden, statt den alten Editor zu ersetzen.
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

export default function PlanPhaseList({
  projectId,
  subprojects,
}: {
  projectId: number;
  subprojects: SubprojectDetail[];
}) {
  const [phases, setPhases] = useState<PlanPhase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<PlanPhase | null>(null);
  const [openPhaseId, setOpenPhaseId] = useState<number | null>(null);
  const [view, setView] = useState<"list" | "gantt">("list");
  const [showCreate, setShowCreate] = useState(false);
  // P15.4 (Collapse/Filter): rein frontendseitig, keine neue Backend-Logik.
  const [subprojectFilter, setSubprojectFilter] = useState<number | null | "all">("all");
  const [collapsedGroups, setCollapsedGroups] = useState<Set<number | null>>(new Set());
  const people = usePeopleMap();

  const refresh = () => {
    api.listPlanPhases(projectId).then(setPhases).catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId]);

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deletePlanPhase(toDelete.id);
    setToDelete(null);
    refresh();
  };

  const subprojectName = (id: number | null) =>
    id === null ? "Projektweit" : subprojects.find((sp) => sp.id === id)?.name ?? "Unbekanntes Teilprojekt";

  const toggleGroup = (id: number | null) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredPhases = subprojectFilter === "all" ? phases : phases.filter((p) => p.subproject_id === subprojectFilter);

  const groups = new Map<number | null, PlanPhase[]>();
  for (const phase of filteredPhases) {
    const list = groups.get(phase.subproject_id) ?? [];
    list.push(phase);
    groups.set(phase.subproject_id, list);
  }
  const groupOrder = [null, ...subprojects.map((sp) => sp.id)].filter((id) => groups.has(id));

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
          <button type="button" className="btn" onClick={() => setShowCreate(true)}>
            + Phase hinzufügen
          </button>
        </div>
      </div>
      {subprojects.length > 0 && (
        <div className="field-row" style={{ marginTop: 0, marginBottom: "0.6rem" }}>
          <label>
            Teilprojekt-Filter
            <select
              value={subprojectFilter === "all" ? "all" : subprojectFilter === null ? "none" : subprojectFilter}
              onChange={(e) => {
                const raw = e.target.value;
                setSubprojectFilter(raw === "all" ? "all" : raw === "none" ? null : Number(raw));
              }}
            >
              <option value="all">Alle</option>
              <option value="none">Projektweit</option>
              {subprojects.map((sp) => (
                <option key={sp.id} value={sp.id}>
                  {sp.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {view === "list" &&
        (filteredPhases.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Phasen geplant.</p>
        ) : (
          groupOrder.map((groupId) => (
            <div key={groupId ?? "project"} style={{ marginBottom: "1rem" }}>
              <button
                type="button"
                onClick={() => toggleGroup(groupId)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  border: "none",
                  background: "none",
                  cursor: "pointer",
                  padding: 0,
                  fontSize: "0.8rem",
                  color: "var(--text-muted)",
                  marginBottom: "0.3rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.03em",
                }}
              >
                <span>{collapsedGroups.has(groupId) ? "▸" : "▾"}</span>
                <span>
                  {subprojectName(groupId)} ({groups.get(groupId)!.length})
                </span>
              </button>
              {!collapsedGroups.has(groupId) &&
                groups.get(groupId)!.map((phase) => (
                <div
                  key={phase.id}
                  className="card"
                  style={{ marginBottom: "0.5rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem", cursor: "pointer" }}
                  onClick={() => setOpenPhaseId(phase.id)}
                >
                  <div className="toolbar">
                    <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>{phase.phase_type}</span>
                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                      <span className="legend-chip" style={{ background: "#eef3fa", padding: "0.1rem 0.55rem", borderRadius: "999px", fontSize: "0.78rem" }}>
                        {PLAN_PHASE_STATUS_LABELS[phase.status]}
                      </span>
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
                    <span>{fmtRange(phase.forecast_start, phase.forecast_end)}</span>
                    {phase.plan_fte != null && <span>{phase.plan_fte.toFixed(2)} FTE</span>}
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
              ))}
            </div>
          ))
        ))}

      {view === "gantt" && <PlanPhaseGantt phases={filteredPhases} subprojects={subprojects} onOpen={setOpenPhaseId} />}

      {showCreate && (
        <PlanPhaseCreateModal projectId={projectId} subprojects={subprojects} onClose={() => setShowCreate(false)} onCreated={refresh} />
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title="Phase löschen"
        message={`Phase "${toDelete?.phase_type}" wirklich löschen?`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />

      <PlanPhaseWorkspace
        planPhaseId={openPhaseId}
        projectId={projectId}
        subprojects={subprojects}
        onClose={() => setOpenPhaseId(null)}
        onChanged={refresh}
      />
    </div>
  );
}
