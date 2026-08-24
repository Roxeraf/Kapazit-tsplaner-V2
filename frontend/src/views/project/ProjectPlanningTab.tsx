import BaselineList from "./components/BaselineList";
import MilestoneList from "./components/MilestoneList";
import PlanPhaseList from "./components/PlanPhaseList";
import ProjectMonthlyCapacityCard from "./components/ProjectMonthlyCapacityCard";
import { useProjectWorkspace } from "./ProjectWorkspaceContext";

// P11 (Planungs-/Kapazitätskonsolidierung): Der Planning-Tab konzentriert sich jetzt
// ausschließlich auf Planung (PlanPhase/Milestone/Kapazität/Planstände). Die Projektstammdaten
// (Name/Kunde/Startmonat/Anzahl Monate) inkl. des batch-/grund-basierten Speichern-Workflows
// (PlanHistory) sind in den Einstellungen-Tab umgezogen (siehe ProjectSettingsTab).
//
// P19.7 (PlanPhase-Baum ist die EINZIGE operative Planungsebene, CONCEPT.md Abschnitt 16):
// die PlanPhase-Liste steht oben und immer offen; Milestones/Projektkapazität/Planstände
// bleiben als projektweite Zusatzbereiche direkt sichtbar daneben.
//
// P20.1 (Auftrag Abschnitt 15): der alte Bedienweg (Teilprojekt-CRUD + ResourceDemandGrid,
// beide @deprecated P18/B-8) ist HIER ENTFERNT - ein normaler Projektleiter sieht diese
// Legacy-Kapazitätsplanung nicht mehr. Bleibt bis zum produktiven B-8-Cutover ausschließlich
// über Administration → "Legacy-Kapazitätsplanung" erreichbar (siehe
// LegacyCapacityDiagnostics.tsx) - keine Datenlöschung, reiner Sichtbarkeits-/Ortswechsel.
export default function ProjectPlanningTab() {
  const { project } = useProjectWorkspace();
  const projectId = project.id;

  return (
    <div>
      {/* Primäre, immer offene Planungsebene (P19.7: PlanPhase-Baum ist die einzige operative
          Planungsebene, CONCEPT.md Abschnitt 16). */}
      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <PlanPhaseList projectId={projectId} />
      </div>

      {/* Projektweite Zusatzbereiche (Audit §16) - bleiben sichtbar, sind kein Legacy. */}
      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <MilestoneList projectId={projectId} />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <ProjectMonthlyCapacityCard projectId={projectId} />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <BaselineList projectId={projectId} />
      </div>
    </div>
  );
}
