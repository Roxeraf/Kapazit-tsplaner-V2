import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import HistoryPanel from "../components/HistoryPanel";
import NotesSection from "../components/NotesSection";
import { useUnsavedChanges } from "../unsavedChanges";
import {
  PHASE_COLORS,
  PHASE_LABELS,
  type Comment,
  type JiraComponent,
  type JiraProject,
  type PhaseCode,
  type PlanHistoryEntry,
  type ProjectDetail as ProjectDetailT,
  type TeamMember,
} from "../types";

const PHASE_CODES: PhaseCode[] = ["p", "k", "t", "s", "g", "?"];
const ROW_HEIGHT = 38;
const BAR_HEIGHT = 20;

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

export default function ProjectDetail() {
  const { id } = useParams();
  const projectId = Number(id);
  const navigate = useNavigate();
  const { isDirty, setIsDirty } = useUnsavedChanges();

  const [saved, setSaved] = useState<ProjectDetailT | null>(null);
  const [draft, setDraft] = useState<ProjectDetailT | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [saveReason, setSaveReason] = useState("");
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);

  const [comments, setComments] = useState<Comment[]>([]);
  const [newSubprojectName, setNewSubprojectName] = useState("");
  const [jiraConfigured, setJiraConfigured] = useState(false);
  const [relevantJiraProjects, setRelevantJiraProjects] = useState<JiraProject[]>([]);
  const [pickerJiraProjectKey, setPickerJiraProjectKey] = useState("");
  const [pickerComponents, setPickerComponents] = useState<JiraComponent[]>([]);
  const [pickerLabels, setPickerLabels] = useState<string[]>([]);
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

  useEffect(() => {
    api
      .jiraStatus()
      .then((status) => {
        setJiraConfigured(status.configured);
        if (!status.configured) return;
        return api.jiraListProjects().then((all) => setRelevantJiraProjects(all.filter((p) => p.relevant)));
      })
      .catch(() => setJiraConfigured(false));
  }, []);

  const handlePickerJiraProjectChange = async (key: string) => {
    setPickerJiraProjectKey(key);
    setPickerComponents([]);
    setPickerLabels([]);
    if (!key) return;
    try {
      const [components, labels] = await Promise.all([api.jiraListComponents(key), api.jiraListLabels(key)]);
      setPickerComponents(components);
      setPickerLabels(labels);
    } catch (e) {
      setError(String(e));
    }
  };

  // Wenn das Projekt schon aus einem aktivierten Jira-Projekt entstanden ist (siehe
  // "Jira-Projekte"-Seite), ist die Zuordnung bereits klar — nicht nochmal danach fragen,
  // direkt die Components davon laden.
  useEffect(() => {
    if (draft?.jira_project_key && jiraConfigured && pickerJiraProjectKey !== draft.jira_project_key) {
      handlePickerJiraProjectChange(draft.jira_project_key);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft?.jira_project_key, jiraConfigured]);

  const linkedJiraProjectName =
    relevantJiraProjects.find((p) => p.key === draft?.jira_project_key)?.name ?? draft?.jira_project_key;

  // Strukturelle Aktionen (Teilprojekt anlegen/löschen, Team-Zuordnung, Jira-Verknüpfung)
  // bleiben sofort wirksam und laden das Projekt neu - das würde unentdeckte, ungespeicherte
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
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleBack = () => {
    if (isDirty) {
      setShowLeaveConfirm(true);
    } else {
      navigate("/");
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

  const handleAddNote = async (subprojectId: number | null, text: string) => {
    await api.createComment(projectId, { subproject_id: subprojectId, text });
    refreshComments();
  };

  const handleJiraComponentChange = async (raw: string) => {
    if (!draft || !confirmDiscardIfDirty()) return;
    await api.updateProject(draft.id, { jira_component: raw.trim() || null });
    load();
  };

  const handleAddSubproject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!draft || !confirmDiscardIfDirty()) return;
    await api.createSubproject(draft.id, newSubprojectName, draft.subprojects.length);
    setNewSubprojectName("");
    load();
  };

  const handleDeleteSubproject = async () => {
    if (!subprojectToDelete || !confirmDiscardIfDirty()) return;
    await api.deleteSubproject(subprojectToDelete.id);
    setSubprojectToDelete(null);
    load();
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

  if (error) return <p style={{ color: "var(--rot)" }}>{error}</p>;
  if (!draft) return <p>Lade Projekt …</p>;

  const monate = draft.monate;
  const generalComments = (subprojectId: number | null) =>
    comments.filter((c) => c.subproject_id === subprojectId && c.monat === null && c.phase_code === null);
  const cellComments = (subprojectId: number | null) =>
    comments.filter((c) => c.subproject_id === subprojectId && c.monat !== null && c.phase_code !== null);

  return (
    <div>
      <div className="toolbar">
        <div>
          <button type="button" className="btn secondary" onClick={handleBack} style={{ marginBottom: "0.5rem" }}>
            ← Zurück
          </button>
          <h2 className="section-title" style={{ margin: 0 }}>
            {draft.name}
          </h2>
          {draft.kunde && <p style={{ color: "var(--text-muted)", margin: "0.2rem 0" }}>{draft.kunde}</p>}
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {isDirty && <span style={{ color: "var(--rot)", fontSize: "0.85rem" }}>● Ungespeicherte Änderungen</span>}
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
          <a className="btn secondary" href={api.exportPptxUrl(draft.id)}>
            Als PPTX exportieren
          </a>
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

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", gap: "0.4rem", alignItems: "center" }}>
          Jira-Komponente/Label (für Ist-FTE des gesamten Projekts)
          <input
            key={draft.jira_component ?? ""}
            style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px" }}
            defaultValue={draft.jira_component ?? ""}
            placeholder="z. B. ETE"
            onBlur={(e) => handleJiraComponentChange(e.target.value)}
          />
        </label>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.35rem 0 0" }}>
          {draft.jira_component ? (
            <>
              Aktuell gespeichert: <strong>{draft.jira_component}</strong>
            </>
          ) : (
            "Noch nichts gespeichert — ohne Wert bleibt die Ist-FTE-Berechnung für dieses Projekt leer."
          )}
        </p>
        {jiraConfigured && (
          <div className="field-row" style={{ marginTop: "0.5rem" }}>
            {draft.jira_project_key ? (
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", alignSelf: "flex-end" }}>
                Verknüpft mit Jira-Projekt: {linkedJiraProjectName} ({draft.jira_project_key})
              </span>
            ) : (
              <label>
                Oder aus Jira-Projekt wählen
                <select value={pickerJiraProjectKey} onChange={(e) => handlePickerJiraProjectChange(e.target.value)}>
                  <option value="">
                    {relevantJiraProjects.length === 0
                      ? "— keine Jira-Projekte als 'wird geplant' markiert —"
                      : "— Jira-Projekt wählen —"}
                  </option>
                  {relevantJiraProjects.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.name} ({p.key})
                    </option>
                  ))}
                </select>
              </label>
            )}
            {pickerJiraProjectKey && (
              <label>
                Komponente/Label
                <select
                  value={draft.jira_component ?? ""}
                  onChange={(e) => {
                    if (e.target.value) handleJiraComponentChange(e.target.value);
                  }}
                >
                  <option value="">— wählen —</option>
                  {pickerComponents.length > 0 && (
                    <optgroup label="Components">
                      {pickerComponents.map((c) => (
                        <option key={`c-${c.id}`} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                    </optgroup>
                  )}
                  {pickerLabels.length > 0 && (
                    <optgroup label="Labels">
                      {pickerLabels.map((l) => (
                        <option key={`l-${l}`} value={l}>
                          {l}
                        </option>
                      ))}
                    </optgroup>
                  )}
                  {pickerComponents.length === 0 && pickerLabels.length === 0 && (
                    <option value="" disabled>
                      Keine Components oder Labels in diesem Jira-Projekt gefunden
                    </option>
                  )}
                </select>
              </label>
            )}
          </div>
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

        <details style={{ marginTop: "0.75rem" }}>
          <summary style={{ cursor: "pointer", color: "var(--navy)" }}>Notizen</summary>
          <NotesSection notes={generalComments(null)} onAdd={(text) => handleAddNote(null, text)} />
        </details>
        <ProjectHistorySection projectId={draft.id} />
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

          <details style={{ marginTop: "0.75rem" }}>
            <summary style={{ cursor: "pointer", color: "var(--navy)" }}>Notizen</summary>
            <NotesSection notes={generalComments(sp.id)} onAdd={(text) => handleAddNote(sp.id, text)} />
          </details>
          <SubprojectHistorySection subprojectId={sp.id} />
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

      <ConfirmDialog
        open={showLeaveConfirm}
        title="Projekt verlassen"
        message="Ungespeicherte Planungsänderungen gehen verloren, wenn du jetzt zurück zum Portfolio gehst."
        confirmLabel="Verlassen"
        onConfirm={() => {
          setIsDirty(false);
          setShowLeaveConfirm(false);
          navigate("/");
        }}
        onCancel={() => setShowLeaveConfirm(false)}
      />
    </div>
  );
}

function ProjectHistorySection({ projectId }: { projectId: number }) {
  const [entries, setEntries] = useState<PlanHistoryEntry[] | null>(null);
  return (
    <details style={{ marginTop: "0.75rem" }} onToggle={(e) => {
      if ((e.target as HTMLDetailsElement).open && entries === null) {
        api.getProjectHistory(projectId).then(setEntries).catch(() => setEntries([]));
      }
    }}>
      <summary style={{ cursor: "pointer", color: "var(--navy)" }}>Verlauf</summary>
      <HistoryPanel entries={entries ?? []} />
    </details>
  );
}

function SubprojectHistorySection({ subprojectId }: { subprojectId: number }) {
  const [entries, setEntries] = useState<PlanHistoryEntry[] | null>(null);
  return (
    <details style={{ marginTop: "0.75rem" }} onToggle={(e) => {
      if ((e.target as HTMLDetailsElement).open && entries === null) {
        api.getSubprojectHistory(subprojectId).then(setEntries).catch(() => setEntries([]));
      }
    }}>
      <summary style={{ cursor: "pointer", color: "var(--navy)" }}>Verlauf</summary>
      <HistoryPanel entries={entries ?? []} />
    </details>
  );
}

interface Drag {
  code: PhaseCode;
  makeActive: boolean;
  changes: Record<string, boolean>;
}

function PhaseRows({
  phasen,
  monate,
  onCommit,
  readOnly = false,
  comments,
  onAddComment,
}: {
  phasen: Record<string, PhaseCode[]>;
  monate: string[];
  onCommit: (code: PhaseCode, changes: Record<string, boolean>) => void;
  readOnly?: boolean;
  comments: Comment[];
  onAddComment: (code: PhaseCode, monat: string, text: string) => void;
}) {
  const [drag, setDrag] = useState<Drag | null>(null);
  const [commentTarget, setCommentTarget] = useState<{ code: PhaseCode; monat: string } | null>(null);
  const [commentDraft, setCommentDraft] = useState("");

  // Drag endet, sobald die Maustaste irgendwo losgelassen wird (auch außerhalb der Tabelle).
  useEffect(() => {
    if (!drag) return;
    const finish = () => {
      onCommit(drag.code, drag.changes);
      setDrag(null);
    };
    window.addEventListener("mouseup", finish);
    return () => window.removeEventListener("mouseup", finish);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drag]);

  const isActive = (code: PhaseCode, monat: string) => {
    if (drag && drag.code === code && monat in drag.changes) return drag.changes[monat];
    return (phasen[monat] ?? []).includes(code);
  };

  const startDrag = (code: PhaseCode, monat: string) => {
    if (readOnly) return;
    const makeActive = !(phasen[monat] ?? []).includes(code);
    setDrag({ code, makeActive, changes: { [monat]: makeActive } });
  };

  const enterDrag = (code: PhaseCode, monat: string) => {
    if (!drag || drag.code !== code || monat in drag.changes) return;
    setDrag({ ...drag, changes: { ...drag.changes, [monat]: drag.makeActive } });
  };

  const commentsFor = (code: PhaseCode, monat: string) =>
    comments.filter((c) => c.phase_code === code && c.monat === monat);

  const handleSaveComment = () => {
    if (!commentTarget || !commentDraft.trim()) return;
    onAddComment(commentTarget.code, commentTarget.monat, commentDraft.trim());
    setCommentDraft("");
    setCommentTarget(null);
  };

  return (
    <>
      {PHASE_CODES.map((code) => (
        <tr key={code} style={{ height: ROW_HEIGHT }}>
          <td className="label" style={{ height: ROW_HEIGHT, padding: "0 0.4rem" }}>
            <span className="legend-swatch" style={{ background: PHASE_COLORS[code], marginRight: "0.4rem" }} />
            {PHASE_LABELS[code]}
          </td>
          {monate.map((m, i) => {
            const active = isActive(code, m);
            const prevActive = i > 0 && isActive(code, monate[i - 1]);
            const nextActive = i < monate.length - 1 && isActive(code, monate[i + 1]);
            const hasComment = commentsFor(code, m).length > 0;
            return (
              <td
                key={m}
                style={{ height: ROW_HEIGHT, padding: 0, border: "none", borderBottom: "1px solid var(--border)", position: "relative" }}
              >
                <button
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    startDrag(code, m);
                  }}
                  onMouseEnter={() => enterDrag(code, m)}
                  aria-label={`${PHASE_LABELS[code]} ${m} ${active ? "entfernen" : "setzen"}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "stretch",
                    width: "100%",
                    height: ROW_HEIGHT,
                    border: "none",
                    background: "transparent",
                    padding: 0,
                    cursor: readOnly ? "default" : "pointer",
                    userSelect: "none",
                  }}
                >
                  <span
                    style={{
                      display: "block",
                      width: "100%",
                      height: active ? BAR_HEIGHT : 0,
                      background: active ? PHASE_COLORS[code] : "transparent",
                      borderTopLeftRadius: active && !prevActive ? "5px" : 0,
                      borderBottomLeftRadius: active && !prevActive ? "5px" : 0,
                      borderTopRightRadius: active && !nextActive ? "5px" : 0,
                      borderBottomRightRadius: active && !nextActive ? "5px" : 0,
                      transition: "all 180ms cubic-bezier(0.4, 0, 0.2, 1)",
                    }}
                  />
                </button>
                <button
                  type="button"
                  title="Kommentar"
                  onClick={(e) => {
                    e.stopPropagation();
                    setCommentTarget({ code, monat: m });
                    setCommentDraft("");
                  }}
                  style={{
                    position: "absolute",
                    top: 1,
                    right: 1,
                    width: 12,
                    height: 12,
                    lineHeight: "12px",
                    fontSize: "9px",
                    padding: 0,
                    border: "none",
                    borderRadius: "50%",
                    background: hasComment ? "var(--rot)" : "transparent",
                    color: hasComment ? "#fff" : "var(--text-muted)",
                    opacity: hasComment ? 1 : 0.4,
                    cursor: "pointer",
                  }}
                >
                  💬
                </button>
              </td>
            );
          })}
        </tr>
      ))}

      {commentTarget && (
        <tr>
          <td colSpan={monate.length + 1} style={{ border: "none", padding: 0 }}>
            <div
              onClick={() => setCommentTarget(null)}
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0, 20, 40, 0.45)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 1000,
              }}
            >
              <div onClick={(e) => e.stopPropagation()} className="card" style={{ maxWidth: "26rem", width: "90%" }}>
                <h3 style={{ color: "var(--navy)", marginTop: 0 }}>
                  {PHASE_LABELS[commentTarget.code]} – {commentTarget.monat}
                </h3>
                {commentsFor(commentTarget.code, commentTarget.monat).length === 0 ? (
                  <p style={{ color: "var(--text-muted)" }}>Noch keine Kommentare.</p>
                ) : (
                  <ul style={{ listStyle: "none", padding: 0, margin: "0 0 0.75rem" }}>
                    {commentsFor(commentTarget.code, commentTarget.monat).map((c) => (
                      <li key={c.id} style={{ padding: "0.35rem 0", borderBottom: "1px solid var(--border)" }}>
                        {c.text}
                      </li>
                    ))}
                  </ul>
                )}
                <textarea
                  value={commentDraft}
                  onChange={(e) => setCommentDraft(e.target.value)}
                  placeholder="z. B. verzögert wegen fehlender Kundenunterschrift"
                  rows={3}
                  style={{ width: "100%", resize: "vertical" }}
                />
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "0.75rem" }}>
                  <button type="button" className="btn secondary" onClick={() => setCommentTarget(null)}>
                    Schließen
                  </button>
                  <button type="button" className="btn" onClick={handleSaveComment}>
                    Kommentar hinzufügen
                  </button>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
