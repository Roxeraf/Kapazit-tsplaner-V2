import { PROJECT_STATUS_LABELS, type ProjectStatus } from "../../types";
import { api } from "../../api/client";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

export default function ProjectSettingsTab() {
  const { project, reload } = useProjectWorkspace();

  const handleStatusChange = async (status: ProjectStatus) => {
    await api.updateProject(project.id, { status });
    reload();
  };

  return (
    <div className="card">
      <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Status</h3>
      <label className="field-row" style={{ marginTop: 0 }}>
        <select value={project.status} onChange={(e) => handleStatusChange(e.target.value as ProjectStatus)}>
          {Object.entries(PROJECT_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "1rem" }}>
        Weitere Projektparameter (Projektleiter, Jira-Verknüpfung bearbeiten) — in Planung (siehe CONCEPT.md, Phase 2
        Einstellungen-Tab).
      </p>
    </div>
  );
}
