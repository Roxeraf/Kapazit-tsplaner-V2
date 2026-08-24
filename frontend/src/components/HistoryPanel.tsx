import type { PlanHistoryEntry } from "../types";
import { describeEntry, formatTimestamp } from "../historyFormat";

export { describeEntry, formatTimestamp };

export default function HistoryPanel({ entries }: { entries: PlanHistoryEntry[] }) {
  if (entries.length === 0) {
    return (
      <p style={{ color: "var(--text-muted)", margin: "0.5rem 0 0", fontSize: "0.85rem" }}>
        Noch keine Änderungen protokolliert.
      </p>
    );
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
