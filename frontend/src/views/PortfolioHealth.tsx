import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { HEALTH_DIMENSION_LABELS, HEALTH_STATUS_COLOR, type PortfolioAllocationGapEntry, type ProjectHealth } from "../types";

const MONAT_NAMEN = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];

// Muss exakt backend/app/constants.py::current_period() entsprechen ("Apr 26"-Format).
function currentPeriod(): string {
  const today = new Date();
  return `${MONAT_NAMEN[today.getMonth()]} ${String(today.getFullYear() % 100).padStart(2, "0")}`;
}

// Phase 26.7: Portfolioweite Sicht auf die bisher komplett ungenutzten Controlling-Endpunkte
// (backend/app/routers/controlling.py, Phase 23) - Project Health über alle Projekte sowie
// Ressourcenengpässe der aktuellen Periode, jeweils mit Sprung zum betroffenen Projekt.
export default function PortfolioHealth() {
  const [health, setHealth] = useState<ProjectHealth[]>([]);
  const [gaps, setGaps] = useState<PortfolioAllocationGapEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const period = currentPeriod();

  useEffect(() => {
    setLoading(true);
    Promise.all([api.getPortfolioHealth(), api.getAllocationGaps(period)])
      .then(([h, g]) => {
        setHealth(h);
        setGaps(g);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const shortfalls = gaps.filter((g) => g.allocation_gap > 0).sort((a, b) => b.allocation_gap - a.allocation_gap);

  return (
    <div>
      <h2 className="section-title">Portfolio Health</h2>
      {loading && <p>Lade Portfolio-Übersicht …</p>}
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      {!loading && !error && (
        <>
          <div className="card" style={{ marginBottom: "1.25rem" }}>
            <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Health je Projekt</h3>
            {health.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Keine Projekte gefunden.</p>
            ) : (
              <table className="planner">
                <thead>
                  <tr>
                    <th style={{ textAlign: "left" }}>Projekt</th>
                    {(Object.keys(HEALTH_DIMENSION_LABELS) as (keyof typeof HEALTH_DIMENSION_LABELS)[]).map((key) => (
                      <th key={key}>{HEALTH_DIMENSION_LABELS[key]}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {health.map((h) => (
                    <tr key={h.project_id}>
                      <td className="label">
                        <Link to={`/projekte/${h.project_id}`}>{h.project_name}</Link>
                      </td>
                      {(Object.keys(HEALTH_DIMENSION_LABELS) as (keyof typeof HEALTH_DIMENSION_LABELS)[]).map((key) => (
                        <td key={key} title={h[key].explanation}>
                          <span
                            aria-hidden="true"
                            style={{
                              display: "inline-block",
                              width: 9,
                              height: 9,
                              borderRadius: "50%",
                              background: HEALTH_STATUS_COLOR[h[key].status],
                            }}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Kapazitätsengpässe ({period})</h3>
            {shortfalls.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Keine Unterdeckung in dieser Periode.</p>
            ) : (
              <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "0.88rem" }}>
                {shortfalls.map((g) => (
                  <li key={g.resource_demand_id} style={{ padding: "0.35rem 0", borderBottom: "1px solid var(--border)" }}>
                    <Link to={`/projekte/${g.project_id}/planung`}>{g.project_name}</Link> — {g.resource_role_name}: Bedarf{" "}
                    {g.fte.toFixed(2)} FTE, zugeordnet {g.assigned_fte.toFixed(2)} FTE ·{" "}
                    <span style={{ color: "var(--rot)" }}>{g.allocation_gap.toFixed(2)} FTE</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
