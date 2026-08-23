import { useEffect, useMemo, useState } from "react";
import { api } from "../../../api/client";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import { ENTITY_TYPE_META as TYPE_META } from "../../../entityTypeMeta";
import { FOLLOW_UP_ACTIONS, useFollowUpAction } from "../../../hooks/useFollowUpAction";
import type { ActivityItem, EntityType } from "../../../types";

function formatRelative(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const days = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (days <= 0) return "heute";
  if (days === 1) return "gestern";
  if (days < 30) return `vor ${days} Tagen`;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export default function ActivityFeed({
  projectId,
  filterTypes,
  onOpenSection,
  onChanged,
  planPhaseId,
  // P19.3 (Tag-Vorschlag bei Folgeobjekten): zusätzlich zu den Tags des Ursprungs-Items werden
  // die Tags der aktuellen Phase vorgeschlagen, falls der Feed im Phasenkontext läuft (siehe
  // CONCEPT.md Abschnitt 8 Beispiel "#Schnittstelle #Kunde von der Phase + #API vom Kommentar").
  phaseTags = [],
  refreshToken,
}: {
  projectId: number;
  filterTypes: EntityType[];
  onOpenSection: (type: EntityType) => void;
  // Der Feed lädt intern selbst nach - ändert sich Aktivität aber durch eine SCHWESTER-
  // Komponente (z.B. NotesSection/TaskList im selben Tab), bekommt ActivityFeed das nicht von
  // selbst mit. refreshToken ist ein simpler Zähler, den der Elternteil bei jeder Mutation
  // hochzählt, damit der Feed konsistent mit dem Rest des Tabs bleibt (P16.1).
  refreshToken?: number;
  onChanged: () => void;
  planPhaseId?: number;
  phaseTags?: string[];
}) {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [typeFilter, setTypeFilter] = useState<EntityType | null>(null);
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    const fetcher = planPhaseId
      ? api.getPlanPhaseActivity(planPhaseId)
      : api.getActivity(projectId);
    fetcher.then(setItems).catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId, planPhaseId, refreshToken]);

  const followUp = useFollowUpAction(projectId, planPhaseId, () => {
    refresh();
    onChanged();
  });

  const availableTags = useMemo(() => {
    const tags = new Set<string>();
    for (const i of items) if (filterTypes.includes(i.entity_type)) i.tags.forEach((t) => tags.add(t));
    return Array.from(tags).sort();
  }, [items, filterTypes]);

  const visible = useMemo(
    () =>
      items.filter(
        (i) =>
          filterTypes.includes(i.entity_type) &&
          (!typeFilter || i.entity_type === typeFilter) &&
          (tagFilter.length === 0 || i.tags.some((t) => tagFilter.includes(t))),
      ),
    [items, filterTypes, typeFilter, tagFilter],
  );

  const toggleTagFilter = (tag: string) => {
    setTagFilter((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]));
  };

  // P19.3: Tag-Vorschlag ist die Union aus Item- und Phasen-Tags (dedupliziert), weiterhin nur
  // ein Vorschlag - keine harte Vererbung.
  const startFollowUp = (item: ActivityItem, target: EntityType) => {
    const suggested = Array.from(new Set([...item.tags, ...phaseTags]));
    followUp.start({ entity_type: item.entity_type, entity_id: item.entity_id }, target, suggested);
  };

  const markBlockerResolved = async (item: ActivityItem) => {
    await api.updateBlocker(item.entity_id, { status: "geloest" });
    refresh();
    onChanged();
  };

  return (
    <div>
      {(error || followUp.error) && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error ?? followUp.error}</p>}
      <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginBottom: "0.75rem" }}>
        <button type="button" className={typeFilter === null ? "btn" : "btn secondary"} onClick={() => setTypeFilter(null)}>
          Alle
        </button>
        {filterTypes.map((t) => (
          <button
            key={t}
            type="button"
            className={typeFilter === t ? "btn" : "btn secondary"}
            onClick={() => setTypeFilter(t)}
          >
            {TYPE_META[t].icon} {TYPE_META[t].label}
          </button>
        ))}
      </div>

      {/* P12.5 (Tag-Filter im Activity-Kontext): rein frontendseitig, alle Daten kommen bereits
          im Activity-Payload mit (item.tags) - kein neuer Endpoint. */}
      {availableTags.length > 0 && (
        <div style={{ display: "flex", gap: "0.3rem", flexWrap: "wrap", marginBottom: "0.75rem", alignItems: "center" }}>
          <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Tags:</span>
          {availableTags.map((t) => (
            <button
              key={t}
              type="button"
              className={tagFilter.includes(t) ? "btn" : "btn secondary"}
              style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem" }}
              onClick={() => toggleTagFilter(t)}
            >
              #{t}
            </button>
          ))}
          {tagFilter.length > 0 && (
            <button type="button" className="btn secondary" style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem" }} onClick={() => setTagFilter([])}>
              Zurücksetzen
            </button>
          )}
        </div>
      )}

      {visible.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Aktivität.</p>
      ) : (
        visible.map((item) => {
          const meta = TYPE_META[item.entity_type];
          const actions = FOLLOW_UP_ACTIONS[item.entity_type] ?? [];
          const key = `${item.entity_type}-${item.entity_id}`;
          return (
            <div key={key} className="card" style={{ marginBottom: "0.5rem", padding: "0.5rem 0.85rem", fontSize: "0.88rem" }}>
              <div className="toolbar">
                <span>
                  <span aria-hidden="true">{meta.icon}</span>{" "}
                  <button
                    type="button"
                    onClick={() => onOpenSection(item.entity_type)}
                    style={{ border: "none", background: "none", cursor: "pointer", color: "var(--navy)", fontWeight: 600, padding: 0 }}
                  >
                    {item.label ?? `${meta.label} #${item.entity_id}`}
                  </button>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.78rem", marginLeft: "0.4rem" }}>
                    {meta.label} · {formatRelative(item.timestamp)}
                  </span>
                </span>
              </div>
              {item.tags.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.25rem 0" }}>
                  {item.tags.map((t) => (
                    <TagChip key={t} name={t} />
                  ))}
                </div>
              )}
              {(actions.length > 0 || item.entity_type === "blocker") && (
                <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginTop: "0.35rem" }}>
                  {actions.map((a) => (
                    <button key={a.target} type="button" className="btn secondary" style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem" }} onClick={() => startFollowUp(item, a.target)}>
                      {a.label}
                    </button>
                  ))}
                  {item.entity_type === "blocker" && (
                    <button
                      type="button"
                      className="btn secondary"
                      style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem" }}
                      onClick={() => markBlockerResolved(item)}
                    >
                      Als gelöst markieren
                    </button>
                  )}
                </div>
              )}
              {followUp.pending && followUp.pending.source.entity_type === item.entity_type && followUp.pending.source.entity_id === item.entity_id && (
                <div style={{ marginTop: "0.4rem", padding: "0.5rem", background: "#f8fafc", borderRadius: "4px" }}>
                  <input
                    autoFocus
                    value={followUp.draftTitle}
                    onChange={(e) => followUp.setDraftTitle(e.target.value)}
                    placeholder={`Titel für ${TYPE_META[followUp.pending.target].label}`}
                    style={{ width: "100%" }}
                  />
                  <div style={{ marginTop: "0.4rem" }}>
                    {followUp.draftTags.length > 0 && (
                      <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                        Tags aus {meta.label}{phaseTags.length > 0 ? " + Phase" : ""} vorgeschlagen — abwählbar, weitere ergänzbar:
                      </span>
                    )}
                    <TagInput value={followUp.draftTags} onChange={followUp.setDraftTags} />
                  </div>
                  <div className="field-row" style={{ marginTop: "0.5rem" }}>
                    <button type="button" className="btn secondary" disabled={followUp.saving || !followUp.draftTitle.trim()} onClick={followUp.submit}>
                      Erstellen
                    </button>
                    <button type="button" className="btn secondary" onClick={followUp.cancel}>
                      Abbrechen
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
