import { useState } from "react";
import { api } from "../../../api/client";
import AttachmentList from "../../../components/AttachmentList";
import AttachmentPicker from "../../../components/AttachmentPicker";
import ConfirmDialog from "../../../components/ConfirmDialog";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import type { MeetingMinutes } from "../../../types";

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function MeetingMinutesList({
  projectId,
  meetings,
  onChanged,
}: {
  projectId: number;
  meetings: MeetingMinutes[];
  onChanged: () => void;
}) {
  const [titel, setTitel] = useState("");
  const [datum, setDatum] = useState(today());
  const [teilnehmer, setTeilnehmer] = useState("");
  const [text, setText] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<MeetingMinutes | null>(null);

  const handleAdd = async () => {
    if (!titel.trim() || !text.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const meeting = await api.createMeetingMinutes(projectId, {
        titel: titel.trim(),
        datum,
        teilnehmer: teilnehmer.trim() || null,
        text: text.trim(),
        tags,
      });
      for (const file of files) {
        await api.uploadDocument(projectId, file, { entityType: "meeting_minutes", entityId: meeting.id });
      }
      setTitel("");
      setDatum(today());
      setTeilnehmer("");
      setText("");
      setTags([]);
      setFiles([]);
      onChanged();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deleteMeetingMinutes(toDelete.id);
    setToDelete(null);
    onChanged();
  };

  return (
    <div>
      {meetings.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Meetingprotokolle.</p>
      ) : (
        meetings.map((m) => (
          <div key={m.id} className="card" style={{ marginBottom: "0.6rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}>
            <div className="toolbar">
              <strong>{m.titel}</strong>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>{formatDate(m.datum)}</span>
                <button
                  type="button"
                  onClick={() => setToDelete(m)}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            </div>
            {m.teilnehmer && <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.2rem 0" }}>Teilnehmer: {m.teilnehmer}</p>}
            <p style={{ margin: "0.35rem 0", whiteSpace: "pre-wrap" }}>{m.text}</p>
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
        <div className="field-row" style={{ marginTop: 0 }}>
          <label style={{ flex: 1 }}>
            Titel
            <input value={titel} onChange={(e) => setTitel(e.target.value)} placeholder="z. B. GoLive-Abnahme" />
          </label>
          <label>
            Datum
            <input type="date" value={datum} onChange={(e) => setDatum(e.target.value)} />
          </label>
        </div>
        <label>
          Teilnehmer
          <input value={teilnehmer} onChange={(e) => setTeilnehmer(e.target.value)} placeholder="optional, kommasepariert" />
        </label>
        <label>
          Protokolltext
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} style={{ width: "100%", resize: "vertical" }} />
        </label>
        <TagInput value={tags} onChange={setTags} />
        <AttachmentPicker files={files} onChange={setFiles} />
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-start" }} disabled={saving} onClick={handleAdd}>
          + Meetingprotokoll hinzufügen
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      <ConfirmDialog
        open={toDelete !== null}
        title="Meetingprotokoll löschen"
        message={`Meetingprotokoll "${toDelete?.titel}" wirklich löschen? Angehängte Dateien bleiben im Dokumente-Tab erhalten.`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
