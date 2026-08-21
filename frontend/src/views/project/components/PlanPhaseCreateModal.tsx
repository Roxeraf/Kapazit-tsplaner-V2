import { useState } from "react";
import { api } from "../../../api/client";
import PersonPicker from "../../../components/PersonPicker";
import TagInput from "../../../components/TagInput";
import {
  PLAN_PHASE_STATUS_LABELS,
  PLAN_PHASE_STATUS_OPTIONS,
  PLAN_PHASE_TYPE_SUGGESTIONS,
  type PlanPhaseStatus,
  type SubprojectDetail,
} from "../../../types";

// P11 (Planungs-/Kapazitätskonsolidierung): kleiner Create-Flow als Modal statt des früheren
// großen Inline-Formulars in PlanPhaseList.tsx. Minimal: Name/Start/Ende (Pflicht). Optional:
// Status/Teilprojekt/Owner/Plan-FTE/Tags. Dateien gehören bewusst NICHT hierher - die werden
// nach dem Anlegen im Dateien-Tab des Workspace verwaltet.
export default function PlanPhaseCreateModal({
  projectId,
  subprojects,
  onClose,
  onCreated,
}: {
  projectId: number;
  subprojects: SubprojectDetail[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [phaseType, setPhaseType] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [status, setStatus] = useState<PlanPhaseStatus>("geplant");
  const [subprojectId, setSubprojectId] = useState("");
  const [ownerPersonId, setOwnerPersonId] = useState<number | null>(null);
  const [planFte, setPlanFte] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSave = phaseType.trim() && start && end;

  const handleSave = async () => {
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      await api.createPlanPhase(projectId, {
        phase_type: phaseType.trim(),
        forecast_start: start,
        forecast_end: end,
        status,
        subproject_id: subprojectId ? Number(subprojectId) : null,
        owner_person_id: ownerPersonId,
        plan_fte: planFte.trim() === "" ? null : Number(planFte),
        tags,
      });
      onCreated();
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0, 20, 40, 0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}
    >
      <div
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        className="card"
        style={{ maxWidth: "28rem", width: "90%", maxHeight: "90vh", overflowY: "auto" }}
      >
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Phase hinzufügen</h3>
        {error && <p style={{ color: "var(--rot)", fontSize: "0.85rem" }}>{error}</p>}

        <div className="field-row" style={{ marginTop: 0, flexDirection: "column", alignItems: "stretch" }}>
          <label>
            Name
            <input
              autoFocus
              value={phaseType}
              onChange={(e) => setPhaseType(e.target.value)}
              list="plan-phase-type-suggestions-create"
              placeholder="z. B. Pflichtenheft"
            />
          </label>
          <datalist id="plan-phase-type-suggestions-create">
            {PLAN_PHASE_TYPE_SUGGESTIONS.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>

          <div className="field-row" style={{ marginTop: 0 }}>
            <label>
              Start
              <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            </label>
            <label>
              Ende
              <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </label>
          </div>

          <div className="field-row" style={{ marginTop: 0 }}>
            <label>
              Status
              <select value={status} onChange={(e) => setStatus(e.target.value as PlanPhaseStatus)}>
                {PLAN_PHASE_STATUS_OPTIONS.map((value) => (
                  <option key={value} value={value}>
                    {PLAN_PHASE_STATUS_LABELS[value]}
                  </option>
                ))}
              </select>
            </label>
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
          </div>

          <div className="field-row" style={{ marginTop: 0 }}>
            <label>
              Owner
              <PersonPicker value={ownerPersonId} onChange={setOwnerPersonId} />
            </label>
            <label>
              Plan-FTE
              <input type="number" min={0} step={0.05} value={planFte} onChange={(e) => setPlanFte(e.target.value)} placeholder="optional" />
            </label>
          </div>

          <label>
            Tags
            <TagInput value={tags} onChange={setTags} />
          </label>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1rem" }}>
          <button type="button" className="btn secondary" onClick={onClose}>
            Abbrechen
          </button>
          <button type="button" className="btn" disabled={!canSave || saving} onClick={handleSave}>
            {saving ? "Speichert …" : "Phase anlegen"}
          </button>
        </div>
      </div>
    </div>
  );
}
