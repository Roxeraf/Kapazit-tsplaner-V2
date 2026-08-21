import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import ConfirmDialog from "../../../components/ConfirmDialog";
import PersonPicker from "../../../components/PersonPicker";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import type { BaselineSnapshotSummary } from "../../../types";

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

// Phase 26.2: POST /projects/{id}/baselines friert automatisch alle aktuellen
// PlanPhase/Milestone-Felder ein (backend/app/routers/baselines.py) - kein Formular mit
// Einzelwerten nötig, nur ein Name.
export default function BaselineList({ projectId }: { projectId: number }) {
  const [baselines, setBaselines] = useState<BaselineSnapshotSummary[]>([]);
  const [name, setName] = useState("");
  const [createdByPersonId, setCreatedByPersonId] = useState<number | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [toDelete, setToDelete] = useState<BaselineSnapshotSummary | null>(null);

  const refresh = () => {
    api.listBaselines(projectId).then(setBaselines).catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId]);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.createBaseline(projectId, { name: name.trim(), created_by_person_id: createdByPersonId, tags });
      setName("");
      setCreatedByPersonId(null);
      setTags([]);
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deleteBaseline(toDelete.id);
    setToDelete(null);
    refresh();
  };

  return (
    <div>
      <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Baselines</h3>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}
      {baselines.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Baseline gespeichert.</p>
      ) : (
        baselines.map((b) => (
          <div
            key={b.id}
            className="toolbar"
            style={{ padding: "0.4rem 0", borderBottom: "1px solid var(--border)", fontSize: "0.85rem" }}
          >
            <div>
              <span>
                <strong>{b.name}</strong> · {formatDateTime(b.created_at)} · {b.entry_count} Einträge
              </span>
              {b.tags.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.3rem 0" }}>
                  {b.tags.map((t) => (
                    <TagChip key={t} name={t} />
                  ))}
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => setToDelete(b)}
              style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
            >
              ×
            </button>
          </div>
        ))
      )}
      <div className="field-row" style={{ marginTop: "0.75rem" }}>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="z. B. Kickoff-Freigabe" />
        </label>
        <label>
          Erstellt von
          <PersonPicker value={createdByPersonId} onChange={setCreatedByPersonId} />
        </label>
        <label>
          Tags
          <TagInput value={tags} onChange={setTags} />
        </label>
        <button
          type="button"
          className="btn secondary"
          style={{ alignSelf: "flex-end" }}
          disabled={saving || !name.trim()}
          onClick={handleSave}
        >
          Baseline speichern
        </button>
      </div>

      <ConfirmDialog
        open={toDelete !== null}
        title="Baseline löschen"
        message={`Baseline "${toDelete?.name}" wirklich löschen?`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
