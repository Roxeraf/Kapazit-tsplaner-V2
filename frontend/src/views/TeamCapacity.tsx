import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import CollapsiblePanel from "../components/CollapsiblePanel";
import ConfirmDialog from "../components/ConfirmDialog";
import type {
  JiraAccountMatch,
  JiraStatus,
  JiraSyncResult,
  PortfolioUtilizationEntry,
  Team,
  UnassignedAuthor,
} from "../types";

export default function TeamCapacity() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [members, setMembers] = useState<PortfolioUtilizationEntry[]>([]);
  const [jiraStatus, setJiraStatus] = useState<JiraStatus | null>(null);
  const [syncResult, setSyncResult] = useState<JiraSyncResult | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unassignedAuthors, setUnassignedAuthors] = useState<UnassignedAuthor[]>([]);
  const [dragOverTeamId, setDragOverTeamId] = useState<number | null>(null);
  const [teamToDelete, setTeamToDelete] = useState<{ id: number; name: string } | null>(null);
  const [memberToDeactivate, setMemberToDeactivate] = useState<{ id: number; name: string } | null>(null);

  const [newTeamName, setNewTeamName] = useState("");
  const [memberName, setMemberName] = useState("");
  const [memberWeeklyHours, setMemberWeeklyHours] = useState(40);
  const [memberJiraAccountId, setMemberJiraAccountId] = useState("");
  const [memberTeamId, setMemberTeamId] = useState<string>("");
  const [jiraQuery, setJiraQuery] = useState("");
  const [jiraMatches, setJiraMatches] = useState<JiraAccountMatch[]>([]);

  const load = () => {
    Promise.all([api.listTeams(), api.getUtilization(), api.jiraStatus(), api.listUnassignedAuthors()])
      .then(([t, u, j, a]) => {
        setTeams(t);
        setMembers(u);
        setJiraStatus(j);
        setUnassignedAuthors(a);
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

  const createMember = async (name: string, jiraAccountId: string | null, weeklyHours: number, teamId: number | null) => {
    const person = await api.createPerson({ display_name: name, jira_account_id: jiraAccountId });
    await api.createResourceProfile(person.id, { team_id: teamId, weekly_hours: weeklyHours });
  };

  const handleCreateMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!memberName.trim()) return;
    await createMember(
      memberName.trim(),
      memberJiraAccountId.trim() || null,
      memberWeeklyHours,
      memberTeamId ? Number(memberTeamId) : null,
    );
    setMemberName("");
    setMemberJiraAccountId("");
    setMemberWeeklyHours(40);
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
    personId: number,
    field: "name" | "jira_account_id" | "weekly_hours",
    raw: string,
  ) => {
    if (field === "weekly_hours") {
      const value = Number(raw);
      await api.updateResourceProfile(personId, { weekly_hours: Number.isFinite(value) ? value : 40 });
    } else if (field === "jira_account_id") {
      await api.updatePerson(personId, { jira_account_id: raw.trim() || null });
    } else {
      await api.updatePerson(personId, { display_name: raw });
    }
    load();
  };

  const handleDropMemberOnTeam = async (personId: number, teamId: number) => {
    await api.updateResourceProfile(personId, { team_id: teamId === 0 ? null : teamId });
    load();
  };

  const handleDeleteTeam = async () => {
    if (!teamToDelete) return;
    await api.deleteTeam(teamToDelete.id);
    setTeamToDelete(null);
    load();
  };

  const handleDeactivateMember = async () => {
    if (!memberToDeactivate) return;
    await api.updatePerson(memberToDeactivate.id, { active: false });
    setMemberToDeactivate(null);
    load();
  };

  const handleCreateFromAuthor = async (author: UnassignedAuthor, weeklyHours: number) => {
    await createMember(author.display_name, author.account_id, weeklyHours, null);
    load();
  };

  const teamName = (teamId: number | null) => teams.find((t) => t.id === teamId)?.name ?? null;
  const membersByTeam = (teamId: number | null) => members.filter((m) => m.team_id === teamId);

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
              {jiraStatus.configured && (jiraStatus.tempo_configured ? " (Worklogs über Tempo)" : " (natives Jira-Worklog)")}
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
        <div className="card" style={{ marginTop: "1rem", borderColor: "var(--blau)" }}>
          <strong>Sync-Ergebnis ({new Date().toLocaleTimeString()})</strong>
          {syncResult.ergebnisse.length === 0 && (
            <p style={{ color: "var(--text-muted)" }}>
              Keine Projekte mit gesetzter Jira-Komponente gefunden (im Projekt-Detail eintragen).
            </p>
          )}
          <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.2rem" }}>
            {syncResult.ergebnisse.map((r) => (
              <li key={r.project_id}>
                <Link to={`/projekte/${r.project_id}`}>{r.project_name}</Link> ({r.jira_component}):{" "}
                {r.error ? (
                  <span style={{ color: "var(--rot)" }}>{r.error}</span>
                ) : (
                  <>
                    {r.worklogs_synced} Worklogs synchronisiert
                    {r.unzugeordnete_buchungen > 0 && `, ${r.unzugeordnete_buchungen} ohne bekannten MA`}
                    {r.worklogs_synced === 0 && r.unzugeordnete_buchungen === 0 && (
                      <span style={{ color: "var(--text-muted)" }}>
                        {" "}
                        — keine gebuchten Zeiten zu dieser Component/diesem Label in Jira gefunden
                      </span>
                    )}
                    {r.unbekannte_beispiele.length > 0 && (
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
                        Beispiele nicht zugeordneter Autoren (Account-ID mit der Teammitglieder-Liste
                        vergleichen):
                        <ul style={{ margin: "0.15rem 0 0", paddingLeft: "1.2rem" }}>
                          {r.unbekannte_beispiele.map((u) => (
                            <li key={u.account_id}>
                              {u.display_name} — <code>{u.account_id}</code>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </li>
            ))}
          </ul>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.5rem 0 0" }}>
            Die synchronisierten Ist-FTE-Werte siehst du danach im Projekt-Detail (Zeile "FTE (Ist,
            Jira)"). "Ohne bekannten MA" heißt: es wurde Zeit gebucht, aber von jemandem ohne
            hinterlegte Jira-Account-ID unten in der Teammitglieder-Liste — deshalb kann die Buchung
            keinem Wochenstunden-Wert zugeordnet werden und fließt nicht in die Ist-FTE ein.
          </p>
        </div>
      )}

      {members.length > 0 && (
        <CollapsiblePanel title={`Alle Teammitglieder (${members.length})`}>
          <table className="planner" style={{ fontSize: "0.85rem" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Name</th>
                <th style={{ textAlign: "left" }}>Team</th>
                <th>Wochenstunden</th>
                <th style={{ textAlign: "left" }}>Jira-Account-ID</th>
              </tr>
            </thead>
            <tbody>
              {[...members]
                .sort((a, b) => a.person_name.localeCompare(b.person_name))
                .map((m) => (
                  <tr key={m.person_id}>
                    <td className="label">{m.person_name}</td>
                    <td style={{ textAlign: "left" }}>{m.team_name ?? "— ohne Team —"}</td>
                    <td>{m.weekly_hours}</td>
                    <td style={{ textAlign: "left", color: "var(--text-muted)" }}>{m.jira_account_id ?? "–"}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </CollapsiblePanel>
      )}

      {unassignedAuthors.length > 0 && (
        <CollapsiblePanel title={`Personen aus Buchungen ohne Teammitglied (${unassignedAuthors.length})`}>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "0 0 0.75rem" }}>
            Diese Namen kommen aus Jira/Tempo-Zeitbuchungen (Klarname automatisch aufgelöst) und
            haben noch keinen Teameintrag — Wochenstunden prüfen und anlegen, dann verschwinden
            sie aus dieser Liste.
          </p>
          {unassignedAuthors.map((author) => (
            <UnassignedAuthorRow key={author.account_id} author={author} onCreate={handleCreateFromAuthor} />
          ))}
        </CollapsiblePanel>
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
              value={memberWeeklyHours}
              onChange={(e) => setMemberWeeklyHours(Number(e.target.value))}
            />
          </label>
          <label>
            Team
            <select value={memberTeamId} onChange={(e) => setMemberTeamId(e.target.value)}>
              <option value="">— ohne Team —</option>
              {teams.map((t) => (
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

      {teams.length > 0 && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "1.25rem", marginBottom: 0 }}>
          Mitglieder per Drag &amp; Drop auf ein anderes Team ziehen, um sie zu verschieben.
        </p>
      )}

      {teams.map((team) => (
        <div
          key={team.id}
          className="card"
          style={{
            marginTop: "0.75rem",
            outline: dragOverTeamId === team.id ? "2px solid var(--blau)" : "none",
            outlineOffset: "-2px",
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOverTeamId(team.id);
          }}
          onDragLeave={() => setDragOverTeamId((id) => (id === team.id ? null : id))}
          onDrop={(e) => {
            e.preventDefault();
            setDragOverTeamId(null);
            const personId = Number(e.dataTransfer.getData("text/plain"));
            if (personId) handleDropMemberOnTeam(personId, team.id);
          }}
        >
          <div className="toolbar" style={{ marginBottom: "0.25rem" }}>
            <h3 style={{ color: "var(--navy)", margin: 0 }}>{team.name}</h3>
            <button
              type="button"
              className="btn secondary"
              style={{ color: "var(--rot)", borderColor: "var(--rot)" }}
              onClick={() => setTeamToDelete({ id: team.id, name: team.name })}
            >
              Team löschen
            </button>
          </div>
          {membersByTeam(team.id).length === 0 && <p style={{ color: "var(--text-muted)" }}>Keine Mitglieder.</p>}
          {membersByTeam(team.id).map((member) => (
            <MemberRow
              key={member.person_id}
              member={member}
              onFieldBlur={handleMemberFieldBlur}
              onDeactivateMember={() => setMemberToDeactivate({ id: member.person_id, name: member.person_name })}
            />
          ))}
        </div>
      ))}

      {membersByTeam(null).length > 0 && (
        <div className="card" style={{ marginTop: "0.75rem" }}>
          <h3 style={{ color: "var(--navy)", margin: "0 0 0.25rem" }}>{teamName(null) ?? "Ohne Team"}</h3>
          {membersByTeam(null).map((member) => (
            <MemberRow
              key={member.person_id}
              member={member}
              onFieldBlur={handleMemberFieldBlur}
              onDeactivateMember={() => setMemberToDeactivate({ id: member.person_id, name: member.person_name })}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={teamToDelete !== null}
        title="Team löschen"
        message={`Team "${teamToDelete?.name}" wirklich löschen? Die Mitglieder bleiben erhalten und werden auf "ohne Team" gesetzt.`}
        onConfirm={handleDeleteTeam}
        onCancel={() => setTeamToDelete(null)}
      />
      <ConfirmDialog
        open={memberToDeactivate !== null}
        title="Teammitglied deaktivieren"
        message={`Teammitglied "${memberToDeactivate?.name}" wirklich deaktivieren? Die Person verschwindet aus der Kapazitätsplanung, bleibt aber (reaktivierbar) in der Administration erhalten.`}
        onConfirm={handleDeactivateMember}
        onCancel={() => setMemberToDeactivate(null)}
      />
    </div>
  );
}

function UnassignedAuthorRow({
  author,
  onCreate,
}: {
  author: UnassignedAuthor;
  onCreate: (author: UnassignedAuthor, weeklyHours: number) => void;
}) {
  const [weeklyHours, setWeeklyHours] = useState(40);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.6rem",
        padding: "0.4rem 0",
        borderTop: "1px solid var(--border)",
      }}
    >
      <span style={{ flex: 1 }}>{author.display_name}</span>
      <label style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
        Wochenstunden
        <input
          type="number"
          min={1}
          max={48}
          value={weeklyHours}
          onChange={(e) => setWeeklyHours(Number(e.target.value))}
          style={{ width: "4rem" }}
        />
      </label>
      <button type="button" className="btn secondary" onClick={() => onCreate(author, weeklyHours)}>
        + Teammitglied anlegen
      </button>
    </div>
  );
}

function MemberRow({
  member,
  onFieldBlur,
  onDeactivateMember,
}: {
  member: PortfolioUtilizationEntry;
  onFieldBlur: (personId: number, field: "name" | "jira_account_id" | "weekly_hours", raw: string) => void;
  onDeactivateMember: () => void;
}) {
  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData("text/plain", String(member.person_id))}
      style={{ borderTop: "1px solid var(--border)", padding: "0.75rem 0", cursor: "grab" }}
    >
      <div className="field-row" style={{ marginTop: 0, alignItems: "center" }}>
        <span style={{ alignSelf: "center", color: "var(--text-muted)" }} title="Ziehbar, um das Team zu wechseln">
          ⠿
        </span>
        <label>
          Name
          <input
            defaultValue={member.person_name}
            onBlur={(e) => onFieldBlur(member.person_id, "name", e.target.value)}
          />
        </label>
        <label>
          Wochenstunden
          <input
            type="number"
            defaultValue={member.weekly_hours}
            onBlur={(e) => onFieldBlur(member.person_id, "weekly_hours", e.target.value)}
          />
        </label>
        <label>
          Jira-Account-ID
          <input
            defaultValue={member.jira_account_id ?? ""}
            onBlur={(e) => onFieldBlur(member.person_id, "jira_account_id", e.target.value)}
          />
        </label>
        <button
          type="button"
          className="btn secondary"
          style={{ alignSelf: "flex-end", color: "var(--rot)", borderColor: "var(--rot)" }}
          onClick={onDeactivateMember}
        >
          Deaktivieren
        </button>
      </div>

      <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
        Zugeordnet (aktuelle Periode): {member.zugeordnet_fte.toFixed(2)} FTE
        {member.auslastung_pct !== null && ` (${member.auslastung_pct.toFixed(0)}% Auslastung)`}
      </div>
    </div>
  );
}
