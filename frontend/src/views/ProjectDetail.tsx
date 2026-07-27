import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { PHASE_COLORS, PHASE_LABELS, type PhaseCode, type ProjectDetail as ProjectDetailT } from "../types";

const PHASE_CODES: PhaseCode[] = ["p", "k", "t", "g", "?"];

export default function ProjectDetail() {
  const { id } = useParams();
  const projectId = Number(id);
  const [project, setProject] = useState<ProjectDetailT | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newSubprojectName, setNewSubprojectName] = useState("");

  const load = () => {
    api
      .getProject(projectId)
      .then(setProject)
      .catch((e) => setError(String(e)));
  };

  useEffect(load, [projectId]);

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

      <div className="legend-row">
        {PHASE_CODES.map((code) => (
          <span key={code} className="legend-chip">
            <span className="legend-swatch" style={{ background: PHASE_COLORS[code] }} />
            {code} = {PHASE_LABELS[code]}
          </span>
        ))}
        <span className="legend-chip">Mehrere Phasen im selben Monat: kommagetrennt eintragen, z. B. "k,t"</span>
      </div>

      {project.subprojects.map((sp) => (
        <div key={sp.id} className="card" style={{ marginBottom: "1.25rem", overflowX: "auto" }}>
          <h3 style={{ color: "var(--navy)", marginTop: 0 }}>{sp.name}</h3>
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
