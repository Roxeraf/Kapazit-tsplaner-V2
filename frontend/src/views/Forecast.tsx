import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ForecastSummary, GapStatus } from "../types";

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

export default function Forecast() {
  const [rows, setRows] = useState<ForecastSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getForecast()
      .then(setRows)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h2 className="section-title" style={{ marginTop: 0 }}>
        Forecast
      </h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
        Hochrechnung Jahresende/Projektende je Projekt (Trendfortschreibung, siehe CONCEPT.md Abschnitt 5).
      </p>

      {loading && <p>Lade Forecast …</p>}
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      {!loading && !error && rows.length === 0 && (
        <div className="stub-view">Keine Projekte mit FTE-Planung gefunden.</div>
      )}

      {rows.map((r) => (
        <div key={r.project_id} className="card" style={{ marginBottom: "0.75rem" }}>
          <div className="toolbar">
            <div>
              <Link to={`/projekte/${r.project_id}`} style={{ textDecoration: "none" }}>
                <h3 style={{ color: "var(--navy)", margin: 0 }}>{r.project_name}</h3>
              </Link>
              <p style={{ margin: "0.2rem 0 0", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                Hochrechnung: {r.projiziert_gesamt.toFixed(2)} FTE · Soll: {r.soll_gesamt.toFixed(2)} FTE ·{" "}
                {r.gap_pct !== null ? `Gap ${(r.gap_pct * 100).toFixed(0)}%` : "Gap unbekannt"}
              </p>
            </div>
            <StatusBadge status={r.status} />
          </div>
        </div>
      ))}
    </div>
  );
}
