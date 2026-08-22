import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import AttachmentList from "../../../components/AttachmentList";
import AttachmentPicker from "../../../components/AttachmentPicker";
import ConfirmDialog from "../../../components/ConfirmDialog";
import PersonPicker from "../../../components/PersonPicker";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import usePeopleMap from "../../../hooks/usePeopleMap";
import { MILESTONE_STATUS_LABELS, type Milestone, type MilestoneStatus, type PlanPhase } from "../../../types";

const NO_PLAN_PHASE = "__none__";

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso + "T00:00:00");
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

// P11 (Planungs-/Kapazitätskonsolidierung): dieselbe UX-Regel wie bei PlanPhase - normal ist
// EIN Datumsfeld ("Datum" = forecast_date, der aktuelle Plan). baseline_date ist compat-only
// und wird im Normalflow nicht mehr angezeigt (siehe BaselineList für Planstände).
// actual_date bleibt sekundär, read-only mit expliziter Korrektur-Aktion, analog
// PlanPhaseWorkspace "Tatsächlicher Verlauf".
// P15.1/15.2 (Milestone UX Completion): analog zur PlanPhase-Liste (P11) ist die Karte im
// Normalzustand eine kompakte, scannbare Zeile (Name/Datum/Status/Owner/Teilprojekt/Tags) -
// Bearbeitung erfolgt über "Bearbeiten", nicht über sechs dauerhaft offene Eingabefelder pro
// Karte. Kein neues Drawer-Bauteil (Milestone ist einfach genug für Inline-Expand statt eines
// eigenen Workspace, siehe CONCEPT.md Abschnitt 0 "keine neue Grob-/Feinplanungsarchitektur").
export default function MilestoneList({ projectId }: { projectId: number }) {
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [phases, setPhases] = useState<PlanPhase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Milestone | null>(null);
  const [correctingId, setCorrectingId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const people = usePeopleMap();

  const [name, setName] = useState("");
  const [planPhaseId, setPlanPhaseId] = useState("");
  const [ownerPersonId, setOwnerPersonId] = useState<number | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);

  const refresh = () => {
    api.listMilestones(projectId).then(setMilestones).catch((e) => setError(String(e)));
    api.listPlanPhases(projectId).then(setPhases).catch(() => setPhases([]));
  };

  useEffect(refresh, [projectId]);

  const handleAdd = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const milestone = await api.createMilestone(projectId, {
        name: name.trim(),
        plan_phase_id: planPhaseId ? Number(planPhaseId) : null,
        owner_person_id: ownerPersonId,
        tags,
      });
      for (const file of files) {
        await api.uploadDocument(projectId, file, { entityType: "milestone", entityId: milestone.id });
      }
      setName("");
      setPlanPhaseId("");
      setOwnerPersonId(null);
      setTags([]);
      setFiles([]);
      setShowCreate(false);
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const update = async (milestone: Milestone, changes: Partial<Milestone>) => {
    try {
      await api.updateMilestone(milestone.id, changes);
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deleteMilestone(toDelete.id);
    setToDelete(null);
    refresh();
  };

  const planPhaseName = (id: number | null) =>
    id === null ? null : phases.find((p) => p.id === id)?.phase_type ?? "Unbekannte Phase";

  return (
    <div>
      <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
        <h3 style={{ color: "var(--navy)", margin: 0 }}>Milestones</h3>
        <button type="button" className="btn" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "Abbrechen" : "+ Milestone hinzufügen"}
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {milestones.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Milestones geplant.</p>
      ) : (
        milestones.map((m) => (
          <div key={m.id} className="card" style={{ marginBottom: "0.5rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}>
            <div className="toolbar" style={{ cursor: "pointer" }} onClick={() => setExpandedId(expandedId === m.id ? null : m.id)}>
              <span style={{ fontWeight: 600, fontSize: "0.95rem" }}>
                ◆ {m.name}
              </span>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <span className="legend-chip" style={{ background: "#eef3fa", padding: "0.1rem 0.55rem", borderRadius: "999px", fontSize: "0.78rem" }}>
                  {MILESTONE_STATUS_LABELS[m.status]}
                </span>
                <button
                  type="button"
                  className="btn secondary"
                  style={{ fontSize: "0.72rem", padding: "0.05rem 0.4rem" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedId(expandedId === m.id ? null : m.id);
                  }}
                >
                  {expandedId === m.id ? "Fertig" : "Bearbeiten"}
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setToDelete(m);
                  }}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            </div>
            <div style={{ display: "flex", gap: "0.9rem", flexWrap: "wrap", color: "var(--text-muted)", fontSize: "0.82rem", marginTop: "0.2rem" }}>
              <span>{fmtDate(m.forecast_date)}</span>
              <span>{planPhaseName(m.plan_phase_id) ?? "Projektweit"}</span>
              {m.owner_person_id != null && <span>{people.get(m.owner_person_id) ?? "…"}</span>}
            </div>
            {m.tags.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginTop: "0.35rem" }}>
                {m.tags.map((t) => (
                  <TagChip key={t} name={t} />
                ))}
              </div>
            )}

            {expandedId === m.id && (
              <div style={{ marginTop: "0.6rem", paddingTop: "0.5rem", borderTop: "1px solid var(--border)" }}>
                <label>
                  Name
                  <input
                    key={m.name}
                    defaultValue={m.name}
                    onBlur={(e) => {
                      const value = e.target.value.trim();
                      if (value && value !== m.name) update(m, { name: value });
                    }}
                  />
                </label>
                <div className="field-row" style={{ marginTop: "0.5rem" }}>
                  <label>
                    Datum
                    <input
                      key={`${m.id}-fd-${m.forecast_date}`}
                      type="date"
                      defaultValue={m.forecast_date ?? ""}
                      onBlur={(e) => update(m, { forecast_date: e.target.value || null })}
                    />
                  </label>
                  <label>
                    Status
                    <select value={m.status} onChange={(e) => update(m, { status: e.target.value as MilestoneStatus })}>
                      {Object.entries(MILESTONE_STATUS_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="field-row" style={{ marginTop: 0 }}>
                  <label>
                    Übergeordnete Phase
                    <select
                      value={m.plan_phase_id ?? NO_PLAN_PHASE}
                      onChange={(e) =>
                        update(m, { plan_phase_id: e.target.value === NO_PLAN_PHASE ? null : Number(e.target.value) })
                      }
                    >
                      <option value={NO_PLAN_PHASE}>Projektweit</option>
                      {phases.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.phase_type}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Owner
                    <PersonPicker value={m.owner_person_id} onChange={(personId) => update(m, { owner_person_id: personId })} />
                  </label>
                </div>

                <div className="toolbar" style={{ marginTop: "0.35rem" }}>
                  <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                    Ist-Datum: {fmtDate(m.actual_date)}
                  </span>
                  <button
                    type="button"
                    className="btn secondary"
                    style={{ fontSize: "0.72rem", padding: "0.05rem 0.4rem" }}
                    onClick={() => setCorrectingId(correctingId === m.id ? null : m.id)}
                  >
                    {correctingId === m.id ? "Fertig" : "Ist-Datum korrigieren"}
                  </button>
                </div>
                {correctingId === m.id && (
                  <input
                    key={`${m.id}-ad-${m.actual_date}`}
                    type="date"
                    defaultValue={m.actual_date ?? ""}
                    onBlur={(e) => update(m, { actual_date: e.target.value || null })}
                    style={{ marginTop: "0.3rem" }}
                  />
                )}

                <label style={{ display: "block", marginTop: "0.4rem" }}>
                  Tags
                  <TagInput value={m.tags} onChange={(newTags) => update(m, { tags: newTags })} />
                </label>
                <AttachmentList documents={m.documents} />
              </div>
            )}
          </div>
        ))
      )}

      {showCreate && (
        <div className="card" style={{ marginTop: "0.75rem", background: "#f8fafc" }}>
          <div className="field-row" style={{ marginTop: 0, flexDirection: "column", alignItems: "stretch" }}>
            <label>
              Neuer Milestone
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="z. B. GoLive" />
            </label>
            <div className="field-row" style={{ marginTop: 0 }}>
              <label>
                Übergeordnete Phase
                <select value={planPhaseId} onChange={(e) => setPlanPhaseId(e.target.value)}>
                  <option value="">Projektweit</option>
                  {phases.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.phase_type}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Owner
                <PersonPicker value={ownerPersonId} onChange={setOwnerPersonId} />
              </label>
            </div>
            <TagInput value={tags} onChange={setTags} />
            <AttachmentPicker files={files} onChange={setFiles} />
            <button type="button" className="btn secondary" style={{ alignSelf: "flex-start" }} disabled={saving} onClick={handleAdd}>
              + Milestone hinzufügen
            </button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title="Milestone löschen"
        message={`Milestone "${toDelete?.name}" wirklich löschen?`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
