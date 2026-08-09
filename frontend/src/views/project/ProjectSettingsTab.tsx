import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { PROJECT_STATUS_LABELS, type JiraComponent, type JiraProject, type ProjectStatus } from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

export default function ProjectSettingsTab() {
  const { project, reload } = useProjectWorkspace();
  const [error, setError] = useState<string | null>(null);

  const [jiraConfigured, setJiraConfigured] = useState(false);
  const [relevantJiraProjects, setRelevantJiraProjects] = useState<JiraProject[]>([]);
  const [pickerJiraProjectKey, setPickerJiraProjectKey] = useState("");
  const [pickerComponents, setPickerComponents] = useState<JiraComponent[]>([]);
  const [pickerLabels, setPickerLabels] = useState<string[]>([]);

  useEffect(() => {
    api
      .jiraStatus()
      .then((status) => {
        setJiraConfigured(status.configured);
        if (!status.configured) return;
        return api.jiraListProjects().then((all) => setRelevantJiraProjects(all.filter((p) => p.relevant)));
      })
      .catch(() => setJiraConfigured(false));
  }, []);

  const handlePickerJiraProjectChange = async (key: string) => {
    setPickerJiraProjectKey(key);
    setPickerComponents([]);
    setPickerLabels([]);
    if (!key) return;
    try {
      const [components, labels] = await Promise.all([api.jiraListComponents(key), api.jiraListLabels(key)]);
      setPickerComponents(components);
      setPickerLabels(labels);
    } catch (e) {
      setError(String(e));
    }
  };

  useEffect(() => {
    if (project.jira_project_key && jiraConfigured && pickerJiraProjectKey !== project.jira_project_key) {
      handlePickerJiraProjectChange(project.jira_project_key);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.jira_project_key, jiraConfigured]);

  const handleStatusChange = async (status: ProjectStatus) => {
    await api.updateProject(project.id, { status });
    reload();
  };

  const handleProjektleiterChange = async (raw: string) => {
    await api.updateProject(project.id, { projektleiter: raw.trim() || null });
    reload();
  };

  const handleJiraComponentChange = async (raw: string) => {
    await api.updateProject(project.id, { jira_component: raw.trim() || null });
    reload();
  };

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Projektparameter</h3>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Status
            <select value={project.status} onChange={(e) => handleStatusChange(e.target.value as ProjectStatus)}>
              {Object.entries(PROJECT_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Projektleiter
            <input
              key={project.projektleiter ?? ""}
              defaultValue={project.projektleiter ?? ""}
              placeholder="z. B. Max Mustermann"
              onBlur={(e) => handleProjektleiterChange(e.target.value)}
            />
          </label>
        </div>
      </div>

      <div className="card">
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Jira-Verknüpfung</h3>
        <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", gap: "0.4rem", alignItems: "center" }}>
          Jira-Komponente/Label (für Ist-FTE des gesamten Projekts)
          <input
            key={project.jira_component ?? ""}
            style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px" }}
            defaultValue={project.jira_component ?? ""}
            placeholder="z. B. ETE"
            onBlur={(e) => handleJiraComponentChange(e.target.value)}
          />
        </label>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.35rem 0 0" }}>
          {project.jira_component ? (
            <>
              Aktuell gespeichert: <strong>{project.jira_component}</strong>
            </>
          ) : (
            "Noch nichts gespeichert — ohne Wert bleibt die Ist-FTE-Berechnung für dieses Projekt leer."
          )}
        </p>
        {jiraConfigured && !project.jira_project_key && (
          <div className="field-row" style={{ marginTop: "0.5rem" }}>
            <label>
              Oder aus Jira-Projekt wählen
              <select value={pickerJiraProjectKey} onChange={(e) => handlePickerJiraProjectChange(e.target.value)}>
                <option value="">
                  {relevantJiraProjects.length === 0
                    ? "— keine Jira-Projekte als 'wird geplant' markiert —"
                    : "— Jira-Projekt wählen —"}
                </option>
                {relevantJiraProjects.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.name} ({p.key})
                  </option>
                ))}
              </select>
            </label>
            {pickerJiraProjectKey && (
              <label>
                Komponente/Label
                <select
                  value={project.jira_component ?? ""}
                  onChange={(e) => {
                    if (e.target.value) handleJiraComponentChange(e.target.value);
                  }}
                >
                  <option value="">— wählen —</option>
                  {pickerComponents.length > 0 && (
                    <optgroup label="Components">
                      {pickerComponents.map((c) => (
                        <option key={`c-${c.id}`} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                    </optgroup>
                  )}
                  {pickerLabels.length > 0 && (
                    <optgroup label="Labels">
                      {pickerLabels.map((l) => (
                        <option key={`l-${l}`} value={l}>
                          {l}
                        </option>
                      ))}
                    </optgroup>
                  )}
                  {pickerComponents.length === 0 && pickerLabels.length === 0 && (
                    <option value="" disabled>
                      Keine Components oder Labels in diesem Jira-Projekt gefunden
                    </option>
                  )}
                </select>
              </label>
            )}
          </div>
        )}
        {project.jira_project_key && (
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.5rem 0 0" }}>
            Verknüpft mit Jira-Projekt: {project.jira_project_key}
          </p>
        )}
        <p style={{ fontSize: "0.8rem", margin: "0.75rem 0 0" }}>
          Sync-Status und offene Issues siehe <Link to={`/projekte/${project.id}/jira`}>Jira-Tab</Link>.
        </p>
      </div>
    </div>
  );
}
