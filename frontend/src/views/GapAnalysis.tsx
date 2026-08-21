import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { GapAnalysis as GapAnalysisT, GapStatus, Team } from "../types";

const STATUS_LABEL: Record<GapStatus, string> = {
  gruen: "im Plan",
  gelb: "Abweichung",
  rot: "kritische Abweichung",
  grau: "keine Ist-Daten",
};

function StatusBadge({ status }: { status: GapStatus }) {
  return (
    <span className={`gap-badge gap-badge--${status}`}>
      <span className="gap-status-dot" />
      {STATUS_LABEL[status]}
    </span>
  );
}

function ProjectGapCard({ gap }: { gap: GapAnalysisT }) {
  const alleWerte = gap.monate.flatMap((m) => [gap.soll[m] ?? 0, gap.ist[m] ?? 0, gap.hochrechnung[m] ?? 0]);
  const max = Math.max(1, ...alleWerte);

  return (
    <div className="card" style={{ marginTop: "1.25rem" }}>
      <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
        <div>
          <Link to={`/projekte/${gap.project_id}`} style={{ textDecoration: "none" }}>
            <h3 style={{ color: "var(--navy)", margin: 0 }}>{gap.project_name}</h3>
          </Link>
          <p style={{ margin: "0.2rem 0 0", fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Hochrechnung {gap.monate[gap.monate.length - 1]}: {gap.projiziert_gesamt.toFixed(2)} FTE ·
            Soll {gap.soll_gesamt.toFixed(2)} FTE ·{" "}
            {gap.gap_pct !== null ? `Gap ${(gap.gap_pct * 100).toFixed(0)}%` : "Gap unbekannt"}
          </p>
        </div>
        <StatusBadge status={gap.status} />
      </div>

      <div className="gap-chart">
        {gap.monate.map((m) => {
          const soll = gap.soll[m] ?? 0;
          const ist = gap.ist[m];
          const hoch = gap.hochrechnung[m];
          return (
            <div key={m} className="gap-chart-col">
              <div className="gap-bar-group">
                <div className="gap-bar gap-bar--soll" style={{ height: `${(soll / max) * 100}%` }} title={`Soll: ${soll.toFixed(2)}`} />
                {ist !== undefined && (
                  <div className="gap-bar gap-bar--ist" style={{ height: `${(ist / max) * 100}%` }} title={`Ist: ${ist.toFixed(2)}`} />
                )}
                {hoch !== undefined && (
                  <div
                    className="gap-bar gap-bar--hochrechnung"
                    style={{ height: `${(hoch / max) * 100}%` }}
                    title={`Hochrechnung: ${hoch.toFixed(2)}`}
                  />
                )}
              </div>
              <span className="gap-chart-label">{m}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function GapAnalysis() {
  const [gaps, setGaps] = useState<GapAnalysisT[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [teamId, setTeamId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTeams()
      .then(setTeams)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .getGap(teamId ? Number(teamId) : undefined)
      .then(setGaps)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [teamId]);

  return (
    <div>
      <div className="toolbar">
        <h2 className="section-title" style={{ margin: 0 }}>
          Gap-Analyse
        </h2>
        <label style={{ fontSize: "0.85rem", color: "var(--text-muted)", display: "flex", gap: "0.4rem", alignItems: "center" }}>
          Team
          <select value={teamId} onChange={(e) => setTeamId(e.target.value)}>
            <option value="">Alle Teams</option>
            {teams
              .filter((t) => t.id !== 0)
              .map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
          </select>
        </label>
      </div>

      <div className="legend-row">
        <span className="legend-chip">
          <span className="legend-swatch" style={{ background: "var(--gap-soll)" }} /> Soll
        </span>
        <span className="legend-chip">
          <span className="legend-swatch" style={{ background: "var(--gap-ist)" }} /> Ist (Jira)
        </span>
        <span className="legend-chip">
          <span className="legend-swatch" style={{ background: "var(--gap-hochrechnung)" }} /> Hochrechnung (Trend)
        </span>
      </div>

      {loading && <p>Lade Gap-Analyse …</p>}
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      {!loading && !error && gaps.length === 0 && (
        <div className="stub-view">
          Keine Projekte mit FTE-Planung gefunden. Lege im Projektmanagement-Dashboard ein Projekt mit Soll-FTE an — die
          Gap-Analyse benötigt zusätzlich eine gepflegte Jira-Komponente (Projekt-Detail) und einen erfolgreichen
          Jira-Sync (Team-Kapazität), um Ist-Werte anzuzeigen.
        </div>
      )}

      {gaps.map((g) => (
        <ProjectGapCard key={g.project_id} gap={g} />
      ))}
    </div>
  );
}
