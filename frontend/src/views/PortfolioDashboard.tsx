import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ProjectSummary } from "../types";

export default function PortfolioDashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

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

  return (
    <div>
      <div className="toolbar">
        <h2 className="section-title" style={{ margin: 0 }}>
          Portfolio-Dashboard
        </h2>
        <div>
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
        {projects.map((p) => (
          <Link key={p.id} to={`/projekte/${p.id}`} className="project-card card">
            <h3>{p.name}</h3>
            {p.kunde && <p className="kunde">{p.kunde}</p>}
            <p className="zeitraum">
              {p.monate[0]} – {p.monate[p.monate.length - 1]}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
