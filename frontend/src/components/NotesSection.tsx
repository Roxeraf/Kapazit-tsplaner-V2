import { useState } from "react";
import type { Comment } from "../types";

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function NotesSection({ notes, onAdd }: { notes: Comment[]; onAdd: (text: string) => Promise<void> }) {
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async () => {
    if (!text.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onAdd(text.trim());
      setText("");
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      {notes.length === 0 ? (
        <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.85rem" }}>Noch keine Notizen.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: "0 0 0.5rem", fontSize: "0.85rem" }}>
          {notes.map((n) => (
            <li key={n.id} style={{ padding: "0.35rem 0", borderBottom: "1px solid var(--border)" }}>
              <div>{n.text}</div>
              <div style={{ color: "var(--text-muted)" }}>{formatTimestamp(n.erstellt_am)}</div>
            </li>
          ))}
        </ul>
      )}
      <div className="field-row" style={{ marginTop: 0 }}>
        <label style={{ flex: 1 }}>
          Neue Notiz
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="z. B. Verzögerung wegen fehlender Kundenunterschrift"
          />
        </label>
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-end" }} disabled={saving} onClick={handleAdd}>
          + Notiz hinzufügen
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem", margin: "0.35rem 0 0" }}>{error}</p>}
    </div>
  );
}
