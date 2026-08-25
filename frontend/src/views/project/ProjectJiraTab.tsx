import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { JiraStatus, JiraSyncResult, JiraSyncStatus, ProjectActualsCoverage } from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

// P20.5 (siehe P20_5_PHASE_ACTUALS_AND_TIME_CONTROL.md Abschnitt 15): kompakte
// "Aktualisiert vor X Minuten"-Anzeige für die Sync-Freshness - keine Sekundenpräzision.
function fmtRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.max(0, Math.round(diffMs / 60000));
  if (minutes < 1) return "gerade eben";
  if (minutes === 1) return "vor 1 Minute";
  if (minutes < 60) return `vor ${minutes} Minuten`;
  const hours = Math.round(minutes / 60);
  return hours === 1 ? "vor 1 Stunde" : `vor ${hours} Stunden`;
}

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function ProjectJiraTab() {
  const { project, reload } = useProjectWorkspace();
  const [error, setError] = useState<string | null>(null);
  const [jiraStatus, setJiraStatus] = useState<JiraStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState<JiraSyncResult | null>(null);
  // P20.5 (Abschnitt 15): Sync-Freshness dieses Projekts - vom manuellen Sync UND vom
  // automatischen Background-Sync (alle 15 Minuten, siehe scheduler.py) gepflegt.
  const [syncStatus, setSyncStatus] = useState<JiraSyncStatus | null>(null);
  // P20.7 (siehe P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 19/26): dieselbe
  // Vertrauens-/Vollständigkeitskennzahl wie im Kapazität-Tab einer einzelnen Phase (P20.5),
  // hier projektweit im Jira-Tab - kein neuer Endpoint, wiederverwendet GET
  // /projects/{id}/actuals-coverage (P20.3). Neu geladen bei jedem reload() (z.B. nach Sync).
  const [coverage, setCoverage] = useState<ProjectActualsCoverage | null>(null);

  useEffect(() => {
    api
      .jiraStatus()
      .then(setJiraStatus)
      .catch((e) => setError(`Integrationsstatus konnte nicht geladen werden: ${String(e)}`));
  }, []);

  const loadSyncStatus = () => {
    api.jiraSyncStatus(project.id).then(setSyncStatus).catch(() => setSyncStatus(null));
  };

  useEffect(() => {
    loadSyncStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  useEffect(() => {
    api.getProjectActualsCoverage(project.id).then(setCoverage).catch(() => setCoverage(null));
  }, [project.id, project.ist]);

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      const result = await api.jiraSync(project.id);
      setLastSyncResult(result);
      loadSyncStatus();
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
        {/* P20.5 (Abschnitt 13-15): der automatische Background-Sync (alle 15 Minuten) ist
            seither die Voraussetzung für aktuelle Ist-Daten, nicht mehr dieser Button - er
            bleibt als "Jetzt aktualisieren"-Sonderfall bestehen (z.B. um nicht auf den
            nächsten Zyklus zu warten). */}
        {syncStatus && (
          <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
            {syncStatus.last_success_at ? (
              <>
                Stand: {fmtDateTime(syncStatus.last_success_at)} ({fmtRelative(syncStatus.last_success_at)})
              </>
            ) : (
              <>Noch keine erfolgreiche Synchronisierung.</>
            )}
            {syncStatus.autosync_enabled && (
              <span> · automatische Aktualisierung alle 15 Minuten aktiv</span>
            )}
            {syncStatus.last_error && (
              <div style={{ color: "var(--rot)", marginTop: "0.2rem" }}>
                Jira-Synchronisierung aktuell nicht möglich: {syncStatus.last_error}
                {syncStatus.last_success_at && " (bisherige Ist-Werte bleiben erhalten)"}
              </div>
            )}
          </div>
        )}
        {jiraConfigured && project.jira_component && (
          <button type="button" className="btn secondary" disabled={syncing} onClick={handleSync}>
            {syncing ? "Aktualisiert …" : "Jetzt aktualisieren"}
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

      {/* P20.7 (Projekt-Coverage-Anzeige, siehe
          P20_PLANPHASE_ACTUALS_AND_PLAN_VS_ACTUAL.md Abschnitt 19/26): reine Vertrauens-/
          Vollständigkeitskennzahl, wie vollständig die Tempo-Ist-Stunden bereits PlanPhasen
          zugeordnet sind - KEINE Health-Ampel, keine Bewertung. Projekt-Ist (oben, "Ist-FTE")
          bleibt davon unberührt und weiterhin die führende Quelle. */}
      {coverage && coverage.project_ist_total > 0 && (
        <div className="card" style={{ marginTop: "1.25rem" }}>
          <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Ist-Zuordnung zu PlanPhasen</h3>
          <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem" }}>
            <div>
              <strong>Gesamt:</strong> {coverage.project_ist_total} h
            </div>
            <div>
              <strong>Zu PlanPhasen zugeordnet:</strong> {coverage.mapped_total} h
            </div>
            {coverage.ambiguous_total > 0 && (
              <div>
                <strong>Nicht eindeutig zugeordnet:</strong> {coverage.ambiguous_total} h
              </div>
            )}
            <div>
              <strong>Nicht zugeordnet:</strong> {coverage.unmapped_total} h
            </div>
            <div style={{ paddingTop: "0.3rem", borderTop: "1px solid var(--border)" }}>
              <strong>Coverage:</strong> {coverage.coverage_pct == null ? "—" : `${coverage.coverage_pct}%`}
            </div>
          </div>
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.6rem 0 0" }}>
            Zuordnung erfolgt je Planphase über das Jira-Label (Drawer → Übersicht →
            "Steuerung" → "Ist-Zuordnung konfigurieren"). Diese Kennzahl bewertet nur die
            Vollständigkeit der Zuordnung, nicht den Projektfortschritt.
          </p>
        </div>
      )}
    </div>
  );
}
