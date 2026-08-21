import {
  PLAN_PHASE_STATUS_LABELS,
  type PlanPhase,
  type PlanPhaseStatus,
  type SubprojectDetail,
} from "../../../types";

// P8: Read-Only-Gantt für PlanPhase-Zeitleisten. Kein Drag&Drop, keine neuen
// Abhängigkeiten. Die Komponente empfängt die Phasen vom Parent (PlanPhaseList)
// und fragt selbst keine Daten ab. Balkenfarben und Status-Punkte orientieren sich
// an den bestehenden Gap-/Status-Variablen aus theme.css.
const STATUS_DOT_COLOR: Record<PlanPhaseStatus, string> = {
  geplant: "var(--grau)",
  laufend: "var(--blau)",
  abgeschlossen: "var(--gruen)",
  verzoegert: "var(--rot)",
};

type BarKind = "baseline" | "forecast" | "actual";

const BAR_COLOR: Record<BarKind, string> = {
  baseline: "var(--gap-soll)",
  forecast: "var(--gap-hochrechnung)",
  actual: "var(--gap-ist)",
};

const BAR_LABEL: Record<BarKind, string> = {
  baseline: "Baseline",
  forecast: "Forecast",
  actual: "Ist",
};

const BAR_KINDS: BarKind[] = ["baseline", "forecast", "actual"];

const STATUS_ORDER: PlanPhaseStatus[] = ["geplant", "laufend", "abgeschlossen", "verzoegert"];

const LABEL_WIDTH = 180;
const MONTH_MIN_PX = 60;

interface BarSpec {
  kind: BarKind;
  startIso: string;
  endIso: string;
}

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

// Ein Balken ist nur zeichenbar, wenn Start UND Ende vorhanden sind.
function barsForPhase(p: PlanPhase): BarSpec[] {
  const bars: BarSpec[] = [];
  if (p.baseline_start && p.baseline_end) {
    bars.push({ kind: "baseline", startIso: p.baseline_start, endIso: p.baseline_end });
  }
  if (p.forecast_start && p.forecast_end) {
    bars.push({ kind: "forecast", startIso: p.forecast_start, endIso: p.forecast_end });
  }
  if (p.actual_start && p.actual_end) {
    bars.push({ kind: "actual", startIso: p.actual_start, endIso: p.actual_end });
  }
  return bars;
}

// Zeitachse aus allen vorhandenen Terminen: min/max auf Monatsanfang/-ende
// erweitern, dann Monats-Spannen generieren. Liefert null, wenn keine Termine.
function computeRange(phases: PlanPhase[]): Range | null {
  const ts: number[] = [];
  for (const p of phases) {
    for (const iso of [
      p.baseline_start,
      p.baseline_end,
      p.forecast_start,
      p.forecast_end,
      p.actual_start,
      p.actual_end,
    ]) {
      if (iso) ts.push(toTs(iso));
    }
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
}: {
  phases: PlanPhase[];
  subprojects: SubprojectDetail[];
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

  // Phasen ohne zeichenbare Balken landen global unten im "Ohne Termin"-Block.
  const noDatesPhases = phases.filter((p) => barsForPhase(p).length === 0);

  const { min, max, months } = range;
  // Damit bei vielen Monaten horizontal gescrollt werden kann, wird das innere
  // Grid mindestens so breit wie Labelspalte + Monate * Mindestbreite.
  const innerMinWidth = `max(100%, ${LABEL_WIDTH + months.length * MONTH_MIN_PX}px)`;

  return (
    <div className="gantt">
      <div className="legend-row">
        {BAR_KINDS.map((kind) => (
          <span key={kind} className="legend-chip">
            <span className="legend-swatch" style={{ background: BAR_COLOR[kind] }} />
            {BAR_LABEL[kind]}
          </span>
        ))}
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
            const drawable = groups
              .get(groupId)!
              .filter((p) => barsForPhase(p).length > 0);
            if (drawable.length === 0) return null;
            return (
              <div key={groupId ?? "project"}>
                <div className="gantt-group-header">
                  <div className="gantt-row-label">{subprojectName(groupId)}</div>
                  <div className="gantt-group-spacer" />
                </div>
                {drawable.map((phase) => {
                  const bars = barsForPhase(phase);
                  return (
                    <div key={phase.id} className="gantt-row">
                      <div className="gantt-row-label">
                        <span
                          className="gantt-status-dot"
                          style={{ background: STATUS_DOT_COLOR[phase.status] }}
                        />
                        <span>{phase.phase_type}</span>
                      </div>
                      <div className="gantt-bars">
                        {bars.map((bar) => {
                          const left = posPct(toTs(bar.startIso), min, max);
                          const right = posPct(toTs(bar.endIso), min, max);
                          return (
                            <div key={bar.kind} className="gantt-bar-track">
                              <div
                                className={`gantt-bar gantt-bar--${bar.kind}`}
                                style={{
                                  left: `${left}%`,
                                  width: `${Math.max(0, right - left)}%`,
                                }}
                                title={`${BAR_LABEL[bar.kind]}: ${fmtDate(bar.startIso)} – ${fmtDate(bar.endIso)}`}
                              />
                            </div>
                          );
                        })}
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
            <div key={phase.id} className="gantt-no-dates-row">
              <span
                className="gantt-status-dot"
                style={{ background: STATUS_DOT_COLOR[phase.status] }}
              />
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
