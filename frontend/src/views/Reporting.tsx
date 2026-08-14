import { useState } from "react";
import { api } from "../api/client";

function downloadCsv(filename: string, rows: (string | number)[][]) {
  const csv = rows
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(";"))
    .join("\n");
  const blob = new Blob([`﻿${csv}`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function Reporting() {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const exportGap = async () => {
    setBusy("gap");
    setError(null);
    try {
      const rows = await api.getGap();
      downloadCsv("gap-analyse.csv", [
        ["Projekt", "Soll gesamt", "Projiziert gesamt", "Gap gesamt", "Gap %", "Status"],
        ...rows.map((r) => [
          r.project_name,
          r.soll_gesamt,
          r.projiziert_gesamt,
          r.gap_gesamt,
          r.gap_pct !== null ? `${(r.gap_pct * 100).toFixed(1)}%` : "",
          r.status,
        ]),
      ]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const exportForecast = async () => {
    setBusy("forecast");
    setError(null);
    try {
      const rows = await api.getForecast();
      downloadCsv("forecast.csv", [
        ["Projekt", "Soll gesamt", "Hochrechnung", "Gap gesamt", "Gap %", "Status"],
        ...rows.map((r) => [
          r.project_name,
          r.soll_gesamt,
          r.projiziert_gesamt,
          r.gap_gesamt,
          r.gap_pct !== null ? `${(r.gap_pct * 100).toFixed(1)}%` : "",
          r.status,
        ]),
      ]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const exportKpis = async () => {
    setBusy("kpis");
    setError(null);
    try {
      const k = await api.getKpis();
      downloadCsv("kpis.csv", [
        ["Kennzahl", "Wert"],
        ["Aktive Projekte", k.anzahl_projekte_aktiv],
        ["Projekte grün", k.anzahl_projekte_gruen],
        ["Projekte gelb", k.anzahl_projekte_gelb],
        ["Projekte rot", k.anzahl_projekte_rot],
        ["Projekte grau", k.anzahl_projekte_grau],
        ["Ø Auslastung %", k.durchschnittliche_auslastung_pct ?? ""],
        ["Offene Risiken", k.offene_risiken_gesamt],
        ["Offene Entscheidungen", k.offene_entscheidungen_gesamt],
      ]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  const exportUtilization = async () => {
    setBusy("utilization");
    setError(null);
    try {
      const rows = await api.getUtilization();
      downloadCsv("auslastung.csv", [
        ["Teammitglied", "Team", "Kapazität (FTE)", "Zugeordnet (FTE)", "Auslastung %"],
        ...rows.map((r) => [
          r.member_name,
          r.team_name ?? "Ohne Team",
          r.kapazitaet_fte,
          r.zugeordnet_fte,
          r.auslastung_pct ?? "",
        ]),
      ]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <h2 className="section-title" style={{ marginTop: 0 }}>
        Reporting
      </h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
        MVP: CSV-Export der aktuellen Controlling-Daten, direkt im Browser erzeugt (kein Server-Roundtrip). Ein
        Portfolio-weiter PPTX-Export ist eine spätere Ausbaustufe (siehe CONCEPT.md Abschnitt 10).
      </p>

      <div className="card" style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginTop: "1rem" }}>
        <button type="button" className="btn secondary" disabled={busy !== null} onClick={exportGap}>
          {busy === "gap" ? "Exportiert …" : "Gap-Analyse als CSV"}
        </button>
        <button type="button" className="btn secondary" disabled={busy !== null} onClick={exportForecast}>
          {busy === "forecast" ? "Exportiert …" : "Forecast als CSV"}
        </button>
        <button type="button" className="btn secondary" disabled={busy !== null} onClick={exportUtilization}>
          {busy === "utilization" ? "Exportiert …" : "Auslastung als CSV"}
        </button>
        <button type="button" className="btn secondary" disabled={busy !== null} onClick={exportKpis}>
          {busy === "kpis" ? "Exportiert …" : "KPIs als CSV"}
        </button>
      </div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}
    </div>
  );
}
