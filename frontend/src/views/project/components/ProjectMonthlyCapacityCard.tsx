import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import type { ProjectMonthlyCapacityEntry } from "../../../types";

// P19.7 (CONCEPT.md Abschnitt 6b.6, Auftrag Abschnitt 20): "Projektkapazität(Monat)" ist
// bereits final gelockt/CONFIRMED im Backend (GET /projects/{id}/capacity/monthly), wurde im
// P19-Audit aber als Frontend-Drilldown nicht verifiziert (§17) - Recherche für dieses Paket
// ergab: es gab bislang GAR KEINE Frontend-Darstellung dieses Endpoints. Diese Karte zeigt
// die vom Backend bereits abgeleitete Monatssumme (ausschließlich aus PlanPhase.plan_fte,
// SUM(monthly_distribution(...)) über alle Leaf-Phasen) und erlaubt den Drilldown je Monat
// nach beitragender Phase (by_phase, additiv zur bestehenden Summe). Rein lesende Auswertung -
// KEINE Bewertung/Ampel/"Plan erfüllt"-Aussage, wie vom Auftrag ausdrücklich verlangt.
export default function ProjectMonthlyCapacityCard({ projectId }: { projectId: number }) {
  const [entries, setEntries] = useState<ProjectMonthlyCapacityEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedPeriod, setExpandedPeriod] = useState<string | null>(null);

  useEffect(() => {
    api
      .getProjectMonthlyCapacity(projectId)
      .then(setEntries)
      .catch((e) => setError(String(e)));
  }, [projectId]);

  return (
    <div>
      <h3 style={{ color: "var(--navy)", margin: 0 }}>Projektkapazität nach Monat</h3>
      <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "0.3rem" }}>
        Abgeleitet aus den Planphasen oben (Plan-Aufwand je Phase, werktage-anteilig auf berührte Monate verteilt) -
        reine Auswertung, kein eigenes Eingabefeld. Zum Aufschlüsseln nach Phase auf einen Monat klicken.
      </p>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {entries == null ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Lädt …</p>
      ) : entries.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Keine Planphasen mit Zeitraum im Projektzeitraum.</p>
      ) : (
        <div style={{ display: "grid", gap: "0.4rem", marginTop: "0.5rem" }}>
          {entries.map((entry) => {
            const isOpen = expandedPeriod === entry.period;
            return (
              <div key={entry.period} className="card" style={{ padding: "0.55rem 0.85rem" }}>
                <button
                  type="button"
                  onClick={() => setExpandedPeriod(isOpen ? null : entry.period)}
                  disabled={entry.by_phase.length === 0}
                  style={{
                    border: "none",
                    background: "none",
                    padding: 0,
                    width: "100%",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: "0.88rem",
                    cursor: entry.by_phase.length === 0 ? "default" : "pointer",
                    color: "inherit",
                  }}
                >
                  <span>
                    {entry.by_phase.length > 0 ? (isOpen ? "▾ " : "▸ ") : ""}
                    <strong>{entry.period}</strong>
                  </span>
                  <span style={{ color: "var(--text-muted)" }}>
                    {entry.hours.toFixed(1)} h ≈ {entry.fte_equivalent.toFixed(2)} FTE
                  </span>
                </button>

                {isOpen && entry.by_phase.length > 0 && (
                  <div style={{ marginTop: "0.4rem", paddingTop: "0.4rem", borderTop: "1px solid var(--border)", display: "grid", gap: "0.15rem" }}>
                    {entry.by_phase.map((contribution) => (
                      <div
                        key={contribution.plan_phase_id}
                        style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", color: "var(--text-muted)" }}
                      >
                        <span>{contribution.phase_type}</span>
                        <span>{contribution.hours.toFixed(1)} h</span>
                      </div>
                    ))}
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.82rem", marginTop: "0.15rem", fontWeight: 600 }}>
                      <span>Gesamt</span>
                      <span>
                        {entry.hours.toFixed(1)} h ≈ {entry.fte_equivalent.toFixed(2)} FTE
                      </span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
