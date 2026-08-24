import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { PlanHistoryEntry } from "../../types";
import HistoryTimeline from "./components/HistoryTimeline";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

export default function ProjectHistoryTab() {
  const { project } = useProjectWorkspace();
  const [entries, setEntries] = useState<PlanHistoryEntry[]>([]);

  useEffect(() => {
    api.getProjectHistory(project.id).then(setEntries).catch(() => setEntries([]));
  }, [project.id]);

  return (
    <div className="card" style={{ maxHeight: "70vh", overflowY: "auto" }}>
      <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Historie</h3>
      <p style={{ color: "var(--text-muted)", fontSize: "0.82rem", marginTop: 0 }}>
        Automatisches, unveränderliches Protokoll fachlich relevanter Projektänderungen. Es
        ist keine zusätzliche Aktion nötig — der User plant, das System dokumentiert.
      </p>
      <HistoryTimeline entries={entries} />
    </div>
  );
}
