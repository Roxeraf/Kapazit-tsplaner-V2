import { useEffect, useState } from "react";
import { api } from "../api/client";
import { JIRA_PROJECT_STATUS_LABELS, type JiraProject, type JiraProjectStatus, type JiraStatus } from "../types";

export default function JiraProjects() {
  const [jiraStatus, setJiraStatus] = useState<JiraStatus | null>(null);
  const [projects, setProjects] = useState<JiraProject[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = (query?: string) => {
    api
      .jiraStatus()
      .then((status) => {
        setJiraStatus(status);
        if (!status.configured) return;
        return api.jiraListProjects(query).then(setProjects);
      })
      .catch((e) => setError(String(e)));
  };

  useEffect(() => load(), []);

  useEffect(() => {
    const timeout = setTimeout(() => load(search || undefined), 300);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const handleRelevantChange = async (project: JiraProject, relevant: boolean) => {
    await api.jiraSetProject(project.key, { relevant, status: project.status });
    load(search || undefined);
  };

  const handleStatusChange = async (project: JiraProject, status: JiraProjectStatus) => {
    await api.jiraSetProject(project.key, { relevant: project.relevant, status });
    load(search || undefined);
  };

  return (
    <div>
      <h2 className="section-title">Jira-Projekte</h2>
      <p style={{ color: "var(--text-muted)" }}>
        Auswahl, welche Jira-Projekte im Kapazitätsplaner geplant werden. Beim Aktivieren wird
        automatisch ein Kapa-Projekt angelegt (taucht dann im Portfolio auf); die Component/Label-
        Zuordnung erfolgt danach im Projekt-Detail.
      </p>

      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}
      {jiraStatus && !jiraStatus.configured && <div className="stub-view">{jiraStatus.hinweis}</div>}

      {jiraStatus?.configured && (
        <div className="card">
          <div className="field-row" style={{ marginTop: 0, marginBottom: "0.75rem" }}>
            <label>
              Suche
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Name oder Key"
              />
            </label>
          </div>
          <table className="planner">
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Jira-Projekt</th>
                <th>Wird geplant</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {projects.length === 0 && (
                <tr>
                  <td colSpan={3} style={{ color: "var(--text-muted)" }}>
                    Keine Jira-Projekte gefunden.
                  </td>
                </tr>
              )}
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
