import type { PlanHistoryEntry } from "./types";

export const EVENT_FIELD = "_entity";

export type HistoryFilter = "all" | "planung" | "kapazitaet" | "team" | "zusammenarbeit";

export const HISTORY_FILTERS: { id: HistoryFilter; label: string }[] = [
  { id: "all", label: "Alle" },
  { id: "planung", label: "Planung" },
  { id: "kapazitaet", label: "Kapazität" },
  { id: "team", label: "Team" },
  { id: "zusammenarbeit", label: "Zusammenarbeit" },
];

export const FIELD_LABELS: Record<string, string> = {
  name: "Name",
  kunde: "Kunde",
  start_monat: "Startmonat",
  anzahl_monate: "Anzahl Monate",
  status: "Status",
  projektleiter_person_id: "Projektleiter",
  jira_component: "Jira-Komponente",
  phase_type: "Name",
  forecast_start: "Start",
  forecast_end: "Ende",
  plan_fte: "Plan-FTE",
  parent_phase_id: "Übergeordnete Phase",
  owner_person_id: "Owner",
  owner_team_id: "Team",
  reihenfolge: "Reihenfolge",
  jira_label: "Jira-Label",
  fte: "FTE",
  person_id: "Person",
  forecast_date: "Datum",
  plan_phase_id: "Phase",
  titel: "Titel",
  beschreibung: "Beschreibung",
  begruendung: "Begründung",
  zustaendig_person_id: "Zuständig",
  faellig_am: "Fällig am",
  title: "Titel",
  description: "Beschreibung",
  severity: "Schwere",
  entschieden_von_person_id: "Entschieden von",
  tags: "Tags",
  jira_issue_key: "Jira-Issue",
  document_id: "Dokument",
  entity_type: "Verknüpft mit",
};

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

export function formatHistoryDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const today = new Date();
  if (d.toDateString() === today.toDateString()) return "Heute";
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return "Gestern";
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function looksLikeIsoDate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}/.test(value);
}

export function formatHistoryValue(feld: string, raw: string | null): string {
  if (raw == null || raw === "") return "—";
  if (feld === "plan_fte" || feld === "fte") {
    const n = Number(raw);
    if (!Number.isNaN(n)) return `${n.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} FTE`;
  }
  if (looksLikeIsoDate(raw)) {
    const d = new Date(raw.length === 10 ? `${raw}T00:00:00` : raw);
    if (!Number.isNaN(d.getTime())) {
      return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
    }
  }
  return raw;
}

function quotedLabel(entry: PlanHistoryEntry): string {
  const label = entry.entity_label || entry.neuer_wert || entry.alter_wert;
  return label ? `„${label}“` : "";
}

function entityKind(entry: PlanHistoryEntry): string {
  const type = entry.entity_type || entry.bereich;
  switch (type) {
    case "plan_phase":
    case "phase_struktur":
    case "phase_subtree_delete":
    case "phase":
      return "Phase";
    case "resource_assignment":
    case "assignment":
      return "Personenbesetzung";
    case "milestone":
      return "Milestone";
    case "project":
    case "stammdaten":
      return "Projekt";
    case "task":
      return "Aufgabe";
    case "blocker":
      return "Blocker";
    case "decision":
      return "Entscheidung";
    case "document_link":
      return "Dokumentverknüpfung";
    case "worklog_override":
    case "jira_mapping":
      return "Jira-Zuordnung";
    case "tag_link":
      return "Tags";
    default:
      return "Eintrag";
  }
}

function actionVerb(entry: PlanHistoryEntry, kind: string): string {
  const action = entry.action;
  const label = quotedLabel(entry);
  if (action === "created") {
    if (kind === "Personenbesetzung") {
      return label ? `${label.replace(/[„"]/g, "").trim() || "Mitarbeiter"} zugewiesen` : "Mitarbeiter zugewiesen";
    }
    return label ? `${kind} ${label} erstellt` : `${kind} erstellt`;
  }
  if (action === "deleted") {
    return label ? `${kind} ${label} gelöscht` : `${kind} gelöscht`;
  }
  if (kind === "Personenbesetzung") return "Personenbesetzung geändert";
  if (kind === "Milestone" && entry.feld === "forecast_date") {
    return label ? `Milestone ${label} verschoben` : "Milestone verschoben";
  }
  if (kind === "Blocker" && (entry.feld === "status" || entry.neuer_wert === "geloest")) {
    if (entry.neuer_wert === "geloest") return label ? `Blocker ${label} gelöst` : "Blocker gelöst";
  }
  if (kind === "Aufgabe" && entry.neuer_wert === "erledigt") {
    return label ? `Aufgabe ${label} abgeschlossen` : "Aufgabe abgeschlossen";
  }
  return label ? `${kind} ${label} geändert` : `${kind} geändert`;
}

export function revisionTitle(entries: PlanHistoryEntry[]): string {
  if (entries.length === 0) return "Änderung";
  const representative =
    entries.find((e) => e.feld === EVENT_FIELD) ??
    entries.find((e) => e.action) ??
    entries[0];
  const kind = entityKind(representative);
  if (representative.action || representative.entity_type) {
    return actionVerb(representative, kind);
  }
  // Legacy-Zeilen ohne action/entity_type.
  if (representative.bereich === "phase") {
    const gesetzt = representative.neuer_wert === "aktiv";
    return `Phase „${representative.feld}"${representative.monat ? ` (${representative.monat})` : ""} ${gesetzt ? "gesetzt" : "entfernt"}`;
  }
  if (representative.bereich === "stammdaten") {
    return `${FIELD_LABELS[representative.feld] ?? representative.feld} geändert`;
  }
  if (representative.bereich === "fte") {
    return `FTE${representative.monat ? ` (${representative.monat})` : ""} geändert`;
  }
  if (representative.bereich === "phase_struktur") {
    return `Phase ${quotedLabel(representative) || ""} geändert`.trim();
  }
  if (representative.bereich === "phase_subtree_delete") {
    return `Phase ${quotedLabel(representative) || representative.alter_wert || ""} gelöscht`.trim();
  }
  return `${kind} geändert`;
}

export function detailRows(entries: PlanHistoryEntry[]): PlanHistoryEntry[] {
  const details = entries.filter((e) => e.feld !== EVENT_FIELD && e.feld !== "person_id");
  return details.length > 0 ? details : entries.filter((e) => e.feld === EVENT_FIELD && (e.alter_wert || e.neuer_wert));
}

export function describeEntry(entry: PlanHistoryEntry): string {
  const title = revisionTitle([entry]);
  if (entry.feld === EVENT_FIELD) return title;
  const label = FIELD_LABELS[entry.feld] ?? entry.feld;
  return `${title}: ${label} ${formatHistoryValue(entry.feld, entry.alter_wert)} → ${formatHistoryValue(entry.feld, entry.neuer_wert)}`;
}

export function rowFilters(entry: PlanHistoryEntry): HistoryFilter[] {
  const type = entry.entity_type || entry.bereich;
  if (type === "assignment" || type === "resource_assignment") return ["team"];
  if (type === "task" || type === "blocker" || type === "decision" || type === "document_link") {
    return ["zusammenarbeit"];
  }
  if (type === "tag_link") {
    if (entry.entity_type === "task" || entry.entity_type === "blocker" || entry.entity_type === "decision") {
      return ["zusammenarbeit"];
    }
    return ["planung"];
  }
  if (entry.feld === "plan_fte" || entry.feld === "fte" || type === "fte") return ["kapazitaet"];
  return ["planung"];
}

export interface HistoryRevision {
  key: string;
  entries: PlanHistoryEntry[];
  timestamp: string;
}

export interface HistoryDateGroup {
  dateLabel: string;
  revisions: HistoryRevision[];
}

export function groupHistory(entries: PlanHistoryEntry[]): HistoryDateGroup[] {
  const groups: HistoryDateGroup[] = [];
  const dateIndex = new Map<string, HistoryDateGroup>();
  const revisionIndex = new Map<string, HistoryRevision>();

  for (const entry of entries) {
    const dLabel = formatHistoryDate(entry.geaendert_am);
    let dateGroup = dateIndex.get(dLabel);
    if (!dateGroup) {
      dateGroup = { dateLabel: dLabel, revisions: [] };
      dateIndex.set(dLabel, dateGroup);
      groups.push(dateGroup);
    }
    const revisionKey = entry.batch_id ? `${dLabel}:${entry.batch_id}` : `${dLabel}:single:${entry.id}`;
    let revision = revisionIndex.get(revisionKey);
    if (!revision) {
      revision = { key: revisionKey, entries: [], timestamp: entry.geaendert_am };
      revisionIndex.set(revisionKey, revision);
      dateGroup.revisions.push(revision);
    }
    revision.entries.push(entry);
  }
  return groups;
}

export function revisionMatchesFilter(entries: PlanHistoryEntry[], filter: HistoryFilter): boolean {
  if (filter === "all") return true;
  return entries.some((e) => rowFilters(e).includes(filter));
}

export function revisionMatchesRange(entries: PlanHistoryEntry[], from: string, to: string): boolean {
  if (!from && !to) return true;
  const ts = entries[0]?.geaendert_am;
  if (!ts) return false;
  const day = ts.slice(0, 10);
  if (from && day < from) return false;
  if (to && day > to) return false;
  return true;
}
