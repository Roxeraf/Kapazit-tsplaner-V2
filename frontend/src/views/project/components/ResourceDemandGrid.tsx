import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import PersonPicker from "../../../components/PersonPicker";
import type { AdminResourceRole, CandidatePerson, ResourceAssignment, ResourceDemand } from "../../../types";

// Phase 26.3: Raster "Rolle × Periode" als Bedienoberfläche für ResourceDemand - ersetzt das
// alte, in Phase 26.2 entfernte FTE-Raster. Zuordnung zu Personen (ResourceAssignment) über
// ein Detail-Panel unterhalb des Rasters, das sich bei Klick auf eine belegte Zelle öffnet.
export default function ResourceDemandGrid({ projectId, periods }: { projectId: number; periods: string[] }) {
  const [demands, setDemands] = useState<ResourceDemand[]>([]);
  const [roles, setRoles] = useState<AdminResourceRole[]>([]);
  const [visibleRoleIds, setVisibleRoleIds] = useState<number[]>([]);
  const [addRoleId, setAddRoleId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [selectedDemandId, setSelectedDemandId] = useState<number | null>(null);
  const [assignments, setAssignments] = useState<ResourceAssignment[]>([]);
  const [candidates, setCandidates] = useState<CandidatePerson[]>([]);
  const [assignPersonId, setAssignPersonId] = useState<number | null>(null);
  const [assignFte, setAssignFte] = useState(0.2);

  const refresh = () => {
    api
      .listResourceDemands(projectId)
      .then((rows) => {
        setDemands(rows);
        setVisibleRoleIds((prev) => Array.from(new Set([...prev, ...rows.map((d) => d.resource_role_id)])));
      })
      .catch((e) => setError(String(e)));
  };

  useEffect(refresh, [projectId]);
  useEffect(() => {
    api.listResourceRoles().then(setRoles).catch(() => setRoles([]));
  }, []);

  const refreshDetail = (demandId: number) => {
    api.listResourceAssignments(demandId).then(setAssignments).catch(() => setAssignments([]));
    api.getResourceDemandCandidates(demandId).then(setCandidates).catch(() => setCandidates([]));
  };

  const selectDemand = (demandId: number) => {
    setSelectedDemandId(demandId);
    setAssignPersonId(null);
    refreshDetail(demandId);
  };

  const demandFor = (roleId: number, period: string) =>
    demands.find((d) => d.resource_role_id === roleId && d.period === period);

  const handleCellBlur = async (roleId: number, period: string, raw: string) => {
    const existing = demandFor(roleId, period);
    const value = raw.trim() === "" ? null : Number(raw);
    if (value === null || !Number.isFinite(value)) {
      if (existing && raw.trim() === "") {
        await api.deleteResourceDemand(existing.id);
        if (selectedDemandId === existing.id) setSelectedDemandId(null);
        refresh();
      }
      return;
    }
    try {
      if (existing) {
        if (existing.fte !== value) {
          await api.updateResourceDemand(existing.id, { fte: value });
          refresh();
        }
      } else {
        const created = await api.createResourceDemand(projectId, { resource_role_id: roleId, period, fte: value });
        refresh();
        selectDemand(created.id);
      }
    } catch (e) {
      setError(String(e));
    }
  };

  const handleAddRole = () => {
    if (!addRoleId) return;
    setVisibleRoleIds((prev) => Array.from(new Set([...prev, Number(addRoleId)])));
    setAddRoleId("");
  };

  const handleAssign = async () => {
    if (!selectedDemandId || assignPersonId == null) return;
    try {
      await api.createResourceAssignment(selectedDemandId, { person_id: assignPersonId, fte: assignFte });
      setAssignPersonId(null);
      refresh();
      refreshDetail(selectedDemandId);
    } catch (e) {
      setError(String(e));
    }
  };

  const handleRemoveAssignment = async (assignmentId: number) => {
    await api.deleteResourceAssignment(assignmentId);
    if (selectedDemandId) {
      refresh();
      refreshDetail(selectedDemandId);
    }
  };

  const roleName = (id: number) => roles.find((r) => r.id === id)?.name ?? "…";
  const selectedDemand = demands.find((d) => d.id === selectedDemandId) ?? null;

  return (
    <div>
      <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Ressourcen</h3>
      {error && <p style={{ color: "var(--rot)", fontSize: "0.8rem" }}>{error}</p>}

      {visibleRoleIds.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Noch kein Ressourcenbedarf geplant.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="planner">
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Rolle</th>
                {periods.map((p) => (
                  <th key={p}>{p}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleRoleIds.map((roleId) => (
                <tr key={roleId}>
                  <td className="label">{roleName(roleId)}</td>
                  {periods.map((period) => {
                    const demand = demandFor(roleId, period);
                    const selected = demand && demand.id === selectedDemandId;
                    return (
                      <td key={period} style={{ background: selected ? "#eef3fa" : undefined }}>
                        <input
                          key={`${roleId}-${period}-${demand?.fte}`}
                          className="fte-input"
                          type="number"
                          step="0.1"
                          min={0}
                          defaultValue={demand?.fte ?? ""}
                          onFocus={() => demand && selectDemand(demand.id)}
                          onBlur={(e) => handleCellBlur(roleId, period, e.target.value)}
                        />
                        {demand && (
                          <div style={{ fontSize: "0.7rem", color: demand.allocation_gap > 0 ? "var(--rot)" : "var(--text-muted)" }}>
                            {demand.assigned_fte.toFixed(2)} zugeordnet
                            {demand.allocation_gap !== 0 && ` (${demand.allocation_gap > 0 ? "+" : ""}${demand.allocation_gap.toFixed(2)})`}
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="field-row" style={{ marginTop: "0.6rem" }}>
        <label>
          Rolle hinzufügen
          <select value={addRoleId} onChange={(e) => setAddRoleId(e.target.value)}>
            <option value="">— wählen —</option>
            {roles
              .filter((r) => !visibleRoleIds.includes(r.id))
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
          </select>
        </label>
        <button type="button" className="btn secondary" style={{ alignSelf: "flex-end" }} disabled={!addRoleId} onClick={handleAddRole}>
          + Hinzufügen
        </button>
      </div>

      {selectedDemand && (
        <div className="card" style={{ marginTop: "0.75rem", background: "#f8fafc" }}>
          <h4 style={{ marginTop: 0, color: "var(--navy)" }}>
            {roleName(selectedDemand.resource_role_id)} · {selectedDemand.period} · Bedarf {selectedDemand.fte.toFixed(2)} FTE
          </h4>

          {assignments.length === 0 ? (
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Noch niemand zugeordnet.</p>
          ) : (
            assignments.map((a) => (
              <div key={a.id} className="toolbar" style={{ fontSize: "0.85rem", padding: "0.2rem 0" }}>
                <span>
                  {a.person_name} — {a.fte.toFixed(2)} FTE
                </span>
                <button
                  type="button"
                  onClick={() => handleRemoveAssignment(a.id)}
                  style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                >
                  ×
                </button>
              </div>
            ))
          )}

          <h5 style={{ marginBottom: "0.3rem", color: "var(--navy)" }}>Geeignete Ressourcen</h5>
          {candidates.length === 0 ? (
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Keine Person mit freier Kapazität für diese Periode gefunden.</p>
          ) : (
            candidates.map((c) => (
              <div key={c.person_id} className="toolbar" style={{ fontSize: "0.85rem", padding: "0.15rem 0" }}>
                <span>
                  {c.display_name} — verfügbar: {c.available_fte.toFixed(2)} FTE
                  {c.skills.length > 0 && <span style={{ color: "var(--text-muted)" }}> · {c.skills.join(", ")}</span>}
                </span>
              </div>
            ))
          )}

          <div className="field-row" style={{ marginTop: "0.5rem" }}>
            <label>
              Person zuordnen
              <PersonPicker value={assignPersonId} onChange={setAssignPersonId} />
            </label>
            <label>
              FTE
              <input
                type="number"
                min={0.1}
                max={2}
                step={0.1}
                value={assignFte}
                onChange={(e) => setAssignFte(Number(e.target.value))}
              />
            </label>
            <button type="button" className="btn secondary" style={{ alignSelf: "flex-end" }} disabled={assignPersonId == null} onClick={handleAssign}>
              Zuordnen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
