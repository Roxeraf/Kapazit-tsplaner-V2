import { useEffect, useMemo, useState } from "react";
import { api } from "../../../api/client";
import TagChip from "../../../components/TagChip";
import { ENTITY_TYPE_META as TYPE_META } from "../../../entityTypeMeta";
import type { ActivityItem, EntityType } from "../../../types";

// Kontextuelle "aus diesem Objekt erstellen"-Aktionen je Quelltyp (Phase 26.4). Jede Aktion
// legt zuerst die Folge-Entität über den bestehenden Create-Endpoint an, danach eine
// EntityRelation (relation_type "resulted_in") - keine neuen Backend-Endpoints nötig.
const FOLLOW_UP_ACTIONS: Partial<Record<EntityType, { target: EntityType; label: string }[]>> = {
  comment: [
    { target: "decision", label: "+ Entscheidung" },
    { target: "task", label: "+ Aufgabe" },
    { target: "risk", label: "+ Risiko" },
    { target: "blocker", label: "+ Blocker" },
  ],
  decision: [
    { target: "task", label: "+ Folgeaufgabe" },
    { target: "blocker", label: "+ Blocker" },
  ],
  blocker: [{ target: "task", label: "+ Aufgabe" }],
};

function formatRelative(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const days = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (days <= 0) return "heute";
  if (days === 1) return "gestern";
  if (days < 30) return `vor ${days} Tagen`;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

async function createFollowUpEntity(projectId: number, target: EntityType, titel: string) {
  switch (target) {
    case "decision":
      return api.createDecision(projectId, { titel });
    case "task":
      return api.createTask(projectId, { titel });
    case "risk":
      return api.createRisk(projectId, { titel });
    case "blocker":
      return api.createBlocker(projectId, { title: titel });
    default:
      throw new Error(`Unbekannter Zieltyp: ${target}`);
  }
}

export default function ActivityFeed({
  projectId,
  filterTypes,
  onOpenSection,
  onChanged,
}: {
  projectId: number;
  filterTypes: EntityType[];
  onOpenSection: (type: EntityType) => void;
  onChanged: () => void;
}) {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [typeFilter, setTypeFilter] = useState<EntityType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<{ item: ActivityItem; target: EntityType } | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [saving, setSaving] = useState(false);

  const refresh = () => {
    api.getActivity(projectId).then(setItems).catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId]);

  const visible = useMemo(
    () => items.filter((i) => filterTypes.includes(i.entity_type) && (!typeFilter || i.entity_type === typeFilter)),
    [items, filterTypes, typeFilter],
  );

  const startFollowUp = (item: ActivityItem, target: EntityType) => {
    setPendingAction({ item, target });
    setDraftTitle("");
  };

  const submitFollowUp = async () => {
    if (!pendingAction || !draftTitle.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createFollowUpEntity(projectId, pendingAction.target, draftTitle.trim());
      await api.createEntityRelation({
        source_entity_type: pendingAction.item.entity_type,
        source_entity_id: pendingAction.item.entity_id,
        target_entity_type: pendingAction.target,
        target_entity_id: (created as { id: number }).id,
        relation_type: "resulted_in",
      });
      setPendingAction(null);
      setDraftTitle("");
      refresh();
      onChanged();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const markBlockerResolved = async (item: ActivityItem) => {
    await api.updateBlocker(item.entity_id, { status: "geloest" });
    refresh();
    onChanged();
  };

  return (
    <div>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}
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
              {pendingAction && pendingAction.item.entity_type === item.entity_type && pendingAction.item.entity_id === item.entity_id && (
                <div className="field-row" style={{ marginTop: "0.4rem" }}>
                  <input
                    autoFocus
                    value={draftTitle}
                    onChange={(e) => setDraftTitle(e.target.value)}
                    placeholder={`Titel für ${TYPE_META[pendingAction.target].label}`}
                    style={{ flex: 1 }}
                  />
                  <button type="button" className="btn secondary" disabled={saving || !draftTitle.trim()} onClick={submitFollowUp}>
                    Erstellen
                  </button>
                  <button type="button" className="btn secondary" onClick={() => setPendingAction(null)}>
                    Abbrechen
                  </button>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
