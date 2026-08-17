import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { PortfolioUtilizationEntry } from "../types";

function levelColor(pct: number | null): string {
  if (pct === null) return "var(--grau)";
  if (pct > 110) return "var(--rot)";
  if (pct > 90) return "var(--gruen)";
  if (pct > 50) return "var(--gelb)";
  return "var(--grau)";
}

export default function Utilization() {
  const [rows, setRows] = useState<PortfolioUtilizationEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getUtilization()
      .then(setRows)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h2 className="section-title" style={{ marginTop: 0 }}>
        Auslastung
      </h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
        Über ResourceAssignment zugeordnetes FTE der aktuellen Periode im Verhältnis zur individuellen
        Kapazität je Teammitglied.
      </p>

      {loading && <p>Lade Auslastung …</p>}
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      {!loading && !error && rows.length === 0 && (
        <div className="stub-view">Keine Teammitglieder gefunden. Lege sie unter Kapazität an.</div>
      )}

      {rows.length > 0 && (
        <table className="planner" style={{ marginTop: "1rem" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>Teammitglied</th>
              <th style={{ textAlign: "left" }}>Team</th>
              <th>Kapazität (FTE)</th>
              <th>Zugeordnet (FTE)</th>
              <th>Auslastung</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.person_id}>
                <td className="label">{r.person_name}</td>
                <td className="label">{r.team_name ?? "Ohne Team"}</td>
                <td>{r.kapazitaet_fte.toFixed(2)}</td>
                <td>{r.zugeordnet_fte.toFixed(2)}</td>
                <td>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
                    <span
                      aria-hidden="true"
                      style={{ width: 9, height: 9, borderRadius: "50%", background: levelColor(r.auslastung_pct) }}
                    />
                    {r.auslastung_pct !== null ? `${r.auslastung_pct.toFixed(0)}%` : "–"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
