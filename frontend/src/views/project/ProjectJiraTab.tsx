import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { JiraSyncResult } from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

export default function ProjectJiraTab() {
  const { project, reload } = useProjectWorkspace();
  const [error, setError] = useState<string | null>(null);
  const [jiraConfigured, setJiraConfigured] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState<JiraSyncResult | null>(null);

  useEffect(() => {
    api
      .jiraStatus()
      .then((status) => setJiraConfigured(status.configured))
      .catch(() => setJiraConfigured(false));
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      const result = await api.jiraSync(project.id);
      setLastSyncResult(result);
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setSyncing(false);
    }
  };

  const monateMitIst = Object.keys(project.ist);

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}
      {!jiraConfigured && (
        <div className="stub-view">
          Jira-Integration ist nicht konfiguriert (siehe <code>JIRA_BASE_URL</code>/<code>JIRA_API_TOKEN</code> im Backend).
        </div>
      )}

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Verknüpfung</h3>
        {project.jira_component ? (
          <p style={{ margin: 0 }}>
            Komponente/Label: <strong>{project.jira_component}</strong>
            {project.jira_project_key && <> — Jira-Projekt: {project.jira_project_key}</>}
          </p>
        ) : (
          <p style={{ color: "var(--text-muted)", margin: 0 }}>Noch keine Jira-Komponente/Label verknüpft.</p>
        )}
        <p style={{ fontSize: "0.85rem", margin: "0.5rem 0 0" }}>
          Verknüpfung ändern: <Link to={`/projekte/${project.id}/einstellungen`}>Einstellungen</Link>
        </p>
      </div>

      <div className="card">
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Ist-FTE (aus Jira-Worklogs)</h3>
        {monateMitIst.length === 0 ? (
          <p style={{ color: "var(--text-muted)" }}>Noch keine Ist-Daten synchronisiert.</p>
        ) : (
          <table className="planner" style={{ marginBottom: "0.75rem" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Monat</th>
                {monateMitIst.map((m) => (
                  <th key={m}>{m}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="label">Ist (FTE)</td>
                {monateMitIst.map((m) => (
                  <td key={m}>{project.ist[m].toFixed(2)}</td>
                ))}
              </tr>
            </tbody>
          </table>
        )}
        {jiraConfigured && project.jira_component && (
          <button type="button" className="btn secondary" disabled={syncing} onClick={handleSync}>
            {syncing ? "Synchronisiert …" : "Jetzt synchronisieren"}
          </button>
        )}
        {lastSyncResult && (
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            Letzter Sync: {lastSyncResult.ergebnisse.reduce((sum, r) => sum + r.worklogs_synced, 0)} Worklogs übernommen.
          </p>
        )}
      </div>
    </div>
  );
}
