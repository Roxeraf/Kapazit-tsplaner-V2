import {
  PLAN_PHASE_STATUS_LABELS,
  type PlanPhase,
  type PlanPhaseStatus,
  type SubprojectDetail,
} from "../../../types";

// P11 (Planungs-/Kapazitätskonsolidierung): Read-Only-Gantt für PlanPhase-Zeitleisten. Zeigt
// pro Phase EINEN Balken (forecast_start/forecast_end = "aktueller Plan" in der normalen UX,
// siehe CONCEPT.md) statt der früheren drei technisch benannten Baseline-/Forecast-/Ist-
// Balken - Baseline ist ein Planstand-Konzept (siehe BaselineList/Planstand-Vergleich), kein
// paralleler Gantt-Layer, und Ist bleibt sekundär (siehe PlanPhaseWorkspace "Tatsächlicher
// Verlauf"). Kein Drag&Drop, keine Speicherung - Klick auf eine Zeile öffnet den
// PlanPhaseWorkspace-Drawer (onOpen), analog zur Listenansicht.
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

function hasBar(p: PlanPhase): boolean {
  return Boolean(p.forecast_start && p.forecast_end);
}

// Zeitachse aus allen vorhandenen Phasenterminen: min/max auf Monatsanfang/-ende erweitern,
// dann Monats-Spannen generieren. Liefert null, wenn keine Termine.
function computeRange(phases: PlanPhase[]): Range | null {
  const ts: number[] = [];
  for (const p of phases) {
    if (p.forecast_start) ts.push(toTs(p.forecast_start));
    if (p.forecast_end) ts.push(toTs(p.forecast_end));
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
  subprojects,
  onOpen,
}: {
  phases: PlanPhase[];
  subprojects: SubprojectDetail[];
  onOpen?: (planPhaseId: number) => void;
}) {
  if (phases.length === 0) {
    return <p className="gantt-empty">Noch keine Phasen geplant.</p>;
  }

  const range = computeRange(phases);
  if (!range) {
    return <p className="gantt-empty">Keine Termine vorhanden.</p>;
  }

  const subprojectName = (id: number | null) =>
    id === null
      ? "Projektweit"
      : subprojects.find((sp) => sp.id === id)?.name ?? "Unbekanntes Teilprojekt";

  // Gruppierung wie PlanPhaseList: null ("Projektweit") zuerst, dann Teilprojekte.
  const groups = new Map<number | null, PlanPhase[]>();
  for (const phase of phases) {
    const list = groups.get(phase.subproject_id) ?? [];
    list.push(phase);
    groups.set(phase.subproject_id, list);
  }
  const groupOrder = [null, ...subprojects.map((sp) => sp.id)].filter((id) => groups.has(id));

  // Phasen ohne Termin landen global unten im "Ohne Termin"-Block.
  const noDatesPhases = phases.filter((p) => !hasBar(p));

  const { min, max, months } = range;
  // Damit bei vielen Monaten horizontal gescrollt werden kann, wird das innere
  // Grid mindestens so breit wie Labelspalte + Monate * Mindestbreite.
  const innerMinWidth = `max(100%, ${LABEL_WIDTH + months.length * MONTH_MIN_PX}px)`;

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
                <span
                  key={`grid-${m.startTs}`}
                  className="gantt-axis-gridline"
                  style={{ left: `${posPct(m.startTs, min, max)}%` }}
                />
              ))}
              {months.map((m) => (
                <span
                  key={`label-${m.startTs}`}
                  className="gantt-axis-month"
                  style={{ left: `${posPct(m.midTs, min, max)}%` }}
                >
                  {m.label}
                </span>
              ))}
            </div>
          </div>

          {groupOrder.map((groupId) => {
            const drawable = groups.get(groupId)!.filter(hasBar);
            if (drawable.length === 0) return null;
            return (
              <div key={groupId ?? "project"}>
                <div className="gantt-group-header">
                  <div className="gantt-row-label">{subprojectName(groupId)}</div>
                  <div className="gantt-group-spacer" />
                </div>
                {drawable.map((phase) => {
                  const left = posPct(toTs(phase.forecast_start!), min, max);
                  const right = posPct(toTs(phase.forecast_end!), min, max);
                  return (
                    <div
                      key={phase.id}
                      className="gantt-row"
                      style={{ cursor: onOpen ? "pointer" : undefined }}
                      onClick={() => onOpen?.(phase.id)}
                    >
                      <div className="gantt-row-label">
                        <span className="gantt-status-dot" style={{ background: STATUS_DOT_COLOR[phase.status] }} />
                        <span>{phase.phase_type}</span>
                      </div>
                      <div className="gantt-bars">
                        <div className="gantt-bar-track">
                          <div
                            className="gantt-bar gantt-bar--forecast"
                            style={{ left: `${left}%`, width: `${Math.max(0, right - left)}%` }}
                            title={`${phase.phase_type}: ${fmtDate(phase.forecast_start!)} – ${fmtDate(phase.forecast_end!)}`}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
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
              {phase.subproject_id !== null && (
                <span style={{ color: "var(--text-muted)" }}>· {subprojectName(phase.subproject_id)}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
