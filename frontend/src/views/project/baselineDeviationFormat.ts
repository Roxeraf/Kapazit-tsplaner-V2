import type { BaselineDeviation } from "../../types";

// P13 (Planstand Experience Completion) / P19.6 (P19_PLANPHASE_WORKSPACE_UX_AUDIT.md Abschnitt
// 3.11/15): menschenlesbare Feld-Label und Delta-Formatierung für Planstand-Abweichungen -
// ursprünglich nur in BaselineList.tsx (Projektebene), jetzt extrahiert, damit die kompakte
// "Seit Planstand VX geändert"-Zeile im PlanPhaseWorkspace (Übersicht-Tab) exakt dieselbe
// Formulierung/Formatierung verwendet statt sie zu duplizieren.

// Exportiert, damit sowohl BaselineList.tsx (Erstellungsdatum eines Planstands) als auch die
// kompakte Planstand-Zeile im PlanPhaseWorkspace (Übersicht-Tab, P19.6) dasselbe Datumsformat
// verwenden.
export function formatBaselineDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

// Nur die Felder, die im normalen Planstand-Vergleich fachlich sichtbar sein sollen. baseline_*
// -Felder (baseline_start/baseline_end/baseline_date) sind compat-only (siehe CONCEPT.md
// Abschnitt 3) und werden hier bewusst nicht angezeigt, obwohl compute_deviations sie technisch
// mitliefert - sonst würde der Begriff "Baseline" durch die Hintertür zurückkommen.
export const BASELINE_FIELD_LABELS: Record<string, string> = {
  forecast_start: "Start",
  forecast_end: "Ende",
  forecast_date: "Datum",
  plan_fte: "Plan-Aufwand",
  // P18/B-7 (CONCEPT.md Abschnitt 6b.14): eine Änderung der übergeordneten Phase ist genauso
  // eine sichtbare Planstand-Abweichung wie eine Termin-/Aufwandsabweichung - reihenfolge
  // (reine Sortierposition) bleibt bewusst außen vor (siehe backend baseline_calc.py).
  parent_phase_id: "Übergeordnete Phase",
  plan_phase_id: "Übergeordnete Phase",
};

// Entity-Label vom Backend kommt als `Planphase „Konfiguration“` (entity_links._resolve_entity_label)
// - für die Vergleichsansicht reicht der reine Name, das technische Präfix ist Rauschen.
export function baselineEntityDisplayName(label: string | null, fallback: string): string {
  if (!label) return fallback;
  const match = label.match(/„(.+)“/);
  return match ? match[1] : label;
}

export function baselineValuesEqual(a: string | null, b: string | null): boolean {
  if (a === b) return true;
  if (a == null || b == null) return false;
  const na = Number(a);
  const nb = Number(b);
  if (!Number.isNaN(na) && !Number.isNaN(nb)) return na === nb;
  return false;
}

export function formatBaselineDeviation(dev: BaselineDeviation, phaseNameById: Map<number, string>): string {
  if (dev.field === "parent_phase_id" || dev.field === "plan_phase_id") {
    const nullLabel = dev.entity_type === "milestone" ? "Projektweit" : "Top-Level";
    const label = (raw: string | null) => {
      if (raw == null) return nullLabel;
      const id = Number(raw);
      return phaseNameById.get(id) ?? `Phase #${id}`;
    };
    return `${label(dev.baseline_value)} → ${label(dev.current_value)}`;
  }
  if (dev.field === "plan_fte") {
    const from = dev.baseline_value == null ? "—" : Number(dev.baseline_value).toFixed(2);
    const to = dev.current_value == null ? "—" : Number(dev.current_value).toFixed(2);
    const delta =
      dev.baseline_value != null && dev.current_value != null
        ? Number(dev.current_value) - Number(dev.baseline_value)
        : null;
    const deltaText = delta == null ? "" : ` (${delta > 0 ? "+" : ""}${delta.toFixed(2)} FTE)`;
    return `${from} → ${to} FTE${deltaText}`;
  }
  const from = dev.baseline_value ? formatBaselineDate(dev.baseline_value) : "—";
  const to = dev.current_value ? formatBaselineDate(dev.current_value) : "—";
  const deltaText = dev.delta_days == null ? "" : ` (${dev.delta_days > 0 ? "+" : ""}${dev.delta_days} Tage)`;
  return `${from} → ${to}${deltaText}`;
}

// P19.6: kompakte Ein-Zeilen-Zusammenfassung für den PlanPhaseWorkspace ("Ende +7 Tage, Bedarf
// +0,20 FTE") statt der vollen Gruppen-/Karten-Darstellung aus BaselineList.tsx - reine
// Kurzform derselben Werte (kein eigenes Berechnungsmodell).
export function summarizeBaselineDeviations(
  deviations: BaselineDeviation[],
  phaseNameById: Map<number, string>,
): string | null {
  const changes = deviations.filter(
    (d) => d.type === "changed" && BASELINE_FIELD_LABELS[d.field] && !baselineValuesEqual(d.baseline_value, d.current_value),
  );
  if (changes.length === 0) return null;
  return changes.map((d) => `${BASELINE_FIELD_LABELS[d.field]} ${formatBaselineDeviation(d, phaseNameById)}`).join(", ");
}
