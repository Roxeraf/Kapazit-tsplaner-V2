import { useEffect, useState } from "react";
import { Outlet, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api/client";
import ConfirmDialog from "../../components/ConfirmDialog";
import Tabs from "../../components/Tabs";
import { useUnsavedChanges } from "../../unsavedChanges";
import { useGuardedNavigate } from "../../useGuardedNavigate";
import type { ProjectDetail } from "../../types";

const TAB_ITEMS = [
  { to: "uebersicht", label: "Übersicht" },
  { to: "planung", label: "Planung" },
  { to: "kommunikation", label: "Kommunikation" },
  { to: "dokumente", label: "Dokumente" },
  { to: "historie", label: "Historie" },
  { to: "jira", label: "Jira" },
  { to: "einstellungen", label: "Einstellungen" },
];

export default function ProjectWorkspace() {
  const { id } = useParams();
  const projectId = Number(id);
  const navigate = useNavigate();
  const { isDirty, setIsDirty } = useUnsavedChanges();
  const guardedNavigate = useGuardedNavigate();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);

  const reload = () => {
    api
      .getProject(projectId)
      .then(setProject)
      .catch((e) => setError(String(e)));
  };

  useEffect(reload, [projectId]);

  const handleBack = () => {
    if (isDirty) {
      setShowLeaveConfirm(true);
    } else {
      navigate("/");
    }
  };

  if (!project) return <p>Lade Projekt …</p>;

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
      <div className="toolbar">
        <div>
          <button type="button" className="btn secondary" onClick={handleBack} style={{ marginBottom: "0.5rem" }}>
            ← Zurück
          </button>
          <h2 className="section-title" style={{ margin: 0 }}>
            {project.name}
          </h2>
          {project.kunde && <p style={{ color: "var(--text-muted)", margin: "0.2rem 0" }}>{project.kunde}</p>}
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          {isDirty && <span style={{ color: "var(--rot)", fontSize: "0.85rem" }}>● Ungespeicherte Änderungen</span>}
          <a className="btn secondary" href={api.exportPptxUrl(project.id)}>
            Als PPTX exportieren
          </a>
        </div>
      </div>

      <Tabs items={TAB_ITEMS} guardedNavigate={guardedNavigate} />

      <Outlet context={{ project, reload }} />

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
