import { useMemo, useState } from "react";
import {
  detailRows,
  FIELD_LABELS,
  formatHistoryValue,
  formatTime,
  groupHistory,
  HISTORY_FILTERS,
  revisionMatchesFilter,
  revisionMatchesRange,
  revisionTitle,
  type HistoryFilter,
} from "../../../historyFormat";
import type { PlanHistoryEntry } from "../../../types";

export default function HistoryTimeline({ entries }: { entries: PlanHistoryEntry[] }) {
  const [filter, setFilter] = useState<HistoryFilter>("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [openKey, setOpenKey] = useState<string | null>(null);

  const groups = useMemo(() => {
    return groupHistory(entries)
      .map((group) => ({
        ...group,
        revisions: group.revisions.filter(
          (rev) => revisionMatchesFilter(rev.entries, filter) && revisionMatchesRange(rev.entries, from, to),
        ),
      }))
      .filter((group) => group.revisions.length > 0);
  }, [entries, filter, from, to]);

  if (entries.length === 0) {
    return (
      <p style={{ color: "var(--text-muted)", margin: "0.5rem 0 0", fontSize: "0.85rem" }}>
        Noch keine Änderungen protokolliert.
      </p>
    );
  }

  return (
    <div>
      <div className="toolbar" style={{ marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.4rem" }}>
        {HISTORY_FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={filter === item.id ? "btn" : "btn secondary"}
            style={{ fontSize: "0.8rem", padding: "0.15rem 0.6rem" }}
            onClick={() => setFilter(item.id)}
          >
            {item.label}
          </button>
        ))}
        <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginLeft: "auto" }}>
          Von{" "}
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          Bis{" "}
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </div>

      {groups.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Keine Einträge für diesen Filter.</p>
      ) : (
        groups.map((group, i) => (
          <section key={group.dateLabel} style={{ marginBottom: "1rem" }}>
            <h4 style={{ color: "var(--navy)", margin: "0 0 0.4rem" }}>{group.dateLabel}</h4>
            {group.revisions.map((revision) => {
              const first = revision.entries[0];
              const details = detailRows(revision.entries);
              const open = openKey === revision.key || (openKey === null && i === 0 && revision === group.revisions[0]);
              return (
                <div
                  key={revision.key}
                  style={{
                    borderBottom: "1px solid var(--border)",
                    padding: "0.45rem 0",
                    fontSize: "0.88rem",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setOpenKey(open ? "" : revision.key)}
                    style={{
                      border: "none",
                      background: "none",
                      padding: 0,
                      cursor: "pointer",
                      textAlign: "left",
                      width: "100%",
                      color: "inherit",
                    }}
                  >
                    <span style={{ color: "var(--text-muted)" }}>{formatTime(first.geaendert_am)}</span>
                    {" · "}
                    <strong>{revisionTitle(revision.entries)}</strong>
                  </button>
                  {open && details.length > 0 && (
                    <div style={{ padding: "0.35rem 0 0.15rem 1.1rem", color: "var(--text-muted)", fontSize: "0.83rem" }}>
                      {details.map((entry) => (
                        <div key={entry.id} style={{ marginBottom: "0.2rem" }}>
                          <span style={{ minWidth: "8rem", display: "inline-block" }}>
                            {FIELD_LABELS[entry.feld] ?? entry.feld}
                          </span>
                          {formatHistoryValue(entry.feld, entry.alter_wert)}
                          {" → "}
                          {formatHistoryValue(entry.feld, entry.neuer_wert)}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </section>
        ))
      )}
    </div>
  );
}
