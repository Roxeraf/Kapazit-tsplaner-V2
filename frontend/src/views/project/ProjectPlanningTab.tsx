import { useEffect, useState } from "react";
import { api } from "../../api/client";
import ConfirmDialog from "../../components/ConfirmDialog";
import { useUnsavedChanges } from "../../unsavedChanges";
import type { Comment, PhaseCode, ProjectDetail as ProjectDetailT, TeamMember } from "../../types";
import PhaseRows from "./components/PhaseRows";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

function diffPhasen(
  alt: Record<string, PhaseCode[]>,
  neu: Record<string, PhaseCode[]>,
  monate: string[],
): { monat: string; codes: PhaseCode[] }[] {
  const changes: { monat: string; codes: PhaseCode[] }[] = [];
  for (const monat of monate) {
    const altCodes = [...(alt[monat] ?? [])].sort().join(",");
    const neuCodes = [...(neu[monat] ?? [])].sort().join(",");
    if (altCodes !== neuCodes) changes.push({ monat, codes: neu[monat] ?? [] });
  }
  return changes;
}

function diffFte(
  alt: Record<string, number>,
  neu: Record<string, number>,
  monate: string[],
): { monat: string; wert: number }[] {
  const changes: { monat: string; wert: number }[] = [];
  for (const monat of monate) {
    if ((alt[monat] ?? 0) !== (neu[monat] ?? 0)) changes.push({ monat, wert: neu[monat] ?? 0 });
  }
  return changes;
}

export default function ProjectPlanningTab() {
  const { project, reload: reloadWorkspace } = useProjectWorkspace();
  const projectId = project.id;
  const { isDirty, setIsDirty } = useUnsavedChanges();

  const [saved, setSaved] = useState<ProjectDetailT | null>(null);
  const [draft, setDraft] = useState<ProjectDetailT | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [saveReason, setSaveReason] = useState("");

  const [comments, setComments] = useState<Comment[]>([]);
  const [newSubprojectName, setNewSubprojectName] = useState("");
  const [subprojectToDelete, setSubprojectToDelete] = useState<{ id: number; name: string } | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [newAssignmentMemberId, setNewAssignmentMemberId] = useState("");
  const [newAssignmentFte, setNewAssignmentFte] = useState(0.5);

  const load = () => {
    api
      .getProject(projectId)
      .then((p) => {
        setSaved(p);
        setDraft(structuredClone(p));
        setIsDirty(false);
      })
      .catch((e) => setError(String(e)));
  };

  const refreshComments = () => {
    api.listComments(projectId).then(setComments).catch(() => {});
  };

  useEffect(() => {
    api.listMembers().then(setMembers).catch((e) => setError(String(e)));
  }, []);

  useEffect(load, [projectId]);
  useEffect(refreshComments, [projectId]);

  // Verlässt der Nutzer die Seite (Tab schließen, Reload, URL-Leiste) mit ungespeicherten
  // Planungsänderungen, warnt der Browser nativ davor.
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (!isDirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

  // Strukturelle Aktionen (Teilprojekt anlegen/löschen, Team-Zuordnung) bleiben sofort
  // wirksam und laden das Projekt neu - das würde unentdeckte, ungespeicherte
  // Planungsänderungen (Entwurfsmodus) stillschweigend verwerfen. Vorher nachfragen.
  const confirmDiscardIfDirty = () => {
    if (!isDirty) return true;
    return window.confirm(
      "Du hast ungespeicherte Planungsänderungen. Diese Aktion lädt das Projekt neu, die Änderungen gehen dabei verloren. Trotzdem fortfahren?",
    );
  };

  // Entwurfsmodus: alle Planungs-Handler schreiben nur noch lokal in draft, keine API-Calls,
  // kein Reload - erst "Speichern" schreibt in die DB (siehe handleSave).
  const handleFteChange = (subprojectId: number, monat: string, raw: string) => {
    const value = Number(raw);
    setDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        subprojects: prev.subprojects.map((sp) =>
          sp.id === subprojectId
            ? { ...sp, fte: { ...sp.fte, [monat]: Number.isFinite(value) ? value : 0 } }
            : sp,
        ),
      };
    });
    setIsDirty(true);
  };

  // Ein Klick ist ein Drag der Länge 1: beides läuft über denselben Commit-Pfad, der die
  // betroffenen Monate zusammen in den lokalen Entwurf übernimmt.
  const commitProjectPhaseDrag = (code: PhaseCode, changes: Record<string, boolean>) => {
    setDraft((prev) => {
      if (!prev) return prev;
      const phasen = { ...prev.phasen };
      for (const [monat, makeActive] of Object.entries(changes)) {
        const current = phasen[monat] ?? [];
        if (current.includes(code) === makeActive) continue;
        phasen[monat] = makeActive ? [...current, code] : current.filter((c) => c !== code);
      }
      return { ...prev, phasen };
    });
    setIsDirty(true);
  };

  const commitSubprojectPhaseDrag = (subprojectId: number, code: PhaseCode, changes: Record<string, boolean>) => {
    setDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        subprojects: prev.subprojects.map((sp) => {
          if (sp.id !== subprojectId) return sp;
          const phasen = { ...sp.phasen };
          for (const [monat, makeActive] of Object.entries(changes)) {
            const current = phasen[monat] ?? [];
            if (current.includes(code) === makeActive) continue;
            phasen[monat] = makeActive ? [...current, code] : current.filter((c) => c !== code);
          }
          return { ...sp, phasen };
        }),
      };
    });
    setIsDirty(true);
  };

  const handleProjectFteChange = (monat: string, raw: string) => {
    const value = Number(raw);
    setDraft((prev) => (prev ? { ...prev, fte: { ...prev.fte, [monat]: Number.isFinite(value) ? value : 0 } } : prev));
    setIsDirty(true);
  };

  const handleProjectFieldChange = (field: "name" | "kunde" | "start_monat" | "anzahl_monate", raw: string) => {
    setDraft((prev) => {
      if (!prev) return prev;
      if (field === "anzahl_monate") {
        const value = Number(raw);
        if (!Number.isFinite(value) || value < 1) return prev;
        return { ...prev, anzahl_monate: value };
      }
      if (field === "kunde") return { ...prev, kunde: raw.trim() || null };
      if (field === "start_monat") {
        if (!/^\d{2}\.\d{4}$/.test(raw)) return prev;
        return { ...prev, start_monat: raw };
      }
      if (!raw.trim()) return prev;
      return { ...prev, name: raw.trim() };
    });
    setIsDirty(true);
  };

  const handleSave = async () => {
    if (!draft || !saved) return;
    setSaving(true);
    setError(null);
    try {
      let kommentarId: number | null = null;
      if (saveReason.trim()) {
        const comment = await api.createComment(saved.id, { text: saveReason.trim() });
        kommentarId = comment.id;
      }

      const stammdaten: Partial<{ name: string; kunde: string | null; start_monat: string; anzahl_monate: number }> = {};
      if (draft.name !== saved.name) stammdaten.name = draft.name;
      if (draft.kunde !== saved.kunde) stammdaten.kunde = draft.kunde;
      if (draft.start_monat !== saved.start_monat) stammdaten.start_monat = draft.start_monat;
      if (draft.anzahl_monate !== saved.anzahl_monate) stammdaten.anzahl_monate = draft.anzahl_monate;
      if (Object.keys(stammdaten).length > 0) {
        await api.updateProject(saved.id, { ...stammdaten, kommentar_id: kommentarId });
      }

      if (!draft.aus_teilprojekten) {
        for (const change of diffPhasen(saved.phasen, draft.phasen, draft.monate)) {
          await api.setProjectPhasen(saved.id, change.monat, change.codes, kommentarId);
        }
        for (const change of diffFte(saved.fte, draft.fte, draft.monate)) {
          await api.setProjectFte(saved.id, change.monat, change.wert, kommentarId);
        }
      }

      for (const sp of draft.subprojects) {
        const savedSp = saved.subprojects.find((s) => s.id === sp.id);
        if (!savedSp) continue;
        for (const change of diffPhasen(savedSp.phasen, sp.phasen, draft.monate)) {
          await api.setPhasen(sp.id, change.monat, change.codes, kommentarId);
        }
        for (const change of diffFte(savedSp.fte, sp.fte, draft.monate)) {
          await api.setFte(sp.id, change.monat, change.wert, kommentarId);
        }
      }

      setSaveReason("");
      setSavedAt(new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }));
      load();
      refreshComments();
      reloadWorkspace();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleAddCellComment = async (
    subprojectId: number | null,
    phaseCode: PhaseCode,
    monat: string,
    text: string,
  ) => {
    await api.createComment(projectId, { subproject_id: subprojectId, monat, phase_code: phaseCode, text });
    refreshComments();
  };

  const handleDeleteComment = async (commentId: number) => {
    await api.deleteComment(commentId);
    refreshComments();
  };

  const handleAddSubproject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft || !confirmDiscardIfDirty()) return;
    await api.createSubproject(draft.id, newSubprojectName, draft.subprojects.length);
    setNewSubprojectName("");
    load();
    reloadWorkspace();
  };

  const handleDeleteSubproject = async () => {
    if (!subprojectToDelete || !confirmDiscardIfDirty()) return;
    await api.deleteSubproject(subprojectToDelete.id);
    setSubprojectToDelete(null);
    load();
    reloadWorkspace();
  };

  const handleAddTeamAssignment = async () => {
    if (!draft || !newAssignmentMemberId || !confirmDiscardIfDirty()) return;
    await api.createAssignment(Number(newAssignmentMemberId), draft.id, newAssignmentFte);
    setNewAssignmentMemberId("");
    load();
  };

  const handleDeleteTeamAssignment = async (assignmentId: number) => {
    if (!confirmDiscardIfDirty()) return;
    await api.deleteAssignment(assignmentId);
    load();
  };

  if (!draft) return <p>Lade Planung …</p>;

  const monate = draft.monate;
  const cellComments = (subprojectId: number | null) =>
    comments.filter((c) => c.subproject_id === subprojectId && c.monat !== null && c.phase_code !== null);

  return (
    <div>
      {error && (
        <div
          className="card"
          style={{
            marginBottom: "1rem",
            borderColor: "var(--rot)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "1rem",
          }}
        >
          <span style={{ color: "var(--rot)" }}>{error}</span>
          <button type="button" className="btn secondary" onClick={() => setError(null)}>
            Schließen
          </button>
        </div>
      )}

      <div className="toolbar" style={{ marginBottom: "1rem" }}>
        <div />
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {!isDirty && savedAt && <span style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Gespeichert um {savedAt}</span>}
          <input
            value={saveReason}
            onChange={(e) => setSaveReason(e.target.value)}
            placeholder="Grund für diese Änderung (optional)"
            style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px", width: "16rem" }}
          />
          <button type="button" className="btn" disabled={!isDirty || saving} onClick={handleSave}>
            {saving ? "Speichert …" : "Speichern"}
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Projektname
            <input key={saved?.name} defaultValue={draft.name} onBlur={(e) => handleProjectFieldChange("name", e.target.value)} />
          </label>
          <label>
            Kunde
            <input
              key={saved?.kunde ?? ""}
              defaultValue={draft.kunde ?? ""}
              onBlur={(e) => handleProjectFieldChange("kunde", e.target.value)}
            />
          </label>
          <label>
            Startmonat (MM.YYYY)
            <input
              key={saved?.start_monat}
              defaultValue={draft.start_monat}
              pattern="\d{2}\.\d{4}"
              onBlur={(e) => handleProjectFieldChange("start_monat", e.target.value)}
            />
          </label>
          <label>
            Anzahl Monate
            <input
              key={saved?.anzahl_monate}
              type="number"
              min={1}
              max={24}
              defaultValue={draft.anzahl_monate}
              onBlur={(e) => handleProjectFieldChange("anzahl_monate", e.target.value)}
            />
          </label>
        </div>
        {(draft.start_monat !== saved?.start_monat || draft.anzahl_monate !== saved?.anzahl_monate) && (
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.5rem 0 0" }}>
            Neue Monatsspalten werden erst nach dem Speichern angezeigt.
          </p>
        )}
      </div>

      <div className="card" style={{ marginBottom: "1.25rem", overflowX: "auto" }}>
        <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
          <h3 style={{ color: "var(--navy)", margin: 0 }}>Projekt gesamt</h3>
        </div>
        {draft.aus_teilprojekten && (
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0 0 0.5rem" }}>
            Phasen und FTE (Soll) sind hier die Zusammenfassung aus den Teilprojekten unten —
            dort eintragen, nicht hier.
          </p>
        )}
        <table className="planner">
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>Gantt-Phasen</th>
              {monate.map((m) => (
                <th key={m}>{m}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <PhaseRows
              phasen={draft.phasen}
              monate={monate}
              onCommit={commitProjectPhaseDrag}
              readOnly={draft.aus_teilprojekten}
              comments={cellComments(null)}
              onAddComment={(code, monat, text) => handleAddCellComment(null, code, monat, text)}
              onDeleteComment={handleDeleteComment}
            />
            <tr>
              <td className="label">FTE (Soll){draft.aus_teilprojekten && " (Σ Teilprojekte)"}</td>
              {monate.map((m) =>
                draft.aus_teilprojekten ? (
                  <td key={m} style={{ color: "var(--text-muted)" }}>
                    {draft.fte[m] !== undefined ? draft.fte[m].toFixed(2) : "–"}
                  </td>
                ) : (
                  <td key={m}>
                    <input
                      className="fte-input"
                      type="number"
                      step="0.1"
                      defaultValue={draft.fte[m] ?? ""}
                      onBlur={(e) => handleProjectFteChange(m, e.target.value)}
                    />
                  </td>
                ),
              )}
            </tr>
            {Object.keys(draft.ist).length > 0 && (
              <tr>
                <td className="label">FTE (Ist, Jira)</td>
                {monate.map((m) => (
                  <td key={m} style={{ color: "var(--text-muted)" }}>
                    {draft.ist[m] !== undefined ? draft.ist[m].toFixed(2) : "–"}
                  </td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Team-Zuordnung</h3>
        {draft.team_assignments.length === 0 && (
          <p style={{ color: "var(--text-muted)", margin: 0 }}>Noch niemand zugeordnet.</p>
        )}
        {draft.team_assignments.map((a) => (
          <span key={a.id} className="legend-chip" style={{ marginRight: "0.5rem" }}>
            {a.member_name} ({a.fte} FTE)
            <button
              type="button"
              onClick={() => handleDeleteTeamAssignment(a.id)}
              style={{ border: "none", background: "none", color: "var(--rot)", cursor: "pointer" }}
            >
              ×
            </button>
          </span>
        ))}
        <div className="field-row">
          <label>
            Teammitglied
            <select value={newAssignmentMemberId} onChange={(e) => setNewAssignmentMemberId(e.target.value)}>
              <option value="">— wählen —</option>
              {members
                .filter((m) => !draft.team_assignments.some((a) => a.team_member_id === m.id))
                .map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
            </select>
          </label>
          <label>
            FTE
            <input
              type="number"
              min={0.1}
              max={2}
              step={0.1}
              value={newAssignmentFte}
              onChange={(e) => setNewAssignmentFte(Number(e.target.value))}
            />
          </label>
          <button type="button" className="btn secondary" style={{ alignSelf: "flex-end" }} onClick={handleAddTeamAssignment}>
            + Zuordnen
          </button>
        </div>
      </div>

      {draft.subprojects.length > 0 && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Teilprojekte (optionale Feinplanung zusätzlich zur Grundplanung oben):
        </p>
      )}

      {draft.subprojects.map((sp) => (
        <div key={sp.id} className="card" style={{ marginBottom: "1.25rem", overflowX: "auto" }}>
          <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
            <h3 style={{ color: "var(--navy)", margin: 0 }}>{sp.name}</h3>
            <button
              type="button"
              className="btn secondary"
              style={{ color: "var(--rot)", borderColor: "var(--rot)" }}
              onClick={() => setSubprojectToDelete({ id: sp.id, name: sp.name })}
            >
              Teilprojekt löschen
            </button>
          </div>
          <table className="planner">
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Gantt-Phasen</th>
                {monate.map((m) => (
                  <th key={m}>{m}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <PhaseRows
                phasen={sp.phasen}
                monate={monate}
                onCommit={(code, changes) => commitSubprojectPhaseDrag(sp.id, code, changes)}
                comments={cellComments(sp.id)}
                onAddComment={(code, monat, text) => handleAddCellComment(sp.id, code, monat, text)}
                onDeleteComment={handleDeleteComment}
              />
              <tr>
                <td className="label">FTE (Soll)</td>
                {monate.map((m) => (
                  <td key={m}>
                    <input
                      className="fte-input"
                      type="number"
                      step="0.1"
                      defaultValue={sp.fte[m] ?? ""}
                      onBlur={(e) => handleFteChange(sp.id, m, e.target.value)}
                    />
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      ))}

      <form className="card" onSubmit={handleAddSubproject}>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Neues Teilprojekt
            <input
              required
              value={newSubprojectName}
              onChange={(e) => setNewSubprojectName(e.target.value)}
              placeholder="z. B. Rollout Nord"
            />
          </label>
        </div>
        <button className="btn" type="submit" style={{ marginTop: "0.75rem" }}>
          Teilprojekt hinzufügen
        </button>
      </form>

      <ConfirmDialog
        open={subprojectToDelete !== null}
        title="Teilprojekt löschen"
        message={`Teilprojekt "${subprojectToDelete?.name}" wirklich löschen? Gantt-Phasen und FTE-Werte gehen dabei verloren.`}
        onConfirm={handleDeleteSubproject}
        onCancel={() => setSubprojectToDelete(null)}
      />
    </div>
  );
}
