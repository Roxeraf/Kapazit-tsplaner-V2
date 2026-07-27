import { useEffect, useState } from "react";
import { api } from "../api/client";
import { JIRA_PROJECT_STATUS_LABELS, type JiraProject, type JiraProjectStatus, type JiraStatus } from "../types";

export default function JiraProjects() {
  const [jiraStatus, setJiraStatus] = useState<JiraStatus | null>(null);
  const [projects, setProjects] = useState<JiraProject[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api
      .jiraStatus()
      .then((status) => {
        setJiraStatus(status);
        if (!status.configured) return;
        return api.jiraListProjects().then(setProjects);
      })
      .catch((e) => setError(String(e)));
  };

  useEffect(load, []);

  const handleRelevantChange = async (project: JiraProject, relevant: boolean) => {
    await api.jiraSetProject(project.key, { relevant, status: project.status });
    load();
  };

  const handleStatusChange = async (project: JiraProject, status: JiraProjectStatus) => {
    await api.jiraSetProject(project.key, { relevant: project.relevant, status });
    load();
  };

  return (
    <div>
      <h2 className="section-title">Jira-Projekte</h2>
      <p style={{ color: "var(--text-muted)" }}>
        Auswahl, welche Jira-Projekte im Kapazitätsplaner geplant werden. Nur relevant markierte
        Projekte tauchen im Component-Picker im Projekt-Detail auf.
      </p>

      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}
      {jiraStatus && !jiraStatus.configured && <div className="stub-view">{jiraStatus.hinweis}</div>}

      {jiraStatus?.configured && (
        <div className="card">
          <table className="planner">
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Jira-Projekt</th>
                <th>Wird geplant</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.key}>
                  <td className="label">
                    {p.name} <span style={{ color: "var(--text-muted)" }}>({p.key})</span>
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={p.relevant}
                      onChange={(e) => handleRelevantChange(p, e.target.checked)}
                    />
                  </td>
                  <td>
                    <select
                      value={p.status}
                      disabled={!p.relevant}
                      onChange={(e) => handleStatusChange(p, e.target.value as JiraProjectStatus)}
                    >
                      {Object.entries(JIRA_PROJECT_STATUS_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
