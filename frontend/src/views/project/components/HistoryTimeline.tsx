import { describeEntry, formatTimestamp } from "../../../components/HistoryPanel";
import type { PlanHistoryEntry } from "../../../types";

const STAMMDATEN_FELD_LABELS: Record<string, string> = {
  name: "Projektname",
  kunde: "Kunde",
  start_monat: "Startmonat",
  anzahl_monate: "Anzahl Monate",
  status: "Status",
  projektleiter: "Projektleiter",
  jira_component: "Jira-Komponente",
};

interface Revision {
  key: string;
  entries: PlanHistoryEntry[];
}

interface DateGroup {
  dateLabel: string;
  revisions: Revision[];
}

function dateLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Unbekanntes Datum";
  const today = new Date();
  const isToday = d.toDateString() === today.toDateString();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = d.toDateString() === yesterday.toDateString();
  if (isToday) return "Heute";
  if (isYesterday) return "Gestern";
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function groupEntries(entries: PlanHistoryEntry[]): DateGroup[] {
  const groups: DateGroup[] = [];
  const dateIndex = new Map<string, DateGroup>();
  const revisionIndex = new Map<string, Revision>();

  for (const entry of entries) {
    const dLabel = dateLabel(entry.geaendert_am);
    let dateGroup = dateIndex.get(dLabel);
    if (!dateGroup) {
      dateGroup = { dateLabel: dLabel, revisions: [] };
      dateIndex.set(dLabel, dateGroup);
      groups.push(dateGroup);
    }

    // Einträge ohne batch_id (ältere Daten oder Änderungen außerhalb des Planung-Speicherflows)
    // bilden je eine eigene Einzel-Revision (Schlüssel = eigene id).
    const revisionKey = entry.batch_id ? `${dLabel}:${entry.batch_id}` : `${dLabel}:single:${entry.id}`;
    let revision = revisionIndex.get(revisionKey);
    if (!revision) {
      revision = { key: revisionKey, entries: [] };
      revisionIndex.set(revisionKey, revision);
      dateGroup.revisions.push(revision);
    }
    revision.entries.push(entry);
  }

  return groups;
}

function summarize(entries: PlanHistoryEntry[]): string[] {
  const bullets: string[] = [];

  const stammdatenFelder = Array.from(new Set(entries.filter((e) => e.bereich === "stammdaten").map((e) => e.feld)));
  for (const feld of stammdatenFelder) {
    bullets.push(`${STAMMDATEN_FELD_LABELS[feld] ?? feld} geändert`);
  }

  const phaseCount = entries.filter((e) => e.bereich === "phase").length;
  if (phaseCount > 0) bullets.push(`${phaseCount} Phase${phaseCount === 1 ? "" : "n"} geändert`);

  const fteEntries = entries.filter((e) => e.bereich === "fte");
  if (fteEntries.length === 1) {
    bullets.push(`FTE (${fteEntries[0].monat ?? "–"}) geändert`);
  } else if (fteEntries.length > 1) {
    bullets.push(`${fteEntries.length} FTE-Werte geändert`);
  }

  return bullets;
}

export default function HistoryTimeline({ entries }: { entries: PlanHistoryEntry[] }) {
  if (entries.length === 0) {
    return <p style={{ color: "var(--text-muted)", margin: "0.5rem 0 0", fontSize: "0.85rem" }}>Noch keine Änderungen protokolliert.</p>;
  }

  const groups = groupEntries(entries);

  return (
    <div>
      {groups.map((group, i) => (
        <details key={group.dateLabel} open={i === 0} style={{ marginBottom: "0.5rem" }}>
          <summary style={{ cursor: "pointer", color: "var(--navy)", fontWeight: 600 }}>{group.dateLabel}</summary>
          <div style={{ paddingLeft: "0.75rem", marginTop: "0.35rem" }}>
            {group.revisions.map((revision) => {
              const first = revision.entries[0];
              const bullets = summarize(revision.entries);
              return (
                <details key={revision.key} style={{ marginBottom: "0.5rem" }}>
                  <summary style={{ cursor: "pointer", fontSize: "0.88rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>{formatTimestamp(first.geaendert_am)}</span>
                    {first.kommentar && <> — „{first.kommentar.text}“</>}
                    {bullets.length > 0 && (
                      <ul style={{ margin: "0.25rem 0 0", paddingLeft: "1.1rem" }}>
                        {bullets.map((b) => (
                          <li key={b} style={{ color: "var(--text-muted)" }}>
                            {b}
                          </li>
                        ))}
                      </ul>
                    )}
                  </summary>
                  <ul style={{ listStyle: "none", padding: "0 0 0 1.1rem", margin: "0.35rem 0 0", fontSize: "0.83rem" }}>
                    {revision.entries.map((entry) => (
                      <li key={entry.id} style={{ padding: "0.2rem 0", borderBottom: "1px solid var(--border)" }}>
                        {describeEntry(entry)}
                      </li>
                    ))}
                  </ul>
                </details>
              );
            })}
          </div>
        </details>
      ))}
    </div>
  );
}
