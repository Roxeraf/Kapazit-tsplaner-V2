import { useEffect, useState } from "react";
import { api } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import ResourceDemandGrid from "./project/components/ResourceDemandGrid";
import type { ProjectDetail, ProjectSummary } from "../types";

// P20.1 (Auftrag Abschnitt 15): der alte Bedienweg (Teilprojekte, projektweites
// Ressourcenbedarf-Raster über ResourceDemand ohne plan_phase_id, "Grobplanung") ist aus dem
// normalen Projekt-Planning-Tab entfernt - ein Projektleiter soll diese Legacy-Planung nicht
// mehr sehen müssen. Bleibt bis zum abgeschlossenen B-8-Cutover ausschließlich über diesen
// expliziten Admin/Diagnose-Pfad erreichbar (Auftrag: "nur über expliziten Admin/Migration/
// Legacy Diagnostics Pfad erreichbar machen"). Keine Funktionsänderung gegenüber der
// vorherigen Einbindung in ProjectPlanningTab.tsx - reiner Ortswechsel.
export default function LegacyCapacityDiagnostics() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState<number | "">("");
  const [draft, setDraft] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newSubprojectName, setNewSubprojectName] = useState("");
  const [subprojectToDelete, setSubprojectToDelete] = useState<{ id: number; name: string } | null>(null);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => setProjects([]));
  }, []);

  const load = (id: number) => {
    api
      .getProject(id)
      .then(setDraft)
      .catch((e) => setError(String(e)));
  };

  useEffect(() => {
    if (projectId === "") {
      setDraft(null);
      return;
    }
    load(projectId);
  }, [projectId]);

  const handleAddSubproject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft) return;
    await api.createSubproject(draft.id, newSubprojectName, draft.subprojects.length);
    setNewSubprojectName("");
    load(draft.id);
  };

  const handleDeleteSubproject = async () => {
    if (!subprojectToDelete || !draft) return;
    await api.deleteSubproject(subprojectToDelete.id);
    setSubprojectToDelete(null);
    load(draft.id);
  };

  return (
    <div>
      <p className="admin-help">
        Alter Bedienweg (Teilprojekte, projektweites Ressourcenbedarf-Raster) für noch nicht auf die
        PlanPhase-Struktur migrierte Projekte. Nur für Administration/Migration - der normale
        Projekt-Planning-Tab zeigt diesen Bereich nicht mehr.
      </p>

      {error && <div className="admin-alert" role="alert">{error}</div>}

      <section className="card admin-card admin-card--wide">
        <label>
          Projekt
          <select value={projectId} onChange={(e) => setProjectId(e.target.value === "" ? "" : Number(e.target.value))}>
            <option value="">— Projekt wählen —</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
      </section>

      {draft && (
        <>
          <div className="card admin-card admin-card--wide" style={{ marginTop: "1rem" }}>
            <ResourceDemandGrid projectId={draft.id} periods={draft.monate} />
          </div>

          <div className="card admin-card admin-card--wide" style={{ marginTop: "1rem" }}>
            <h3>Teilprojekte</h3>
            {draft.subprojects.length > 0 && (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                Optionale Gruppierung für Phasen/Milestones der PlanPhase-Struktur:
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

            <form className="admin-inline-form" onSubmit={handleAddSubproject}>
              <label>
                Neues Teilprojekt
                <input
                  required
                  value={newSubprojectName}
                  onChange={(e) => setNewSubprojectName(e.target.value)}
                  placeholder="z. B. Rollout Nord"
                />
              </label>
              <button className="btn" type="submit">
                Teilprojekt hinzufügen
              </button>
            </form>
          </div>
        </>
      )}

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
