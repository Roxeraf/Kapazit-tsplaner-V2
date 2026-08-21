import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import PersonPicker from "../../../components/PersonPicker";
import type { AdminProjectRole, ProjectMembership } from "../../../types";

// Phase 26.1: "Projektteam" - reine Frontend-Neuerung auf den seit Phase 14 bestehenden,
// bisher ungenutzten Endpunkten GET/POST /projects/{id}/memberships und GET /project-roles.
export default function ProjectTeamSection({ projectId }: { projectId: number }) {
  const [memberships, setMemberships] = useState<ProjectMembership[]>([]);
  const [roles, setRoles] = useState<AdminProjectRole[]>([]);
  const [newPersonId, setNewPersonId] = useState<number | null>(null);
  const [newRoleId, setNewRoleId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    api.listProjectMemberships(projectId).then(setMemberships).catch((e) => setError(String(e)));
  };

  useEffect(() => {
    refresh();
    api.listProjectRoles().then(setRoles).catch(() => setRoles([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const handleAdd = async () => {
    if (newPersonId == null || newRoleId === "") return;
    setError(null);
    try {
      await api.createProjectMembership(projectId, newPersonId, newRoleId);
      setNewPersonId(null);
      setNewRoleId("");
      refresh();
    } catch (e) {
      setError(String(e));
    }
  };

  const handleRemove = async (membershipId: number) => {
    await api.deleteProjectMembership(membershipId);
    refresh();
  };

  const byRole = new Map<string, ProjectMembership[]>();
  for (const m of memberships) {
    const list = byRole.get(m.project_role_name) ?? [];
    list.push(m);
    byRole.set(m.project_role_name, list);
  }

  return (
    <div>
      <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Projektteam</h3>
      <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginTop: "-0.3rem" }}>
        Wer am Projekt beteiligt ist - das ist unabhängig von der Kapazitätsbesetzung (FTE-Zuordnung im
        Planung-Tab). Eine Person hier hinzuzufügen erzeugt keine automatische FTE-Zuordnung.
      </p>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}
      {memberships.length === 0 ? (
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Noch niemand zugeordnet.</p>
      ) : (
        Array.from(byRole.entries()).map(([roleName, members]) => (
          <div key={roleName} style={{ marginBottom: "0.6rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.2rem" }}>{roleName}</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
              {members.map((m) => (
                <span
                  key={m.id}
                  className="legend-chip"
                  style={{ background: "#eef3fa", padding: "0.15rem 0.6rem", borderRadius: "999px", display: "inline-flex", alignItems: "center", gap: "0.3rem" }}
                >
                  {m.person_name}
                  <button
                    type="button"
                    onClick={() => handleRemove(m.id)}
                    style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
                    aria-label={`${m.person_name} entfernen`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>
        ))
      )}
      <div className="field-row" style={{ marginTop: "0.6rem" }}>
        <label>
          Person
          <PersonPicker value={newPersonId} onChange={setNewPersonId} placeholder="Person suchen …" />
        </label>
        <label>
          Rolle
          <select value={newRoleId} onChange={(e) => setNewRoleId(e.target.value ? Number(e.target.value) : "")}>
            <option value="">— wählen —</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="btn secondary" onClick={handleAdd} disabled={newPersonId == null || newRoleId === ""}>
          Hinzufügen
        </button>
      </div>
    </div>
  );
}
