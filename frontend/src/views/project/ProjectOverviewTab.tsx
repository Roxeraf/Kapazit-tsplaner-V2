import { useProjectWorkspace } from "./ProjectWorkspaceContext";

export default function ProjectOverviewTab() {
  const { project } = useProjectWorkspace();
  return (
    <div className="stub-view">
      Übersicht für „{project.name}" — in Planung (siehe CONCEPT.md, Phase 5 Übersicht-Tab).
    </div>
  );
}
