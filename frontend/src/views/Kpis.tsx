import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { KpiSummary } from "../types";

function StatTile({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="card" style={{ textAlign: "center" }}>
      <div style={{ fontSize: "1.6rem", fontWeight: 700, color: color ?? "var(--navy)" }}>{value}</div>
      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>{label}</div>
    </div>
  );
}

export default function Kpis() {
  const [kpis, setKpis] = useState<KpiSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getKpis().then(setKpis).catch((e) => setError(String(e)));
  }, []);

  if (error) return <p style={{ color: "var(--rot)" }}>{error}</p>;
  if (!kpis) return <p>Lade KPIs …</p>;

  return (
    <div>
      <h2 className="section-title" style={{ marginTop: 0 }}>
        KPIs
      </h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
        Portfolio-Kennzahlen, aggregiert aus Gap-Analyse, Auslastung und Kommunikation.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
        <StatTile label="Aktive Projekte" value={kpis.anzahl_projekte_aktiv} />
        <StatTile
          label="Ø Auslastung"
          value={kpis.durchschnittliche_auslastung_pct !== null ? `${kpis.durchschnittliche_auslastung_pct.toFixed(0)}%` : "–"}
        />
        <StatTile label="Offene Risiken" value={kpis.offene_risiken_gesamt} color="var(--rot)" />
        <StatTile label="Offene Entscheidungen" value={kpis.offene_entscheidungen_gesamt} color="var(--gelb)" />
      </div>

      <h3 style={{ color: "var(--navy)", marginTop: "1.5rem" }}>Projektstatus-Verteilung (Gap-Ampel)</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "1rem" }}>
        <StatTile label="Grün" value={kpis.anzahl_projekte_gruen} color="var(--gruen)" />
        <StatTile label="Gelb" value={kpis.anzahl_projekte_gelb} color="var(--gelb)" />
        <StatTile label="Rot" value={kpis.anzahl_projekte_rot} color="var(--rot)" />
        <StatTile label="Grau (keine Ist-Daten)" value={kpis.anzahl_projekte_grau} color="var(--grau)" />
      </div>
    </div>
  );
}
