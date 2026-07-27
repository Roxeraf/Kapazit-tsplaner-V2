import { useEffect, useState } from "react";
import { api } from "../api/client";
import type {
  JiraAccountMatch,
  JiraStatus,
  JiraSyncResult,
  SubprojectListItem,
  TeamWithMembers,
} from "../types";

export default function TeamCapacity() {
  const [teams, setTeams] = useState<TeamWithMembers[]>([]);
  const [subprojects, setSubprojects] = useState<SubprojectListItem[]>([]);
  const [jiraStatus, setJiraStatus] = useState<JiraStatus | null>(null);
  const [syncResult, setSyncResult] = useState<JiraSyncResult | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [newTeamName, setNewTeamName] = useState("");
  const [memberName, setMemberName] = useState("");
  const [memberWochenstunden, setMemberWochenstunden] = useState(40);
  const [memberJiraAccountId, setMemberJiraAccountId] = useState("");
  const [memberTeamId, setMemberTeamId] = useState<string>("");
  const [jiraQuery, setJiraQuery] = useState("");
  const [jiraMatches, setJiraMatches] = useState<JiraAccountMatch[]>([]);

  const load = () => {
    Promise.all([api.listTeams(), api.listAllSubprojects(), api.jiraStatus()])
      .then(([t, s, j]) => {
        setTeams(t);
        setSubprojects(s);
        setJiraStatus(j);
      })
      .catch((e) => setError(String(e)));
  };

  useEffect(load, []);

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTeamName.trim()) return;
    await api.createTeam(newTeamName.trim());
    setNewTeamName("");
    load();
  };

  const handleCreateMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!memberName.trim()) return;
    await api.createMember({
      name: memberName.trim(),
      jira_account_id: memberJiraAccountId.trim() || null,
      wochenstunden: memberWochenstunden,
      team_id: memberTeamId ? Number(memberTeamId) : null,
    });
    setMemberName("");
    setMemberJiraAccountId("");
    setMemberWochenstunden(40);
    setMemberTeamId("");
    setJiraMatches([]);
    setJiraQuery("");
    load();
  };

  const handleJiraLookup = async () => {
    if (!jiraQuery.trim()) return;
    try {
      const matches = await api.jiraLookupAccount(jiraQuery.trim());
      setJiraMatches(matches);
    } catch (e) {
      setError(String(e));
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      const result = await api.jiraSync();
      setSyncResult(result);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSyncing(false);
    }
  };

  const handleMemberFieldBlur = async (
    memberId: number,
    field: "name" | "jira_account_id" | "wochenstunden",
    raw: string,
  ) => {
    if (field === "wochenstunden") {
      const value = Number(raw);
      await api.updateMember(memberId, { wochenstunden: Number.isFinite(value) ? value : 40 });
    } else if (field === "jira_account_id") {
      await api.updateMember(memberId, { jira_account_id: raw.trim() || null });
    } else {
      await api.updateMember(memberId, { name: raw });
    }
    load();
  };

  const handleAddAssignment = async (memberId: number, subprojectId: string, anteil: number) => {
    if (!subprojectId) return;
    await api.createAssignment(memberId, Number(subprojectId), anteil);
    load();
  };

  return (
    <div>
      <div className="toolbar">
        <h2 className="section-title" style={{ margin: 0 }}>
          Team-Kapazität
        </h2>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {jiraStatus && (
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Jira: {jiraStatus.configured ? "verbunden" : "nicht konfiguriert"}
            </span>
          )}
          <button className="btn" onClick={handleSync} disabled={!jiraStatus?.configured || syncing}>
            {syncing ? "Synchronisiere …" : "Jira-Sync jetzt ausführen"}
          </button>
        </div>
      </div>

      {jiraStatus && !jiraStatus.configured && (
        <div className="stub-view" style={{ marginTop: "0.75rem" }}>
          {jiraStatus.hinweis}
        </div>
      )}
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      {syncResult && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <strong>Sync-Ergebnis</strong>
          {syncResult.ergebnisse.length === 0 && (
            <p style={{ color: "var(--text-muted)" }}>
              Keine Teilprojekte mit gesetzter Jira-Komponente gefunden (siehe Projekt-Detail).
            </p>
          )}
          <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.2rem" }}>
            {syncResult.ergebnisse.map((r) => (
              <li key={r.subproject_id}>
                {r.subproject_name} ({r.jira_component}):{" "}
                {r.error ? (
                  <span style={{ color: "var(--rot)" }}>{r.error}</span>
                ) : (
                  <>
                    {r.worklogs_synced} Worklogs synchronisiert
                    {r.unzugeordnete_buchungen > 0 && `, ${r.unzugeordnete_buchungen} ohne bekannten MA`}
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <form className="card" style={{ marginTop: "1rem" }} onSubmit={handleCreateTeam}>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Neues Team
            <input value={newTeamName} onChange={(e) => setNewTeamName(e.target.value)} placeholder="z. B. Team Nord" />
          </label>
        </div>
        <button className="btn" type="submit" style={{ marginTop: "0.75rem" }}>
          Team anlegen
        </button>
      </form>

      <form className="card" style={{ marginTop: "1rem" }} onSubmit={handleCreateMember}>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Name
            <input required value={memberName} onChange={(e) => setMemberName(e.target.value)} />
          </label>
          <label>
            Wochenstunden
            <input
              type="number"
              min={1}
              max={48}
              value={memberWochenstunden}
              onChange={(e) => setMemberWochenstunden(Number(e.target.value))}
            />
          </label>
          <label>
            Team
            <select value={memberTeamId} onChange={(e) => setMemberTeamId(e.target.value)}>
              <option value="">— ohne Team —</option>
              {teams
                .filter((t) => t.id !== 0)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Jira-Account-ID
            <input
              value={memberJiraAccountId}
              onChange={(e) => setMemberJiraAccountId(e.target.value)}
              placeholder="wird über Jira-Suche befüllt"
            />
          </label>
        </div>

        <div className="field-row">
          <label>
            Jira-Nutzersuche (Name/E-Mail)
            <input value={jiraQuery} onChange={(e) => setJiraQuery(e.target.value)} />
          </label>
          <button
            type="button"
            className="btn secondary"
            style={{ alignSelf: "flex-end" }}
            onClick={handleJiraLookup}
            disabled={!jiraStatus?.configured}
          >
            Suchen
          </button>
        </div>
        {jiraMatches.length > 0 && (
          <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.2rem" }}>
            {jiraMatches.map((m) => (
              <li key={m.account_id}>
                <button
                  type="button"
                  className="btn secondary"
                  style={{ padding: "0.15rem 0.5rem", fontSize: "0.8rem" }}
                  onClick={() => setMemberJiraAccountId(m.account_id)}
                >
                  übernehmen
                </button>{" "}
                {m.display_name} {m.email && `(${m.email})`}
              </li>
            ))}
          </ul>
        )}

        <button className="btn" type="submit" style={{ marginTop: "0.75rem" }}>
          Teammitglied anlegen
        </button>
      </form>

      {teams.map((team) => (
        <div key={team.id} className="card" style={{ marginTop: "1.25rem" }}>
          <h3 style={{ color: "var(--navy)", marginTop: 0 }}>{team.name}</h3>
          {team.members.length === 0 && <p style={{ color: "var(--text-muted)" }}>Keine Mitglieder.</p>}
          {team.members.map((member) => (
            <MemberRow
              key={member.id}
              member={member}
              subprojects={subprojects}
              onFieldBlur={handleMemberFieldBlur}
              onAddAssignment={handleAddAssignment}
              onDeleteAssignment={async (id) => {
                await api.deleteAssignment(id);
                load();
              }}
              onDeleteMember={async () => {
                await api.deleteMember(member.id);
                load();
              }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function MemberRow({
  member,
  subprojects,
  onFieldBlur,
  onAddAssignment,
  onDeleteAssignment,
  onDeleteMember,
}: {
  member: TeamWithMembers["members"][number];
  subprojects: SubprojectListItem[];
  onFieldBlur: (memberId: number, field: "name" | "jira_account_id" | "wochenstunden", raw: string) => void;
  onAddAssignment: (memberId: number, subprojectId: string, anteil: number) => void;
  onDeleteAssignment: (assignmentId: number) => void;
  onDeleteMember: () => void;
}) {
  const [newSubprojectId, setNewSubprojectId] = useState("");
  const [newAnteil, setNewAnteil] = useState(100);

  return (
    <div style={{ borderTop: "1px solid var(--border)", padding: "0.75rem 0" }}>
      <div className="field-row" style={{ marginTop: 0, alignItems: "center" }}>
        <label>
          Name
          <input defaultValue={member.name} onBlur={(e) => onFieldBlur(member.id, "name", e.target.value)} />
        </label>
        <label>
          Wochenstunden
          <input
            type="number"
            defaultValue={member.wochenstunden}
            onBlur={(e) => onFieldBlur(member.id, "wochenstunden", e.target.value)}
          />
        </label>
        <label>
          Jira-Account-ID
          <input
            defaultValue={member.jira_account_id ?? ""}
            onBlur={(e) => onFieldBlur(member.id, "jira_account_id", e.target.value)}
          />
        </label>
        <button
          type="button"
          className="btn secondary"
          style={{ alignSelf: "flex-end", color: "var(--rot)", borderColor: "var(--rot)" }}
          onClick={onDeleteMember}
        >
          Entfernen
        </button>
      </div>

      <div style={{ marginTop: "0.5rem", fontSize: "0.85rem" }}>
        <strong>Zuordnungen: </strong>
        {member.assignments.length === 0 && <span style={{ color: "var(--text-muted)" }}>keine</span>}
        {member.assignments.map((a) => (
          <span key={a.id} className="legend-chip" style={{ marginRight: "0.5rem" }}>
            {a.project_name} / {a.subproject_name} ({a.anteil}%)
            <button
              type="button"
              onClick={() => onDeleteAssignment(a.id)}
              style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
            >
              ×
            </button>
          </span>
        ))}
      </div>

      <div className="field-row" style={{ marginTop: "0.4rem" }}>
        <label>
          Teilprojekt zuordnen
          <select value={newSubprojectId} onChange={(e) => setNewSubprojectId(e.target.value)}>
            <option value="">— wählen —</option>
            {subprojects.map((sp) => (
              <option key={sp.id} value={sp.id}>
                {sp.project_name} / {sp.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Anteil (%)
          <input
            type="number"
            min={1}
            max={100}
            value={newAnteil}
            onChange={(e) => setNewAnteil(Number(e.target.value))}
          />
        </label>
        <button
          type="button"
          className="btn secondary"
          style={{ alignSelf: "flex-end" }}
          onClick={() => {
            onAddAssignment(member.id, newSubprojectId, newAnteil);
            setNewSubprojectId("");
          }}
        >
          + Zuordnen
        </button>
      </div>
    </div>
  );
}
