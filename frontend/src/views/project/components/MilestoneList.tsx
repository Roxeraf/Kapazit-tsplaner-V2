import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import AttachmentList from "../../../components/AttachmentList";
import AttachmentPicker from "../../../components/AttachmentPicker";
import ConfirmDialog from "../../../components/ConfirmDialog";
import PersonPicker from "../../../components/PersonPicker";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import usePeopleMap from "../../../hooks/usePeopleMap";
import { MILESTONE_STATUS_LABELS, type Milestone, type MilestoneStatus, type SubprojectDetail } from "../../../types";

const NO_SUBPROJECT = "__none__";

export default function MilestoneList({
  projectId,
  subprojects,
}: {
  projectId: number;
  subprojects: SubprojectDetail[];
}) {
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Milestone | null>(null);
  const people = usePeopleMap();

  const [name, setName] = useState("");
  const [subprojectId, setSubprojectId] = useState("");
  const [ownerPersonId, setOwnerPersonId] = useState<number | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);

  const refresh = () => {
    api.listMilestones(projectId).then(setMilestones).catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId]);

  const handleAdd = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const milestone = await api.createMilestone(projectId, {
        name: name.trim(),
        subproject_id: subprojectId ? Number(subprojectId) : null,
        owner_person_id: ownerPersonId,
        tags,
      });
      for (const file of files) {
        await api.uploadDocument(projectId, file, { entityType: "milestone", entityId: milestone.id });
      }
      setName("");
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

  const subprojectName = (id: number | null) =>
    id === null ? null : subprojects.find((sp) => sp.id === id)?.name ?? "Unbekanntes Teilprojekt";

  return (
    <div>
      <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Milestones</h3>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {milestones.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Milestones geplant.</p>
      ) : (
        milestones.map((m) => (
          <div key={m.id} className="card" style={{ marginBottom: "0.6rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}>
            <div className="toolbar">
              <input
                key={m.name}
                defaultValue={m.name}
                style={{ fontWeight: 600, border: "none", background: "none", padding: 0, fontSize: "0.95rem" }}
                onBlur={(e) => {
                  const value = e.target.value.trim();
                  if (value && value !== m.name) update(m, { name: value });
                }}
              />
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <select value={m.status} onChange={(e) => update(m, { status: e.target.value as MilestoneStatus })}>
                  {Object.entries(MILESTONE_STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setToDelete(m)}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            </div>
            {subprojectName(m.subproject_id) && (
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.2rem 0 0" }}>
                Teilprojekt: {subprojectName(m.subproject_id)}
              </p>
            )}
            <div className="field-row" style={{ marginTop: "0.5rem" }}>
              <label>
                Plan-Datum
                <input
                  key={`${m.id}-bd-${m.baseline_date}`}
                  type="date"
                  defaultValue={m.baseline_date ?? ""}
                  onBlur={(e) => update(m, { baseline_date: e.target.value || null })}
                />
              </label>
              <label>
                Forecast-Datum
                <input
                  key={`${m.id}-fd-${m.forecast_date}`}
                  type="date"
                  defaultValue={m.forecast_date ?? ""}
                  onBlur={(e) => update(m, { forecast_date: e.target.value || null })}
                />
              </label>
              <label>
                Ist-Datum
                <input
                  key={`${m.id}-ad-${m.actual_date}`}
                  type="date"
                  defaultValue={m.actual_date ?? ""}
                  onBlur={(e) => update(m, { actual_date: e.target.value || null })}
                />
              </label>
              <label>
                Teilprojekt
                <select
                  value={m.subproject_id ?? NO_SUBPROJECT}
                  onChange={(e) =>
                    update(m, { subproject_id: e.target.value === NO_SUBPROJECT ? null : Number(e.target.value) })
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
              <PersonPicker value={m.owner_person_id} onChange={(personId) => update(m, { owner_person_id: personId })} />
            </label>
            {m.owner_person_id != null && (
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.2rem 0 0" }}>
                {people.get(m.owner_person_id) ?? "…"}
              </p>
            )}
            {m.tags.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.3rem 0" }}>
                {m.tags.map((t) => (
                  <TagChip key={t} name={t} />
                ))}
              </div>
            )}
            <AttachmentList documents={m.documents} />
          </div>
        ))
      )}

      <div className="field-row" style={{ marginTop: "0.75rem", flexDirection: "column", alignItems: "stretch" }}>
        <label>
          Neuer Milestone
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="z. B. GoLive" />
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
          + Milestone hinzufügen
        </button>
      </div>

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
