import { useState } from "react";
import { api } from "../api/client";
import type { EntityType } from "../types";

// P19.3 (Activity/Comments/Follow-up Objects): "Aus Objekt erstellen" existierte bisher nur
// als lokale Logik in ActivityFeed.tsx - hierher extrahiert, damit NotesSection.tsx dieselbe
// Erstellung + EntityRelation(resulted_in)-Verknüpfung nutzen kann, ohne sie zu duplizieren
// (siehe CONCEPT.md Abschnitt 8 "Aus Objekt erstellen", P19_PLANPHASE_WORKSPACE_UX_AUDIT.md
// Abschnitt 22). Kein neuer Endpoint, keine neue Relation-Art - weiterhin zwei sequentielle
// Calls (Create + POST /entity-relations mit relation_type "resulted_in").

// Kontextuelle "aus diesem Objekt erstellen"-Aktionen je Quelltyp. Comment ist die primäre
// Quelle (Kommentarliste UND Activity-Feed), Decision/Blocker bleiben zusätzlich als Quelle
// im Activity-Feed nutzbar (unverändert gegenüber der bisherigen ActivityFeed-Logik).
export const FOLLOW_UP_ACTIONS: Partial<Record<EntityType, { target: EntityType; label: string }[]>> = {
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

export interface FollowUpSource {
  entity_type: EntityType;
  entity_id: number;
}

// P16.3: "Aus Objekt erstellen" übernimmt plan_phase_id vom Ursprung, falls die Aktion im
// Phasenkontext ausgelöst wird und der Zieltyp die Spalte hat (Risk hat bewusst keine
// plan_phase_id, siehe CONCEPT.md Abschnitt 4/8 - kein Fehler, kein Fallback).
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

// Ein Hook je Container (ActivityFeed/NotesSection) - jeder verwaltet seinen eigenen
// "gerade in Bearbeitung"-Zustand (pendingAction/draftTitle/draftTags), aber die
// Erstell-/Verknüpfungslogik selbst lebt nur einmal hier.
export function useFollowUpAction(projectId: number, planPhaseId: number | undefined, onCreated: () => void) {
  const [pending, setPending] = useState<{ source: FollowUpSource; target: EntityType } | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  // P12.4 (Tag-Vorschläge bei Folgeobjekten): vorausgewählte Tags sind nur ein Vorschlag - der
  // User kann sie abwählen oder weitere hinzufügen. Keine harte Vererbung.
  const [draftTags, setDraftTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = (source: FollowUpSource, target: EntityType, suggestedTags: string[]) => {
    setPending({ source, target });
    setDraftTitle("");
    setDraftTags(suggestedTags);
    setError(null);
  };

  const cancel = () => {
    setPending(null);
    setDraftTitle("");
    setDraftTags([]);
  };

  const submit = async () => {
    if (!pending || !draftTitle.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await createFollowUpEntity(projectId, pending.target, draftTitle.trim(), draftTags, planPhaseId);
      await api.createEntityRelation({
        source_entity_type: pending.source.entity_type,
        source_entity_id: pending.source.entity_id,
        target_entity_type: pending.target,
        target_entity_id: (created as { id: number }).id,
        relation_type: "resulted_in",
      });
      cancel();
      onCreated();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return { pending, draftTitle, setDraftTitle, draftTags, setDraftTags, saving, error, start, cancel, submit };
}
