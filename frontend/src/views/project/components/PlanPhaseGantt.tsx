import { useState } from "react";
import { PLAN_PHASE_STATUS_LABELS, type PlanPhase, type PlanPhaseStatus } from "../../../types";

// P18/B-6 (CONCEPT.md Abschnitt 6b): Tree-Gantt statt Teilprojekt-Gruppierung - Phasen werden
// rekursiv nach parent_phase_id eingerückt (max. 3 Ebenen). Eine Parent-Phase zeigt einen
// Summary-Balken aus derived_forecast_start/derived_forecast_end (abgeleitet aus den
// Leaf-Nachfahren, Abschnitt 6b.3) statt eines eigenen editierbaren Zeitraums. Kein
// Drag&Drop, keine Speicherung - Klick auf eine Zeile öffnet den PlanPhaseWorkspace-Drawer.
const STATUS_DOT_COLOR: Record<PlanPhaseStatus, string> = {
  geplant: "var(--grau)",
  laufend: "var(--blau)",
  abgeschlossen: "var(--gruen)",
  entfaellt: "var(--text-muted)",
  verzoegert: "var(--rot)",
};

const STATUS_ORDER: PlanPhaseStatus[] = ["geplant", "laufend", "abgeschlossen", "entfaellt"];

const LABEL_WIDTH = 180;
const MONTH_MIN_PX = 60;
const INDENT_PX = 16;

interface MonthSpan {
  startTs: number;
  midTs: number;
  endTs: number;
  label: string;
}

interface Range {
  min: number;
  max: number;
  months: MonthSpan[];
}

// Local midnight vermeidet den UTC-Off-by-one (ISO-Datum sonst einen Tag zurück).
function toTs(iso: string): number {
  return new Date(iso + "T00:00:00").getTime();
}

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function posPct(ts: number, min: number, max: number): number {
  if (max === min) return 0;
  const pct = ((ts - min) / (max - min)) * 100;
  return Math.max(0, Math.min(100, pct));
}

function effectiveStart(p: PlanPhase): string | null {
  return p.has_children ? p.derived_forecast_start : p.forecast_start;
}
function effectiveEnd(p: PlanPhase): string | null {
  return p.has_children ? p.derived_forecast_end : p.forecast_end;
}
function hasBar(p: PlanPhase): boolean {
  return Boolean(effectiveStart(p) && effectiveEnd(p));
}

// Zeitachse aus allen vorhandenen Phasenterminen: min/max auf Monatsanfang/-ende erweitern,
// dann Monats-Spannen generieren. Liefert null, wenn keine Termine.
function computeRange(phases: PlanPhase[]): Range | null {
  const ts: number[] = [];
  for (const p of phases) {
    const start = effectiveStart(p);
    const end = effectiveEnd(p);
    if (start) ts.push(toTs(start));
    if (end) ts.push(toTs(end));
  }
  if (ts.length === 0) return null;
  const minDate = new Date(Math.min(...ts));
  const maxDate = new Date(Math.max(...ts));
  // Auf ersten Tag des Startmonats bzw. ersten Tag des Folgemonats runden.
  const start = new Date(minDate.getFullYear(), minDate.getMonth(), 1);
  const end = new Date(maxDate.getFullYear(), maxDate.getMonth() + 1, 1);
  const min = start.getTime();
  const max = end.getTime();
  const months: MonthSpan[] = [];
  const cur = new Date(start);
  while (cur.getTime() < max) {
    const startTs = cur.getTime();
    const next = new Date(cur.getFullYear(), cur.getMonth() + 1, 1);
    const endTs = next.getTime();
    months.push({
      startTs,
      midTs: (startTs + endTs) / 2,
      endTs,
      label: cur.toLocaleDateString("de-DE", { month: "short", year: "2-digit" }),
    });
    cur.setMonth(cur.getMonth() + 1);
  }
  return { min, max, months };
}

export default function PlanPhaseGantt({
  phases,
  onOpen,
}: {
  phases: PlanPhase[];
  onOpen?: (planPhaseId: number) => void;
}) {
  const [collapsedGroups, setCollapsedGroups] = useState<Set<number>>(new Set());

  if (phases.length === 0) {
    return <p className="gantt-empty">Noch keine Phasen geplant.</p>;
  }

  const range = computeRange(phases);
  if (!range) {
    return <p className="gantt-empty">Keine Termine vorhanden.</p>;
  }

  const childrenOf = new Map<number | null, PlanPhase[]>();
  for (const phase of phases) {
    const list = childrenOf.get(phase.parent_phase_id) ?? [];
    list.push(phase);
    childrenOf.set(phase.parent_phase_id, list);
  }
  for (const list of childrenOf.values()) list.sort((a, b) => a.reihenfolge - b.reihenfolge || a.id - b.id);
  const topLevel = childrenOf.get(null) ?? [];

  const noDatesPhases = phases.filter((p) => !hasBar(p));

  const { min, max, months } = range;
  // Damit bei vielen Monaten horizontal gescrollt werden kann, wird das innere
  // Grid mindestens so breit wie Labelspalte + Monate * Mindestbreite.
  const innerMinWidth = `max(100%, ${LABEL_WIDTH + months.length * MONTH_MIN_PX}px)`;

  const renderRow = (phase: PlanPhase, depth: number) => {
    const start = effectiveStart(phase);
    const end = effectiveEnd(phase);
    const children = (childrenOf.get(phase.id) ?? []).filter(hasBar);
    const collapsed = collapsedGroups.has(phase.id);
    if (!start || !end) return null;
    const left = posPct(toTs(start), min, max);
    const right = posPct(toTs(end), min, max);
    return (
      <div key={phase.id}>
        <div className="gantt-row" style={{ cursor: onOpen ? "pointer" : undefined }} onClick={() => onOpen?.(phase.id)}>
          <div className="gantt-row-label" style={{ paddingLeft: depth * INDENT_PX }}>
            {phase.has_children && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setCollapsedGroups((prev) => {
                    const next = new Set(prev);
                    if (next.has(phase.id)) next.delete(phase.id);
                    else next.add(phase.id);
                    return next;
                  });
                }}
                style={{ border: "none", background: "none", cursor: "pointer", padding: 0, color: "var(--text-muted)" }}
              >
                {collapsed ? "▸" : "▾"}
              </button>
            )}
            <span className="gantt-status-dot" style={{ background: STATUS_DOT_COLOR[phase.status] }} />
            <span>{phase.phase_type}</span>
          </div>
          <div className="gantt-bars">
            <div className="gantt-bar-track">
              <div
                className="gantt-bar gantt-bar--forecast"
                style={
                  phase.has_children
                    ? { left: `${left}%`, width: `${Math.max(0, right - left)}%`, background: "transparent", border: "2px solid var(--blau)" }
                    : { left: `${left}%`, width: `${Math.max(0, right - left)}%` }
                }
                title={`${phase.phase_type}: ${fmtDate(start)} – ${fmtDate(end)}${phase.has_children ? " (abgeleitet aus Unterphasen)" : ""}`}
              />
            </div>
          </div>
        </div>
        {!collapsed && children.map((child) => renderRow(child, depth + 1))}
      </div>
    );
  };

  return (
    <div className="gantt">
      <div className="legend-row">
        {STATUS_ORDER.map((s) => (
          <span key={s} className="legend-chip">
            <span className="gantt-status-dot" style={{ background: STATUS_DOT_COLOR[s] }} />
            {PLAN_PHASE_STATUS_LABELS[s]}
          </span>
        ))}
      </div>

      <div className="gantt-scroll">
        <div className="gantt-inner" style={{ minWidth: innerMinWidth }}>
          <div className="gantt-axis">
            <div className="gantt-axis-corner" />
            <div className="gantt-axis-months">
              {months.map((m) => (
                <span key={`grid-${m.startTs}`} className="gantt-axis-gridline" style={{ left: `${posPct(m.startTs, min, max)}%` }} />
              ))}
              {months.map((m) => (
                <span key={`label-${m.startTs}`} className="gantt-axis-month" style={{ left: `${posPct(m.midTs, min, max)}%` }}>
                  {m.label}
                </span>
              ))}
            </div>
          </div>

          {topLevel.filter(hasBar).map((phase) => renderRow(phase, 0))}
        </div>
      </div>

      {noDatesPhases.length > 0 && (
        <div className="gantt-no-dates">
          <div className="gantt-no-dates-title">Ohne Termin</div>
          {noDatesPhases.map((phase) => (
            <div
              key={phase.id}
              className="gantt-no-dates-row"
              style={{ cursor: onOpen ? "pointer" : undefined }}
              onClick={() => onOpen?.(phase.id)}
            >
              <span className="gantt-status-dot" style={{ background: STATUS_DOT_COLOR[phase.status] }} />
              <span>{phase.phase_type}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
