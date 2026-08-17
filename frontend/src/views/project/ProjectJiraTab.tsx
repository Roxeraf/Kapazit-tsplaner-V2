import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { JiraStatus, JiraSyncResult } from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

export default function ProjectJiraTab() {
  const { project, reload } = useProjectWorkspace();
  const [error, setError] = useState<string | null>(null);
  const [jiraStatus, setJiraStatus] = useState<JiraStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState<JiraSyncResult | null>(null);

  useEffect(() => {
    api
      .jiraStatus()
      .then(setJiraStatus)
      .catch((e) => setError(`Integrationsstatus konnte nicht geladen werden: ${String(e)}`));
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
  const jiraConfigured = jiraStatus?.configured === true;
  const syncErrors = lastSyncResult?.ergebnisse.filter((result) => result.error) ?? [];

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}
      {!jiraConfigured && (
        <div className="stub-view">
          {jiraStatus?.hinweis ?? "Jira-/Tempo-Integrationsstatus wird geladen …"}
        </div>
      )}

      {jiraStatus && jiraConfigured && (
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <strong>Integration:</strong> Jira verbunden
          {jiraStatus.tempo_configured ? " · Tempo verbunden" : " · native Jira-Worklogs"}
          <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "0.25rem" }}>
            {jiraStatus.hinweis}
          </div>
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
          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            <p>Letzter Sync: {lastSyncResult.ergebnisse.reduce((sum, r) => sum + r.worklogs_synced, 0)} Worklogs übernommen.</p>
            {syncErrors.map((result) => (
              <p key={result.project_id} style={{ color: "var(--rot)" }}>
                {result.project_name}: {result.error}
              </p>
            ))}
            {lastSyncResult.ergebnisse.map((result) => result.unzugeordnete_buchungen > 0 && (
              <p key={`unknown-${result.project_id}`} style={{ color: "var(--orange, #a65b00)" }}>
                {result.unzugeordnete_buchungen} Buchungen sind noch keiner Person zugeordnet und werden vorläufig mit 40 Wochenstunden berechnet.
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
