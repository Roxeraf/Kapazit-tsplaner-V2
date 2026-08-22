import { useEffect, useState } from "react";
import { api } from "../../api/client";
import DocumentListPanel from "./components/DocumentListPanel";
import type { Document } from "../../types";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

// P19.5 (P19_PLANPHASE_WORKSPACE_UX_AUDIT.md Abschnitt 3.10/13): Die eigentliche
// Darstellungslogik (Upload, Suche, Typ-/Tag-Filter, Backlinks, Löschen) lebt jetzt in
// DocumentListPanel.tsx, geteilt mit dem Dateien-Tab im PlanPhaseWorkspace. Dieser Tab bleibt
// für das reine Laden der projektweiten Dokumentenliste zuständig (unverändertes Verhalten:
// alle Dokumente des Projekts, kein Entity-Filter).
export default function ProjectDocumentsTab() {
  const { project } = useProjectWorkspace();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    api
      .listDocuments(project.id)
      .then(setDocuments)
      .catch((e) => setError(String(e)));
  };

  useEffect(refresh, [project.id]);

  return (
    <div>
      {error && <p style={{ color: "var(--rot)" }}>{error}</p>}
      <DocumentListPanel projectId={project.id} documents={documents} onRefresh={refresh} />
    </div>
  );
}
