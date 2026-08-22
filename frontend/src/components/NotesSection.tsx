import { useState } from "react";
import { ENTITY_TYPE_META } from "../entityTypeMeta";
import { FOLLOW_UP_ACTIONS, useFollowUpAction } from "../hooks/useFollowUpAction";
import type { Comment, EntityType } from "../types";
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

// P19.3 (Kommentar-Threading): Backend erlaubt beliebige parent_id-Verschachtelungstiefe -
// die Darstellung begrenzt sich bewusst auf eine Ebene (wie die meisten Kommentarsysteme,
// siehe P19_PLANPHASE_WORKSPACE_UX_AUDIT.md Abschnitt 24 P19.3 "Risks"): jede Antwort wird dem
// obersten Vorfahren zugeordnet, auch eine "Antwort auf eine Antwort" erscheint also auf
// derselben eingerückten Ebene unter der Wurzel, nicht weiter verschachtelt.
function groupByRoot(notes: Comment[]): { roots: Comment[]; repliesByRoot: Map<number, Comment[]> } {
  const byId = new Map(notes.map((n) => [n.id, n]));
  const topAncestorId = (note: Comment): number => {
    let current = note;
    const seen = new Set<number>();
    while (current.parent_id != null && !seen.has(current.id)) {
      seen.add(current.id);
      const parent = byId.get(current.parent_id);
      if (!parent) break;
      current = parent;
    }
    return current.id;
  };

  const roots = notes.filter((n) => n.parent_id == null);
  const repliesByRoot = new Map<number, Comment[]>();
  for (const note of notes) {
    if (note.parent_id == null) continue;
    const rootId = topAncestorId(note);
    if (rootId === note.id) continue;
    const list = repliesByRoot.get(rootId) ?? [];
    list.push(note);
    repliesByRoot.set(rootId, list);
  }
  for (const list of repliesByRoot.values()) {
    list.sort((a, b) => a.erstellt_am.localeCompare(b.erstellt_am));
  }
  return { roots, repliesByRoot };
}

export default function NotesSection({
  notes,
  onAdd,
  onDelete,
  projectId,
  planPhaseId,
  // P19.3/P19.4: Tag-Vorschlag bei "Aus Kommentar erstellen" ist die Union aus Kommentar- UND
  // Phasen-Tags (siehe CONCEPT.md Abschnitt 8, Auftragsbeispiel "#Schnittstelle #Kunde von der
  // Phase + #API vom Kommentar") - nur relevant, wenn NotesSection im Phasenkontext läuft.
  phaseTags = [],
  onChanged,
}: {
  notes: Comment[];
  onAdd: (input: { text: string; tags: string[]; files: File[]; parentId?: number | null }) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  // Nur gesetzt, wenn "Aus Kommentar erstellen" hier angeboten werden soll (braucht ein
  // Zielprojekt für den Create-Endpoint) - ohne projectId bleibt NotesSection eine reine
  // Notizliste wie bisher (z. B. falls künftig irgendwo ohne Projektkontext genutzt).
  projectId?: number;
  planPhaseId?: number;
  phaseTags?: string[];
  // Aufruf nach "Aus Kommentar erstellen" - die neu erzeugte Aufgabe/der Blocker/die
  // Entscheidung lebt außerhalb von NotesSection (eigene Liste im selben Tab), daher muss der
  // Elternteil selbst neu laden (analog ActivityFeed.onChanged, P16.1).
  onChanged?: () => void;
}) {
  const [text, setText] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noteToDelete, setNoteToDelete] = useState<Comment | null>(null);

  const [replyingToId, setReplyingToId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState("");
  const [replyTags, setReplyTags] = useState<string[]>([]);
  const [replySaving, setReplySaving] = useState(false);

  const followUp = useFollowUpAction(projectId ?? 0, planPhaseId, () => onChanged?.());

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

  const startReply = (parentId: number) => {
    setReplyingToId(parentId);
    setReplyText("");
    setReplyTags([]);
  };

  const submitReply = async () => {
    if (replyingToId == null || !replyText.trim()) return;
    setReplySaving(true);
    setError(null);
    try {
      await onAdd({ text: replyText.trim(), tags: replyTags, files: [], parentId: replyingToId });
      setReplyingToId(null);
      setReplyText("");
      setReplyTags([]);
    } catch (e) {
      setError(String(e));
    } finally {
      setReplySaving(false);
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

  const startFollowUpFromComment = (comment: Comment, target: EntityType) => {
    const suggested = Array.from(new Set([...comment.tags, ...phaseTags]));
    followUp.start({ entity_type: "comment", entity_id: comment.id }, target, suggested);
  };

  const { roots, repliesByRoot } = groupByRoot(notes);
  const commentActions = FOLLOW_UP_ACTIONS.comment ?? [];

  const renderNote = (note: Comment, isReply: boolean) => (
    <div
      key={note.id}
      className="card"
      style={{
        marginBottom: isReply ? "0.4rem" : "0.6rem",
        marginLeft: isReply ? "1.5rem" : 0,
        padding: "0.6rem 0.85rem",
        fontSize: "0.88rem",
        background: isReply ? "#fafbfc" : undefined,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
        <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
          {isReply && "↳ "}
          {formatTimestamp(note.erstellt_am)}
        </span>
        <button
          type="button"
          onClick={() => setNoteToDelete(note)}
          title="Notiz löschen"
          style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer", fontSize: "1rem", lineHeight: 1 }}
        >
          ×
        </button>
      </div>
      <div style={{ margin: "0.3rem 0" }}>{note.text}</div>
      {note.tags.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", marginBottom: "0.2rem" }}>
          {note.tags.map((t) => (
            <TagChip key={t} name={t} />
          ))}
        </div>
      )}
      <AttachmentList documents={note.documents} />

      <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginTop: "0.35rem" }}>
        <button
          type="button"
          className="btn secondary"
          style={{ fontSize: "0.72rem", padding: "0.05rem 0.4rem" }}
          onClick={() => startReply(note.id)}
        >
          ↩ Antworten
        </button>
        {projectId != null &&
          commentActions.map((a) => (
            <button
              key={a.target}
              type="button"
              className="btn secondary"
              style={{ fontSize: "0.72rem", padding: "0.05rem 0.4rem" }}
              onClick={() => startFollowUpFromComment(note, a.target)}
            >
              {a.label}
            </button>
          ))}
      </div>

      {replyingToId === note.id && (
        <div style={{ marginTop: "0.5rem", padding: "0.5rem", background: "#f8fafc", borderRadius: "4px" }}>
          <input
            autoFocus
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Antwort schreiben …"
            style={{ width: "100%" }}
          />
          <TagInput value={replyTags} onChange={setReplyTags} />
          <div className="field-row" style={{ marginTop: "0.4rem" }}>
            <button type="button" className="btn secondary" disabled={replySaving || !replyText.trim()} onClick={submitReply}>
              Antwort senden
            </button>
            <button type="button" className="btn secondary" onClick={() => setReplyingToId(null)}>
              Abbrechen
            </button>
          </div>
        </div>
      )}

      {followUp.pending && followUp.pending.source.entity_type === "comment" && followUp.pending.source.entity_id === note.id && (
        <div style={{ marginTop: "0.5rem", padding: "0.5rem", background: "#f8fafc", borderRadius: "4px" }}>
          <input
            autoFocus
            value={followUp.draftTitle}
            onChange={(e) => followUp.setDraftTitle(e.target.value)}
            placeholder={`Titel für ${ENTITY_TYPE_META[followUp.pending.target].label}`}
            style={{ width: "100%" }}
          />
          <div style={{ marginTop: "0.4rem" }}>
            {followUp.draftTags.length > 0 && (
              <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                Tags aus Kommentar{phaseTags.length > 0 ? " + Phase" : ""} vorgeschlagen — abwählbar, weitere ergänzbar:
              </span>
            )}
            <TagInput value={followUp.draftTags} onChange={followUp.setDraftTags} />
          </div>
          <div className="field-row" style={{ marginTop: "0.5rem" }}>
            <button type="button" className="btn secondary" disabled={followUp.saving || !followUp.draftTitle.trim()} onClick={followUp.submit}>
              Erstellen
            </button>
            <button type="button" className="btn secondary" onClick={followUp.cancel}>
              Abbrechen
            </button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div>
      {notes.length === 0 ? (
        <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.85rem" }}>Noch keine Notizen.</p>
      ) : (
        <div style={{ marginBottom: "0.75rem" }}>
          {roots.map((root) => (
            <div key={root.id}>
              {renderNote(root, false)}
              {(repliesByRoot.get(root.id) ?? []).map((reply) => renderNote(reply, true))}
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
      {(error || followUp.error) && <p style={{ color: "var(--rot)", fontSize: "0.8rem", margin: "0.35rem 0 0" }}>{error ?? followUp.error}</p>}
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
