import { useEffect, useState } from "react";
import ConfirmDialog from "../../../components/ConfirmDialog";
import { PHASE_COLORS, PHASE_LABELS, type Comment, type PhaseCode } from "../../../types";

const PHASE_CODES: PhaseCode[] = ["p", "k", "t", "s", "g", "?"];
const ROW_HEIGHT = 38;
const BAR_HEIGHT = 20;

interface Drag {
  code: PhaseCode;
  makeActive: boolean;
  changes: Record<string, boolean>;
}

export default function PhaseRows({
  phasen,
  monate,
  onCommit,
  readOnly = false,
  comments,
  onAddComment,
  onDeleteComment,
}: {
  phasen: Record<string, PhaseCode[]>;
  monate: string[];
  onCommit: (code: PhaseCode, changes: Record<string, boolean>) => void;
  readOnly?: boolean;
  comments: Comment[];
  onAddComment: (code: PhaseCode, monat: string, text: string) => Promise<void>;
  onDeleteComment: (id: number) => Promise<void>;
}) {
  const [drag, setDrag] = useState<Drag | null>(null);
  const [commentTarget, setCommentTarget] = useState<{ code: PhaseCode; monat: string } | null>(null);
  const [commentDraft, setCommentDraft] = useState("");
  const [commentSaving, setCommentSaving] = useState(false);
  const [commentError, setCommentError] = useState<string | null>(null);
  const [commentToDelete, setCommentToDelete] = useState<Comment | null>(null);

  // Drag endet, sobald die Maustaste irgendwo losgelassen wird (auch außerhalb der Tabelle).
  useEffect(() => {
    if (!drag) return;
    const finish = () => {
      onCommit(drag.code, drag.changes);
      setDrag(null);
    };
    window.addEventListener("mouseup", finish);
    return () => window.removeEventListener("mouseup", finish);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drag]);

  const isActive = (code: PhaseCode, monat: string) => {
    if (drag && drag.code === code && monat in drag.changes) return drag.changes[monat];
    return (phasen[monat] ?? []).includes(code);
  };

  const startDrag = (code: PhaseCode, monat: string) => {
    if (readOnly) return;
    const makeActive = !(phasen[monat] ?? []).includes(code);
    setDrag({ code, makeActive, changes: { [monat]: makeActive } });
  };

  const enterDrag = (code: PhaseCode, monat: string) => {
    if (!drag || drag.code !== code || monat in drag.changes) return;
    setDrag({ ...drag, changes: { ...drag.changes, [monat]: drag.makeActive } });
  };

  const commentsFor = (code: PhaseCode, monat: string) =>
    comments.filter((c) => c.phase_code === code && c.monat === monat);

  const openCommentDialog = (code: PhaseCode, monat: string) => {
    setCommentTarget({ code, monat });
    setCommentDraft("");
    setCommentError(null);
  };

  const handleSaveComment = async () => {
    if (!commentTarget || !commentDraft.trim()) return;
    setCommentSaving(true);
    setCommentError(null);
    try {
      await onAddComment(commentTarget.code, commentTarget.monat, commentDraft.trim());
      setCommentDraft("");
      setCommentTarget(null);
    } catch (e) {
      setCommentError(String(e));
    } finally {
      setCommentSaving(false);
    }
  };

  const handleDeleteComment = async () => {
    if (!commentToDelete) return;
    setCommentError(null);
    try {
      await onDeleteComment(commentToDelete.id);
      setCommentToDelete(null);
    } catch (e) {
      setCommentError(String(e));
      setCommentToDelete(null);
    }
  };

  return (
    <>
      {PHASE_CODES.map((code) => (
        <tr key={code} style={{ height: ROW_HEIGHT }}>
          <td className="label" style={{ height: ROW_HEIGHT, padding: "0 0.4rem" }}>
            <span className="legend-swatch" style={{ background: PHASE_COLORS[code], marginRight: "0.4rem" }} />
            {PHASE_LABELS[code]}
          </td>
          {monate.map((m, i) => {
            const active = isActive(code, m);
            const prevActive = i > 0 && isActive(code, monate[i - 1]);
            const nextActive = i < monate.length - 1 && isActive(code, monate[i + 1]);
            const hasComment = commentsFor(code, m).length > 0;
            return (
              <td
                key={m}
                style={{ height: ROW_HEIGHT, padding: 0, border: "none", borderBottom: "1px solid var(--border)", position: "relative" }}
              >
                <button
                  type="button"
                  onMouseDown={(e) => {
                    if (e.button !== 0) return;
                    e.preventDefault();
                    startDrag(code, m);
                  }}
                  onMouseEnter={() => enterDrag(code, m)}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    openCommentDialog(code, m);
                  }}
                  aria-label={`${PHASE_LABELS[code]} ${m} ${active ? "entfernen" : "setzen"} (Rechtsklick: Kommentar)`}
                  title="Rechtsklick: Kommentar"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "stretch",
                    width: "100%",
                    height: ROW_HEIGHT,
                    border: "none",
                    background: "transparent",
                    padding: 0,
                    cursor: readOnly ? "default" : "pointer",
                    userSelect: "none",
                  }}
                >
                  <span
                    style={{
                      display: "block",
                      width: "100%",
                      height: active ? BAR_HEIGHT : 0,
                      background: active ? PHASE_COLORS[code] : "transparent",
                      borderTopLeftRadius: active && !prevActive ? "5px" : 0,
                      borderBottomLeftRadius: active && !prevActive ? "5px" : 0,
                      borderTopRightRadius: active && !nextActive ? "5px" : 0,
                      borderBottomRightRadius: active && !nextActive ? "5px" : 0,
                      transition: "all 180ms cubic-bezier(0.4, 0, 0.2, 1)",
                    }}
                  />
                </button>
                {hasComment && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      openCommentDialog(code, m);
                    }}
                    title={`Kommentar ansehen: „${commentsFor(code, m)[commentsFor(code, m).length - 1].text}“`}
                    aria-label={`Kommentar zu ${PHASE_LABELS[code]} ${m} ansehen`}
                    style={{
                      position: "absolute",
                      top: 0,
                      right: 0,
                      width: 18,
                      height: 18,
                      padding: 0,
                      border: "none",
                      background: "transparent",
                      cursor: "pointer",
                    }}
                  >
                    <span
                      aria-hidden="true"
                      style={{
                        position: "absolute",
                        top: 0,
                        right: 0,
                        width: 0,
                        height: 0,
                        borderStyle: "solid",
                        borderWidth: "0 9px 9px 0",
                        borderColor: "transparent var(--rot) transparent transparent",
                      }}
                    />
                  </button>
                )}
              </td>
            );
          })}
        </tr>
      ))}

      {commentTarget && (
        <tr>
          <td colSpan={monate.length + 1} style={{ border: "none", padding: 0 }}>
            <div
              onClick={() => setCommentTarget(null)}
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0, 20, 40, 0.45)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 1000,
              }}
            >
              <div onClick={(e) => e.stopPropagation()} className="card" style={{ maxWidth: "26rem", width: "90%" }}>
                <h3 style={{ color: "var(--navy)", marginTop: 0 }}>
                  {PHASE_LABELS[commentTarget.code]} – {commentTarget.monat}
                </h3>
                {commentsFor(commentTarget.code, commentTarget.monat).length === 0 ? (
                  <p style={{ color: "var(--text-muted)" }}>Noch keine Kommentare.</p>
                ) : (
                  <ul style={{ listStyle: "none", padding: 0, margin: "0 0 0.75rem" }}>
                    {commentsFor(commentTarget.code, commentTarget.monat).map((c) => (
                      <li
                        key={c.id}
                        style={{
                          padding: "0.35rem 0",
                          borderBottom: "1px solid var(--border)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                          gap: "0.5rem",
                        }}
                      >
                        <span>{c.text}</span>
                        <button
                          type="button"
                          onClick={() => setCommentToDelete(c)}
                          title="Kommentar löschen"
                          style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer", fontSize: "1rem", lineHeight: 1 }}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <textarea
                  value={commentDraft}
                  onChange={(e) => setCommentDraft(e.target.value)}
                  placeholder="z. B. verzögert wegen fehlender Kundenunterschrift"
                  rows={3}
                  style={{ width: "100%", resize: "vertical" }}
                />
                {commentError && (
                  <p style={{ color: "var(--rot)", fontSize: "0.8rem", margin: "0.35rem 0 0" }}>{commentError}</p>
                )}
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "0.75rem" }}>
                  <button type="button" className="btn secondary" onClick={() => setCommentTarget(null)}>
                    Schließen
                  </button>
                  <button type="button" className="btn" disabled={commentSaving} onClick={handleSaveComment}>
                    {commentSaving ? "Speichert …" : "Kommentar hinzufügen"}
                  </button>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}

      <ConfirmDialog
        open={commentToDelete !== null}
        title="Kommentar löschen"
        message={`Kommentar "${commentToDelete?.text}" wirklich löschen?`}
        onConfirm={handleDeleteComment}
        onCancel={() => setCommentToDelete(null)}
      />
    </>
  );
}
