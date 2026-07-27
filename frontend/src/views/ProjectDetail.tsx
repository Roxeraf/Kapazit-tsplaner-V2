import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import {
  PHASE_COLORS,
  PHASE_LABELS,
  type JiraComponent,
  type JiraProject,
  type PhaseCode,
  type ProjectDetail as ProjectDetailT,
} from "../types";

const PHASE_CODES: PhaseCode[] = ["p", "k", "t", "s", "g", "?"];
const ROW_HEIGHT = 38;
const BAR_HEIGHT = 20;

export default function ProjectDetail() {
  const { id } = useParams();
  const projectId = Number(id);
  const [project, setProject] = useState<ProjectDetailT | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newSubprojectName, setNewSubprojectName] = useState("");
  const [jiraConfigured, setJiraConfigured] = useState(false);
  const [relevantJiraProjects, setRelevantJiraProjects] = useState<JiraProject[]>([]);
  const [pickerJiraProjectKey, setPickerJiraProjectKey] = useState("");
  const [pickerComponents, setPickerComponents] = useState<JiraComponent[]>([]);
  const [pickerLabels, setPickerLabels] = useState<string[]>([]);
  const [subprojectToDelete, setSubprojectToDelete] = useState<{ id: number; name: string } | null>(null);

  const load = () => {
    api
      .getProject(projectId)
      .then(setProject)
      .catch((e) => setError(String(e)));
  };

  useEffect(load, [projectId]);

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
    if (project?.jira_project_key && jiraConfigured && pickerJiraProjectKey !== project.jira_project_key) {
      handlePickerJiraProjectChange(project.jira_project_key);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project?.jira_project_key, jiraConfigured]);

  const linkedJiraProjectName =
    relevantJiraProjects.find((p) => p.key === project?.jira_project_key)?.name ?? project?.jira_project_key;

  const handleFteChange = async (subprojectId: number, monat: string, raw: string) => {
    const value = Number(raw);
    await api.setFte(subprojectId, monat, Number.isFinite(value) ? value : 0);
    load();
  };

  // Ein Klick ist ein Drag der Länge 1: beides läuft über denselben Commit-Pfad, der erst am
  // Ende (mouseup) die betroffenen Monate nacheinander speichert und dann einmal neu lädt —
  // sonst würde jede Zelle während des Ziehens einen eigenen Request+Reload auslösen.
  const commitProjectPhaseDrag = async (code: PhaseCode, changes: Record<string, boolean>) => {
    if (!project) return;
    for (const [monat, makeActive] of Object.entries(changes)) {
      const current = project.phasen[monat] ?? [];
      if (current.includes(code) === makeActive) continue;
      const next = makeActive ? [...current, code] : current.filter((c) => c !== code);
      await api.setProjectPhasen(project.id, monat, next);
    }
    load();
  };

  const commitSubprojectPhaseDrag = async (
    subprojectId: number,
    phasen: Record<string, PhaseCode[]>,
    code: PhaseCode,
    changes: Record<string, boolean>,
  ) => {
    for (const [monat, makeActive] of Object.entries(changes)) {
      const current = phasen[monat] ?? [];
      if (current.includes(code) === makeActive) continue;
      const next = makeActive ? [...current, code] : current.filter((c) => c !== code);
      await api.setPhasen(subprojectId, monat, next);
    }
    load();
  };

  const handleProjectFteChange = async (monat: string, raw: string) => {
    if (!project) return;
    const value = Number(raw);
    await api.setProjectFte(project.id, monat, Number.isFinite(value) ? value : 0);
    load();
  };

  const handleJiraComponentChange = async (raw: string) => {
    if (!project) return;
    await api.updateProject(project.id, { jira_component: raw.trim() || null });
    load();
  };

  const handleProjectFieldChange = async (
    field: "name" | "kunde" | "start_monat" | "anzahl_monate",
    raw: string,
  ) => {
    if (!project) return;
    if (field === "anzahl_monate") {
      const value = Number(raw);
      if (!Number.isFinite(value) || value < 1) return;
      await api.updateProject(project.id, { anzahl_monate: value });
    } else if (field === "kunde") {
      await api.updateProject(project.id, { kunde: raw.trim() || null });
    } else if (field === "start_monat") {
      if (!/^\d{2}\.\d{4}$/.test(raw)) return;
      await api.updateProject(project.id, { start_monat: raw });
    } else {
      if (!raw.trim()) return;
      await api.updateProject(project.id, { name: raw.trim() });
    }
    load();
  };

  const handleAddSubproject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!project) return;
    await api.createSubproject(project.id, newSubprojectName, project.subprojects.length);
    setNewSubprojectName("");
    load();
  };

  const handleDeleteSubproject = async () => {
    if (!subprojectToDelete) return;
    await api.deleteSubproject(subprojectToDelete.id);
    setSubprojectToDelete(null);
    load();
  };

  if (error) return <p style={{ color: "var(--rot)" }}>{error}</p>;
  if (!project) return <p>Lade Projekt …</p>;

  const monate = project.monate;

  return (
    <div>
      <div className="toolbar">
        <div>
          <h2 className="section-title" style={{ margin: 0 }}>
            {project.name}
          </h2>
          {project.kunde && <p style={{ color: "var(--text-muted)", margin: "0.2rem 0" }}>{project.kunde}</p>}
        </div>
        <a className="btn" href={api.exportPptxUrl(project.id)}>
          Als PPTX exportieren
        </a>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div className="field-row" style={{ marginTop: 0 }}>
          <label>
            Projektname
            <input key={project.name} defaultValue={project.name} onBlur={(e) => handleProjectFieldChange("name", e.target.value)} />
          </label>
          <label>
            Kunde
            <input
              key={project.kunde ?? ""}
              defaultValue={project.kunde ?? ""}
              onBlur={(e) => handleProjectFieldChange("kunde", e.target.value)}
            />
          </label>
          <label>
            Startmonat (MM.YYYY)
            <input
              key={project.start_monat}
              defaultValue={project.start_monat}
              pattern="\d{2}\.\d{4}"
              onBlur={(e) => handleProjectFieldChange("start_monat", e.target.value)}
            />
          </label>
          <label>
            Anzahl Monate
            <input
              key={project.anzahl_monate}
              type="number"
              min={1}
              max={24}
              defaultValue={project.anzahl_monate}
              onBlur={(e) => handleProjectFieldChange("anzahl_monate", e.target.value)}
            />
          </label>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", gap: "0.4rem", alignItems: "center" }}>
          Jira-Komponente/Label (für Ist-FTE des gesamten Projekts)
          <input
            key={project.jira_component ?? ""}
            style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px" }}
            defaultValue={project.jira_component ?? ""}
            placeholder="z. B. ETE"
            onBlur={(e) => handleJiraComponentChange(e.target.value)}
          />
        </label>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", margin: "0.35rem 0 0" }}>
          {project.jira_component ? (
            <>
              Aktuell gespeichert: <strong>{project.jira_component}</strong>
            </>
          ) : (
            "Noch nichts gespeichert — ohne Wert bleibt die Ist-FTE-Berechnung für dieses Projekt leer."
          )}
        </p>
        {jiraConfigured && (
          <div className="field-row" style={{ marginTop: "0.5rem" }}>
            {project.jira_project_key ? (
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", alignSelf: "flex-end" }}>
                Verknüpft mit Jira-Projekt: {linkedJiraProjectName} ({project.jira_project_key})
              </span>
            ) : (
              <label>
                Oder aus Jira-Projekt wählen
                <select
                  value={pickerJiraProjectKey}
                  onChange={(e) => handlePickerJiraProjectChange(e.target.value)}
                >
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
                  value={project.jira_component ?? ""}
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
        {project.aus_teilprojekten && (
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
              phasen={project.phasen}
              monate={monate}
              onCommit={commitProjectPhaseDrag}
              readOnly={project.aus_teilprojekten}
            />
            <tr>
              <td className="label">FTE (Soll){project.aus_teilprojekten && " (Σ Teilprojekte)"}</td>
              {monate.map((m) =>
                project.aus_teilprojekten ? (
                  <td key={m} style={{ color: "var(--text-muted)" }}>
                    {project.fte[m] !== undefined ? project.fte[m].toFixed(2) : "–"}
                  </td>
                ) : (
                  <td key={m}>
                    <input
                      className="fte-input"
                      type="number"
                      step="0.1"
                      defaultValue={project.fte[m] ?? ""}
                      onBlur={(e) => handleProjectFteChange(m, e.target.value)}
                    />
                  </td>
                ),
              )}
            </tr>
            {Object.keys(project.ist).length > 0 && (
              <tr>
                <td className="label">FTE (Ist, Jira)</td>
                {monate.map((m) => (
                  <td key={m} style={{ color: "var(--text-muted)" }}>
                    {project.ist[m] !== undefined ? project.ist[m].toFixed(2) : "–"}
                  </td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {project.subprojects.length > 0 && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Teilprojekte (optionale Feinplanung zusätzlich zur Grundplanung oben):
        </p>
      )}

      {project.subprojects.map((sp) => (
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
                onCommit={(code, changes) => commitSubprojectPhaseDrag(sp.id, sp.phasen, code, changes)}
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
}: {
  phasen: Record<string, PhaseCode[]>;
  monate: string[];
  onCommit: (code: PhaseCode, changes: Record<string, boolean>) => void;
  readOnly?: boolean;
}) {
  const [drag, setDrag] = useState<Drag | null>(null);

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
            return (
              <td key={m} style={{ height: ROW_HEIGHT, padding: 0, border: "none", borderBottom: "1px solid var(--border)" }}>
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
              </td>
            );
          })}
        </tr>
      ))}
    </>
  );
}
