import { useState } from "react";
import type { Comment } from "../types";
import AttachmentList from "./AttachmentList";
import AttachmentPicker from "./AttachmentPicker";
import ConfirmDialog from "./ConfirmDialog";
import TagChip from "./TagChip";
import TagInput from "./TagInput";

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function NotesSection({
  notes,
  onAdd,
  onDelete,
}: {
  notes: Comment[];
  onAdd: (input: { text: string; tags: string[]; files: File[] }) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  const [text, setText] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noteToDelete, setNoteToDelete] = useState<Comment | null>(null);

  const handleAdd = async () => {
    if (!text.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onAdd({ text: text.trim(), tags, files });
      setText("");
      setTags([]);
      setFiles([]);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!noteToDelete) return;
    setError(null);
    try {
      await onDelete(noteToDelete.id);
      setNoteToDelete(null);
    } catch (e) {
      setError(String(e));
      setNoteToDelete(null);
    }
  };

  return (
    <div>
      {notes.length === 0 ? (
        <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.85rem" }}>Noch keine Notizen.</p>
      ) : (
        <div style={{ marginBottom: "0.75rem" }}>
          {notes.map((n) => (
            <div
              key={n.id}
              className="card"
              style={{ marginBottom: "0.6rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>{formatTimestamp(n.erstellt_am)}</span>
                <button
                  type="button"
                  onClick={() => setNoteToDelete(n)}
                  title="Notiz löschen"
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer", fontSize: "1rem", lineHeight: 1 }}
                >
                  ×
                </button>
              </div>
              <div style={{ margin: "0.3rem 0" }}>{n.text}</div>
              {n.tags.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginBottom: "0.2rem" }}>
                  {n.tags.map((t) => (
                    <TagChip key={t} name={t} />
                  ))}
                </div>
              )}
              <AttachmentList documents={n.documents} />
            </div>
          ))}
        </div>
      )}
      <div className="field-row" style={{ marginTop: 0, flexDirection: "column", alignItems: "stretch" }}>
        <label style={{ flex: 1 }}>
          Neue Notiz
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="z. B. Kunde hat die finale Freigabe für den GoLive erteilt"
          />
        </label>
        <TagInput value={tags} onChange={setTags} />
        <AttachmentPicker files={files} onChange={setFiles} />
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-start" }} disabled={saving} onClick={handleAdd}>
          + Notiz hinzufügen
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem", margin: "0.35rem 0 0" }}>{error}</p>}
      <ConfirmDialog
        open={noteToDelete !== null}
        title="Notiz löschen"
        message={`Notiz "${noteToDelete?.text}" wirklich löschen? Angehängte Dateien bleiben im Dokumente-Tab erhalten.`}
        onConfirm={handleDelete}
        onCancel={() => setNoteToDelete(null)}
      />
    </div>
  );
}
