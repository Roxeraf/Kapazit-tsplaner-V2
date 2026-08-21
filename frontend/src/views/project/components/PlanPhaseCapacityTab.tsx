import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import PersonPicker from "../../../components/PersonPicker";
import type { AdminResourceRole, CandidatePerson, PhaseMetricsOut, ResourceAssignment, ResourceDemand } from "../../../types";

const MONAT_NAMEN = ["Jan", "Feb", "Mrz", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];

// Periode ("Apr 26") aus forecast_start ableiten - ResourceDemand ist im Backend immer
// periodengebunden (constants.parse_period), auch wenn die Kapazitäts-UX pro Phase nur eine
// einzelne Rolle-FTE-Zeile zeigen will. Für Phasen ohne Termin: laufender Monat.
function defaultPeriod(forecastStart: string | null): string {
  const d = forecastStart ? new Date(forecastStart + "T00:00:00") : new Date();
  if (Number.isNaN(d.getTime())) return `${MONAT_NAMEN[new Date().getMonth()]} ${String(new Date().getFullYear()).slice(2)}`;
  return `${MONAT_NAMEN[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`;
}

function fmtFte(v: number | null | undefined): string {
  return v == null ? "—" : `${v.toFixed(2)} FTE`;
}

function DemandAssignments({ demand, onChanged }: { demand: ResourceDemand; onChanged: () => void }) {
  const [assignments, setAssignments] = useState<ResourceAssignment[]>([]);
  const [candidates, setCandidates] = useState<CandidatePerson[]>([]);
  const [personId, setPersonId] = useState<number | null>(null);
  const [fte, setFte] = useState(0.2);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    api.listResourceAssignments(demand.id).then(setAssignments).catch(() => setAssignments([]));
    api.getResourceDemandCandidates(demand.id).then(setCandidates).catch(() => setCandidates([]));
  };

  useEffect(refresh, [demand.id]);

  const handleAssign = async () => {
    if (personId == null) return;
    try {
      await api.createResourceAssignment(demand.id, { person_id: personId, fte });
      setPersonId(null);
      refresh();
      onChanged();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleRemove = async (assignmentId: number) => {
    await api.deleteResourceAssignment(assignmentId);
    refresh();
    onChanged();
  };

  return (
    <div style={{ marginTop: "0.4rem", paddingLeft: "0.5rem", borderLeft: "2px solid var(--border)" }}>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.78rem" }}>{error}</p>}
      {assignments.length === 0 ? (
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.2rem 0" }}>Noch niemand zugeordnet.</p>
      ) : (
        assignments.map((a) => (
          <div key={a.id} className="toolbar" style={{ fontSize: "0.82rem", padding: "0.1rem 0" }}>
            <span>
              {a.person_name} — {a.fte.toFixed(2)} FTE
            </span>
            <button type="button" onClick={() => handleRemove(a.id)} style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}>
              ×
            </button>
          </div>
        ))
      )}
      <div className="field-row" style={{ marginTop: "0.35rem" }}>
        <label style={{ flex: 1 }}>
          Person zuordnen
          <PersonPicker value={personId} onChange={setPersonId} />
        </label>
        <label>
          FTE
          <input type="number" min={0.1} max={2} step={0.1} value={fte} onChange={(e) => setFte(Number(e.target.value))} style={{ width: "4.5rem" }} />
        </label>
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-end" }} disabled={personId == null} onClick={handleAssign}>
          Zuordnen
        </button>
      </div>
      {candidates.length > 0 && (
        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0.3rem 0 0" }}>
          Verfügbar: {candidates.map((c) => `${c.display_name} (${c.available_fte.toFixed(2)})`).join(", ")}
        </p>
      )}
    </div>
  );
}

// P11 (PlanPhase Workspace, Tab "Kapazität"): Plan-FTE + Planstunden als Kopfzeile, darunter
// die Rollen-Aufschlüsselung (ResourceDemand, plan_phase_id-gefiltert) inkl. Personenbesetzung
// (ResourceAssignment) - in schlichter Fachsprache statt Backend-Begriffen. Reine
// Wiederverwendung bestehender Endpoints (routers/capacity.py), keine neuen.
export default function PlanPhaseCapacityTab({
  projectId,
  planPhaseId,
  planFte,
  forecastStart,
  demands,
  metrics,
  onChanged,
}: {
  projectId: number;
  planPhaseId: number;
  planFte: number | null;
  forecastStart: string | null;
  demands: ResourceDemand[];
  metrics: PhaseMetricsOut;
  onChanged: () => void;
}) {
  const [roles, setRoles] = useState<AdminResourceRole[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [addRoleId, setAddRoleId] = useState("");
  const [addFte, setAddFte] = useState(0.2);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listResourceRoles().then(setRoles).catch(() => setRoles([]));
  }, []);

  const handleAddDemand = async () => {
    if (!addRoleId) return;
    try {
      await api.createResourceDemand(projectId, {
        plan_phase_id: planPhaseId,
        resource_role_id: Number(addRoleId),
        period: defaultPeriod(forecastStart),
        fte: addFte,
      });
      setAddRoleId("");
      setAddFte(0.2);
      onChanged();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleDeleteDemand = async (demandId: number) => {
    await api.deleteResourceDemand(demandId);
    if (expandedId === demandId) setExpandedId(null);
    onChanged();
  };

  // P14.2 (Reconciliation sichtbar): plan_fte bleibt führend (CONCEPT.md Abschnitt 3/6) - wenn
  // die Rollen-Aufschlüsselung mehr FTE summiert als geplant, wird das nicht automatisch
  // korrigiert, sondern klar erklärt statt eine verwirrende negative Zahl zu zeigen.
  const openFte = metrics.reconciliation.open_fte;
  const overAllocated = openFte != null && openFte < 0;

  return (
    <div>
      <div className="card" style={{ marginBottom: "0.75rem" }}>
        <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Phasenaufwand</h4>
        <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 0 }}>
          Der Aufwand dieser einen Phase - unabhängig von der projektweiten Monatsansicht "Projektkapazität nach
          Monat" weiter oben im Planung-Tab (zwei getrennte Achsen, keine doppelte Pflege).
        </p>
        <div style={{ fontSize: "0.85rem", display: "grid", gap: "0.3rem" }}>
          <div>
            <strong>Plan-Aufwand:</strong> {fmtFte(planFte)}
          </div>
          <div>
            <strong>Planstunden:</strong> {metrics.plan_hours == null ? "—" : `${metrics.plan_hours} h`}
          </div>
        </div>
      </div>

      <div className="card">
        <h4 style={{ color: "var(--navy)", marginTop: 0, marginBottom: "0.5rem" }}>Aufschlüsselung</h4>
        {demands.length === 0 ? (
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch keine Rollen-Aufschlüsselung.</p>
        ) : (
          demands.map((d) => (
            <div key={d.id} style={{ marginBottom: "0.5rem", paddingBottom: "0.4rem", borderBottom: "1px solid var(--border)" }}>
              <div className="toolbar">
                <button
                  type="button"
                  onClick={() => setExpandedId(expandedId === d.id ? null : d.id)}
                  style={{ border: "none", background: "none", cursor: "pointer", textAlign: "left", padding: 0, fontSize: "0.88rem", fontWeight: 600, color: "var(--navy)" }}
                >
                  {expandedId === d.id ? "▾" : "▸"} {d.resource_role_name}
                </button>
                <div style={{ display: "flex", gap: "0.6rem", alignItems: "center", fontSize: "0.85rem" }}>
                  <span>Bedarf {d.fte.toFixed(2)} FTE</span>
                  <span style={{ color: d.allocation_gap > 0 ? "var(--rot)" : "var(--gruen)" }}>
                    Besetzt {d.assigned_fte.toFixed(2)}
                    {d.allocation_gap > 0 && ` · noch unbesetzt ${d.allocation_gap.toFixed(2)}`}
                  </span>
                  <button type="button" onClick={() => handleDeleteDemand(d.id)} style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}>
                    ×
                  </button>
                </div>
              </div>
              {expandedId === d.id && <DemandAssignments demand={d} onChanged={onChanged} />}
            </div>
          ))
        )}

        <div style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>
              <strong>Aufgeschlüsselt:</strong> {fmtFte(metrics.reconciliation.breakdown_fte)}
            </span>
            {!overAllocated && (
              <span>
                <strong>Noch nicht aufgeschlüsselt:</strong> {fmtFte(openFte)}
              </span>
            )}
          </div>
          {overAllocated && (
            <p style={{ color: "var(--rot)", margin: "0.3rem 0 0", fontSize: "0.82rem" }}>
              Aufgeschlüsselter Bedarf liegt {Math.abs(openFte!).toFixed(2)} FTE über dem geplanten
              Phasenaufwand. Plan-FTE bleibt führend.
            </p>
          )}
        </div>

        {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}
        <div className="field-row" style={{ marginTop: "0.6rem" }}>
          <label>
            Rolle hinzufügen
            <select value={addRoleId} onChange={(e) => setAddRoleId(e.target.value)}>
              <option value="">— wählen —</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            FTE
            <input type="number" min={0.1} step={0.1} value={addFte} onChange={(e) => setAddFte(Number(e.target.value))} style={{ width: "4.5rem" }} />
          </label>
          <button type="button" className="btn secondary" style={{ alignSelf: "flex-end" }} disabled={!addRoleId} onClick={handleAddDemand}>
            + Hinzufügen
          </button>
        </div>
      </div>
    </div>
  );
}
