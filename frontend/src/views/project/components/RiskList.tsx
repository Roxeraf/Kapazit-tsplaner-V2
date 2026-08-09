import { useState } from "react";
import { api } from "../../../api/client";
import AttachmentList from "../../../components/AttachmentList";
import AttachmentPicker from "../../../components/AttachmentPicker";
import ConfirmDialog from "../../../components/ConfirmDialog";
import TagInput from "../../../components/TagInput";
import { RISK_LEVEL_LABELS, RISK_STATUS_LABELS, type Risk, type RiskLevel, type RiskStatus } from "../../../types";

const LEVEL_COLOR: Record<RiskLevel, string> = { niedrig: "var(--gruen)", mittel: "var(--gelb)", hoch: "var(--rot)" };

export default function RiskList({
  projectId,
  risks,
  onChanged,
}: {
  projectId: number;
  risks: Risk[];
  onChanged: () => void;
}) {
  const [titel, setTitel] = useState("");
  const [beschreibung, setBeschreibung] = useState("");
  const [wahrscheinlichkeit, setWahrscheinlichkeit] = useState<RiskLevel>("mittel");
  const [auswirkung, setAuswirkung] = useState<RiskLevel>("mittel");
  const [owner, setOwner] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<Risk | null>(null);

  const handleAdd = async () => {
    if (!titel.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const risk = await api.createRisk(projectId, {
        titel: titel.trim(),
        beschreibung: beschreibung.trim() || null,
        wahrscheinlichkeit,
        auswirkung,
        owner: owner.trim() || null,
        tags,
      });
      for (const file of files) {
        await api.uploadDocument(projectId, file, { entityType: "risk", entityId: risk.id });
      }
      setTitel("");
      setBeschreibung("");
      setOwner("");
      setTags([]);
      setFiles([]);
      onChanged();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (risk: Risk, status: RiskStatus) => {
    await api.updateRisk(risk.id, { status });
    onChanged();
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deleteRisk(toDelete.id);
    setToDelete(null);
    onChanged();
  };

  const sorted = [...risks].sort((a, b) => {
    const rank: Record<RiskLevel, number> = { hoch: 0, mittel: 1, niedrig: 2 };
    return rank[a.auswirkung] - rank[b.auswirkung];
  });

  return (
    <div>
      {sorted.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Risiken.</p>
      ) : (
        sorted.map((r) => (
          <div key={r.id} className="card" style={{ marginBottom: "0.6rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}>
            <div className="toolbar">
              <strong>
                <span
                  aria-hidden="true"
                  style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: LEVEL_COLOR[r.auswirkung],
                    marginRight: "0.4rem",
                  }}
                />
                {r.titel}
              </strong>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <select value={r.status} onChange={(e) => handleStatusChange(r, e.target.value as RiskStatus)}>
                  {Object.entries(RISK_STATUS_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => setToDelete(r)}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            </div>
            {r.beschreibung && <p style={{ margin: "0.35rem 0" }}>{r.beschreibung}</p>}
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: 0 }}>
              Wahrscheinlichkeit: {RISK_LEVEL_LABELS[r.wahrscheinlichkeit]} · Auswirkung: {RISK_LEVEL_LABELS[r.auswirkung]}
              {r.owner && ` · Owner: ${r.owner}`}
            </p>
            {r.tags.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.3rem 0" }}>
                {r.tags.map((t) => (
                  <span key={t} style={{ fontSize: "0.75rem", color: "var(--blau)" }}>
                    #{t}
                  </span>
                ))}
              </div>
            )}
            <AttachmentList documents={r.documents} />
          </div>
        ))
      )}

      <div className="field-row" style={{ marginTop: "0.75rem", flexDirection: "column", alignItems: "stretch" }}>
        <label>
          Neues Risiko
          <input value={titel} onChange={(e) => setTitel(e.target.value)} placeholder="z. B. Ressourcenengpass Testphase" />
        </label>
        <label>
          Beschreibung
          <input value={beschreibung} onChange={(e) => setBeschreibung(e.target.value)} placeholder="optional" />
        </label>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Wahrscheinlichkeit
            <select value={wahrscheinlichkeit} onChange={(e) => setWahrscheinlichkeit(e.target.value as RiskLevel)}>
              {Object.entries(RISK_LEVEL_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Auswirkung
            <select value={auswirkung} onChange={(e) => setAuswirkung(e.target.value as RiskLevel)}>
              {Object.entries(RISK_LEVEL_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Owner
            <input value={owner} onChange={(e) => setOwner(e.target.value)} placeholder="optional" />
          </label>
        </div>
        <TagInput value={tags} onChange={setTags} />
        <AttachmentPicker files={files} onChange={setFiles} />
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-start" }} disabled={saving} onClick={handleAdd}>
          + Risiko hinzufügen
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      <ConfirmDialog
        open={toDelete !== null}
        title="Risiko löschen"
        message={`Risiko "${toDelete?.titel}" wirklich löschen? Angehängte Dateien bleiben im Dokumente-Tab erhalten.`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
