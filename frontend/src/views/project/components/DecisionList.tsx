import { useState } from "react";
import { api } from "../../../api/client";
import AttachmentList from "../../../components/AttachmentList";
import AttachmentPicker from "../../../components/AttachmentPicker";
import ConfirmDialog from "../../../components/ConfirmDialog";
import PersonPicker from "../../../components/PersonPicker";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import usePeopleMap from "../../../hooks/usePeopleMap";
import { DECISION_STATUS_LABELS, type Decision, type DecisionStatus } from "../../../types";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export default function DecisionList({
  projectId,
  decisions,
  onChanged,
}: {
  projectId: number;
  decisions: Decision[];
  onChanged: () => void;
}) {
  const [titel, setTitel] = useState("");
  const [beschreibung, setBeschreibung] = useState("");
  const [entschiedenVonPersonId, setEntschiedenVonPersonId] = useState<number | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Decision | null>(null);
  const people = usePeopleMap();

  const handleAdd = async () => {
    if (!titel.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const decision = await api.createDecision(projectId, {
        titel: titel.trim(),
        beschreibung: beschreibung.trim() || null,
        entschieden_von_person_id: entschiedenVonPersonId,
        tags,
      });
      for (const file of files) {
        await api.uploadDocument(projectId, file, { entityType: "decision", entityId: decision.id });
      }
      setTitel("");
      setBeschreibung("");
      setEntschiedenVonPersonId(null);
      setTags([]);
      setFiles([]);
      onChanged();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (decision: Decision, status: DecisionStatus) => {
    await api.updateDecision(decision.id, { status });
    onChanged();
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deleteDecision(toDelete.id);
    setToDelete(null);
    onChanged();
  };

  return (
    <div>
      {decisions.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Entscheidungen.</p>
      ) : (
        decisions.map((d) => (
          <div key={d.id} className="card" style={{ marginBottom: "0.6rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}>
            <div className="toolbar">
              <strong>{d.titel}</strong>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <select value={d.status} onChange={(e) => handleStatusChange(d, e.target.value as DecisionStatus)}>
                  {Object.entries(DECISION_STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setToDelete(d)}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            </div>
            {d.beschreibung && <p style={{ margin: "0.35rem 0" }}>{d.beschreibung}</p>}
            {(d.entschieden_am || d.entschieden_von_person_id != null) && (
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
                {d.entschieden_am && `Entschieden am ${formatDate(d.entschieden_am)}`}
                {d.entschieden_von_person_id != null &&
                  `${d.entschieden_am ? " von " : "Entschieden von "}${people.get(d.entschieden_von_person_id) ?? "…"}`}
              </p>
            )}
            {d.tags.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.3rem 0" }}>
                {d.tags.map((t) => (
                  <TagChip key={t} name={t} />
                ))}
              </div>
            )}
            <AttachmentList documents={d.documents} />
          </div>
        ))
      )}

      <div className="field-row" style={{ marginTop: "0.75rem", flexDirection: "column", alignItems: "stretch" }}>
        <label>
          Neue Entscheidung
          <input value={titel} onChange={(e) => setTitel(e.target.value)} placeholder="z. B. Rollout auf Oktober verschieben" />
        </label>
        <label>
          Beschreibung
          <input value={beschreibung} onChange={(e) => setBeschreibung(e.target.value)} placeholder="optional" />
        </label>
        <label>
          Entschieden von
          <PersonPicker value={entschiedenVonPersonId} onChange={setEntschiedenVonPersonId} />
        </label>
        <TagInput value={tags} onChange={setTags} />
        <AttachmentPicker files={files} onChange={setFiles} />
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-start" }} disabled={saving} onClick={handleAdd}>
          + Entscheidung hinzufügen
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      <ConfirmDialog
        open={toDelete !== null}
        title="Entscheidung löschen"
        message={`Entscheidung "${toDelete?.titel}" wirklich löschen? Angehängte Dateien bleiben im Dokumente-Tab erhalten.`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
