import { useEffect, useMemo, useState } from "react";
import { api } from "../../../api/client";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
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

// P16.3 (Collaboration & Knowledge Experience): "Aus Objekt erstellen" übernimmt plan_phase_id
// vom Ursprung, falls das Feed im Phasenkontext läuft und der Zieltyp die Spalte hat (Risk hat
// bewusst keine plan_phase_id, siehe CONCEPT.md Abschnitt 4/8 - kein Fehler, kein Fallback).
async function createFollowUpEntity(
  projectId: number,
  target: EntityType,
  titel: string,
  tags: string[],
  planPhaseId: number | undefined,
) {
  switch (target) {
    case "decision":
      return api.createDecision(projectId, { titel, tags, plan_phase_id: planPhaseId ?? null });
    case "task":
      return api.createTask(projectId, { titel, tags, plan_phase_id: planPhaseId ?? null });
    case "risk":
      return api.createRisk(projectId, { titel, tags });
    case "blocker":
      return api.createBlocker(projectId, { title: titel, tags, plan_phase_id: planPhaseId ?? null });
    default:
      throw new Error(`Unbekannter Zieltyp: ${target}`);
  }
}

export default function ActivityFeed({
  projectId,
  filterTypes,
  onOpenSection,
  onChanged,
  planPhaseId,
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
}) {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [typeFilter, setTypeFilter] = useState<EntityType | null>(null);
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<{ item: ActivityItem; target: EntityType } | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  // P12.4 (Tag-Vorschläge bei Folgeobjekten): Tags des Ursprungs werden vorausgewählt, aber nur
  // als Vorschlag - der User kann sie abwählen oder weitere hinzufügen. Keine harte Vererbung.
  const [draftTags, setDraftTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const refresh = () => {
    const fetcher = planPhaseId
      ? api.getPlanPhaseActivity(planPhaseId)
      : api.getActivity(projectId);
    fetcher.then(setItems).catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId, planPhaseId, refreshToken]);

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

  const startFollowUp = (item: ActivityItem, target: EntityType) => {
    setPendingAction({ item, target });
    setDraftTitle("");
    setDraftTags([...item.tags]);
  };

  const submitFollowUp = async () => {
    if (!pendingAction || !draftTitle.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createFollowUpEntity(
        projectId,
        pendingAction.target,
        draftTitle.trim(),
        draftTags,
        planPhaseId,
      );
      await api.createEntityRelation({
        source_entity_type: pendingAction.item.entity_type,
        source_entity_id: pendingAction.item.entity_id,
        target_entity_type: pendingAction.target,
        target_entity_id: (created as { id: number }).id,
        relation_type: "resulted_in",
      });
      setPendingAction(null);
      setDraftTitle("");
      setDraftTags([]);
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
              {pendingAction && pendingAction.item.entity_type === item.entity_type && pendingAction.item.entity_id === item.entity_id && (
                <div style={{ marginTop: "0.4rem", padding: "0.5rem", background: "#f8fafc", borderRadius: "4px" }}>
                  <input
                    autoFocus
                    value={draftTitle}
                    onChange={(e) => setDraftTitle(e.target.value)}
                    placeholder={`Titel für ${TYPE_META[pendingAction.target].label}`}
                    style={{ width: "100%" }}
                  />
                  <div style={{ marginTop: "0.4rem" }}>
                    {item.tags.length > 0 && (
                      <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                        Tags aus {meta.label} vorgeschlagen — abwählbar, weitere ergänzbar:
                      </span>
                    )}
                    <TagInput value={draftTags} onChange={setDraftTags} />
                  </div>
                  <div className="field-row" style={{ marginTop: "0.5rem" }}>
                    <button type="button" className="btn secondary" disabled={saving || !draftTitle.trim()} onClick={submitFollowUp}>
                      Erstellen
                    </button>
                    <button type="button" className="btn secondary" onClick={() => setPendingAction(null)}>
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
