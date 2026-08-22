import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import ConfirmDialog from "../../../components/ConfirmDialog";
import PersonPicker from "../../../components/PersonPicker";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import type { BaselineDeviation, BaselineSnapshotSummary } from "../../../types";

// P13 (Planstand Experience Completion): fachlicher Begriff ist "Planstand", nicht "Baseline" -
// das Wort "Baseline" verschwindet aus dem normalen UI (CONCEPT.md Abschnitt 5.3/13.1). Der
// technische Modell-/Endpointname (BaselineSnapshot, /baselines) bleibt unverändert, nur die
// UI-Beschriftung ändert sich. Reine Wiederverwendung bestehender Endpoints
// (POST/GET/DELETE .../baselines, GET .../baselines/{id}/deviations) - kein neuer Endpoint.

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

// Nur die Felder, die im normalen Planstand-Vergleich fachlich sichtbar sein sollen. baseline_*
// -Felder (baseline_start/baseline_end/baseline_date) sind compat-only (siehe CONCEPT.md
// Abschnitt 3) und werden hier bewusst nicht angezeigt, obwohl compute_deviations sie technisch
// mitliefert - sonst würde der Begriff "Baseline" durch die Hintertür zurückkommen.
const FIELD_LABELS: Record<string, string> = {
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
function entityDisplayName(label: string | null, fallback: string): string {
  if (!label) return fallback;
  const match = label.match(/„(.+)“/);
  return match ? match[1] : label;
}

function valuesEqual(a: string | null, b: string | null): boolean {
  if (a === b) return true;
  if (a == null || b == null) return false;
  const na = Number(a);
  const nb = Number(b);
  if (!Number.isNaN(na) && !Number.isNaN(nb)) return na === nb;
  return false;
}

function formatDeviation(dev: BaselineDeviation, phaseNameById: Map<number, string>): string {
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
  const from = dev.baseline_value ? formatDate(dev.baseline_value) : "—";
  const to = dev.current_value ? formatDate(dev.current_value) : "—";
  const deltaText = dev.delta_days == null ? "" : ` (${dev.delta_days > 0 ? "+" : ""}${dev.delta_days} Tage)`;
  return `${from} → ${to}${deltaText}`;
}

function ComparisonPanel({ baselineId, projectId }: { baselineId: number; projectId: number }) {
  const [deviations, setDeviations] = useState<BaselineDeviation[] | null>(null);
  const [phaseNameById, setPhaseNameById] = useState<Map<number, string>>(new Map());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getBaselineDeviations(baselineId).then(setDeviations).catch((e) => setError(String(e)));
    // Für die "Übergeordnete Phase"-Deviation (parent_phase_id/plan_phase_id) reichen rohe
    // IDs nicht - Phasennamen aus dem AKTUELLEN Baum auflösen (eine gelöschte Phase zeigt
    // dann "Phase #<id>", da entity_id bewusst kein FK ist, siehe models.BaselineEntry).
    api
      .listPlanPhases(projectId)
      .then((phases) => setPhaseNameById(new Map(phases.map((p) => [p.id, p.phase_type]))))
      .catch(() => setPhaseNameById(new Map()));
  }, [baselineId, projectId]);

  if (error) return <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>;
  if (!deviations) return <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Lade Vergleich …</p>;

  const relevant = deviations.filter((d) => FIELD_LABELS[d.field] && !valuesEqual(d.baseline_value, d.current_value));

  if (relevant.length === 0) {
    return <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Keine Abweichungen zum aktuellen Plan.</p>;
  }

  const groups = new Map<string, { name: string; devs: BaselineDeviation[] }>();
  for (const dev of relevant) {
    const key = `${dev.entity_type}-${dev.entity_id}`;
    const group = groups.get(key) ?? { name: entityDisplayName(dev.label, `#${dev.entity_id}`), devs: [] };
    group.devs.push(dev);
    groups.set(key, group);
  }

  return (
    <div style={{ marginTop: "0.5rem", display: "grid", gap: "0.6rem" }}>
      {Array.from(groups.values()).map((group) => (
        <div key={group.name} style={{ fontSize: "0.85rem" }}>
          <strong>{group.name}</strong>
          <div style={{ display: "grid", gap: "0.15rem", marginTop: "0.2rem" }}>
            {group.devs.map((dev) => (
              <div key={dev.field} style={{ display: "flex", gap: "0.5rem", color: "var(--text-muted)" }}>
                <span style={{ minWidth: "5rem" }}>{FIELD_LABELS[dev.field]}</span>
                <span>{formatDeviation(dev, phaseNameById)}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function BaselineList({ projectId }: { projectId: number }) {
  const [baselines, setBaselines] = useState<BaselineSnapshotSummary[]>([]);
  const [name, setName] = useState("");
  const [reason, setReason] = useState("");
  const [createdByPersonId, setCreatedByPersonId] = useState<number | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [toDelete, setToDelete] = useState<BaselineSnapshotSummary | null>(null);
  const [comparingId, setComparingId] = useState<number | null>(null);

  const refresh = () => {
    api.listBaselines(projectId).then(setBaselines).catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId]);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.createBaseline(projectId, {
        name: name.trim(),
        reason: reason.trim() || null,
        created_by_person_id: createdByPersonId,
        tags,
      });
      setName("");
      setReason("");
      setCreatedByPersonId(null);
      setTags([]);
      setShowCreate(false);
      refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    await api.deleteBaseline(toDelete.id);
    setToDelete(null);
    refresh();
  };

  // Versionsnummerierung: Liste kommt neueste zuerst (created_at desc) - V1 ist der älteste
  // festgehaltene Planstand, Vn der neueste.
  const total = baselines.length;

  return (
    <div>
      <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
        <h3 style={{ color: "var(--navy)", margin: 0 }}>Planstände</h3>
        <button type="button" className="btn" onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "Abbrechen" : "+ Planstand festhalten"}
        </button>
      </div>
      <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: 0 }}>
        <strong>Aktueller Plan</strong> ist der live bearbeitbare Plan in der Phasen-/Milestone-Liste oben. Ein
        Planstand ist ein benannter, eingefrorener historischer Stand davon, gegen den später verglichen werden
        kann.
      </p>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {showCreate && (
        <div className="card" style={{ marginBottom: "0.75rem", background: "#f8fafc" }}>
          <div className="field-row" style={{ marginTop: 0, flexDirection: "column", alignItems: "stretch" }}>
            <label>
              Name
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="z. B. V4 – Replanung nach Kundenworkshop" />
            </label>
            <label>
              Grund
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="optional, z. B. Kunde verschiebt Schnittstellenfreigabe"
              />
            </label>
            <div className="field-row" style={{ marginTop: 0 }}>
              <label>
                Erstellt von
                <PersonPicker value={createdByPersonId} onChange={setCreatedByPersonId} />
              </label>
            </div>
            <label>
              Tags
              <TagInput value={tags} onChange={setTags} />
            </label>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0.2rem 0 0" }}>
              Enthält: ✓ Planphasen · ✓ Plan-Aufwand · ✓ Meilensteine
            </p>
            <button
              type="button"
              className="btn"
              style={{ alignSelf: "flex-start", marginTop: "0.4rem" }}
              disabled={saving || !name.trim()}
              onClick={handleSave}
            >
              Planstand festhalten
            </button>
          </div>
        </div>
      )}

      {baselines.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch kein Planstand festgehalten.</p>
      ) : (
        baselines.map((b, idx) => (
          <div key={b.id} className="card" style={{ marginBottom: "0.5rem", padding: "0.6rem 0.85rem", fontSize: "0.88rem" }}>
            <div className="toolbar">
              <span>
                <strong>V{total - idx}</strong> {b.name} · {formatDate(b.created_at)}
              </span>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <button
                  type="button"
                  className="btn secondary"
                  style={{ fontSize: "0.75rem", padding: "0.1rem 0.5rem" }}
                  onClick={() => setComparingId(comparingId === b.id ? null : b.id)}
                >
                  {comparingId === b.id ? "Vergleich schließen" : "Mit aktuellem Plan vergleichen"}
                </button>
                <button
                  type="button"
                  onClick={() => setToDelete(b)}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            </div>
            {b.reason && <p style={{ fontSize: "0.82rem", margin: "0.3rem 0 0" }}>{b.reason}</p>}
            {b.tags.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem", margin: "0.3rem 0 0" }}>
                {b.tags.map((t) => (
                  <TagChip key={t} name={t} />
                ))}
              </div>
            )}
            {comparingId === b.id && <ComparisonPanel baselineId={b.id} projectId={projectId} />}
          </div>
        ))
      )}

      <ConfirmDialog
        open={toDelete !== null}
        title="Planstand löschen"
        message={`Planstand "${toDelete?.name}" wirklich löschen?`}
        onConfirm={handleDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  );
}
