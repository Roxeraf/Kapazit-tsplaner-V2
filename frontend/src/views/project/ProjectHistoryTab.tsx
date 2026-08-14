import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { PlanHistoryEntry } from "../../types";
import HistoryTimeline from "./components/HistoryTimeline";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

function SubprojectHistorySection({ subprojectId, name }: { subprojectId: number; name: string }) {
  const [entries, setEntries] = useState<PlanHistoryEntry[]>([]);
  useEffect(() => {
    api.getSubprojectHistory(subprojectId).then(setEntries).catch(() => setEntries([]));
  }, [subprojectId]);
  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <h3 style={{ color: "var(--navy)", marginTop: 0 }}>{name}</h3>
      <HistoryTimeline entries={entries} />
    </div>
  );
}

export default function ProjectHistoryTab() {
  const { project } = useProjectWorkspace();
  const [entries, setEntries] = useState<PlanHistoryEntry[]>([]);

  useEffect(() => {
    api.getProjectHistory(project.id).then(setEntries).catch(() => setEntries([]));
  }, [project.id]);

  return (
    <div style={{ maxHeight: "70vh", overflowY: "auto" }}>
      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3 style={{ color: "var(--navy)", marginTop: 0 }}>Projekt</h3>
        <HistoryTimeline entries={entries} />
      </div>
      {project.subprojects.map((sp) => (
        <SubprojectHistorySection key={sp.id} subprojectId={sp.id} name={sp.name} />
      ))}
    </div>
  );
}
