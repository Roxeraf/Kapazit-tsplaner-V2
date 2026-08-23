import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import ConfirmDialog from "../../../components/ConfirmDialog";
import PersonPicker from "../../../components/PersonPicker";
import TagChip from "../../../components/TagChip";
import TagInput from "../../../components/TagInput";
import {
  BASELINE_FIELD_LABELS as FIELD_LABELS,
  baselineEntityDisplayName as entityDisplayName,
  baselineValuesEqual as valuesEqual,
  formatBaselineDate as formatDate,
  formatBaselineDeviation as formatDeviation,
} from "../baselineDeviationFormat";
import type { BaselineDeviation, BaselineSnapshotSummary } from "../../../types";

// P13 (Planstand Experience Completion): fachlicher Begriff ist "Planstand", nicht "Baseline" -
// das Wort "Baseline" verschwindet aus dem normalen UI (CONCEPT.md Abschnitt 5.3/13.1). Der
// technische Modell-/Endpointname (BaselineSnapshot, /baselines) bleibt unverändert, nur die
// UI-Beschriftung ändert sich. Reine Wiederverwendung bestehender Endpoints
// (POST/GET/DELETE .../baselines, GET .../baselines/{id}/deviations) - kein neuer Endpoint.
//
// P19.6 (P19_PLANPHASE_WORKSPACE_UX_AUDIT.md Abschnitt 3.11/15): FIELD_LABELS und die
// Delta-Rendering-Logik (formatDeviation/entityDisplayName/valuesEqual) sind jetzt in
// baselineDeviationFormat.ts extrahiert, damit die kompakte "Seit Planstand VX geändert"-Zeile
// im PlanPhaseWorkspace dieselbe Formatierung wiederverwendet statt sie zu duplizieren. Diese
// Datei importiert sie unter den ursprünglichen lokalen Namen zurück - keine Verhaltensänderung
// an dieser Stelle.

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

  // P18.1 Stabilization: strukturelle Phase hinzugefügt/entfernt-Zeilen sind kein Feld-Delta
  // (kein Eintrag in FIELD_LABELS) und werden separat, nicht in der Feld-Gruppe je Phase,
  // dargestellt - "Phase hinzugefügt" gehört zur Phase selbst, nicht zu einem ihrer Felder.
  const structural = deviations.filter((d) => d.type === "added" || d.type === "removed");
  const fieldChanges = deviations.filter(
    (d) => d.type === "changed" && FIELD_LABELS[d.field] && !valuesEqual(d.baseline_value, d.current_value)
  );

  if (structural.length === 0 && fieldChanges.length === 0) {
    return <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Keine Abweichungen zum aktuellen Plan.</p>;
  }

  const groups = new Map<string, { name: string; devs: BaselineDeviation[] }>();
  for (const dev of fieldChanges) {
    const key = `${dev.entity_type}-${dev.entity_id}`;
    const group = groups.get(key) ?? { name: entityDisplayName(dev.label, `#${dev.entity_id}`), devs: [] };
    group.devs.push(dev);
    groups.set(key, group);
  }

  return (
    <div style={{ marginTop: "0.5rem", display: "grid", gap: "0.6rem" }}>
      {structural.length > 0 && (
        <div style={{ display: "grid", gap: "0.2rem" }}>
          {structural.map((dev) => (
            <div
              key={`${dev.entity_type}-${dev.entity_id}-${dev.type}`}
              style={{ fontSize: "0.85rem", color: dev.type === "added" ? "var(--gruen)" : "var(--rot)" }}
            >
              {dev.type === "added" ? "+ Phase hinzugefügt: " : "− Phase entfernt: "}
              {entityDisplayName(dev.label, dev.type === "added" ? "Neue Phase" : "Entfernte Phase")}
            </div>
          ))}
        </div>
      )}
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
