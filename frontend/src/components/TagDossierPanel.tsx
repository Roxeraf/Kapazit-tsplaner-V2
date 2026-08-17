import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ENTITY_TYPE_META } from "../entityTypeMeta";
import { useTagDossier } from "../tagDossier";
import type { TagDossier } from "../types";

// Phase 26.5: Sidepanel, das sich bei Klick auf einen Tag (TagChip.tsx) öffnet und ein
// dynamisches Dossier zeigt (Counts je Entitätstyp, Entitäten, jüngste Aktivität) statt nur
// lokal zu filtern. Mehrere Tags kombinierbar (AND/OR) über den Toggle + "Tag hinzufügen".
export default function TagDossierPanel({ projectId }: { projectId?: number }) {
  const { openTags, mode, isOpen, addTag, removeTag, setMode, close } = useTagDossier();
  const [dossier, setDossier] = useState<TagDossier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addDraft, setAddDraft] = useState("");

  useEffect(() => {
    if (!isOpen || openTags.length === 0) {
      setDossier(null);
      return;
    }
    api
      .getTagDossier(openTags, mode, projectId)
      .then(setDossier)
      .catch((e) => setError(String(e)));
  }, [isOpen, openTags, mode, projectId]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: "min(26rem, 100vw)",
        background: "#fff",
        borderLeft: "1px solid var(--border)",
        boxShadow: "-4px 0 16px rgba(0,0,0,0.12)",
        zIndex: 900,
        overflowY: "auto",
        padding: "1rem",
      }}
    >
      <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
        <h3 style={{ color: "var(--navy)", margin: 0 }}>
          {openTags.map((t) => `#${t}`).join(mode === "and" ? " + " : " oder ")}
        </h3>
        <button type="button" className="btn secondary" onClick={close}>
          Schließen
        </button>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", alignItems: "center", marginBottom: "0.5rem" }}>
        {openTags.map((t) => (
          <span key={t} className="legend-chip" style={{ background: "#eef3fa", padding: "0.1rem 0.5rem", borderRadius: "999px" }}>
            #{t}
            <button
              type="button"
              onClick={() => removeTag(t)}
              style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer", marginLeft: "0.25rem" }}
            >
              ×
            </button>
          </span>
        ))}
        {openTags.length > 1 && (
          <div style={{ display: "flex", gap: "0.2rem", marginLeft: "0.3rem" }}>
            <button type="button" className={mode === "and" ? "btn" : "btn secondary"} style={{ fontSize: "0.72rem", padding: "0.05rem 0.4rem" }} onClick={() => setMode("and")}>
              UND
            </button>
            <button type="button" className={mode === "or" ? "btn" : "btn secondary"} style={{ fontSize: "0.72rem", padding: "0.05rem 0.4rem" }} onClick={() => setMode("or")}>
              ODER
            </button>
          </div>
        )}
      </div>

      <div className="field-row" style={{ marginTop: 0, marginBottom: "1rem" }}>
        <input
          value={addDraft}
          onChange={(e) => setAddDraft(e.target.value)}
          placeholder="Weiteren Tag kombinieren …"
          style={{ flex: 1 }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && addDraft.trim()) {
              addTag(addDraft.trim());
              setAddDraft("");
            }
          }}
        />
        <button
          type="button"
          className="btn secondary"
          onClick={() => {
            if (addDraft.trim()) {
              addTag(addDraft.trim());
              setAddDraft("");
            }
          }}
        >
          + Kombinieren
        </button>
      </div>

      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {!dossier ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Lade Dossier …</p>
      ) : (
        <>
          <div style={{ marginBottom: "1rem" }}>
            {Object.entries(dossier.counts).length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Keine Treffer.</p>
            ) : (
              Object.entries(dossier.counts).map(([type, count]) => (
                <div key={type} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", padding: "0.15rem 0" }}>
                  <span>
                    {ENTITY_TYPE_META[type as keyof typeof ENTITY_TYPE_META]?.icon ?? "•"} {ENTITY_TYPE_META[type as keyof typeof ENTITY_TYPE_META]?.label ?? type}
                  </span>
                  <strong>{count}</strong>
                </div>
              ))
            )}
          </div>

          {dossier.activity.length > 0 && (
            <div>
              <h4 style={{ color: "var(--navy)", marginBottom: "0.4rem" }}>Aktuelle Lage</h4>
              {dossier.activity.slice(0, 10).map((item) => {
                const meta = ENTITY_TYPE_META[item.entity_type];
                return (
                  <div key={`${item.entity_type}-${item.entity_id}`} style={{ fontSize: "0.85rem", padding: "0.2rem 0" }}>
                    {meta?.icon ?? "•"} {item.label ?? `${meta?.label ?? item.entity_type} #${item.entity_id}`}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
