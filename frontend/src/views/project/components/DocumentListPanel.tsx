import { useMemo, useState } from "react";
import { api } from "../../../api/client";
import ConfirmDialog from "../../../components/ConfirmDialog";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import { CATEGORY_ICONS, CATEGORY_LABELS, categorize, type DocumentCategory } from "../../../documentIcons";
import type { Document, EntityType } from "../../../types";

// P19.5 (CONCEPT.md Abschnitt 8 / P19_PLANPHASE_WORKSPACE_UX_AUDIT.md Abschnitt 3.10/13):
// gemeinsame Darstellungslogik der zentralen Dokumentenablage (Suche, Typ-/Tag-Filter,
// "Verwendet in"-Backlinks, Löschen mit Impact-Hinweis) - vorher zweimal implementiert
// (ProjectDocumentsTab.tsx vollständig, PlanPhaseWorkspace.tsx-Dateien-Tab als schwächere
// Eigenbau-Liste). Beide Stellen rendern jetzt dieselbe Komponente, parametrisiert über
// `documents` (bereits vom Aufrufer geladen/gescoped - kein neuer Backend-Filter-Endpoint
// nötig, siehe Audit Abschnitt 21) und optional `entityFilter` (verknüpft neue Uploads
// zusätzlich mit dieser Entität, z.B. plan_phase). Die Filterung (Suche/Typ/Tag) läuft hier
// bewusst rein client-seitig - für ProjectDocumentsTab bedeutet das eine reine
// Performance-Verbesserung (ein Fetch statt Server-Roundtrip pro Tastenanschlag), keine
// sichtbare Verhaltensänderung.
export interface DocumentEntityFilter {
  entityType: EntityType;
  entityId: number;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentListPanel({
  projectId,
  documents,
  onRefresh,
  entityFilter,
  emptyText = "Keine Dokumente gefunden.",
}: {
  projectId: number;
  documents: Document[];
  onRefresh: () => void;
  entityFilter?: DocumentEntityFilter;
  emptyText?: string;
}) {
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<DocumentCategory | "alle">("alle");
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [uploadTags, setUploadTags] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [toDelete, setToDelete] = useState<Document | null>(null);

  const allTags = useMemo(() => Array.from(new Set(documents.flatMap((d) => d.tags))).sort(), [documents]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return documents.filter((d) => {
      if (term && !d.dateiname.toLowerCase().includes(term)) return false;
      if (tagFilter && !d.tags.includes(tagFilter)) return false;
      if (typeFilter !== "alle" && categorize(d.mimetype, d.dateiname) !== typeFilter) return false;
      return true;
    });
  }, [documents, search, tagFilter, typeFilter]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        await api.uploadDocument(projectId, file, {
          tags: uploadTags,
          entityType: entityFilter?.entityType,
          entityId: entityFilter?.entityId,
        });
      }
      setUploadTags([]);
      onRefresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    try {
      await api.deleteDocument(toDelete.id);
      setToDelete(null);
      onRefresh();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Hochladen</h3>
        <TagInput value={uploadTags} onChange={setUploadTags} />
        <input
          type="file"
          multiple
          disabled={uploading}
          onChange={(e) => {
            handleUpload(e.target.files);
            e.target.value = "";
          }}
          style={{ marginTop: "0.5rem" }}
        />
      </div>

      <div className="toolbar" style={{ marginBottom: "1rem", flexWrap: "wrap" }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Dateien durchsuchen …"
          style={{ padding: "0.4rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px", minWidth: "14rem" }}
        />
        <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
          <button
            type="button"
            className={typeFilter === "alle" ? "btn" : "btn secondary"}
            onClick={() => setTypeFilter("alle")}
          >
            Alle
          </button>
          {(Object.keys(CATEGORY_LABELS) as DocumentCategory[]).map((cat) => (
            <button
              key={cat}
              type="button"
              className={typeFilter === cat ? "btn" : "btn secondary"}
              onClick={() => setTypeFilter(cat)}
            >
              {CATEGORY_ICONS[cat]} {CATEGORY_LABELS[cat]}
            </button>
          ))}
        </div>
      </div>

      {allTags.length > 0 && (
        <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginBottom: "1rem" }}>
          {tagFilter && (
            <button type="button" className="btn secondary" onClick={() => setTagFilter(null)}>
              Filter zurücksetzen (#{tagFilter})
            </button>
          )}
          {allTags
            .filter((t) => t !== tagFilter)
            .map((t) => (
              <button key={t} type="button" className="btn secondary" onClick={() => setTagFilter(t)}>
                #{t}
              </button>
            ))}
        </div>
      )}

      {filtered.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>{emptyText}</p>
      ) : (
        filtered.map((doc) => {
          const cat = categorize(doc.mimetype, doc.dateiname);
          return (
            <div key={doc.id} className="card" style={{ marginBottom: "0.75rem" }}>
              <div className="toolbar">
                <div>
                  <a href={api.downloadDocumentUrl(doc.id)} target="_blank" rel="noreferrer" style={{ fontWeight: 600 }}>
                    {CATEGORY_ICONS[cat]} {doc.dateiname}
                  </a>
                  {doc.tags.length > 0 && (
                    <div style={{ display: "flex", gap: "0.3rem", flexWrap: "wrap", marginTop: "0.25rem" }}>
                      {doc.tags.map((t) => (
                        <TagChip key={t} name={t} />
                      ))}
                    </div>
                  )}
                  <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.3rem 0 0" }}>
                    {formatSize(doc.groesse_bytes)} · {formatTimestamp(doc.hochgeladen_am)}
                    {doc.hochgeladen_von && ` · ${doc.hochgeladen_von}`}
                  </p>
                  {doc.used_in.length > 0 && (
                    <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.3rem 0 0" }}>
                      Verwendet in:{" "}
                      {doc.used_in.map((u, i) => (
                        <span key={`${u.entity_type}-${u.entity_id}`}>
                          {i > 0 && ", "}
                          {u.label}
                        </span>
                      ))}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  className="btn secondary"
                  style={{ color: "var(--rot)", borderColor: "var(--rot)" }}
                  onClick={() => setToDelete(doc)}
                >
                  Löschen
                </button>
              </div>
            </div>
          );
        })
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title="Dokument löschen"
        message={
          toDelete && toDelete.used_in.length > 0
            ? `"${toDelete.dateiname}" wird verwendet in: ${toDelete.used_in.map((u) => u.label).join(", ")}. Trotzdem endgültig löschen?`
            : `"${toDelete?.dateiname}" wirklich endgültig löschen?`
        }
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
