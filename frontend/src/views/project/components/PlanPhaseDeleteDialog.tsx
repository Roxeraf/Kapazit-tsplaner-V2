import { useState } from "react";
import { api } from "../../../api/client";
import type { PlanPhase, PlanPhaseSubtreeImpact } from "../../../types";

type Step = "confirm" | "blocked" | "subtree";

// P18/B-6 (CONCEPT.md Abschnitt 6b.9, BD-11 CLOSED): Standard-Löschen einer Phase mit
// Unterphasen ist blockiert, NICHT kaskadierend. Bietet die zwei vorgesehenen Wege an:
// "Unterphasen verschieben" (Phase wird danach wieder leaf und normal löschbar) oder die
// separate, stark bestätigte "Gesamten Zweig löschen"-Aktion (Bestätigung per exaktem
// Phasennamen + Nachfahrenzahl, Auswirkungsanzeige vorher).
export default function PlanPhaseDeleteDialog({
  phase,
  onClose,
  onDeleted,
}: {
  phase: PlanPhase | null;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [step, setStep] = useState<Step>("confirm");
  const [blockedInfo, setBlockedInfo] = useState<{ childCount: number; message: string } | null>(null);
  const [impact, setImpact] = useState<PlanPhaseSubtreeImpact | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (phase == null) return null;

  const reset = () => {
    setStep("confirm");
    setBlockedInfo(null);
    setImpact(null);
    setConfirmText("");
    setError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleConfirmDelete = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.tryDeletePlanPhase(phase.id);
      if (!result.blocked) {
        onDeleted();
        handleClose();
        return;
      }
      setBlockedInfo({ childCount: result.childCount, message: result.message });
      setStep("blocked");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleMoveChildrenToTopLevel = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.reparentPlanPhaseChildren(phase.id, null);
      const result = await api.tryDeletePlanPhase(phase.id);
      if (!result.blocked) {
        onDeleted();
        handleClose();
      } else {
        setError("Phase hat weiterhin Unterphasen und konnte nicht gelöscht werden.");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleShowSubtreeImpact = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await api.getPlanPhaseSubtreeImpact(phase.id);
      setImpact(data);
      setStep("subtree");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteSubtree = async () => {
    if (impact == null) return;
    setBusy(true);
    setError(null);
    try {
      await api.deletePlanPhaseSubtree(phase.id, {
        confirm_phase_type: confirmText,
        confirm_descendant_count: impact.descendant_phase_count,
      });
      onDeleted();
      handleClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      onClick={handleClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0, 20, 40, 0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1100 }}
    >
      <div role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()} className="card" style={{ maxWidth: "30rem", width: "90%" }}>
        {error && <p style={{ color: "var(--rot)", fontSize: "0.85rem" }}>{error}</p>}

        {step === "confirm" && (
          <>
            <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Phase löschen</h3>
            <p style={{ fontSize: "0.9rem" }}>Phase "{phase.phase_type}" wirklich löschen?</p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1rem" }}>
              <button type="button" className="btn secondary" onClick={handleClose}>
                Abbrechen
              </button>
              <button type="button" className="btn" style={{ background: "var(--rot)", borderColor: "var(--rot)" }} disabled={busy} onClick={handleConfirmDelete}>
                {busy ? "…" : "Löschen"}
              </button>
            </div>
          </>
        )}

        {step === "blocked" && blockedInfo && (
          <>
            <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Phase enthält Unterphasen</h3>
            <p style={{ fontSize: "0.9rem" }}>{blockedInfo.message}</p>
            <p style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
              Diese Phase kann nicht direkt gelöscht werden, solange sie Unterphasen enthält. Verschiebe die
              Unterphasen (z. B. auf Top-Level) oder lösche den gesamten Zweig bewusst.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "1rem" }}>
              <button type="button" className="btn secondary" disabled={busy} onClick={handleMoveChildrenToTopLevel}>
                Unterphasen auf Top-Level verschieben, dann löschen
              </button>
              <button type="button" className="btn secondary" style={{ color: "var(--rot)", borderColor: "var(--rot)" }} disabled={busy} onClick={handleShowSubtreeImpact}>
                Gesamten Zweig löschen …
              </button>
              <button type="button" className="btn secondary" onClick={handleClose}>
                Abbrechen
              </button>
            </div>
          </>
        )}

        {step === "subtree" && impact && (
          <>
            <h3 style={{ color: "var(--rot)", marginTop: 0 }}>Gesamten Zweig löschen</h3>
            <p style={{ fontSize: "0.85rem" }}>Diese Aktion löscht "{impact.phase_type}" und alle Unterphasen unwiderruflich:</p>
            <ul style={{ fontSize: "0.85rem", margin: "0.4rem 0" }}>
              <li>{impact.descendant_phase_count} Unterphase(n)</li>
              <li>{impact.resource_demands_affected} Ressourcenbedarfe, {impact.resource_assignments_affected} Personenzuordnungen</li>
              <li>
                {impact.comments_affected} Kommentare, {impact.tasks_affected} Aufgaben, {impact.blockers_affected} Blocker,{" "}
                {impact.decisions_affected} Entscheidungen (bleiben erhalten, werden nur entkoppelt)
              </li>
              <li>{impact.milestones_affected} Meilensteine (bleiben erhalten, werden nur entkoppelt)</li>
              <li>{impact.documents_affected} Dokumentverknüpfungen</li>
            </ul>
            <label style={{ fontSize: "0.85rem" }}>
              Zur Bestätigung Phasenname exakt eingeben: <strong>{impact.phase_type}</strong>
              <input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} style={{ marginTop: "0.3rem" }} />
            </label>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "1rem" }}>
              <button type="button" className="btn secondary" onClick={handleClose}>
                Abbrechen
              </button>
              <button
                type="button"
                className="btn"
                style={{ background: "var(--rot)", borderColor: "var(--rot)" }}
                disabled={busy || confirmText !== impact.phase_type}
                onClick={handleDeleteSubtree}
              >
                {busy ? "…" : "Endgültig löschen"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
