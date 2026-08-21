import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import ConfirmDialog from "../components/ConfirmDialog";
import { PROJECT_STATUS_LABELS } from "../types";
import type { ForecastSummary, GapStatus, ProjectStatus, ProjectSummary } from "../types";

export default function PortfolioDashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [gapByProject, setGapByProject] = useState<Record<number, GapStatus>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<{ id: number; name: string } | null>(null);
  const [dragId, setDragId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);

  const [name, setName] = useState("");
  const [kunde, setKunde] = useState("");
  const [startMonat, setStartMonat] = useState("04.2026");
  const [anzahlMonate, setAnzahlMonate] = useState(14);

  const load = () => {
    setLoading(true);
    api
      .listProjects()
      .then(setProjects)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
    api
      .getForecast()
      .then((rows: ForecastSummary[]) =>
        setGapByProject(Object.fromEntries(rows.map((r) => [r.project_id, r.status]))),
      )
      .catch(() => undefined); // Mini-Indikator ist optional, kein Blocker fürs Dashboard
  };

  useEffect(load, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.createProject({ name, kunde: kunde || undefined, start_monat: startMonat, anzahl_monate: anzahlMonate });
    setName("");
    setKunde("");
    setShowForm(false);
    load();
  };

  const handleDeleteProject = async () => {
    if (!projectToDelete) return;
    await api.deleteProject(projectToDelete.id);
    setProjectToDelete(null);
    load();
  };

  const handleStatusChange = async (projectId: number, status: ProjectStatus) => {
    await api.updateProject(projectId, { status });
    load();
  };

  const handleDrop = (targetId: number) => {
    const currentDragId = dragId;
    setDragId(null);
    setDragOverId(null);
    if (currentDragId === null || currentDragId === targetId) return;

    const ordered = [...projects];
    const fromIndex = ordered.findIndex((p) => p.id === currentDragId);
    const toIndex = ordered.findIndex((p) => p.id === targetId);
    if (fromIndex === -1 || toIndex === -1) return;
    const [moved] = ordered.splice(fromIndex, 1);
    ordered.splice(toIndex, 0, moved);
    setProjects(ordered);
    api.reorderProjects(ordered.map((p) => p.id)).catch((e) => {
      setError(String(e));
      load();
    });
  };

  return (
    <div>
      <div className="toolbar">
        <h2 className="section-title" style={{ margin: 0 }}>
          Projektmanagement-Dashboard
        </h2>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.85rem" }}>
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
            />
            Archivierte anzeigen
          </label>
          <a className="btn secondary" href={api.exportPortfolioPptxUrl()} style={{ marginRight: "0.5rem" }}>
            Portfolio als PPTX exportieren
          </a>
          <button className="btn" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Abbrechen" : "+ Neues Projekt"}
          </button>
        </div>
      </div>

      {showForm && (
        <form className="card" style={{ marginTop: "1rem" }} onSubmit={handleCreate}>
          <div className="field-row">
            <label>
              Projektname
              <input required value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label>
              Kunde
              <input value={kunde} onChange={(e) => setKunde(e.target.value)} />
            </label>
            <label>
              Startmonat (MM.YYYY)
              <input
                required
                pattern="\d{2}\.\d{4}"
                value={startMonat}
                onChange={(e) => setStartMonat(e.target.value)}
              />
            </label>
            <label>
              Anzahl Monate
              <input
                type="number"
                min={1}
                max={24}
                required
                value={anzahlMonate}
                onChange={(e) => setAnzahlMonate(Number(e.target.value))}
              />
            </label>
          </div>
          <button className="btn" type="submit" style={{ marginTop: "0.75rem" }}>
            Anlegen
          </button>
        </form>
      )}

      {loading && <p>Lade Projekte …</p>}
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}

      {!loading && !error && projects.length === 0 && (
        <div className="stub-view">Noch keine Projekte angelegt. Lege oben das erste Projekt an.</div>
      )}

      <div className="project-grid">
        {projects
          .filter((p) => showArchived || p.status !== "archiviert")
          .map((p) => (
          <div
            key={p.id}
            className={`project-card-wrapper${p.status === "on_hold" || p.status === "archiviert" ? " project-card-wrapper--muted" : ""}`}
            draggable
            onDragStart={() => setDragId(p.id)}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOverId(p.id);
            }}
            onDragLeave={() => setDragOverId((id) => (id === p.id ? null : id))}
            onDrop={(e) => {
              e.preventDefault();
              handleDrop(p.id);
            }}
            onDragEnd={() => {
              setDragId(null);
              setDragOverId(null);
            }}
            style={{
              outline: dragOverId === p.id && dragId !== p.id ? "2px solid var(--blau)" : "none",
              outlineOffset: "-2px",
            }}
          >
            <Link to={`/projekte/${p.id}`} className="project-card card">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.5rem" }}>
                <h3 style={{ margin: 0 }}>{p.name}</h3>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexShrink: 0 }}>
                  {p.status !== "aktiv" && (
                    <span className={`project-status-badge project-status-badge--${p.status}`}>
                      {PROJECT_STATUS_LABELS[p.status]}
                    </span>
                  )}
                  {gapByProject[p.id] && (
                    <span
                      className={`gap-status-dot gap-dot--${gapByProject[p.id]}`}
                      style={{ width: "10px", height: "10px", flexShrink: 0 }}
                      title={`Gap-Analyse: ${gapByProject[p.id]}`}
                    />
                  )}
                </div>
              </div>
              <p className="kunde">{p.kunde || " "}</p>
              <p className="zeitraum">
                {p.monate[0]} – {p.monate[p.monate.length - 1]}
              </p>
            </Link>
            <select
              className="project-status-select"
              value={p.status}
              title="Projekt-Status ändern"
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => handleStatusChange(p.id, e.target.value as ProjectStatus)}
            >
              {Object.entries(PROJECT_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="project-card-delete"
              draggable={false}
              title="Projekt löschen"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                setProjectToDelete({ id: p.id, name: p.name });
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <ConfirmDialog
        open={projectToDelete !== null}
        title="Projekt löschen"
        message={`Projekt "${projectToDelete?.name}" wirklich löschen? Alle Teilprojekte, Planungsdaten und Team-Zuordnungen dieses Projekts gehen dabei unwiderruflich verloren.`}
        onConfirm={handleDeleteProject}
        onCancel={() => setProjectToDelete(null)}
      />
    </div>
  );
}
