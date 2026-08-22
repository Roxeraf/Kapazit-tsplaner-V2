import { useEffect, useState } from "react";
import { api } from "../../api/client";
import ConfirmDialog from "../../components/ConfirmDialog";
import type { ProjectDetail as ProjectDetailT } from "../../types";
import BaselineList from "./components/BaselineList";
import MilestoneList from "./components/MilestoneList";
import PlanPhaseList from "./components/PlanPhaseList";
import ResourceDemandGrid from "./components/ResourceDemandGrid";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

// P11 (Planungs-/Kapazitätskonsolidierung): Der Planning-Tab konzentriert sich jetzt
// ausschließlich auf Planung (PlanPhase/Milestone/Kapazität/Planstände/Teilprojekte). Die
// Projektstammdaten (Name/Kunde/Startmonat/Anzahl Monate) inkl. des batch-/grund-basierten
// Speichern-Workflows (PlanHistory) sind in den Einstellungen-Tab umgezogen (siehe
// ProjectSettingsTab) - das waren reine Stammdaten, kein Planungs-Arbeitsschritt, und das
// globale "Speichern"-Paradigma stand im Widerspruch zum Sofort-Speichern der Phasen/
// Milestones/Baselines darunter (zwei konkurrierende Bedienkonzepte auf derselben Seite).
export default function ProjectPlanningTab() {
  const { project, reload: reloadWorkspace } = useProjectWorkspace();
  const projectId = project.id;

  const [draft, setDraft] = useState<ProjectDetailT | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [newSubprojectName, setNewSubprojectName] = useState("");
  const [subprojectToDelete, setSubprojectToDelete] = useState<{ id: number; name: string } | null>(null);

  const load = () => {
    api
      .getProject(projectId)
      .then((p) => setDraft(p))
      .catch((e) => setError(String(e)));
  };

  useEffect(load, [projectId]);

  const handleAddSubproject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft) return;
    await api.createSubproject(draft.id, newSubprojectName, draft.subprojects.length);
    setNewSubprojectName("");
    load();
    reloadWorkspace();
  };

  const handleDeleteSubproject = async () => {
    if (!subprojectToDelete) return;
    await api.deleteSubproject(subprojectToDelete.id);
    setSubprojectToDelete(null);
    load();
    reloadWorkspace();
  };

  if (!draft) return <p>Lade Planung …</p>;

  return (
    <div>
      {error && (
        <div
          className="card"
          style={{
            marginBottom: "1rem",
            borderColor: "var(--rot)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "1rem",
          }}
        >
          <span style={{ color: "var(--rot)" }}>{error}</span>
          <button type="button" className="btn secondary" onClick={() => setError(null)}>
            Schließen
          </button>
        </div>
      )}

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <PlanPhaseList projectId={projectId} />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <MilestoneList projectId={projectId} />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <ResourceDemandGrid projectId={projectId} periods={draft.monate} />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <BaselineList projectId={projectId} />
      </div>

      {draft.subprojects.length > 0 && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Teilprojekte (optionale Gruppierung für Phasen/Milestones oben):
        </p>
      )}

      {draft.subprojects.map((sp) => (
        <div key={sp.id} className="toolbar" style={{ marginBottom: "0.4rem" }}>
          <span>{sp.name}</span>
          <button
            type="button"
            className="btn secondary"
            style={{ color: "var(--rot)", borderColor: "var(--rot)" }}
            onClick={() => setSubprojectToDelete({ id: sp.id, name: sp.name })}
          >
            Teilprojekt löschen
          </button>
        </div>
      ))}

      <form className="card" onSubmit={handleAddSubproject}>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Neues Teilprojekt
            <input
              required
              value={newSubprojectName}
              onChange={(e) => setNewSubprojectName(e.target.value)}
              placeholder="z. B. Rollout Nord"
            />
          </label>
        </div>
        <button className="btn" type="submit" style={{ marginTop: "0.75rem" }}>
          Teilprojekt hinzufügen
        </button>
      </form>

      <ConfirmDialog
        open={subprojectToDelete !== null}
        title="Teilprojekt löschen"
        message={`Teilprojekt "${subprojectToDelete?.name}" wirklich löschen? Alle diesem Teilprojekt zugeordneten Phasen und Milestones werden dabei ebenfalls gelöscht.`}
        onConfirm={handleDeleteSubproject}
        onCancel={() => setSubprojectToDelete(null)}
      />
    </div>
  );
}
