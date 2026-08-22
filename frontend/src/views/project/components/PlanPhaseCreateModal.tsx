import { useState } from "react";
import { api } from "../../../api/client";
import PersonPicker from "../../../components/PersonPicker";
import TagInput from "../../../components/TagInput";
import {
  MAX_PLAN_PHASE_DEPTH,
  PLAN_PHASE_STATUS_LABELS,
  PLAN_PHASE_STATUS_OPTIONS,
  PLAN_PHASE_TYPE_SUGGESTIONS,
  planPhaseDepth,
  type PlanPhase,
  type PlanPhaseStatus,
} from "../../../types";

// P11 (Planungs-/Kapazitätskonsolidierung): kleiner Create-Flow als Modal statt des früheren
// großen Inline-Formulars in PlanPhaseList.tsx. Minimal: Name/Start/Ende (Pflicht). Optional:
// Status/Owner/Plan-FTE/Tags. Dateien gehören bewusst NICHT hierher - die werden nach dem
// Anlegen im Dateien-Tab des Workspace verwaltet.
//
// P18/B-6 (CONCEPT.md Abschnitt 6b.1/6b.2): "Übergeordnete Phase" ersetzt den früheren
// "Teilprojekt"-Select als primären Strukturierungs-Mechanismus (subproject_id bleibt nur
// noch compat-only im Modell bestehen, keine neue Subproject-UX). Phasen auf Ebene 3
// (MAX_PLAN_PHASE_DEPTH) werden aus der Auswahl ausgeblendet, da sie keine weitere Unterphase
// mehr aufnehmen dürfen (BD-10) - reine Frontend-Vorfilterung, das Backend validiert
// unabhängig davon noch einmal verbindlich.
export default function PlanPhaseCreateModal({
  projectId,
  allPhases,
  defaultParentPhaseId = null,
  onClose,
  onCreated,
}: {
  projectId: number;
  allPhases: PlanPhase[];
  defaultParentPhaseId?: number | null;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [phaseType, setPhaseType] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [status, setStatus] = useState<PlanPhaseStatus>("geplant");
  const [parentPhaseId, setParentPhaseId] = useState(defaultParentPhaseId != null ? String(defaultParentPhaseId) : "");
  const [ownerPersonId, setOwnerPersonId] = useState<number | null>(null);
  const [planFte, setPlanFte] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSave = phaseType.trim() && start && end;
  const eligibleParents = allPhases.filter((p) => planPhaseDepth(allPhases, p.id) < MAX_PLAN_PHASE_DEPTH);

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
        parent_phase_id: parentPhaseId ? Number(parentPhaseId) : null,
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
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>{defaultParentPhaseId != null ? "Unterphase hinzufügen" : "Phase hinzufügen"}</h3>
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
              Übergeordnete Phase
              <select value={parentPhaseId} onChange={(e) => setParentPhaseId(e.target.value)}>
                <option value="">— Top-Level —</option>
                {eligibleParents.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.phase_type}
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
              Geplanter Ressourcenbedarf (FTE)
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
