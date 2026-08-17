import { useState } from "react";
import { api } from "../../../api/client";
import AttachmentList from "../../../components/AttachmentList";
import AttachmentPicker from "../../../components/AttachmentPicker";
import ConfirmDialog from "../../../components/ConfirmDialog";
import PersonPicker from "../../../components/PersonPicker";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import usePeopleMap from "../../../hooks/usePeopleMap";
import {
  BLOCKER_PARTY_LABELS,
  BLOCKER_SEVERITY_LABELS,
  BLOCKER_STATUS_LABELS,
  type Blocker,
  type BlockerParty,
  type BlockerSeverity,
  type BlockerStatus,
} from "../../../types";

const SEVERITY_COLOR: Record<BlockerSeverity, string> = {
  niedrig: "var(--gruen)",
  mittel: "var(--gelb)",
  hoch: "var(--rot)",
  kritisch: "var(--rot)",
};

export default function BlockerList({
  projectId,
  blockers,
  onChanged,
}: {
  projectId: number;
  blockers: Blocker[];
  onChanged: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<BlockerSeverity>("mittel");
  const [causedByParty, setCausedByParty] = useState<BlockerParty>("UNKNOWN");
  const [waitingForParty, setWaitingForParty] = useState<BlockerParty>("UNKNOWN");
  const [ownerPersonId, setOwnerPersonId] = useState<number | null>(null);
  const [nextAction, setNextAction] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Blocker | null>(null);
  const people = usePeopleMap();

  const handleAdd = async () => {
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const blocker = await api.createBlocker(projectId, {
        title: title.trim(),
        description: description.trim() || null,
        severity,
        caused_by_party: causedByParty,
        waiting_for_party: waitingForParty,
        owner_person_id: ownerPersonId,
        next_action: nextAction.trim() || null,
        active_since: new Date().toISOString().slice(0, 10),
        tags,
      });
      for (const file of files) {
        await api.uploadDocument(projectId, file, { entityType: "blocker", entityId: blocker.id });
      }
      setTitle("");
      setDescription("");
      setSeverity("mittel");
      setCausedByParty("UNKNOWN");
      setWaitingForParty("UNKNOWN");
      setOwnerPersonId(null);
      setNextAction("");
      setTags([]);
      setFiles([]);
      onChanged();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (blocker: Blocker, status: BlockerStatus) => {
    await api.updateBlocker(blocker.id, { status });
    onChanged();
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deleteBlocker(toDelete.id);
    setToDelete(null);
    onChanged();
  };

  const daysSince = (iso: string | null) => {
    if (!iso) return null;
    const start = new Date(iso).getTime();
    if (Number.isNaN(start)) return null;
    return Math.max(0, Math.floor((Date.now() - start) / (1000 * 60 * 60 * 24)));
  };

  const sorted = [...blockers].sort((a, b) => {
    const rank: Record<BlockerSeverity, number> = { kritisch: 0, hoch: 1, mittel: 2, niedrig: 3 };
    return rank[a.severity] - rank[b.severity];
  });

  return (
    <div>
      {sorted.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Keine Blocker.</p>
      ) : (
        sorted.map((b) => (
          <div key={b.id} className="card" style={{ marginBottom: "0.6rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}>
            <div className="toolbar">
              <strong>
                <span
                  aria-hidden="true"
                  style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: SEVERITY_COLOR[b.severity],
                    marginRight: "0.4rem",
                  }}
                />
                {b.title}
              </strong>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <select value={b.status} onChange={(e) => handleStatusChange(b, e.target.value as BlockerStatus)}>
                  {Object.entries(BLOCKER_STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setToDelete(b)}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            </div>
            {b.description && <p style={{ margin: "0.35rem 0" }}>{b.description}</p>}
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
              Verursacht durch: {BLOCKER_PARTY_LABELS[b.caused_by_party]} · Ball liegt bei:{" "}
              <strong>{BLOCKER_PARTY_LABELS[b.waiting_for_party]}</strong>
              {daysSince(b.active_since) !== null && ` · seit ${daysSince(b.active_since)} Tagen`}
              {b.owner_person_id != null && ` · Owner: ${people.get(b.owner_person_id) ?? "…"}`}
            </p>
            {b.next_action && (
              <p style={{ fontSize: "0.78rem", margin: "0.2rem 0 0" }}>
                <strong>Nächste Aktion:</strong> {b.next_action}
              </p>
            )}
            {b.tags.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.3rem 0" }}>
                {b.tags.map((t) => (
                  <TagChip key={t} name={t} />
                ))}
              </div>
            )}
            <AttachmentList documents={b.documents} />
          </div>
        ))
      )}

      <div className="field-row" style={{ marginTop: "0.75rem", flexDirection: "column", alignItems: "stretch" }}>
        <label>
          Neuer Blocker
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="z. B. Kundenfreigabe Schnittstelle fehlt" />
        </label>
        <label>
          Beschreibung
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="optional" />
        </label>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Schweregrad
            <select value={severity} onChange={(e) => setSeverity(e.target.value as BlockerSeverity)}>
              {Object.entries(BLOCKER_SEVERITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Verursacht durch
            <select value={causedByParty} onChange={(e) => setCausedByParty(e.target.value as BlockerParty)}>
              {Object.entries(BLOCKER_PARTY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ball liegt bei
            <select value={waitingForParty} onChange={(e) => setWaitingForParty(e.target.value as BlockerParty)}>
              {Object.entries(BLOCKER_PARTY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
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
            Nächste Aktion
            <input value={nextAction} onChange={(e) => setNextAction(e.target.value)} placeholder="optional" />
          </label>
        </div>
        <TagInput value={tags} onChange={setTags} />
        <AttachmentPicker files={files} onChange={setFiles} />
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-start" }} disabled={saving} onClick={handleAdd}>
          + Blocker hinzufügen
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      <ConfirmDialog
        open={toDelete !== null}
        title="Blocker löschen"
        message={`Blocker "${toDelete?.title}" wirklich löschen?`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
