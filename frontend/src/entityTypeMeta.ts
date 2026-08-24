import type { EntityType } from "./types";

// Gemeinsame Icon-/Label-Zuordnung für EntityType, genutzt von ActivityFeed.tsx und
// TagDossierPanel.tsx (Phase 26.4/26.5) - eine Quelle statt zweier driftender Kopien.
export const ENTITY_TYPE_META: Record<EntityType, { icon: string; label: string }> = {
  comment: { icon: "💬", label: "Diskussion" },
  decision: { icon: "✓", label: "Entscheidung" },
  risk: { icon: "⚠", label: "Risiko" },
  meeting_minutes: { icon: "📅", label: "Meeting" },
  task: { icon: "☑", label: "Aufgabe" },
  blocker: { icon: "🔴", label: "Blocker" },
  plan_phase: { icon: "📌", label: "Phase" },
  milestone: { icon: "🚩", label: "Milestone" },
  document: { icon: "📄", label: "Dokument" },
  baseline_snapshot: { icon: "📸", label: "Snapshot" },
};

// P19.4 (Tag-Dossier-Drilldown): bildet ActivityItem.entity_type auf die Sub-Ansicht im
// Kommunikation-Tab ab - ursprünglich lokal in ProjectCommunicationTab.tsx (Phase 26.4),
// hierher verschoben, damit TagDossierPanel.tsx dieselbe Zuordnung für die Navigation aus
// dem Dossier heraus nutzen kann, ohne sie zu duplizieren.
export const ENTITY_TYPE_TO_COMMUNICATION_SECTION: Partial<Record<EntityType, string>> = {
  comment: "diskussionen",
  decision: "entscheidungen",
  risk: "risiken",
  meeting_minutes: "meetingprotokolle",
  task: "aufgaben",
  blocker: "blocker",
};
