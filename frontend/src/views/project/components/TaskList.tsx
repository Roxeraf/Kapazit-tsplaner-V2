import { useState } from "react";
import { api } from "../../../api/client";
import AttachmentList from "../../../components/AttachmentList";
import AttachmentPicker from "../../../components/AttachmentPicker";
import ConfirmDialog from "../../../components/ConfirmDialog";
import PersonPicker from "../../../components/PersonPicker";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import usePeopleMap from "../../../hooks/usePeopleMap";
import { TASK_STATUS_LABELS, type Task, type TaskStatus } from "../../../types";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export default function TaskList({
  projectId,
  tasks,
  onChanged,
}: {
  projectId: number;
  tasks: Task[];
  onChanged: () => void;
}) {
  const [titel, setTitel] = useState("");
  const [beschreibung, setBeschreibung] = useState("");
  const [zustaendigPersonId, setZustaendigPersonId] = useState<number | null>(null);
  const [faelligAm, setFaelligAm] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Task | null>(null);
  const people = usePeopleMap();

  const handleAdd = async () => {
    if (!titel.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const task = await api.createTask(projectId, {
        titel: titel.trim(),
        beschreibung: beschreibung.trim() || null,
        zustaendig_person_id: zustaendigPersonId,
        faellig_am: faelligAm || null,
        tags,
      });
      for (const file of files) {
        await api.uploadDocument(projectId, file, { entityType: "task", entityId: task.id });
      }
      setTitel("");
      setBeschreibung("");
      setZustaendigPersonId(null);
      setFaelligAm("");
      setTags([]);
      setFiles([]);
      onChanged();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (task: Task, status: TaskStatus) => {
    await api.updateTask(task.id, { status });
    onChanged();
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deleteTask(toDelete.id);
    setToDelete(null);
    onChanged();
  };

  const sorted = [...tasks].sort((a, b) => {
    const rank: Record<TaskStatus, number> = { offen: 0, in_bearbeitung: 1, erledigt: 2 };
    return rank[a.status] - rank[b.status];
  });

  return (
    <div>
      {sorted.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Aufgaben.</p>
      ) : (
        sorted.map((t) => (
          <div key={t.id} className="card" style={{ marginBottom: "0.6rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}>
            <div className="toolbar">
              <strong>{t.titel}</strong>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <select value={t.status} onChange={(e) => handleStatusChange(t, e.target.value as TaskStatus)}>
                  {Object.entries(TASK_STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setToDelete(t)}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            </div>
            {t.beschreibung && <p style={{ margin: "0.35rem 0" }}>{t.beschreibung}</p>}
            {(t.zustaendig_person_id != null || t.faellig_am) && (
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
                {t.zustaendig_person_id != null && `Zuständig: ${people.get(t.zustaendig_person_id) ?? "…"}`}
                {t.zustaendig_person_id != null && t.faellig_am && " · "}
                {t.faellig_am && `Fällig am ${formatDate(t.faellig_am)}`}
              </p>
            )}
            {t.tags.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.3rem 0" }}>
                {t.tags.map((tag) => (
                  <TagChip key={tag} name={tag} />
                ))}
              </div>
            )}
            <AttachmentList documents={t.documents} />
          </div>
        ))
      )}

      <div className="field-row" style={{ marginTop: "0.75rem", flexDirection: "column", alignItems: "stretch" }}>
        <label>
          Neue Aufgabe
          <input value={titel} onChange={(e) => setTitel(e.target.value)} placeholder="z. B. Kickoff vorbereiten" />
        </label>
        <label>
          Beschreibung
          <input value={beschreibung} onChange={(e) => setBeschreibung(e.target.value)} placeholder="optional" />
        </label>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Zuständig
            <PersonPicker value={zustaendigPersonId} onChange={setZustaendigPersonId} />
          </label>
          <label>
            Fällig am
            <input type="date" value={faelligAm} onChange={(e) => setFaelligAm(e.target.value)} />
          </label>
        </div>
        <TagInput value={tags} onChange={setTags} />
        <AttachmentPicker files={files} onChange={setFiles} />
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-start" }} disabled={saving} onClick={handleAdd}>
          + Aufgabe hinzufügen
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      <ConfirmDialog
        open={toDelete !== null}
        title="Aufgabe löschen"
        message={`Aufgabe "${toDelete?.titel}" wirklich löschen? Angehängte Dateien bleiben im Dokumente-Tab erhalten.`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
