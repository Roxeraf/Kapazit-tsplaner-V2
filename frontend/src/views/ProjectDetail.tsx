import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import {
  PHASE_COLORS,
  PHASE_LABELS,
  type JiraComponent,
  type JiraProject,
  type PhaseCode,
  type ProjectDetail as ProjectDetailT,
} from "../types";

const PHASE_CODES: PhaseCode[] = ["p", "k", "t", "s", "g", "?"];

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
    if (!key) return;
    try {
      setPickerComponents(await api.jiraListComponents(key));
    } catch (e) {
      setError(String(e));
    }
  };

  const handlePhaseChange = async (subprojectId: number, monat: string, raw: string) => {
    const codes = raw
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean) as PhaseCode[];
    await api.setPhasen(subprojectId, monat, codes);
    load();
  };

  const handleFteChange = async (subprojectId: number, monat: string, raw: string) => {
    const value = Number(raw);
    await api.setFte(subprojectId, monat, Number.isFinite(value) ? value : 0);
    load();
  };

  const handleProjectPhaseChange = async (monat: string, raw: string) => {
    if (!project) return;
    const codes = raw
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean) as PhaseCode[];
    await api.setProjectPhasen(project.id, monat, codes);
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

  const handleAddSubproject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!project) return;
    await api.createSubproject(project.id, newSubprojectName, project.subprojects.length);
    setNewSubprojectName("");
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
        <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", gap: "0.4rem", alignItems: "center" }}>
          Jira-Komponente/Label (für Ist-FTE des gesamten Projekts)
          <input
            style={{ padding: "0.3rem 0.5rem", border: "1px solid var(--border)", borderRadius: "4px" }}
            defaultValue={project.jira_component ?? ""}
            placeholder="z. B. ETE"
            onBlur={(e) => handleJiraComponentChange(e.target.value)}
          />
        </label>
        {jiraConfigured && (
          <div className="field-row" style={{ marginTop: "0.5rem" }}>
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
            {pickerJiraProjectKey && (
              <label>
                Komponente
                <select
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) handleJiraComponentChange(e.target.value);
                  }}
                >
                  <option value="">— Komponente wählen —</option>
                  {pickerComponents.map((c) => (
                    <option key={c.id} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
        )}
      </div>

      <div className="legend-row">
        {PHASE_CODES.map((code) => (
          <span key={code} className="legend-chip">
            <span className="legend-swatch" style={{ background: PHASE_COLORS[code] }} />
            {code} = {PHASE_LABELS[code]}
          </span>
        ))}
        <span className="legend-chip">Mehrere Phasen im selben Monat: kommagetrennt eintragen, z. B. "k,t"</span>
      </div>

      <div className="card" style={{ marginBottom: "1.25rem", overflowX: "auto" }}>
        <div className="toolbar" style={{ marginBottom: "0.5rem" }}>
          <h3 style={{ color: "var(--navy)", margin: 0 }}>Projekt gesamt</h3>
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
            <tr>
              <td className="label">Phasencode(s)</td>
              {monate.map((m) => (
                <td key={m}>
                  <input
                    className="phase-input"
                    defaultValue={(project.phasen[m] ?? []).join(",")}
                    onBlur={(e) => handleProjectPhaseChange(m, e.target.value)}
                  />
                </td>
              ))}
            </tr>
            <tr>
              <td className="label">FTE (Soll)</td>
              {monate.map((m) => (
                <td key={m}>
                  <input
                    className="fte-input"
                    type="number"
                    step="0.1"
                    defaultValue={project.fte[m] ?? ""}
                    onBlur={(e) => handleProjectFteChange(m, e.target.value)}
                  />
                </td>
              ))}
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
              <tr>
                <td className="label">Phasencode(s)</td>
                {monate.map((m) => (
                  <td key={m}>
                    <input
                      className="phase-input"
                      defaultValue={(sp.phasen[m] ?? []).join(",")}
                      onBlur={(e) => handlePhaseChange(sp.id, m, e.target.value)}
                    />
                  </td>
                ))}
              </tr>
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
    </div>
  );
}
