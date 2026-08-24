import MilestoneList from "./components/MilestoneList";
import PlanPhaseList from "./components/PlanPhaseList";
import ProjectMonthlyCapacityCard from "./components/ProjectMonthlyCapacityCard";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

// P11: Planning-Tab konzentriert sich auf Planung (PlanPhase/Milestone/Kapazität).
// P19.7: PlanPhase-Baum ist die einzige operative Planungsebene.
// P20.1: Legacy-Kapazitätsplanung (Teilprojekt-CRUD + ResourceDemandGrid) liegt unter
// Administration → "Legacy-Kapazitätsplanung".
// P20.3: Planstände sind kein Benutzerkonzept mehr — der Block ist entfernt. Nachvollziehbarkeit
// liegt ausschließlich im Historie-Tab (automatischer Audit Trail).
export default function ProjectPlanningTab() {
  const { project } = useProjectWorkspace();
  const projectId = project.id;

  return (
    <div>
      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <PlanPhaseList projectId={projectId} />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <MilestoneList projectId={projectId} />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <ProjectMonthlyCapacityCard projectId={projectId} />
      </div>
    </div>
  );
}
