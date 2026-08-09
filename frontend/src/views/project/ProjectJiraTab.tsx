import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { JiraComponent, JiraProject } from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

export default function ProjectJiraTab() {
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

  // Wenn das Projekt schon aus einem aktivierten Jira-Projekt entstanden ist (siehe
  // "Jira-Projekte"-Seite), ist die Zuordnung bereits klar — nicht nochmal danach fragen,
  // direkt die Components davon laden.
  useEffect(() => {
    if (project.jira_project_key && jiraConfigured && pickerJiraProjectKey !== project.jira_project_key) {
      handlePickerJiraProjectChange(project.jira_project_key);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.jira_project_key, jiraConfigured]);

  const linkedJiraProjectName =
    relevantJiraProjects.find((p) => p.key === project.jira_project_key)?.name ?? project.jira_project_key;

  const handleJiraComponentChange = async (raw: string) => {
    await api.updateProject(project.id, { jira_component: raw.trim() || null });
    reload();
  };

  const handleSync = async () => {
    setError(null);
    try {
      await api.jiraSync(project.id);
      reload();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}
      {!jiraConfigured && (
        <div className="stub-view">
          Jira-Integration ist nicht konfiguriert (siehe <code>JIRA_BASE_URL</code>/<code>JIRA_API_TOKEN</code> im Backend).
        </div>
      )}
      <div className="card">
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
        {jiraConfigured && (
          <div className="field-row" style={{ marginTop: "0.5rem" }}>
            {project.jira_project_key ? (
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", alignSelf: "flex-end" }}>
                Verknüpft mit Jira-Projekt: {linkedJiraProjectName} ({project.jira_project_key})
              </span>
            ) : (
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
            )}
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
        {jiraConfigured && project.jira_component && (
          <button type="button" className="btn secondary" style={{ marginTop: "0.75rem" }} onClick={handleSync}>
            Jetzt synchronisieren
          </button>
        )}
      </div>
    </div>
  );
}
