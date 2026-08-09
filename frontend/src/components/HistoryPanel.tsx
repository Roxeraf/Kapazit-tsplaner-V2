import type { PlanHistoryEntry } from "../types";

export const BEREICH_LABELS: Record<PlanHistoryEntry["bereich"], string> = {
  phase: "Phase",
  fte: "FTE (Soll)",
  stammdaten: "Stammdaten",
};

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function describeEntry(entry: PlanHistoryEntry): string {
  if (entry.bereich === "phase") {
    const gesetzt = entry.neuer_wert === "aktiv";
    return `Phase "${entry.feld}"${entry.monat ? ` (${entry.monat})` : ""} ${gesetzt ? "gesetzt" : "entfernt"}`;
  }
  return `${BEREICH_LABELS[entry.bereich]} "${entry.feld}"${entry.monat ? ` (${entry.monat})` : ""}: ${entry.alter_wert ?? "–"} → ${entry.neuer_wert ?? "–"}`;
}

export default function HistoryPanel({ entries }: { entries: PlanHistoryEntry[] }) {
  if (entries.length === 0) {
    return <p style={{ color: "var(--text-muted)", margin: "0.5rem 0 0", fontSize: "0.85rem" }}>Noch keine Änderungen protokolliert.</p>;
  }
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: "0.5rem 0 0", fontSize: "0.85rem" }}>
      {entries.map((entry) => (
        <li key={entry.id} style={{ padding: "0.35rem 0", borderBottom: "1px solid var(--border)" }}>
          <div>{describeEntry(entry)}</div>
          <div style={{ color: "var(--text-muted)" }}>
            {formatTimestamp(entry.geaendert_am)}
            {entry.kommentar && <> — Grund: {entry.kommentar.text}</>}
          </div>
        </li>
      ))}
    </ul>
  );
}
