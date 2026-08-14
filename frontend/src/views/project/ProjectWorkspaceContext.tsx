import { useOutletContext } from "react-router-dom";
import type { ProjectDetail } from "../../types";

export interface ProjectWorkspaceContextValue {
  project: ProjectDetail;
  reload: () => void;
}

export function useProjectWorkspace() {
  return useOutletContext<ProjectWorkspaceContextValue>();
}
