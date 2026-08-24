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
// und wird im Normalflow nicht mehr angezeigt.
// actual_date bleibt sekundär, read-only mit expliziter Korrektur-Aktion, analog
// PlanPhaseWorkspace "Tatsächlicher Verlauf".
// P15.1/15.2 (Milestone UX Completion): analog zur PlanPhase-Liste (P11) ist die Karte im
// Normalzustand eine kompakte, scannbare Zeile (Name/Datum/Status/Owner/Teilprojekt/Tags) -
// Bearbeitung erfolgt über "Bearbeiten", nicht über sechs dauerhaft offene Eingabefelder pro
// Karte. Kein neues Drawer-Bauteil (Milestone ist einfach genug für Inline-Expand statt eines
// eigenen Workspace, siehe CONCEPT.md Abschnitt 0 "keine neue Grob-/Feinplanungsarchitektur").
//
// P19.5 (P19_PLANPHASE_WORKSPACE_UX_AUDIT.md Abschnitt 3.12/14): dieselbe Komponente wird jetzt
// zusätzlich als kompakte "Meilensteine dieser Phase"-Karte im PlanPhaseWorkspace gemountet
// (Wiederverwendung, kein Duplikat, keine zweite Milestone-Engine). Dafür optional:
// - `planPhaseId`: filtert die Anzeige auf genau diese Phase und wird als Default für neue
//   Milestones vorbelegt (weiterhin änderbar im Anlage-Formular).
// - `milestones`/`allPhases`: bereits geladene Daten (z.B. aus PlanPhaseDetail bzw. der schon
//   im Workspace vorhandenen `allPhases`-Prop) - wenn gesetzt, verzichtet die Komponente auf
//   ihren eigenen Fetch und spart so den sonst nötigen zusätzlichen Round-Trip.
// - `title`/`addLabel`/`emptyText`: Beschriftungs-Overrides für den phasenscoped Kontext
//   ("Meilensteine" statt "Milestones", siehe Auftragstext). ProjectPlanningTab.tsx ruft die
//   Komponente unverändert ohne diese Props auf - Verhalten dort bleibt exakt wie zuvor.
export default function MilestoneList({
  projectId,
  planPhaseId,
  milestones: milestonesProp,
  allPhases: allPhasesProp,
  onChanged,
  title = "Milestones",
  addLabel = "+ Milestone hinzufügen",
  emptyText = "Noch keine Milestones geplant.",
}: {
  projectId: number;
  planPhaseId?: number;
  milestones?: Milestone[];
  allPhases?: PlanPhase[];
  onChanged?: () => void;
  title?: string;
  addLabel?: string;
  emptyText?: string;
}) {
  const [milestones, setMilestones] = useState<Milestone[]>(milestonesProp ?? []);
  const [phases, setPhases] = useState<PlanPhase[]>(allPhasesProp ?? []);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Milestone | null>(null);
  const [correctingId, setCorrectingId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const people = usePeopleMap();

  const [name, setName] = useState("");
  const [formPlanPhaseId, setFormPlanPhaseId] = useState(planPhaseId != null ? String(planPhaseId) : "");
  const [ownerPersonId, setOwnerPersonId] = useState<number | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);

  // Wenn der Aufrufer bereits geladene Daten übergibt (Workspace-Fall), diese übernehmen statt
  // selbst zu fetchen. Ohne `milestones`/`allPhases`-Prop (ProjectPlanningTab-Fall) unverändert
  // ein eigener Fetch beim Mount bzw. nach jeder Mutation.
  const fetchMilestones = () => {
    if (milestonesProp !== undefined) return;
    api.listMilestones(projectId).then(setMilestones).catch((e) => setError(String(e)));
  };
  const fetchPhases = () => {
    if (allPhasesProp !== undefined) return;
    api.listPlanPhases(projectId).then(setPhases).catch(() => setPhases([]));
  };

  useEffect(() => {
    fetchMilestones();
    fetchPhases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    if (milestonesProp !== undefined) setMilestones(milestonesProp);
  }, [milestonesProp]);

  useEffect(() => {
    if (allPhasesProp !== undefined) setPhases(allPhasesProp);
  }, [allPhasesProp]);

  const refresh = () => {
    fetchMilestones();
    fetchPhases();
    onChanged?.();
  };

  const handleAdd = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const milestone = await api.createMilestone(projectId, {
        name: name.trim(),
        plan_phase_id: formPlanPhaseId ? Number(formPlanPhaseId) : null,
        owner_person_id: ownerPersonId,
        tags,
      });
      for (const file of files) {
        await api.uploadDocument(projectId, file, { entityType: "milestone", entityId: milestone.id });
      }
      setName("");
      setFormPlanPhaseId(planPhaseId != null ? String(planPhaseId) : "");
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

  const visibleMilestones = planPhaseId != null ? milestones.filter((m) => m.plan_phase_id === planPhaseId) : milestones;

  return (
    <div>
      <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
        <h3 style={{ color: "var(--navy)", margin: 0 }}>{title}</h3>
        <button type="button" className="btn" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "Abbrechen" : addLabel}
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {visibleMilestones.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>{emptyText}</p>
      ) : (
        visibleMilestones.map((m) => (
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
                <select value={formPlanPhaseId} onChange={(e) => setFormPlanPhaseId(e.target.value)}>
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
              {addLabel}
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
