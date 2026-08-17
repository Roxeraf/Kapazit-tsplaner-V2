import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import AttachmentList from "../../../components/AttachmentList";
import AttachmentPicker from "../../../components/AttachmentPicker";
import ConfirmDialog from "../../../components/ConfirmDialog";
import PersonPicker from "../../../components/PersonPicker";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import usePeopleMap from "../../../hooks/usePeopleMap";
import {
  PLAN_PHASE_STATUS_LABELS,
  PLAN_PHASE_TYPE_SUGGESTIONS,
  type PlanPhase,
  type PlanPhaseStatus,
  type SubprojectDetail,
} from "../../../types";

const NO_SUBPROJECT = "__none__";

function clampProgress(raw: string): number | null {
  if (raw.trim() === "") return null;
  const value = Number(raw);
  if (!Number.isFinite(value)) return null;
  return Math.min(100, Math.max(0, value));
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
  const people = usePeopleMap();

  const [phaseType, setPhaseType] = useState("");
  const [subprojectId, setSubprojectId] = useState("");
  const [ownerPersonId, setOwnerPersonId] = useState<number | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);

  const refresh = () => {
    api.listPlanPhases(projectId).then(setPhases).catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId]);

  const handleAdd = async () => {
    if (!phaseType.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const phase = await api.createPlanPhase(projectId, {
        phase_type: phaseType.trim(),
        subproject_id: subprojectId ? Number(subprojectId) : null,
        owner_person_id: ownerPersonId,
        tags,
      });
      for (const file of files) {
        await api.uploadDocument(projectId, file, { entityType: "plan_phase", entityId: phase.id });
      }
      setPhaseType("");
      setSubprojectId("");
      setOwnerPersonId(null);
      setTags([]);
      setFiles([]);
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const update = async (phase: PlanPhase, changes: Partial<PlanPhase>) => {
    try {
      await api.updatePlanPhase(phase.id, changes);
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deletePlanPhase(toDelete.id);
    setToDelete(null);
    refresh();
  };

  const subprojectName = (id: number | null) =>
    id === null ? "Projektweit" : subprojects.find((sp) => sp.id === id)?.name ?? "Unbekanntes Teilprojekt";

  const groups = new Map<number | null, PlanPhase[]>();
  for (const phase of phases) {
    const list = groups.get(phase.subproject_id) ?? [];
    list.push(phase);
    groups.set(phase.subproject_id, list);
  }
  const groupOrder = [null, ...subprojects.map((sp) => sp.id)].filter((id) => groups.has(id));

  return (
    <div>
      <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Phasen</h3>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {phases.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Phasen geplant.</p>
      ) : (
        groupOrder.map((groupId) => (
          <div key={groupId ?? "project"} style={{ marginBottom: "1rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.3rem" }}>
              {subprojectName(groupId)}
            </div>
            {groups
              .get(groupId)!
              .map((phase) => (
                <div key={phase.id} className="card" style={{ marginBottom: "0.6rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}>
                  <div className="toolbar">
                    <input
                      key={phase.phase_type}
                      defaultValue={phase.phase_type}
                      list="plan-phase-type-suggestions"
                      style={{ fontWeight: 600, border: "none", background: "none", padding: 0, fontSize: "0.95rem" }}
                      onBlur={(e) => {
                        const value = e.target.value.trim();
                        if (value && value !== phase.phase_type) update(phase, { phase_type: value });
                      }}
                    />
                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                      <select
                        value={phase.status}
                        onChange={(e) => update(phase, { status: e.target.value as PlanPhaseStatus })}
                      >
                        {Object.entries(PLAN_PHASE_STATUS_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => setToDelete(phase)}
                        style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                      >
                        ×
                      </button>
                    </div>
                  </div>

                  <div className="field-row" style={{ marginTop: "0.5rem" }}>
                    <label>
                      Plan-Start
                      <input
                        key={`${phase.id}-bs-${phase.baseline_start}`}
                        type="date"
                        defaultValue={phase.baseline_start ?? ""}
                        onBlur={(e) => update(phase, { baseline_start: e.target.value || null })}
                      />
                    </label>
                    <label>
                      Plan-Ende
                      <input
                        key={`${phase.id}-be-${phase.baseline_end}`}
                        type="date"
                        defaultValue={phase.baseline_end ?? ""}
                        onBlur={(e) => update(phase, { baseline_end: e.target.value || null })}
                      />
                    </label>
                    <label>
                      Forecast-Start
                      <input
                        key={`${phase.id}-fs-${phase.forecast_start}`}
                        type="date"
                        defaultValue={phase.forecast_start ?? ""}
                        onBlur={(e) => update(phase, { forecast_start: e.target.value || null })}
                      />
                    </label>
                    <label>
                      Forecast-Ende
                      <input
                        key={`${phase.id}-fe-${phase.forecast_end}`}
                        type="date"
                        defaultValue={phase.forecast_end ?? ""}
                        onBlur={(e) => update(phase, { forecast_end: e.target.value || null })}
                      />
                    </label>
                  </div>
                  <div className="field-row">
                    <label>
                      Ist-Start
                      <input
                        key={`${phase.id}-as-${phase.actual_start}`}
                        type="date"
                        defaultValue={phase.actual_start ?? ""}
                        onBlur={(e) => update(phase, { actual_start: e.target.value || null })}
                      />
                    </label>
                    <label>
                      Ist-Ende
                      <input
                        key={`${phase.id}-ae-${phase.actual_end}`}
                        type="date"
                        defaultValue={phase.actual_end ?? ""}
                        onBlur={(e) => update(phase, { actual_end: e.target.value || null })}
                      />
                    </label>
                    <label>
                      Fortschritt (%)
                      <input
                        key={`${phase.id}-progress-${phase.progress}`}
                        type="number"
                        min={0}
                        max={100}
                        defaultValue={phase.progress ?? ""}
                        onBlur={(e) => update(phase, { progress: clampProgress(e.target.value) })}
                      />
                    </label>
                    <label>
                      Teilprojekt
                      <select
                        value={phase.subproject_id ?? NO_SUBPROJECT}
                        onChange={(e) =>
                          update(phase, {
                            subproject_id: e.target.value === NO_SUBPROJECT ? null : Number(e.target.value),
                          })
                        }
                      >
                        <option value={NO_SUBPROJECT}>Projektweit</option>
                        {subprojects.map((sp) => (
                          <option key={sp.id} value={sp.id}>
                            {sp.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <label style={{ display: "block", marginTop: "0.4rem" }}>
                    Owner
                    <PersonPicker
                      value={phase.owner_person_id}
                      onChange={(personId) => update(phase, { owner_person_id: personId })}
                    />
                  </label>
                  {phase.owner_person_id != null && (
                    <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.2rem 0 0" }}>
                      {people.get(phase.owner_person_id) ?? "…"}
                    </p>
                  )}
                  {phase.tags.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.3rem 0" }}>
                      {phase.tags.map((t) => (
                        <TagChip key={t} name={t} />
                      ))}
                    </div>
                  )}
                  <AttachmentList documents={phase.documents} />
                </div>
              ))}
          </div>
        ))
      )}

      <datalist id="plan-phase-type-suggestions">
        {PLAN_PHASE_TYPE_SUGGESTIONS.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>

      <div className="field-row" style={{ marginTop: "0.75rem", flexDirection: "column", alignItems: "stretch" }}>
        <label>
          Neue Phase
          <input
            value={phaseType}
            onChange={(e) => setPhaseType(e.target.value)}
            list="plan-phase-type-suggestions"
            placeholder="z. B. Pflichtenheft"
          />
        </label>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Teilprojekt
            <select value={subprojectId} onChange={(e) => setSubprojectId(e.target.value)}>
              <option value="">Projektweit</option>
              {subprojects.map((sp) => (
                <option key={sp.id} value={sp.id}>
                  {sp.name}
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
          + Phase hinzufügen
        </button>
      </div>

      <ConfirmDialog
        open={toDelete !== null}
        title="Phase löschen"
        message={`Phase "${toDelete?.phase_type}" wirklich löschen?`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
